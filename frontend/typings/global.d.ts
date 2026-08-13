/**
 * 微信小程序全局类型声明（V3.0 增强版）
 */

declare function App<T>(options: T): void

/**
 * 页面实例（Page 内 this 的类型）
 * 注意：data 声明为必选，避免每处 this.data.x 都被判定 possibly undefined
 */
interface WxPageInstance<D = any> {
  data: D
  setData(data: Partial<D> | Record<string, any>, callback?: () => void): void
  route: string
  options: Record<string, string>
  selectComponent(selector: string): any
  selectAllComponents(selector: string): any[]
  createSelectorQuery(): any
}

declare function Page<D = any, P extends Record<string, any> = Record<string, any>>(
  options: { data?: D } & P & ThisType<WxPageInstance<D> & P>,
): void
declare function Component<D extends Record<string, any> = any, P extends Record<string, any> = any, M extends Record<string, any> = any>(options: {
  properties?: Record<string, any>
  data?: Record<string, any>
  methods?: Record<string, any>
  lifetimes?: Record<string, any>
  observers?: Record<string, (...args: any[]) => void>
  behaviors?: any[]
  [key: string]: any
}): void
declare function Behavior(options: any): any
declare function getApp<T = any>(): T
declare function getCurrentPages(): { route: string; [key: string]: any }[]
declare function setTimeout(cb: () => void, delay: number): number
declare function clearTimeout(id: number): void

/**
 * 应用实例接口（阶段三精简版）
 *
 * globalData 只保留网络层必需的最小配置，业务状态统一由 store/index.ts 管理。
 * 旧版的 businessId / diagnosisResult / _navLock / safeNavigate 等已全部移除。
 */
interface IAppOption {
  globalData: {
    /** 显式覆盖的 API 地址（留空则走 config.ts 三级降级） */
    apiBase: string
    /** Dev 环境地址：必须局域网 IP，不能 localhost */
    DEV_API_BASE: string
    /** 登录态 token 镜像（写入以 TokenStorage 为准） */
    authToken?: string | null
  }
  /** 是否非正式版环境 */
  isDev(): boolean
  /** 退出登录：清 token + 清空全局仓库 */
  logout(): void
}

/** 分块（流式）请求任务，用于 SSE 接收 Agent 思考过程 */
interface WxRequestTask {
  abort(): void
  onChunkReceived(cb: (res: { data: ArrayBuffer }) => void): void
  offChunkReceived(cb?: (res: { data: ArrayBuffer }) => void): void
  onHeadersReceived(cb: (res: { header: Record<string, string> }) => void): void
}

/** WebSocket 连接任务（connectSocket 返回值），用于流式对话 */
interface WxSocketTask {
  send(options: { data: string | ArrayBuffer; success?: () => void; fail?: (err: { errMsg: string }) => void }): void
  close(options?: { code?: number; reason?: string; success?: () => void; fail?: (err: any) => void }): void
  onOpen(cb: (res: { header?: Record<string, string> }) => void): void
  onMessage(cb: (res: { data: string | ArrayBuffer }) => void): void
  onClose(cb: (res: { code?: number; reason?: string }) => void): void
  onError(cb: (res: { errMsg: string }) => void): void
}

// 微信小程序环境内置支持 require
declare const require: (id: string) => any
declare const module: any
declare const exports: any

// 兼容前端打包时注入的 process.env（Vite / Webpack 等常见场景）
declare const process: {
  env?: {
    NODE_ENV?: string
    [k: string]: string | undefined
  }
  version?: string
  platform?: string
}

declare const wx: {
  // ===== 网络 =====
  request<T = any>(options: {
    url: string
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
    data?: any
    header?: Record<string, string>
    timeout?: number
    /** 开启分块传输（SSE / 流式接收 Agent 思考过程），2.23.0+ 基础库支持 */
    enableChunked?: boolean
    success?: (res: { data: T; statusCode: number; header: Record<string, string> }) => void
    fail?: (err: { errMsg: string }) => void
    complete?: () => void
  }): WxRequestTask
  connectSocket(options: {
    url: string
    header?: Record<string, string>
    protocols?: string[]
    success?: () => void
    fail?: (err: { errMsg: string }) => void
    complete?: () => void
  }): WxSocketTask
  uploadFile(options: {
    url: string
    filePath: string
    name: string
    header?: Record<string, string>
    formData?: Record<string, any>
    timeout?: number
    success?: (res: { data: string; statusCode: number }) => void
    fail?: (err: { errMsg: string }) => void
    complete?: () => void
  }): void

  // ===== 登录 =====
  login(options: {
    success?: (res: { code: string; errMsg: string }) => void
    fail?: (err: { errMsg: string }) => void
    complete?: () => void
  }): void

  // ===== 媒体选择 =====
  chooseMedia(options: {
    count: number
    mediaType: ('image' | 'video' | 'mix')[]
    sourceType?: ('album' | 'camera')[]
    sizeType?: ('original' | 'compressed')[]
    maxDuration?: number
    camera?: 'back' | 'front'
    success: (res: { tempFiles: { tempFilePath: string; size: number; duration?: number; fileType: string }[]; type: string }) => void
    fail?: (err: { errMsg: string }) => void
  }): void
  chooseImage(options: {
    count?: number
    sizeType?: ('original' | 'compressed')[]
    sourceType?: ('album' | 'camera')[]
    success: (res: { tempFilePaths: string[]; tempFiles: { path: string; size: number }[] }) => void
    fail?: (err: { errMsg: string }) => void
  }): void
  chooseMessageFile(options: {
    count: number
    type: 'all' | 'file' | 'image' | 'video'
    extension?: string[]
    success: (res: { tempFiles: { path: string; name: string; size: number }[] }) => void
    fail?: (err: { errMsg: string }) => void
  }): void
  previewImage(options: { urls: string[]; current?: string; showmenu?: boolean }): void
  saveImageToPhotosAlbum(options: { filePath: string; success?: () => void; fail?: (err: any) => void }): void

  // ===== 导航 =====
  navigateTo(options: { url: string; success?: () => void; fail?: (err: any) => void; complete?: () => void }): void
  redirectTo(options: { url: string; success?: () => void; fail?: (err: any) => void; complete?: () => void }): void
  reLaunch(options: { url: string; success?: () => void; fail?: (err: any) => void; complete?: () => void }): void
  switchTab(options: { url: string; success?: () => void; fail?: (err: any) => void; complete?: () => void }): void
  navigateBack(options?: { delta?: number; success?: () => void; fail?: (err: any) => void; complete?: () => void }): void

  // ===== 交互反馈 =====
  showToast(options: {
    title: string
    icon?: 'success' | 'none' | 'loading' | 'error'
    image?: string
    duration?: number
    mask?: boolean
    success?: () => void
    fail?: () => void
  }): void
  showLoading(options: { title: string; mask?: boolean; success?: () => void }): void
  hideLoading(): void
  showModal(options: {
    title?: string
    content: string
    showCancel?: boolean
    cancelText?: string
    cancelColor?: string
    confirmText?: string
    confirmColor?: string
    editable?: boolean
    placeholderText?: string
    success?: (res: { confirm: boolean; cancel: boolean; content?: string }) => void
    fail?: (err: { errMsg: string }) => void
    complete?: () => void
  }): void
  showActionSheet(options: {
    itemList: string[]
    itemColor?: string
    success?: (res: { tapIndex: number }) => void
    fail?: (err: { errMsg: string }) => void
  }): void

  // ===== 下拉刷新 =====
  startPullDownRefresh(options?: { success?: () => void; fail?: (err: any) => void }): void
  stopPullDownRefresh(): void

  // ===== 本地存储 =====
  getStorageSync<T = any>(key: string): T
  setStorageSync(key: string, value: any): void
  removeStorageSync(key: string): void
  clearStorageSync(): void
  getStorageInfoSync(): { keys: string[]; currentSize: number; limitSize: number }

  // ===== 设置/权限 =====
  authorize(options: { scope: string; success?: () => void; fail?: (err: any) => void }): void
  getSetting(options: {
    success?: (res: { authSetting: Record<string, boolean> }) => void
    fail?: (err: any) => void
  }): void
  openSetting(options?: { success?: (res: { authSetting: Record<string, boolean> }) => void }): void

  // ===== 设备/系统 =====
  getSystemInfoSync(): {
    platform: 'ios' | 'android' | 'devtools' | string
    system: string
    model: string
    pixelRatio: number
    windowWidth: number
    windowHeight: number
    screenWidth: number
    screenHeight: number
    version: string
    SDKVersion: string
  }
  getNetworkType(options: {
    success?: (res: { networkType: 'wifi' | '4g' | '3g' | '2g' | 'none' | 'unknown' }) => void
    fail?: () => void
  }): void
  getAccountInfoSync(): {
    miniProgram: { appId: string; envVersion: 'develop' | 'trial' | 'release'; version: string }
  }
  canIUse(schema: string): boolean
  nextTick(cb: () => void): void

  // ===== 节点查询（Canvas 2D 需要） =====
  createSelectorQuery(): {
    select(selector: string): {
      fields(fields: { node?: boolean; size?: boolean; rect?: boolean }): any
      boundingClientRect(cb?: (rect: any) => void): any
    }
    selectAll(selector: string): any
    in(component: any): any
    exec(cb?: (res: any[]) => void): void
  }
  pageScrollTo(options: { scrollTop?: number; selector?: string; duration?: number }): void

  // ===== 剪贴板 =====
  setClipboardData(options: { data: string; success?: () => void; fail?: () => void }): void
  getClipboardData(options: { success?: (res: { data: string }) => void; fail?: () => void }): void

  // ===== 更新 =====
  getUpdateManager(): {
    onCheckForUpdate(cb: (res: { hasUpdate: boolean }) => void): void
    onUpdateReady(cb: () => void): void
    onUpdateFailed(cb: (err: any) => void): void
    applyUpdate(): void
  }
}

declare namespace WechatMiniprogram {
  type IAnyObject = Record<string, any>

  interface GeneralCallbackResult {
    errMsg: string
  }

  interface LoginSuccessCallbackResult {
    code: string
    errMsg: string
  }

  type Input = {
    detail: { value: string; cursor?: number; keyCode?: number }
    currentTarget: { dataset: Record<string, any>; id: string }
    target?: any
    mark?: Record<string, any>
  }
  type TextareaInput = {
    detail: { value: string; cursor?: number }
    currentTarget: { dataset: Record<string, any> }
  }
  type BaseEvent<TDetail = any, TDataset extends Record<string, any> = Record<string, any>> = {
    currentTarget: { dataset: TDataset; id: string }
    target?: any
    mark?: Record<string, any>
    detail?: TDetail
    type: string
    timeStamp: number
  }
  type TouchEvent = BaseEvent & {
    touches: any[]
    changedTouches: any[]
  }
  type FormEvent = {
    detail: { value: Record<string, any>; formId?: string }
    currentTarget: { dataset: Record<string, any> }
  }
}

declare const Behavior: (options: any) => any
