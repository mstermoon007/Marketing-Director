/**
 * 诊断报告页 Diagnosis，展示五维评分、Top 问题与技能建议
 *
 * @file    pages/diagnosis/index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import type { DiagnosisReport } from '../../types/index'

import { ISSUE_LEVEL_COLOR, ISSUE_LEVEL_ICON, ISSUE_LEVEL_LABEL } from '../../utils/constants'
import { setStorage, STORAGE_KEYS } from '../../utils/storage'

import { get, post } from '../../api/request'

import { getDiagnosisTips, getIndustrySkill } from '../../skills/index'

interface DiagnosisPageData {
  loading: boolean
  generating: boolean
  report: DiagnosisReport | null
  skillLabel: string
  skillIcon: string
  skillTips: string[]
  issueLevelIcon: Record<string, string>
  issueLevelLabel: Record<string, string>
  issueLevelColor: Record<string, string>
}

Page<DiagnosisPageData, {}>({
  data: {
    loading: true,
    generating: false,
    report: null,
    skillLabel: '',
    skillIcon: '',
    skillTips: [],
    issueLevelIcon: ISSUE_LEVEL_ICON,
    issueLevelLabel: ISSUE_LEVEL_LABEL,
    issueLevelColor: ISSUE_LEVEL_COLOR,
  },

  /**
   * 页面加载：优先取 URL 参数 business_id，否则用全局
   *
   * @param options 路由参数 business_id
   * @returns void
   * @example
   * ```ts
   * wx.navigateTo({ url: '/pages/diagnosis/index?business_id=xxx' })
   * ```
   */
  onLoad(options: { business_id?: string }): void {
    const businessId = options.business_id || getApp<IAppOption>().globalData.businessId
    if (businessId) {
      this.loadReport(businessId)
    } else {
      this.setData({ loading: false })
    }
  },

  /**
   * 加载诊断报告：先拉 /diagnosis/latest，404 则触发 /diagnosis/start 重新生成
   *
   * @param businessId 企业ID
   * @returns Promise<void>
   */
  async loadReport(businessId: string): Promise<void> {
    this.setData({ loading: true })

    try {
      const app = getApp<IAppOption>()
      const industry = app.globalData.businessInfo?.industry || ''

      let report: DiagnosisReport | null = null

      try {
        report = await get<DiagnosisReport>('/diagnosis/latest', { business_id: businessId })
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : String(err)
        const statusCode = (err as { statusCode?: number }).statusCode ?? (errMsg.includes('404') ? 404 : 0)
        if (statusCode === 404 || errMsg.includes('404') || errMsg.includes('不存在')) {
          report = await post<DiagnosisReport>('/diagnosis/start', { business_id: businessId })
        } else {
          throw err
        }
      }

      if (report) {
        this.renderReport(report, industry)
      } else {
        this.setData({ loading: false })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[diagnosis] loadReport failed:`, msg)
      wx.showToast({ title: msg || '诊断失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  /**
   * 渲染报告：写回 App 状态、Storage 并更新页面 data
   *
   * @param report   诊断报告
   * @param industry 行业名，用于技能建议匹配
   */
  renderReport(report: DiagnosisReport, industry: string): void {
    const skill = getIndustrySkill(industry)
    const skillTips = industry ? getDiagnosisTips(industry) : []

    const app = getApp<IAppOption>()
    app.saveState('diagnosisId', report.id)
    app.globalData.diagnosisResult = report
    setStorage(STORAGE_KEYS.DIAGNOSIS, report)

    this.setData({
      report,
      skillLabel: skill.label,
      skillIcon: skill.icon,
      skillTips,
      loading: false,
    })
  },

  /**
   * 重试按钮：重新 loadReport
   *
   * @returns void
   */
  onRetry(): void {
    const businessId = getApp<IAppOption>().globalData.businessId
    if (businessId) {
      this.loadReport(businessId)
    } else {
      wx.showToast({ title: '请先填写企业信息', icon: 'none' })
    }
  },

  /**
   * 生成路线图：保存 report.quarterly_roadmap 到全局/Storage 并跳转 roadmap
   *
   * @description 跳转顺序：navigateTo roadmap → switchTab plan → reLaunch roadmap（多级兜底）
   * @returns void
   */
  onGeneratePlan(): void {
    if (!this.data.report) return
    this.setData({ generating: true })

    try {
      const app = getApp<IAppOption>()
      if (this.data.report.quarterly_roadmap) {
        app.globalData.currentRoadmap = this.data.report.quarterly_roadmap
        setStorage(STORAGE_KEYS.ROADMAP, this.data.report.quarterly_roadmap)
      }

      const pages = getCurrentPages()
      const tabBarPages = (app as unknown as { tabBarPages?: string[] })?.tabBarPages || [
        'pages/roadmap/index',
        'pages/plan/index',
        'pages/home/index',
        'pages/review/index',
      ]
      const isTabPage = tabBarPages.some((p: string) => p.includes('roadmap'))

      if (isTabPage) {
        wx.switchTab({ url: '/pages/roadmap/index' })
      } else {
        wx.navigateTo({
          url: '/pages/roadmap/index',
          fail: () => {
            wx.switchTab({
              url: '/pages/plan/index',
              fail: () => {
                wx.reLaunch({ url: '/pages/roadmap/index' })
              },
            })
          },
        })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[diagnosis] onGeneratePlan failed:`, msg)
      wx.showToast({ title: msg || '跳转失败', icon: 'none' })
    } finally {
      this.setData({ generating: false })
    }
  },
})
