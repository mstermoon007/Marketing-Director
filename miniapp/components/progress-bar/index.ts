/**
 * 进度条组件，展示季度周进度与阶段信息
 *
 * @file    index.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

interface ProgressBarProperties {
  currentWeek: number
  totalWeeks: number
  phaseIndex: number
  phaseName: string
}

interface PhaseRange {
  start: number
  end: number
  name: string
}

interface ProgressBarData {
  progressPercent: number
  phaseRanges: PhaseRange[]
}

Component<ProgressBarProperties, ProgressBarData, WechatMiniprogram.IAnyObject>({
  properties: {
    currentWeek: {
      type: Number,
      value: 1,
    },
    totalWeeks: {
      type: Number,
      value: 12,
    },
    phaseIndex: {
      type: Number,
      value: 1,
    },
    phaseName: {
      type: String,
      value: '启动期',
    },
  },

  data: {
    progressPercent: 0,
    phaseRanges: [
      { start: 1, end: 4, name: '启动期' },
      { start: 5, end: 8, name: '放量期' },
      { start: 9, end: 12, name: '收获期' },
    ],
  },

  observers: {
    'currentWeek, totalWeeks': function (currentWeek: number, totalWeeks: number): void {
      const percent: number = totalWeeks > 0 ? Math.min(100, Math.max(0, (currentWeek / totalWeeks) * 100)) : 0
      this.setData({ progressPercent: percent })
    },
  },

  lifetimes: {
    attached(): void {
      const { currentWeek, totalWeeks } = this.properties
      const percent: number = totalWeeks > 0 ? Math.min(100, Math.max(0, (currentWeek / totalWeeks) * 100)) : 0
      this.setData({ progressPercent: percent })
    },
  },
})
