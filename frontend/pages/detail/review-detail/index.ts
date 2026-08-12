/**
 * 复盘详情页（阶段四 · 复盘与提升闭环）
 *
 * 展示 AI 周复盘报告：总评 / 指标达成(vs_target) / 做得好 / 待改进 / 下周建议。
 *
 * 闭环落点：用户点击「采纳建议并生成下周计划」→ 调用 applyReview：
 *   后端据建议重新生成下周计划并自动排期 → 前端拉回真实 todos → 跳转日程页。
 * 这一跳完成了「复盘 → 更新计划 → 进入执行」的闭环，无需手动在多个功能间穿梭。
 */

import { store, bindStore } from '../../../store/index'
import { submitFeedback, applyReview, getSchedule } from '../../../api/loops'
import { classifyError, showErrorToast } from '../../../utils/error'
import type { ReviewReport, MetricComparison } from '../../../types'
import { formatRelativeTime } from '../../../utils/date'

interface MetricVM extends MetricComparison {
  rate: number
  rateColor: string
}

interface ReviewData {
  hasData: boolean
  review: ReviewReport | null
  summary: string
  metrics: MetricVM[]
  whatWorked: string[]
  whatDidnt: string[]
  suggestions: string[]
  businessId: string
  weekNumber: number
  updatedText: string
  applying: boolean
  /** 采纳后是否已完成排期（展示成功态） */
  applied: boolean
}

Page<ReviewData, Record<string, any>>({
  data: {
    hasData: false,
    review: null,
    summary: '',
    metrics: [],
    whatWorked: [],
    whatDidnt: [],
    suggestions: [],
    businessId: '',
    weekNumber: 0,
    updatedText: '',
    applying: false,
    applied: false,
  } as ReviewData,

  _unsub: undefined as (() => void) | undefined,

  onLoad(): void {
    const unsub = bindStore(this, (s) => this.build(s.review, s.profile?.business_id))
    this._unsub = unsub
  },

  onUnload(): void {
    if (this._unsub) this._unsub()
  },

  build(r: ReviewReport | null, businessId?: string): Partial<ReviewData> {
    if (!r) {
      return { hasData: false, review: null, metrics: [], whatWorked: [], whatDidnt: [], suggestions: [] }
    }
    return {
      hasData: true,
      review: r,
      summary: r.summary || '',
      metrics: (r.vs_target || []).map((m) => this.metricVM(m)),
      whatWorked: r.what_worked || [],
      whatDidnt: r.what_didnt || [],
      suggestions: r.suggestions || [],
      businessId: businessId || r.business_id || '',
      weekNumber: r.week_number || 0,
      updatedText: r.created_at ? `生成于 ${formatRelativeTime(r.created_at)}` : '',
    }
  },

  /** 指标达成率计算 + 配色 */
  metricVM(m: MetricComparison): MetricVM {
    const target = Number(m.target || 0)
    const actual = Number(m.actual || 0)
    const rate = target > 0 ? Math.round((actual / target) * 100) : m.achieved ? 100 : 0
    const rateColor = rate >= 100 ? '#07c160' : rate >= 70 ? '#ff976a' : '#ee0a24'
    return { ...m, rate, rateColor }
  },

  /** 采纳建议 → 生成下周计划并自动排期 → 跳日程 */
  onApply(): void {
    const r = this.data.review
    if (!r || !r.id) {
      wx.showToast({ title: '复盘缺少 ID', icon: 'none' })
      return
    }
    if (this.data.applying) return
    this.setData({ applying: true })
    wx.showLoading({ title: '生成下周计划…', mask: true })

    applyReview(r.id, this.data.businessId)
      .then((res) => {
        wx.hideLoading()
        this.setData({ applying: false })
        if (!res.ok) {
          wx.showToast({ title: res.error || '采纳失败', icon: 'none' })
          return
        }
        if (res.plan) store.setPlan(res.plan)
        // 拉回带真实 id 的 todos，日程打卡才能落库
        return getSchedule(this.data.businessId).then((sr) => {
          if (sr && sr.ok && Array.isArray(sr.todos)) {
            store.setTodosFromBackend(sr.todos)
          }
          this.setData({ applied: true })
          wx.showToast({ title: '下周计划已排好', icon: 'success' })
          setTimeout(() => wx.switchTab({ url: '/pages/schedule/index' }), 900)
        })
      })
      .catch((err) => {
        wx.hideLoading()
        this.setData({ applying: false })
        showErrorToast(classifyError(err))
      })
  },

  /** 对单条建议点赞/踩，参与策略学习 */
  onRateSuggestion(e: WechatMiniprogram.TouchEvent): void {
    const { idx, rating } = e.currentTarget.dataset as { idx: number; rating: number }
    const r = this.data.review
    if (!r) return
    const suggestion = this.data.suggestions[idx]
    if (!suggestion) return
    submitFeedback({
      targetType: 'suggestion',
      targetId: r.id,
      rating: Number(rating),
      comment: suggestion,
      businessId: this.data.businessId,
    }).catch(() => {})
    wx.showToast({ title: Number(rating) > 0 ? '已采纳 👍' : '已记录 👎', icon: 'none' })
  },

  goChat(): void {
    wx.switchTab({ url: '/pages/chat/index' })
  },

  onShareAppMessage(): WechatMiniprogram.Page.ICustomShareContent {
    const w = this.data.weekNumber
    return {
      title: w ? `第 ${w} 周营销复盘 · 下周建议已生成` : '我的营销周复盘',
      path: '/pages/chat/index',
    }
  },
})
