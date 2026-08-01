/**
 * 统一API请求封装 V3.0
 *
 * 文档6.1节规范实现：
 *  - 统一响应格式：{ code: 0, data: {...}, message: "ok" }
 *  - Token自动注入（Authorization: Bearer xxx）
 *  - code=1002（未登录/Token过期）自动清态跳转onboarding
 *  - 环境配置（dev/prod）baseUrl 切换
 *  - PUT/DELETE 完整HTTP方法
 *
 * 向后兼容：保持 get/post/upload 函数签名不变，不破坏现有调用方
 */

import { TokenStorage } from '../utils/storage'
import { handleTokenExpired } from '../utils/auth'
import { API_CODE } from '../utils/constants'

// ========== 环境配置（文档2.3节） ==========
const BASE_URL: Record<'dev' | 'prod', string> = {
  dev: 'http://localhost:8000/api',
  prod: 'https://api.example.com/api',
}

type Env = keyof typeof BASE_URL

/**
 * 获取当前环境（通过小程序全局 __wxConfig.envVersion 判断，或从globalData显式覆盖）
 *   develop / trial -> dev
 *   release -> prod
 */
const detectEnv = (): Env => {
  try {
    const app = getApp<IAppOption>()
    // 1. 显式 apiBase（历史兼容，优先保留）
    if (app?.globalData?.apiBase && !app.globalData.apiBase.includes('example.com')) {
      return 'dev'
    }
    // 2. 微信官方版本判断
    const envVer = (wx as any)?.getAccountInfoSync?.()?.miniProgram?.envVersion
    if (envVer === 'release') return 'prod'
    return 'dev'
  } catch {
    return 'dev'
  }
}

/**
 * 实际 baseUrl：优先使用 globalData.apiBase（兼容现有逻辑），否则按环境自动切换
 */
const getBase = (): string => {
  try {
    const app = getApp<IAppOption>()
    if (app?.globalData?.apiBase) return app.globalData.apiBase
  } catch {
    /* ignore */
  }
  return BASE_URL[detectEnv()]
}

// ========== 统一响应格式 ==========
interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

// ========== 通用请求选项 ==========
interface RequestOptions {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
  timeout?: number
  /** 是否跳过 token 注入（如登录接口） */
  skipAuth?: boolean
  /** 是否跳过 code===0 判断（兼容旧接口不规范返回） */
  skipCodeCheck?: boolean
  header?: Record<string, string>
}

/**
 * 核心请求函数：统一拦截逻辑
 */
function _requestCore<T>(opts: RequestOptions): Promise<T> {
  return new Promise((resolve, reject) => {
    const header: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(opts.header || {}),
    }

    // 1. 自动注入 Token
    if (!opts.skipAuth) {
      const token = TokenStorage.get()
      if (token) {
        header['Authorization'] = `Bearer ${token}`
      }
    }

    wx.request({
      url: getBase() + opts.url,
      method: opts.method,
      data: opts.data,
      header,
      timeout: opts.timeout || 30000,

      success(res) {
        // ===== HTTP 层成功 =====
        const statusCode = res.statusCode

        // 401 / 403 → 当 token 过期处理
        if (statusCode === 401 || statusCode === 403) {
          handleTokenExpired()
          reject(new Error('登录已过期'))
          return
        }

        const r = (res.data || {}) as ApiResponse<T>

        // 跳过 code 检查（兼容老接口）
        if (opts.skipCodeCheck) {
          resolve(r as unknown as T)
          return
        }

        // 正常响应 code===0 → 成功
        if (typeof r.code === 'number') {
          if (r.code === API_CODE.SUCCESS) {
            resolve(r.data)
          } else if (r.code === API_CODE.NOT_LOGIN) {
            // 1002 未登录 → 清态跳转
            handleTokenExpired()
            reject(new Error(r.message || '请先登录'))
          } else {
            reject(new Error(r.message || `请求失败 (code=${r.code})`))
          }
        } else {
          // 后端未按规范返回 code 字段：兜底兼容（向后兼容）
          resolve(r as unknown as T)
        }
      },

      fail(err) {
        // ===== 网络层失败 =====
        const msg = err?.errMsg || '网络请求失败'
        if (msg.includes('timeout')) {
          reject(new Error('请求超时，请重试'))
        } else if (msg.includes('fail') || msg.includes('abort')) {
          reject(new Error('网络连接异常，请检查网络'))
        } else {
          reject(new Error(msg))
        }
      },
    })
  })
}

// ========== 对外方法：保持签名与老版本 100% 兼容 ==========

/** GET */
export function get<T>(path: string, data?: Record<string, any>, opts?: Partial<RequestOptions>): Promise<T> {
  return _requestCore<T>({
    url: path,
    method: 'GET',
    data,
    ...opts,
  })
}

/** POST JSON */
export function post<T>(path: string, body: Record<string, unknown> = {}, opts?: Partial<RequestOptions>): Promise<T> {
  return _requestCore<T>({
    url: path,
    method: 'POST',
    data: body,
    ...opts,
  })
}

/** PUT JSON */
export function put<T>(path: string, body: Record<string, unknown> = {}, opts?: Partial<RequestOptions>): Promise<T> {
  return _requestCore<T>({
    url: path,
    method: 'PUT',
    data: body,
    ...opts,
  })
}

/** DELETE */
export function del<T>(path: string, data?: Record<string, any>, opts?: Partial<RequestOptions>): Promise<T> {
  return _requestCore<T>({
    url: path,
    method: 'DELETE',
    data,
    ...opts,
  })
}

/**
 * 上传文件（逐文件 + 生成两阶段模式）
 *
 * 适配后端两阶段接口：
 *   1) POST /review/{plan_id}/upload  — 逐个暂存
 *   2) POST /review/{plan_id}/generate — 汇总生成复盘报告
 *
 * 兼容旧接口：若后端不支持两阶段，失败后回退到单次 POST /review/plan_xxx。
 * 此部分保留原实现，仅注入Authorization header。
 */
export function upload<T>(path: string, files: string[]): Promise<T> {
  return new Promise((resolve, reject) => {
    if (files.length === 0) {
      reject(new Error('请选择文件'))
      return
    }

    // 构造通用 header（含 token）
    const token = TokenStorage.get()
    const authHeader: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}

    let completed = 0
    let failed = false
    let legacyFallbackTried = false

    // 逐个文件 stage 上传
    files.forEach((filePath) => {
      wx.uploadFile({
        url: getBase() + path + '/upload',
        filePath,
        name: 'file',
        header: authHeader,
        success(res) {
          try {
            const r = JSON.parse(res.data) as ApiResponse<{ file_path: string; staged_count: number }>
            if (r.code !== 0 && r.code !== undefined) {
              failed = true
              reject(new Error(r.message || '上传失败'))
              return
            }
            completed++
            if (completed === files.length && !failed) {
              // 全部上传完 → 调用 generate
              wx.request<T>({
                url: getBase() + path + '/generate',
                method: 'POST',
                header: {
                  'Content-Type': 'application/json',
                  ...authHeader,
                },
                success(genRes) {
                  const gr = (genRes.data as unknown) as ApiResponse<T>
                  if (typeof gr.code === 'number' && gr.code !== 0) {
                    reject(new Error(gr.message || '生成复盘报告失败'))
                  } else {
                    resolve((gr.data ?? gr) as T)
                  }
                },
                fail(genErr) {
                  reject(new Error(genErr.errMsg || '生成复盘报告失败'))
                },
              })
            }
          } catch (e) {
            failed = true
            reject(new Error('解析上传响应失败'))
          }
        },
        fail(err) {
          // 旧接口兼容：/upload 路径失败 → 回退到原整体上传
          const msg = String(err.errMsg || '')
          const isNotFound = msg.includes('url not found') || msg.includes('404') || msg.includes('not exist')
          if (isNotFound && !legacyFallbackTried) {
            legacyFallbackTried = true
            _uploadLegacy<T>(path, files, authHeader).then(resolve).catch(reject)
            return
          }
          if (legacyFallbackTried) return // 避免重复 reject
          failed = true
          reject(new Error(err.errMsg || '上传失败'))
        },
      })
    })
  })
}

/** 回退：旧版一次性上传接口（兼容） */
function _uploadLegacy<T>(path: string, files: string[], authHeader: Record<string, string>): Promise<T> {
  return new Promise((resolve, reject) => {
    const results: unknown[] = []
    let completed = 0
    files.forEach((filePath) => {
      wx.uploadFile({
        url: getBase() + path,
        filePath,
        name: 'files',
        header: authHeader,
        success(res) {
          try {
            const r = JSON.parse(res.data) as ApiResponse<T>
            results.push(r)
            completed++
            if (completed === files.length) {
              const last = results[results.length - 1] as ApiResponse<T>
              if (typeof last.code === 'number' && last.code !== 0) {
                reject(new Error(last.message || '解析响应失败'))
              } else {
                resolve((last.data ?? last) as T)
              }
            }
          } catch {
            completed++
            reject(new Error('解析响应失败'))
          }
        },
        fail(err) {
          reject(new Error(err.errMsg || '上传失败'))
        },
      })
    })
  })
}

// ========== 工具方法 ==========
export const requestUtil = {
  /** 获取当前 baseUrl（调试用） */
  getBaseUrl: getBase,
  /** 获取当前环境 */
  detectEnv,
  /** 重新设置 baseUrl（本地调试） */
  setBase(url: string) {
    try {
      const app = getApp<IAppOption>()
      if (app?.globalData) app.globalData.apiBase = url
    } catch {
      /* ignore */
    }
  },
}
