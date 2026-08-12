/**
 * 闭环业务接口封装（阶段四：功能闭环实现与联通）
 *
 * 对应后端 src/api/loops.py，把「一次性对话输出」升级为可保存 / 可编辑 /
 * 可确认 / 可反馈的完整业务闭环：
 *
 *   计划闭环   confirmPlan / editPlan / regeneratePlan
 *   日程闭环   checkinTodo / syncSchedule / getSchedule
 *   数据闭环   uploadMetrics
 *   复盘闭环   triggerReview / applyReview
 *   持续学习   submitFeedback
 *
 * 所有接口自动附带 JWT（见 request.ts）。
 */

import { get, post, put, uploadFile } from './request'
import type { DayPlan, ReviewReport, SevenDayPlan, Task } from '../types'

// ============================================================
// 通用返回结构
// ============================================================

/** 后端闭环接口统一约定：ok 为 false 时 error 携带原因 */
export interface LoopResult {
  ok: boolean
  error?: string
}

/** 后端 todos 表的一行（与 loops.py::_todo_to_dict 对齐） */
export interface BackendTodo {
  id: string
  business_id: string
  plan_id: string | null
  day_index: number
  date: string
  title: string
  time_slot: string
  status: 'pending' | 'doing' | 'done'
  how_to: string
  checklist: string[] | null
  notes: string | null
  completed_at: string | null
  images: string[]
}

/** 排期扁平项（确认计划 / 应用复盘后返回，用于即时提示） */
export interface ScheduleItem {
  day_index: number
  date: string
  title: string
  time_slot: string
  how_to: string
}

// ============================================================
// 一、计划闭环
// ============================================================

export interface ConfirmPlanResult {
  ok: boolean
  plan_id: string
  schedule: ScheduleItem[]
}

/**
 * 确认计划 → 后端标记 confirmed + 自动排期落库 todos。
 * 这是「计划闭环 → 日程闭环」的衔接点。
 */
export function confirmPlan(planId: string): Promise<ConfirmPlanResult> {
  return post<ConfirmPlanResult>(`/plan/${planId}/confirm`, {})
}

/** 单条微调项（day_index + task_index 定位，未传字段保持原值） */
export interface PlanEdit {
  day_index: number
  task_index: number
  title?: string
  time_slot?: string
  how_to?: string
  checklist?: string[]
}

/** 微调计划中的任务，写回后端 days JSON。 */
export function editPlan(
  planId: string,
  edits: PlanEdit[],
): Promise<LoopResult & { plan?: Record<string, unknown> }> {
  return post(`/plan/${planId}/edit`, { edits: edits as unknown as Record<string, unknown>[] })
}

/** 重新生成计划（结合最新记忆 + 反馈评分）。 */
export function regeneratePlan(planId: string): Promise<LoopResult & { plan?: SevenDayPlan }> {
  return post(`/plan/${planId}/regenerate`, {})
}

// ============================================================
// 二、日程闭环
// ============================================================

/**
 * 任务打卡 / 状态变更 → 落库 todos，供复盘 Agent 读取真实执行情况。
 */
export function checkinTodo(opts: {
  todoId: string
  status?: 'pending' | 'doing' | 'done'
  notes?: string
  images?: string[]
}): Promise<LoopResult & { todo?: BackendTodo }> {
  const body: Record<string, unknown> = { todo_id: opts.todoId }
  if (opts.status !== undefined) body.status = opts.status
  if (opts.notes !== undefined) body.notes = opts.notes
  if (opts.images !== undefined) body.images = opts.images
  return put('/schedule/checkin', body)
}

/**
 * 把对话里产出的排期结果补录落库（快捷指令「安排本周日程」场景）。
 */
export function syncSchedule(opts: {
  businessId?: string
  planId?: string
  days: DayPlan[] | Array<Record<string, unknown>>
}): Promise<LoopResult & { persisted?: number; business_id?: string }> {
  return post('/schedule/sync', {
    business_id: opts.businessId || '',
    plan_id: opts.planId || null,
    days: opts.days as unknown as Record<string, unknown>[],
  })
}

/** 读取已落库排期（跨会话持久，反映真实打卡状态）。 */
export function getSchedule(
  businessId = '',
): Promise<{ ok: boolean; business_id?: string; todos: BackendTodo[] }> {
  return get('/schedule', businessId ? { business_id: businessId } : {})
}

// ============================================================
// 三、数据上传闭环
// ============================================================

export interface KpiRow {
  metric: string
  target: number | null
  actual: number | null
  achievement_rate: number | null
  status?: string
}

export interface KpiResult {
  rows: KpiRow[]
  derived?: Record<string, number | string>
  overall_achievement?: number
  summary?: string
}

export interface MetricsUploadResult {
  ok: boolean
  error?: string
  merged_numbers?: Record<string, number>
  kpi?: KpiResult
  business_id?: string
}

/**
 * 上传业务数据（CSV / 截图）→ 后端安全解析 → 落库 metrics → 返回 KPI。
 * 前端只需把 wx.chooseMedia / chooseMessageFile 的临时路径传进来。
 */
export function uploadMetrics(filePath: string, businessId = ''): Promise<MetricsUploadResult> {
  return uploadFile<MetricsUploadResult>(
    '/metrics/upload',
    filePath,
    'file',
    businessId ? { business_id: businessId } : {},
  )
}

/**
 * 通用文件暂存：小程序本地临时路径 → 服务端可读路径。
 *
 * 必须先走这一步，`streamChat({ files })` 传的路径服务端才打得开；
 * 直接把 wx 的 tempFilePath 丢给后端，Agent 是读不到内容的。
 */
export function stageFile(filePath: string): Promise<{ ok: boolean; file_path: string }> {
  return uploadFile<{ ok: boolean; file_path: string }>('/files/upload', filePath, 'file')
}

/** 批量暂存，返回服务端路径数组（单个失败不影响其余）。 */
export async function stageFiles(filePaths: string[]): Promise<string[]> {
  const out: string[] = []
  for (const p of filePaths) {
    try {
      const r = await stageFile(p)
      if (r && r.file_path) out.push(r.file_path)
    } catch (err) {
      console.warn('[loops] 文件暂存失败，已跳过：', p, err)
    }
  }
  return out
}

// ============================================================
// 四、复盘闭环
// ============================================================

export interface ReviewTriggerResult {
  ok: boolean
  error?: string
  /** 为 true 表示本周还没有上传数据，需要先引导上传 */
  needs_upload?: boolean
  review?: ReviewReport
}

/** 触发复盘（周末定时 / 手动）。无上传数据时返回 needs_upload=true。 */
export function triggerReview(opts: {
  businessId?: string
  weekNumber?: number
} = {}): Promise<ReviewTriggerResult> {
  return post('/review/trigger', {
    business_id: opts.businessId || '',
    week_number: opts.weekNumber ?? null,
  })
}

export interface ReviewApplyResult {
  ok: boolean
  error?: string
  plan?: SevenDayPlan
  schedule?: ScheduleItem[]
}

/** 采纳复盘建议 → 重新生成下周计划并自动排期。 */
export function applyReview(reviewId: string, businessId = ''): Promise<ReviewApplyResult> {
  return post(`/review/${reviewId}/apply`, { business_id: businessId })
}

// ============================================================
// 五、持续学习：反馈采集
// ============================================================

export type FeedbackTarget = 'diagnosis' | 'plan' | 'schedule' | 'review' | 'card' | 'suggestion'

export interface FeedbackResult {
  ok: boolean
  feedback_id?: string
  updated_cards?: number
  error?: string
}

/**
 * 提交反馈（👍 rating=1 / 👎 rating=-1 / 修改计划 rating=-1 + comment）。
 * 后端据此更新 strategy_scores，影响后续 RAG 检索排序 → 「越用越懂你」。
 */
export function submitFeedback(opts: {
  targetType: FeedbackTarget
  targetId?: string
  rating: number
  comment?: string
  businessId?: string
  cardIds?: string[]
}): Promise<FeedbackResult> {
  return post('/agent/feedback', {
    target_type: opts.targetType,
    target_id: opts.targetId || null,
    rating: opts.rating,
    comment: opts.comment || null,
    business_id: opts.businessId || null,
    card_ids: opts.cardIds || [],
  })
}

// ============================================================
// 六、辅助：后端 todo → 前端 Task 视图模型
// ============================================================

/** 把后端 todos 按 day_index 聚合成 DayPlan[]（日历视图用）。 */
export function groupTodosByDay(todos: BackendTodo[]): DayPlan[] {
  const DAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const map = new Map<number, DayPlan>()
  ;(todos || []).forEach((t) => {
    const idx = t.day_index || 1
    if (!map.has(idx)) {
      map.set(idx, {
        day_index: idx,
        day_name: DAY_NAMES[(idx - 1) % 7] || `第${idx}天`,
        date: t.date || '',
        focus: '',
        tasks: [],
      })
    }
    const day = map.get(idx)!
    if (!day.date && t.date) day.date = t.date
    const task: Task = {
      id: t.id,
      time_slot: t.time_slot || '',
      title: t.title,
      how_to: t.how_to || '',
      checklist: t.checklist || [],
      status: t.status,
      done: t.status === 'done',
      notes: t.notes || '',
      images: t.images || [],
      completed_at: t.completed_at,
    }
    day.tasks.push(task)
  })
  return Array.from(map.values()).sort((a, b) => a.day_index - b.day_index)
}
