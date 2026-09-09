import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'

// Run the production conversation controller against an isolated HTTP/storage
// boundary. Tests never send model requests or mutate user conversations.
const source = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const controller = source.slice(
  source.indexOf('type OpenCodeHealthResult'),
  source.indexOf('const assetInitialFetchSize'),
)
const js = ts.transpileModule(controller.replaceAll('import.meta.env', 'environment'), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
}).outputText

function setup() {
  const sessions = [
    { id: 'a', title: '会话 A' },
    { id: 'b', title: '会话 B' },
  ]
  const histories = {
    a: [
      {
        info: { id: 'u-a', role: 'user' },
        parts: [{ type: 'text', text: '当前会话对应的知识库 ID 是 kb-a。\n\n问题 A' }],
      },
    ],
    b: [{ info: { id: 'u-b', role: 'user' }, parts: [{ type: 'text', text: '问题 B' }] }],
  }
  const statuses = {}
  const storage = new Map()
  const requests = []
  const deferred = new Map()
  const failures = new Set()
  const ref = (value) => ({ value })
  const window = {
    location: { href: 'http://localhost/' },
    localStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
    },
    sessionStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
    },
    setTimeout,
    clearTimeout,
  }
  const fetch = async (url, init = {}) => {
    const path = new URL(url, window.location.href).pathname.replace('/agent-api', '')
    const method = init.method || 'GET'
    const body = init.body && JSON.parse(init.body)
    requests.push({ path, method, body })
    const json = (value) => new Response(JSON.stringify(value), { status: 200 })
    if (failures.has(`${method} ${path}`))
      return new Response(JSON.stringify({ message: '测试服务错误' }), { status: 500 })
    if (path === '/event')
      return new Response(
        new ReadableStream({
          start(stream) {
            init.signal.addEventListener('abort', () => stream.close(), { once: true })
          },
        }),
      )
    if (deferred.has(path)) return json(await deferred.get(path))
    if (path === '/global/health') return json({ healthy: true })
    if (path === '/provider')
      return json({
        connected: ['test'],
        default: { test: 'model' },
        all: [{ id: 'test', models: { model: { id: 'model', name: 'Test' } } }],
      })
    if (path === '/session/status') return json(statuses)
    if (path === '/session' && method === 'GET') return json(sessions)
    if (path === '/session' && method === 'POST') {
      const session = { id: `created-${sessions.length}`, ...body }
      sessions.push(session)
      histories[session.id] = []
      return json(session)
    }
    const [, id, action] = path.match(/^\/session\/([^/]+)(?:\/(.*))?$/) || []
    if (action === 'message') return json(histories[id] || [])
    if (action === 'abort') {
      delete statuses[id]
      return json(true)
    }
    if (action === 'prompt_async') return new Response(null, { status: 204 })
    if (method === 'PATCH') {
      Object.assign(
        sessions.find((item) => item.id === id),
        body,
      )
      return json(sessions.find((item) => item.id === id))
    }
    if (method === 'DELETE') {
      sessions.splice(
        sessions.findIndex((item) => item.id === id),
        1,
      )
      return json(true)
    }
    return json(sessions.find((item) => item.id === id))
  }
  const get = new Function(
    'ref',
    'computed',
    'nextTick',
    'window',
    'fetch',
    'environment',
    'selectedAssetId',
    'selectedAsset',
    'assets',
    `${js}\nreturn {
    connectAgent, closeAgentEventStream, loadAgentSessions, newAgentConversation, openAgentSession,
    showAgentSessionDialog, submitAgentSessionDialog, toAgentChatMessages, handleOpenCodeEvent,
    agentSessionId, agentSessions, agentChatMessages, agentSessionAssetIndex, agentSessionTitleInput,
    agentChatInput, isAgentSending, isAgentHistoryLoading, isAgentHistoryFailed, agentSessionDialogError,
    filteredAgentSessions, sendAgentMessage,
  }`,
  )
  const api = get(
    ref,
    (fn) => ({
      get value() {
        return fn()
      },
    }),
    async () => {},
    window,
    fetch,
    {},
    ref('kb-new'),
    ref({ name: '测试资产' }),
    ref([]),
  )
  return { api, sessions, histories, statuses, storage, requests, deferred, failures }
}

test('new sessions are created lazily; rename and delete update server and local state', async () => {
  const { api, sessions, requests } = setup()
  try {
    await api.connectAgent('')
    const sessionCount = sessions.length
    await api.newAgentConversation()
    assert.equal(api.agentSessionId.value, '')
    assert.equal(sessions.length, sessionCount)
    api.agentChatInput.value = '检查当前资产库'
    await api.sendAgentMessage()
    const id = api.agentSessionId.value
    assert.ok(id.startsWith('created-'))
    assert.equal(sessions.length, sessionCount + 1)
    assert.equal(api.agentSessionAssetIndex.value[id], 'kb-new')
    assert.deepEqual(
      requests.find((item) => item.method === 'POST' && item.path === '/session')?.body,
      {},
    )
    assert.ok(requests.some((item) => item.method === 'GET' && item.path === `/session/${id}`))
    assert.ok(!requests.some((item) => item.method === 'PATCH' && item.path === `/session/${id}`))
    sessions.find((item) => item.id === id).title = '自动生成的诊断标题'
    api.handleOpenCodeEvent(
      new MessageEvent('message', {
        data: JSON.stringify({ type: 'session.idle', properties: { sessionID: id } }),
      }),
    )
    await new Promise((resolve) => setImmediate(resolve))
    const session = api.agentSessions.value.find((item) => item.id === id)
    assert.equal(session.title, '自动生成的诊断标题')
    api.showAgentSessionDialog('rename', session)
    api.agentSessionTitleInput.value = '诊断记录'
    await api.submitAgentSessionDialog()
    assert.equal(sessions.find((item) => item.id === id).title, '诊断记录')
    api.showAgentSessionDialog('delete', session)
    await api.submitAgentSessionDialog()
    assert.equal(api.agentSessionId.value, '')
    assert.ok(!api.agentSessions.value.some((item) => item.id === id))
  } finally {
    api.closeAgentEventStream()
  }
})

test('switching preserves background generation, drafts, and asset context', async () => {
  const { api, statuses, requests } = setup()
  try {
    statuses.a = { type: 'busy' }
    await api.connectAgent('')
    await api.openAgentSession({ id: 'a' })
    assert.equal(api.isAgentSending.value, true)
    assert.equal(api.agentSessionAssetIndex.value.a, 'kb-a')
    api.agentChatInput.value = 'A 的草稿'
    await api.openAgentSession({ id: 'b' })
    assert.equal(api.isAgentSending.value, false)
    assert.equal(api.agentChatInput.value, '')
    await api.openAgentSession({ id: 'a' })
    assert.equal(api.agentChatInput.value, 'A 的草稿')
    assert.ok(!requests.some((item) => item.path.endsWith('/abort')))
  } finally {
    api.closeAgentEventStream()
  }
})

test('late history cannot overwrite the currently selected conversation', async () => {
  const { api, deferred } = setup()
  try {
    await api.connectAgent('')
    let release
    deferred.set(
      '/session/a/message',
      new Promise((resolve) => {
        release = resolve
      }),
    )
    const old = api.openAgentSession({ id: 'a' })
    await new Promise((resolve) => setImmediate(resolve))
    await api.openAgentSession({ id: 'b' })
    release([{ info: { role: 'user' }, parts: [{ type: 'text', text: '迟到的 A' }] }])
    await old
    assert.equal(api.agentSessionId.value, 'b')
    assert.equal(api.agentChatMessages.value[0].content, '问题 B')
    assert.equal(api.isAgentHistoryLoading.value, false)
  } finally {
    api.closeAgentEventStream()
  }
})

test('reconnecting starts with an empty conversation instead of restoring the active session', async () => {
  const { api, histories } = setup()
  try {
    histories.b.push({
      info: { id: 'error-b', role: 'assistant', error: { data: { message: '连接失败' } } },
      parts: [],
    })
    await api.connectAgent('')
    await api.openAgentSession({ id: 'b' })
    await api.connectAgent('')
    assert.equal(api.agentSessionId.value, '')
    assert.equal(api.agentChatMessages.value.length, 0)
  } finally {
    api.closeAgentEventStream()
  }
})

test('session storage is scoped by server; child agent sessions are hidden', async () => {
  const { api, sessions } = setup()
  try {
    sessions.push({ id: 'child', parentID: 'a', title: '子任务' })
    await api.connectAgent('')
    await api.openAgentSession({ id: 'a' })
    assert.equal(api.filteredAgentSessions.value.length, 2)
    await api.connectAgent('http://other-server')
    assert.equal(api.agentSessionId.value, '')
    assert.equal(api.agentSessionAssetIndex.value.a, undefined)
  } finally {
    api.closeAgentEventStream()
  }
})

test('history failure blocks sending; explicit reload recovers', async () => {
  const { api, failures, requests } = setup()
  try {
    await api.connectAgent('')
    failures.add('GET /session/a/message')
    await api.openAgentSession({ id: 'a' })
    assert.equal(api.isAgentHistoryFailed.value, true)
    api.agentChatInput.value = '不能发到未加载的会话'
    await api.sendAgentMessage()
    assert.ok(!requests.some((item) => item.path.endsWith('/prompt_async')))
    failures.clear()
    await api.openAgentSession({ id: 'a' })
    assert.equal(api.isAgentHistoryFailed.value, false)
  } finally {
    api.closeAgentEventStream()
  }
})

test('failed deletion retains the session; successful deletion aborts a busy session first', async () => {
  const { api, failures, statuses, requests } = setup()
  try {
    await api.connectAgent('')
    failures.add('DELETE /session/a')
    api.showAgentSessionDialog('delete', { id: 'a' })
    await api.submitAgentSessionDialog()
    assert.ok(api.agentSessions.value.some((item) => item.id === 'a'))
    assert.match(api.agentSessionDialogError.value, /测试服务错误/)
    failures.clear()
    statuses.a = { type: 'busy' }
    const offset = requests.length
    await api.submitAgentSessionDialog()
    const actions = requests.slice(offset)
    assert.ok(
      actions.findIndex((item) => item.path.endsWith('/abort')) <
        actions.findIndex((item) => item.method === 'DELETE'),
    )
    assert.ok(!api.agentSessions.value.some((item) => item.id === 'a'))
  } finally {
    api.closeAgentEventStream()
  }
})

test('streamed deltas captured during history loading do not duplicate fetched text', async () => {
  const { api, deferred, statuses } = setup()
  try {
    await api.connectAgent('')
    statuses.a = { type: 'busy' }
    let release
    deferred.set(
      '/session/a/message',
      new Promise((resolve) => {
        release = resolve
      }),
    )
    const loading = api.openAgentSession({ id: 'a' })
    await new Promise((resolve) => setImmediate(resolve))
    const emit = (type, properties) =>
      api.handleOpenCodeEvent(
        new MessageEvent('message', { data: JSON.stringify({ type, properties }) }),
      )
    emit('message.updated', { info: { id: 'm', role: 'assistant', sessionID: 'a' } })
    emit('message.part.updated', {
      part: { id: 'p', messageID: 'm', sessionID: 'a', type: 'text', text: 'Hello' },
    })
    emit('message.part.delta', {
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
    assert.equal(api.agentChatMessages.value[0].content, 'Hello world')
    emit('message.part.delta', {
      sessionID: 'a',
      messageID: 'm',
      partID: 'p',
      field: 'text',
      delta: '!',
    })
    assert.equal(api.agentChatMessages.value[0].content, 'Hello world!')
  } finally {
    api.closeAgentEventStream()
  }
})
