"use strict";
/**
 * 计划详情页（阶段四 · 计划闭环）
 *
 * 两种形态自动切换：
 *   A. 计划模式 —— store.plan 存在时，渲染可交互的 7 天计划：
 *      逐条微调标题/时段 → 保存到后端 → 「确认并排期」自动落库为日程
 *   B. 进度模式 —— 只有 todos（已排期）时，按天展示执行进度
 *
 * 这是「制定方案 → 执行跟踪」的衔接节点：确认动作会把计划变成日程。
 */
Object.defineProperty(exports, "__esModule", { value: true });
const index_1 = require("../../../store/index");
const constants_1 = require("../../../utils/constants");
const loops_1 = require("../../../api/loops");
const error_1 = require("../../../utils/error");
const DAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
Page({
    data: {
        days: [],
        hasData: false,
        overall: 0,
        doneCount: 0,
        totalCount: 0,
        planMode: false,
        plan: null,
        planDays: [],
        planTheme: '',
        planGoals: [],
        weekNumber: 0,
        phaseName: '',
        confirmed: false,
        pendingEdits: 0,
        submitting: false,
    },
    _unsub: undefined,
    /** 累积的微调项，保存时一次性提交 */
    _edits: [],
    onLoad() {
        const unsub = (0, index_1.bindStore)(this, (s) => {
            const progress = this.build(s.todos);
            const planView = this.buildPlan(s.plan);
            return Object.assign(Object.assign({}, progress), planView);
        });
        this._unsub = unsub;
    },
    onUnload() {
        if (this._unsub)
            this._unsub();
    },
    // ===================== 进度模式 =====================
    build(todos) {
        const list = todos || [];
        const map = new Map();
        list.forEach((t) => {
            const idx = t.day_index || 0;
            if (!map.has(idx)) {
                map.set(idx, { day_index: idx, day_name: t.day_name || '', date: t.date || '', percent: 0, tasks: [] });
            }
            map.get(idx).tasks.push(t);
        });
        const days = Array.from(map.values())
            .sort((a, b) => a.day_index - b.day_index)
            .map((d) => {
            const total = d.tasks.length;
            const done = d.tasks.filter((t) => t.status === constants_1.TASK_STATUS.DONE).length;
            return Object.assign(Object.assign({}, d), { percent: total ? Math.round((done / total) * 100) : 0 });
        });
        const total = list.length;
        const done = list.filter((t) => t.status === constants_1.TASK_STATUS.DONE).length;
        return {
            days,
            hasData: total > 0,
            overall: total ? Math.round((done / total) * 100) : 0,
            doneCount: done,
            totalCount: total,
        };
    },
    // ===================== 计划模式 =====================
    buildPlan(plan) {
        if (!plan || !Array.isArray(plan.days) || plan.days.length === 0) {
            return { planMode: false, plan: null, planDays: [] };
        }
        const planDays = plan.days.map((d, i) => {
            var _a;
            return (Object.assign(Object.assign({}, d), { day_index: (_a = d.day_index) !== null && _a !== void 0 ? _a : i + 1, day_name: d.day_name || DAY_NAMES[i % 7], tasks: (d.tasks || []).map((t, ti) => (Object.assign(Object.assign({}, t), { id: t.id || `d${i + 1}t${ti}` }))) }));
        });
        return {
            planMode: true,
            plan,
            planDays,
            planTheme: plan.theme || plan.focus || '',
            planGoals: plan.goals || [],
            weekNumber: plan.week_number || 0,
            phaseName: plan.phase_name || '',
            confirmed: plan.status === 'confirmed',
        };
    },
    /** 点击任务标题 → 弹窗改写（微调计划） */
    onEditTitle(e) {
        const { dayIndex, taskIndex } = e.currentTarget.dataset;
        const day = this.data.planDays.find((d) => d.day_index === Number(dayIndex));
        if (!day)
            return;
        const task = day.tasks[Number(taskIndex)];
        if (!task)
            return;
        wx.showModal({
            title: '修改任务',
            editable: true,
            placeholderText: '输入新的任务描述',
            content: task.title || '',
            success: (res) => {
                if (!res.confirm)
                    return;
                const nextTitle = (res.content || '').trim();
                if (!nextTitle || nextTitle === task.title)
                    return;
                this.applyLocalEdit(Number(dayIndex), Number(taskIndex), { title: nextTitle });
            },
        });
    },
    /** 点击时段 → 修改执行时间 */
    onEditSlot(e) {
        const { dayIndex, taskIndex } = e.currentTarget.dataset;
        const day = this.data.planDays.find((d) => d.day_index === Number(dayIndex));
        if (!day)
            return;
        const task = day.tasks[Number(taskIndex)];
        if (!task)
            return;
        wx.showModal({
            title: '修改执行时段',
            editable: true,
            placeholderText: '例如 09:00-09:30',
            content: task.time_slot || '',
            success: (res) => {
                if (!res.confirm)
                    return;
                const next = (res.content || '').trim();
                if (!next || next === task.time_slot)
                    return;
                this.applyLocalEdit(Number(dayIndex), Number(taskIndex), { time_slot: next });
            },
        });
    },
    /** 本地先改（即时反馈），同时记入待提交队列 */
    applyLocalEdit(dayIndex, taskIndex, patch) {
        const planDays = this.data.planDays.map((d) => {
            if (d.day_index !== dayIndex)
                return d;
            const tasks = d.tasks.slice();
            tasks[taskIndex] = Object.assign(Object.assign({}, tasks[taskIndex]), patch);
            return Object.assign(Object.assign({}, d), { tasks });
        });
        this.setData({ planDays });
        // 合并同一任务的多次修改
        const existing = this._edits.find((x) => x.day_index === dayIndex && x.task_index === taskIndex);
        if (existing) {
            Object.assign(existing, patch);
        }
        else {
            this._edits.push(Object.assign({ day_index: dayIndex, task_index: taskIndex }, patch));
        }
        this.setData({ pendingEdits: this._edits.length });
        // 同步回 store，保证退出页面后修改不丢
        const plan = this.data.plan;
        if (plan)
            index_1.store.setPlan(Object.assign(Object.assign({}, plan), { days: planDays }));
    },
    /** 保存微调 → 写回后端 days JSON，并作为负反馈参与策略学习 */
    onSaveEdits() {
        const plan = this.data.plan;
        if (!plan || !plan.id || this._edits.length === 0)
            return;
        this.setData({ submitting: true });
        (0, loops_1.editPlan)(plan.id, this._edits)
            .then((res) => {
            this.setData({ submitting: false });
            if (!res.ok) {
                wx.showToast({ title: res.error || '保存失败', icon: 'none' });
                return;
            }
            // 用户改了计划 = 对原方案不满意，记一次负反馈让下次推荐更贴合
            (0, loops_1.submitFeedback)({
                targetType: 'plan',
                targetId: plan.id,
                rating: -1,
                comment: `用户微调了 ${this._edits.length} 项任务`,
                businessId: plan.business_id,
            }).catch(() => { });
            this._edits = [];
            this.setData({ pendingEdits: 0 });
            wx.showToast({ title: '已保存微调', icon: 'success' });
        })
            .catch((err) => {
            this.setData({ submitting: false });
            (0, error_1.showErrorToast)((0, error_1.classifyError)(err));
        });
    },
    /** 确认计划 → 后端自动排期落库 → 跳日程页 */
    onConfirm() {
        const plan = this.data.plan;
        if (!plan || !plan.id) {
            wx.showToast({ title: '计划缺少 ID，请重新生成', icon: 'none' });
            return;
        }
        if (this._edits.length > 0) {
            wx.showModal({
                title: '还有未保存的微调',
                content: '要先保存修改再确认排期吗？',
                confirmText: '先保存',
                cancelText: '直接确认',
                success: (res) => {
                    if (res.confirm) {
                        this.onSaveEdits();
                    }
                    else {
                        this.doConfirm(plan);
                    }
                },
            });
            return;
        }
        this.doConfirm(plan);
    },
    doConfirm(plan) {
        this.setData({ submitting: true });
        wx.showLoading({ title: '排期中…', mask: true });
        (0, loops_1.confirmPlan)(plan.id)
            .then((res) => {
            wx.hideLoading();
            this.setData({ submitting: false });
            if (!res.ok) {
                wx.showToast({ title: '确认失败，请重试', icon: 'none' });
                return;
            }
            index_1.store.setPlan(Object.assign(Object.assign({}, plan), { status: 'confirmed' }));
            this.setData({ confirmed: true });
            // 拉回带真实 id 的 todos，日程页打卡才能落库
            return (0, loops_1.getSchedule)(plan.business_id).then((sr) => {
                if (sr && sr.ok && Array.isArray(sr.todos)) {
                    index_1.store.setTodosFromBackend(sr.todos);
                }
                wx.showToast({ title: `已排期 ${res.schedule.length} 项`, icon: 'success' });
                setTimeout(() => wx.switchTab({ url: '/pages/schedule/index' }), 900);
            });
        })
            .catch((err) => {
            wx.hideLoading();
            this.setData({ submitting: false });
            (0, error_1.showErrorToast)((0, error_1.classifyError)(err));
        });
    },
    /** 对计划整体不满意 → 重新生成一版 */
    onRegenerate() {
        const plan = this.data.plan;
        if (!plan || !plan.id)
            return;
        wx.showModal({
            title: '重新生成计划',
            content: '将结合你的历史反馈重新出一版 7 天计划，当前微调会被覆盖。',
            success: (res) => {
                if (!res.confirm)
                    return;
                wx.showLoading({ title: '生成中…', mask: true });
                (0, loops_1.submitFeedback)({
                    targetType: 'plan',
                    targetId: plan.id,
                    rating: -1,
                    comment: '用户要求重新生成计划',
                    businessId: plan.business_id,
                }).catch(() => { });
                (0, loops_1.regeneratePlan)(plan.id)
                    .then((r) => {
                    wx.hideLoading();
                    if (!r.ok || !r.plan) {
                        wx.showToast({ title: r.error || '生成失败', icon: 'none' });
                        return;
                    }
                    this._edits = [];
                    index_1.store.setPlan(r.plan);
                    this.setData({ pendingEdits: 0, confirmed: false });
                    wx.showToast({ title: '已生成新计划', icon: 'success' });
                })
                    .catch((err) => {
                    wx.hideLoading();
                    (0, error_1.showErrorToast)((0, error_1.classifyError)(err));
                });
            },
        });
    },
    // ===================== 进度模式交互 =====================
    onTaskToggle(e) {
        const id = e.detail.id;
        index_1.store.toggleTodo(id);
    },
    goChat() {
        wx.switchTab({ url: '/pages/chat/index' });
    },
    goSchedule() {
        wx.switchTab({ url: '/pages/schedule/index' });
    },
    /** 分享计划 */
    onShareAppMessage() {
        const theme = this.data.planTheme || '我的营销执行计划';
        return {
            title: `【7天营销计划】${theme}`,
            path: '/pages/chat/index',
        };
    },
});
