"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
App({
    globalData: {
        businessId: '',
        diagnosisId: '',
        planId: '',
        reviewId: '',
        apiBase: 'http://localhost:8000/api',
    },
    /** 初始化：从本地缓存恢复全部状态 */
    onLaunch() {
        this.restoreFromStorage();
    },
    /** 从 storage 恢复 */
    restoreFromStorage() {
        const keys = ['businessId', 'diagnosisId', 'planId', 'reviewId'];
        keys.forEach((key) => {
            const val = wx.getStorageSync(key);
            if (val) {
                ;
                this.globalData[key] = val;
            }
        });
    },
    /** 保存单个状态值 */
    saveState(key, value) {
        this.globalData[key] = value;
        wx.setStorageSync(key, value);
    },
    /** 获取状态值 */
    getState(key) {
        return this.globalData[key];
    },
    /** 重置所有状态 */
    resetAll() {
        const keys = ['businessId', 'diagnosisId', 'planId', 'reviewId'];
        keys.forEach((key) => {
            this.globalData[key] = '';
            wx.removeStorageSync(key);
        });
    },
});
