/**
 * 应用入口 V3.0（文档7.1节 全局状态管理）
 *
 * - 全局状态管理：globalData 扩展为 ID + 对象两级结构
 * - 本地缓存恢复：onLaunch 时从 storage 读取并填充 globalData
 * - 企业信息懒加载：首次用到时从 /business/info 拉取
 */

import type { GlobalState } from './types/index'
import {
  STORAGE_KEYS,
  getStorage,
  TokenStorage,
  setStorage,
} from './utils/storage'
import { ensureLogin, isLoggedIn, hasBusinessInfo } from './utils/auth'

App({
  globalData: {
    // ===== ID级状态（旧版兼容 + 新版最小粒度） =====
    businessId: '',
    diagnosisId: '',
    planId: '',
    reviewId: '',
    apiBase: 'http://localhost:8000/api',

    // ===== 对象级状态（文档7.1节） =====
    authToken: null,
    userInfo: null,
    businessInfo: null,
    currentPhase: null,
    currentWeek: null,
    diagnosisResult: null,
    currentRoadmap: null,
    weeklyPlan: null,
    latestReview: null,
  } as GlobalState,

  /** 初始化：从本地缓存恢复全部状态 + 静默登录（可选） */
  async onLaunch() {
    this.restoreFromStorage()

    // 已有token → 异步预加载企业信息（不阻塞启动）
    if (isLoggedIn() && hasBusinessInfo()) {
      this.loadBusinessInfo().catch(() => {/* ignore */})
    }
  },

  /**
   * 从 storage 恢复全局状态
   * ID级：直接读字符串
   * 对象级：从带TTL的storage工具读取（过期自动null）
   */
  restoreFromStorage() {
    const g = this.globalData

    // 1) ID级状态（原有兼容）
    const idKeys: (keyof GlobalState)[] = [
      'businessId',
      'diagnosisId',
      'planId',
      'reviewId',
    ] as const
    idKeys.forEach((key) => {
      const legacyKey = key as string // 'businessId' 对应 STORAGE_KEYS.BUSINESS_ID = 'businessId'
      const val = wx.getStorageSync(legacyKey)
      if (val) {
        ;(g as unknown as Record<string, unknown>)[key] = val
      }
    })

    // 2) Token → authToken 双向同步
    const token = TokenStorage.get()
    if (token) g.authToken = token

    // 3) 对象级状态（V3.0 新增，带TTL）
    g.userInfo = getStorage(STORAGE_KEYS.USER_INFO) || null
    g.businessInfo = getStorage(STORAGE_KEYS.BUSINESS_INFO) || null
    g.diagnosisResult = getStorage(STORAGE_KEYS.DIAGNOSIS) || null
    g.currentRoadmap = getStorage(STORAGE_KEYS.ROADMAP) || null
    g.weeklyPlan = getStorage(STORAGE_KEYS.WEEKLY_PLAN) || null

    // 4) currentPhase/currentWeek fallback 从businessInfo派生
    if (g.businessInfo) {
      if (typeof g.businessInfo.current_phase === 'number' && !g.currentPhase) {
        g.currentPhase = g.businessInfo.current_phase
      }
      if (typeof g.businessInfo.current_week === 'number' && !g.currentWeek) {
        g.currentWeek = g.businessInfo.current_week
      }
    }
  },

  /** 保存单个状态值 → 同时更新 globalData + storage */
  saveState<K extends keyof GlobalState>(key: K, value: GlobalState[K]) {
    const g = this.globalData
    ;(g as unknown as Record<string, unknown>)[key as string] = value

    // ID类字符串 → 按旧路径也存一份（兼容老页面）
    if (typeof value === 'string') {
      const idKeys: Record<string, string> = {
        businessId: 'businessId',
        diagnosisId: 'diagnosisId',
        planId: 'planId',
        reviewId: 'reviewId',
      }
      if (idKeys[key as string]) {
        wx.setStorageSync(key as string, value)
      }
    }
  },

  /** 读取状态值 */
  getState<K extends keyof GlobalState>(key: K): GlobalState[K] {
    return this.globalData[key]
  },

  /** 重置所有业务状态（保留apiBase配置） */
  resetAll() {
    const g = this.globalData
    const keepApi = g.apiBase

    // 清 globalData
    const empty: GlobalState = {
      businessId: '',
      diagnosisId: '',
      planId: '',
      reviewId: '',
      apiBase: keepApi,
      authToken: null,
      userInfo: null,
      businessInfo: null,
      currentPhase: null,
      currentWeek: null,
      diagnosisResult: null,
      currentRoadmap: null,
      weeklyPlan: null,
      latestReview: null,
    }
    Object.assign(g, empty)

    // 清 storage
    const keysToRemove = [
      'businessId',
      'diagnosisId',
      'planId',
      'reviewId',
      STORAGE_KEYS.USER_INFO,
      STORAGE_KEYS.BUSINESS_INFO,
      STORAGE_KEYS.DIAGNOSIS,
      STORAGE_KEYS.ROADMAP,
      STORAGE_KEYS.WEEKLY_PLAN,
      STORAGE_KEYS.LAST_CHECKIN_TIME,
    ]
    keysToRemove.forEach((k) => {
      try {
        wx.removeStorageSync(k)
      } catch {
        /* ignore */
      }
    })
    TokenStorage.clear()
  },

  // ============================================================
  // ===== V3.0 新增：全局业务辅助方法 ==========================
  // ============================================================

  /**
   * 从后端加载企业完整信息 → 写入 globalData.businessInfo 及 TTL storage
   * 自动更新 currentPhase/currentWeek
   */
  async loadBusinessInfo(): Promise<void> {
    try {
      const g = this.globalData
      if (!g.businessId) return

      // 懒加载 import 避免循环依赖
      const { get } = await import('./api/request')
      const biz = await get<any>(`/business/${g.businessId}`).catch(
        async () => {
          // 别名端点兜底
          return get<any>('/business/info')
        },
      )
      if (!biz) return

      g.businessInfo = biz
      g.currentPhase = biz.current_phase ?? null
      g.currentWeek = biz.current_week ?? null
      setStorage(STORAGE_KEYS.BUSINESS_INFO, biz)

      // 同步ID
      if (biz.diagnosis_id && !g.diagnosisId) g.diagnosisId = biz.diagnosis_id
      if (biz.plan_id && !g.planId) g.planId = biz.plan_id
      if (biz.review_id && !g.reviewId) g.reviewId = biz.review_id

      // 如果有quarterly_roadmap，也塞进全局
      if (biz.diagnosisResult?.quarterly_roadmap) {
        g.currentRoadmap = biz.diagnosisResult.quarterly_roadmap
      }
    } catch (err) {
      console.warn('[app] loadBusinessInfo failed:', err)
    }
  },

  /**
   * 快捷：确保登录 + 有企业信息 → 无则跳转 onboarding
   * @returns true=已就绪可继续；false=未就绪（已发起跳转）
   */
  async ensureReady(): Promise<boolean> {
    const loginResult = await ensureLogin(false)
    if (!loginResult) {
      wx.reLaunch({ url: '/pages/onboarding/index' })
      return false
    }
    if (!this.globalData.businessId && !hasBusinessInfo()) {
      wx.reLaunch({ url: '/pages/onboarding/index' })
      return false
    }
    return true
  },

  /**
   * 更新当前周/阶段（从dashboard或plan结果反推）
   */
  updateWeekInfo(week: number | null, phaseIndex: number | null) {
    const g = this.globalData
    if (typeof week === 'number') g.currentWeek = week
    if (typeof phaseIndex === 'number') g.currentPhase = phaseIndex
    if (g.businessInfo) {
      if (typeof week === 'number') g.businessInfo.current_week = week
      if (typeof phaseIndex === 'number') g.businessInfo.current_phase = phaseIndex
    }
  },
})
