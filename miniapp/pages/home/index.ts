/**
 * 工作台首页
 * 展示当前进度和快速入口
 */
import { get } from '../../api/request'
import { getDiagnosisTips, getIndustrySkill, type SkillKey } from '../../skills/index'
import type { BusinessProfile, DiagnosisReport, SevenDayPlan, ReviewReport } from '../../types/index'

interface HomeData {
  business: BusinessProfile | null
  diagnosis: DiagnosisReport | null
  plan: SevenDayPlan | null
  review: ReviewReport | null
  loading: boolean
  skillTips: string[]
  skillLabel: string
  skillIcon: string
}

Page<HomeData, {}>({
  data: {
    business: null,
    diagnosis: null,
    plan: null,
    review: null,
    loading: true,
    skillTips: [],
    skillLabel: '',
    skillIcon: '',
  },

  onShow() {
    this.loadAll()
  },

  async loadAll() {
    const app = getApp()
    const { businessId, diagnosisId, planId } = app.globalData

    this.setData({ loading: true })

    try {
      const results: Partial<HomeData> = {}

      if (businessId) {
        try {
          results.business = await get<BusinessProfile>(`/business/${businessId}`)
          if (results.business?.industry) {
            const skill = getIndustrySkill(results.business.industry)
            results.skillTips = getDiagnosisTips(results.business.industry)
            results.skillLabel = skill.label
            results.skillIcon = skill.icon
          }
        } catch { /* ignore */ }
      }
      if (diagnosisId) {
        try {
          results.diagnosis = await get<DiagnosisReport>(`/diagnosis/${diagnosisId}`)
        } catch { /* ignore */ }
      }
      if (planId) {
        try {
          results.plan = await get<SevenDayPlan>(`/execution/${planId}`)
        } catch { /* ignore */ }
      }

      this.setData({ ...results, loading: false } as HomeData)
    } catch {
      this.setData({ loading: false })
    }
  },

  /** 跳转：填写企业信息 */
  goProfile() {
    wx.navigateTo({ url: '/pages/profile/index' })
  },

  /** 跳转：诊断报告 */
  goDiagnosis() {
    const diagnosisId = getApp().globalData.diagnosisId
    if (diagnosisId) {
      wx.navigateTo({ url: `/pages/diagnosis/index` })
    } else {
      wx.navigateTo({ url: '/pages/profile/index' })
    }
  },

  /** 跳转：执行计划（tabBar） */
  goPlan() {
    wx.switchTab({ url: '/pages/plan/index' })
  },

  /** 跳转：上传截图 */
  goUpload() {
    const planId = getApp().globalData.planId
    if (planId) {
      wx.navigateTo({ url: `/pages/upload/index` })
    } else {
      wx.showToast({ title: '请先生成执行计划', icon: 'none' })
    }
  },

  /** 跳转：复盘报告（tabBar） */
  goReview() {
    wx.switchTab({ url: '/pages/review/index' })
  },

  /** 重新开始 */
  onReset() {
    wx.showModal({
      title: '确认重新开始？',
      content: '将清除所有数据，从头开始填写企业信息',
      success: (res) => {
        if (res.confirm) {
          const app = getApp()
          app.resetAll()
          this.setData({
            business: null,
            diagnosis: null,
            plan: null,
            review: null,
          })
          wx.navigateTo({ url: '/pages/profile/index' })
        }
      },
    })
  },
})
