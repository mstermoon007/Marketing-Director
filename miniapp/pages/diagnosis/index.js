"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * 诊断报告查看页
 */
const request_1 = require("../../api/request");
const index_1 = require("../../skills/index");
Page({
    data: {
        loading: true,
        generating: false,
        report: null,
        scoreList: [],
        skillLabel: '',
        skillIcon: '',
        skillTips: [],
    },
    onLoad(options) {
        const businessId = options.business_id || getApp().globalData.businessId;
        if (businessId) {
            this.loadReport(businessId);
        }
        else {
            this.setData({ loading: false });
        }
    },
    async loadReport(businessId) {
        this.setData({ loading: true });
        try {
            const [report, business] = await Promise.all([
                (0, request_1.get)(`/diagnosis/${businessId}`).catch(() => null),
                (0, request_1.get)(`/business/${businessId}`).catch(() => null),
            ]);
            if (report) {
                this.renderReport(report, (business === null || business === void 0 ? void 0 : business.industry) || '');
            }
            else {
                const newReport = await (0, request_1.post)(`/diagnosis/${businessId}`);
                this.renderReport(newReport, (business === null || business === void 0 ? void 0 : business.industry) || '');
            }
        }
        catch (err) {
            wx.showToast({ title: err.message || '诊断失败', icon: 'none' });
            this.setData({ loading: false });
        }
    },
    renderReport(report, industry) {
        const breakdown = report.score_breakdown || {};
        const colors = ['#e74c3c', '#ff9800', '#fbc02d', '#2196f3', '#4caf50'];
        const scoreList = Object.entries(breakdown).map(([name, score], i) => ({
            name,
            score,
            color: colors[i % colors.length],
        }));
        const skill = (0, index_1.getIndustrySkill)(industry);
        const skillTips = industry ? (0, index_1.getDiagnosisTips)(industry) : [];
        const app = getApp();
        app.saveState('diagnosisId', report.id);
        this.setData({
            report,
            scoreList,
            skillLabel: skill.label,
            skillIcon: skill.icon,
            skillTips,
            loading: false,
        });
    },
    async onGeneratePlan() {
        if (!this.data.report)
            return;
        this.setData({ generating: true });
        try {
            wx.switchTab({ url: '/pages/plan/index' });
        }
        catch (err) {
            wx.showToast({ title: err.message || '跳转失败', icon: 'none' });
        }
        finally {
            this.setData({ generating: false });
        }
    },
    onRetry() {
        this.loadReport(getApp().globalData.businessId);
    },
});
