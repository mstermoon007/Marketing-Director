"use strict";
/**
 * 复盘详情页（阶段四 · 复盘与提升闭环）
 *
 * 展示 AI 周复盘报告：总评 / 指标达成(vs_target) / 做得好 / 待改进 / 下周建议。
 *
 * 闭环落点：用户点击「采纳建议并生成下周计划」→ 调用 applyReview：
 *   后端据建议重新生成下周计划并自动排期 → 前端拉回真实 todos → 跳转日程页。
 * 这一跳完成了「复盘 → 更新计划 → 进入执行」的闭环，无需手动在多个功能间穿梭。
 */
Object.defineProperty(exports, "__esModule", { value: true });
const index_1 = require("../../../store/index");
const loops_1 = require("../../../api/loops");
const error_1 = require("../../../utils/error");
const date_1 = require("../../../utils/date");
Page({
    data: {
        hasData: false,
        review: null,
        summary: '',
        metrics: [],
        whatWorked: [],
        whatDidnt: [],
        suggestions: [],
        businessId: '',
        weekNumber: 0,
        updatedText: '',
        applying: false,
        applied: false,
    },
    _unsub: undefined,
    onLoad() {
        const unsub = (0, index_1.bindStore)(this, (s) => { var _a; return this.build(s.review, (_a = s.profile) === null || _a === void 0 ? void 0 : _a.business_id); });
        this._unsub = unsub;
    },
    onUnload() {
        if (this._unsub)
            this._unsub();
    },
    build(r, businessId) {
        if (!r) {
            return { hasData: false, review: null, metrics: [], whatWorked: [], whatDidnt: [], suggestions: [] };
        }
        return {
            hasData: true,
            review: r,
            summary: r.summary || '',
            metrics: (r.vs_target || []).map((m) => this.metricVM(m)),
            whatWorked: r.what_worked || [],
            whatDidnt: r.what_didnt || [],
            suggestions: r.suggestions || [],
            businessId: businessId || r.business_id || '',
            weekNumber: r.week_number || 0,
            updatedText: r.created_at ? `生成于 ${(0, date_1.formatRelativeTime)(r.created_at)}` : '',
        };
    },
    /** 指标达成率计算 + 配色 */
    metricVM(m) {
        const target = Number(m.target || 0);
        const actual = Number(m.actual || 0);
        const rate = target > 0 ? Math.round((actual / target) * 100) : m.achieved ? 100 : 0;
        const rateColor = rate >= 100 ? '#07c160' : rate >= 70 ? '#ff976a' : '#ee0a24';
        return Object.assign(Object.assign({}, m), { rate, rateColor });
    },
    /** 采纳建议 → 生成下周计划并自动排期 → 跳日程 */
    onApply() {
        const r = this.data.review;
        if (!r || !r.id) {
            wx.showToast({ title: '复盘缺少 ID', icon: 'none' });
            return;
        }
        if (this.data.applying)
            return;
        this.setData({ applying: true });
        wx.showLoading({ title: '生成下周计划…', mask: true });
        (0, loops_1.applyReview)(r.id, this.data.businessId)
            .then((res) => {
            wx.hideLoading();
            this.setData({ applying: false });
            if (!res.ok) {
                wx.showToast({ title: res.error || '采纳失败', icon: 'none' });
                return;
            }
            if (res.plan)
                index_1.store.setPlan(res.plan);
            // 拉回带真实 id 的 todos，日程打卡才能落库
            return (0, loops_1.getSchedule)(this.data.businessId).then((sr) => {
                if (sr && sr.ok && Array.isArray(sr.todos)) {
                    index_1.store.setTodosFromBackend(sr.todos);
                }
                this.setData({ applied: true });
                wx.showToast({ title: '下周计划已排好', icon: 'success' });
                setTimeout(() => wx.switchTab({ url: '/pages/schedule/index' }), 900);
            });
        })
            .catch((err) => {
            wx.hideLoading();
            this.setData({ applying: false });
            (0, error_1.showErrorToast)((0, error_1.classifyError)(err));
        });
    },
    /** 对单条建议点赞/踩，参与策略学习 */
    onRateSuggestion(e) {
        const { idx, rating } = e.currentTarget.dataset;
        const r = this.data.review;
        if (!r)
            return;
        const suggestion = this.data.suggestions[idx];
        if (!suggestion)
            return;
        (0, loops_1.submitFeedback)({
            targetType: 'suggestion',
            targetId: r.id,
            rating: Number(rating),
            comment: suggestion,
            businessId: this.data.businessId,
        }).catch(() => { });
        wx.showToast({ title: Number(rating) > 0 ? '已采纳 👍' : '已记录 👎', icon: 'none' });
    },
    goChat() {
        wx.switchTab({ url: '/pages/chat/index' });
    },
    onShareAppMessage() {
        const w = this.data.weekNumber;
        return {
            title: w ? `第 ${w} 周营销复盘 · 下周建议已生成` : '我的营销周复盘',
            path: '/pages/chat/index',
        };
    },
});
