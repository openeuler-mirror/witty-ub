import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const apiSource = readFileSync(new URL('../src/api/agent.ts', import.meta.url), 'utf8')
const apiController = apiSource.slice(0, apiSource.indexOf('// agent base 默认同源'))
const apiJs = ts.transpileModule(apiController.replaceAll('export ', ''), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
}).outputText
const apiExports = new Function(
  `${apiJs}\nreturn { AgentApi, buildBasicAuthHeader, extractAgentError, isSecureRemoteAgentAddress, normalizeAgentServerAddress }`,
)()

const chatSource = readFileSync(
  new URL('../src/composables/useAgentChat.ts', import.meta.url),
  'utf8',
)
const chatController = chatSource.slice(chatSource.indexOf('const CONNECTION_KEY'))
const chatJs = ts.transpileModule(chatController.replaceAll('export ', ''), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
}).outputText
const createAgentChatState = new Function(
  'ref',
  'shallowRef',
  'computed',
  'reactive',
  'nextTick',
  'useToast',
  'useAssets',
  'AgentApi',
  'buildBasicAuthHeader',
  'defaultAgentApiBase',
  'extractAgentError',
  'isSecureRemoteAgentAddress',
  'normalizeAgentServerAddress',
  `${chatJs}\nreturn createAgentChatState`,
)(
  (value) => ({ value }),
  (value) => ({ value }),
  (getter) => ({
    get value() {
      return getter()
    },
  }),
  (value) => value,
  async (callback) => callback?.(),
  () => ({ toast() {} }),
  // 全量资产列表：sessionAssetName 按它解析资产名
  () => ({
    assets: {
      value: [
        { id: 'kb-a', name: '资产 A' },
        { id: 'kb-b', name: '资产 B' },
        { id: 'kb-new', name: '测试资产' },
      ],
    },
  }),
  apiExports.AgentApi,
  apiExports.buildBasicAuthHeader,
  () => '/agent-api',
  apiExports.extractAgentError,
  apiExports.isSecureRemoteAgentAddress,
  apiExports.normalizeAgentServerAddress,
)

const flush = () => new Promise((resolve) => setImmediate(resolve))

function setup() {
  const makeServer = () => ({
    sessions: [
      { id: 'a', title: '会话 A' },
      { id: 'b', title: '会话 B' },
      { id: 'child', parentID: 'a', title: '子任务' },
    ],
    histories: {
      a: [
        {
          info: { id: 'u-a', role: 'user' },
          parts: [{ type: 'text', text: '当前会话对应的知识库 ID 是 kb-a。\n\n问题 A' }],
        },
      ],
      b: [{ info: { id: 'u-b', role: 'user' }, parts: [{ type: 'text', text: '问题 B' }] }],
      child: [],
    },
    statuses: {},
  })
  const servers = { local: makeServer(), remote: makeServer() }
  const storage = new Map()
  const requests = []
  const failures = new Set()
  const deferred = new Map()
  const streams = { local: [], remote: [] }
  const localStorage = {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: (key) => storage.delete(key),
  }
  globalThis.localStorage = localStorage
  globalThis.sessionStorage = localStorage
  globalThis.window = {
    localStorage,
    sessionStorage: localStorage,
    setTimeout,
    clearTimeout,
    location: { href: 'http://local.test/' },
  }
  globalThis.btoa ??= (value) => Buffer.from(value, 'binary').toString('base64')

  globalThis.fetch = async (url, init = {}) => {
    const parsed = new URL(url, 'http://local.test/')
    const serverName = parsed.origin === 'https://remote.test' ? 'remote' : 'local'
    const server = servers[serverName]
    const path = parsed.pathname.replace(/^\/agent-api/, '')
    const method = init.method ?? 'GET'
    const body = init.body ? JSON.parse(init.body) : undefined
    requests.push({ server: serverName, path, method, body })
    const json = (value, status = 200) =>
      new Response(JSON.stringify(value), {
        status,
        headers: { 'Content-Type': 'application/json' },
      })
    if (failures.has(`${serverName} ${method} ${path}`))
      return json({ message: '测试服务错误' }, 500)
    if (path === '/event') {
      return new Response(
        new ReadableStream({
          start(controller) {
            streams[serverName].push(controller)
            init.signal?.addEventListener(
              'abort',
              () => {
                try {
                  controller.close()
                } catch {
                  /* already closed */
                }
              },
              { once: true },
            )
          },
        }),
        { headers: { 'Content-Type': 'text/event-stream' } },
      )
    }
    const deferredKey = `${serverName} ${path}`
    if (deferred.has(deferredKey)) return json(await deferred.get(deferredKey))
    if (path === '/global/health') return json({ healthy: true })
    if (path === '/provider') {
      return json({
        connected: ['test'],
        default: { test: 'model' },
        all: [{ id: 'test', models: { model: { id: 'model', providerID: 'test', name: 'Test' } } }],
      })
    }
    if (path === '/session/status') return json(server.statuses)
    if (path === '/session' && method === 'GET') return json(server.sessions)
    if (path === '/session' && method === 'POST') {
      const session = { id: `created-${server.sessions.length}`, ...body }
      server.sessions.push(session)
      server.histories[session.id] = []
      return json(session)
    }
    const [, id, action] = path.match(/^\/session\/([^/]+)(?:\/(.*))?$/) ?? []
    if (action === 'message') return json(server.histories[id] ?? [])
    if (action === 'abort') {
      delete server.statuses[id]
      return json(true)
    }
    if (action === 'prompt_async') return new Response(null, { status: 204 })
    const session = server.sessions.find((item) => item.id === id)
    if (method === 'PATCH') {
      Object.assign(session, body)
      return json(session)
    }
    if (method === 'DELETE') {
      server.sessions.splice(
        server.sessions.findIndex((item) => item.id === id),
        1,
      )
      return json(true)
    }
    return json(session)
  }

  const state = createAgentChatState()
  const emit = async (serverName, type, properties) => {
    const controller = streams[serverName].at(-1)
    assert.ok(controller, `missing ${serverName} event stream`)
    controller.enqueue(
      new TextEncoder().encode(`data: ${JSON.stringify({ type, properties })}\n\n`),
    )
    await flush()
  }
  const cleanup = async () => {
    state.closeEventStream()
    await flush()
  }
  return { state, servers, storage, requests, failures, deferred, emit, cleanup }
}

test('event stream flushes a final frame without a trailing blank line', async () => {
  const originalFetch = globalThis.fetch
  try {
    globalThis.fetch = async () => new Response('data: {"type":"session.idle"}')
    const events = []
    const api = new apiExports.AgentApi('/agent-api')
    await api.openEventStream(new AbortController().signal, (event) => events.push(event))
    assert.deepEqual(events, [{ type: 'session.idle' }])
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('new conversation clears the window and creates the session lazily on first send', async () => {
  const { state, servers, storage, cleanup } = setup()
  try {
    await state.loginLocalAgent()
    assert.equal(state.connectionState.value, 'connected', state.connectionError.value)
    state.setAsset({ id: 'kb-new', name: '测试资产' })
    await flush()
    await state.openConversation('a')
    await state.newConversation()
    // 新建对话只清空窗口，不预建服务端会话
    assert.equal(state.sessionId.value, '')
    assert.deepEqual(state.messages.value, [])
    assert.equal(state.activeSessionTitle.value, '开始新对话')
    assert.equal(storage.get('witty-ub.active-session:/agent-api'), undefined)
    // 首次发送才惰性创建会话
    const sessionsBefore = servers.local.sessions.length
    state.input.value = '首次提问'
    await state.sendMessage()
    await flush()
    const id = state.sessionId.value
    assert.ok(id.startsWith('created-'))
    assert.equal(servers.local.sessions.length, sessionsBefore + 1)
    assert.equal(state.sessionAssetName(id), '测试资产')
    // 不再用首条问题改写标题
    assert.equal(state.activeSessionTitle.value, '开始新对话')
    const session = state.sessions.value.find((item) => item.id === id)
    state.showSessionDialog('rename', session)
    state.sessionTitleInput.value = '诊断记录'
    await state.submitSessionDialog()
    assert.equal(servers.local.sessions.find((item) => item.id === id).title, '诊断记录')
    state.showSessionDialog('delete', session)
    await state.submitSessionDialog()
    assert.equal(state.sessionId.value, '')
    assert.ok(!state.sessions.value.some((item) => item.id === id))
  } finally {
    await cleanup()
  }
})

test('switching preserves background generation, drafts, and asset context', async () => {
  const { state, servers, requests, cleanup } = setup()
  try {
    servers.local.statuses.a = { type: 'busy' }
    await state.loginLocalAgent()
    await state.openConversation('a')
    assert.equal(state.isSending.value, true)
    assert.equal(state.sessionAssetName('a'), '资产 A')
    state.input.value = 'A 的草稿'
    await state.openConversation('b')
    assert.equal(state.isSending.value, false)
    assert.equal(state.input.value, '')
    await state.openConversation('a')
    assert.equal(state.input.value, 'A 的草稿')
    assert.ok(!requests.some((request) => request.path.endsWith('/abort')))
  } finally {
    await cleanup()
  }
})

// 回归：切到另一个资产库后打开 Agent 面板，历史问答记录里的资产库名称
// 必须仍按全量资产列表解析，不能只认当前资产库（否则会显示成 ID）。
test('非当前资产库的会话也显示资产名，并可按资产名检索', async () => {
  const { state, storage, cleanup } = setup()
  try {
    // 用户此前在资产 A 提问过，映射已落在 localStorage；当前打开的是资产 B
    storage.set('witty-ub.agent-session-assets:/agent-api', JSON.stringify({ a: 'kb-a' }))
    await state.loginLocalAgent()
    state.setAsset({ id: 'kb-b', name: '资产 B' })
    await flush()

    assert.equal(state.sessionAssetName('a'), '资产 A')
    assert.notEqual(state.sessionAssetName('a'), 'kb-a')
    // 没登记资产、以及资产已被删除的会话仍交给界面显示占位文案
    assert.equal(state.sessionAssetName('b'), '')
    assert.equal(state.sessionAssetName('child'), '')

    state.sessionSearch.value = '资产 A'
    assert.deepEqual(
      state.filteredSessions.value.map((item) => item.id),
      ['a'],
    )
  } finally {
    await cleanup()
  }
})

test('late history cannot overwrite the selected conversation', async () => {
  const { state, deferred, cleanup } = setup()
  try {
    await state.loginLocalAgent()
    let release
    deferred.set(
      'local /session/a/message',
      new Promise((resolve) => {
        release = resolve
      }),
    )
    const old = state.openConversation('a')
    await flush()
    await state.openConversation('b')
    release([{ info: { role: 'user' }, parts: [{ type: 'text', text: '迟到的 A' }] }])
    await old
    assert.equal(state.sessionId.value, 'b')
    assert.equal(state.messages.value[0].content, '问题 B')
    assert.equal(state.isHistoryLoading.value, false)
  } finally {
    await cleanup()
  }
})

test('reconnect starts an empty window and history/model errors return on explicit open', async () => {
  const { state, servers, storage, cleanup } = setup()
  try {
    servers.local.histories.b.push({
      info: { id: 'error-b', role: 'assistant', error: { data: { message: '连接失败' } } },
      parts: [],
    })
    await state.loginLocalAgent()
    await state.openConversation('b')
    assert.equal(state.messages.value.at(-1).content, '连接失败')
    await state.loginLocalAgent()
    // 连接后进入「开始新对话」空窗口，不自动恢复上次会话
    assert.equal(state.sessionId.value, '')
    assert.equal(state.messages.value.length, 0)
    assert.equal(storage.get('witty-ub.active-session:/agent-api'), undefined)
    // 显式打开仍恢复历史与历史错误态
    await state.openConversation('b')
    assert.equal(state.sessionId.value, 'b')
    assert.equal(state.messages.value.at(-1).status, 'error')
    assert.equal(state.messages.value.at(-1).content, '连接失败')
  } finally {
    await cleanup()
  }
})

test('initial asset sync does not restore the stored conversation on connect', async () => {
  const { state, storage, cleanup } = setup()
  try {
    storage.set('witty-ub.active-session:/agent-api', 'a')
    state.setAsset({ id: 'kb-a', name: '测试资产' })
    await state.loginLocalAgent()
    // 连接后不自动恢复历史会话，活动会话标识被清除
    assert.equal(state.sessionId.value, '')
    assert.equal(state.messages.value.length, 0)
    assert.equal(storage.get('witty-ub.active-session:/agent-api'), undefined)
  } finally {
    await cleanup()
  }
})

test('session storage is scoped by server and child sessions are hidden', async () => {
  const { state, cleanup } = setup()
  try {
    await state.loginLocalAgent()
    await state.openConversation('a')
    assert.equal(state.filteredSessions.value.length, 2)
    state.remoteAddress.value = 'https://remote.test'
    state.remoteUsername.value = 'user'
    state.remotePassword.value = 'password'
    await state.loginRemoteAgent()
    assert.equal(state.sessionId.value, '')
    assert.equal(state.sessionAssetName('a'), '')
    assert.equal(state.filteredSessions.value.length, 2)
  } finally {
    await cleanup()
  }
})

test('history failure blocks sending and explicit reload recovers', async () => {
  const { state, failures, requests, cleanup } = setup()
  try {
    await state.loginLocalAgent()
    failures.add('local GET /session/a/message')
    await state.openConversation('a')
    assert.equal(state.isHistoryFailed.value, true)
    state.input.value = '不能发到未加载的会话'
    await state.sendMessage()
    assert.ok(!requests.some((request) => request.path.endsWith('/prompt_async')))
    failures.clear()
    await state.openConversation('a')
    assert.equal(state.isHistoryFailed.value, false)
  } finally {
    await cleanup()
  }
})

test('failed deletion retains a session; successful deletion aborts a busy session first', async () => {
  const { state, servers, failures, requests, cleanup } = setup()
  try {
    await state.loginLocalAgent()
    failures.add('local DELETE /session/a')
    const session = state.sessions.value.find((item) => item.id === 'a')
    state.showSessionDialog('delete', session)
    await state.submitSessionDialog()
    assert.ok(state.sessions.value.some((item) => item.id === 'a'))
    assert.match(state.sessionDialogError.value, /测试服务错误/)
    failures.clear()
    servers.local.statuses.a = { type: 'busy' }
    const offset = requests.length
    await state.submitSessionDialog()
    const actions = requests.slice(offset)
    assert.ok(
      actions.findIndex((item) => item.path.endsWith('/abort')) <
        actions.findIndex((item) => item.method === 'DELETE'),
    )
    assert.ok(!state.sessions.value.some((item) => item.id === 'a'))
  } finally {
    await cleanup()
  }
})

test('stream deltas queued during history loading do not duplicate fetched text', async () => {
  const { state, servers, deferred, emit, cleanup } = setup()
  try {
    await state.loginLocalAgent()
    servers.local.statuses.a = { type: 'busy' }
    let release
    deferred.set(
      'local /session/a/message',
      new Promise((resolve) => {
        release = resolve
      }),
    )
    const loading = state.openConversation('a')
    await flush()
    await emit('local', 'message.updated', { info: { id: 'm', role: 'assistant', sessionID: 'a' } })
    await emit('local', 'message.part.updated', {
      part: { id: 'p', messageID: 'm', sessionID: 'a', type: 'text', text: 'Hello' },
    })
    await emit('local', 'message.part.delta', {
      sessionID: 'a',
      messageID: 'm',
      partID: 'p',
      field: 'text',
      delta: ' world',
    })
    release([
      {
        info: { id: 'm', role: 'assistant' },
        parts: [{ id: 'p', type: 'text', text: 'Hello world' }],
      },
    ])
    await loading
    assert.equal(state.messages.value[0].content, 'Hello world')
    await emit('local', 'message.part.delta', {
      sessionID: 'a',
      messageID: 'm',
      partID: 'p',
      field: 'text',
      delta: '!',
    })
    assert.equal(state.messages.value[0].content, 'Hello world!')
  } finally {
    await cleanup()
  }
})
