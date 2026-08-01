/**
 * 微信小程序全局类型声明（V3.0 增强版）
 */

declare function App<T>(options: T): void
declare function Page<D, P>(options: { data?: D; [key: string]: any } & P): void
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

/** 应用实例接口 */
interface IAppOption {
  globalData: {
    businessId: string
    diagnosisId: string
    planId: string
    reviewId: string
    apiBase: string
    userInfo?: { user_id: string; nickname?: string; avatar?: string } | null
    authToken?: string | null
    businessInfo?: any | null
    currentPhase?: number | null
    currentWeek?: number | null
    diagnosisResult?: any | null
    currentRoadmap?: any | null
    weeklyPlan?: any | null
    latestReview?: any | null
  }
  restoreFromStorage(): void
  saveState<K extends string>(key: K, value: any): void
  getState<K extends string>(key: K): any
  resetAll(): void
  loadBusinessInfo?(): Promise<void>
  ensureReady?(): Promise<boolean>
  updateWeekInfo?(week: number | null, phaseIndex: number | null): void
}

// 微信小程序环境内置支持 require
declare const require: (id: string) => any
declare const module: any
declare const exports: any

declare const wx: {
  // ===== 网络 =====
  request<T = any>(options: {
    url: string
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
    data?: any
    header?: Record<string, string>
    timeout?: number
    success?: (res: { data: T; statusCode: number; header: Record<string, string> }) => void
    fail?: (err: { errMsg: string }) => void
    complete?: () => void
  }): void
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
