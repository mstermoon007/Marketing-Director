/**
 * 登录鉴权工具，封装微信小程序登录流程与token管理
 *
 * @file    auth.ts
 * @author  AI Marketing Team
 * @version 3.0.0
 * @since   2026-01-01
 */

import { post } from '../api/request'

import { getStorage, removeStorage, setStorage, STORAGE_KEYS, TokenStorage } from './storage'

export interface LoginResult {
  token: string
  user_id: string
  is_new_user: boolean
  /** 生产环境后端基址：登录成功后由后端下发（取代原先的本地加密/硬编码方案） */
  api_base_url?: string
}

export interface UserInfo {
  user_id: string
  nickname?: string
  avatar?: string
}

/**
 * 是否已登录（有token）
 *
 * @returns 是否已登录
 */
export function isLoggedIn(): boolean {
  return TokenStorage.exists()
}

/**
 * 是否已完成企业信息填写
 *
 * @returns 是否存在企业信息
 */
export function hasBusinessInfo(): boolean {
  return !!getStorage<string>(STORAGE_KEYS.BUSINESS_ID) || !!getStorage<object>(STORAGE_KEYS.BUSINESS_INFO)
}

/**
 * 是否已完成诊断（有诊断结果）
 *
 * @returns 是否存在诊断结果
 */
export function hasDiagnosis(): boolean {
  return !!getStorage<string>(STORAGE_KEYS.DIAGNOSIS_ID) || !!getStorage<object>(STORAGE_KEYS.DIAGNOSIS)
}

/**
 * 执行微信登录：wx.login code -> 后端换 token
 * 文档6.3.1接口：POST /api/auth/login
 *
 * @returns 登录结果Promise，包含token、user_id、is_new_user
 * @example
 * ```ts
 * const result = await wxLogin()
 * console.log(result.token)
 * ```
 */
export async function wxLogin(): Promise<LoginResult> {
  return new Promise<LoginResult>((resolve, reject): void => {
    wx.login({
      async success(res: WechatMiniprogram.LoginSuccessCallbackResult): Promise<void> {
        if (!res.code) {
          reject(new Error('微信登录失败：未获取code'))
          return
        }
        try {
          const result = await post<LoginResult>('/auth/login', { code: res.code })
          if (result?.token) {
            TokenStorage.set(result.token)
          }
          if (result?.user_id) {
            setStorage<UserInfo>(STORAGE_KEYS.USER_INFO, { user_id: result.user_id })
          }
          // 生产环境配置下发：登录成功后持久化，取代原先的本地加密/硬编码方案
          if (result?.api_base_url) {
            setStorage<string>(STORAGE_KEYS.API_BASE_URL, result.api_base_url)
          }
          resolve(result)
        } catch (e) {
          reject(e)
        }
      },
      fail(err: WechatMiniprogram.GeneralCallbackResult): void {
        reject(new Error(`wx.login 调用失败: ${err.errMsg ?? '未知错误'}`))
      },
    })
  })
}

/**
 * 确保已登录（如果未登录则执行登录）
 * 失败后跳转onboarding页（默认不跳转，可选参数）
 *
 * @param redirectOnFail 失败时是否跳转onboarding页，默认false
 * @returns 登录结果或null（失败时）
 */
export async function ensureLogin(redirectOnFail = false): Promise<LoginResult | null> {
  if (isLoggedIn()) {
    return {
      token: TokenStorage.get(),
      user_id: getStorage<UserInfo>(STORAGE_KEYS.USER_INFO)?.user_id ?? '',
      is_new_user: false,
    }
  }
  try {
    return await wxLogin()
  } catch {
    if (redirectOnFail) {
      // 用 reLaunch 而非 redirectTo：调用方多为 tabBar 页面，
      // redirectTo 会让页面栈失去 tabBar 上下文，reLaunch 语义更正确
      wx.reLaunch({ url: '/pages/onboarding/index' })
    }
    return null
  }
}

/**
 * 登出：清除登录态 + 跳转引导页
 *
 * @param redirect 是否跳转引导页，默认true
 */
export function logout(redirect = true): void {
  TokenStorage.clear()
  removeStorage(STORAGE_KEYS.USER_INFO)
  if (redirect) {
    wx.reLaunch({ url: '/pages/onboarding/index' })
  }
}

/**
 * 处理 Token 过期（HTTP 401 / code=1002）
 * 请求封装中自动调用
 */
export function handleTokenExpired(): void {
  TokenStorage.clear()
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]
  if (current && !current.route.includes('onboarding')) {
    wx.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
    setTimeout((): void => {
      wx.reLaunch({ url: '/pages/onboarding/index' })
    }, 800)
  }
}
