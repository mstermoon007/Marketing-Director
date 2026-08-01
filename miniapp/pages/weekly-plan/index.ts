/**
 * 周计划页 Weekly Plan，7天任务日历、完成统计与任务打卡入口
 *
 * @file    pages/weekly-plan/index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import type { DayPlan, SevenDayPlan, Task } from '../../types/index'

import { TASK_STATUS } from '../../utils/constants'
import { setStorage, STORAGE_KEYS } from '../../utils/storage'

import { get, post } from '../../api/request'

interface DailyCompletion {
  completed: number
  total: number
  rate: number
}

interface WeeklyPlanPageData {
  loading: boolean
  plan: SevenDayPlan | null
  metrics: string[]
  activeDay: number
  activeDayData: DayPlan | null
  completionRate: number
  doneCount: number
  totalCount: number
  dailyCompletion: DailyCompletion[]
  weekLabel: string
}

Page<WeeklyPlanPageData, {}>({
  data: {
    loading: true,
    plan: null,
    metrics: [],
    activeDay: 0,
    activeDayData: null,
    completionRate: 0,
    doneCount: 0,
    totalCount: 0,
    dailyCompletion: [],
    weekLabel: '',
  },

  /**
   * 页面加载：确保 App ready → 校验 businessId/diagnosisId → 加载周计划
   *
   * @returns Promise<void>
   */
  async onLoad(): Promise<void> {
    const app = getApp<IAppOption>()
    const ready = await app.ensureReady()
    if (!ready) return

    const { businessId, diagnosisId } = app.globalData
    if (!businessId || !diagnosisId) {
      wx.reLaunch({ url: '/pages/onboarding/index' })
      return
    }

    this.loadWeeklyPlan()
  },

  /**
   * 页面展示：如已有 planId 则重新计算完成率统计
   *
   * @returns Promise<void>
   */
  async onShow(): Promise<void> {
    const app = getApp<IAppOption>()
    if (!app.globalData.planId) return

    if (this.data.plan) {
      this.computeStats()
    }
  },

  /**
   * 加载周计划：/plan/weekly → 失败则 POST /execution/{diagnosisId} 生成
   *
   * @returns Promise<void>
   */
  async loadWeeklyPlan(): Promise<void> {
    this.setData({ loading: true })
    const app = getApp<IAppOption>()
    const weekNumber = app.globalData.currentWeek || 3

    try {
      const plan = await get<SevenDayPlan>('/plan/weekly', { week_number: weekNumber })
      this.renderPlan(plan)
    } catch (err) {
      try {
        const diagnosisId = app.globalData.diagnosisId
        if (diagnosisId) {
          const plan = await post<SevenDayPlan>(`/execution/${diagnosisId}`, {})
          this.renderPlan(plan)
        } else {
          throw err
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        console.error(`[weekly-plan] loadWeeklyPlan failed:`, msg)
        wx.showToast({ title: msg || '加载计划失败', icon: 'none' })
        this.setData({ loading: false })
      }
    }
  },

  /**
   * 渲染周计划：写回全局/Storage，计算活跃天与中文周标
   *
   * @param plan 7天计划
   */
  renderPlan(plan: SevenDayPlan): void {
    const app = getApp<IAppOption>()
    app.saveState('planId', plan.id)
    app.globalData.weeklyPlan = plan
    setStorage<SevenDayPlan>(STORAGE_KEYS.WEEKLY_PLAN, plan)

    const metrics = plan.key_metrics ? Object.keys(plan.key_metrics) : []
    const today = new Date()
    const startDate = plan.start_date ? new Date(plan.start_date) : null
    let activeDay = 0
    if (startDate && !isNaN(startDate.getTime())) {
      const diffMs = today.getTime() - startDate.getTime()
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
      activeDay = Math.max(0, Math.min(6, diffDays))
    }

    const activeDayData = plan.days?.[activeDay] ?? plan.days?.[0] ?? null
    const weekLabel = `周${this.numToChinese(plan.week_number || 1)}`

    this.setData({
      plan,
      metrics,
      activeDay,
      activeDayData,
      weekLabel,
      loading: false,
    }, () => {
      this.computeStats()
    })
  },

  /**
   * 数字转中文（1→一，12→十二）
   *
   * @param n 数字
   * @returns 中文字符串
   */
  numToChinese(n: number): string {
    const map = ['日', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']
    return map[n] ?? String(n)
  },

  /**
   * 计算本周整体 & 每日完成率统计
   */
  computeStats(): void {
    const plan = this.data.plan
    if (!plan || !plan.days) return

    let totalCount = 0
    let doneCount = 0
    const dailyCompletion: DailyCompletion[] = []

    plan.days.forEach((day: DayPlan) => {
      let dayTotal = 0
      let dayDone = 0
      if (day.tasks) {
        day.tasks.forEach((task: Task) => {
          dayTotal++
          totalCount++
          const isDone = task.status === TASK_STATUS.DONE || task.done === true
          if (isDone) {
            dayDone++
            doneCount++
          }
        })
      }
      dailyCompletion.push({
        completed: dayDone,
        total: dayTotal,
        rate: dayTotal > 0 ? Math.round((dayDone / dayTotal) * 100) : 0,
      })
    })

    const completionRate = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0

    this.setData({
      completionRate,
      doneCount,
      totalCount,
      dailyCompletion,
    })
  },

  /**
   * 点击某日切换 activeDay
   *
   * @param e detail.dayIndex 或 dataset.index
   * @returns void
   */
  onDayTap(e: WechatMiniprogram.BaseEvent): void {
    const dayIndex = e.detail?.dayIndex ?? e.currentTarget?.dataset?.index
    if (dayIndex === undefined || dayIndex === null) return
    const plan = this.data.plan
    if (plan?.days?.[dayIndex]) {
      this.setData({
        activeDay: dayIndex as number,
        activeDayData: plan.days[dayIndex as number],
      })
    }
  },

  /**
   * 点击任务详情：跳转 task-detail
   *
   * @param e detail.task.id 或 dataset.taskId
   * @returns void
   */
  onTaskDetail(e: WechatMiniprogram.BaseEvent): void {
    const task = e.detail?.task
    const taskId = task?.id ?? e.currentTarget?.dataset?.taskId
    if (taskId) {
      wx.navigateTo({ url: `/pages/task-detail/index?task_id=${taskId}` })
    }
  },

  /**
   * 任务打卡：bind:checkin 触发
   *
   * @param e detail.task.id 或 dataset.taskId
   * @returns Promise<void>
   */
  async onTaskCheckIn(e: WechatMiniprogram.BaseEvent): Promise<void> {
    const task = e.detail?.task
    const taskId = task?.id ?? e.currentTarget?.dataset?.taskId
    if (!taskId) return

    try {
      this.setData({ loading: true })
      await post('/task/checkin', {
        task_id: taskId,
        notes: '',
        images: [],
      })
      wx.showToast({ title: '打卡成功', icon: 'success' })
      this.loadWeeklyPlan()
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error(`[weekly-plan] onTaskCheckIn failed:`, msg)
      wx.showToast({ title: msg || '打卡失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 开始复盘：跳转 review 页
   *
   * @returns void
   */
  onStartReview(): void {
    wx.navigateTo({ url: '/pages/review/index' })
  },

  /**
   * 重试按钮：重新加载周计划
   *
   * @returns void
   */
  onRetry(): void {
    this.loadWeeklyPlan()
  },
})
