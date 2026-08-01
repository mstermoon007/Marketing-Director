/**
 * 个人中心 Profile，展示企业资料、执行统计与数据重置入口
 *
 * @file    pages/profile/index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import type { BusinessProfile } from '../../types/index'

import { hasBusinessInfo } from '../../utils/auth'
import {
  INDUSTRIES,
  MARKETING_CHANNELS,
  MONTHLY_BUDGETS,
  PHASES,
  PRICE_RANGES,
  TEAM_SIZES,
} from '../../utils/constants'
import { clearAllStorage, getStorage, setStorage, STORAGE_KEYS } from '../../utils/storage'

import { get, post, put } from '../../api/request'

interface Stats {
  totalTasksCompleted: number
  totalCheckinDays: number
  currentStreak: number
  weekCompletionRate: number
}

type EditForm = Partial<BusinessProfile>

interface ProfilePageData {
  business: BusinessProfile | null
  stats: Stats
  editing: boolean
  editForm: EditForm
  industries: string[]
  teamSizes: string[]
  priceRanges: string[]
  monthlyBudgets: string[]
  marketingChannels: string[]
  phaseList: typeof PHASES
  phaseText: string
  weekText: string
  weeksRemainingInQuarter: number
}

Page({
  data: {
    business: null as BusinessProfile | null,
    stats: {
      totalTasksCompleted: 0,
      totalCheckinDays: 0,
      currentStreak: 0,
      weekCompletionRate: 0,
    } as Stats,
    editing: false,
    editForm: {} as EditForm,
    industries: INDUSTRIES,
    teamSizes: TEAM_SIZES,
    priceRanges: PRICE_RANGES,
    monthlyBudgets: MONTHLY_BUDGETS,
    marketingChannels: MARKETING_CHANNELS,
    phaseList: PHASES,
    phaseText: '',
    weekText: '',
    weeksRemainingInQuarter: 0,
  } as ProfilePageData,

  /**
   * 页面展示：加载企业信息并计算统计
   *
   * @description onShow 时刷新，避免切换 tab 后数据过期
   * @returns Promise<void>
   */
  async onShow(): Promise<void> {
    await this.loadBusinessInfo()
    this.calcMockStats()
  },

  /**
   * 拉取企业信息（API → Storage 回退 → 跳 onboarding）
   *
   * @returns Promise<void>
   */
  async loadBusinessInfo(): Promise<void> {
    try {
      const business = await get<BusinessProfile>('/business/info')
      if (business) {
        setStorage(STORAGE_KEYS.BUSINESS_INFO, business)
        if (business.id || business.business_id) {
          const bid = business.business_id ?? business.id
          getApp<IAppOption>().saveState('businessId', bid)
          setStorage(STORAGE_KEYS.BUSINESS_ID, bid)
        }
        this.setData({
          business,
          phaseText: this.buildPhaseText(business.current_phase, business.current_week),
          weekText: this.buildWeekText(business.current_week),
          weeksRemainingInQuarter: Math.max(0, 12 - (business.current_week || 1)),
        })
      } else if (!hasBusinessInfo()) {
        wx.navigateTo({ url: '/pages/onboarding/index' })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.warn(`[profile] loadBusinessInfo fallback to cache:`, msg)
      const cached = getStorage<BusinessProfile>(STORAGE_KEYS.BUSINESS_INFO)
      if (cached) {
        this.setData({
          business: cached,
          phaseText: this.buildPhaseText(cached.current_phase, cached.current_week),
          weekText: this.buildWeekText(cached.current_week),
          weeksRemainingInQuarter: Math.max(0, 12 - (cached.current_week || 1)),
        })
      } else {
        wx.navigateTo({ url: '/pages/onboarding/index' })
      }
    }
  },

  /**
   * 构建阶段描述文案 "Phase X 名称"
   *
   * @param phase 阶段序号 1~3
   * @param week  当前周 1~12
   * @returns 格式化文本
   */
  buildPhaseText(phase?: number, week?: number): string {
    const p = PHASES.find((ph) => ph.index === phase) ?? PHASES[0]
    return `Phase ${p.index} ${p.name}`
  },

  /**
   * 构建周描述文案 "第 N 周"
   *
   * @param week 周数
   * @returns 格式化文本
   */
  buildWeekText(week?: number): string {
    const w = week ?? 1
    return `第 ${w} 周`
  },

  /**
   * 计算 mock 统计数据（当前为本地假数据，后续接入 API）
   */
  calcMockStats(): void {
    const totalTasksCompleted = 12
    const totalCheckinDays = 8
    const currentStreak = 3
    const weekCompletionRate = 67
    this.setData({
      stats: {
        totalTasksCompleted,
        totalCheckinDays,
        currentStreak,
        weekCompletionRate,
      },
    })
  },

  /**
   * 进入编辑模式：用现有 business 填充 editForm
   *
   * @returns void
   */
  onEditInfo(): void {
    if (!this.data.business) return
    const b = this.data.business
    this.setData({
      editing: true,
      editForm: {
        company_name: b.company_name,
        industry: b.industry,
        city: b.city,
        team_size: b.team_size,
        main_product: b.main_product,
        price_range: b.price_range,
        target_customer: b.target_customer,
        current_channels: [...(b.current_channels || [])],
        monthly_budget: b.monthly_budget,
        biggest_pain: b.biggest_pain,
      },
    })
  },

  /**
   * 取消编辑，清空 editForm
   *
   * @returns void
   */
  onCancelEdit(): void {
    this.setData({ editing: false, editForm: {} })
  },

  /**
   * 编辑模式文本输入事件
   *
   * @param e dataset.field 为字段名
   * @returns void
   */
  onEditInput(e: WechatMiniprogram.Input): void {
    const { field } = e.currentTarget.dataset
    this.setData({
      [`editForm.${field}`]: e.detail.value,
    })
  },

  /**
   * 编辑模式 Picker 选择事件
   *
   * @param e dataset.field 目标字段，dataset.source 数据源属性
   * @returns void
   */
  onEditPicker(e: WechatMiniprogram.BaseEvent<{ value: string | number }>): void {
    const { field, source } = e.currentTarget.dataset
    const index = Number(e.detail.value)
    const arr = (this.data as unknown as Record<string, string[]>)[source]
    const value = arr[index]
    this.setData({
      [`editForm.${field}`]: value,
    })
  },

  /**
   * 编辑模式渠道多选变更
   *
   * @param e checkbox 组 change 事件
   * @returns void
   */
  onEditChannelChange(e: WechatMiniprogram.BaseEvent<{ value: (string | number)[] }>): void {
    const values = e.detail.value
    const selected = values.map((i: string | number) => this.data.marketingChannels[Number(i)])
    this.setData({
      'editForm.current_channels': selected,
    })
  },

  /**
   * 保存编辑：必填校验 → PUT/POST → 回写 Storage → 刷新
   *
   * @returns Promise<void>
   */
  async onSaveEdit(): Promise<void> {
    const ef = this.data.editForm
    const required: (keyof EditForm)[] = [
      'company_name',
      'industry',
      'city',
      'team_size',
      'main_product',
      'price_range',
      'target_customer',
      'monthly_budget',
      'biggest_pain',
    ]
    for (const k of required) {
      const v = (ef as Record<string, unknown>)[k]
      if (Array.isArray(v)) {
        if (v.length === 0) {
          wx.showToast({ title: '请完成所有必填项', icon: 'none' })
          return
        }
      } else if (!String(v ?? '').trim()) {
        wx.showToast({ title: '请完成所有必填项', icon: 'none' })
        return
      }
    }
    try {
      wx.showLoading({ title: '保存中...', mask: true })
      const businessId = this.data.business?.id ?? this.data.business?.business_id ?? getApp<IAppOption>().globalData.businessId
      const payload = { ...ef }
      let result: BusinessProfile
      if (businessId) {
        result = await put<BusinessProfile>(`/business/${businessId}`, payload)
      } else {
        result = await post<BusinessProfile>('/business/create', payload)
      }
      if (result) {
        setStorage(STORAGE_KEYS.BUSINESS_INFO, result)
      }
      wx.hideLoading()
      wx.showToast({ title: '保存成功', icon: 'success' })
      this.setData({ editing: false, editForm: {} })
      await this.loadBusinessInfo()
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[profile] onSaveEdit failed:`, msg)
      wx.hideLoading()
      wx.showToast({
        title: msg || '保存失败',
        icon: 'none',
      })
    }
  },

  /**
   * 重置全部数据：弹确认框 → doResetAll
   *
   * @returns void
   */
  onResetAll(): void {
    wx.showModal({
      title: '重新开始',
      content: '此操作将清除当前的企业信息、诊断报告和所有执行数据，且不可恢复。确认要重新开始吗？',
      confirmColor: '#ee0a24',
      confirmText: '确认重置',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          this.doResetAll()
        }
      },
    })
  },

  /**
   * 执行重置：App.resetAll + clearAllStorage → reLaunch onboarding
   */
  doResetAll(): void {
    wx.showLoading({ title: '清除数据中...', mask: true })
    setTimeout((): void => {
      const app = getApp<IAppOption>()
      app.resetAll()
      clearAllStorage(false)
      wx.hideLoading()
      wx.reLaunch({ url: '/pages/onboarding/index' })
    }, 600)
  },

  /**
   * 跳诊断页
   *
   * @returns void
   */
  onGoDiagnosis(): void {
    wx.navigateTo({ url: '/pages/diagnosis/index' })
  },

  /**
   * 跳路线图 tab（兼容非 tab 环境）
   *
   * @returns void
   */
  onGoRoadmap(): void {
    wx.switchTab({
      url: '/pages/plan/index',
      fail: () => {
        wx.navigateTo({ url: '/pages/plan/index' })
      },
    })
  },

  /**
   * 跳复盘 tab（兼容非 tab 环境）
   *
   * @returns void
   */
  onGoReview(): void {
    wx.switchTab({
      url: '/pages/review/index',
      fail: () => {
        wx.navigateTo({ url: '/pages/review/index' })
      },
    })
  },

  /**
   * 跳周计划页
   *
   * @returns void
   */
  onGoWeekly(): void {
    wx.navigateTo({ url: '/pages/plan/index' })
  },
})
