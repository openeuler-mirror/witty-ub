import { computed, nextTick, reactive, ref, shallowRef } from 'vue'
import {
  AgentApi,
  buildBasicAuthHeader,
  defaultAgentApiBase,
  extractAgentError,
  isSecureRemoteAgentAddress,
  normalizeAgentServerAddress,
  type AgentStreamEvent,
  type OpenCodeMessage,
  type OpenCodeSession,
  type OpenCodeSessionStatus,
} from '../api/agent'
import { useToast } from './useToast'

/**
 * P1.3 AI 故障诊断助手状态：
 * - 本机 /agent-api 反代免认证；远程直连 + Basic Authorization
 * - Basic 凭据只保存在当前页面内存，且仅通过 HTTPS 发送
 * - 会话按资产在前端索引（localStorage：sessionId -> assetId），切资产自动重置会话
 * - SSE 手动解析（EventSource 无法带 header）；中止/断流/错误均有明确状态
 */

export type AgentView = 'login' | 'models' | 'providers' | 'chat'

export type AgentChatPart = {
  id: string
  type: 'reasoning' | 'text'
  text: string
  collapsed?: boolean
}

export type AgentChatMessage = {
  id: string
  role: 'user' | 'assistant'
  parts: AgentChatPart[]
  content: string
  reasoning: string
  status: 'thinking' | 'done' | 'error'
  messageId?: string
}

const CONNECTION_KEY = 'witty-ub.agent-connection'
const SESSION_ASSET_KEY = 'witty-ub.agent-session-assets'
const ACTIVE_SESSION_KEY = 'witty-ub.active-session'
const DEFAULT_MODEL_KEY = 'witty-ub.agent-default-model'
const KNOWLEDGE_PREFIX_RE = /^当前(?:页面选中|会话对应)的知识库 ID 是 [^。]+。\n\n/
const KNOWLEDGE_ID_RE = /^当前(?:页面选中|会话对应)的知识库 ID 是 ([^。]+)。/

let state: ReturnType<typeof createAgentChatState> | null = null

export function useAgentChat() {
  if (!state) state = createAgentChatState()
  return state
}

export function createAgentChatState() {
  const { toast } = useToast()

  const view = ref<AgentView>('login')
  const api = shallowRef<AgentApi | null>(null)
  const connectionState = ref<'connected' | 'connecting' | 'disconnected'>('disconnected')
  const connectionError = ref('')
  const isLoggingIn = ref(false)

  // 远程登录表单（内存态，不持久化）
  const remoteUsername = ref('')
  const remotePassword = ref('')
  const remoteAddress = ref('')

  // 模型 / Provider
  const connectedModels = ref<{ providerID: string; id: string; name: string }[]>([])
  const providerNames = ref<Record<string, string>>({})
  const providerDefaults = ref<Record<string, string>>({})
  const availableProviders = ref<{ id: string; name: string }[]>([])
  const selectedModel = ref<{ providerID: string; modelID: string } | null>(null)
  const providerApiKey = ref('')
  const isAuthorizing = ref(false)
  const modelSearch = ref('')
  const providerSearch = ref('')
  const expandedProviderId = ref('')

  // 会话与消息
  const sessions = ref<OpenCodeSession[]>([])
  const sessionStatuses = ref<Record<string, OpenCodeSessionStatus>>({})
  const sessionDrafts = ref<Record<string, string>>({})
  const sessionAssetIndex = ref<Record<string, string>>({})
  const sessionId = ref('')
  const isSessionsLoading = ref(false)
  const isHistoryLoading = ref(false)
  const isHistoryFailed = ref(false)
  const isSessionCreating = ref(false)
  const isSessionSaving = ref(false)
  const isSubmitting = ref(false)
  const sessionSearch = ref('')
  const messages = ref<AgentChatMessage[]>([])
  const input = ref('')
  const isSending = ref(false)
  const sessionDialog = ref<{ kind: 'rename' | 'delete'; session: OpenCodeSession } | null>(null)
  const sessionTitleInput = ref('')
  const sessionDialogError = ref('')
  const messagesRef = ref<HTMLElement | null>(null)
  const currentAsset = reactive<{ id: string; name: string }>({ id: '', name: '' })

  let eventController: AbortController | null = null
  let eventReady: Promise<boolean> | null = null
  let connectionSequence = 0
  let requestSequence = 0
  let sessionListSequence = 0
  let eventStreamSequence = 0
  let historyEvents: AgentStreamEvent[] = []
  let assistantMessageIds = new Set<string>()
  let ignoredAbortError: { sessionId: string; sequence: number } | null = null
  let localMessageSeq = 0

  // ---------- 持久化（均不含凭据） ----------

  const storageKey = (baseKey: string, instance = api.value) =>
    `${baseKey}:${instance?.apiBase ?? ''}`

  const loadSessionAssetIndex = () => {
    try {
      sessionAssetIndex.value = JSON.parse(
        localStorage.getItem(storageKey(SESSION_ASSET_KEY)) ?? '{}',
      )
    } catch {
      sessionAssetIndex.value = {}
    }
  }

  const saveSessionAssetIndex = () => {
    try {
      localStorage.setItem(storageKey(SESSION_ASSET_KEY), JSON.stringify(sessionAssetIndex.value))
    } catch {
      // Browser storage is optional.
    }
  }

  const registerSessionAsset = (sid: string, assetId: string) => {
    if (!sid || !assetId) return
    sessionAssetIndex.value[sid] = assetId
    saveSessionAssetIndex()
  }

  const saveActiveSession = () => {
    try {
      if (sessionId.value) localStorage.setItem(storageKey(ACTIVE_SESSION_KEY), sessionId.value)
      else localStorage.removeItem(storageKey(ACTIVE_SESSION_KEY))
    } catch {
      // Browser storage is optional.
    }
  }

  const loadDefaultModel = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey(DEFAULT_MODEL_KEY)) ?? 'null')
      if (saved?.providerID && saved?.modelID) selectedModel.value = saved
    } catch {
      // 忽略损坏数据
    }
  }

  const saveDefaultModel = () => {
    if (selectedModel.value) {
      localStorage.setItem(storageKey(DEFAULT_MODEL_KEY), JSON.stringify(selectedModel.value))
    }
  }

  const restoreConnection = (): AgentApi | null => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(CONNECTION_KEY) ?? 'null')
      if (!saved?.apiBase) return null
      // Migrate old records that contained authHeader by overwriting them
      // before any connection attempt.
      sessionStorage.setItem(CONNECTION_KEY, JSON.stringify({ apiBase: saved.apiBase }))
      return new AgentApi(saved.apiBase)
    } catch {
      return null
    }
  }

  const persistConnection = (instance: AgentApi) => {
    if (instance.authHeader) {
      sessionStorage.removeItem(CONNECTION_KEY)
      return
    }
    sessionStorage.setItem(CONNECTION_KEY, JSON.stringify({ apiBase: instance.apiBase }))
  }

  // ---------- 连接 ----------

  const scrollToBottom = async () => {
    await nextTick()
    const container = messagesRef.value
    if (container) container.scrollTop = container.scrollHeight
  }

  const refreshSessions = async () => {
    if (!api.value) return
    const instance = api.value
    const sequence = ++sessionListSequence
    isSessionsLoading.value = true
    try {
      const loaded = (await instance.listSessions()) ?? []
      if (sequence !== sessionListSequence || instance !== api.value) return
      sessions.value = loaded.sort(
        (left, right) =>
          (right.time?.updated ?? right.time?.created ?? 0) -
          (left.time?.updated ?? left.time?.created ?? 0),
      )
    } catch (error) {
      if (sequence !== sessionListSequence || instance !== api.value) return
      connectionError.value = error instanceof Error ? error.message : '读取会话失败'
    } finally {
      if (sequence === sessionListSequence) isSessionsLoading.value = false
    }
  }

  const pickDefaultModel = () => {
    const models = connectedModels.value
    if (models.length === 0) return false
    const saved = selectedModel.value
    if (
      saved &&
      models.some((model) => model.providerID === saved.providerID && model.id === saved.modelID)
    ) {
      return true
    }
    const sameProvider = saved
      ? models.find((model) => model.providerID === saved.providerID)
      : undefined
    const target = sameProvider ?? models[0]
    if (!target) return false
    selectedModel.value = { providerID: target.providerID, modelID: target.id }
    return true
  }

  const loadModels = async (instance = api.value): Promise<boolean> => {
    if (!instance) return false
    const list = await instance.providers()
    if (instance !== api.value) return false
    const all = list.all ?? []
    const connected = new Set(list.connected ?? [])
    providerNames.value = Object.fromEntries(
      all.map((provider) => [provider.id, provider.name || provider.id]),
    )
    connectedModels.value = all
      .filter((provider) => connected.has(provider.id))
      .flatMap((provider) =>
        Object.values(provider.models ?? {}).map((model) => ({
          providerID: provider.id,
          id: model.id,
          name: model.name || model.id,
        })),
      )
    providerDefaults.value = list.default ?? {}
    availableProviders.value = all
      .filter((provider) => (list.default ?? {})[provider.id])
      .map((provider) => ({ id: provider.id, name: provider.name || provider.id }))
    return pickDefaultModel()
  }

  const connect = async (instance: AgentApi, nextView: AgentView = 'models') => {
    const sequence = ++connectionSequence
    closeEventStream()
    requestSequence += 1
    sessionListSequence += 1
    connectionState.value = 'connecting'
    connectionError.value = ''
    api.value = instance
    sessions.value = []
    sessionStatuses.value = {}
    sessionDrafts.value = {}
    selectedModel.value = null
    loadSessionAssetIndex()
    try {
      const health = await instance.health()
      if (sequence !== connectionSequence || instance !== api.value) return
      if (health && health.healthy === false) {
        throw new Error('OpenCode 服务器健康检查未通过')
      }
      connectionState.value = 'connected'
      persistConnection(instance)
      loadDefaultModel()
      const hasModel = await loadModels(instance)
      if (sequence !== connectionSequence || instance !== api.value) return
      view.value = hasModel ? nextView : 'models'
      await resetConversation()
      await refreshSessions()
      // A2（对齐旧版 e3dbde3c）：连接后进入空窗口「开始新对话」，不自动恢复上次会话
      saveActiveSession()
    } catch (error) {
      if (sequence !== connectionSequence || instance !== api.value) return
      connectionState.value = 'disconnected'
      api.value = null
      connectionError.value = error instanceof Error ? error.message : '连接 OpenCode 服务器失败'
      view.value = 'login'
    }
  }

  const loginLocalAgent = () => connect(new AgentApi(defaultAgentApiBase()))

  const loginRemoteAgent = async () => {
    const address = normalizeAgentServerAddress(remoteAddress.value)
    if (!address) {
      connectionError.value = '请输入远程服务器地址（IP:端口）'
      return
    }
    if (!isSecureRemoteAgentAddress(address)) {
      connectionError.value = '远程 Basic 认证仅支持 HTTPS；本机服务请使用“连接本机 Agent”'
      return
    }
    if (!remoteUsername.value || !remotePassword.value) {
      connectionError.value = '请输入远程服务器的用户名和密码'
      return
    }
    isLoggingIn.value = true
    try {
      await connect(
        new AgentApi(address, buildBasicAuthHeader(remoteUsername.value, remotePassword.value)),
      )
      // 登录成功即丢弃明文表单内容
      remoteUsername.value = ''
      remotePassword.value = ''
    } finally {
      isLoggingIn.value = false
    }
  }

  const authorizeProvider = async (providerID: string) => {
    if (!api.value || !providerApiKey.value || isAuthorizing.value) return
    isAuthorizing.value = true
    connectionError.value = ''
    try {
      await api.value.saveProviderKey(providerID, providerApiKey.value)
      providerApiKey.value = ''
      await api.value.disposeInstance().catch(() => null)
      const hasModel = await loadModels()
      if (hasModel) {
        view.value = 'models'
        toast('认证成功，已刷新可用模型', 'success')
      }
    } catch (error) {
      connectionError.value = error instanceof Error ? error.message : 'Provider 认证失败'
    } finally {
      isAuthorizing.value = false
    }
  }

  // ---------- 事件流 ----------

  const getOrCreatePart = (
    message: AgentChatMessage,
    type: 'reasoning' | 'text',
    partId: string,
  ) => {
    const key = `${type}:${partId}`
    let part = message.parts.find((item) => item.id === key)
    if (!part) {
      part = { id: key, type, text: '' }
      message.parts.push(part)
    }
    return part
  }

  const syncMessageText = (message: AgentChatMessage) => {
    message.reasoning = message.parts
      .filter((part) => part.type === 'reasoning')
      .map((part) => part.text)
      .filter(Boolean)
      .join('\n\n')
    message.content = message.parts
      .filter((part) => part.type === 'text')
      .map((part) => part.text)
      .filter(Boolean)
      .join('\n\n')
  }

  const finishPending = (fallback: string) => {
    const pending = messages.value.find((message) => message.status === 'thinking')
    if (pending && !pending.content) pending.content = fallback
    if (pending) pending.status = 'done'
    isSending.value = false
    if (sessionId.value) sessionStatuses.value[sessionId.value] = { type: 'idle' }
    void scrollToBottom()
    void refreshSessions()
    const sequence = requestSequence
    const sid = sessionId.value
    if (api.value && sid) {
      void api.value
        .listMessages(sid)
        .then((history) => {
          if (sequence === requestSequence && sid === sessionId.value && !isSending.value) {
            assistantMessageIds = new Set()
            messages.value = toChatMessages(history ?? [])
          }
        })
        .catch(() => null)
    }
  }

  // 用户主动中止后，OpenCode 仍会回一条 abort 错误（session.error / message.updated.info.error）。
  // 旧版用 shouldIgnoreNextAgentAbortError 吞掉它；这里统一判断，避免弹出英文「Aborted」错误条。
  const consumeIgnoredAbortError = (errorSession: string) => {
    const ignored = ignoredAbortError
    return !!ignored && ignored.sessionId === errorSession && ignored.sequence === requestSequence
  }

  const markResponseFailed = (errorText: string) => {
    const pending = messages.value.find((message) => message.status === 'thinking')
    if (pending) {
      pending.status = 'error'
      if (!pending.parts.some((part) => part.id === `${pending.id}:error`)) {
        pending.parts.push({ id: `${pending.id}:error`, type: 'text', text: errorText })
      }
      syncMessageText(pending)
    }
    isSending.value = false
    if (sessionId.value) sessionStatuses.value[sessionId.value] = { type: 'idle' }
    connectionError.value = errorText
    void scrollToBottom()
  }

  const handleAgentEvent = (event: AgentStreamEvent) => {
    const props = event.properties ?? {}
    if (event.type === 'session.updated' && props.info?.id) {
      sessions.value = sessions.value.map((session) =>
        session.id === props.info?.id ? { ...session, ...props.info } : session,
      )
    }
    const eventSession = props.sessionID || props.info?.sessionID || props.part?.sessionID || ''
    if (eventSession && event.type === 'session.status' && props.status?.type) {
      sessionStatuses.value[eventSession] = { type: props.status.type }
    }
    if (eventSession && eventSession !== sessionId.value) return
    if (isHistoryLoading.value) {
      historyEvents.push(event)
      return
    }

    if (event.type === 'session.status' && ['busy', 'retry'].includes(props.status?.type ?? '')) {
      isSending.value = true
    }

    if (event.type === 'message.updated' && props.info?.role === 'assistant' && props.info.id) {
      // 中止后的 message.updated 会带 Aborted 错误：直接跳过，别新建气泡、别弹错误条
      if (props.info.error && consumeIgnoredAbortError(eventSession || sessionId.value)) return
      assistantMessageIds.add(props.info.id)
      let pending = messages.value.find((message) => message.status === 'thinking')
      if (pending?.messageId && pending.messageId !== props.info.id) {
        pending.status = 'done'
        pending = undefined
      }
      if (!pending && !messages.value.some((message) => message.messageId === props.info?.id)) {
        pending = {
          id: props.info.id,
          role: 'assistant',
          parts: [],
          reasoning: '',
          content: '',
          status: 'thinking',
          messageId: props.info.id,
        }
        messages.value.push(pending)
      }
      if (pending && !pending.messageId) pending.messageId = props.info.id
      if (props.info.error) {
        markResponseFailed(extractAgentError(props.info.error) || '模型响应失败')
      }
      return
    }

    if (event.type === 'message.part.updated' && props.part) {
      const messageID = props.part.messageID ?? ''
      if (!messageID || !assistantMessageIds.has(messageID)) return
      const target =
        messages.value.find((message) => message.messageId === messageID) ??
        messages.value.find((message) => message.status === 'thinking')
      if (!target) return
      const type = props.part.type === 'reasoning' ? 'reasoning' : 'text'
      const part = getOrCreatePart(target, type, props.part.id || type)
      // 服务端推送全量 part.text，按 part.id 覆盖写
      part.text = props.part.text ?? ''
      syncMessageText(target)
      void scrollToBottom()
      return
    }

    if (event.type === 'message.part.delta' && props.messageID && props.partID) {
      const target = messages.value.find((message) => message.messageId === props.messageID)
      const part = target?.parts.find((item) => item.id.endsWith(`:${props.partID}`))
      if (target && part && props.field === 'text') {
        part.text += props.delta ?? ''
        syncMessageText(target)
        void scrollToBottom()
      }
      return
    }

    if (
      event.type === 'session.idle' ||
      (event.type === 'session.status' && props.status?.type === 'idle')
    ) {
      finishPending('Agent 已完成处理，但没有返回文本结果。')
      return
    }

    if (event.type === 'session.error') {
      const errorSession = eventSession || sessionId.value
      if (consumeIgnoredAbortError(errorSession)) {
        // 中止后的错误不是故障：保留本地「用户终止响应」气泡，也不要重载历史
        // （服务端历史里这条消息带 Aborted 错误，重载会把英文错误盖回来）
        isSending.value = false
        if (sessionId.value) sessionStatuses.value[sessionId.value] = { type: 'idle' }
        return
      }
      markResponseFailed(extractAgentError(props.error) || 'Agent 处理出错，请稍后重试')
    }
  }

  const replayHistoryEvents = () => {
    const queued = historyEvents
    historyEvents = []
    const parts = new Map<string, NonNullable<AgentStreamEvent['properties']>['part']>()
    for (const event of queued) {
      const props = event.properties
      if (event.type === 'message.part.updated' && props?.part?.id) {
        parts.set(props.part.id, { ...props.part })
      } else if (event.type === 'message.part.delta' && props?.partID) {
        const part = parts.get(props.partID)
        if (part && props.field === 'text') part.text = (part.text ?? '') + (props.delta ?? '')
      } else {
        handleAgentEvent(event)
      }
    }
    for (const part of parts.values()) {
      if (!part) continue
      const target = messages.value.find((message) => message.messageId === part.messageID)
      const existing = target?.parts.find((item) => item.id === `${part.type}:${part.id}`)
      if (!existing || (part.text ?? '').startsWith(existing.text)) {
        handleAgentEvent({ type: 'message.part.updated', properties: { part } })
      }
    }
  }

  const closeEventStream = () => {
    eventStreamSequence += 1
    eventController?.abort()
    eventController = null
    eventReady = null
  }

  const connectEvents = (): Promise<boolean> => {
    if (!api.value) return Promise.resolve(false)
    if (eventController) return eventReady ?? Promise.resolve(true)
    eventController = new AbortController()
    const controller = eventController
    const sequence = ++eventStreamSequence
    const instance = api.value
    let settleReady: (connected: boolean) => void = () => undefined
    eventReady = new Promise<boolean>((resolve) => {
      settleReady = resolve
    })
    void instance
      .openEventStream(controller.signal, handleAgentEvent, () => settleReady(true))
      .then(() => {
        if (sequence === eventStreamSequence && !controller.signal.aborted) {
          connectionState.value = 'disconnected'
          connectionError.value = 'Agent 事件流连接已断开'
        }
      })
      .catch((error) => {
        settleReady(false)
        if (sequence === eventStreamSequence && !controller.signal.aborted) {
          connectionState.value = 'disconnected'
          connectionError.value = error instanceof Error ? error.message : 'Agent 事件流连接失败'
        }
      })
      .finally(() => {
        if (sequence === eventStreamSequence && eventController === controller) {
          eventController = null
          eventReady = null
        }
      })
    return eventReady
  }

  const suspend = () => {
    connectionSequence += 1
    requestSequence += 1
    sessionListSequence += 1
    ignoredAbortError = null
    historyEvents = []
    isHistoryLoading.value = false
    isSubmitting.value = false
    closeEventStream()
  }

  // ---------- 会话与消息 ----------

  const resetConversation = async () => {
    requestSequence += 1
    closeEventStream()
    sessionId.value = ''
    messages.value = []
    assistantMessageIds = new Set()
    historyEvents = []
    ignoredAbortError = null
    isSending.value = false
    isHistoryLoading.value = false
    isHistoryFailed.value = false
    isSubmitting.value = false
    connectionError.value = ''
    await scrollToBottom()
  }

  const toChatMessages = (list: OpenCodeMessage[]): AgentChatMessage[] => {
    const result: AgentChatMessage[] = []
    for (const item of list) {
      const role = item.info?.role as AgentChatMessage['role'] | undefined
      if (role !== 'user' && role !== 'assistant') continue
      const parts: AgentChatPart[] = (item.parts ?? [])
        .filter((part) => part.type === 'reasoning' || part.type === 'text')
        .map((part, index) => ({
          id: `${part.type}:${part.id ?? index}`,
          type: part.type as 'reasoning' | 'text',
          text: part.text ?? '',
          // 对齐旧版：历史消息里的「思考过程」默认收起，正文默认展开
          collapsed: part.type === 'reasoning',
        }))
      const message: AgentChatMessage = {
        id: item.info?.id || `history-${result.length}`,
        role,
        parts,
        reasoning: '',
        content: '',
        status: item.info?.error ? 'error' : 'done',
        messageId: item.info?.id,
      }
      if (item.info?.error) {
        const errorText = extractAgentError(item.info.error) || '模型响应失败'
        message.parts.push({ id: `${message.id}:error`, type: 'text', text: errorText })
      }
      if (role === 'assistant') assistantMessageIds.add(item.info?.id ?? '')
      syncMessageText(message)
      if (role === 'user') message.content = message.content.replace(KNOWLEDGE_PREFIX_RE, '')
      result.push(message)
    }
    return result
  }

  const openConversation = async (sid: string) => {
    if (!api.value || isSessionCreating.value || isSessionSaving.value || isSubmitting.value) return
    if (sessionId.value) sessionDrafts.value[sessionId.value] = input.value
    await resetConversation()
    sessionId.value = sid
    input.value = sessionDrafts.value[sid] ?? ''
    saveActiveSession()
    const sequence = requestSequence
    isHistoryLoading.value = true
    isHistoryFailed.value = false
    try {
      const instance = api.value
      const connected = await connectEvents()
      if (sequence !== requestSequence || sid !== sessionId.value || instance !== api.value) return
      if (!connected) throw new Error(connectionError.value || 'Agent 事件流连接失败')
      const statuses = await instance.sessionStatuses()
      const history = (await instance.listMessages(sid)) ?? []
      if (sequence !== requestSequence || sid !== sessionId.value || instance !== api.value) return
      sessionStatuses.value = statuses ?? {}
      messages.value = toChatMessages(history)
      const context = history
        .find((message) => message.info.role === 'user')
        ?.parts?.find((part) => part.type === 'text')?.text
      const assetId = context?.match(KNOWLEDGE_ID_RE)?.[1]
      if (assetId && !sessionAssetIndex.value[sid]) registerSessionAsset(sid, assetId)
      const historicalModel = [...history].reverse().find((message) => message.info.model)
        ?.info.model
      if (
        historicalModel?.providerID &&
        historicalModel.modelID &&
        connectedModels.value.some(
          (model) =>
            model.providerID === historicalModel.providerID && model.id === historicalModel.modelID,
        )
      ) {
        selectedModel.value = {
          providerID: historicalModel.providerID,
          modelID: historicalModel.modelID,
        }
      }
      isSending.value = !!statuses[sid] && statuses[sid]?.type !== 'idle'
      if (isSending.value) {
        const last = messages.value.at(-1)
        if (last?.role === 'assistant' && last.status !== 'error') last.status = 'thinking'
        else {
          messages.value.push({
            id: `agent-assistant-${++localMessageSeq}`,
            role: 'assistant',
            parts: [],
            reasoning: '',
            content: '',
            status: 'thinking',
          })
        }
      }
      isHistoryLoading.value = false
      replayHistoryEvents()
    } catch (error) {
      if (sequence !== requestSequence || sid !== sessionId.value) return
      isHistoryFailed.value = true
      historyEvents = []
      closeEventStream()
      connectionError.value = error instanceof Error ? error.message : '读取会话历史失败'
    } finally {
      if (sequence === requestSequence) isHistoryLoading.value = false
    }
    await scrollToBottom()
  }

  const newConversation = async () => {
    if (!api.value || isSessionSaving.value || isSubmitting.value) return
    if (sessionId.value) sessionDrafts.value[sessionId.value] = input.value
    // A2（对齐旧版 e3dbde3c）：只清空窗口，「开始新对话」；会话在首次发送时惰性创建
    await resetConversation()
    view.value = 'chat'
    saveActiveSession()
  }

  const showSessionDialog = (kind: 'rename' | 'delete', session: OpenCodeSession) => {
    sessionDialog.value = { kind, session }
    sessionTitleInput.value = session.title ?? ''
    sessionDialogError.value = ''
  }

  const submitSessionDialog = async () => {
    const dialog = sessionDialog.value
    if (!dialog || !api.value || isSessionSaving.value) return
    const { kind, session } = dialog
    const title = sessionTitleInput.value.trim()
    if (kind === 'rename' && !title) {
      sessionDialogError.value = '请输入会话标题'
      return
    }
    isSessionSaving.value = true
    sessionDialogError.value = ''
    try {
      if (kind === 'rename') {
        const updated = await api.value.renameSession(session.id, title)
        sessions.value = sessions.value.map((item) =>
          item.id === session.id ? { ...item, ...updated, title } : item,
        )
        sessionDialog.value = null
        return
      }
      const statuses = await api.value.sessionStatuses()
      if (statuses[session.id] && statuses[session.id]?.type !== 'idle') {
        await api.value.abort(session.id)
      }
      const deleted = await api.value.deleteSession(session.id)
      if (deleted === false) throw new Error('服务端未确认删除会话，请重试')
      sessions.value = sessions.value.filter((item) => item.id !== session.id)
      delete sessionAssetIndex.value[session.id]
      saveSessionAssetIndex()
      delete sessionDrafts.value[session.id]
      delete sessionStatuses.value[session.id]
      if (sessionId.value === session.id) {
        await resetConversation()
        saveActiveSession()
      }
      sessionDialog.value = null
    } catch (error) {
      sessionDialogError.value = error instanceof Error ? error.message : '保存会话失败'
    } finally {
      isSessionSaving.value = false
    }
  }

  const abortAgentSession = async () => {
    if (!api.value || !sessionId.value) return
    const abortingSessionId = sessionId.value
    const sequence = ++requestSequence
    ignoredAbortError = { sessionId: abortingSessionId, sequence }
    try {
      await api.value.abort(abortingSessionId)
    } catch {
      // 中止失败也按已完成处理，等待事件流收尾
    }
    if (sequence !== requestSequence) return
    const pending = messages.value.find((message) => message.status === 'thinking')
    if (pending) {
      pending.parts = [{ id: 'text:abort', type: 'text', text: '用户终止响应' }]
      pending.content = '用户终止响应'
      pending.status = 'done'
    }
    isSending.value = false
    sessionStatuses.value[abortingSessionId] = { type: 'idle' }
    void scrollToBottom()
  }

  const ensureSession = async () => {
    if (sessionId.value) return sessionId.value
    if (!api.value) throw new Error('未连接 OpenCode 服务器')
    const created = await api.value.createSessionWithDetail()
    if (!created?.id) throw new Error('Agent 服务没有返回会话 ID')
    sessionId.value = created.id
    registerSessionAsset(created.id, currentAsset.id)
    saveActiveSession()
    sessions.value = [created, ...sessions.value.filter((session) => session.id !== created.id)]
    return sessionId.value
  }

  const sendMessage = async () => {
    const question = input.value.trim()
    if (
      !question ||
      isSending.value ||
      isHistoryLoading.value ||
      isHistoryFailed.value ||
      isSessionCreating.value ||
      isSessionSaving.value ||
      isSubmitting.value
    )
      return
    if (!api.value) {
      connectionError.value = '尚未连接 OpenCode 服务器'
      return
    }
    if (!selectedModel.value) {
      view.value = 'models'
      return
    }
    input.value = ''
    localMessageSeq += 1
    messages.value.push({
      id: `agent-user-${localMessageSeq}`,
      role: 'user',
      parts: [],
      reasoning: '',
      content: question,
      status: 'done',
    })
    messages.value.push({
      id: `agent-assistant-${localMessageSeq}`,
      role: 'assistant',
      parts: [],
      reasoning: '',
      content: '',
      status: 'thinking',
    })
    isSending.value = true
    const sequence = ++requestSequence
    ignoredAbortError = null
    isSubmitting.value = true
    void scrollToBottom()
    try {
      const sid = await ensureSession()
      if (sequence !== requestSequence) return
      void connectEvents()
      const assetId = sessionAssetIndex.value[sid] || currentAsset.id
      if (!sessionAssetIndex.value[sid]) registerSessionAsset(sid, assetId)
      const knowledgePrefix = assetId ? `当前会话对应的知识库 ID 是 ${assetId}。\n\n` : ''
      // A2（对齐旧版 e3dbde3c）：不再用首条问题改写标题，标题由 OpenCode 生成
      sessionStatuses.value[sid] = { type: 'busy' }
      await api.value.promptAsync(
        sid,
        selectedModel.value.providerID,
        selectedModel.value.modelID,
        `${knowledgePrefix}${question}`,
      )
    } catch (error) {
      if (sequence !== requestSequence) return
      markResponseFailed(error instanceof Error ? error.message : '发送失败')
    } finally {
      if (sequence === requestSequence) isSubmitting.value = false
    }
  }

  // ---------- 视图辅助 ----------

  const sessionAssetName = (sid: string) => {
    const assetId = sessionAssetIndex.value[sid] ?? ''
    return assetId && assetId === currentAsset.id ? currentAsset.name : assetId
  }

  const filteredSessions = computed(() => {
    const keyword = sessionSearch.value.trim().toLowerCase()
    return sessions.value
      .filter((session) => !session.parentID)
      .filter((session) => {
        if (!keyword) return true
        const title = (session.title ?? '').toLowerCase()
        const asset = (sessionAssetName(session.id) ?? '').toLowerCase()
        return title.includes(keyword) || asset.includes(keyword)
      })
  })

  const activeSessionTitle = computed(
    () => sessions.value.find((session) => session.id === sessionId.value)?.title || '开始新对话',
  )

  const filteredModels = computed(() => {
    const keyword = modelSearch.value.trim().toLowerCase()
    if (!keyword) return connectedModels.value
    return connectedModels.value.filter(
      (model) =>
        model.name.toLowerCase().includes(keyword) ||
        model.providerID.toLowerCase().includes(keyword),
    )
  })

  const filteredProviders = computed(() => {
    const keyword = providerSearch.value.trim().toLowerCase()
    if (!keyword) return availableProviders.value
    return availableProviders.value.filter((provider) =>
      provider.name.toLowerCase().includes(keyword),
    )
  })

  const displayPartsOf = (message: AgentChatMessage): AgentChatPart[] => {
    // 用户消息没有 parts（本地发送时 parts 为空，历史消息只回填 content），
    // 必须回退到 content，否则用户气泡里没有任何文字（旧版为 <p>{{ message.content }}</p>）。
    if (message.role === 'user') {
      return message.content
        ? [{ id: `${message.id}:user-text`, type: 'text', text: message.content }]
        : []
    }
    const parts = message.parts.filter(
      (part) => part.text || (part.type === 'reasoning' && message.status === 'thinking'),
    )
    if (parts.length > 0) return parts
    if (message.content) return [{ id: 'text:fallback', type: 'text', text: message.content }]
    if (message.status === 'thinking') {
      return [{ id: 'reasoning:placeholder', type: 'reasoning', text: '' }]
    }
    return []
  }

  const setAsset = (asset: { id: string; name: string } | null) => {
    const nextId = asset?.id ?? ''
    if (currentAsset.id === nextId) return
    const isInitialAsset = !currentAsset.id
    if (sessionId.value) sessionDrafts.value[sessionId.value] = input.value
    currentAsset.id = nextId
    currentAsset.name = asset?.name ?? ''
    if (isInitialAsset) return
    void resetConversation().then(saveActiveSession)
    sessionSearch.value = ''
  }

  const restore = async () => {
    const saved = restoreConnection()
    if (!saved) return
    await connect(saved, 'chat')
  }

  return {
    // 状态
    view,
    api,
    connectionState,
    connectionError,
    isLoggingIn,
    remoteUsername,
    remotePassword,
    remoteAddress,
    connectedModels,
    providerNames,
    availableProviders,
    selectedModel,
    providerApiKey,
    isAuthorizing,
    modelSearch,
    providerSearch,
    expandedProviderId,
    sessions,
    sessionStatuses,
    sessionId,
    isSessionsLoading,
    isHistoryLoading,
    isHistoryFailed,
    isSessionCreating,
    isSessionSaving,
    isSubmitting,
    sessionSearch,
    messages,
    input,
    isSending,
    sessionDialog,
    sessionTitleInput,
    sessionDialogError,
    messagesRef,
    filteredSessions,
    activeSessionTitle,
    filteredModels,
    filteredProviders,
    displayPartsOf,
    // 动作
    setAsset,
    restore,
    loginLocalAgent,
    loginRemoteAgent,
    authorizeProvider,
    refreshSessions,
    openConversation,
    newConversation,
    showSessionDialog,
    submitSessionDialog,
    abortAgentSession,
    closeEventStream,
    suspend,
    sendMessage,
    scrollToBottom,
    sessionAssetName,
    selectModel: (providerID: string, modelID: string) => {
      selectedModel.value = { providerID, modelID }
      saveDefaultModel()
      view.value = 'chat'
    },
    goBack: () => {
      view.value = connectionState.value === 'connected' ? 'chat' : 'login'
    },
  }
}
