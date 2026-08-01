/**
 * 复盘提交页 Review，四问一图表单提交 + AI 分析报告轮询
 *
 * @file    pages/review/index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import type { MetricComparison, ReviewReport, ReviewSubmitForm } from '../../types/index'

import { REVIEW_TYPES, REVIEW_TYPE_LABEL } from '../../utils/constants'

import { get, post } from '../../api/request'

interface MetricItem {
  name: string
  target: number
  actual: number
  percent: number
  achieved: boolean
}

interface ReviewPageData {
  reviewType: 'weekly' | 'monthly' | 'quarterly'
  weekNumber: number
  formData: ReviewSubmitForm
  submitting: boolean
  submittingProgress: number

  analysisLoading: boolean
  latestReview: ReviewReport | null
  metrics: MetricItem[]
  showAnalysis: boolean
  aiProcessing: boolean
}

const EMPTY_FORM: ReviewSubmitForm = {
  review_type: 'weekly',
  week_number: 3,
  completed_tasks: '',
  incomplete_tasks: '',
  key_takeaway: '',
  difficulties: '',
  images: [],
}

Page<ReviewPageData, {}>({
  data: {
    reviewType: REVIEW_TYPES.WEEKLY,
    weekNumber: 3,
    formData: { ...EMPTY_FORM },
    submitting: false,
    submittingProgress: 0,

    analysisLoading: false,
    latestReview: null,
    metrics: [],
    showAnalysis: false,
    aiProcessing: false,
  },

  /**
   * 页面加载：校验 planId → 绑定周数 → 加载最近复盘报告
   *
   * @returns Promise<void>
   */
  async onLoad(): Promise<void> {
    const app = getApp<IAppOption>()
    if (!app.globalData.planId) {
      wx.showToast({ title: '请先生成本周任务', icon: 'none' })
      setTimeout(() => {
        wx.navigateTo({ url: '/pages/weekly-plan/index' })
      }, 1200)
      return
    }

    const weekNumber = app.globalData.currentWeek || 3
    this.setData({
      weekNumber,
      formData: {
        ...this.data.formData,
        week_number: weekNumber,
      },
    })

    await this.loadLatestReview()
  },

  /**
   * 页面展示：planId 缺失则跳转周计划
   *
   * @returns Promise<void>
   */
  async onShow(): Promise<void> {
    const app = getApp<IAppOption>()
    if (!app.globalData.planId) {
      wx.navigateTo({ url: '/pages/weekly-plan/index' })
      return
    }
  },

  /**
   * 加载最近复盘报告：失败时静默置空 loading
   *
   * @returns Promise<void>
   */
  async loadLatestReview(): Promise<void> {
    this.setData({ analysisLoading: true })
    try {
      const review = await get<ReviewReport>('/review/latest')
      this.renderReview(review)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.warn(`[review] loadLatestReview no data:`, msg)
      this.setData({ analysisLoading: false })
    }
  },

  /**
   * 渲染复盘报告：保存 reviewId，计算指标对比数组，如 AI 处理中则启动轮询
   *
   * @param review 复盘报告
   */
  renderReview(review: ReviewReport): void {
    const app = getApp<IAppOption>()
    app.saveState('reviewId', review.id)
    app.globalData.latestReview = review

    const metrics = (review.vs_target || []).map((m: MetricComparison) => ({
      name: m.metric_name,
      target: m.target,
      actual: m.actual,
      percent: m.target > 0 ? Math.min(100, Math.round((m.actual / m.target) * 100)) : 0,
      achieved: m.achieved,
    }))

    const aiProcessing = review.ai_analysis_status === 'processing'

    this.setData({
      latestReview: review,
      metrics,
      showAnalysis: true,
      analysisLoading: false,
      aiProcessing,
    })

    if (aiProcessing) {
      this.startPollingReview()
    }
  },

  /**
   * AI 分析轮询：每 10s 拉一次，最多 3 次；done 成功/failed 失败/超出次数停止
   */
  startPollingReview(): void {
    let attempts = 0
    const maxAttempts = 3
    const interval = 10000

    const poll = async (): Promise<void> => {
      attempts++
      if (attempts > maxAttempts) return

      try {
        const review = await get<ReviewReport>('/review/latest')
        if (review.ai_analysis_status === 'done') {
          this.renderReview(review)
          wx.showToast({ title: 'AI分析完成', icon: 'success' })
          return
        }
        if (review.ai_analysis_status === 'failed') {
          this.setData({ aiProcessing: false })
          wx.showToast({ title: 'AI分析失败，请稍后刷新', icon: 'none' })
          return
        }
        setTimeout(poll, interval)
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        console.warn(`[review] poll retry:`, msg)
        setTimeout(poll, interval)
      }
    }

    setTimeout(poll, interval)
  },

  /**
   * 复盘类型切换（weekly/monthly/quarterly）
   *
   * @param e dataset.type 为目标类型
   * @returns void
   */
  onSelectReviewType(e: WechatMiniprogram.BaseEvent): void {
    const type = e.currentTarget?.dataset?.type as 'weekly' | 'monthly' | 'quarterly'
    if (!type) return
    this.setData({
      reviewType: type,
      formData: {
        ...this.data.formData,
        review_type: type,
      },
    })
  },

  /**
   * 表单输入事件（textarea / input）
   *
   * @param e dataset.field 为 ReviewSubmitForm 的字段名
   * @returns void
   */
  onInput(e: WechatMiniprogram.Input | WechatMiniprogram.TextareaInput): void {
    const field = e.currentTarget?.dataset?.field as keyof ReviewSubmitForm
    if (!field) return
    const value = e.detail?.value || ''
    this.setData({
      formData: {
        ...this.data.formData,
        [field]: value,
      } as ReviewSubmitForm,
    })
  },

  /**
   * 选择复盘截图：最多 9 张，超限 toast 提示
   *
   * @returns void
   */
  onSelectImages(): void {
    const currentCount = this.data.formData.images?.length || 0
    const remainCount = 9 - currentCount
    if (remainCount <= 0) {
      wx.showToast({ title: '最多上传9张', icon: 'none' })
      return
    }

    wx.chooseMedia({
      count: remainCount,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const newUrls = res.tempFiles.map((f) => f.tempFilePath)
        this.setData({
          formData: {
            ...this.data.formData,
            images: [...(this.data.formData.images || []), ...newUrls],
          },
        })
      },
    })
  },

  /**
   * 预览截图
   *
   * @param e dataset.idx 为 images 数组索引
   * @returns void
   */
  onPreviewImage(e: WechatMiniprogram.BaseEvent): void {
    const idx = e.currentTarget?.dataset?.idx as number
    if (idx === undefined || idx === null) return
    const urls = this.data.formData.images || []
    wx.previewImage({
      urls,
      current: urls[idx],
    })
  },

  /**
   * 删除截图
   *
   * @param e dataset.idx 为 images 数组索引
   * @returns void
   */
  onRemoveImage(e: WechatMiniprogram.BaseEvent): void {
    const idx = e.currentTarget?.dataset?.idx as number
    if (idx === undefined || idx === null) return
    const images = [...(this.data.formData.images || [])]
    images.splice(idx, 1)
    this.setData({
      formData: {
        ...this.data.formData,
        images,
      },
    })
  },

  /**
   * 提交复盘：必填校验 → 空图建议 → _doSubmit
   *
   * @returns Promise<void>
   */
  async onSubmitReview(): Promise<void> {
    if (this.data.submitting) return

    const { formData } = this.data

    if (!formData.completed_tasks?.trim()) {
      wx.showToast({ title: '请填写Q1：完成了哪些任务', icon: 'none' })
      return
    }
    if (!formData.incomplete_tasks?.trim()) {
      wx.showToast({ title: '请填写Q2：哪些没完成', icon: 'none' })
      return
    }
    if (!formData.key_takeaway?.trim()) {
      wx.showToast({ title: '请填写Q3：最大收获', icon: 'none' })
      return
    }
    if (!formData.difficulties?.trim()) {
      wx.showToast({ title: '请填写Q4：遇到的困难', icon: 'none' })
      return
    }

    if (!formData.images || formData.images.length === 0) {
      wx.showModal({
        title: '提示',
        content: '建议上传数据截图，AI分析会更准确哦~',
        confirmText: '继续提交',
        cancelText: '去上传',
        success: (res) => {
          if (res.cancel) {
            this.onSelectImages()
          } else {
            this._doSubmit()
          }
        },
      })
      return
    }

    this._doSubmit()
  },

  /**
   * 实际执行提交：POST /review/submit → 保存 reviewId → 刷新报告
   *
   * @returns Promise<void>
   */
  async _doSubmit(): Promise<void> {
    this.setData({
      submitting: true,
      submittingProgress: 10,
    })

    try {
      this.setData({ submittingProgress: 30 })

      const submitBody: ReviewSubmitForm = {
        ...this.data.formData,
        review_type: this.data.reviewType,
        week_number: this.data.weekNumber,
      }

      const result = await post<{ review_id?: string }>(
        '/review/submit',
        submitBody as unknown as Record<string, unknown>,
      )
      this.setData({ submittingProgress: 70 })

      if (result?.review_id) {
        const app = getApp<IAppOption>()
        app.saveState('reviewId', result.review_id)
      }

      this.setData({ submittingProgress: 85 })

      await this.loadLatestReview()

      this.setData({
        submitting: false,
        submittingProgress: 100,
      })

      wx.showToast({ title: '提交成功', icon: 'success' })

      if (this.data.aiProcessing) {
        setTimeout(() => {
          wx.showToast({
            title: 'AI分析中，30秒后刷新',
            icon: 'none',
            duration: 3000,
          })
        }, 800)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[review] _doSubmit failed:`, msg)
      this.setData({
        submitting: false,
        submittingProgress: 0,
      })
      wx.showToast({ title: msg || '提交失败', icon: 'none' })
    }
  },

  /**
   * 刷新 AI 分析报告
   *
   * @returns void
   */
  onRefreshAnalysis(): void {
    this.loadLatestReview()
  },
})
