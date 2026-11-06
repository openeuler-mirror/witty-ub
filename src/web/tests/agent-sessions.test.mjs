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
  const reactive = (value) => value
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
    'reactive',
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
    answerAgentPermission, submitAgentQuestion,
    abortAgentSession,
    buildAgentTurns, isVisibleAgentText, isVisibleAgentReasoning, hasAgentTurnContent,
    isAgentTurnExpanded, toggleAgentTurn,
    getAgentTurnSummary, getAgentToolView, getAgentToolStatusLabel,
    isAgentToolExpanded, toggleAgentTool,
    agentChatMessagesRef, isAgentChatPinnedToBottom, handleAgentChatScroll, scrollAgentChatToBottom,
    agentSessionId, agentSessions, agentChatMessages, agentSessionAssetIndex, agentSessionTitleInput,
    agentChatInput, isAgentSending, isAgentHistoryLoading, isAgentHistoryFailed, agentSessionDialogError,
    agentConnectionError,
    agentPendingPermissions, agentPendingQuestions, agentQuestionAnswers,
    filteredAgentSessions, sendAgentMessage,
  }`,
  )
  const api = get(
    ref,
    reactive,
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

test('只含工具调用的 assistant 消息归入回合过程，不产生空白气泡', async () => {
  const { api } = setup()
  try {
    const messages = api.toAgentChatMessages([
      {
        info: { id: 'user', role: 'user' },
        parts: [{ id: 'user-text', type: 'text', text: '检查日志' }],
      },
      {
        info: { id: 'tool-only', role: 'assistant' },
        parts: [
          {
            id: 'tool',
            type: 'tool',
            tool: 'bash',
            state: { status: 'completed', input: { command: 'date' } },
          },
        ],
      },
      {
        info: { id: 'answer', role: 'assistant' },
        parts: [{ id: 'answer-text', type: 'text', text: '检查完成' }],
      },
    ])

    const turns = api.buildAgentTurns(messages)
    assert.equal(turns.length, 1)
    assert.ok(turns[0].process.some((part) => part.type === 'tool'))
    assert.deepEqual(
      turns[0].answer.map((part) => part.text),
      ['检查完成'],
    )

    await api.connectAgent('')
    await api.openAgentSession({ id: 'a' })
    const emit = (id) =>
      api.handleOpenCodeEvent(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'message.updated',
            properties: { sessionID: 'a', info: { id, role: 'assistant', sessionID: 'a' } },
          }),
        }),
      )

    emit('stream-tool-only')
    emit('stream-answer')

    const ids = api.agentChatMessages.value.map((message) => message.messageId)
    assert.ok(ids.includes('stream-tool-only'))
    assert.equal(ids.at(-1), 'stream-answer')
    const streamedTurns = api.buildAgentTurns(api.agentChatMessages.value)
    assert.equal(streamedTurns.at(-1)?.hasAssistant, true)
  } finally {
    api.closeAgentEventStream()
  }
})

test('permission and structured question events can be answered without aborting the session', async () => {
  const { api, histories, requests } = setup()
  try {
    await api.connectAgent('')
    await api.openAgentSession({ id: 'a' })
    api.handleOpenCodeEvent(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'permission.asked',
          properties: {
            id: 'per_1',
            sessionID: 'a',
            permission: 'bash',
            patterns: ['git status'],
            metadata: {},
            always: ['git status'],
          },
        }),
      }),
    )
    assert.equal(api.agentPendingPermissions.value.length, 1)
    api.handleOpenCodeEvent(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'permission.asked',
          properties: {
            id: 'per_duplicate',
            sessionID: 'a',
            permission: 'bash',
            patterns: ['git status'],
            metadata: {},
            always: ['git status'],
          },
        }),
      }),
    )
    assert.equal(api.agentPendingPermissions.value.length, 1)
    await api.answerAgentPermission(api.agentPendingPermissions.value[0], 'once')
    assert.deepEqual(
      requests.find((item) => item.path === '/session/a/permissions/per_1')?.body,
      { response: 'once' },
    )
    assert.equal(api.agentPendingPermissions.value.length, 0)

    api.handleOpenCodeEvent(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'permission.asked',
          properties: {
            id: 'per_session_always',
            sessionID: 'a',
            permission: 'external_directory',
            patterns: ['/logs/current/app.log'],
            metadata: {},
            always: ['/logs/current/*'],
          },
        }),
      }),
    )
    await api.answerAgentPermission(api.agentPendingPermissions.value[0], 'always')
    assert.deepEqual(
      requests.find((item) => item.path === '/session/a/permissions/per_session_always')?.body,
      { response: 'once' },
    )
    api.handleOpenCodeEvent(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'permission.asked',
          properties: {
            id: 'per_auto_once',
            sessionID: 'a',
            permission: 'external_directory',
            patterns: ['/logs/current/worker.log'],
            metadata: {},
            always: ['/logs/current/*'],
          },
        }),
      }),
    )
    await new Promise((resolve) => setImmediate(resolve))
    assert.deepEqual(
      requests.find((item) => item.path === '/session/a/permissions/per_auto_once')?.body,
      { response: 'once' },
    )

    api.handleOpenCodeEvent(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'question.asked',
          properties: {
            id: 'que_1',
            sessionID: 'a',
            questions: [
              {
                header: '处理方式',
                question: '下一步怎么做？',
                options: [{ label: '继续', description: '继续执行' }],
              },
            ],
          },
        }),
      }),
    )
    assert.equal(api.agentPendingQuestions.value.length, 1)
    api.agentQuestionAnswers.value.que_1 = [['继续']]
    await api.submitAgentQuestion(api.agentPendingQuestions.value[0])
    assert.deepEqual(requests.find((item) => item.path === '/question/que_1/reply')?.body, {
      answers: [['继续']],
    })
    assert.equal(api.agentPendingQuestions.value.length, 0)
    assert.equal(api.agentChatMessages.value.at(-1).role, 'user')
    assert.equal(api.agentChatMessages.value.at(-1).content, '# 问题\n\n下一步怎么做？\n继续')
    assert.deepEqual(api.agentChatMessages.value.at(-1).questionReply, [
      { question: '下一步怎么做？', answer: '继续' },
    ])
    histories.a.push({
      info: { id: 'u-later', role: 'user' },
      parts: [{ type: 'text', text: '后续普通对话' }],
    })
    api.handleOpenCodeEvent(
      new MessageEvent('message', {
        data: JSON.stringify({ type: 'session.idle', properties: { sessionID: 'a' } }),
      }),
    )
    await new Promise((resolve) => setImmediate(resolve))
    const replyIndex = api.agentChatMessages.value.findIndex(
      (message) => message.id === 'agent-question-reply-que_1',
    )
    const laterIndex = api.agentChatMessages.value.findIndex((message) => message.id === 'u-later')
    assert.ok(replyIndex >= 0)
    assert.ok(replyIndex < laterIndex)
  } finally {
    api.closeAgentEventStream()
  }
})

test('an active abort is rendered as a user stop instead of a session error', async () => {
  const { api } = setup()
  try {
    const messages = api.toAgentChatMessages([
      {
        info: {
          id: 'assistant-aborted',
          role: 'assistant',
          error: { name: 'MessageAbortedError', data: { message: 'The operation was aborted' } },
        },
        parts: [],
      },
    ])
    assert.equal(messages[0].status, 'done')
    assert.equal(messages[0].content, '用户终止响应')

    await api.connectAgent('')
    await api.openAgentSession({ id: 'a' })
    api.isAgentSending.value = true
    await api.abortAgentSession()
    api.handleOpenCodeEvent(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'message.updated',
          properties: {
            sessionID: 'a',
            info: {
              id: 'assistant-aborted',
              sessionID: 'a',
              role: 'assistant',
              error: { name: 'MessageAbortedError', data: { message: 'aborted' } },
            },
          },
        }),
      }),
    )
    assert.equal(api.agentConnectionError.value, '')
    assert.equal(api.agentChatMessages.value.at(-1).content, '用户终止响应')
    assert.equal(api.agentChatMessages.value.at(-1).status, 'done')
  } finally {
    api.closeAgentEventStream()
  }
})

const agentPart = (id, type, text, extra = {}) => ({ id, type, text, ...extra })
const agentUser = (id, content) => ({
  id,
  role: 'user',
  reasoning: '',
  content,
  status: 'done',
})
const agentStep = (id, finish, parts, status = 'done') => ({
  id,
  messageId: id,
  role: 'assistant',
  reasoning: '',
  content: '',
  status,
  parts,
  finish,
})

test('多步工具调用归组为一个回合，只有末步文本作为最终回答', () => {
  const { api } = setup()
  const turns = api.buildAgentTurns([
    agentUser('u1', '生成定界报告'),
    agentStep('a1', 'tool-calls', [
      agentPart('p1', 'reasoning', '第一步思考'),
      agentPart('p2', 'text', '我先查契约'),
    ]),
    agentStep('a2', 'tool-calls', []),
    agentStep('a3', 'tool-calls', [agentPart('p3', 'reasoning', '继续取证')]),
    agentStep('a4', 'stop', [agentPart('p4', 'text', '最终结论')]),
  ])
  assert.equal(turns.length, 1)
  assert.equal(turns[0].hasAssistant, true)
  assert.deepEqual(
    turns[0].answer.map((item) => item.text),
    ['最终结论'],
  )
  assert.deepEqual(
    turns[0].process.map((item) => item.text),
    ['第一步思考', '我先查契约', '继续取证'],
  )
  assert.equal(api.hasAgentTurnContent(turns[0]), true)
})

test('空白步骤与空白、synthetic、ignored 文本不参与渲染', () => {
  const { api } = setup()
  const turns = api.buildAgentTurns([
    agentUser('u1', '检查'),
    agentStep('a1', 'tool-calls', [
      agentPart('p1', 'reasoning', '   '),
      agentPart('p2', 'text', '   '),
      agentPart('p3', 'text', '系统注入', { synthetic: true }),
      agentPart('p4', 'text', '忽略文本', { ignored: true }),
      agentPart('p5', 'text', '可见说明'),
    ]),
    agentStep('a2', 'tool-calls', []),
  ])
  assert.deepEqual(
    turns[0].process.map((item) => item.text),
    ['可见说明'],
  )
  assert.equal(turns[0].answer.length, 0)
  assert.equal(api.hasAgentTurnContent(turns[0]), true)

  const emptyTurns = api.buildAgentTurns([
    agentUser('u2', '空回合'),
    agentStep('a3', 'tool-calls', []),
  ])
  assert.equal(api.hasAgentTurnContent(emptyTurns[0]), false)
})

test('思考过程默认折叠，展开状态按回合记忆', () => {
  const { api } = setup()
  assert.equal(api.isAgentTurnExpanded('u1'), false)
  api.toggleAgentTurn('u1')
  assert.equal(api.isAgentTurnExpanded('u1'), true)
  assert.equal(api.isAgentTurnExpanded('u2'), false)
  api.toggleAgentTurn('u1')
  assert.equal(api.isAgentTurnExpanded('u1'), false)
})

test('中止、错误与缺少 finish 的历史消息仍在最终回答区可见', () => {
  const { api } = setup()
  const aborted = api.buildAgentTurns([
    agentUser('u1', '中止'),
    { ...agentStep('a1', 'tool-calls', [agentPart('p1', 'text', '用户终止响应')]), aborted: true },
  ])
  assert.deepEqual(
    aborted[0].answer.map((item) => item.text),
    ['用户终止响应'],
  )

  const failed = api.buildAgentTurns([
    agentUser('u2', '失败'),
    agentStep('a2', 'tool-calls', [agentPart('p2', 'text', '模型响应失败。')], 'error'),
  ])
  assert.deepEqual(
    failed[0].answer.map((item) => item.text),
    ['模型响应失败。'],
  )

  const legacy = api.buildAgentTurns([
    agentUser('u3', '历史'),
    agentStep('a3', undefined, [agentPart('p3', 'text', '历史最终回答')]),
  ])
  assert.deepEqual(
    legacy[0].answer.map((item) => item.text),
    ['历史最终回答'],
  )
})

test('问询答复把回合切开，答问前后的助手步分属两张卡片', () => {
  const { api } = setup()
  const turns = api.buildAgentTurns([
    agentUser('u1', '第一个问题'),
    agentStep('a1', 'stop', [agentPart('p1', 'text', '第一段回答')]),
    { ...agentUser('u2', '# 问题\n\n选哪个'), questionReply: [{ question: '选哪个', answer: 'A' }] },
    agentStep('a2', 'stop', [agentPart('p2', 'text', '第二段回答')]),
  ])
  assert.equal(turns.length, 2)
  assert.equal(turns[0].user.id, 'u1')
  assert.deepEqual(
    turns[0].answer.map((item) => item.text),
    ['第一段回答'],
  )
  assert.equal(turns[1].user.id, 'u2')
  assert.deepEqual(
    turns[1].answer.map((item) => item.text),
    ['第二段回答'],
  )
})

const agentTool = (id, name, status, input = {}, extra = {}) => ({
  id,
  type: 'tool',
  text: '',
  tool: { name, status, input, ...extra },
})

test('工具调用进入过程流，并按类型给出动作与结果', () => {
  const { api } = setup()
  const turns = api.buildAgentTurns([
    agentUser('u1', '查日志'),
    {
      ...agentStep('a1', 'tool-calls', [
        agentTool('t1', 'bash', 'completed', { command: 'tail -n 50 app.log' }),
        agentTool('t2', 'edit', 'error', { filePath: 'src/App.vue' }, { error: '写回失败' }),
      ]),
      time: { created: 1_000 },
    },
    {
      ...agentStep('a2', 'stop', [agentPart('p1', 'text', '结论')]),
      time: { created: 1_000, completed: 61_000 },
    },
  ])
  const turn = turns[0]
  assert.equal(turn.process.filter((item) => item.type === 'tool').length, 2)
  assert.deepEqual(api.getAgentToolView(turn.process[0]), {
    verb: '运行命令',
    detail: 'tail -n 50 app.log',
    fullDetail: 'tail -n 50 app.log',
  })
  assert.deepEqual(api.getAgentToolView(turn.process[1]), {
    verb: '编辑文件',
    detail: 'src/App.vue',
    fullDetail: 'src/App.vue',
  })
  assert.equal(api.getAgentToolStatusLabel(turn.process[0]), '完成')
  assert.equal(api.getAgentToolStatusLabel(turn.process[1]), '失败')
  assert.equal(
    api.getAgentTurnSummary(turn),
    '已完成，用时 1 分，执行了 1 条命令、修改了 1 个文件、失败 1 次。',
  )
})

test('思考中折叠行刷新为最新过程内容，结束后显示摘要', () => {
  const { api } = setup()
  const turn = { key: 'u1', hasAssistant: true, process: [], answer: [], status: 'thinking' }
  assert.equal(api.getAgentTurnSummary(turn), '正在分析问题并查询诊断数据')
  turn.process = [agentPart('p1', 'reasoning', '第一段\n正在定位时延异常')]
  assert.equal(api.getAgentTurnSummary(turn), '正在定位时延异常')
  turn.process = [...turn.process, agentTool('t1', 'bash', 'running', { command: 'date' })]
  assert.equal(api.getAgentTurnSummary(turn), '运行命令：date')
  turn.status = 'done'
  turn.durationMs = 65_000
  assert.equal(api.getAgentTurnSummary(turn), '已完成，用时 1 分 5 秒，执行了 1 条命令。')
})

test('工具行折叠时截断，展开后保留完整命令与多行', () => {
  const { api } = setup()
  const command = `set -e\nfor i in $(seq 1 60); do echo "line-$i"; done\n${'x'.repeat(200)}`
  const view = api.getAgentToolView(agentTool('t1', 'bash', 'completed', { command }))
  assert.equal(view.verb, '运行命令')
  assert.equal(view.fullDetail, command)
  assert.ok(view.detail.length < command.length)
  assert.ok(view.detail.endsWith('…'))

  assert.equal(api.isAgentToolExpanded('a1:t1'), false)
  api.toggleAgentTool('a1:t1')
  assert.equal(api.isAgentToolExpanded('a1:t1'), true)
  assert.equal(api.isAgentToolExpanded('a1:t2'), false)
  api.toggleAgentTool('a1:t1')
  assert.equal(api.isAgentToolExpanded('a1:t1'), false)
})

test('向上滚动后不再强制贴底，回到底部重新固定', async () => {
  const { api } = setup()
  const container = { scrollHeight: 1_000, scrollTop: 600, clientHeight: 400 }
  api.agentChatMessagesRef.value = container
  api.handleAgentChatScroll()
  assert.equal(api.isAgentChatPinnedToBottom.value, true)

  container.scrollTop = 100
  api.handleAgentChatScroll()
  assert.equal(api.isAgentChatPinnedToBottom.value, false)
  await api.scrollAgentChatToBottom()
  assert.equal(container.scrollTop, 100, '非固定状态下的新内容不能把视角拽回底部')
  assert.equal(api.isAgentChatPinnedToBottom.value, false)

  await api.scrollAgentChatToBottom(true)
  assert.equal(container.scrollTop, 1_000)
  assert.equal(api.isAgentChatPinnedToBottom.value, true)

  container.scrollTop = 580
  api.handleAgentChatScroll()
  assert.equal(api.isAgentChatPinnedToBottom.value, true, '滚回底部阈值内重新固定')
})

test('自动贴底不会被流式增高误判为用户上滑', async () => {
  const { api } = setup()
  const container = { scrollHeight: 500, scrollTop: 0, clientHeight: 300 }
  api.agentChatMessagesRef.value = container
  await api.scrollAgentChatToBottom(true)
  assert.equal(container.scrollTop, 500)
  // 内容在 scroll 事件到达前继续长高，事件仍上报自动滚动后的位置
  container.scrollHeight = 900
  api.handleAgentChatScroll()
  assert.equal(api.isAgentChatPinnedToBottom.value, true)

  container.scrollTop = 100
  api.handleAgentChatScroll()
  assert.equal(api.isAgentChatPinnedToBottom.value, false, '真实上滑仍然退出固定')
})
