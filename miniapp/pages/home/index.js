"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * 工作台首页
 * 展示当前进度和快速入口
 */
const request_1 = require("../../api/request");
const index_1 = require("../../skills/index");
Page({
    data: {
        business: null,
        diagnosis: null,
        plan: null,
        review: null,
        loading: true,
        skillTips: [],
        skillLabel: '',
        skillIcon: '',
    },
    onShow() {
        this.loadAll();
    },
    async loadAll() {
        var _a;
        const app = getApp();
        const { businessId, diagnosisId, planId } = app.globalData;
        this.setData({ loading: true });
        try {
            const results = {};
            if (businessId) {
                try {
                    results.business = await (0, request_1.get)(`/business/${businessId}`);
                    if ((_a = results.business) === null || _a === void 0 ? void 0 : _a.industry) {
                        const skill = (0, index_1.getIndustrySkill)(results.business.industry);
                        results.skillTips = (0, index_1.getDiagnosisTips)(results.business.industry);
                        results.skillLabel = skill.label;
                        results.skillIcon = skill.icon;
                    }
                }
                catch ( /* ignore */_b) { /* ignore */ }
            }
            if (diagnosisId) {
                try {
                    results.diagnosis = await (0, request_1.get)(`/diagnosis/${diagnosisId}`);
                }
                catch ( /* ignore */_c) { /* ignore */ }
            }
            if (planId) {
                try {
                    results.plan = await (0, request_1.get)(`/execution/${planId}`);
                }
                catch ( /* ignore */_d) { /* ignore */ }
            }
            this.setData(Object.assign(Object.assign({}, results), { loading: false }));
        }
        catch (_e) {
            this.setData({ loading: false });
        }
    },
    /** 跳转：填写企业信息 */
    goProfile() {
        wx.navigateTo({ url: '/pages/profile/index' });
    },
    /** 跳转：诊断报告 */
    goDiagnosis() {
        const diagnosisId = getApp().globalData.diagnosisId;
        if (diagnosisId) {
            wx.navigateTo({ url: `/pages/diagnosis/index` });
        }
        else {
            wx.navigateTo({ url: '/pages/profile/index' });
        }
    },
    /** 跳转：执行计划（tabBar） */
    goPlan() {
        wx.switchTab({ url: '/pages/plan/index' });
    },
    /** 跳转：上传截图 */
    goUpload() {
        const planId = getApp().globalData.planId;
        if (planId) {
            wx.navigateTo({ url: `/pages/upload/index` });
        }
        else {
            wx.showToast({ title: '请先生成执行计划', icon: 'none' });
        }
    },
    /** 跳转：复盘报告（tabBar） */
    goReview() {
        wx.switchTab({ url: '/pages/review/index' });
    },
    /** 重新开始 */
    onReset() {
        wx.showModal({
            title: '确认重新开始？',
            content: '将清除所有数据，从头开始填写企业信息',
            success: (res) => {
                if (res.confirm) {
                    const app = getApp();
                    app.resetAll();
                    this.setData({
                        business: null,
                        diagnosis: null,
                        plan: null,
                        review: null,
                    });
                    wx.navigateTo({ url: '/pages/profile/index' });
                }
            },
        });
    },
});
