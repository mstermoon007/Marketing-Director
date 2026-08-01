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
import { tryDecryptProdBaseUrl } from '../utils/env'

// ========== 环境配置（文档2.3节） ==========
//
// ⚠️ 安全策略（V3.0 GitHub风格）：
//   1) 开发环境：使用 http://localhost:8000/api（开发调试，默认）
//   2) 生产环境：prod 域名**绝不以明文存储**，而是以三级加密的密文形式
//      保存在 utils/env.ts（PROD_BASE_URL_CIPHER），运行时通过
//      GITHUB_SEED（由 globalData / wx.storage / process.env 三选一注入）
//      单向派生 SHA-256 密钥 → XOR解密还原真实域名。
//   3) 回退策略：当生产环境 Seed 未配置、或解密失败时，
//      立刻调用 wx.showModal 提示运维/开发者「需要配置 GITHUB_SEED」，
//      避免「静默失败导致 request 打到 example.com 而被拦截」的老问题。
//
const DEV_BASE_URL = 'http://localhost:8000/api'

type EnvKind = 'dev' | 'prod'

/**
 * 根据小程序 envVersion 判定环境
 *   develop  → dev（开发者工具 + 真机调试）
 *   trial    → dev（体验版）
 *   release  → prod（正式版，需要密文解密注入）
 */
const detectEnvKind = (): EnvKind => {
  try {
    const app = getApp<IAppOption>()
    // 1) 显式 apiBase（兼容老代码，优先级最高）
    if (
      app?.globalData?.apiBase &&
      !app.globalData.apiBase.includes('example.com') &&
      /^https?:\/\//.test(app.globalData.apiBase)
    ) {
      return 'dev'
    }
    // 2) 微信官方版本判断
    const envVer = (wx as any)?.getAccountInfoSync?.()?.miniProgram?.envVersion
    if (envVer === 'release') return 'prod'
    return 'dev'
  } catch {
    return 'dev'
  }
}

/** 生产密文缓存（小程序生命周期只解密 1 次） */
let _cachedProdBaseUrl: string | null | undefined = undefined

/**
 * 实际 baseUrl：优先 globalData.apiBase → dev直接返回 → prod密文解密
 *
 * ⚠️ prod 场景失败策略：
 *   若未配置 Seed 或解密得到乱码（含 example.com / 空串 / 未以 http 开头），
 *   立刻 showModal 提醒配置 GITHUB_SEED，并抛错阻断首个 request，
 *   避免请求打到无效域名而被白名单/ DNS 双层拦截而「静默失败」。
 */
const getBase = async (): Promise<string> => {
  // 最高优先级：开发者在 globalData.apiBase 里手动覆盖
  try {
    const app = getApp<IAppOption>()
    if (app?.globalData?.apiBase) return app.globalData.apiBase
  } catch {
    /* ignore */
  }

  const env = detectEnvKind()

  // develop / trial → dev 本地
  if (env === 'dev') return DEV_BASE_URL

  // ================ PROD 场景（release）================
  // 1) 内存缓存命中
  if (_cachedProdBaseUrl !== undefined) {
    if (_cachedProdBaseUrl) return _cachedProdBaseUrl
    // else: 已失败过，走「抛错」路径，保证用户看到错误提示
  }

  // 2) 调 env.ts 解密
  const plain = await tryDecryptProdBaseUrl()
  const valid =
    !!plain &&
    !plain.includes('example.com') &&
    plain.length >= 16 &&
    /^https:\/\/[a-z0-9.-]+(:\d+)?(\/.*)?$/i.test(plain)

  if (valid) {
    _cachedProdBaseUrl = plain!
    return plain!
  }

  // 3) 失败：缓存失败状态 → 明确弹窗提示 → 抛错
  _cachedProdBaseUrl = null
  const hint =
    `生产环境 BaseURL 解密失败（命中了历史占位符域名）\n` +
    `请在全局配置里注入 GITHUB_SEED\n` +
    `方法：getApp().globalData.GITHUB_SEED = 'ghp_xxx' \n` +
    `或 wx.setStorageSync('GITHUB_SEED', 'ghp_xxx')`
  console.error('[request] PROD_URL_INVALID:', plain || '(empty)')
  try {
    wx.showModal({
      title: '请先配置生产环境',
      content: hint,
      showCancel: false,
      confirmText: '知道了',
    })
  } catch {
    /* ignore */
  }
  throw new Error('[config] 生产环境URL未正确配置（占位符example.com未替换）')
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
 *
 * 注意：getBase() 在 prod 场景下是 async 的（需要解密密文），
 * 所以本函数内部先「await getBase()」拿到最终 baseUrl，
 * 再进入 wx.request 的 Promise 回调式处理。
 */
function _requestCore<T>(opts: RequestOptions): Promise<T> {
  return (async () => {
    const base = await getBase()
    return new Promise<T>((resolve, reject) => {
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
        url: base + opts.url,
        method: opts.method,
        data: opts.data,
        header,
        timeout: opts.timeout || 30000,

        success(res) {
          const statusCode = res.statusCode
          // 401 / 403 → 当 token 过期处理
          if (statusCode === 401 || statusCode === 403) {
            handleTokenExpired()
            reject(new Error('登录已过期'))
            return
          }
          const r = (res.data || {}) as ApiResponse<T>
          if (opts.skipCodeCheck) {
            resolve(r as unknown as T)
            return
          }
          if (typeof r.code === 'number') {
            if (r.code === API_CODE.SUCCESS) {
              resolve(r.data)
            } else if (r.code === API_CODE.NOT_LOGIN) {
              handleTokenExpired()
              reject(new Error(r.message || '请先登录'))
            } else {
              reject(new Error(r.message || `请求失败 (code=${r.code})`))
            }
          } else {
            // 后端未按规范返回 code：兜底
            resolve(r as unknown as T)
          }
        },

        fail(err) {
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
  })() as unknown as Promise<T>
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
  return (async () => {
    const base = await getBase()
    return new Promise<T>((resolve, reject) => {
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
          url: base + path + '/upload',
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
                  url: base + path + '/generate',
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
            } catch {
              failed = true
              reject(new Error('解析上传响应失败'))
            }
          },
          fail(err) {
            // 旧接口兼容：/upload 路径失败 → 回退到原整体上传
            const msg = String(err.errMsg || '')
            const isNotFound =
              msg.includes('url not found') || msg.includes('404') || msg.includes('not exist')
            if (isNotFound && !legacyFallbackTried) {
              legacyFallbackTried = true
              _uploadLegacy<T>(base, path, files, authHeader).then(resolve).catch(reject)
              return
            }
            if (legacyFallbackTried) return
            failed = true
            reject(new Error(err.errMsg || '上传失败'))
          },
        })
      })
    })
  })() as unknown as Promise<T>
}

/** 回退：旧版一次性上传接口（兼容） */
function _uploadLegacy<T>(
  base: string,
  path: string,
  files: string[],
  authHeader: Record<string, string>,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const results: unknown[] = []
    let completed = 0
    files.forEach((filePath) => {
      wx.uploadFile({
        url: base + path,
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
  /** 获取当前 baseUrl（调试用，注意：生产环境是异步解密） */
  getBaseUrl: getBase,
  /** 获取当前环境 */
  detectEnv: detectEnvKind,
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
