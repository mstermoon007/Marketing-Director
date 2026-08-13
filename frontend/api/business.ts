/**
 * 个人中心 / 资源列表接口封装
 *
 * 对应后端 backend/api/profile.py：
 *   GET /api/business/list        当前用户名下企业
 *   GET /api/diagnosis/history    诊断历史
 *   GET /api/plan/history         计划历史
 *   GET /api/review/history       复盘历史
 *
 * 所有接口自动附带 JWT（见 request.ts）。
 */

import { get } from './request'

/** 企业摘要（与后端 _business_to_dict 对齐） */
export interface BusinessSummary {
  id: string
  business_name: string
  industry: string
  city: string
  created_at: string | null
}

/** 历史记录通用结构（各类型字段不同，用 Record 收敛） */
export type HistoryItem = Record<string, unknown>

export interface ListResult<T> {
  list: T[]
  total: number
}

/** 当前用户名下所有企业。 */
export function getMyBusinesses(): Promise<ListResult<BusinessSummary>> {
  return get<ListResult<BusinessSummary>>('/profile/businesses')
}

/** 当前用户所有诊断报告历史。 */
export function getDiagnosisHistory(): Promise<ListResult<HistoryItem>> {
  return get<ListResult<HistoryItem>>('/profile/diagnosis-history')
}

/** 当前用户所有执行计划历史。 */
export function getPlanHistory(): Promise<ListResult<HistoryItem>> {
  return get<ListResult<HistoryItem>>('/profile/plan-history')
}

/** 当前用户所有复盘报告历史。 */
export function getReviewHistory(): Promise<ListResult<HistoryItem>> {
  return get<ListResult<HistoryItem>>('/profile/review-history')
}
