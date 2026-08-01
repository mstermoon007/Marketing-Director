/**
 * 周历组件，展示一周7天日期与每日任务完成率
 *
 * @file    index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import { formatDate, getWeekdayLabel, isToday } from '../../utils/date'

interface DayItem {
  date: Date
  weekday: string
  dateStr: string
  dateNum: number
  isToday: boolean
  isActive: boolean
  rate: number
  hasRate: boolean
}

interface DailyCompletion {
  completed: number
  total: number
  rate: number
}

interface WeekCalendarProperties {
  startDate: string
  activeDayIndex: number
  dailyCompletion: DailyCompletion[]
}

interface WeekCalendarData {
  days: DayItem[]
}

const WEEK_LENGTH = 7
const MIN_DAY_INDEX = 0
const MAX_DAY_INDEX = 6

/**
 * 获取本周周一的Date对象
 *
 * @returns 本周周一0点的Date
 */
function getThisMonday(): Date {
  const now = new Date()
  const day = now.getDay()
  const diffToMonday = day === 0 ? -6 : 1 - day
  const base = new Date(now)
  base.setDate(now.getDate() + diffToMonday)
  base.setHours(0, 0, 0, 0)
  return base
}

/**
 * 解析基准日期
 *
 * @param startDate 起始日期字符串（可空）
 * @returns 基准Date对象
 */
function resolveBaseDate(startDate: string): Date {
  if (startDate) {
    const parsed = new Date(startDate)
    if (!isNaN(parsed.getTime())) {
      parsed.setHours(0, 0, 0, 0)
      return parsed
    }
  }
  return getThisMonday()
}

interface DayComputeParams {
  startDate: string
  activeDayIndex: number
  dailyCompletion: DailyCompletion[]
}

/**
 * 计算一周7天的显示数据
 *
 * @param params 计算参数
 * @returns 日数据数组
 */
function computeDays(params: DayComputeParams): DayItem[] {
  const { startDate, activeDayIndex, dailyCompletion } = params
  const base = resolveBaseDate(startDate)

  const safeActiveIndex = Math.max(MIN_DAY_INDEX, Math.min(MAX_DAY_INDEX, activeDayIndex ?? MIN_DAY_INDEX))
  const completion: DailyCompletion[] = dailyCompletion?.length === WEEK_LENGTH ? dailyCompletion : []

  const days: DayItem[] = []
  for (let i = 0; i < WEEK_LENGTH; i++) {
    const d = new Date(base)
    d.setDate(base.getDate() + i)
    const dateStr = formatDate(d)
    const rateData: DailyCompletion | null = completion[i] ?? null
    const rate = rateData ? rateData.rate : 0

    days.push({
      date: d,
      weekday: getWeekdayLabel(d),
      dateStr,
      dateNum: d.getDate(),
      isToday: isToday(dateStr),
      isActive: i === safeActiveIndex,
      rate,
      hasRate: !!rateData,
    })
  }

  return days
}

Component<WeekCalendarProperties, WeekCalendarData, {
  computeDays: (startDate: string, activeDayIndex: number, dailyCompletion: DailyCompletion[]) => void
}>({
  properties: {
    startDate: {
      type: String,
      value: '',
    },
    activeDayIndex: {
      type: Number,
      value: 0,
    },
    dailyCompletion: {
      type: Array,
      value: [],
    },
  },

  data: {
    days: [] as DayItem[],
  },

  observers: {
    'startDate, activeDayIndex, dailyCompletion': function (
      startDate: string,
      activeDayIndex: number,
      dailyCompletion: DailyCompletion[]
    ): void {
      this.computeDays(startDate, activeDayIndex, dailyCompletion)
    },
  },

  lifetimes: {
    attached: function (): void {
      this.computeDays(
        this.properties.startDate,
        this.properties.activeDayIndex,
        this.properties.dailyCompletion
      )
    },
  },

  methods: {
    /**
     * 计算并更新一周日期数据
     *
     * @param startDate 起始日期
     * @param activeDayIndex 选中日期索引
     * @param dailyCompletion 每日完成率
     */
    computeDays(
      startDate: string,
      activeDayIndex: number,
      dailyCompletion: DailyCompletion[]
    ): void {
      this.setData({
        days: computeDays({ startDate, activeDayIndex, dailyCompletion }),
      })
    },

    /**
     * 点击某天触发change事件
     *
     * @param e 事件对象，含dayIndex dataset
     */
    onTapDay(e: WechatMiniprogram.BaseEvent<{ dayIndex: number }>): void {
      const dayIndex = Number(e.currentTarget.dataset.dayIndex)
      const day = this.data.days[dayIndex]
      if (!day) return
      this.triggerEvent('change', {
        dayIndex,
        date: day.dateStr,
      })
    },
  },
})
