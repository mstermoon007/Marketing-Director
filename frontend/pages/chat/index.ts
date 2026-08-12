import { ensureLogin } from '../../utils/auth'
import { store, bindStore, ChatMessage, MessageCard, ProfileSummary } from '../../store/index'
import { streamChat } from '../../api/agent'
import { getSchedule, stageFiles, submitFeedback, syncSchedule } from '../../api/loops'
import { classifyError, showErrorToast } from '../../utils/error'
import { AgentIntent, AgentStreamEvent } from '../../utils/constants'
import { getStorage, STORAGE_KEYS } from '../../utils/storage'
import type { DiagnosisReport, ReviewReport, SevenDayPlan } from '../../types'

interface Attachment {
  path: string
  name: string
  type: 'image' | 'file'
}

interface ChatData {
  messages: ChatMessage[]
  agentStatus: { streaming: boolean; thinking: boolean; steps: string[]; intent?: AgentIntent }
  profile: ProfileSummary | null
  inputText: string
  attachments: Attachment[]
  quickActions: Array<{ label: string; prompt: string }>
  toView: string
  showThinking: boolean
  /** 上传进行中（暂存文件到服务端时的占位提示） */
  uploading: boolean
  /** 追问模式：Agent 需要更多信息时展示的引导选项 */
  clarifyChips: string[]
  /** 每条消息的反馈状态 msgId -> 1 | -1 */
  feedbackMap: Record<string, number>
}

const DEFAULT_QUICK = [
  { label: '🩺 诊断我的生意', prompt: '帮我诊断一下当前生意，找出核心问题' },
  { label: '🗺️ 生成营销计划', prompt: '为我生成未来一周的营销执行计划' },
  { label: '📅 安排本周日程', prompt: '把计划拆解成每天可执行的任务并排好日程' },
  { label: '🔄 复盘本周', prompt: '帮我复盘本周执行情况并给出调整建议' },
]

/**
 * 追问引导：Agent 说「需要更多信息」时，按意图给出可一键补全的示例，
 * 避免用户面对开放式问题卡住（多轮澄清的关键体验）。
 */
const CLARIFY_CHIPS: Record<string, string[]> = {
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
}

Page<ChatData, Record<string, any>>({
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
  } as ChatData,

  _unsub: undefined as (() => void) | undefined,
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

  onLoad(): void {
    // 确保登录（失败自动跳 onboarding）
    ensureLogin(true)

    this._sessionId = store.getState().sessionId || `${this.getUserId()}:default`
    store.setSession(this._sessionId)

    const unsub = bindStore(this, (s) => ({
      messages: s.messages,
      agentStatus: s.agentStatus,
      profile: s.profile,
      showThinking: s.settings.showThinking,
    }))
    this._unsub = unsub

    this._businessId = store.getState().profile?.business_id || ''

    // 首屏：缓存为空时给一句欢迎语（仅当前会话）
    if (store.getState().messages.length === 0) {
      store.addMessage({
        role: 'system',
        content: '你好，我是你的 AI 营销顾问。告诉我你的生意情况，我可以帮你诊断、制定计划、安排日程和复盘。',
      })
    }
    this.scrollToBottom()
  },

  onShow(): void {
    // 从后台返回：store 订阅已保证数据同步，仅重新定位到底部
    this.scrollToBottom()
  },

  onUnload(): void {
    this._abortStream()
    if (this._unsub) this._unsub()
  },

  getUserId(): string {
    // 注意：必须走 getStorage（带 TTL 包装），直接 wx.getStorageSync 会拿到 {data,timestamp} 包装对象
    const info = getStorage<{ user_id?: string }>(STORAGE_KEYS.USER_INFO)
    return info && info.user_id ? info.user_id : 'local'
  },

  onInput(e: WechatMiniprogram.Input): void {
    this.setData({ inputText: e.detail.value })
  },

  onQuickSelect(e: WechatMiniprogram.TouchEvent): void {
    const prompt = e.detail.prompt as string
    this.setData({ inputText: prompt })
    this.send()
  },

  /** 点击追问引导 chip → 直接作为下一轮输入发出（多轮澄清） */
  onClarifyTap(e: WechatMiniprogram.TouchEvent): void {
    const text = e.currentTarget.dataset.text as string
    if (!text) return
    this.setData({ inputText: text, clarifyChips: [] })
    this.send()
  },

  onPickImage(): void {
    wx.chooseMedia({
      count: 3,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const adds: Attachment[] = res.tempFiles.map((f) => ({
          path: f.tempFilePath,
          name: f.tempFilePath.split('/').pop() || 'image',
          type: 'image' as const,
        }))
        this.setData({ attachments: [...this.data.attachments, ...adds] })
      },
      fail: () => {},
    })
  },

  onPickFile(): void {
    wx.chooseMessageFile({
      count: 3,
      type: 'file',
      success: (res) => {
        const adds: Attachment[] = res.tempFiles.map((f) => ({
          path: f.path,
          name: f.name,
          type: 'file' as const,
        }))
        this.setData({ attachments: [...this.data.attachments, ...adds] })
      },
      fail: () => {},
    })
  },

  onRemoveAttach(e: WechatMiniprogram.TouchEvent): void {
    const idx = e.currentTarget.dataset.index as number
    const next = this.data.attachments.slice()
    next.splice(idx, 1)
    this.setData({ attachments: next })
  },

  send(): void {
    const text = (this.data.inputText || '').trim()
    const attachments = this.data.attachments
    if (!text && attachments.length === 0) return
    // 附件上传进行中：禁止重入
    if (this.data.uploading) return
    // 防连点：与当前在途文本完全一致（多为误触双发）则忽略
    if (this._locked && text && text === this._inflightText) return

    this._locked = true
    this._inflightText = text || '[附件]'

    // 1) 用户消息入栈
    store.addMessage({ role: 'user', content: text || '[附件]' })
    this.setData({ inputText: '', attachments: [], clarifyChips: [] })
    this.scrollToBottom()

    // 2) 附件先真上传（本地临时路径服务端读不到），拿到服务端路径再开流
    if (attachments.length > 0) {
      this.setData({ uploading: true })
      wx.showLoading({ title: '上传中…', mask: true })
      stageFiles(attachments.map((a) => a.path))
        .then((serverPaths) => {
          wx.hideLoading()
          this.setData({ uploading: false })
          if (serverPaths.length === 0) {
            store.addMessage({
              role: 'system',
              content: '附件上传失败了，请检查网络或换一个文件（支持 PNG/JPG 截图与 CSV）。',
            })
            this.scrollToBottom()
            this._locked = false
            return
          }
          this.startStream(text || '请查看我上传的资料并给出建议', serverPaths)
        })
        .catch((err) => {
          wx.hideLoading()
          this.setData({ uploading: false })
          showErrorToast(classifyError(err))
          this._locked = false
        })
      return
    }

    this.startStream(text, [])
  },

  /** 真正发起 SSE 流式对话（自带请求序号 + 可取消句柄） */
  startStream(message: string, files: string[]): void {
    const mySeq = ++this._reqSeq
    this._currentSeq = mySeq
    this._locked = true

    // 取消上一个仍在进行（或正在初始化）的流，避免快速操作消息交错
    this._abortStream()
    // 清理被超车旧流的占位气泡（内容为空则移除，否则标记完成）
    store.cleanupStreamingAgent()

    const msg = store.addMessage({
      role: 'agent',
      content: '',
      thinkingSteps: [],
      toolCalls: [],
      streaming: true,
    })
    this._streamMsgId = msg.id
    this.scrollToBottom()

    const handle = streamChat({
      message,
      sessionId: this._sessionId,
      businessId: this._businessId,
      files,
      // onError 统一在 handle.promise.catch 处理（含 abort 静默）
      onEvent: (e) => this.onStreamEvent(e, mySeq),
    })
    this._streamHandle = handle
    handle.promise.catch((err) => {
      // 主动中止（被新流超车 / 页面销毁）不提示、不落状态
      if (err && (err as any).isAbort) return
      if (mySeq !== this._currentSeq) return
      store.endStreaming()
      store.updateLastAgent({ streaming: false, content: '⚠️ ' + classifyError(err).message })
      showErrorToast(classifyError(err))
      this._release(mySeq)
    })
  },

  /** 释放状态锁：仅当仍是当前有效流时才释放（被更新的流接管时不释放） */
  _release(mySeq: number): void {
    if (mySeq !== this._currentSeq) return
    this._locked = false
    this._streamHandle = null
  },

  /** 主动中止上一个仍在进行的流（快速连续发送 / 页面销毁时调用） */
  _abortStream(): void {
    const h = this._streamHandle
    if (h) {
      try {
        h.abort()
      } catch {
        /* ignore */
      }
      this._streamHandle = null
    }
  },

  onStreamEvent(e: AgentStreamEvent, mySeq: number): void {
    // 竞态防护：只处理当前有效流的事件，旧流迟到事件直接丢弃
    if (mySeq !== this._currentSeq) return
    switch (e.type) {
      case 'intent':
        store.beginStreaming(e.intent)
        this.scrollToBottom()
        break
      case 'thinking':
        store.appendThinkingStep(e.step)
        store.updateLastAgent({ thinkingSteps: store.getState().agentStatus.steps })
        this.scrollToBottom()
        break
      case 'tool':
        {
          const cur = store.getState().messages
          const last = cur[cur.length - 1]
          const tools = [...(last?.toolCalls || []), e.name]
          store.updateLastAgent({ toolCalls: tools })
        }
        break
      case 'done':
        this.finalizeAgent(e, mySeq)
        break
      case 'error':
        store.endStreaming()
        store.updateLastAgent({ streaming: false, content: '⚠️ ' + e.message })
        break
    }
  },

  finalizeAgent(e: Extract<AgentStreamEvent, { type: 'done' }>, mySeq: number): void {
    if (mySeq !== this._currentSeq) return
    const card = this.parseCard(e.data)
    store.updateLastAgent({
      content: e.response,
      intent: e.intent,
      streaming: false,
      card,
    })
    store.endStreaming()

    if (e.business_id) this._businessId = e.business_id
    this.syncFromResult(e, mySeq)
    this.renderClarify(e, mySeq)
    this._release(mySeq)
    this.scrollToBottom()
  },

  /**
   * 追问渲染：Agent 表示信息不足时，给出可一键补全的引导选项，
   * 让多轮澄清从「用户自己憋答案」变成「点一下就能继续」。
   */
  renderClarify(e: Extract<AgentStreamEvent, { type: 'done' }>, mySeq: number): void {
    if (mySeq !== this._currentSeq) return
    const needs = e.needs_clarification || (e.data as any)?.needs_clarification
    if (!needs) {
      if (this.data.clarifyChips.length) this.setData({ clarifyChips: [] })
      return
    }
    this.setData({ clarifyChips: CLARIFY_CHIPS[e.intent] || [] })
  },

  /**
   * 把结构化结果落进 Store —— 闭环的关键一环。
   * 对话产出的诊断/计划/日程/复盘不再「说完就丢」，而是变成
   * 看板、计划详情、日程页可读可改的持久数据。
   */
  syncFromResult(e: Extract<AgentStreamEvent, { type: 'done' }>, mySeq: number): void {
    const data = (e.data || {}) as Record<string, any>
    if (mySeq !== this._currentSeq) return

    // ① 诊断报告 → 画像 + 诊断详情
    if (data.diagnosis) {
      const diag = data.diagnosis as DiagnosisReport & Record<string, any>
      store.setDiagnosis(diag)
      const prev = store.getState().profile || {}
      const profile: ProfileSummary = {
        ...prev,
        business_id: diag.business_id || this._businessId || prev.business_id,
        overall_score: diag.overall_score ?? prev.overall_score,
        dimension_scores: diag.dimension_scores ?? prev.dimension_scores,
        updated_at: new Date().toISOString(),
      }
      if (diag.company_name) profile.company_name = diag.company_name
      if (diag.industry) profile.industry = diag.industry
      if (diag.city) profile.city = diag.city
      if (diag.main_product) profile.main_product = diag.main_product
      if (diag.target_customer) profile.target_customer = diag.target_customer
      store.setProfile(profile)
    }

    // ② 计划 → 供计划详情页微调与确认
    if (data.plan) {
      store.setPlan(data.plan as SevenDayPlan)
    }

    // ③ 排期 → 扁平化进 todos，并补录落库（跨会话可见）
    if (data.schedule && Array.isArray(data.schedule)) {
      const days = data.schedule as Array<{
        day_index: number
        day_name: string
        date: string
        tasks: any[]
      }>
      const todos: Array<any> = []
      days.forEach((d) =>
        (d.tasks || []).forEach((t, i) =>
          todos.push({
            ...t,
            id: t.id || `${d.day_index}_${i}`,
            status: t.status || 'pending',
            day_index: d.day_index,
            day_name: d.day_name,
            date: d.date,
          }),
        ),
      )
      store.setTodos(todos)
      // 落库：让日程页刷新后仍在，且打卡有真实 todo_id 可用
      syncSchedule({
        businessId: this._businessId,
        planId: data.plan_id || (data.plan && data.plan.id) || undefined,
        days,
      })
        .then(() => {
          // 若已被更新的流接管，不再回拉（避免覆盖新状态）
          if (mySeq !== this._currentSeq) return
          this.refreshTodosFromBackend()
        })
        .catch(() => {
          /* 落库失败不阻塞对话，本地 todos 仍可用 */
        })
    }

    // ④ 复盘 → 存下来供复盘详情页展示与「采纳建议」
    if (data.review) {
      store.setReview(data.review as ReviewReport)
    }

    // 业务 ID 补写进画像，供其他页面调用闭环接口
    if (this._businessId) {
      const prev = store.getState().profile
      if (prev && !prev.business_id) {
        store.setProfile({ ...prev, business_id: this._businessId })
      }
    }
  },

  /** 排期落库后拉一次真实 todos（带后端 id，打卡才能生效） */
  refreshTodosFromBackend(): void {
    getSchedule(this._businessId)
      .then((res) => {
        if (res && res.ok && Array.isArray(res.todos) && res.todos.length) {
          store.setTodosFromBackend(res.todos)
        }
      })
      .catch(() => {})
  },

  parseCard(data: Record<string, unknown> | undefined): MessageCard | null {
    if (!data) return null
    const d = data as Record<string, any>
    // 优先级：复盘 > 计划 > 日程 > 诊断（越靠后的产出越贴近用户当前诉求）
    if (d.review) return { kind: 'review', report: d.review }
    if (d.plan) return { kind: 'plan', plan: d.plan }
    if (d.schedule) return { kind: 'schedule', days: d.schedule }
    if (d.diagnosis) return { kind: 'diagnosis', report: d.diagnosis }
    return null
  },

  scrollToBottom(): void {
    const msgs = store.getState().messages
    if (msgs.length) {
      this.setData({ toView: msgs[msgs.length - 1].id })
    }
  },

  /** 点击气泡里的结构化结果卡片 → 按类型跳到对应可视化页面 */
  onCardTap(e: WechatMiniprogram.TouchEvent): void {
    const detail = (e.detail || {}) as { kind?: string; refId?: string }
    const kind = detail.kind || ''
    const refId = detail.refId || ''
    switch (kind) {
      case 'diagnosis':
        wx.navigateTo({ url: `/pages/detail/diagnosis-detail/index?id=${refId}` })
        break
      case 'review':
        wx.navigateTo({ url: `/pages/detail/review-detail/index?id=${refId}` })
        break
      case 'schedule':
        wx.switchTab({ url: '/pages/schedule/index' })
        break
      case 'plan':
        wx.navigateTo({ url: `/pages/detail/plan-detail/index?id=${refId}` })
        break
      default:
        wx.switchTab({ url: '/pages/dashboard/index' })
        break
    }
  },

  /**
   * 持续学习：把 👍/👎 写回后端，更新策略有效性评分，
   * 后续 RAG 检索会按这个分数重排 → 「越用越懂你」。
   */
  onFeedback(e: WechatMiniprogram.TouchEvent): void {
    const d = (e.detail || {}) as { rating: number; msgId: string; kind: string; refId: string }
    const map = { ...this.data.feedbackMap }
    if (d.rating === 0) {
      delete map[d.msgId]
    } else {
      map[d.msgId] = d.rating
    }
    this.setData({ feedbackMap: map })

    if (d.rating === 0) return

    const targetType = (['diagnosis', 'plan', 'schedule', 'review'].indexOf(d.kind) >= 0
      ? d.kind
      : 'card') as 'diagnosis' | 'plan' | 'schedule' | 'review' | 'card'

    submitFeedback({
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
        })
      })
      .catch(() => {
        // 反馈失败静默处理，不打断对话
      })
  },

  goDashboard(): void {
    wx.switchTab({ url: '/pages/dashboard/index' })
  },
})
