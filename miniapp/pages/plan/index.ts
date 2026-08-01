/**
 * 7天任务卡片页（周视图）
 */
import { get, post } from '../../api/request'
import type { SevenDayPlan, DayPlan, Task } from '../../types/index'

interface PageData {
  loading: boolean
  plan: SevenDayPlan | null
  metrics: string[]
  activeDay: number
  activeDayData: DayPlan | null
}

Page<PageData, {}>({
  data: {
    loading: true,
    plan: null,
    metrics: [],
    activeDay: 0,
    activeDayData: null,
  },

  onLoad(options: { diagnosis_id?: string }) {
    const diagnosisId = options.diagnosis_id || getApp<IAppOption>().globalData.diagnosisId

    if (diagnosisId) {
      this.loadOrCreatePlan(diagnosisId)
    } else {
      this.setData({ loading: false })
    }
  },

  onShow() {
    const plan = this.data.plan!
    if (plan) {
      this.restoreTaskState()
    }
  },

  async loadOrCreatePlan(diagnosisId: string) {
    this.setData({ loading: true })

    try {
      const plan = await post<SevenDayPlan>(`/execution/${diagnosisId}`, { start_date: '' })
      this.renderPlan(plan)
    } catch (err) {
      try {
        const plan = await get<SevenDayPlan>(`/execution/${diagnosisId}`)
        this.renderPlan(plan)
      } catch {
        wx.showToast({ title: (err as Error).message || '生成失败', icon: 'none' })
        this.setData({ loading: false })
      }
    }
  },

  renderPlan(plan: SevenDayPlan) {
    const app = getApp<IAppOption>()
    app.saveState('planId', plan.id)

    const metrics = plan.key_metrics ? Object.keys(plan.key_metrics) : []
    const activeDayData = plan.days.length > 0 ? plan.days[0] : null

    this.setData({
      plan,
      metrics,
      activeDay: 0,
      activeDayData,
      loading: false,
    })

    this.restoreTaskState()
  },

  restoreTaskState() {
    const plan = this.data.plan!
    if (!plan) return

    const key = `plan_${plan.id}_tasks`
    const saved = wx.getStorageSync(key)
    if (saved) {
      const updatedPlan = { ...plan }
      const states = JSON.parse(saved) as Record<string, boolean>

      updatedPlan.days.forEach((day: DayPlan, di: number) => {
        day.tasks.forEach((task: Task, ti: number) => {
          const taskKey = `${di}_${ti}`
          task.done = states[taskKey] || false
        })
      })

      this.setData({
        plan: updatedPlan,
        activeDayData: updatedPlan.days[this.data.activeDay!] || null,
      })
    }
  },

  saveTaskState() {
    const plan = this.data.plan!
    if (!plan) return

    const states: Record<string, boolean> = {}
    plan.days.forEach((day: DayPlan, di: number) => {
      day.tasks.forEach((task: Task, ti: number) => {
        states[`${di}_${ti}`] = task.done || false
      })
    })

    const key = `plan_${plan.id}_tasks`
    wx.setStorageSync(key, JSON.stringify(states))
  },

  onDayTap(e: WechatMiniprogram.TouchEvent) {
    const idx = e.currentTarget.dataset.index as number
    const plan = this.data.plan!
    if (plan && plan.days[idx]) {
      this.setData({ activeDay: idx, activeDayData: plan.days[idx] })
    }
  },

  onTaskToggle(e: WechatMiniprogram.TouchEvent) {
    const plan = this.data.plan!
    if (!plan) return

    const taskIndex = e.currentTarget.dataset.index as number
    const dayIdx = this.data.activeDay!

    const updatedPlan = { ...plan }
    if (updatedPlan.days[dayIdx] && updatedPlan.days[dayIdx]!.tasks[taskIndex]) {
      const task = updatedPlan.days[dayIdx]!.tasks[taskIndex]!
      task.done = !task.done
      this.setData({ plan: updatedPlan, activeDayData: updatedPlan.days[dayIdx] || null })
      this.saveTaskState()
    }
  },

  onGoDayDetail() {
    const plan = this.data.plan!
    const dayData = this.data.activeDayData!
    if (!plan || !dayData) return

    const dayIndex = this.data.activeDay!

    const app = getApp<IAppOption>()
    ;(app.globalData as unknown as Record<string, unknown>).currentDayData = dayData
    ;(app.globalData as unknown as Record<string, unknown>).currentDayIndex = dayIndex

    wx.navigateTo({ url: `/pages/plan/day?plan_id=${plan.id}&day_index=${dayIndex}` })
  },

  onStartReview() {
    const plan = this.data.plan!
    if (!plan) return
    wx.navigateTo({ url: `/pages/upload/index?plan_id=${plan.id}` })
  },

  onGenerate() {
    const diagnosisId = getApp<IAppOption>().globalData.diagnosisId
    if (diagnosisId) {
      this.loadOrCreatePlan(diagnosisId)
    }
  },
})
