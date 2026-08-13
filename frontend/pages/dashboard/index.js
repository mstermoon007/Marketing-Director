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
const storage_1 = require("../../utils/storage");
const DIM_LABELS = {
    positioning: '定位',
    product: '产品',
    channel: '渠道',
    content: '内容',
    conversion: '转化',
    service: '服务',
    repurchase: '复购',
};
/** 雷达图维度固定顺序（避免 Object.keys 无序导致每次进入顺序抖动）。 */
const DIM_ORDER = [
    'positioning',
    'product',
    'channel',
    'content',
    'conversion',
    'service',
    'repurchase',
];
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
        this._restoreKpi();
    },
    onShow() {
        // 从其它页面（如对话里完成诊断/排期）返回时，重新派生并恢复上次 KPI 回显
        this.derive(index_1.store.getState().profile, index_1.store.getState().todos);
        this._restoreKpi();
    },
    onUnload() {
        if (this._unsub)
            this._unsub();
    },
    /** 从本地缓存恢复最近一次上传解析出的 KPI（跨页面/重启不丢失）。 */
    _restoreKpi() {
        const cached = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.DASHBOARD_KPI);
        if (cached) {
            this.setData({
                lastKpi: cached.lastKpi || null,
                mergedNumbers: cached.mergedNumbers || {},
                hasMerged: !!cached.hasMerged,
            });
        }
    },
    /** 持久化最近一次上传解析结果，供下次进入看板回显。 */
    _persistKpi(lastKpi, mergedNumbers, hasMerged) {
        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.DASHBOARD_KPI, { lastKpi, mergedNumbers, hasMerged });
    },
    /** 从 store 派生看板展示数据 */
    derive(profile, todos) {
        const dims = (profile === null || profile === void 0 ? void 0 : profile.dimension_scores) || {};
        // 固定维度顺序，未出现在 DIM_ORDER 的维度追加在末尾（兼容未来扩展）
        const keys = [...DIM_ORDER, ...Object.keys(dims).filter((k) => !DIM_ORDER.includes(k))];
        const labels = [];
        const values = [];
        keys.forEach((k) => {
            if (!(k in dims))
                return;
            labels.push(DIM_LABELS[k] || k);
            values.push(Number(dims[k]) || 0);
        });
        // 今日任务（按日期匹配今天）
        const today = this.todayStr();
        const todayTasks = (todos || []).filter((t) => t.date === today);
        // 本周完成率：仅统计「本周（周一~周日）」内的待办，避免跨周累计失真
        const { start, end } = this.weekRange();
        const weekTodos = (todos || []).filter((t) => t.date && t.date >= start && t.date <= end);
        const total = weekTodos.length;
        const done = weekTodos.filter((t) => t.status === constants_1.TASK_STATUS.DONE).length;
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
    /** 本周（周一 00:00 ~ 周日 23:59）的日期区间，用于按周聚合统计。 */
    weekRange() {
        const now = new Date();
        const dow = now.getDay() || 7; // 周日=0 归为 7，方便算周一偏移
        const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (dow - 1));
        const sunday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (dow - 1) + 6);
        const fmt = (d) => {
            const m = `${d.getMonth() + 1}`.padStart(2, '0');
            const day = `${d.getDate()}`.padStart(2, '0');
            return `${d.getFullYear()}-${m}-${day}`;
        };
        return { start: fmt(monday), end: fmt(sunday) };
    },
    todayStr() {
        const d = new Date();
        const m = `${d.getMonth() + 1}`.padStart(2, '0');
        const day = `${d.getDate()}`.padStart(2, '0');
        return `${d.getFullYear()}-${m}-${day}`;
    },
    onTaskToggle(e) {
        const id = e.detail.id;
        // 先更新本地状态（即时反馈），再上报后端打卡（闭环：完成态反馈至复盘 Agent）
        index_1.store.toggleTodo(id);
        const todo = index_1.store.getState().todos.find((t) => t.id === id);
        const status = (todo === null || todo === void 0 ? void 0 : todo.status) === constants_1.TASK_STATUS.DONE ? 'done' : 'pending';
        (0, loops_1.checkinTodo)({ todoId: id, status }).catch((err) => {
            console.warn('[dashboard] 任务打卡上报失败（本地已更新）：', err);
        });
    },
    /** 上传业务数据 → 后端解析 → 回吐 KPI */
    onUpload() {
        var _a;
        if (this.data.uploading)
            return;
        // 优先用当前企业 ID（对话中已建立），回退到画像里携带的 business_id
        const businessId = index_1.store.getState().currentBusinessId || ((_a = index_1.store.getState().profile) === null || _a === void 0 ? void 0 : _a.business_id) || '';
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
                    this._persistKpi(r.kpi || null, r.merged_numbers || {}, !!(r.merged_numbers && Object.keys(r.merged_numbers).length));
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
