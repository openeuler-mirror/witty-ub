// OpenCode 诊断助手客户端：本机走同源 /agent-api 反代（免认证），
// 远程直连 OpenCode 服务地址并使用 Basic Authorization。
// 凭据只出现在 Authorization header 与 sessionStorage，不进 URL / 日志 / 持久化。

export type OpenCodeSession = {
  id: string
  title?: string
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
  info: { id?: string; role?: string; sessionID?: string }
  parts?: OpenCodeMessagePart[]
}

export type AgentStreamEvent = {
  type: string
  properties?: {
    sessionID?: string
    info?: { id?: string; role?: string; sessionID?: string }
    part?: { id?: string; type?: string; text?: string; sessionID?: string; messageID?: string }
    status?: { type?: string }
    error?: unknown
  }
}

export const AGENT_NAME = 'witty-ub-diagnostician'

export const normalizeAgentServerAddress = (raw: string) => {
  const value = raw.trim().replace(/\/+$/, '')
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value
  if (value.startsWith('/')) return value
  return `http://${value}`
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

  createSession() {
    return this.request<OpenCodeSession>('/session', { method: 'POST', body: '{}' })
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

  // SSE 用 fetch + ReadableStream（EventSource 无法带 Authorization header）
  async openEventStream(signal: AbortSignal, onEvent: (event: AgentStreamEvent) => void) {
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
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const frames = buffer.split(/\r?\n\r?\n/)
      buffer = frames.pop() ?? ''
      for (const frame of frames) {
        const data = frame
          .split(/\r?\n/)
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trimStart())
          .join('\n')
        if (!data) continue
        try {
          onEvent(JSON.parse(data) as AgentStreamEvent)
        } catch {
          // 非 JSON 帧忽略
        }
      }
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

// agent base 默认同源 /agent-api（可被 env / 运行时注入覆盖）
export const defaultAgentApiBase = (): string => {
  const runtime = (window as any).__WITTY_CONFIG__ ?? {}
  const fromEnv = (import.meta as any).env?.VITE_OPENCODE_API_BASE_URL
  return String(fromEnv ?? runtime.agentApiBase ?? '/agent-api').replace(/\/+$/, '')
}
