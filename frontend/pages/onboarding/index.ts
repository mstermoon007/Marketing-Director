import { ensureLogin, isLoggedIn } from '../../utils/auth'

interface OnboardData {
  logging: boolean
}

Page<OnboardData, Record<string, any>>({
  data: {
    logging: false,
  } as OnboardData,

  onLoad(): void {
    // 已登录则直接进入对话
    if (isLoggedIn()) {
      wx.switchTab({ url: '/pages/chat/index' })
    }
  },

  async onLogin(): Promise<void> {
    if (this.data.logging) return
    this.setData({ logging: true })
    try {
      const res = await ensureLogin(false)
      if (res && res.token) {
        wx.switchTab({ url: '/pages/chat/index' })
      } else {
        wx.showToast({ title: '登录失败，请重试', icon: 'none' })
      }
    } catch (e) {
      wx.showToast({ title: '登录失败，请检查网络', icon: 'none' })
    } finally {
      this.setData({ logging: false })
    }
  },
})
