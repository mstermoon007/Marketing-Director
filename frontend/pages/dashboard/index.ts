/**
 * 看板页（阶段四 · 数据闭环入口 + 季度进度）
 *
 * 在原有「综合健康度 / 五维雷达 / 今日任务」基础上补齐：
 *   1. 季度进度条（calculateQuarterProgress + weekToPhase）→ 看清自己在 12 周里的位置；
 *   2. 业务数据上传入口（uploadMetrics）→ 选 CSV / 截图上传，后端安全解析并回吐 KPI，
 *      为周末「复盘闭环」提供真实数据燃料。
 */

import { store, bindStore, ProfileSummary } from '../../store/index'
import { TASK_STATUS } from '../../utils/constants'
import { calculateQuarterProgress, weekToPhase, QUARTER_TOTAL_WEEKS } from '../../utils/date'
import { uploadMetrics, checkinTodo } from '../../api/loops'
import { classifyError, showErrorToast } from '../../utils/error'
import { getStorage, setStorage, STORAGE_KEYS } from '../../utils/storage'
import type { KpiResult } from '../../api/loops'

interface DashData {
  profile: ProfileSummary | null
  radarLabels: string[]
  radarValues: number[]
  overallScore: number
  weekCompletion: number
  todayTasks: any[]
  hasData: boolean

  // 阶段四新增
  currentWeek: number
  totalWeeks: number
  quarterProgress: number
  phaseName: string
  phaseIndex: number
  /** 数据上传 */
  uploading: boolean
  lastKpi: KpiResult | null
  mergedNumbers: Record<string, number>
  hasMerged: boolean
}

const DIM_LABELS: Record<string, string> = {
  positioning: '定位',
  product: '产品',
  channel: '渠道',
  content: '内容',
  conversion: '转化',
  service: '服务',
  repurchase: '复购',
}

/** 雷达图维度固定顺序（避免 Object.keys 无序导致每次进入顺序抖动）。 */
const DIM_ORDER: string[] = [
  'positioning',
  'product',
  'channel',
  'content',
  'conversion',
  'service',
  'repurchase',
]

Page<DashData, Record<string, any>>({
  data: {
    profile: null,
    radarLabels: ['定位', '产品', '渠道', '内容', '转化'],
    radarValues: [],
    overallScore: 0,
    weekCompletion: 0,
    todayTasks: [],
    hasData: false,

    currentWeek: 0,
    totalWeeks: QUARTER_TOTAL_WEEKS,
    quarterProgress: 0,
    phaseName: '',
    phaseIndex: 0,
    uploading: false,
    lastKpi: null,
    mergedNumbers: {},
    hasMerged: false,
  } as DashData,

  _unsub: undefined as (() => void) | undefined,

  onLoad(): void {
    const unsub = bindStore(this, (s) => this.derive(s.profile, s.todos))
    this._unsub = unsub
    this._restoreKpi()
  },

  onShow(): void {
    // 从其它页面（如对话里完成诊断/排期）返回时，重新派生并恢复上次 KPI 回显
    this.derive(store.getState().profile, store.getState().todos)
    this._restoreKpi()
  },

  onUnload(): void {
    if (this._unsub) this._unsub()
  },

  /** 从本地缓存恢复最近一次上传解析出的 KPI（跨页面/重启不丢失）。 */
  _restoreKpi(): void {
    const cached = getStorage<{
      lastKpi: KpiResult | null
      mergedNumbers: Record<string, number>
      hasMerged: boolean
    }>(STORAGE_KEYS.DASHBOARD_KPI)
    if (cached) {
      this.setData({
        lastKpi: cached.lastKpi || null,
        mergedNumbers: cached.mergedNumbers || {},
        hasMerged: !!cached.hasMerged,
      })
    }
  },

  /** 持久化最近一次上传解析结果，供下次进入看板回显。 */
  _persistKpi(lastKpi: KpiResult | null, mergedNumbers: Record<string, number>, hasMerged: boolean): void {
    setStorage(STORAGE_KEYS.DASHBOARD_KPI, { lastKpi, mergedNumbers, hasMerged })
  },

  /** 从 store 派生看板展示数据 */
  derive(profile: ProfileSummary | null, todos: any[]): Partial<DashData> {
    const dims = profile?.dimension_scores || {}
    // 固定维度顺序，未出现在 DIM_ORDER 的维度追加在末尾（兼容未来扩展）
    const keys = [...DIM_ORDER, ...Object.keys(dims).filter((k) => !DIM_ORDER.includes(k))]
    const labels: string[] = []
    const values: number[] = []
    keys.forEach((k) => {
      if (!(k in dims)) return
      labels.push(DIM_LABELS[k] || k)
      values.push(Number(dims[k]) || 0)
    })

    // 今日任务（按日期匹配今天）
    const today = this.todayStr()
    const todayTasks = (todos || []).filter((t) => t.date === today)

    // 本周完成率：仅统计「本周（周一~周日）」内的待办，避免跨周累计失真
    const { start, end } = this.weekRange()
    const weekTodos = (todos || []).filter((t) => t.date && t.date >= start && t.date <= end)
    const total = weekTodos.length
    const done = weekTodos.filter((t) => t.status === TASK_STATUS.DONE).length
    const weekCompletion = total ? Math.round((done / total) * 100) : 0

    // 阶段四：季度进度
    const cw = profile?.current_week || 0
    const phase = weekToPhase(cw)

    return {
      profile,
      radarLabels: labels.length ? labels : (['定位', '产品', '渠道', '内容', '转化'] as string[]),
      radarValues: values,
      overallScore: profile?.overall_score || 0,
      weekCompletion,
      todayTasks,
      hasData: !!(profile || total > 0),
      currentWeek: cw,
      totalWeeks: QUARTER_TOTAL_WEEKS,
      quarterProgress: calculateQuarterProgress(cw),
      phaseName: phase ? phase.name : '',
      phaseIndex: phase ? phase.index : 0,
    } as Partial<DashData>
  },

  /** 本周（周一 00:00 ~ 周日 23:59）的日期区间，用于按周聚合统计。 */
  weekRange(): { start: string; end: string } {
    const now = new Date()
    const dow = now.getDay() || 7 // 周日=0 归为 7，方便算周一偏移
    const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (dow - 1))
    const sunday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (dow - 1) + 6)
    const fmt = (d: Date) => {
      const m = `${d.getMonth() + 1}`.padStart(2, '0')
      const day = `${d.getDate()}`.padStart(2, '0')
      return `${d.getFullYear()}-${m}-${day}`
    }
    return { start: fmt(monday), end: fmt(sunday) }
  },

  todayStr(): string {
    const d = new Date()
    const m = `${d.getMonth() + 1}`.padStart(2, '0')
    const day = `${d.getDate()}`.padStart(2, '0')
    return `${d.getFullYear()}-${m}-${day}`
  },

  onTaskToggle(e: WechatMiniprogram.TouchEvent): void {
    const id = e.detail.id as string
    // 先更新本地状态（即时反馈），再上报后端打卡（闭环：完成态反馈至复盘 Agent）
    store.toggleTodo(id)
    const todo = store.getState().todos.find((t) => t.id === id)
    const status = todo?.status === TASK_STATUS.DONE ? 'done' : 'pending'
    checkinTodo({ todoId: id, status }).catch((err) => {
      console.warn('[dashboard] 任务打卡上报失败（本地已更新）：', err)
    })
  },

  /** 上传业务数据 → 后端解析 → 回吐 KPI */
  onUpload(): void {
    if (this.data.uploading) return
    // 优先用当前企业 ID（对话中已建立），回退到画像里携带的 business_id
    const businessId =
      store.getState().currentBusinessId || store.getState().profile?.business_id || ''
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      success: (res) => {
        const file = res.tempFiles && res.tempFiles[0]
        if (!file) return
        this.setData({ uploading: true })
        wx.showLoading({ title: '解析数据中…', mask: true })
        uploadMetrics(file.path, businessId)
          .then((r) => {
            wx.hideLoading()
            this.setData({ uploading: false })
            if (!r.ok) {
              wx.showToast({ title: r.error || '上传失败', icon: 'none' })
              return
            }
            this.setData({
              lastKpi: r.kpi || null,
              mergedNumbers: r.merged_numbers || {},
              hasMerged: !!(r.merged_numbers && Object.keys(r.merged_numbers).length),
            })
            this._persistKpi(
              r.kpi || null,
              r.merged_numbers || {},
              !!(r.merged_numbers && Object.keys(r.merged_numbers).length),
            )
            wx.showToast({ title: '数据已同步', icon: 'success' })
          })
          .catch((err) => {
            wx.hideLoading()
            this.setData({ uploading: false })
            showErrorToast(classifyError(err))
          })
      },
      fail: () => {
        // 用户取消选择，静默
      },
    })
  },

  goChat(): void {
    wx.switchTab({ url: '/pages/chat/index' })
  },

  goPlan(): void {
    wx.navigateTo({ url: '/pages/detail/plan-detail/index' })
  },

  goReview(): void {
    wx.navigateTo({ url: '/pages/detail/review-detail/index' })
  },
})
