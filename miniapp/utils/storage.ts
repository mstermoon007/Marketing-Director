/**
 * 本地缓存管理工具，支持TTL自动过期与统一Key管理
 *
 * @file    storage.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER_INFO: 'user_info',
  BUSINESS_INFO: 'business_info',
  DIAGNOSIS: 'diagnosis_result',
  ROADMAP: 'current_roadmap',
  WEEKLY_PLAN: 'weekly_plan_cache',
  LAST_CHECKIN_TIME: 'last_checkin_time',
  BUSINESS_ID: 'businessId',
  DIAGNOSIS_ID: 'diagnosisId',
  PLAN_ID: 'planId',
  REVIEW_ID: 'reviewId',
} as const

export type StorageKey = typeof STORAGE_KEYS[keyof typeof STORAGE_KEYS]

const TTL: Partial<Record<StorageKey, number>> = {
  [STORAGE_KEYS.BUSINESS_INFO]: 86400000,
  [STORAGE_KEYS.DIAGNOSIS]: 604800000,
  [STORAGE_KEYS.ROADMAP]: 604800000,
  [STORAGE_KEYS.WEEKLY_PLAN]: 86400000,
  [STORAGE_KEYS.AUTH_TOKEN]: 7 * 86400000,
}

interface StoragePayload<T> {
  data: T
  timestamp: number
}

/**
 * 写入缓存（自动记录时间戳）
 *
 * @param key 缓存键名
 * @param data 缓存数据
 */
export function setStorage<T>(key: StorageKey, data: T): void {
  const payload: StoragePayload<T> = {
    data,
    timestamp: Date.now(),
  }
  try {
    wx.setStorageSync(key, payload)
  } catch (e) {
    console.error(`[storage] set ${key} failed:`, e)
  }
}

/**
 * 读取缓存（自动校验TTL，过期返回null并清除）
 *
 * @param key 缓存键名
 * @returns 缓存数据或null
 */
export function getStorage<T>(key: StorageKey): T | null {
  try {
    const payload = wx.getStorageSync(key) as StoragePayload<T> | ''
    if (!payload) return null

    if (typeof payload === 'object' && 'timestamp' in payload && 'data' in payload) {
      const ttl = TTL[key]
      if (ttl && Date.now() - payload.timestamp > ttl) {
        wx.removeStorageSync(key)
        return null
      }
      return payload.data as T
    }

    return payload as unknown as T
  } catch (e) {
    console.error(`[storage] get ${key} failed:`, e)
    return null
  }
}

/**
 * 删除指定缓存
 *
 * @param key 缓存键名
 */
export function removeStorage(key: StorageKey): void {
  try {
    wx.removeStorageSync(key)
  } catch (e) {
    console.error(`[storage] remove ${key} failed:`, e)
  }
}

/**
 * 清除全部业务缓存（保留登录token可选）
 *
 * @param keepAuth 是否保留登录token，默认true
 */
export function clearAllStorage(keepAuth = true): void {
  const allKeys = Object.values(STORAGE_KEYS)
  allKeys.forEach((key: StorageKey): void => {
    if (keepAuth && key === STORAGE_KEYS.AUTH_TOKEN) return
    try {
      wx.removeStorageSync(key)
    } catch {
      /* ignore */
    }
  })
}

export const TokenStorage = {
  /**
   * 获取token字符串
   *
   * @returns token值，不存在返回空字符串
   */
  get(): string {
    return getStorage<string>(STORAGE_KEYS.AUTH_TOKEN) ?? ''
  },

  /**
   * 设置token
   *
   * @param token 登录token
   */
  set(token: string): void {
    setStorage(STORAGE_KEYS.AUTH_TOKEN, token)
  },

  /**
   * 清除token
   */
  clear(): void {
    removeStorage(STORAGE_KEYS.AUTH_TOKEN)
  },

  /**
   * 判断token是否存在
   *
   * @returns 是否存在token
   */
  exists(): boolean {
    return !!TokenStorage.get()
  },
}
