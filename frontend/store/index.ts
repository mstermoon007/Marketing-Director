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

import { getStorage, setStorage, removeStorage, STORAGE_KEYS } from '../utils/storage'
import { AgentIntent, TASK_STATUS } from '../utils/constants'
import type { Task, DayPlan, DiagnosisReport, SevenDayPlan, ReviewReport } from '../types'

/** 单条对话消息 */
export interface ChatMessage {
  id: string
  role: 'user' | 'agent' | 'system'
  content: string
  intent?: AgentIntent
  /** 流式思考步骤（仅 agent 消息，用于「思考中」指示） */
  thinkingSteps?: string[]
  /** 本轮调用的 Tool 名称 */
  toolCalls?: string[]
  /** 该条消息是否仍在流式生成中（用于气泡显示光标 / 思考指示） */
  streaming?: boolean
  createdAt: number
  /** 关联结构化卡片（诊断/计划/日程/复盘），由后端 data 解析 */
  card?: MessageCard | null
}

/** 结构化结果卡片（按意图渲染为富文本组件） */
export type MessageCard =
  | { kind: 'diagnosis'; report: DiagnosisReport }
  | { kind: 'plan'; plan: SevenDayPlan }
  | { kind: 'schedule'; days: DayPlan[] }
  | { kind: 'review'; report: ReviewReport }
  | { kind: 'raw'; title: string; payload: Record<string, unknown> }

/** 用户画像摘要（Agent 记忆，看板展示用） */
export interface ProfileSummary {
  business_id?: string
  company_name?: string
  industry?: string
  city?: string
  main_product?: string
  target_customer?: string
  overall_score?: number
  /** 五维得分（雷达图） */
  dimension_scores?: Record<string, number>
  current_week?: number
  updated_at?: string
}

/** Agent 处理状态（思考指示 / 流式进度） */
export interface AgentStatus {
  streaming: boolean
  thinking: boolean
  steps: string[]
  intent?: AgentIntent
}

/** 用户设置 */
export interface UserSettings {
  showThinking: boolean
}

/** 仓库完整状态 */
export interface StoreState {
  sessionId: string
  messages: ChatMessage[]
  profile: ProfileSummary | null
  /** 当前选中的企业 ID（对话/看板/上传复用，避免重复依赖 profile 字段） */
  currentBusinessId: string
  /** 个人中心：当前用户名下企业列表 */
  businesses: Array<{
    id: string
    business_name: string
    industry: string
    city: string
    created_at: string | null
  }>
  /** 最新日程任务（扁平化，含所属日信息） */
  todos: Array<Task & { day_index: number; day_name: string; date: string }>
  /** 最新诊断报告（闭环：对话产出后持久化，看板/详情可查） */
  diagnosis: DiagnosisReport | null
  /** 最新计划（闭环：可交互编辑、确认） */
  plan: SevenDayPlan | null
  /** 最新复盘报告（闭环：下周建议来源） */
  review: ReviewReport | null
  agentStatus: AgentStatus
  settings: UserSettings
}

type Listener = (state: StoreState) => void

function genId(): string {
  return `m_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

const MAX_CACHED_MESSAGES = 60

class Store {
  private state: StoreState
  private listeners: Set<Listener> = new Set()

  constructor() {
    this.state = {
      sessionId: '',
      messages: [],
      profile: null,
      currentBusinessId: '',
      businesses: [],
      todos: [],
      diagnosis: null,
      plan: null,
      review: null,
      agentStatus: { streaming: false, thinking: false, steps: [], intent: undefined },
      settings: { showThinking: true },
    }
  }

  /** 读取当前状态（只读快照引用） */
  getState(): StoreState {
    return this.state
  }

  /** 订阅状态变更，返回取消订阅函数 */
  subscribe(listener: Listener): () => void {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  private emit(): void {
    this.listeners.forEach((l) => l(this.state))
  }

  private set(patch: Partial<StoreState>): void {
    this.state = { ...this.state, ...patch }
    this.emit()
  }

  // ===================== 会话 / 消息 =====================

  /** 开始新会话 */
  startNewSession(sessionId: string): void {
    this.state = {
      ...this.state,
      sessionId,
      messages: [],
      agentStatus: { streaming: false, thinking: false, steps: [], intent: undefined },
    }
    this.emit()
    this.persistConversation()
  }

  setSession(sessionId: string): void {
    if (this.state.sessionId !== sessionId) {
      this.set({ sessionId })
    }
  }

  addMessage(msg: Omit<ChatMessage, 'id' | 'createdAt'> & { id?: string; createdAt?: number }): ChatMessage {
    const full: ChatMessage = {
      id: msg.id || genId(),
      createdAt: msg.createdAt || Date.now(),
      role: msg.role,
      content: msg.content,
      intent: msg.intent,
      thinkingSteps: msg.thinkingSteps,
      // 归一化为数组：用户消息等未携带 toolCalls 时避免组件收到 undefined 触发类型告警
      toolCalls: msg.toolCalls || [],
      streaming: msg.streaming,
      card: msg.card,
    }
    this.set({ messages: [...this.state.messages, full] })
    this.persistConversation()
    return full
  }

  /** 更新最后一条 agent 消息（流式追加内容 / 思考步骤） */
  updateLastAgent(patch: Partial<ChatMessage>): void {
    const msgs = this.state.messages
    if (msgs.length === 0) return
    const last = msgs[msgs.length - 1]
    if (last.role !== 'agent') return
    const updated = { ...last, ...patch }
    this.set({ messages: [...msgs.slice(0, -1), updated] })
    this.persistConversation()
  }

  // ===================== Agent 状态 =====================

  setAgentStatus(patch: Partial<AgentStatus>): void {
    this.set({ agentStatus: { ...this.state.agentStatus, ...patch } })
  }

  appendThinkingStep(step: string): void {
    this.set({
      agentStatus: {
        ...this.state.agentStatus,
        thinking: true,
        steps: [...this.state.agentStatus.steps, step],
      },
    })
  }

  beginStreaming(intent?: AgentIntent): void {
    this.set({
      agentStatus: { streaming: true, thinking: true, steps: [], intent },
    })
  }

  endStreaming(): void {
    this.set({
      agentStatus: { streaming: false, thinking: false, steps: [], intent: undefined },
    })
  }

  /**
   * 清理被新流「超车」的旧 agent 气泡：内容为空则直接移除（避免残留空气泡），
   * 已有内容则标记完成。用于快速连续发送时防止旧流占位消息卡在「生成中」。
   */
  cleanupStreamingAgent(): void {
    const msgs = this.state.messages
    for (let i = msgs.length - 1; i >= 0; i--) {
      const m = msgs[i]
      if (m.role === 'agent' && m.streaming) {
        if (!m.content) {
          this.state.messages = [...msgs.slice(0, i), ...msgs.slice(i + 1)]
        } else {
          msgs[i] = { ...m, streaming: false }
          this.state.messages = [...msgs]
        }
        this.emit()
        this.persistConversation()
        return
      }
    }
  }

  // ===================== 画像 / 日程 / 设置 =====================

  setProfile(profile: ProfileSummary | null): void {
    this.set({ profile })
    setStorage(STORAGE_KEYS.PROFILE_SUMMARY, profile)
    // 画像带 business_id 时同步到当前企业，提升上传/排期复用命中率
    if (profile?.business_id) {
      this.setCurrentBusinessId(profile.business_id)
    }
  }

  /** 设置当前企业 ID（对话/看板/上传复用），持久化便于重启恢复。 */
  setCurrentBusinessId(id: string): void {
    if (!id) return
    this.set({ currentBusinessId: id })
    setStorage(STORAGE_KEYS.BUSINESS_ID, id)
  }

  /** 设置当前用户名下企业列表（个人中心用），持久化便于离线展示。 */
  setBusinesses(list: StoreState['businesses']): void {
    this.set({ businesses: list || [] })
    setStorage(STORAGE_KEYS.BUSINESS_LIST, list || [])
  }

  setTodos(todos: StoreState['todos']): void {
    this.set({ todos })
    setStorage(STORAGE_KEYS.SCHEDULE_CACHE, todos)
  }

  /** 直接用后端 todo 列表（含 id/status）覆盖本地日程。 */
  setTodosFromBackend(raw: any[]): void {
    const todos = (raw || []).map((t) => ({
      id: t.id,
      title: t.title,
      time_slot: t.time_slot || '',
      how_to: t.how_to || '',
      checklist: t.checklist || [],
      status: t.status || TASK_STATUS.PENDING,
      done: t.status === TASK_STATUS.DONE,
      day_index: t.day_index || 0,
      day_name: t.day_name || '',
      date: t.date || '',
      notes: t.notes || '',
    }))
    this.setTodos(todos)
  }

  /** 本地翻转任务完成态（闭环：完成标记 → 页面再上报后端 checkin）。 */
  toggleTodo(id: string): void {
    const todos = this.state.todos.map((t) => {
      if (t.id !== id) return t
      const done = t.status === TASK_STATUS.DONE
      return {
        ...t,
        status: done ? TASK_STATUS.PENDING : TASK_STATUS.DONE,
        done: !done,
      }
    })
    this.setTodos(todos)
  }

  setDiagnosis(diagnosis: DiagnosisReport | null): void {
    this.set({ diagnosis })
    setStorage(STORAGE_KEYS.DIAGNOSIS, diagnosis)
  }

  setPlan(plan: SevenDayPlan | null): void {
    this.set({ plan })
    setStorage(STORAGE_KEYS.WEEKLY_PLAN, plan)
  }

  setReview(review: ReviewReport | null): void {
    this.set({ review })
    setStorage(STORAGE_KEYS.LATEST_REVIEW, review)
  }

  setSettings(patch: Partial<UserSettings>): void {
    const next = { ...this.state.settings, ...patch }
    this.set({ settings: next })
    setStorage(STORAGE_KEYS.USER_SETTINGS, next)
  }

  // ===================== 持久化（启动秒开 / 离线） =====================

  /** 启动时从 wx.storage 恢复关键状态 */
  loadCache(): void {
    const cachedMsgs = getStorage<ChatMessage[]>(STORAGE_KEYS.CHAT_SUMMARY)
    if (cachedMsgs && Array.isArray(cachedMsgs)) {
      // 兼容旧缓存：确保每条消息都有 toolCalls 数组，避免组件类型告警
      this.state.messages = cachedMsgs.slice(-MAX_CACHED_MESSAGES).map((m) => ({
        ...m,
        toolCalls: m.toolCalls || [],
      }))
    }
    const profile = getStorage<ProfileSummary | null>(STORAGE_KEYS.PROFILE_SUMMARY)
    if (profile) this.state.profile = profile
    const currentBusinessId = getStorage<string>(STORAGE_KEYS.BUSINESS_ID)
    if (currentBusinessId) this.state.currentBusinessId = currentBusinessId
    const businesses = getStorage<StoreState['businesses']>(STORAGE_KEYS.BUSINESS_LIST)
    if (businesses && Array.isArray(businesses)) this.state.businesses = businesses
    const todos = getStorage<StoreState['todos']>(STORAGE_KEYS.SCHEDULE_CACHE)
    if (todos && Array.isArray(todos)) this.state.todos = todos
    const settings = getStorage<UserSettings>(STORAGE_KEYS.USER_SETTINGS)
    if (settings) this.state.settings = settings
    const diagnosis = getStorage<DiagnosisReport | null>(STORAGE_KEYS.DIAGNOSIS)
    if (diagnosis) this.state.diagnosis = diagnosis
    const plan = getStorage<SevenDayPlan | null>(STORAGE_KEYS.WEEKLY_PLAN)
    if (plan) this.state.plan = plan
    const review = getStorage<ReviewReport | null>(STORAGE_KEYS.LATEST_REVIEW)
    if (review) this.state.review = review
    this.emit()
  }

  private persistConversation(): void {
    const msgs = this.state.messages.slice(-MAX_CACHED_MESSAGES)
    setStorage(STORAGE_KEYS.CHAT_SUMMARY, msgs)
  }

  /** 清空（退出登录时调用）。
   *
   * 同步清理本地持久化的业务数据（画像/日程/诊断/计划/复盘/KPI/企业列表/当前企业），
   * 否则下一位用户登录时会从 wx.storage 读到上一位用户的数据，造成数据泄漏。
   * 注意：登录 token 由 logout 显式清除，这里不触碰。
   */
  clearAll(): void {
    this.state = {
      sessionId: '',
      messages: [],
      profile: null,
      currentBusinessId: '',
      businesses: [],
      todos: [],
      diagnosis: null,
      plan: null,
      review: null,
      agentStatus: { streaming: false, thinking: false, steps: [], intent: undefined },
      settings: { showThinking: true },
    }
    ;[
      STORAGE_KEYS.PROFILE_SUMMARY,
      STORAGE_KEYS.SCHEDULE_CACHE,
      STORAGE_KEYS.DIAGNOSIS,
      STORAGE_KEYS.WEEKLY_PLAN,
      STORAGE_KEYS.LATEST_REVIEW,
      STORAGE_KEYS.DASHBOARD_KPI,
      STORAGE_KEYS.BUSINESS_LIST,
      STORAGE_KEYS.BUSINESS_ID,
    ].forEach((k) => removeStorage(k))
    this.emit()
  }
}

export const store = new Store()

/**
 * 将仓库状态桥接到小程序页面/组件实例。
 * @param page   页面或组件实例（需有 setData）
 * @param selector 从 StoreState 选取需要映射到 data 的字段
 * @returns 取消订阅函数（在 onUnload / detached 调用）
 */
export function bindStore<T extends Record<string, unknown>>(
  page: { setData: (data: any, cb?: () => void) => void },
  selector: (s: StoreState) => T,
): () => void {
  const update = (): void => {
    page.setData(selector(store.getState()))
  }
  const unsub = store.subscribe(update)
  update()
  return unsub
}
