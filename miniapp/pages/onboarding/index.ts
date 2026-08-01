/**
 * 新用户引导页 Onboarding，四步收集企业信息并启动诊断
 *
 * @file    pages/onboarding/index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import { ensureLogin, hasBusinessInfo, hasDiagnosis } from '../../utils/auth'
import {
  INDUSTRIES,
  MARKETING_CHANNELS,
  MONTHLY_BUDGETS,
  PRICE_RANGES,
  TEAM_SIZES,
} from '../../utils/constants'
import { setStorage, STORAGE_KEYS } from '../../utils/storage'

import { post } from '../../api/request'

interface FormData {
  company_name: string
  industry: string
  city: string
  team_size: string
  main_product: string
  price_range: string
  target_customer: string
  current_channels: string[]
  monthly_budget: string
  biggest_pain: string
}

interface OnboardingPageData {
  currentStep: number
  stepTitles: string[]
  formData: FormData
  industries: string[]
  teamSizes: string[]
  priceRanges: string[]
  monthlyBudgets: string[]
  marketingChannels: string[]
  canNextStep: boolean
  submitting: boolean
  industryIndex: number
  teamSizeIndex: number
  priceRangeIndex: number
  monthlyBudgetIndex: number
}

Page({
  data: {
    currentStep: 0,
    stepTitles: [
      '企业基本信息',
      '产品与目标客户',
      '当前营销现状',
      '确认并启动诊断',
    ],
    formData: {
      company_name: '',
      industry: '',
      city: '',
      team_size: '',
      main_product: '',
      price_range: '',
      target_customer: '',
      current_channels: [],
      monthly_budget: '',
      biggest_pain: '',
    } as FormData,
    industries: INDUSTRIES,
    teamSizes: TEAM_SIZES,
    priceRanges: PRICE_RANGES,
    monthlyBudgets: MONTHLY_BUDGETS,
    marketingChannels: MARKETING_CHANNELS,
    canNextStep: false,
    submitting: false,
    industryIndex: 0,
    teamSizeIndex: 0,
    priceRangeIndex: 0,
    monthlyBudgetIndex: 0,
  } as OnboardingPageData,

  /**
   * 页面加载：检查业务状态，确保登录，校验当前步骤
   *
   * @description 若已完成企业信息+诊断则跳首页，否则确保登录并校验当前步骤可推进性
   * @returns Promise<void>
   * @example
   * ```ts
   * // 首次进入自动执行
   * await onLoad()
   * ```
   */
  async onLoad(): Promise<void> {
    if (hasBusinessInfo() && hasDiagnosis()) {
      wx.redirectTo({ url: '/pages/home/index' })
      return
    }
    await ensureLogin(true)
    this.validateCurrentStep()
  },

  /**
   * 文本输入事件：更新 formData 对应字段并校验当前步骤
   *
   * @param e 输入事件，dataset.field 指定字段名，detail.value 为输入值
   * @returns void
   */
  onInput(e: WechatMiniprogram.Input): void {
    const { field } = e.currentTarget.dataset
    const { value } = e.detail
    this.setData({
      [`formData.${field}`]: value,
    })
    this.validateCurrentStep()
  },

  /**
   * Picker 选择器变更事件：更新表单字段与对应索引，校验当前步骤
   *
   * @param e picker change 事件，dataset.field=目标字段，dataset.source=数据源属性名
   * @returns void
   */
  onPickerChange(e: WechatMiniprogram.BaseEvent<{ value: string | number }>): void {
    const { field, source } = e.currentTarget.dataset
    const index = Number(e.detail.value)
    const arr = (this.data as unknown as Record<string, string[]>)[source]
    const value = arr[index]
    const update: Record<string, string | number> = {
      [`formData.${field}`]: value,
    }
    const indexField = field.replace(/([A-Z])/g, '_$1').toLowerCase() + '_index'
    if ((this.data as unknown as Record<string, unknown>)[indexField] !== undefined) {
      update[indexField] = index
    } else {
      const map: Record<string, string> = {
        industry: 'industryIndex',
        team_size: 'teamSizeIndex',
        price_range: 'priceRangeIndex',
        monthly_budget: 'monthlyBudgetIndex',
      }
      if (map[field]) {
        update[map[field]] = index
      }
    }
    this.setData(update)
    this.validateCurrentStep()
  },

  /**
   * 营销渠道多选事件：更新当前渠道集合并校验
   *
   * @param e checkbox change 事件，detail.value 为选中索引数组
   * @returns void
   */
  onChannelChange(e: WechatMiniprogram.BaseEvent<{ value: (string | number)[] }>): void {
    const values = e.detail.value
    const selected = values.map((i: string | number) => this.data.marketingChannels[Number(i)])
    this.setData({
      'formData.current_channels': selected,
    })
    this.validateCurrentStep()
  },

  /**
   * 根据当前步骤的必填规则校验可推进性并写回 canNextStep
   */
  validateCurrentStep(): void {
    const { currentStep, formData } = this.data
    let valid = false
    switch (currentStep) {
      case 0:
        valid = !!(
          formData.company_name.trim() &&
          formData.industry &&
          formData.city.trim() &&
          formData.team_size
        )
        break
      case 1:
        valid = !!(
          formData.main_product.trim() &&
          formData.price_range &&
          formData.target_customer.trim()
        )
        break
      case 2:
        valid = !!(
          formData.current_channels.length > 0 &&
          formData.monthly_budget &&
          formData.biggest_pain.trim()
        )
        break
      case 3:
        valid = true
        break
    }
    this.setData({ canNextStep: valid })
  },

  /**
   * 全量校验所有步骤（用于提交前最终校验）
   *
   * @returns 校验失败返回错误提示文案，通过返回 null
   */
  validateAllSteps(): string | null {
    const f = this.data.formData
    if (!f.company_name.trim()) return '请填写企业名称'
    if (!f.industry) return '请选择行业'
    if (!f.city.trim()) return '请填写所在城市'
    if (!f.team_size) return '请选择团队规模'
    if (!f.main_product.trim()) return '请填写主营产品'
    if (!f.price_range) return '请选择客单价范围'
    if (!f.target_customer.trim()) return '请描述目标客户'
    if (f.current_channels.length === 0) return '请选择至少一个营销渠道'
    if (!f.monthly_budget) return '请选择月营销预算'
    if (!f.biggest_pain.trim()) return '请描述最大痛点'
    return null
  },

  /**
   * 下一步：校验当前步骤可推进则 currentStep + 1 并重新校验
   *
   * @returns void
   */
  onNextStep(): void {
    if (!this.data.canNextStep) {
      wx.showToast({ title: '请完成当前步骤必填项', icon: 'none' })
      return
    }
    const nextStep = this.data.currentStep + 1
    if (nextStep < 4) {
      this.setData({ currentStep: nextStep })
      this.validateCurrentStep()
    }
  },

  /**
   * 上一步：回退一步并重新校验
   *
   * @returns void
   */
  onPrevStep(): void {
    const prev = this.data.currentStep - 1
    if (prev >= 0) {
      this.setData({ currentStep: prev })
      this.validateCurrentStep()
    }
  },

  /**
   * 提交表单：全量校验 → 创建企业 → 启动诊断 → 跳转诊断页
   *
   * @description 失败时 toast 提示；成功后 businessId/diagnosisId 会写入 App 状态与 Storage
   * @returns Promise<void>
   * @example
   * ```ts
   * // 绑定到"确认并启动诊断"按钮
   * bindtap="onSubmit"
   * ```
   */
  async onSubmit(): Promise<void> {
    const missing = this.validateAllSteps()
    if (missing) {
      wx.showToast({ title: missing, icon: 'none' })
      return
    }
    if (this.data.submitting) return
    this.setData({ submitting: true })
    wx.showLoading({ title: '启动诊断中...', mask: true })
    try {
      const businessResult = await post<{ id: string; business_id?: string }>(
        '/business/create',
        this.data.formData as unknown as Record<string, unknown>,
      )
      const businessId = businessResult.business_id ?? businessResult.id
      const app = getApp<IAppOption>()
      app.saveState('businessId', businessId)
      setStorage(STORAGE_KEYS.BUSINESS_ID, businessId)
      setStorage(STORAGE_KEYS.BUSINESS_INFO, { ...this.data.formData, id: businessId })

      const diagnosisResult = await post<{ id: string; diagnosis_id?: string }>(
        '/diagnosis/start',
        {
          business_id: businessId,
          ...(this.data.formData as unknown as Record<string, unknown>),
        },
      )
      const diagnosisId = diagnosisResult.diagnosis_id ?? diagnosisResult.id
      app.saveState('diagnosisId', diagnosisId)
      setStorage(STORAGE_KEYS.DIAGNOSIS_ID, diagnosisId)

      wx.hideLoading()
      wx.redirectTo({ url: '/pages/diagnosis/index' })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[onboarding] onSubmit failed:`, msg)
      wx.hideLoading()
      wx.showToast({
        title: msg || '提交失败，请重试',
        icon: 'none',
      })
    } finally {
      this.setData({ submitting: false })
    }
  },
})
