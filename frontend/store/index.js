"use strict";
/**
 * 轻量响应式全局状态仓库（阶段三：自研 Store，零额外依赖）
 *
 * 设计目标：
 *   - 单一可信源：会话消息 / 用户画像摘要 / 待办日程 / Agent 处理状态 / 用户设置
 *   - 发布-订阅：组件 subscribe 后，状态变更自动收到通知并 setData（桥接小程序渲染层）
 *   - 启动秒开 + 离线可读：关键状态持久化到 wx.storage（对话摘要 / 最新日程 / 设置 / 画像）
 *   - 避免旧版 globalData 散乱写入导致的导航竞态
 *
 * 组件用法：
 *   const unsub = bindStore(this, (s) => ({ messages: s.messages, agentStatus: s.agentStatus }))
 *   // onUnload: unsub()
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.store = void 0;
exports.bindStore = bindStore;
const storage_1 = require("../utils/storage");
const constants_1 = require("../utils/constants");
function genId() {
    return `m_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}
const MAX_CACHED_MESSAGES = 60;
class Store {
    constructor() {
        this.listeners = new Set();
        this.state = {
            sessionId: '',
            messages: [],
            profile: null,
            todos: [],
            diagnosis: null,
            plan: null,
            review: null,
            agentStatus: { streaming: false, thinking: false, steps: [], intent: undefined },
            settings: { showThinking: true },
        };
    }
    /** 读取当前状态（只读快照引用） */
    getState() {
        return this.state;
    }
    /** 订阅状态变更，返回取消订阅函数 */
    subscribe(listener) {
        this.listeners.add(listener);
        return () => {
            this.listeners.delete(listener);
        };
    }
    emit() {
        this.listeners.forEach((l) => l(this.state));
    }
    set(patch) {
        this.state = Object.assign(Object.assign({}, this.state), patch);
        this.emit();
    }
    // ===================== 会话 / 消息 =====================
    /** 开始新会话 */
    startNewSession(sessionId) {
        this.state = Object.assign(Object.assign({}, this.state), { sessionId, messages: [], agentStatus: { streaming: false, thinking: false, steps: [], intent: undefined } });
        this.emit();
        this.persistConversation();
    }
    setSession(sessionId) {
        if (this.state.sessionId !== sessionId) {
            this.set({ sessionId });
        }
    }
    addMessage(msg) {
        const full = {
            id: msg.id || genId(),
            createdAt: msg.createdAt || Date.now(),
            role: msg.role,
            content: msg.content,
            intent: msg.intent,
            thinkingSteps: msg.thinkingSteps,
            toolCalls: msg.toolCalls,
            streaming: msg.streaming,
            card: msg.card,
        };
        this.set({ messages: [...this.state.messages, full] });
        this.persistConversation();
        return full;
    }
    /** 更新最后一条 agent 消息（流式追加内容 / 思考步骤） */
    updateLastAgent(patch) {
        const msgs = this.state.messages;
        if (msgs.length === 0)
            return;
        const last = msgs[msgs.length - 1];
        if (last.role !== 'agent')
            return;
        const updated = Object.assign(Object.assign({}, last), patch);
        this.set({ messages: [...msgs.slice(0, -1), updated] });
        this.persistConversation();
    }
    // ===================== Agent 状态 =====================
    setAgentStatus(patch) {
        this.set({ agentStatus: Object.assign(Object.assign({}, this.state.agentStatus), patch) });
    }
    appendThinkingStep(step) {
        this.set({
            agentStatus: Object.assign(Object.assign({}, this.state.agentStatus), { thinking: true, steps: [...this.state.agentStatus.steps, step] }),
        });
    }
    beginStreaming(intent) {
        this.set({
            agentStatus: { streaming: true, thinking: true, steps: [], intent },
        });
    }
    endStreaming() {
        this.set({
            agentStatus: { streaming: false, thinking: false, steps: [], intent: undefined },
        });
    }
    /**
     * 清理被新流「超车」的旧 agent 气泡：内容为空则直接移除（避免残留空气泡），
     * 已有内容则标记完成。用于快速连续发送时防止旧流占位消息卡在「生成中」。
     */
    cleanupStreamingAgent() {
        const msgs = this.state.messages;
        for (let i = msgs.length - 1; i >= 0; i--) {
            const m = msgs[i];
            if (m.role === 'agent' && m.streaming) {
                if (!m.content) {
                    this.state.messages = [...msgs.slice(0, i), ...msgs.slice(i + 1)];
                }
                else {
                    msgs[i] = Object.assign(Object.assign({}, m), { streaming: false });
                    this.state.messages = [...msgs];
                }
                this.emit();
                this.persistConversation();
                return;
            }
        }
    }
    // ===================== 画像 / 日程 / 设置 =====================
    setProfile(profile) {
        this.set({ profile });
        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.PROFILE_SUMMARY, profile);
    }
    setTodos(todos) {
        this.set({ todos });
        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.SCHEDULE_CACHE, todos);
    }
    /** 直接用后端 todo 列表（含 id/status）覆盖本地日程。 */
    setTodosFromBackend(raw) {
        const todos = (raw || []).map((t) => ({
            id: t.id,
            title: t.title,
            time_slot: t.time_slot || '',
            how_to: t.how_to || '',
            checklist: t.checklist || [],
            status: t.status || constants_1.TASK_STATUS.PENDING,
            done: t.status === constants_1.TASK_STATUS.DONE,
            day_index: t.day_index || 0,
            day_name: t.day_name || '',
            date: t.date || '',
            notes: t.notes || '',
        }));
        this.setTodos(todos);
    }
    /** 本地翻转任务完成态（闭环：完成标记 → 页面再上报后端 checkin）。 */
    toggleTodo(id) {
        const todos = this.state.todos.map((t) => {
            if (t.id !== id)
                return t;
            const done = t.status === constants_1.TASK_STATUS.DONE;
            return Object.assign(Object.assign({}, t), { status: done ? constants_1.TASK_STATUS.PENDING : constants_1.TASK_STATUS.DONE, done: !done });
        });
        this.setTodos(todos);
    }
    setDiagnosis(diagnosis) {
        this.set({ diagnosis });
        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.DIAGNOSIS, diagnosis);
    }
    setPlan(plan) {
        this.set({ plan });
        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.WEEKLY_PLAN, plan);
    }
    setReview(review) {
        this.set({ review });
        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.LATEST_REVIEW, review);
    }
    setSettings(patch) {
        const next = Object.assign(Object.assign({}, this.state.settings), patch);
        this.set({ settings: next });
        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.USER_SETTINGS, next);
    }
    // ===================== 持久化（启动秒开 / 离线） =====================
    /** 启动时从 wx.storage 恢复关键状态 */
    loadCache() {
        const cachedMsgs = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.CHAT_SUMMARY);
        if (cachedMsgs && Array.isArray(cachedMsgs)) {
            this.state.messages = cachedMsgs.slice(-MAX_CACHED_MESSAGES);
        }
        const profile = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.PROFILE_SUMMARY);
        if (profile)
            this.state.profile = profile;
        const todos = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.SCHEDULE_CACHE);
        if (todos && Array.isArray(todos))
            this.state.todos = todos;
        const settings = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.USER_SETTINGS);
        if (settings)
            this.state.settings = settings;
        const diagnosis = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.DIAGNOSIS);
        if (diagnosis)
            this.state.diagnosis = diagnosis;
        const plan = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.WEEKLY_PLAN);
        if (plan)
            this.state.plan = plan;
        const review = (0, storage_1.getStorage)(storage_1.STORAGE_KEYS.LATEST_REVIEW);
        if (review)
            this.state.review = review;
        this.emit();
    }
    persistConversation() {
        const msgs = this.state.messages.slice(-MAX_CACHED_MESSAGES);
        (0, storage_1.setStorage)(storage_1.STORAGE_KEYS.CHAT_SUMMARY, msgs);
    }
    /** 清空（退出登录时调用） */
    clearAll() {
        this.state = {
            sessionId: '',
            messages: [],
            profile: null,
            todos: [],
            diagnosis: null,
            plan: null,
            review: null,
            agentStatus: { streaming: false, thinking: false, steps: [], intent: undefined },
            settings: { showThinking: true },
        };
        this.emit();
    }
}
exports.store = new Store();
/**
 * 将仓库状态桥接到小程序页面/组件实例。
 * @param page   页面或组件实例（需有 setData）
 * @param selector 从 StoreState 选取需要映射到 data 的字段
 * @returns 取消订阅函数（在 onUnload / detached 调用）
 */
function bindStore(page, selector) {
    const update = () => {
        page.setData(selector(exports.store.getState()));
    };
    const unsub = exports.store.subscribe(update);
    update();
    return unsub;
}
