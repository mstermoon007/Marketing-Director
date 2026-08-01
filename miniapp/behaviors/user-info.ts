/**
 * 用户/企业信息共享 Behavior（文档7.2节规范）
 *
 * 页面/组件通过 behaviors: [userInfoBehavior] 混入，自动获取：
 *   - data.userInfo: {user_id, nickname?, avatar?}
 *   - data.businessInfo: BusinessProfile 完整对象
 *   - data.currentPhase / data.currentWeek
 *   - data.isLoggedIn / data.hasBusinessInfo / data.hasDiagnosis
 *
 * attached 生命周期时，从 getApp().globalData 同步；
 * 也可手动调用 this.syncUserInfo() 主动刷新。
 */

import {
  STORAGE_KEYS,
  getStorage,
  TokenStorage,
} from '../utils/storage'
import type {
  BusinessProfile,
  DiagnosisReport,
  QuarterRoadmap,
  SevenDayPlan,
  ReviewReport,
} from '../types/index'

export interface UserInfoBehaviorData {
  userInfo: { user_id: string; nickname?: string; avatar?: string } | null
  businessInfo: BusinessProfile | null
  currentPhase: number | null
  currentWeek: number | null
  diagnosisResult: DiagnosisReport | null
  currentRoadmap: QuarterRoadmap | null
  weeklyPlan: SevenDayPlan | null
  latestReview: ReviewReport | null
  isLoggedIn: boolean
  hasBusinessInfo: boolean
  hasDiagnosis: boolean
  hasPlan: boolean
  hasReview: boolean
}

export interface UserInfoBehaviorMethods {
  /** 手动同步 globalData 到组件/页面 data */
  syncUserInfo(): void
  /** 刷新业务信息：从后端拉最新 businessInfo */
  refreshBusinessInfo(): Promise<void>
  /** 清除本地登录态（登出） */
  clearAuth(): void
}

/** 从全局对象读并规范化 */
function _pickGlobal(): Partial<UserInfoBehaviorData> {
  const app = getApp<IAppOption>()
  const g = app?.globalData
  if (!g) return {}

  const token = TokenStorage.get() || g.authToken || null
  const businessId =
    getStorage<string>(STORAGE_KEYS.BUSINESS_ID) || g.businessId || ''
  const diagnosisId =
    getStorage<string>(STORAGE_KEYS.DIAGNOSIS_ID) || g.diagnosisId || ''
  const planId = getStorage<string>(STORAGE_KEYS.PLAN_ID) || g.planId || ''
  const reviewId =
    getStorage<string>(STORAGE_KEYS.REVIEW_ID) || g.reviewId || ''

  return {
    userInfo:
      g.userInfo ||
      getStorage<{ user_id: string; nickname?: string; avatar?: string }>(
        STORAGE_KEYS.USER_INFO,
      ),
    businessInfo:
      g.businessInfo ||
      getStorage<BusinessProfile>(STORAGE_KEYS.BUSINESS_INFO),
    currentPhase:
      typeof g.currentPhase === 'number'
        ? g.currentPhase
        : (g.businessInfo?.current_phase ?? null),
    currentWeek:
      typeof g.currentWeek === 'number'
        ? g.currentWeek
        : (g.businessInfo?.current_week ?? null),
    diagnosisResult:
      g.diagnosisResult ||
      getStorage<DiagnosisReport>(STORAGE_KEYS.DIAGNOSIS),
    currentRoadmap:
      g.currentRoadmap ||
      g.diagnosisResult?.quarterly_roadmap ||
      getStorage<QuarterRoadmap>(STORAGE_KEYS.ROADMAP),
    weeklyPlan: g.weeklyPlan || getStorage<SevenDayPlan>(STORAGE_KEYS.WEEKLY_PLAN),
    latestReview: g.latestReview || null,

    isLoggedIn: !!token,
    hasBusinessInfo: !!businessId,
    hasDiagnosis: !!diagnosisId,
    hasPlan: !!planId,
    hasReview: !!reviewId,
  }
}

export const userInfoBehavior = Behavior({
  data: {
    userInfo: null,
    businessInfo: null,
    currentPhase: null,
    currentWeek: null,
    diagnosisResult: null,
    currentRoadmap: null,
    weeklyPlan: null,
    latestReview: null,
    isLoggedIn: false,
    hasBusinessInfo: false,
    hasDiagnosis: false,
    hasPlan: false,
    hasReview: false,
  } as UserInfoBehaviorData,

  lifetimes: {
    attached() {
      ;(this as any).syncUserInfo()
    },
  },

  pageLifetimes: {
    show() {
      // 页面每次显示时刷新，避免切换回来后数据陈旧
      try {
        ;(this as any).syncUserInfo()
      } catch {
        /* ignore */
      }
    },
  },

  methods: {
    /** 把 globalData/storage 同步到当前 page/component 的 data */
    syncUserInfo(this: any) {
      const latest = _pickGlobal()
      this.setData(latest)
    },

    /** 从后端重新拉 businessInfo 并同步 globalData + storage */
    async refreshBusinessInfo(this: any) {
      try {
        const app = getApp<IAppOption>()
        const bizId =
          getStorage<string>(STORAGE_KEYS.BUSINESS_ID) ||
          app?.globalData?.businessId
        if (!bizId) return

        const { get } = await import('../api/request')
        const biz = await get<any>(`/business/info`)
        if (!biz) return

        // 同步 globalData
        if (app?.globalData) {
          app.globalData.businessInfo = biz
          app.globalData.currentPhase = biz.current_phase ?? null
          app.globalData.currentWeek = biz.current_week ?? null
        }
        // 同步 storage
        try {
          const { setStorage } = await import('../utils/storage')
          setStorage(STORAGE_KEYS.BUSINESS_INFO, biz)
        } catch {
          /* ignore */
        }
        ;(this as any).syncUserInfo()
      } catch (err) {
        console.warn('[behavior] refreshBusinessInfo failed:', err)
      }
    },

    /** 清除登录态 → 跳转 onboarding */
    clearAuth(this: any) {
      try {
        TokenStorage.clear()
        const storageMod = require('../utils/storage')
        storageMod.clearAllStorage(false)
        const removeStorage = storageMod.removeStorage
        removeStorage(STORAGE_KEYS.AUTH_TOKEN)
        const app = getApp<IAppOption>()
        if (app?.resetAll) app.resetAll()
        wx.reLaunch({ url: '/pages/onboarding/index' })
      } catch {
        /* ignore */
      }
    },
  } as UserInfoBehaviorMethods & ThisType<any>,
})

export default userInfoBehavior
