"use strict";
/**
 * 看板页（阶段四 · 数据闭环入口 + 季度进度）
 *
 * 在原有「综合健康度 / 五维雷达 / 今日任务」基础上补齐：
 *   1. 季度进度条（calculateQuarterProgress + weekToPhase）→ 看清自己在 12 周里的位置；
 *   2. 业务数据上传入口（uploadMetrics）→ 选 CSV / 截图上传，后端安全解析并回吐 KPI，
 *      为周末「复盘闭环」提供真实数据燃料。
 */
Object.defineProperty(exports, "__esModule", { value: true });
const index_1 = require("../../store/index");
const constants_1 = require("../../utils/constants");
const date_1 = require("../../utils/date");
const loops_1 = require("../../api/loops");
const error_1 = require("../../utils/error");
const DIM_LABELS = {
    positioning: '定位',
    product: '产品',
    channel: '渠道',
    content: '内容',
    conversion: '转化',
    service: '服务',
    repurchase: '复购',
};
Page({
    data: {
        profile: null,
        radarLabels: ['定位', '产品', '渠道', '内容', '转化'],
        radarValues: [],
        overallScore: 0,
        weekCompletion: 0,
        todayTasks: [],
        hasData: false,
        currentWeek: 0,
        totalWeeks: date_1.QUARTER_TOTAL_WEEKS,
        quarterProgress: 0,
        phaseName: '',
        phaseIndex: 0,
        uploading: false,
        lastKpi: null,
        mergedNumbers: {},
        hasMerged: false,
    },
    _unsub: undefined,
    onLoad() {
        const unsub = (0, index_1.bindStore)(this, (s) => this.derive(s.profile, s.todos));
        this._unsub = unsub;
    },
    onUnload() {
        if (this._unsub)
            this._unsub();
    },
    /** 从 store 派生看板展示数据 */
    derive(profile, todos) {
        const dims = (profile === null || profile === void 0 ? void 0 : profile.dimension_scores) || {};
        const labels = [];
        const values = [];
        Object.keys(dims).forEach((k) => {
            labels.push(DIM_LABELS[k] || k);
            values.push(Number(dims[k]) || 0);
        });
        // 今日任务（按日期匹配今天）
        const today = this.todayStr();
        const todayTasks = (todos || []).filter((t) => t.date === today);
        // 本周完成率
        const total = (todos || []).length;
        const done = (todos || []).filter((t) => t.status === constants_1.TASK_STATUS.DONE).length;
        const weekCompletion = total ? Math.round((done / total) * 100) : 0;
        // 阶段四：季度进度
        const cw = (profile === null || profile === void 0 ? void 0 : profile.current_week) || 0;
        const phase = (0, date_1.weekToPhase)(cw);
        return {
            profile,
            radarLabels: labels.length ? labels : ['定位', '产品', '渠道', '内容', '转化'],
            radarValues: values,
            overallScore: (profile === null || profile === void 0 ? void 0 : profile.overall_score) || 0,
            weekCompletion,
            todayTasks,
            hasData: !!(profile || total > 0),
            currentWeek: cw,
            totalWeeks: date_1.QUARTER_TOTAL_WEEKS,
            quarterProgress: (0, date_1.calculateQuarterProgress)(cw),
            phaseName: phase ? phase.name : '',
            phaseIndex: phase ? phase.index : 0,
        };
    },
    todayStr() {
        const d = new Date();
        const m = `${d.getMonth() + 1}`.padStart(2, '0');
        const day = `${d.getDate()}`.padStart(2, '0');
        return `${d.getFullYear()}-${m}-${day}`;
    },
    onTaskToggle(e) {
        const id = e.detail.id;
        const todos = index_1.store.getState().todos.map((t) => t.id === id
            ? Object.assign(Object.assign({}, t), { status: t.status === constants_1.TASK_STATUS.DONE ? constants_1.TASK_STATUS.PENDING : constants_1.TASK_STATUS.DONE }) : t);
        index_1.store.setTodos(todos);
    },
    /** 上传业务数据 → 后端解析 → 回吐 KPI */
    onUpload() {
        var _a;
        if (this.data.uploading)
            return;
        const businessId = ((_a = index_1.store.getState().profile) === null || _a === void 0 ? void 0 : _a.business_id) || '';
        wx.chooseMessageFile({
            count: 1,
            type: 'file',
            success: (res) => {
                const file = res.tempFiles && res.tempFiles[0];
                if (!file)
                    return;
                this.setData({ uploading: true });
                wx.showLoading({ title: '解析数据中…', mask: true });
                (0, loops_1.uploadMetrics)(file.path, businessId)
                    .then((r) => {
                    wx.hideLoading();
                    this.setData({ uploading: false });
                    if (!r.ok) {
                        wx.showToast({ title: r.error || '上传失败', icon: 'none' });
                        return;
                    }
                    this.setData({
                        lastKpi: r.kpi || null,
                        mergedNumbers: r.merged_numbers || {},
                        hasMerged: !!(r.merged_numbers && Object.keys(r.merged_numbers).length),
                    });
                    wx.showToast({ title: '数据已同步', icon: 'success' });
                })
                    .catch((err) => {
                    wx.hideLoading();
                    this.setData({ uploading: false });
                    (0, error_1.showErrorToast)((0, error_1.classifyError)(err));
                });
            },
            fail: () => {
                // 用户取消选择，静默
            },
        });
    },
    goChat() {
        wx.switchTab({ url: '/pages/chat/index' });
    },
    goPlan() {
        wx.navigateTo({ url: '/pages/detail/plan-detail/index' });
    },
    goReview() {
        wx.navigateTo({ url: '/pages/detail/review-detail/index' });
    },
});
