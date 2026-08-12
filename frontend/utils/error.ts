/**
 * 错误分级与统一处理（阶段三）
 *
 * 把底层 wx.request 的错误、HTTP 状态码、后端业务 code 统一归类为
 * network / auth / business / unknown 四级，供 UI 层做差异化提示与重试。
 */

import { ERROR_LEVEL, ErrorLevel } from './constants'

export interface AppError {
  level: ErrorLevel
  message: string
  /** 是否可重试（网络抖动 / 超时通常可重试） */
  retryable: boolean
  /** 原始错误对象（调试用） */
  raw?: unknown
}

/**
 * 将任意异常归类为 AppError。
 *
 * @param err   捕获到的错误（可能是 Error / 字符串 / wx fail 对象）
 * @param statusCode 可选 HTTP 状态码（401/403 → auth）
 */
export function classifyError(err: unknown, statusCode?: number): AppError {
  // HTTP 鉴权类
  if (statusCode === 401 || statusCode === 403) {
    return { level: ERROR_LEVEL.AUTH, message: '登录已过期，请重新登录', retryable: false, raw: err }
  }

  const msg: string = typeof err === 'string' ? err : (err as Error)?.message || '未知错误'

  // 网络类关键词
  if (
    /timeout|超时/.test(msg) ||
    /fail|abort|network|网络|无法连接|request:fail/.test(msg)
  ) {
    return { level: ERROR_LEVEL.NETWORK, message: '网络连接异常，请检查网络后重试', retryable: true, raw: err }
  }

  // 后端业务错误（message 里常带「失败 / 错误 / 无效」）
  if (/失败|错误|无效|缺失|不正确|unauthorized|forbidden/i.test(msg)) {
    return { level: ERROR_LEVEL.BUSINESS, message: msg, retryable: false, raw: err }
  }

  return { level: ERROR_LEVEL.UNKNOWN, message: msg || '发生未知错误', retryable: false, raw: err }
}

/**
 * Toast 展示错误（按级别用不同图标/文案）。
 */
export function showErrorToast(err: AppError): void {
  const icon: WechatMiniprogram.ShowToastOption['icon'] =
    err.level === ERROR_LEVEL.NETWORK ? 'none' : err.level === ERROR_LEVEL.AUTH ? 'error' : 'none'
  wx.showToast({ title: err.message, icon, duration: 2000 })
}
