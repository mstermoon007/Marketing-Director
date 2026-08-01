/**
 * 工作台首页 Dashboard，展示阶段进度、今日任务与本周完成率
 *
 * @file    pages/index/index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import type { DashboardData, Task } from '../../types/index'

import { hasBusinessInfo } from '../../utils/auth'
import { WEEKDAY_LABELS } from '../../utils/constants'
import { getStorage, STORAGE_KEYS } from '../../utils/storage'

import { get, post } from '../../api/request'

interface WeekCompletionItem {
  day: string
  completed: number
  total: number
  rate: number
  barHeight: number
  isToday: boolean
  isCompleted: boolean
}

interface IndexPageData {
  loading: boolean
  dashboard: DashboardData | null
  phaseInfo: {
    phase_index: number
    phase_name: string
    weeks_cover: string
  }
  weeklyProgress: number
  todayTasks: Task[]
  weekCompletion: WeekCompletionItem[]
  currentWeek: number
  totalWeeks: number
  weekdayLabels: string[]
}

Page({
  data: {
    loading: false,
    dashboard: null as DashboardData | null,
    phaseInfo: {
      phase_index: 1,
      phase_name: '启动期',
      weeks_cover: '1-4',
    },
    weeklyProgress: 0,
    todayTasks: [] as Task[],
    weekCompletion: [] as WeekCompletionItem[],
    currentWeek: 1,
    totalWeeks: 12,
    weekdayLabels: WEEKDAY_LABELS,
  } as IndexPageData,

  /**
   * 页面加载：拉取 Dashboard 数据
   *
   * @returns void
   */
  onLoad(): void {
    this.loadDashboard()
  },

  /**
   * 页面展示：检查 businessId 状态，无数据则跳转 onboarding
   *
   * @returns void
   */
  onShow(): void {
    const app = getApp<IAppOption>()
    const bid = app.globalData.businessId || getStorage<string>(STORAGE_KEYS.BUSINESS_ID)
    if (bid || hasBusinessInfo()) {
      this.loadDashboard()
    } else {
      wx.redirectTo({ url: '/pages/onboarding/index' })
    }
  },

  /**
   * 拉取 Dashboard 数据并计算渲染辅助字段（isToday / barHeight 等）
   *
   * @description 失败时 toast，无论成功失败都会关闭 loading
   * @returns Promise<void>
   */
  async loadDashboard(): Promise<void> {
    const app = getApp<IAppOption>()
    const businessId = app.globalData.businessId || getStorage<string>(STORAGE_KEYS.BUSINESS_ID)
    if (!businessId) {
      wx.redirectTo({ url: '/pages/onboarding/index' })
      return
    }
    wx.showLoading({ title: '加载中...', mask: true })
    this.setData({ loading: true })
    try {
      const data = await get<DashboardData>('/dashboard', { business_id: businessId })
      const wc = (data.week_completion || []).map((item, idx) => {
        const now = new Date()
        const todayIdx = now.getDay()
        const weekMap = [0, 1, 2, 3, 4, 5, 6]
        const weekdayPos = weekMap[idx] ?? idx
        return {
          ...item,
          barHeight: Math.max(10, item.rate || 0),
          isToday: weekdayPos === todayIdx,
          isCompleted: item.total > 0 && item.completed >= item.total,
        }
      })
      this.setData({
        dashboard: data,
        phaseInfo: data.phase_info || this.data.phaseInfo,
        weeklyProgress: data.weekly_progress || 0,
        currentWeek: data.current_week || 1,
        totalWeeks: data.total_weeks || 12,
        todayTasks: (data.today_tasks || []) as Task[],
        weekCompletion: wc,
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[index] loadDashboard failed:`, msg)
      wx.showToast({
        title: msg || '加载失败',
        icon: 'none',
      })
    } finally {
      this.setData({ loading: false })
      wx.hideLoading()
    }
  },

  /**
   * 任务打卡事件：bind:checkin 或 bindtap 触发
   *
   * @param e 事件，从 detail.task.id 或 dataset.taskId 取 task_id
   * @returns Promise<void>
   * @example
   * ```wxml
   * <task-card bind:checkin="onCheckIn" data-task-id="{{item.id}}" />
   * ```
   */
  async onCheckIn(e: WechatMiniprogram.BaseEvent): Promise<void> {
    const taskId = e.detail?.task?.id ?? e.currentTarget.dataset.taskId
    if (!taskId) return
    try {
      this.setData({ loading: true })
      wx.showLoading({ title: '打卡中...', mask: true })
      await post('/task/checkin', { task_id: taskId })
      wx.hideLoading()
      wx.showToast({ title: '打卡成功', icon: 'success' })
      await this.loadDashboard()
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[index] onCheckIn failed:`, msg)
      wx.hideLoading()
      wx.showToast({
        title: msg || '打卡失败',
        icon: 'none',
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 查看任务详情：跳转 task-detail 或 plan/day
   *
   * @param e 事件，detail.task.id 或 dataset.taskId
   * @returns void
   */
  onTaskDetail(e: WechatMiniprogram.BaseEvent): void {
    const taskId = e.detail?.task?.id ?? e.currentTarget.dataset.taskId
    if (taskId) {
      wx.navigateTo({ url: `/pages/plan/day?task_id=${taskId}` })
    }
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
   * 跳诊断页
   *
   * @returns void
   */
  onGoDiagnosis(): void {
    wx.navigateTo({ url: '/pages/diagnosis/index' })
  },

  /**
   * 跳周计划页
   *
   * @returns void
   */
  onGoWeekly(): void {
    wx.navigateTo({ url: '/pages/plan/index' })
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
   * 跳个人中心 tab（兼容非 tab 环境）
   *
   * @returns void
   */
  onGoProfile(): void {
    wx.switchTab({
      url: '/pages/profile/index',
      fail: () => {
        wx.navigateTo({ url: '/pages/profile/index' })
      },
    })
  },

  /**
   * 下拉刷新：重新加载 Dashboard
   *
   * @returns Promise<void>
   */
  async onPullDownRefresh(): Promise<void> {
    try {
      await this.loadDashboard()
    } finally {
      wx.stopPullDownRefresh()
    }
  },
})
