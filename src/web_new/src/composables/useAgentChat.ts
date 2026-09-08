import { computed, nextTick, reactive, ref } from 'vue'
import {
  AgentApi,
  buildBasicAuthHeader,
  defaultAgentApiBase,
  isSecureRemoteAgentAddress,
  normalizeAgentServerAddress,
  type OpenCodeMessage,
  type OpenCodeSession,
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
const DEFAULT_MODEL_KEY = 'witty-ub.agent-default-model'
const KNOWLEDGE_PREFIX_RE = /^当前(?:页面选中|会话对应)的知识库 ID 是 [^。]+。\n\n/

let state: ReturnType<typeof createAgentChatState> | null = null

export function useAgentChat() {
  if (!state) state = createAgentChatState()
  return state
}

function createAgentChatState() {
  const { toast } = useToast()

  const view = ref<AgentView>('login')
  const api = ref<AgentApi | null>(null)
  const connectionState = ref<'connected' | 'connecting' | 'disconnected'>('disconnected')
  const connectionError = ref('')
  const isLoggingIn = ref(false)

  // 远程登录表单（内存态，不持久化）
  const remoteUsername = ref('')
  const remotePassword = ref('')
  const remoteAddress = ref('')

  // 模型 / Provider
  const connectedModels = ref<{ providerID: string; id: string; name: string }[]>([])
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
  const sessionId = ref('')
  const isSessionsLoading = ref(false)
  const sessionSearch = ref('')
  const messages = ref<AgentChatMessage[]>([])
  const input = ref('')
  const isSending = ref(false)
  const messagesRef = ref<HTMLElement | null>(null)
  const currentAsset = reactive<{ id: string; name: string }>({ id: '', name: '' })

  let eventController: AbortController | null = null
  let assistantMessageIds = new Set<string>()
  let shouldIgnoreNextAbortError = false
  let localMessageSeq = 0

  // ---------- 持久化（均不含凭据） ----------

  const loadSessionAssetIndex = (): Record<string, string> => {
    try {
      return JSON.parse(localStorage.getItem(SESSION_ASSET_KEY) ?? '{}')
    } catch {
      return {}
    }
  }

  const saveSessionAssetIndex = (index: Record<string, string>) => {
    localStorage.setItem(SESSION_ASSET_KEY, JSON.stringify(index))
  }

  const registerSessionAsset = (sid: string, assetId: string) => {
    if (!sid || !assetId) return
    const index = loadSessionAssetIndex()
    index[sid] = assetId
    saveSessionAssetIndex(index)
  }

  const loadDefaultModel = () => {
    try {
      const saved = JSON.parse(localStorage.getItem(DEFAULT_MODEL_KEY) ?? 'null')
      if (saved?.providerID && saved?.modelID) selectedModel.value = saved
    } catch {
      // 忽略损坏数据
    }
  }

  const saveDefaultModel = () => {
    if (selectedModel.value) {
      localStorage.setItem(DEFAULT_MODEL_KEY, JSON.stringify(selectedModel.value))
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
    isSessionsLoading.value = true
    try {
      sessions.value = (await api.value.listSessions()) ?? []
    } catch (error) {
      connectionError.value = error instanceof Error ? error.message : '读取会话失败'
    } finally {
      isSessionsLoading.value = false
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

  const loadModels = async (): Promise<boolean> => {
    if (!api.value) return false
    const list = await api.value.providers()
    const all = list.all ?? []
    const connected = new Set(list.connected ?? [])
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
    connectionState.value = 'connecting'
    connectionError.value = ''
    api.value = instance
    try {
      const health = await instance.health()
      if (health && health.healthy === false) {
        throw new Error('OpenCode 服务器健康检查未通过')
      }
      connectionState.value = 'connected'
      persistConnection(instance)
      loadDefaultModel()
      const hasModel = await loadModels()
      view.value = hasModel ? nextView : 'models'
      if (view.value === 'chat') {
        await refreshSessions()
        await resetConversation()
      }
    } catch (error) {
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
    void scrollToBottom()
    void refreshSessions()
  }

  const markResponseFailed = (errorText: string) => {
    const pending = messages.value.find((message) => message.status === 'thinking')
    if (pending) {
      pending.status = 'error'
      if (!pending.content) pending.content = errorText
    }
    isSending.value = false
    connectionError.value = errorText
    void scrollToBottom()
  }

  const handleAgentEvent = (event: { type: string; properties?: any }) => {
    const props = event.properties ?? {}
    const eventSession = props.sessionID || props.info?.sessionID || props.part?.sessionID || ''
    if (eventSession && eventSession !== sessionId.value) return

    if (event.type === 'message.updated' && props.info?.role === 'assistant' && props.info.id) {
      assistantMessageIds.add(props.info.id)
      const pending = messages.value.find((message) => message.status === 'thinking')
      if (pending && !pending.messageId) pending.messageId = props.info.id
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

    if (
      event.type === 'session.idle' ||
      (event.type === 'session.status' && props.status?.type === 'idle')
    ) {
      finishPending('Agent 已完成处理，但没有返回文本结果。')
      return
    }

    if (event.type === 'session.error') {
      if (shouldIgnoreNextAbortError) {
        shouldIgnoreNextAbortError = false
        finishPending('')
        return
      }
      markResponseFailed('Agent 处理出错，请稍后重试')
    }
  }

  const connectEvents = async () => {
    if (!api.value || eventController) return
    eventController = new AbortController()
    const controller = eventController
    try {
      await api.value.openEventStream(controller.signal, handleAgentEvent)
      if (!controller.signal.aborted) {
        connectionState.value = 'disconnected'
        connectionError.value = 'Agent 事件流连接已断开'
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        connectionState.value = 'disconnected'
        connectionError.value = error instanceof Error ? error.message : 'Agent 事件流连接失败'
      }
    } finally {
      if (eventController === controller) eventController = null
    }
  }

  // ---------- 会话与消息 ----------

  const resetConversation = async () => {
    sessionId.value = ''
    messages.value = []
    assistantMessageIds = new Set()
    isSending.value = false
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
        }))
      const message: AgentChatMessage = {
        id: item.info?.id || `history-${result.length}`,
        role,
        parts,
        reasoning: '',
        content: '',
        status: 'done',
        messageId: item.info?.id,
      }
      if (role === 'assistant') assistantMessageIds.add(item.info?.id ?? '')
      syncMessageText(message)
      if (role === 'user') message.content = message.content.replace(KNOWLEDGE_PREFIX_RE, '')
      result.push(message)
    }
    return result
  }

  const openConversation = async (sid: string) => {
    if (!api.value || isSending.value) return
    sessionId.value = sid
    messages.value = []
    assistantMessageIds = new Set()
    try {
      const history = (await api.value.listMessages(sid)) ?? []
      messages.value = toChatMessages(history)
    } catch (error) {
      connectionError.value = error instanceof Error ? error.message : '读取会话历史失败'
    }
    void connectEvents()
    await scrollToBottom()
  }

  const newConversation = async () => {
    if (isSending.value) {
      await abortAgentSession()
    }
    await resetConversation()
    view.value = 'chat'
  }

  const renameConversation = async (sid: string) => {
    const title = window.prompt('新的会话名称')?.trim()
    if (!title || !api.value) return
    try {
      await api.value.renameSession(sid, title)
      await refreshSessions()
    } catch (error) {
      toast(error instanceof Error ? error.message : '会话改名失败', 'error')
    }
  }

  const deleteConversation = async (sid: string) => {
    if (!api.value || !window.confirm('确认删除该会话？')) return
    try {
      await api.value.deleteSession(sid)
      const index = loadSessionAssetIndex()
      delete index[sid]
      saveSessionAssetIndex(index)
      await refreshSessions()
      if (sessionId.value === sid) await resetConversation()
    } catch (error) {
      toast(error instanceof Error ? error.message : '删除会话失败', 'error')
    }
  }

  const abortAgentSession = async () => {
    if (!api.value || !sessionId.value) return
    shouldIgnoreNextAbortError = true
    try {
      await api.value.abort(sessionId.value)
    } catch {
      // 中止失败也按已完成处理，等待事件流收尾
    }
    const pending = messages.value.find((message) => message.status === 'thinking')
    if (pending) {
      pending.parts = [{ id: 'text:abort', type: 'text', text: '用户终止响应' }]
      pending.content = '用户终止响应'
      pending.status = 'done'
    }
    isSending.value = false
    void scrollToBottom()
  }

  const ensureSession = async () => {
    if (sessionId.value) return sessionId.value
    if (!api.value) throw new Error('未连接 OpenCode 服务器')
    const created = await api.value.createSession()
    sessionId.value = created.id
    registerSessionAsset(created.id, currentAsset.id)
    sessions.value = [created, ...sessions.value]
    return sessionId.value
  }

  const sendMessage = async () => {
    const question = input.value.trim()
    if (!question || isSending.value) return
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
    void scrollToBottom()
    try {
      const sid = await ensureSession()
      void connectEvents()
      const knowledgePrefix = currentAsset.id
        ? `当前会话对应的知识库 ID 是 ${currentAsset.id}。\n\n`
        : ''
      await api.value.promptAsync(
        sid,
        selectedModel.value.providerID,
        selectedModel.value.modelID,
        `${knowledgePrefix}${question}`,
      )
    } catch (error) {
      markResponseFailed(error instanceof Error ? error.message : '发送失败')
    }
  }

  // ---------- 视图辅助 ----------

  const sessionAssetName = (sid: string) => {
    const assetId = loadSessionAssetIndex()[sid] ?? ''
    return assetId && assetId === currentAsset.id ? currentAsset.name : assetId
  }

  const filteredSessions = computed(() => {
    const keyword = sessionSearch.value.trim().toLowerCase()
    if (!keyword) return sessions.value
    return sessions.value.filter((session) => {
      const title = (session.title ?? '').toLowerCase()
      const asset = (sessionAssetName(session.id) ?? '').toLowerCase()
      return title.includes(keyword) || asset.includes(keyword)
    })
  })

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
    if (message.role !== 'assistant') return []
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
    currentAsset.id = nextId
    currentAsset.name = asset?.name ?? ''
    // 切资产：重置会话与搜索（会话索引保留，历史可通过搜索找回）
    sessionId.value = ''
    messages.value = []
    sessionSearch.value = ''
  }

  const restore = async () => {
    const saved = restoreConnection()
    if (!saved) return
    await connect(saved, 'login')
    if (connectionState.value === 'connected') {
      view.value = 'chat'
      await refreshSessions()
    }
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
    availableProviders,
    selectedModel,
    providerApiKey,
    isAuthorizing,
    modelSearch,
    providerSearch,
    expandedProviderId,
    sessions,
    sessionId,
    isSessionsLoading,
    sessionSearch,
    messages,
    input,
    isSending,
    messagesRef,
    filteredSessions,
    filteredModels,
    filteredProviders,
    displayPartsOf,
    // 动作
    setAsset,
    restore,
    loginLocalAgent,
    loginRemoteAgent,
    authorizeProvider,
    openConversation,
    newConversation,
    renameConversation,
    deleteConversation,
    abortAgentSession,
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
