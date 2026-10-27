import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { compileTemplate, parse } from '@vue/compiler-sfc'
import { renderToString } from 'vue/server-renderer'
import ts from 'typescript'
import * as vue from 'vue'
import * as workflow from '../src/utils/caseWorkflow.ts'

const descriptor = parse(readFileSync(new URL('../src/components/CaseOverview.vue', import.meta.url), 'utf8')).descriptor
const source = descriptor.scriptSetup.content
const js = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText
const template = compileTemplate({
  source: descriptor.template.content, filename: 'CaseOverview.vue', id: 'workspace',
  compilerOptions: { expressionPlugins: ['typescript'] },
})
const renderExports = {}
new Function('require', 'exports', ts.transpileModule(template.code, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText)(() => vue, renderExports)

const createWorkspace = (api, request = async () => []) => {
  const props = vue.reactive({ view: 'documents' })
  const watchers = []
  let renderedTree
  const document = { activeElement: null }
  const keyListeners = new Set()
  const window = {
    addEventListener: (event, listener) => { if (event === 'keydown') keyListeners.add(listener) },
    removeEventListener: (event, listener) => { if (event === 'keydown') keyListeners.delete(listener) },
  }
  class Element {
    isConnected = true
    offsetParent = {}
    focus() { document.activeElement = this }
  }
  const require = (name) => {
    if (name === 'vue') return { ...vue, onBeforeUnmount: () => {}, onMounted: () => {}, watch: (source, callback) => watchers.push({ source, callback }) }
    if (name.endsWith('/api/diagCase')) return api
    if (name.endsWith('/api/client')) return { request, apiBase: '' }
    if (name.endsWith('/utils/caseWorkflow')) return workflow
    throw new Error(`Unexpected import: ${name}`)
  }
  const state = new Function('require', 'exports', 'defineProps', 'defineEmits', 'localStorage', 'document', 'HTMLElement', 'window',
    `${js}\nreturn {
      load, reports, matches, legacyCases, documentFilter, filteredReports, pagedReports, scopedMatches, error,
      loading, importOpen, importMode, importing, importError, file, serverPath, optionsError, importOptions,
      sourceName, operator, declaredVerified, batch, toggleImport, loadImportOptions, submitImport, outcomeLabel,
      reportPages, reportPage, firstOptions, secondOptions, selection, count, selectFirst, selectSecond,
      pagedCases, filtered, pages, pagedLegacy, legacyPages, legacyPage,
      importDialogOpen, importPanel, closeImport, importKeydown,
    }`)(
    require, {}, () => props, () => () => {}, { getItem: () => '', setItem: () => {} },
    document, Element, window,
  )
  return {
    ...state, props, watchers, document, Element, keyListeners,
    renderedInputs: () => {
      const inputs = []
      const visit = (node) => {
        if (Array.isArray(node)) { node.forEach(visit); return }
        if (!vue.isVNode(node)) return
        if (node.type === 'input') inputs.push(node.props)
        if (Array.isArray(node.children)) visit(node.children)
      }
      visit(renderedTree)
      return inputs
    },
    render: async () => {
      const context = {}
      const html = await renderToString(vue.createSSRApp({
        setup: () => ({ ...workflow, ...state, view: props.view, apiBase: '', emit: () => {} }),
        render(...args) {
          renderedTree = renderExports.render.apply(this, args)
          return renderedTree
        },
      }), context)
      return html + (context.teleports?.body ?? '')
    },
  }
}

test('定界文档取完跨资产全部页，已验证文档仍可查阅，待验证只是文档子筛选', async () => {
  const documents = Array.from({ length: 253 }, (_, index) => ({
    report_id: `document-${index}`, kb_id: `asset-${index % 3}`,
    validation_status: index % 2 ? 'validated' : 'pending',
    indexable_fault_count: 2, validated_fault_count: index % 2 ? 2 : 0,
  }))
  const calls = []
  const state = createWorkspace({
    fetchReports: async (page, size) => {
      calls.push([page, size])
      return { total: documents.length, items: documents.slice((page - 1) * size, page * size) }
    },
    searchDiagCases: async () => { throw new Error('文档页不加载独立待验证案例') },
  }, async () => { throw new Error('任务案例不属于文档待验证') })
  await state.load()
  assert.equal(state.error.value, '')
  assert.deepEqual(calls, [[1, 100], [2, 100], [3, 100]])
  assert.deepEqual(state.filteredReports.value, documents)
  assert.equal(new Set(state.reports.value.map((item) => item.kb_id)).size, 3)
  state.documentFilter.value = 'pending'
  assert.equal(state.filteredReports.value.length, 127)
  assert.ok(state.filteredReports.value.every((item) => item.validation_status === 'pending'))
  state.documentFilter.value = 'all'
  assert.equal(state.filteredReports.value.length, 253)
})

test('已知案例使用正式库查询并同时加载任务案例，不要求验证字段', async () => {
  const queries = []
  const legacy = [{
    id: 'legacy', case_category: '原故障大类', root_cause_type: '原根因类型',
    log_file_id: 'log-1', task_ids: ['task-1'], source_kind: 'task', effective: true,
  }, { id: 'file', root_cause_type: '文件案例', source_kind: 'historical', effective: true }]
  const state = createWorkspace({
    searchDiagCases: async (query) => {
      queries.push(query)
      return { total: 1, matches: [{ case: { id: 'verified', status: 'confirmed', verification_json: { closed_loop: true } } }] }
    },
    fetchReports: async () => { throw new Error('已知案例不混入文档') },
  }, async (path) => { assert.equal(path, '/case_library/list'); return legacy })
  state.props.view = 'library'
  await state.load()
  assert.equal(state.error.value, '')
  assert.deepEqual(queries, [{ scope: 'library', include_status: ['confirmed'], page_num: 1, page_cnt: 200 }])
  assert.equal(state.scopedMatches.value.length, 1)
  assert.deepEqual(state.legacyCases.value, legacy)
  assert.equal(workflow.legacyCaseOrigin(legacy[0]), '任务日志自动生成')
  assert.equal(workflow.legacyCaseOrigin(legacy[1]), '历史文件案例')
  assert.equal(state.reports.value.length, 0)
})

test('列表隐藏分类列，分类仍可通过标签筛选文档与案例', async () => {
  const state = createWorkspace({})
  const labels = { first_level_label: '网络故障', second_level_label: '链路中断' }
  state.reports.value = [{ report_id: 'r1', title: '文档标题', classifications: [{ ...labels, status: 'pair' }] }]
  state.matches.value = [{ case: { id: 'c1', title: '案例标题', ...labels, status: 'confirmed', verification_json: { closed_loop: true } } }]
  state.legacyCases.value = [{ id: 'l1', root_cause_type: '任务案例', case_category: '旧分类' }]
  for (const view of ['documents', 'library']) {
    state.props.view = view
    state.selectFirst('网络故障')
    state.selectSecond('链路中断')
    const html = await state.render()
    const headers = [...html.matchAll(/<th>(.*?)<\/th>/g)].map((match) => match[1])
    assert.ok(headers.length)
    assert.ok(headers.every((header) => !header.includes('分类')))
    assert.match(html, /网络故障/)
    assert.match(html, /链路中断/)
    assert.doesNotMatch(html, /<td>网络故障|<td>旧分类/)
    assert.match(html, view === 'documents' ? /文档标题/ : /案例标题/)
  }
})

test('文档验证状态优先，已验证故障去重计数优先于兼容案例数', () => {
  const documents = [
    { validation_status: 'pending', indexable_fault_count: 2, validated_fault_count: 0 },
    { validation_status: 'partial', indexable_fault_count: 2, validated_fault_count: 1 },
    { validation_status: 'validated', indexable_fault_count: 2, validated_fault_count: 2 },
    { validation_status: 'unavailable' },
  ]
  assert.deepEqual(workflow.filterDocuments(documents, 'pending'), documents.slice(0, 2))
  assert.equal(workflow.documentProgress({ indexable_fault_count: 3, validated_fault_count: 1, verified_case_count: 4 }), '1/3')
  assert.equal(workflow.reportNeedsVerification({ indexable_fault_count: 3, validated_fault_count: 1, verified_case_count: 4 }), true)
  assert.equal(workflow.documentProgress({ fault_count: 2, verified_case_count: 2 }), '2/2')
  assert.equal(workflow.reportNeedsVerification({ report_available: false }), false)
  assert.equal(workflow.sourceReportLabel('valid'), '查看来源定界文档')
})

test('导入入口与表单只出现在文档页，切换服务器路径只显示手工文本输入并说明容器语义', async () => {
  const state = createWorkspace({ fetchImportOptions: async () => ({ path_import_enabled: true, allowed_roots: ['/readonly'] }) })
  const closed = await state.render()
  assert.match(closed, /class="primary-btn"[^>]*aria-haspopup="dialog"/)
  assert.doesNotMatch(closed, /role="dialog"/)
  state.toggleImport()
  await Promise.resolve()
  let html = await state.render()
  assert.match(html, /role="dialog" aria-modal="true"/)
  assert.match(html, /class="import-panel"/)
  assert.match(html, /class="ghost-btn"[^>]*>关闭</)
  assert.match(html, /type="file"/)
  assert.match(html, /accept=".json,.zip"/)
  state.importMode.value = 'path'
  html = await state.render()
  assert.doesNotMatch(html, /type="file"/)
  assert.match(html, /type="text"/)
  assert.match(html, /容器内挂载路径/)
  assert.match(html, /不是浏览器所在电脑的本地路径/)
  assert.match(html, /\/readonly/)
  state.props.view = 'library'
  html = await state.render()
  assert.doesNotMatch(html, /导入定界报告|服务器绝对路径|type="file"/)
  assert.equal(state.importDialogOpen.value, false)
  state.closeImport()
  state.toggleImport()
  assert.equal(state.importOpen.value, false)
})

test('实际编译渲染的上传与服务器路径输入互斥，未选文件、已选文件及切回上传均成立', async () => {
  const state = createWorkspace({ fetchImportOptions: async () => ({ path_import_enabled: true, allowed_roots: ['/readonly'] }) })
  state.toggleImport()
  await Promise.resolve()
  const assertInputs = async (mode, file, expected) => {
    state.importMode.value = mode
    state.file.value = file
    await state.render()
    assert.deepEqual(state.renderedInputs().filter((input) => ['file', 'text'].includes(input.type))
      .map((input) => input.type), expected)
  }
  await assertInputs('upload', null, ['file'])
  const file = new File(['{}'], 'report.json')
  await assertInputs('upload', file, ['file'])
  await assertInputs('path', file, ['text'])
  await assertInputs('upload', null, ['file'])
})

test('弹窗关闭保留输入与结果，导入期间关闭、Esc 与重复提交均被拦截，结束后刷新列表', async () => {
  let resolveImport
  let imports = 0
  let lists = 0
  const result = {
    batch_id: 'batch', status: 'partial', file_count: 2,
    summary: { imported: 1, duplicate: 0, failed: 1, cases: { confirmed: 1, draft: 0, skipped: 0, existing: 0 } },
    items: [{ original_name: 'broken.json', status: 'failed', error: '报告格式无效' }],
  }
  const state = createWorkspace({
    fetchImportOptions: async () => ({ path_import_enabled: true, allowed_roots: ['/readonly'] }),
    importCases: async () => { imports++; return new Promise((resolve) => { resolveImport = resolve }) },
    fetchReports: async () => { lists++; return { total: 0, items: [] } },
  })

  state.file.value = new File(['{}'], 'report.json')
  state.operator.value = '操作人'
  state.sourceName.value = '团队'
  state.serverPath.value = '/readonly/report.json'
  state.importError.value = '前次错误'
  state.toggleImport()
  state.closeImport()
  assert.equal(state.file.value.name, 'report.json')
  assert.equal(state.importError.value, '前次错误')
  state.toggleImport()
  assert.equal(state.operator.value, '操作人')
  const pending = state.submitImport()
  assert.equal(state.importing.value, true)
  state.closeImport()
  state.toggleImport()
  state.importKeydown({ key: 'Escape', preventDefault() {}, stopPropagation() {} })
  await state.submitImport()
  assert.equal(state.importOpen.value, true)
  assert.equal(imports, 1)
  assert.match(await state.render(), /aria-label="关闭" disabled/)
  resolveImport(result)
  await pending
  assert.equal(state.importing.value, false)
  assert.equal(lists, 1)
  assert.equal(state.importOpen.value, true)
  assert.match(await state.render(), /报告格式无效/)
  state.closeImport()
  state.toggleImport()
  assert.match(await state.render(), /报告格式无效/)
  assert.equal(state.sourceName.value, '团队')
  assert.equal(state.serverPath.value, '/readonly/report.json')
})

test('旧版弹窗进入时聚焦，Tab 限制在弹窗内，Esc 关闭后归还入口焦点', async () => {
  const state = createWorkspace({ fetchImportOptions: async () => ({ path_import_enabled: false, allowed_roots: [] }) })
  const opener = new state.Element()
  const first = new state.Element()
  const last = new state.Element()
  const panel = new state.Element()
  panel.querySelectorAll = () => [first, last]
  state.importPanel.value = vue.markRaw(panel)
  state.document.activeElement = opener
  state.toggleImport()
  const focusWatcher = state.watchers.find((item) => item.source === state.importDialogOpen)
  await focusWatcher.callback(true)
  assert.ok(state.keyListeners.has(state.importKeydown))
  assert.equal(state.document.activeElement, panel)
  let prevented = false
  state.document.activeElement = last
  state.importKeydown({ key: 'Tab', shiftKey: false, preventDefault() { prevented = true } })
  assert.equal(prevented, true)
  assert.equal(state.document.activeElement, first)
  state.document.activeElement = null
  for (const listener of state.keyListeners) {
    listener({ key: 'Escape', preventDefault() {}, stopPropagation() {} })
  }
  assert.equal(state.importOpen.value, false)
  await focusWatcher.callback(false)
  assert.equal(state.keyListeners.size, 0)
  assert.equal(state.document.activeElement, opener)
})

test('文档分类标签来自报告故障，计数按文档去重，筛选与翻页状态联动', async () => {
  const state = createWorkspace({})
  const a = { first_level_label: '网络', second_level_label: '连接', status: 'pair' }
  const b = { first_level_label: '存储', second_level_label: '容量', status: 'pair' }
  state.reports.value = [
    { report_id: 'pending', title: '多分类待验证文档', validation_status: 'pending', classifications: [a, a, b] },
    { report_id: 'done', title: '已验证文档', validation_status: 'validated', classifications: [a] },
  ]
  assert.deepEqual(state.firstOptions.value, ['网络', '存储'])
  assert.equal(state.count('网络'), 2)
  state.selectFirst('网络')
  state.selectSecond('连接')
  state.reportPage.value = 4
  state.documentFilter.value = 'pending'
  state.watchers.find((item) => item.source === state.documentFilter).callback()
  assert.equal(state.reportPage.value, 1)
  assert.equal(state.selection.value.second, '')
  assert.equal(state.count('网络'), 1)
  assert.deepEqual(state.filteredReports.value.map((item) => item.report_id), ['pending'])
  const html = await state.render()
  assert.equal((html.match(/多分类待验证文档/g) ?? []).length, 1)
  assert.doesNotMatch(html, />已验证文档</)
  state.reportPage.value = 3
  state.selectFirst('存储')
  assert.equal(state.reportPage.value, 1)
  assert.equal(state.selection.value.second, '')
})
