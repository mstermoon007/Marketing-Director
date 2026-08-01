/**
 * 全局常量定义，包含阶段、任务状态、行业、预算等配置
 *
 * @file    constants.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

export interface Phase {
  index: number
  name: string
  weeksCover: string
  keyActions: string[]
  successCriteria: string
}

export const PHASES: Phase[] = [
  {
    index: 1,
    name: '启动期',
    weeksCover: '1-4',
    keyActions: ['账号基建', '竞品调研', '核心素材库建立', '话术体系建立'],
    successCriteria: '完成3个平台账号搭建，积累20条核心素材',
  },
  {
    index: 2,
    name: '放量期',
    weeksCover: '5-8',
    keyActions: ['规律内容发布', '获取首批有效咨询', '启动转介绍'],
    successCriteria: '每周稳定发布5条内容，获取10+有效咨询',
  },
  {
    index: 3,
    name: '收获+裂变期',
    weeksCover: '9-12',
    keyActions: ['重点追单转化', '设计裂变活动', '复盘成功案例'],
    successCriteria: '转化率提升至20%，完成1次裂变活动',
  },
]

export const TASK_STATUS = {
  PENDING: 'pending' as const,
  DOING: 'doing' as const,
  DONE: 'done' as const,
}

export type TaskStatus = typeof TASK_STATUS[keyof typeof TASK_STATUS]

export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  [TASK_STATUS.PENDING]: '未开始',
  [TASK_STATUS.DOING]: '进行中',
  [TASK_STATUS.DONE]: '已完成',
}

export const REVIEW_TYPES = {
  WEEKLY: 'weekly' as const,
  MONTHLY: 'monthly' as const,
  QUARTERLY: 'quarterly' as const,
}

export type ReviewType = typeof REVIEW_TYPES[keyof typeof REVIEW_TYPES]

export const REVIEW_TYPE_LABEL: Record<ReviewType, string> = {
  [REVIEW_TYPES.WEEKLY]: '周复盘',
  [REVIEW_TYPES.MONTHLY]: '月复盘',
  [REVIEW_TYPES.QUARTERLY]: '季度复盘',
}

export const INDUSTRIES: string[] = [
  '餐饮',
  '零售',
  '教育',
  '美容',
  '服务',
  '制造',
  '医疗',
  '房产',
  '中介',
  '其他',
]

export const TEAM_SIZES: string[] = [
  '1-5人',
  '6-20人',
  '21-50人',
  '51-200人',
  '200人以上',
]

export const PRICE_RANGES: string[] = [
  '0-50元',
  '50-200元',
  '200-1000元',
  '1000-5000元',
  '5000元以上',
]

export const MONTHLY_BUDGETS: string[] = [
  '0-1000元',
  '1000-5000元',
  '5000-10000元',
  '1万-3万元',
  '3万-10万元',
  '10万元以上',
]

export const MARKETING_CHANNELS: string[] = [
  '线下门店',
  '美团外卖',
  '大众点评',
  '小红书',
  '抖音',
  '微信公众号',
  '朋友圈广告',
  '社群运营',
  '线下地推',
  '转介绍',
  '视频号',
  '知乎',
]

export const WEEKDAY_LABELS: string[] = [
  '周日',
  '周一',
  '周二',
  '周三',
  '周四',
  '周五',
  '周六',
]

export const WEEK_SCHEDULE_RULES = {
  1: { type: '准备日', label: '周一', desc: '本周计划梳理、素材准备' },
  2: { type: '执行日', label: '周二', desc: '核心营销动作' },
  3: { type: '执行日', label: '周三', desc: '核心营销动作' },
  4: { type: '执行日', label: '周四', desc: '核心营销动作' },
  5: { type: '执行日', label: '周五', desc: '核心营销动作' },
  6: { type: '汇总日', label: '周六', desc: '数据整理、周复盘填写' },
  0: { type: '休息日', label: '周日', desc: '休息调整' },
} as const

export type WeekScheduleKey = keyof typeof WEEK_SCHEDULE_RULES

export const ISSUE_LEVEL = {
  HIGH: 'high' as const,
  MEDIUM: 'medium' as const,
  LOW: 'low' as const,
}

export type IssueLevel = typeof ISSUE_LEVEL[keyof typeof ISSUE_LEVEL]

export const ISSUE_LEVEL_LABEL: Record<IssueLevel, string> = {
  [ISSUE_LEVEL.HIGH]: '严重',
  [ISSUE_LEVEL.MEDIUM]: '中等',
  [ISSUE_LEVEL.LOW]: '轻微',
}

export const ISSUE_LEVEL_COLOR: Record<IssueLevel, string> = {
  [ISSUE_LEVEL.HIGH]: '#ee0a24',
  [ISSUE_LEVEL.MEDIUM]: '#ff976a',
  [ISSUE_LEVEL.LOW]: '#07c160',
}

export const ISSUE_LEVEL_ICON: Record<IssueLevel, string> = {
  [ISSUE_LEVEL.HIGH]: '🔴',
  [ISSUE_LEVEL.MEDIUM]: '🟡',
  [ISSUE_LEVEL.LOW]: '🟢',
}

export const API_CODE = {
  SUCCESS: 0,
  PARAM_ERROR: 1001,
  NOT_LOGIN: 1002,
  NO_PERMISSION: 1003,
  DIAGNOSIS_PROCESSING: 2001,
  DIAGNOSIS_FAILED: 2002,
  SERVER_ERROR: 5000,
} as const

export type ApiCode = typeof API_CODE[keyof typeof API_CODE]

export const QUARTER_TOTAL_WEEKS = 12
