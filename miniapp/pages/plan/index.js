"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * 7天任务卡片页（周视图）
 */
const request_1 = require("../../api/request");
Page({
    data: {
        loading: true,
        plan: null,
        metrics: [],
        activeDay: 0,
        activeDayData: null,
    },
    onLoad(options) {
        const diagnosisId = options.diagnosis_id || getApp().globalData.diagnosisId;
        if (diagnosisId) {
            this.loadOrCreatePlan(diagnosisId);
        }
        else {
            this.setData({ loading: false });
        }
    },
    onShow() {
        const plan = this.data.plan;
        if (plan) {
            this.restoreTaskState();
        }
    },
    async loadOrCreatePlan(diagnosisId) {
        this.setData({ loading: true });
        try {
            const plan = await (0, request_1.post)(`/execution/${diagnosisId}`, { start_date: '' });
            this.renderPlan(plan);
        }
        catch (err) {
            try {
                const plan = await (0, request_1.get)(`/execution/${diagnosisId}`);
                this.renderPlan(plan);
            }
            catch (_a) {
                wx.showToast({ title: err.message || '生成失败', icon: 'none' });
                this.setData({ loading: false });
            }
        }
    },
    renderPlan(plan) {
        const app = getApp();
        app.saveState('planId', plan.id);
        const metrics = plan.key_metrics ? Object.keys(plan.key_metrics) : [];
        const activeDayData = plan.days.length > 0 ? plan.days[0] : null;
        this.setData({
            plan,
            metrics,
            activeDay: 0,
            activeDayData,
            loading: false,
        });
        this.restoreTaskState();
    },
    restoreTaskState() {
        const plan = this.data.plan;
        if (!plan)
            return;
        const key = `plan_${plan.id}_tasks`;
        const saved = wx.getStorageSync(key);
        if (saved) {
            const updatedPlan = Object.assign({}, plan);
            const states = JSON.parse(saved);
            updatedPlan.days.forEach((day, di) => {
                day.tasks.forEach((task, ti) => {
                    const taskKey = `${di}_${ti}`;
                    task.done = states[taskKey] || false;
                });
            });
            this.setData({
                plan: updatedPlan,
                activeDayData: updatedPlan.days[this.data.activeDay] || null,
            });
        }
    },
    saveTaskState() {
        const plan = this.data.plan;
        if (!plan)
            return;
        const states = {};
        plan.days.forEach((day, di) => {
            day.tasks.forEach((task, ti) => {
                states[`${di}_${ti}`] = task.done || false;
            });
        });
        const key = `plan_${plan.id}_tasks`;
        wx.setStorageSync(key, JSON.stringify(states));
    },
    onDayTap(e) {
        const idx = e.currentTarget.dataset.index;
        const plan = this.data.plan;
        if (plan && plan.days[idx]) {
            this.setData({ activeDay: idx, activeDayData: plan.days[idx] });
        }
    },
    onTaskToggle(e) {
        const plan = this.data.plan;
        if (!plan)
            return;
        const taskIndex = e.currentTarget.dataset.index;
        const dayIdx = this.data.activeDay;
        const updatedPlan = Object.assign({}, plan);
        if (updatedPlan.days[dayIdx] && updatedPlan.days[dayIdx].tasks[taskIndex]) {
            const task = updatedPlan.days[dayIdx].tasks[taskIndex];
            task.done = !task.done;
            this.setData({ plan: updatedPlan, activeDayData: updatedPlan.days[dayIdx] || null });
            this.saveTaskState();
        }
    },
    onGoDayDetail() {
        const plan = this.data.plan;
        const dayData = this.data.activeDayData;
        if (!plan || !dayData)
            return;
        const dayIndex = this.data.activeDay;
        const app = getApp();
        app.globalData.currentDayData = dayData;
        app.globalData.currentDayIndex = dayIndex;
        wx.navigateTo({ url: `/pages/plan/day?plan_id=${plan.id}&day_index=${dayIndex}` });
    },
    onStartReview() {
        const plan = this.data.plan;
        if (!plan)
            return;
        wx.navigateTo({ url: `/pages/upload/index?plan_id=${plan.id}` });
    },
    onGenerate() {
        const diagnosisId = getApp().globalData.diagnosisId;
        if (diagnosisId) {
            this.loadOrCreatePlan(diagnosisId);
        }
    },
});
