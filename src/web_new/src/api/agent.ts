// OpenCode 诊断助手客户端：本机走同源 /agent-api 反代（免认证），
// 远程直连 OpenCode 服务地址并使用 Basic Authorization。
// 凭据只保存在当前页面内存，并且仅允许通过 HTTPS 发送。

export type OpenCodeSession = {
  id: string
  title?: string
  parentID?: string
  time?: { created?: number; updated?: number }
}

export type OpenCodeModel = { id: string; providerID: string; name?: string }

export type OpenCodeProvider = {
  id: string
  name?: string
  models?: Record<string, OpenCodeModel>
}

export type OpenCodeProviderList = {
  all?: OpenCodeProvider[]
  connected?: string[]
  default?: Record<string, string>
}

export type OpenCodeMessagePart = { id?: string; type?: string; text?: string }

export type OpenCodeMessage = {
  info: {
    id?: string
    role?: string
    sessionID?: string
    error?: unknown
    model?: { providerID?: string; modelID?: string }
  }
  parts?: OpenCodeMessagePart[]
}

export type OpenCodeSessionStatus = { type?: string }

/** 受限操作授权请求：Agent 要执行 bash 等操作时由服务端挂起，等前端答复（once / reject）。 */
export type AgentPermissionRequest = {
  id: string
  sessionID: string
  permission: string
  patterns: string[]
  metadata?: Record<string, unknown>
  always?: string[]
  tool?: { messageID: string; callID: string }
}

/** 结构化问询的一道题：选项由 Agent 给出，允许补充自定义答案。 */
export type AgentQuestion = {
  question: string
  header: string
  options: Array<{ label: string; description: string }>
  multiple?: boolean
  custom?: boolean
}

export type AgentQuestionRequest = {
  id: string
  sessionID: string
  questions: AgentQuestion[]
  tool?: { messageID: string; callID: string }
}

export type AgentStreamEvent = {
  type: string
  properties?: {
    sessionID?: string
    info?: {
      id?: string
      role?: string
      sessionID?: string
      title?: string
      error?: unknown
      time?: { created?: number; updated?: number }
    }
    part?: { id?: string; type?: string; text?: string; sessionID?: string; messageID?: string }
    status?: { type?: string }
    error?: unknown
    messageID?: string
    partID?: string
    field?: string
    delta?: string
    // permission.* / question.* 事件的字段（授权卡与问询卡的数据来源）
    id?: string
    requestID?: string
    permission?: string
    type?: string
    patterns?: string[]
    pattern?: string | string[]
    title?: string
    metadata?: Record<string, unknown>
    always?: string[]
    tool?: { messageID: string; callID: string }
    questions?: AgentQuestion[]
    reply?: 'once' | 'always' | 'reject'
  }
}

export const AGENT_NAME = 'witty-ub-diagnostician'

export const normalizeAgentServerAddress = (raw: string) => {
  const value = raw.trim().replace(/\/+$/, '')
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value
  if (value.startsWith('/')) return value
  return `https://${value}`
}

export const isSecureRemoteAgentAddress = (address: string) => {
  try {
    return new URL(address).protocol === 'https:'
  } catch {
    return false
  }
}

export const buildBasicAuthHeader = (username: string, password: string) =>
  `Basic ${btoa(unescape(encodeURIComponent(`${username}:${password}`)))}`

export class AgentApi {
  apiBase: string
  authHeader: string

  constructor(apiBase: string, authHeader = '') {
    this.apiBase = apiBase.replace(/\/+$/, '')
    this.authHeader = authHeader
  }

  headers(withBody = false): Record<string, string> {
    return {
      ...(withBody ? { 'Content-Type': 'application/json' } : {}),
      ...(this.authHeader ? { Authorization: this.authHeader } : {}),
    }
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.apiBase}${path}`, {
      ...init,
      headers: this.headers(!!init.body),
    })
    if (response.status === 204) return null as T
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(extractAgentError(data) || `请求失败：${response.status}`)
    }
    return data as T
  }

  health() {
    return this.request<{ healthy?: boolean; version?: string }>('/global/health')
  }

  providers() {
    return this.request<OpenCodeProviderList>('/provider')
  }

  saveProviderKey(providerID: string, key: string) {
    return this.request<boolean>(`/auth/${encodeURIComponent(providerID)}`, {
      method: 'PUT',
      body: JSON.stringify({ type: 'api', key }),
    })
  }

  disposeInstance() {
    return this.request<unknown>('/instance/dispose', { method: 'POST' })
  }

  listSessions() {
    return this.request<OpenCodeSession[]>('/session')
  }

  // 不预置标题，由服务端生成；创建后再取一次会话详情
  createSession(title?: string) {
    return this.request<OpenCodeSession>('/session', {
      method: 'POST',
      body: JSON.stringify(title ? { title } : {}),
    })
  }

  createSessionWithDetail(title?: string) {
    return this.createSession(title).then(async (created) => {
      if (!created?.id) return created
      return this.getSession(created.id)
    })
  }

  getSession(id: string) {
    return this.request<OpenCodeSession>(`/session/${encodeURIComponent(id)}`)
  }

  renameSession(id: string, title: string) {
    return this.request<OpenCodeSession>(`/session/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    })
  }

  deleteSession(id: string) {
    return this.request<unknown>(`/session/${encodeURIComponent(id)}`, { method: 'DELETE' })
  }

  listMessages(sessionId: string) {
    return this.request<OpenCodeMessage[]>(`/session/${encodeURIComponent(sessionId)}/message`)
  }

  sessionStatuses() {
    return this.request<Record<string, OpenCodeSessionStatus>>('/session/status')
  }

  promptAsync(sessionId: string, providerID: string, modelID: string, text: string) {
    return this.request<unknown>(`/session/${encodeURIComponent(sessionId)}/prompt_async`, {
      method: 'POST',
      body: JSON.stringify({
        agent: AGENT_NAME,
        model: { providerID, modelID },
        parts: [{ type: 'text', text }],
      }),
    })
  }

  abort(sessionId: string) {
    return this.request<boolean>(`/session/${encodeURIComponent(sessionId)}/abort`, {
      method: 'POST',
    })
  }

  listPermissions() {
    return this.request<AgentPermissionRequest[]>('/permission')
  }

  // 服务端只认 once / reject；「本会话始终允许」由前端记规则后继续用 once 应答
  respondPermission(sessionId: string, requestId: string, response: 'once' | 'reject') {
    return this.request<boolean>(
      `/session/${encodeURIComponent(sessionId)}/permissions/${encodeURIComponent(requestId)}`,
      { method: 'POST', body: JSON.stringify({ response }) },
    )
  }

  listQuestions() {
    return this.request<AgentQuestionRequest[]>('/question')
  }

  replyQuestion(requestId: string, answers: string[][]) {
    return this.request<boolean>(`/question/${encodeURIComponent(requestId)}/reply`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    })
  }

  rejectQuestion(requestId: string) {
    return this.request<boolean>(`/question/${encodeURIComponent(requestId)}/reject`, {
      method: 'POST',
    })
  }

  // SSE 用 fetch + ReadableStream（EventSource 无法带 Authorization header）
  async openEventStream(
    signal: AbortSignal,
    onEvent: (event: AgentStreamEvent) => void,
    onOpen?: () => void,
  ) {
    const response = await fetch(`${this.apiBase}/event`, {
      headers: { Accept: 'text/event-stream', ...this.headers() },
      signal,
    })
    if (!response.ok || !response.body) {
      throw new Error(`事件流连接失败：${response.status}`)
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const emitFrame = (frame: string) => {
      const data = frame
        .split(/\r?\n/)
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
        .join('\n')
      if (!data) return
      try {
        onEvent(JSON.parse(data) as AgentStreamEvent)
      } catch {
        // 非 JSON 帧忽略
      }
    }
    onOpen?.()
    for (;;) {
      const { done, value } = await reader.read()
      if (done) {
        buffer += decoder.decode()
        if (buffer.trim()) emitFrame(buffer)
        break
      }
      buffer += decoder.decode(value, { stream: true })
      const frames = buffer.split(/\r?\n\r?\n/)
      buffer = frames.pop() ?? ''
      frames.forEach(emitFrame)
    }
  }
}

export const extractAgentError = (payload: unknown): string => {
  if (!payload) return ''
  if (typeof payload === 'string') return payload
  if (Array.isArray(payload)) return payload.map(extractAgentError).filter(Boolean).join('; ')
  if (typeof payload === 'object') {
    const record = payload as Record<string, unknown>
    return (
      extractAgentError(record.error) ||
      extractAgentError(record.data) ||
      extractAgentError(record.cause) ||
      extractAgentError(record.message)
    )
  }
  return ''
}

/** 用户主动中止：服务端用 Aborted 错误收尾，界面要按「已停止」而不是「失败」处理。 */
export const isAgentAbortError = (payload: unknown): boolean => {
  if (!payload || typeof payload !== 'object') return false
  const value = payload as Record<string, unknown>
  if (value.name === 'MessageAbortedError' || value.name === 'AbortError') return true
  return isAgentAbortError(value.error) || isAgentAbortError(value.data)
}

// agent base 默认同源 /agent-api（可被 env / 运行时注入覆盖）
export const defaultAgentApiBase = (): string => {
  const runtime = (window as any).__WITTY_CONFIG__ ?? {}
  const fromEnv = (import.meta as any).env?.VITE_OPENCODE_API_BASE_URL
  return String(fromEnv ?? runtime.agentApiBase ?? '/agent-api').replace(/\/+$/, '')
}
