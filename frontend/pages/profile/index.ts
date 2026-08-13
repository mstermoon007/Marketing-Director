/**
 * 个人中心页（阶段五新增）
 *
 * 聚合展示当前用户：
 *   - 名下企业列表（可切换当前企业）
 *   - 诊断 / 计划 / 复盘的历史数量
 *   - 退出登录（加固：清空会话态 + 本地业务数据，避免下一位用户读到泄漏数据）
 */

import { store } from '../../store/index'
import { getMyBusinesses, getDiagnosisHistory, getPlanHistory, getReviewHistory } from '../../api/business'
import { logout as doLogout } from '../../utils/auth'
import { getStorage, STORAGE_KEYS } from '../../utils/storage'

interface ProfileData {
  loading: boolean
  userId: string
  businesses: Array<{
    id: string
    business_name: string
    industry: string
    city: string
    created_at: string | null
  }>
  activeBusinessId: string
  counts: { diagnosis: number; plan: number; review: number }
}

Page<ProfileData, Record<string, any>>({
  data: {
    loading: true,
    userId: '',
    businesses: [],
    activeBusinessId: '',
    counts: { diagnosis: 0, plan: 0, review: 0 },
  } as ProfileData,

  onShow(): void {
    const userId = getStorage<{ user_id: string }>(STORAGE_KEYS.USER_INFO)?.user_id || ''
    this.setData({
      userId,
      activeBusinessId: store.getState().currentBusinessId,
    })
    this.loadData()
  },

  /** 拉取名下企业 + 各历史数量，并同步到全局 store（看板/上传复用）。 */
  async loadData(): Promise<void> {
    this.setData({ loading: true })
    try {
      const [biz, diag, plan, review] = await Promise.all([
        getMyBusinesses(),
        getDiagnosisHistory(),
        getPlanHistory(),
        getReviewHistory(),
      ])
      const list = (biz.list || []) as ProfileData['businesses']
      // 若本地尚未选定企业，默认选中最近创建的一家
      let active = store.getState().currentBusinessId
      if (!active && list.length) active = list[0].id
      if (active) store.setCurrentBusinessId(active)
      store.setBusinesses(list)
      this.setData({
        businesses: list,
        activeBusinessId: active,
        counts: {
          diagnosis: diag.total || 0,
          plan: plan.total || 0,
          review: review.total || 0,
        },
      })
    } catch (e) {
      console.warn('[profile] 加载个人数据失败：', e)
      wx.showToast({ title: '加载失败，请重试', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  onSelectBusiness(e: WechatMiniprogram.TouchEvent): void {
    const id = e.detail.id as string
    store.setCurrentBusinessId(id)
    this.setData({ activeBusinessId: id })
  },

  onLogout(): void {
    wx.showModal({
      title: '退出登录',
      content: '将清除本机所有业务数据，确定退出？',
      success: (res) => {
        if (res.confirm) {
          doLogout(true)
        }
      },
    })
  },
})
