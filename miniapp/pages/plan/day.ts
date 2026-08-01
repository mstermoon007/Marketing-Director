/**
 * 日详情页
 * 优先使用从 plan/index 传递的全局数据，避免重复请求
 */
import { get } from '../../api/request'
import type { DayPlan, SevenDayPlan } from '../../types/index'

interface PageData {
  day: DayPlan | null
}

Page<PageData, {}>({
  data: {
    day: null,
  },

  onLoad(options: { plan_id?: string; day_index?: string }) {
    const app = getApp<IAppOption>()
    const globalData = app.globalData as unknown as Record<string, unknown>

    // 优先使用从 plan/index 传递的数据
    const cachedDay = globalData.currentDayData as DayPlan | undefined
    const cachedIndex = globalData.currentDayIndex as number | undefined

    if (cachedDay && (cachedIndex === undefined || cachedIndex === (options.day_index ? parseInt(options.day_index, 10) : 0))) {
      this.setData({ day: cachedDay })
      // 清除缓存
      delete globalData.currentDayData
      delete globalData.currentDayIndex
    } else {
      // 回退：从 API 加载
      const planId = options.plan_id || app.globalData.planId
      const dayIndex = options.day_index ? parseInt(options.day_index, 10) : 0
      if (planId) {
        this.loadDay(planId, dayIndex)
      }
    }
  },

  async loadDay(planId: string, dayIndex: number) {
    try {
      const plan = await get<SevenDayPlan>(`/execution/${planId}`)
      if (plan.days && plan.days[dayIndex]) {
        this.setData({ day: plan.days[dayIndex] })
      }
    } catch (err) {
      wx.showToast({ title: (err as Error).message || '加载失败', icon: 'none' })
    }
  },
})
