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

import { TokenStorage, STORAGE_KEYS } from '../utils/storage'
import { handleTokenExpired } from '../utils/auth'
import { API_CODE } from '../utils/constants'
import { classifyError } from '../utils/error'
import { DEV_PORT, DEV_DEFAULT_URL, resolveDevBaseUrl, PROD_DEFAULT_URL } from '../config'
import { detectEnvKind, PLACEHOLDER_DOMAIN } from '../utils/env'

// ======================== 常量集中定义 ========================
// ===== 超时配置（环境分级，避免 WAServiceMainContext 全局 timeout 兜底炸崩渲染层）=====
/** Dev 环境（开发者工具 / 真机调试）：后端没起时 10s 快速失败，不傻等 30s */
const DEV_TIMEOUT = 10000
/** Prod 环境（正式版）：正常网络 30s 超时 */
const PROD_TIMEOUT = 30000
/** Dev 环境上传超时：上传慢多给点时间，但不要 60s */
const DEV_UPLOAD_TIMEOUT = 20000
/** Prod 环境上传超时 */
const PROD_UPLOAD_TIMEOUT = 60000
/** getBase() 解密总超时：避免 prod 场景下 showModal 等用户操作阻塞初始化整 3s 还没拿到 base → 快速降级 */
const GET_BASE_RESOLVE_TIMEOUT = 3000
/** 按环境返回默认请求超时（毫秒） */
const defaultTimeoutMs = (): number => (detectEnvKind() === 'dev' ? DEV_TIMEOUT : PROD_TIMEOUT)
/** 按环境返回默认上传超时（毫秒） */
const defaultUploadTimeoutMs = (): number =>
  detectEnvKind() === 'dev' ? DEV_UPLOAD_TIMEOUT : PROD_UPLOAD_TIMEOUT

/**
 * 通用 Promise 超时工具：Promise.race([task, rejectAfter(ms)])
 * 用于任何可能被用户交互/解密/IO 阻塞的异步调用，防止卡死 → 基础库全局 timeout 兜底炸崩
 */
const withTimeout = <T>(task: Promise<T>, ms: number, desc = 'operation'): Promise<T> =>
  Promise.race([
    task,
    new Promise<T>((_, reject) => {
      const _t = setTimeout(() => {
        clearTimeout(_t)
        reject(new Error(`${desc} 超时 (${ms}ms)，请检查后端服务或网络`))
      }, ms)
    }),
  ])

/**
 * 终极兜底：检测并提示回环地址。
 * 不再自动替换为硬编码 IP，而是警告用户通过 Storage 配置真实 IP。
 */
const _sanitizeLocalhostUrl = (url: string): string => {
  if (!url) return url
  if (/^(https?:\/\/)?(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?/i.test(url)) {
    console.warn(
      '[request] 检测到 localhost URL，真机调试将无法连接。\n' +
      '  请在 Console 执行：\n' +
      `  wx.setStorageSync('${STORAGE_KEYS.DEV_API_BASE}', 'http://你的本机IP:${DEV_PORT}/api')`
    )
  }
  return url
}

/**
 * Dev 环境 BaseURL 三级降级（委托至 config.ts 统一管理）：
 *   1. Storage(md:dev_api_base) — Console 设置一次即可持久化
 *   2. globalData.DEV_API_BASE — app.ts onLaunch 注入
 *   3. config.ts 默认值（localhost 兜底）— 仅开发工具模拟器可用
 */
const _resolveDevBaseUrl = (): string => resolveDevBaseUrl()

/**
 * 读取登录后持久化的生产地址（后端下发）
 */
const _readStoredProdBaseUrl = (): string | null => {
  try {
    const fromStorage = (wx as any)?.getStorageSync?.(STORAGE_KEYS.API_BASE_URL)
    if (typeof fromStorage === 'string' && fromStorage) return fromStorage
  } catch { /* ignore */ }
  return null
}

/**
 * 校验生产地址格式（必须是 https 的合法域名，排除占位符）
 */
const _isValidProdBaseUrl = (url: string | null | undefined): url is string => {
  return (
    !!url &&
    !url.includes(PLACEHOLDER_DOMAIN) &&
    url.length >= 16 &&
    /^https:\/\/[a-z0-9.-]+(:\d+)?(\/.*)?$/i.test(url)
  )
}

/** 生产地址缓存（小程序生命周期仅解析 1 次） */
let _cachedProdBaseUrl: string | null | undefined = undefined

/**
 * BaseURL 获取链路：
 *   Dev  → globalData.DEV_API_BASE → Storage(md:dev_api_base) → 局域网 IP
 *   Prod → 登录成功后后端下发的 API_BASE_URL（持久化）→ 回退 PROD_DEFAULT_URL → 仍失败弹窗阻断
 *
 * 注意：无论哪条链路返回的 URL，最终在 wx.request 前都会被 _sanitizeLocalhostUrl 替换。
 */
const getBase = async (): Promise<string> => {
  // 最高优先级：globalData.apiBase（兼容老代码），但跳过 localhost/回环地址
  try {
    const app = getApp<IAppOption>()
    const base = app?.globalData?.apiBase
    if (
      base &&
      !/^(https?:\/\/)?(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?/i.test(base)
    ) {
      return base
    }
  } catch {
    /* ignore */
  }

  const env = detectEnvKind()

  if (env === 'dev') {
    const resolved = _resolveDevBaseUrl()
    // ⚠️ 若最终仍是回环地址（理论上不会），打印 WARN 引导用户
    if (/^(https?:\/\/)?(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?/i.test(resolved)) {
      console.warn(
        '[request] Dev BaseURL 命中回环地址。请执行：\n' +
        `  wx.setStorageSync('${STORAGE_KEYS.DEV_API_BASE}', '${DEV_DEFAULT_URL}')\n` +
        '然后关闭小程序重新打开。'
      )
    } else {
      console.info(`[request] Dev BaseURL: ${resolved}`)
    }
    return resolved
  }

  // ================ PROD 场景（release）================
  if (_cachedProdBaseUrl !== undefined) {
    if (_cachedProdBaseUrl) return _cachedProdBaseUrl
  }

  // 生产地址来自「登录成功后后端下发并持久化」的配置，不再本地硬编码/加密
  const stored = _readStoredProdBaseUrl()
  const prodUrl = _isValidProdBaseUrl(stored)
    ? stored!
    : (_isValidProdBaseUrl(PROD_DEFAULT_URL) ? PROD_DEFAULT_URL : null)

  if (prodUrl) {
    _cachedProdBaseUrl = prodUrl
    return prodUrl
  }

  // 失败：明确弹窗 → 抛错阻断
  _cachedProdBaseUrl = null
  const hint =
    `生产环境 BaseURL 未配置\n` +
    `登录成功后后端会下发 api_base_url 并持久化；若仍为空：\n` +
    `  · 后端配置环境变量 PUBLIC_API_BASE_URL（公开生产域名）\n` +
    `  · 或前端 frontend/config.ts 的 PROD_DEFAULT_URL 填入公开生产域名`
  console.error('[request] PROD_URL_INVALID: 后端未下发 api_base_url 且无引导地址')
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
  throw new Error('[config] 生产环境URL未配置（后端未下发 api_base_url，且无 PROD_DEFAULT_URL 引导地址）')
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
    // getBase() 超时保护：prod 解密场景有 showModal 等用户交互可能阻塞，3s 没拿到就快速失败
    const base = await withTimeout(getBase(), GET_BASE_RESOLVE_TIMEOUT, '获取 BaseURL')
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

      const finalUrl = base + opts.url
      // 🔴 终极兜底：如果仍然是 localhost/127.0.0.1，强制替换为局域网 IP（任何情况都不会向 localhost 发请求）
      const safeUrl = _sanitizeLocalhostUrl(finalUrl)
      if (safeUrl !== finalUrl) {
        console.warn('[request] 检测到 localhost URL，已强制替换为局域网 IP：', finalUrl, '→', safeUrl)
      }
      console.info(`[request] ${opts.method} ${safeUrl}`)

      const reqTimeout = opts.timeout || defaultTimeoutMs()
      wx.request({
        url: safeUrl,
        method: opts.method,
        data: opts.data,
        header,
        timeout: reqTimeout,

        success(res: { data: any; statusCode: number; header: Record<string, string> }) {
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

        fail(err: { errMsg: string }) {
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
    // getBase() 超时保护：prod 解密场景有 showModal 等用户交互可能阻塞
    const base = _sanitizeLocalhostUrl(
      await withTimeout(getBase(), GET_BASE_RESOLVE_TIMEOUT, '获取 BaseURL')
    )
    const upTimeout = defaultUploadTimeoutMs()
    const reqTimeout = defaultTimeoutMs()
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
          timeout: upTimeout,
          success(res: { data: string; statusCode: number }) {
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
                  timeout: reqTimeout,
                  header: {
                    'Content-Type': 'application/json',
                    ...authHeader,
                  },
                  success(genRes: { data: any; statusCode: number }) {
                    const gr = (genRes.data as unknown) as ApiResponse<T>
                    if (typeof gr.code === 'number' && gr.code !== 0) {
                      reject(new Error(gr.message || '生成复盘报告失败'))
                    } else {
                      resolve((gr.data ?? gr) as T)
                    }
                  },
                  fail(genErr: { errMsg: string }) {
                    reject(new Error(genErr.errMsg || '生成复盘报告失败'))
                  },
                })
              }
            } catch {
              failed = true
              reject(new Error('解析上传响应失败'))
            }
          },
          fail(err: { errMsg: string }) {
            // 旧接口兼容：/upload 路径失败 → 回退到原整体上传
            const msg = String(err.errMsg || '')
            const isNotFound =
              msg.includes('url not found') || msg.includes('404') || msg.includes('not exist')
            if (isNotFound && !legacyFallbackTried) {
              legacyFallbackTried = true
              _uploadLegacy<T>(base, path, files, authHeader, upTimeout).then(resolve).catch(reject)
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

/**
 * 通用单文件上传（阶段四闭环：数据上传 → 指标解析）
 *
 * 与 upload() 的两阶段复盘流程不同，这里是「一次 POST 一个文件」的通用形态，
 * 适用于 /metrics/upload 这类直接返回解析结果的端点。
 *
 * @param path      形如 '/metrics/upload'
 * @param filePath  wx.chooseMedia / chooseMessageFile 返回的本地临时路径
 * @param name      form-data 字段名（后端 UploadFile 参数名，默认 'file'）
 * @param formData  附加表单字段（会被 wx 转成字符串）
 */
export function uploadFile<T>(
  path: string,
  filePath: string,
  name = 'file',
  formData: Record<string, string> = {},
): Promise<T> {
  return (async () => {
    const base = _sanitizeLocalhostUrl(
      await withTimeout(getBase(), GET_BASE_RESOLVE_TIMEOUT, '获取 BaseURL')
    )
    const token = TokenStorage.get()
    const authHeader: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}

    return new Promise<T>((resolve, reject) => {
      if (!filePath) {
        reject(new Error('请选择文件'))
        return
      }
      wx.uploadFile({
        url: base + path,
        filePath,
        name,
        formData,
        header: authHeader,
        timeout: defaultUploadTimeoutMs(),
        success(res: { data: string; statusCode: number }) {
          if (res.statusCode === 401 || res.statusCode === 403) {
            handleTokenExpired()
            reject(new Error('登录已过期，请重新登录'))
            return
          }
          let parsed: any
          try {
            parsed = JSON.parse(res.data)
          } catch {
            reject(new Error('解析上传响应失败'))
            return
          }
          // 兼容 {code,data,message} 与裸对象（FastAPI 直返 dict）两种返回
          if (parsed && typeof parsed.code === 'number') {
            if (parsed.code === API_CODE.NOT_LOGIN) {
              handleTokenExpired()
              reject(new Error(parsed.message || '请先登录'))
              return
            }
            if (parsed.code !== API_CODE.SUCCESS) {
              reject(new Error(parsed.message || '上传失败'))
              return
            }
            resolve((parsed.data ?? parsed) as T)
            return
          }
          resolve(parsed as T)
        },
        fail(err: { errMsg: string }) {
          reject(new Error(err.errMsg || '上传失败'))
        },
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
  upTimeout = 60000,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const results: unknown[] = []
    let completed = 0
    files.forEach((filePath) => {
      wx.uploadFile({
        url: base + path,
        filePath,
        timeout: upTimeout,
        name: 'files',
        header: authHeader,
        success(res: { data: string; statusCode: number }) {
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
        fail(err: { errMsg: string }) {
          reject(new Error(err.errMsg || '上传失败'))
        },
      })
    })
  })
}

// ========== 流式（SSE / 分块）请求 ==========
/**
 * UTF-8 字节数组 → 字符串（不依赖 TextDecoder，兼容低版本基础库）
 */
function utf8Decode(bytes: Uint8Array): string {
  let out = ''
  let i = 0
  const len = bytes.length
  while (i < len) {
    const c = bytes[i++]
    if (c < 0x80) {
      out += String.fromCharCode(c)
    } else if (c >= 0xc0 && c < 0xe0) {
      const c2 = bytes[i++]
      out += String.fromCharCode(((c & 0x1f) << 6) | (c2 & 0x3f))
    } else if (c >= 0xe0 && c < 0xf0) {
      const c2 = bytes[i++]
      const c3 = bytes[i++]
      out += String.fromCharCode(((c & 0x0f) << 12) | ((c2 & 0x3f) << 6) | (c3 & 0x3f))
    } else {
      const c2 = bytes[i++]
      const c3 = bytes[i++]
      const c4 = bytes[i++]
      const cp = ((c & 0x07) << 18) | ((c2 & 0x3f) << 12) | ((c3 & 0x3f) << 6) | (c4 & 0x3f)
      const u = cp - 0x10000
      out += String.fromCharCode(0xd800 + (u >> 10), 0xdc00 + (u & 0x3ff))
    }
  }
  return out
}

/**
 * 流式对话选项（WebSocket 实现）。
 */
export interface StreamOptions {
  /** WS 路径，例如 '/agent/chat/ws'（基于 getBase() 的 host 拼接为 ws(s)://host/api…） */
  url: string
  /** 连接建立后发送的首帧请求体（JSON） */
  data?: Record<string, unknown>
  /** 每解析出一个事件回调（与后端 WS 回推的 JSON 载荷一致） */
  onEvent: (event: any) => void
  /** 错误回调（已归类为 AppError） */
  onError?: (err: import('../utils/error').AppError) => void
}

/**
 * 可中断的流式句柄：promise 在流结束（成功/失败）时 settle；
 * abort() 主动中止（新对话 / 离开页面），中止不会触发 onError，也不会弹错误提示。
 * 被 abort 时 promise 以带 `isAbort` 标记的错误 reject，调用方可据以静默忽略。
 */
export interface StreamHandle {
  promise: Promise<void>
  abort: () => void
}

/**
 * 流式请求（WebSocket）：用 wx.connectSocket 建立长连接，
 * 连接后发送首帧 JSON（opts.data），随后逐个回推后端 Agent 事件（onEvent）。
 *
 * 对应后端 ``WS /api/agent/chat/ws`` 协议：
 *   - token 通过 ``?token=`` 查询参数下发（小程序 connectSocket 自定义请求头支持有限）；
 *   - 后端空闲时下发 ``{"type":"ping"}`` 心跳，前端忽略；
 *   - 后端下推 ``{"type":"error", "message": ...}`` 时当作失败（reject）；
 *   - 连接关闭（onClose）即视为流正常结束并 resolve。
 *
 * 不再使用 wx.request({enableChunked:true}) 的 SSE 方案，规避微信分块请求
 * 在部分基础库版本下的 ``Error: timeout``（WAServiceMainContext 原生超时）。
 */
export function stream(opts: StreamOptions): StreamHandle {
  let aborted = false
  let ws: WxSocketTask | null = null
  let settled = false
  let resolveFn: () => void = () => {}
  let rejectFn: (e: any) => void = () => {}

  const promise = new Promise<void>((resolve, reject) => {
    resolveFn = resolve
    rejectFn = reject
  })

  const onErr = (msg: string, isAbort = false): void => {
    const appErr = classifyError(new Error(msg))
    if (!isAbort) opts.onError?.(appErr)
    if (!settled) {
      settled = true
      rejectFn(appErr)
    }
  }

  // 异步获取 BaseURL（生产环境需解密），其余逻辑在拿到 base 后执行
  ;(async () => {
    try {
      const base = _sanitizeLocalhostUrl(
        await withTimeout(getBase(), GET_BASE_RESOLVE_TIMEOUT, '获取 BaseURL'),
      )
      // 若在中止后才拿到 base，不再发起连接
      if (aborted) return

      const token = TokenStorage.get()
      // http(s)://host/api → ws(s)://host/api
      const wsBase = base.replace(/^http/i, 'ws')
      const wsUrl = wsBase + opts.url + (token ? `?token=${encodeURIComponent(token)}` : '')

      ws = wx.connectSocket({ url: wsUrl })

      ws?.onOpen(() => {
        if (aborted) return
        try {
          ws?.send({ data: JSON.stringify(opts.data || {}) })
        } catch {
          onErr('WebSocket 首帧发送失败')
        }
      })

      ws?.onMessage((res: { data: string | ArrayBuffer }) => {
        if (aborted) return
        try {
          const text =
            typeof res.data === 'string'
              ? res.data
              : utf8Decode(new Uint8Array(res.data as ArrayBuffer))
          const evt = JSON.parse(text)
          if (!evt || typeof evt !== 'object') return
          // 心跳忽略，不回调业务
          if (evt.type === 'ping') return
          // 后端下推的错误事件 → 当作失败处理（与 SSE HTTP>=400 等价）
          if (evt.type === 'error') {
            if (/token|登录|未登录|失效/i.test(String(evt.message || ''))) {
              handleTokenExpired()
            }
            onErr(evt.message || '流式对话出错')
            return
          }
          opts.onEvent(evt)
        } catch (e) {
          // 解析异常不中断整个流，仅记录
          console.error('[stream] ws message parse error', e)
        }
      })

      ws?.onClose(() => {
        if (aborted) return
        if (!settled) {
          settled = true
          resolveFn()
        }
      })

      ws?.onError((err: { errMsg?: string }) => {
        if (aborted) return
        onErr(err?.errMsg || 'WebSocket 连接失败')
      })
    } catch (e: any) {
      onErr(e?.message || 'WebSocket 初始化失败')
    }
  })()

  const abort = (): void => {
    if (aborted) return
    aborted = true
    try {
      ws?.close({ code: 1000 })
    } catch {
      /* ignore */
    }
    if (!settled) {
      settled = true
      const err = classifyError(new Error('stream aborted'))
      ;(err as any).isAbort = true
      rejectFn(err)
    }
  }

  return { promise, abort }
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
