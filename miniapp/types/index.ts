/**
 * 全局类型定义 V3.0
 *
 * 与开发文档7.4节 数据模型定义 严格对齐
 *  - Business：company_name / main_product / monthly_budget 等
 *  - Diagnosis：dimension_scores / overall_comment / top_issues / quarterly_roadmap 等
 *  - SevenDayPlan：week_number / phase_name / focus 等
 *  - Task：三态 status (pending/doing/done)
 *
 * 同时导出 LEGACY_* 类型别名，避免旧代码立即报错。
 * 页面迁移完成后可移除 LEGACY 别名。
 */

import type { TaskStatus, IssueLevel } from '../utils/constants'

// ============================================================
// ===== 1. 企业信息 BusinessProfile （文档7.4.1节） ===========
// ============================================================
export interface BusinessProfile {
  // ===== 标识 =====
  id: string
  business_id?: string // 兼容旧命名

  // ===== 企业基本信息（步骤1） =====
  /** 企业名称（文档字段：company_name） */
  company_name: string
  /** 所属行业 */
  industry: string
  /** 所在城市 */
  city: string
  /** 团队规模 */
  team_size: string

  // ===== 产品与目标客户（步骤2） =====
  /** 主营产品（文档字段：main_product） */
  main_product: string
  /** 客单价范围 */
  price_range: string
  /** 目标客户画像描述（文档字段：target_customer，单数描述性文本） */
  target_customer: string

  // ===== 当前营销现状（步骤3） =====
  /** 现有营销渠道 - 多选 string[]（文档规范） */
  current_channels: string[]
  /** 月营销预算（文档字段：monthly_budget，非revenue） */
  monthly_budget: string
  /** 最大痛点描述 */
  biggest_pain: string
  /** 竞品信息（原字段保留） */
  competitors?: string
  /** 月营收（原字段保留，作为补充） */
  monthly_revenue?: string

  // ===== 周期/阶段信息 =====
  created_at: string
  /** 当前处于第几阶段 1|2|3（文档8.4节） */
  current_phase: number
  /** 当前处于第几周 1~12 */
  current_week: number

  // ===== 诊断/执行相关 ID（冗余方便前端直接取） =====
  diagnosis_id?: string
  roadmap_id?: string
  plan_id?: string
  review_id?: string
}

// ===== 旧别名（向后兼容，页面迁移后删除） =====
/** @deprecated 使用 BusinessProfile，字段映射见文档 */
export interface LegacyBusinessProfile {
  id: string
  /** @deprecated → company_name */
  business_name: string
  industry: string
  city: string
  /** @deprecated → main_product */
  product_desc: string
  price_range: string
  /** @deprecated → target_customer */
  target_customers: string
  competitors: string
  /** @deprecated 请用 current_channels: string[] */
  current_channels: string
  /** @deprecated → monthly_budget */
  monthly_revenue: string
  team_size: string
  biggest_pain: string
  created_at: string
}

// ============================================================
// ===== 2. 诊断报告 DiagnosisReport （文档6.3.3节） =========
// ============================================================

/** Top问题项（文档6.3.3 top_issues） */
export interface DiagnosisIssue {
  /** 严重级别 high/medium/low（文档枚举） */
  level: IssueLevel
  /** 问题标题 */
  title: string
  /** 一句话建议 */
  suggestion: string
  /** 所属维度（可选：positioning/product/channel/content/conversion） */
  category?: string
  /** 详细描述（可选扩展） */
  description?: string
  /** 快速修复措施（从Problem.quick_fix迁移） */
  quick_fix?: string
}

/** 季度路线图内嵌对象（在诊断报告中） */
export interface PhaseItem {
  phase_index: number
  phase_name: string
  weeks_cover: string
  key_actions: string[]
  success_criteria: string
  completed?: boolean
}

export interface QuarterRoadmap {
  id?: string
  business_id?: string
  diagnosis_id?: string
  overall_goal: string
  start_date?: string
  total_weeks?: number
  current_week?: number
  phases: PhaseItem[]
  created_at?: string
}

export interface DiagnosisReport {
  id: string
  business_id: string

  // ===== 评分 =====
  /** 综合健康度总分 0~100 */
  overall_score: number
  /** 总体评价文字（文档：overall_comment） */
  overall_comment: string
  /** 五维得分（文档：dimension_scores，键名：positioning/product/channel/content/conversion） */
  dimension_scores: Record<string, number>

  // ===== 核心问题 =====
  /** Top 3 核心问题（文档6.3.3节，level: high/medium/low） */
  top_issues: DiagnosisIssue[]

  // ===== 战略与焦点 =====
  /** 季度战略摘要（原字段保留） */
  strategy_summary?: string
  /** 本周聚焦（原字段保留） */
  this_week_focus?: string

  // ===== 内嵌路线图 =====
  /** 季度路线图（文档6.3.3节：quarterly_roadmap） */
  quarterly_roadmap: QuarterRoadmap

  created_at: string

  // ===== 兼容冗余字段 =====
  /** @deprecated 已由 dimension_scores 替代，仍保留用于旧页过渡 */
  score_breakdown?: Record<string, number>
  /** @deprecated 已由 overall_comment 替代 */
  score_summary?: string
  /** @deprecated 已由 top_issues 替代 */
  top3_problems?: Array<{
    /** @deprecated 改为 level: high/medium/low */
    severity: 'critical' | 'major' | 'minor'
    category: string
    description: string
    quick_fix: string
  }>
}

// ============================================================
// ===== 3. 7天计划 SevenDayPlan （文档6.3.4节） =============
// ============================================================

export interface Task {
  /** 唯一ID */
  id: string
  /** 时间段 "09:00-09:30" */
  time_slot: string
  /** 任务标题 */
  title: string
  /** 怎么做 - 自由文本描述 */
  how_to: string
  /** 执行步骤清单（有序数组） */
  checklist: string[]
  /** 完成标准 */
  done_criteria?: string
  /** 预计耗时（分钟） */
  estimated_minutes?: number
  /** 任务状态三态：pending/doing/done */
  status?: TaskStatus
  /** 兼容旧：完成标记（无状态时回退） */
  done?: boolean

  /** 完成时间 ISO */
  completed_at?: string | null
  /** 打卡备注 */
  notes?: string
  /** 上传的图片URL数组 */
  images?: string[]
}

export interface DayPlan {
  /** 周内序号 1~7（文档：day_index） */
  day_index: number
  /** 中文名 周一/周二...（文档：day_name） */
  day_name: string
  /** 日期 YYYY-MM-DD（文档：date） */
  date: string
  /** 当日焦点（文档：focus） */
  focus: string
  /** 当日任务数组 */
  tasks: Task[]

  // ===== 兼容冗余 =====
  /** @deprecated → day_name */
  day_label?: string
}

export interface SevenDayPlan {
  id: string
  business_id: string
  diagnosis_id: string

  /** 本周第几周 1~12（文档6.3.4：week_number） */
  week_number: number
  /** 所属阶段名（文档：phase_name） */
  phase_name: string
  /** 本周核心主题（文档：focus / theme） */
  focus: string
  theme?: string

  /** 本周目标列表 */
  goals?: string[]
  /** 关键指标目标值（键→目标值） */
  key_metrics?: Record<string, number>

  /** 计划开始日期 YYYY-MM-DD */
  start_date: string

  /** 7天计划数据 */
  days: DayPlan[]

  created_at: string

  // ===== 计算属性辅助 =====
  /** 完成率 0~100 （前端本地计算） */
  completion_rate?: number
}

// ============================================================
// ===== 4. 任务详情 TaskDetail （文档4.7节） ==================
// ============================================================
export interface TaskDetail extends Task {
  /** 执行记录列表 */
  execution_logs?: Array<{
    id: string
    type: 'image' | 'text'
    content: string
    created_at: string
  }>
}

// ============================================================
// ===== 5. 复盘报告 ReviewReport （文档6.3.6节） =============
// ============================================================

export interface MetricComparison {
  metric_name: string
  target: number
  actual: number
  achieved: boolean
}

export interface ReviewReport {
  id: string
  plan_id: string
  business_id: string

  /** 复盘类型 weekly/monthly/quarterly */
  review_type?: string
  /** 第几周（week_type时） */
  week_number?: number

  /** 总评 */
  summary: string
  /** 关键数值 */
  numbers: Record<string, number>
  /** 指标对比 */
  vs_target: MetricComparison[]
  /** 做得好的地方 */
  what_worked: string[]
  /** 做得不好的地方 */
  what_didnt: string[]
  /** AI建议 */
  suggestions: string[]

  created_at: string

  /** AI分析状态 processing/done/failed（文档状态字段） */
  ai_analysis_status?: 'processing' | 'done' | 'failed'
}

/** 复盘提交表单（文档4.8节6个问题） */
export interface ReviewSubmitForm {
  review_type: 'weekly' | 'monthly' | 'quarterly'
  week_number?: number
  /** Q1: 本周完成了哪些任务？ */
  completed_tasks: string
  /** Q2: 哪些任务没完成？为什么？ */
  incomplete_tasks: string
  /** Q3: 本周最大的收获是什么？ */
  key_takeaway: string
  /** Q4: 遇到了什么困难？ */
  difficulties: string
  /** Q5: 数据截图URL数组 */
  images: string[]
}

// ============================================================
// ===== 6. 工作台 Dashboard （文档6.3.7节） ==================
// ============================================================
export interface DashboardData {
  /** 当前周数 */
  current_week: number
  /** 总周数，默认12 */
  total_weeks: number
  /** 当前阶段信息 */
  phase_info: {
    phase_index: number
    phase_name: string
    weeks_cover: string
  }
  /** 季度进度百分比 0~100 */
  weekly_progress: number
  /** 今日聚焦任务列表（精简版） */
  today_tasks: Array<{
    id: string
    title: string
    time_slot: string
    status: TaskStatus
  }>
  /** 本周每天完成率（周一~周日） */
  week_completion: Array<{
    day: string
    completed: number
    total: number
    rate: number
  }>
}

// ============================================================
// ===== 7. 全局状态 GlobalState （文档7.1节） =================
// ============================================================
export interface GlobalState {
  // ===== ID级状态 =====
  businessId: string
  diagnosisId: string
  planId: string
  reviewId: string

  // ===== 配置 =====
  apiBase: string

  // ===== 对象级状态（文档7.1节globalData新增） =====
  authToken: string | null
  userInfo: { user_id: string; nickname?: string; avatar?: string } | null
  businessInfo: BusinessProfile | null
  currentPhase: number | null
  currentWeek: number | null
  diagnosisResult: DiagnosisReport | null
  currentRoadmap: QuarterRoadmap | null
  weeklyPlan: SevenDayPlan | null
  latestReview: ReviewReport | null
}

// ============================================================
// ===== 8. 登录接口 （文档6.3.1节） ==========================
// ============================================================
export interface LoginResult {
  token: string
  user_id: string
  is_new_user: boolean
}

// ============================================================
// ===== 9. 兼容旧类型别名（旧页面不立即报错） ==================
// ============================================================
/** @deprecated 使用 DiagnosisIssue */
export type Problem = DiagnosisReport['top3_problems'] extends (infer U)[] ? U : never

/** @deprecated 使用 SevenDayPlan */
export type LegacySevenDayPlan = SevenDayPlan

/** @deprecated 使用 QuarterRoadmap */
export type Roadmap = QuarterRoadmap
