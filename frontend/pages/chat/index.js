"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const auth_1 = require("../../utils/auth");
const index_1 = require("../../store/index");
const agent_1 = require("../../api/agent");
const loops_1 = require("../../api/loops");
const error_1 = require("../../utils/error");
const storage_1 = require("../../utils/storage");
const DEFAULT_QUICK = [
    { label: '🩺 诊断我的生意', prompt: '帮我诊断一下当前生意，找出核心问题' },
    { label: '🗺️ 生成营销计划', prompt: '为我生成未来一周的营销执行计划' },
    { label: '📅 安排本周日程', prompt: '把计划拆解成每天可执行的任务并排好日程' },
    { label: '🔄 复盘本周', prompt: '帮我复盘本周执行情况并给出调整建议' },
];
/**
 * 追问引导：Agent 说「需要更多信息」时，按意图给出可一键补全的示例，
 * 避免用户面对开放式问题卡住（多轮澄清的关键体验）。
 */
const CLARIFY_CHIPS = {
    diagnose: [
        '我在杭州开一家咖啡店，客单价 35，主要靠外卖',
        '我做少儿英语培训，成都，最大痛点是招生难',
        '我是本地家政公司，获客全靠熟人介绍',
    ],
    plan: [
        '先按上面说的生意，帮我出 7 天计划',
        '预算每月 3000 元，团队 2 人，请按这个来排',
    ],
    schedule: [
        '发朋友圈、给老客打电话、拍一条短视频',
        '按上周的计划直接排期',
    ],
    review: ['我这就上传本周数据截图', '本周新增客户 12、咨询量 45、成交 6'],
};
Page({
    data: {
        messages: [],
        agentStatus: { streaming: false, thinking: false, steps: [], intent: undefined },
        profile: null,
        inputText: '',
        attachments: [],
        quickActions: DEFAULT_QUICK,
        toView: '',
        showThinking: true,
        uploading: false,
        clarifyChips: [],
        feedbackMap: {},
    },
    _unsub: undefined,
    _sessionId: '',
    /** 当前会话绑定的企业 ID（由后端 done 事件回传，后续闭环接口都要用） */
    _businessId: '',
    /** 请求序号：每次发起新对话自增，旧流回调若序号不符则丢弃（防竞态） */
    _reqSeq: 0,
    /** 当前有效流的序号；只有 _currentSeq 匹配的回调才允许落状态 */
    _currentSeq: 0,
    /** 状态锁：进行中（含附件上传）禁止重入，避免快速操作消息交错 */
    _locked: false,
    /** 当前在途文本（用于防连点重复发送） */
    _inflightText: '',
    /** 当前流式句柄（用于主动中止旧流） */
    _streamHandle: null,
    /** 当前流占位的 agent 消息 id（精确更新，避免「取最后一条」竞态） */
    _streamMsgId: '',
    onLoad() {
        var _a;
        // 确保登录（失败自动跳 onboarding）
        (0, auth_1.ensureLogin)(true);
        this._sessionId = index_1.store.getState().sessionId || `${this.getUserId()}:default`;
        index_1.store.setSession(this._sessionId);
        const unsub = (0, index_1.bindStore)(this, (s) => ({
            messages: s.messages,
            agentStatus: s.agentStatus,
            profile: s.profile,
            showThinking: s.settings.showThinking,
        }));
        this._unsub = unsub;
        this._businessId = ((_a = index_1.store.getState().profile) === null || _a === void 0 ? void 0 : _a.business_id) || '';
        // 首屏：缓存为空时给一句欢迎语（仅当前会话）
        if (index_1.store.getState().messages.length === 0) {
            index_1.store.addMessage({
                role: 'system',
                content: '你好，我是你的 AI 营销顾问。告诉我你的生意情况，我可以帮你诊断、制定计划、安排日程和复盘。',
            });
        }
        this.scrollToBottom();
    },
    onShow() {
        // 从后台返回：store 订阅已保证数据同步，仅重新定位到底部
        this.scrollToBottom();
    },
    onUnload() {
        this._abortStream();
        if (this._unsub)
            this._unsub();
    },
    getUserId() {
        // 注意：必须走 getStorage（带 TTL 包装），直接 wx.getStorageSync 会拿到 {data,timestamp} 包装对象
        const info = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.USER_INFO);
        return info && info.user_id ? info.user_id : 'local';
    },
    onInput(e) {
        this.setData({ inputText: e.detail.value });
    },
    onQuickSelect(e) {
        const prompt = e.detail.prompt;
        this.setData({ inputText: prompt });
        this.send();
    },
    /** 点击追问引导 chip → 直接作为下一轮输入发出（多轮澄清） */
    onClarifyTap(e) {
        const text = e.currentTarget.dataset.text;
        if (!text)
            return;
        this.setData({ inputText: text, clarifyChips: [] });
        this.send();
    },
    onPickImage() {
        wx.chooseMedia({
            count: 3,
            mediaType: ['image'],
            sourceType: ['album', 'camera'],
            success: (res) => {
                const adds = res.tempFiles.map((f) => ({
                    path: f.tempFilePath,
                    name: f.tempFilePath.split('/').pop() || 'image',
                    type: 'image',
                }));
                this.setData({ attachments: [...this.data.attachments, ...adds] });
            },
            fail: () => { },
        });
    },
    onPickFile() {
        wx.chooseMessageFile({
            count: 3,
            type: 'file',
            success: (res) => {
                const adds = res.tempFiles.map((f) => ({
                    path: f.path,
                    name: f.name,
                    type: 'file',
                }));
                this.setData({ attachments: [...this.data.attachments, ...adds] });
            },
            fail: () => { },
        });
    },
    onRemoveAttach(e) {
        const idx = e.currentTarget.dataset.index;
        const next = this.data.attachments.slice();
        next.splice(idx, 1);
        this.setData({ attachments: next });
    },
    send() {
        const text = (this.data.inputText || '').trim();
        const attachments = this.data.attachments;
        if (!text && attachments.length === 0)
            return;
        // 附件上传进行中：禁止重入
        if (this.data.uploading)
            return;
        // 防连点：与当前在途文本完全一致（多为误触双发）则忽略
        if (this._locked && text && text === this._inflightText)
            return;
        this._locked = true;
        this._inflightText = text || '[附件]';
        // 1) 用户消息入栈
        index_1.store.addMessage({ role: 'user', content: text || '[附件]' });
        this.setData({ inputText: '', attachments: [], clarifyChips: [] });
        this.scrollToBottom();
        // 2) 附件先真上传（本地临时路径服务端读不到），拿到服务端路径再开流
        if (attachments.length > 0) {
            this.setData({ uploading: true });
            wx.showLoading({ title: '上传中…', mask: true });
            (0, loops_1.stageFiles)(attachments.map((a) => a.path))
                .then((serverPaths) => {
                wx.hideLoading();
                this.setData({ uploading: false });
                if (serverPaths.length === 0) {
                    index_1.store.addMessage({
                        role: 'system',
                        content: '附件上传失败了，请检查网络或换一个文件（支持 PNG/JPG 截图与 CSV）。',
                    });
                    this.scrollToBottom();
                    this._locked = false;
                    return;
                }
                this.startStream(text || '请查看我上传的资料并给出建议', serverPaths);
            })
                .catch((err) => {
                wx.hideLoading();
                this.setData({ uploading: false });
                (0, error_1.showErrorToast)((0, error_1.classifyError)(err));
                this._locked = false;
            });
            return;
        }
        this.startStream(text, []);
    },
    /** 真正发起 SSE 流式对话（自带请求序号 + 可取消句柄） */
    startStream(message, files) {
        const mySeq = ++this._reqSeq;
        this._currentSeq = mySeq;
        this._locked = true;
        // 取消上一个仍在进行（或正在初始化）的流，避免快速操作消息交错
        this._abortStream();
        // 清理被超车旧流的占位气泡（内容为空则移除，否则标记完成）
        index_1.store.cleanupStreamingAgent();
        const msg = index_1.store.addMessage({
            role: 'agent',
            content: '',
            thinkingSteps: [],
            toolCalls: [],
            streaming: true,
        });
        this._streamMsgId = msg.id;
        this.scrollToBottom();
        const handle = (0, agent_1.streamChat)({
            message,
            sessionId: this._sessionId,
            businessId: this._businessId,
            files,
            // onError 统一在 handle.promise.catch 处理（含 abort 静默）
            onEvent: (e) => this.onStreamEvent(e, mySeq),
        });
        this._streamHandle = handle;
        handle.promise.catch((err) => {
            // 主动中止（被新流超车 / 页面销毁）不提示、不落状态
            if (err && err.isAbort)
                return;
            if (mySeq !== this._currentSeq)
                return;
            index_1.store.endStreaming();
            index_1.store.updateLastAgent({ streaming: false, content: '⚠️ ' + (0, error_1.classifyError)(err).message });
            (0, error_1.showErrorToast)((0, error_1.classifyError)(err));
            this._release(mySeq);
        });
    },
    /** 释放状态锁：仅当仍是当前有效流时才释放（被更新的流接管时不释放） */
    _release(mySeq) {
        if (mySeq !== this._currentSeq)
            return;
        this._locked = false;
        this._streamHandle = null;
    },
    /** 主动中止上一个仍在进行的流（快速连续发送 / 页面销毁时调用） */
    _abortStream() {
        const h = this._streamHandle;
        if (h) {
            try {
                h.abort();
            }
            catch (_a) {
                /* ignore */
            }
            this._streamHandle = null;
        }
    },
    onStreamEvent(e, mySeq) {
        // 竞态防护：只处理当前有效流的事件，旧流迟到事件直接丢弃
        if (mySeq !== this._currentSeq)
            return;
        switch (e.type) {
            case 'intent':
                index_1.store.beginStreaming(e.intent);
                this.scrollToBottom();
                break;
            case 'thinking':
                index_1.store.appendThinkingStep(e.step);
                index_1.store.updateLastAgent({ thinkingSteps: index_1.store.getState().agentStatus.steps });
                this.scrollToBottom();
                break;
            case 'tool':
                {
                    const cur = index_1.store.getState().messages;
                    const last = cur[cur.length - 1];
                    const tools = [...((last === null || last === void 0 ? void 0 : last.toolCalls) || []), e.name];
                    index_1.store.updateLastAgent({ toolCalls: tools });
                }
                break;
            case 'done':
                this.finalizeAgent(e, mySeq);
                break;
            case 'error':
                index_1.store.endStreaming();
                index_1.store.updateLastAgent({ streaming: false, content: '⚠️ ' + e.message });
                break;
        }
    },
    finalizeAgent(e, mySeq) {
        if (mySeq !== this._currentSeq)
            return;
        const card = this.parseCard(e.data);
        index_1.store.updateLastAgent({
            content: e.response,
            intent: e.intent,
            streaming: false,
            card,
        });
        index_1.store.endStreaming();
        if (e.business_id)
            this._businessId = e.business_id;
        this.syncFromResult(e, mySeq);
        this.renderClarify(e, mySeq);
        this._release(mySeq);
        this.scrollToBottom();
    },
    /**
     * 追问渲染：Agent 表示信息不足时，给出可一键补全的引导选项，
     * 让多轮澄清从「用户自己憋答案」变成「点一下就能继续」。
     */
    renderClarify(e, mySeq) {
        var _a;
        if (mySeq !== this._currentSeq)
            return;
        const needs = e.needs_clarification || ((_a = e.data) === null || _a === void 0 ? void 0 : _a.needs_clarification);
        if (!needs) {
            if (this.data.clarifyChips.length)
                this.setData({ clarifyChips: [] });
            return;
        }
        this.setData({ clarifyChips: CLARIFY_CHIPS[e.intent] || [] });
    },
    /**
     * 把结构化结果落进 Store —— 闭环的关键一环。
     * 对话产出的诊断/计划/日程/复盘不再「说完就丢」，而是变成
     * 看板、计划详情、日程页可读可改的持久数据。
     */
    syncFromResult(e, mySeq) {
        var _a, _b;
        const data = (e.data || {});
        if (mySeq !== this._currentSeq)
            return;
        // ① 诊断报告 → 画像 + 诊断详情
        if (data.diagnosis) {
            const diag = data.diagnosis;
            index_1.store.setDiagnosis(diag);
            const prev = index_1.store.getState().profile || {};
            const profile = Object.assign(Object.assign({}, prev), { business_id: diag.business_id || this._businessId || prev.business_id, overall_score: (_a = diag.overall_score) !== null && _a !== void 0 ? _a : prev.overall_score, dimension_scores: (_b = diag.dimension_scores) !== null && _b !== void 0 ? _b : prev.dimension_scores, updated_at: new Date().toISOString() });
            if (diag.company_name)
                profile.company_name = diag.company_name;
            if (diag.industry)
                profile.industry = diag.industry;
            if (diag.city)
                profile.city = diag.city;
            if (diag.main_product)
                profile.main_product = diag.main_product;
            if (diag.target_customer)
                profile.target_customer = diag.target_customer;
            index_1.store.setProfile(profile);
        }
        // ② 计划 → 供计划详情页微调与确认
        if (data.plan) {
            index_1.store.setPlan(data.plan);
        }
        // ③ 排期 → 扁平化进 todos，并补录落库（跨会话可见）
        if (data.schedule && Array.isArray(data.schedule)) {
            const days = data.schedule;
            const todos = [];
            days.forEach((d) => (d.tasks || []).forEach((t, i) => todos.push(Object.assign(Object.assign({}, t), { id: t.id || `${d.day_index}_${i}`, status: t.status || 'pending', day_index: d.day_index, day_name: d.day_name, date: d.date }))));
            index_1.store.setTodos(todos);
            // 落库：让日程页刷新后仍在，且打卡有真实 todo_id 可用
            (0, loops_1.syncSchedule)({
                businessId: this._businessId,
                planId: data.plan_id || (data.plan && data.plan.id) || undefined,
                days,
            })
                .then(() => {
                // 若已被更新的流接管，不再回拉（避免覆盖新状态）
                if (mySeq !== this._currentSeq)
                    return;
                this.refreshTodosFromBackend();
            })
                .catch(() => {
                /* 落库失败不阻塞对话，本地 todos 仍可用 */
            });
        }
        // ④ 复盘 → 存下来供复盘详情页展示与「采纳建议」
        if (data.review) {
            index_1.store.setReview(data.review);
        }
        // 业务 ID 补写进画像，供其他页面调用闭环接口
        if (this._businessId) {
            const prev = index_1.store.getState().profile;
            if (prev && !prev.business_id) {
                index_1.store.setProfile(Object.assign(Object.assign({}, prev), { business_id: this._businessId }));
            }
        }
    },
    /** 排期落库后拉一次真实 todos（带后端 id，打卡才能生效） */
    refreshTodosFromBackend() {
        (0, loops_1.getSchedule)(this._businessId)
            .then((res) => {
            if (res && res.ok && Array.isArray(res.todos) && res.todos.length) {
                index_1.store.setTodosFromBackend(res.todos);
            }
        })
            .catch(() => { });
    },
    parseCard(data) {
        if (!data)
            return null;
        const d = data;
        // 优先级：复盘 > 计划 > 日程 > 诊断（越靠后的产出越贴近用户当前诉求）
        if (d.review)
            return { kind: 'review', report: d.review };
        if (d.plan)
            return { kind: 'plan', plan: d.plan };
        if (d.schedule)
            return { kind: 'schedule', days: d.schedule };
        if (d.diagnosis)
            return { kind: 'diagnosis', report: d.diagnosis };
        return null;
    },
    scrollToBottom() {
        const msgs = index_1.store.getState().messages;
        if (msgs.length) {
            this.setData({ toView: msgs[msgs.length - 1].id });
        }
    },
    /** 点击气泡里的结构化结果卡片 → 按类型跳到对应可视化页面 */
    onCardTap(e) {
        const detail = (e.detail || {});
        const kind = detail.kind || '';
        const refId = detail.refId || '';
        switch (kind) {
            case 'diagnosis':
                wx.navigateTo({ url: `/pages/detail/diagnosis-detail/index?id=${refId}` });
                break;
            case 'review':
                wx.navigateTo({ url: `/pages/detail/review-detail/index?id=${refId}` });
                break;
            case 'schedule':
                wx.switchTab({ url: '/pages/schedule/index' });
                break;
            case 'plan':
                wx.navigateTo({ url: `/pages/detail/plan-detail/index?id=${refId}` });
                break;
            default:
                wx.switchTab({ url: '/pages/dashboard/index' });
                break;
        }
    },
    /**
     * 持续学习：把 👍/👎 写回后端，更新策略有效性评分，
     * 后续 RAG 检索会按这个分数重排 → 「越用越懂你」。
     */
    onFeedback(e) {
        const d = (e.detail || {});
        const map = Object.assign({}, this.data.feedbackMap);
        if (d.rating === 0) {
            delete map[d.msgId];
        }
        else {
            map[d.msgId] = d.rating;
        }
        this.setData({ feedbackMap: map });
        if (d.rating === 0)
            return;
        const targetType = (['diagnosis', 'plan', 'schedule', 'review'].indexOf(d.kind) >= 0
            ? d.kind
            : 'card');
        (0, loops_1.submitFeedback)({
            targetType,
            targetId: d.refId || d.msgId,
            rating: d.rating,
            businessId: this._businessId,
        })
            .then(() => {
            wx.showToast({
                title: d.rating > 0 ? '已记住你的偏好' : '收到，下次会调整',
                icon: 'none',
                duration: 1500,
            });
        })
            .catch(() => {
            // 反馈失败静默处理，不打断对话
        });
    },
    goDashboard() {
        wx.switchTab({ url: '/pages/dashboard/index' });
    },
});
