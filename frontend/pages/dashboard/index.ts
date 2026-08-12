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
import { uploadMetrics } from '../../api/loops'
import { classifyError, showErrorToast } from '../../utils/error'
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
  },

  onUnload(): void {
    if (this._unsub) this._unsub()
  },

  /** 从 store 派生看板展示数据 */
  derive(profile: ProfileSummary | null, todos: any[]): Partial<DashData> {
    const dims = profile?.dimension_scores || {}
    const labels: string[] = []
    const values: number[] = []
    Object.keys(dims).forEach((k) => {
      labels.push(DIM_LABELS[k] || k)
      values.push(Number(dims[k]) || 0)
    })

    // 今日任务（按日期匹配今天）
    const today = this.todayStr()
    const todayTasks = (todos || []).filter((t) => t.date === today)

    // 本周完成率
    const total = (todos || []).length
    const done = (todos || []).filter((t) => t.status === TASK_STATUS.DONE).length
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

  todayStr(): string {
    const d = new Date()
    const m = `${d.getMonth() + 1}`.padStart(2, '0')
    const day = `${d.getDate()}`.padStart(2, '0')
    return `${d.getFullYear()}-${m}-${day}`
  },

  onTaskToggle(e: WechatMiniprogram.TouchEvent): void {
    const id = e.detail.id as string
    const todos = store.getState().todos.map((t) =>
      t.id === id
        ? { ...t, status: t.status === TASK_STATUS.DONE ? TASK_STATUS.PENDING : TASK_STATUS.DONE }
        : t,
    )
    store.setTodos(todos)
  },

  /** 上传业务数据 → 后端解析 → 回吐 KPI */
  onUpload(): void {
    if (this.data.uploading) return
    const businessId = store.getState().profile?.business_id || ''
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
