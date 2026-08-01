/**
 * 季度路线图 Roadmap，三阶段展示、周切换与跳周计划入口
 *
 * @file    pages/roadmap/index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import type { PhaseItem, QuarterRoadmap } from '../../types/index'

import { PHASES, QUARTER_TOTAL_WEEKS } from '../../utils/constants'
import { weekToPhase, weekToPhaseIndex } from '../../utils/date'
import { setStorage, STORAGE_KEYS } from '../../utils/storage'

import { get } from '../../api/request'

interface RoadmapPageData {
  loading: boolean
  overallGoal: string
  currentWeek: number
  totalWeeks: number
  phases: PhaseItem[]
  phaseInfo: {
    phase_index: number
    phase_name: string
    weeks_cover: string
  } | null
  weekOptions: string[]
  weekIndex: number
}

Page<RoadmapPageData, {}>({
  data: {
    loading: true,
    overallGoal: '建立线上获客体系，月新增客户50人',
    currentWeek: 1,
    totalWeeks: 12,
    phases: [],
    phaseInfo: null,
    weekOptions: [],
    weekIndex: 0,
  },

  /**
   * 页面加载：初始化周选项并加载路线图数据
   *
   * @returns void
   */
  onLoad(): void {
    this.initWeekOptions()
    this.loadData()
  },

  /**
   * 页面展示：非首次进入自动刷新
   *
   * @returns void
   */
  onShow(): void {
    if (!this.data.loading) {
      this.loadData()
    }
  },

  /**
   * 初始化周下拉选项 "第 1 周" ... "第 12 周"
   */
  initWeekOptions(): void {
    const weekOptions: string[] = []
    for (let i = 1; i <= QUARTER_TOTAL_WEEKS; i++) {
      weekOptions.push(`第 ${i} 周`)
    }
    this.setData({ weekOptions })
  },

  /**
   * 加载路线图：API → 404 回退 App.globalData.diagnosisResult → 再失败置空
   *
   * @returns Promise<void>
   */
  async loadData(): Promise<void> {
    const app = getApp<IAppOption>()
    const businessId = app.globalData.businessId

    if (!businessId) {
      wx.navigateTo({ url: '/pages/onboarding/index' })
      return
    }

    this.setData({ loading: true })

    try {
      let roadmap: QuarterRoadmap | null = null

      try {
        roadmap = await get<QuarterRoadmap>('/roadmap/current', { business_id: businessId })
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        console.warn(`[roadmap] /roadmap/current fallback:`, msg)
        if (msg.includes('404') || msg.includes('不存在')) {
          const diagnosisResult = app.globalData.diagnosisResult
          if (diagnosisResult?.quarterly_roadmap) {
            roadmap = diagnosisResult.quarterly_roadmap
          }
        }
      }

      if (roadmap) {
        this.renderRoadmap(roadmap)
      } else {
        this.setData({
          loading: false,
          phases: [],
          phaseInfo: null,
        })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.warn(`[roadmap] loadData failed:`, msg)
      const diagnosisResult = getApp<IAppOption>().globalData.diagnosisResult
      if (diagnosisResult?.quarterly_roadmap) {
        this.renderRoadmap(diagnosisResult.quarterly_roadmap)
      } else {
        this.setData({
          loading: false,
          phases: [],
          phaseInfo: null,
        })
      }
    }
  },

  /**
   * 渲染路线图：写回全局 + Storage，计算当前阶段信息
   *
   * @param roadmap 季度路线图
   */
  renderRoadmap(roadmap: QuarterRoadmap): void {
    const app = getApp<IAppOption>()
    app.globalData.currentRoadmap = roadmap
    setStorage(STORAGE_KEYS.ROADMAP, roadmap)

    const currentWeek = roadmap.current_week ?? app.globalData.currentWeek ?? 1
    const safeWeek = Math.max(1, Math.min(QUARTER_TOTAL_WEEKS, currentWeek))
    const totalWeeks = roadmap.total_weeks ?? QUARTER_TOTAL_WEEKS

    let phases: PhaseItem[] = roadmap.phases && roadmap.phases.length > 0
      ? roadmap.phases
      : PHASES.map((p) => ({
          phase_index: p.index,
          phase_name: p.name,
          weeks_cover: p.weeksCover,
          key_actions: p.keyActions,
          success_criteria: p.successCriteria,
        }))

    const phase = weekToPhase(safeWeek)
    const phaseInfo = {
      phase_index: phase.index,
      phase_name: phase.name,
      weeks_cover: phase.weeksCover,
    }

    this.setData({
      loading: false,
      overallGoal: roadmap.overall_goal || this.data.overallGoal,
      currentWeek: safeWeek,
      totalWeeks,
      phases,
      phaseInfo,
      weekIndex: safeWeek - 1,
    })
  },

  /**
   * 跳诊断页（失败则 reLaunch 兜底）
   *
   * @returns void
   */
  onGoDiagnosis(): void {
    wx.navigateTo({
      url: '/pages/diagnosis/index',
      fail: () => {
        wx.reLaunch({ url: '/pages/diagnosis/index' })
      },
    })
  },

  /**
   * 跳周计划页：navigateTo → switchTab → navigateTo → reLaunch 多层兜底
   *
   * @returns void
   */
  onGoWeekly(): void {
    const url = '/pages/weekly-plan/index'
    const fallbackUrl = '/pages/plan/index'

    wx.navigateTo({
      url,
      fail: () => {
        wx.switchTab({
          url: fallbackUrl,
          fail: () => {
            wx.navigateTo({
              url: fallbackUrl,
              fail: () => {
                wx.reLaunch({ url: fallbackUrl })
              },
            })
          },
        })
      },
    })
  },

  /**
   * 周选择器变更：更新 currentWeek / phaseInfo 并同步到 App
   *
   * @param e picker change 事件，detail.value 为索引
   * @returns void
   */
  onWeekChange(e: WechatMiniprogram.BaseEvent<{ value: string | number }>): void {
    const index = Number(e.detail?.value ?? 0)
    const newWeek = index + 1
    const phase = weekToPhase(newWeek)
    const phaseInfo = {
      phase_index: phase.index,
      phase_name: phase.name,
      weeks_cover: phase.weeksCover,
    }

    this.setData({
      currentWeek: newWeek,
      weekIndex: index,
      phaseInfo,
    })

    const app = getApp<IAppOption>()
    app.updateWeekInfo(newWeek, weekToPhaseIndex(newWeek))
  },
})
