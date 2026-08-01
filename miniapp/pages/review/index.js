"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * 复盘报告查看页
 */
const request_1 = require("../../api/request");
Page({
    data: {
        loading: true,
        review: null,
        metrics: [],
    },
    onLoad(options) {
        const planId = options.plan_id || getApp().globalData.planId;
        if (planId) {
            this.loadReview(planId);
        }
        else {
            this.setData({ loading: false });
        }
    },
    onShow() {
        if (!this.data.review) {
            const planId = getApp().globalData.planId;
            if (planId) {
                this.loadReview(planId);
            }
        }
    },
    async loadReview(planId) {
        this.setData({ loading: true });
        try {
            const review = await (0, request_1.get)(`/review/${planId}`);
            this.renderReview(review);
        }
        catch (err) {
            wx.showToast({ title: err.message || '加载失败', icon: 'none' });
            this.setData({ loading: false });
        }
    },
    renderReview(review) {
        const metrics = (review.vs_target || []).map((m) => ({
            name: m.metric_name,
            target: m.target,
            actual: m.actual,
            percent: m.target > 0 ? Math.min(100, Math.round((m.actual / m.target) * 100)) : 0,
            achieved: m.achieved,
        }));
        this.setData({ review, metrics, loading: false });
    },
    onRetry() {
        const planId = getApp().globalData.planId;
        if (planId)
            this.loadReview(planId);
    },
    onBackToPlan() {
        wx.switchTab({ url: '/pages/plan/index' });
    },
    onGoUpload() {
        const planId = getApp().globalData.planId;
        if (planId) {
            wx.navigateTo({ url: `/pages/upload/index?plan_id=${planId}` });
        }
    },
});
