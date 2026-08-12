"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const auth_1 = require("../../utils/auth");
Page({
    data: {
        logging: false,
    },
    onLoad() {
        // 已登录则直接进入对话
        if ((0, auth_1.isLoggedIn)()) {
            wx.switchTab({ url: '/pages/chat/index' });
        }
    },
    async onLogin() {
        if (this.data.logging)
            return;
        this.setData({ logging: true });
        try {
            const res = await (0, auth_1.ensureLogin)(false);
            if (res && res.token) {
                wx.switchTab({ url: '/pages/chat/index' });
            }
            else {
                wx.showToast({ title: '登录失败，请重试', icon: 'none' });
            }
        }
        catch (e) {
            wx.showToast({ title: '登录失败，请检查网络', icon: 'none' });
        }
        finally {
            this.setData({ logging: false });
        }
    },
});
