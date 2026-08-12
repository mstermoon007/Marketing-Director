"use strict";
/**
 * 日程页（阶段四 · 执行跟踪 + 复盘触发）
 *
 * 在原有「按天任务列表」基础上补齐闭环能力：
 *   1. 顶部 7 天日历条（generateWeekDates）→ 一眼看清本周排布与每日完成度；
 *   2. 勾选任务 → 本地即时翻转 + 后端 checkinTodo 落库（供复盘 Agent 读取真实执行）；
 *   3. 周末自动浮现「本周复盘」CTA → triggerReview → 直接跳复盘详情，闭环到「提升」。
 */
Object.defineProperty(exports, "__esModule", { value: true });
const index_1 = require("../../store/index");
const constants_1 = require("../../utils/constants");
const date_1 = require("../../utils/date");
const loops_1 = require("../../api/loops");
const error_1 = require("../../utils/error");
Page({
    data: {
        groups: [],
        hasData: false,
        doneCount: 0,
        totalCount: 0,
        week: [],
        weekRange: '',
        showReviewCta: false,
        reviewing: false,
    },
    _unsub: undefined,
    onLoad() {
        const unsub = (0, index_1.bindStore)(this, (s) => { var _a; return this.buildAll(s.todos, (_a = s.profile) === null || _a === void 0 ? void 0 : _a.business_id); });
        this._unsub = unsub;
    },
    onShow() {
        // 周末判定 / 今天高亮依赖实时日期，进入页面时强制刷新一次
        this.refresh();
    },
    onUnload() {
        if (this._unsub)
            this._unsub();
    },
    refresh() {
        var _a;
        const s = index_1.store.getState();
        this.setData(this.buildAll(s.todos, (_a = s.profile) === null || _a === void 0 ? void 0 : _a.business_id));
    },
    buildAll(todos, businessId) {
        const groups = this.buildGroups(todos);
        const week = this.buildWeek(todos);
        void businessId;
        return Object.assign(Object.assign({}, groups), { week, weekRange: week.length ? `${(0, date_1.formatShortDate)(week[0].date)} - ${(0, date_1.formatShortDate)(week[6].date)}` : '', showReviewCta: this.isReviewDay() });
    },
    buildGroups(todos) {
        const list = todos || [];
        const map = new Map();
        list.forEach((t) => {
            const idx = t.day_index || 0;
            if (!map.has(idx)) {
                const date = t.date || '';
                map.set(idx, {
                    day_index: idx,
                    day_name: t.day_name || '',
                    date,
                    dateLabel: date ? `${(0, date_1.formatShortDate)(date)} ${this.weekdayOf(date)}` : '',
                    isToday: date ? this.isToday(date) : false,
                    doneCount: 0,
                    tasks: [],
                });
            }
            map.get(idx).tasks.push(t);
        });
        for (const g of map.values()) {
            g.doneCount = g.tasks.filter((t) => t.status === constants_1.TASK_STATUS.DONE).length;
        }
        const groups = Array.from(map.values()).sort((a, b) => a.day_index - b.day_index);
        const total = list.length;
        const done = list.filter((t) => t.status === constants_1.TASK_STATUS.DONE).length;
        return { groups, hasData: total > 0, doneCount: done, totalCount: total };
    },
    /** 周历：以今天所在周周一为起点，按日期聚合完成度 */
    buildWeek(todos) {
        const days = (0, date_1.generateWeekDates)();
        const list = todos || [];
        return days.map((d) => {
            const dayTodos = list.filter((t) => t.date === d.date);
            const total = dayTodos.length;
            const done = dayTodos.filter((t) => t.status === constants_1.TASK_STATUS.DONE).length;
            return {
                date: d.date,
                weekday: d.weekday,
                isToday: d.isToday,
                done,
                total,
                rate: total ? Math.round((done / total) * 100) : 0,
            };
        });
    },
    weekdayOf(date) {
        const d = new Date(date);
        if (isNaN(d.getTime()))
            return '';
        return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()];
    },
    isToday(date) {
        const d = new Date(date);
        const now = new Date();
        const pad = (n) => `${n}`.padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` ===
            `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    },
    /** 周六(汇总日)/周日 → 显示复盘横幅 */
    isReviewDay() {
        const wd = new Date().getDay();
        return wd === 6 || wd === 0;
    },
    /** 勾选任务 → 本地翻转 + 后端打卡（best-effort） */
    onTaskToggle(e) {
        const id = e.detail.id;
        if (!id)
            return;
        index_1.store.toggleTodo(id);
        const t = index_1.store.getState().todos.find((x) => x.id === id);
        if (t && t.id) {
            (0, loops_1.checkinTodo)({ todoId: t.id, status: t.status }).catch(() => { });
        }
    },
    /** 本周复盘 → 触发后端复盘 → 跳详情 */
    onReviewTap() {
        if (this.data.reviewing)
            return;
        const prof = index_1.store.getState().profile;
        const businessId = (prof === null || prof === void 0 ? void 0 : prof.business_id) || '';
        const weekNumber = (prof === null || prof === void 0 ? void 0 : prof.current_week) || 0;
        this.setData({ reviewing: true });
        wx.showLoading({ title: '生成复盘…', mask: true });
        (0, loops_1.triggerReview)({ businessId, weekNumber })
            .then((res) => {
            wx.hideLoading();
            this.setData({ reviewing: false });
            if (!res.ok) {
                wx.showToast({ title: res.error || '复盘失败', icon: 'none' });
                return;
            }
            if (res.needs_upload) {
                wx.showModal({
                    title: '先上传本周数据',
                    content: '复盘需要基于业务数据。去「看板」上传本周 CSV 或数据截图，再回来复盘。',
                    confirmText: '去上传',
                    success: (r) => {
                        if (r.confirm)
                            wx.switchTab({ url: '/pages/dashboard/index' });
                    },
                });
                return;
            }
            if (res.review) {
                index_1.store.setReview(res.review);
                wx.navigateTo({ url: `/pages/detail/review-detail/index?id=${res.review.id}` });
            }
            else {
                wx.showToast({ title: '复盘已生成', icon: 'success' });
            }
        })
            .catch((err) => {
            wx.hideLoading();
            this.setData({ reviewing: false });
            (0, error_1.showErrorToast)((0, error_1.classifyError)(err));
        });
    },
    goChat() {
        wx.switchTab({ url: '/pages/chat/index' });
    },
});
