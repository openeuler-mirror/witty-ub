import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { compileTemplate, parse } from '@vue/compiler-sfc'
import { renderToString } from 'vue/server-renderer'
import ts from 'typescript'
import * as vue from 'vue'
import * as workflow from '../src/utils/caseWorkflow.ts'

const descriptor = parse(readFileSync(new URL('../src/components/knowledge/AllCasesSection.vue', import.meta.url), 'utf8')).descriptor
const source = descriptor.scriptSetup.content
const js = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText
const template = compileTemplate({
  source: descriptor.template.content, filename: 'AllCasesSection.vue', id: 'workspace',
  compilerOptions: { expressionPlugins: ['typescript'] },
})
const renderExports = {}
new Function('require', 'exports', ts.transpileModule(template.code, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText)(() => vue, renderExports)

const createWorkspace = (api, fetchCases = async () => []) => {
  const props = vue.reactive({ view: 'documents' })
  const watchers = []
  let renderedTree
  let renderedModalNodes = []
  const require = (name) => {
    if (name === 'vue') return { ...vue, onMounted: () => {}, watch: (source, callback) => watchers.push({ source, callback }) }
    if (name.endsWith('/api/diagnosticReport') || name.endsWith('/api/diagCaseLibrary')) return api
    if (name.endsWith('/api/caseLibrary')) return { fetchCases }
    if (name.endsWith('/utils/caseWorkflow')) return workflow
    if (name.endsWith('/useDiagCaseDetail')) return {
      useDiagCaseDetail: () => ({ openCase: () => {}, caseVersion: vue.ref(0), bumpCaseVersion: () => {} }),
    }
    if (name.endsWith('/useReportWorkbench')) return { useReportWorkbench: () => ({ openReport: () => {} }) }
    if (name.endsWith('/useOperator')) return { useOperator: () => ({ operator: vue.ref(''), setOperator: () => {} }) }
    throw new Error(`Unexpected import: ${name}`)
  }
  const state = new Function('require', 'exports', 'defineProps', 'defineEmits',
    `${js}\nreturn {
      load, reports, matches, legacyCases, reportCases, query, documentFilter, filteredReports, pagedReports, scopedMatches, error,
      loading, importOpen, importMode, importing, importError, file, serverPath, optionsError, importOptions,
      sourceName, operator, declaredVerified, batch, toggleImport, loadImportOptions, submitImport, outcomeLabel,
      reportPages, reportPage, firstOptions, secondOptions, selection, count, selectFirst, selectSecond,
      pagedCases, filtered, pages, filteredLegacy, pagedLegacy, legacyPages, legacyPage,
      importDialogOpen, closeImport, resetSearchPages,
    }`)(
    require, {}, () => props, () => () => {},
  )
  return {
    ...state, props, watchers,
    renderedInputs: () => {
      const inputs = []
      const visit = (node) => {
        if (Array.isArray(node)) { node.forEach(visit); return }
        if (!vue.isVNode(node)) return
        if (node.type === 'input') inputs.push(node.props)
        if (Array.isArray(node.children)) visit(node.children)
      }
      visit([renderedTree, renderedModalNodes])
      return inputs
    },
    renderedSearchForm: () => {
      let found
      const visit = (node) => {
        if (Array.isArray(node)) { node.forEach(visit); return }
        if (!vue.isVNode(node)) return
        if (node.type === 'form' && node.props?.role === 'search') found = node
        if (Array.isArray(node.children)) visit(node.children)
      }
      visit(renderedTree)
      return found
    },
    render: () => {
      const app = vue.createSSRApp({
        setup: () => ({ ...workflow, ...state, view: props.view, emit: () => {}, openCase: () => {}, openReport: () => {} }),
        render(...args) {
          renderedTree = renderExports.render.apply(this, args)
          return renderedTree
        },
      })
      app.component('PageNav', { render: () => null })
      app.component('BaseModal', {
        props: ['open', 'label', 'size', 'closeOnEsc', 'closeOnOverlay'],
        setup: (props, { slots }) => () => {
          renderedModalNodes = props.open ? [slots.header?.(), slots.default?.(), slots.footer?.()] : []
          return props.open ? vue.h('section', {
            role: 'dialog', 'aria-modal': 'true', 'aria-label': props.label,
            'data-close-on-esc': String(props.closeOnEsc), 'data-close-on-overlay': String(props.closeOnOverlay),
            'data-size': props.size,
          }, renderedModalNodes) : null
        },
      })
      return renderToString(app)
    },
  }
}

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

test('全局定界文档无需选择资产，取完全部页，已验证文档仍保留在全部文档', async () => {
  const documents = Array.from({ length: 253 }, (_, index) => ({
    report_id: `document-${index}`, kb_id: `asset-${index % 3}`,
    validation_status: index % 2 ? 'validated' : 'pending',
    indexable_fault_count: 2, validated_fault_count: index % 2 ? 2 : 0,
  }))
  const calls = []
  const state = createWorkspace({
    fetchDiagnosticReports: async (query) => {
      calls.push(query)
      const { pageNum, pageCnt } = query
      return { total: documents.length, items: documents.slice((pageNum - 1) * pageCnt, pageNum * pageCnt) }
    },
    searchDiagCases: async (query) => {
      assert.equal(query.scope, 'all')
      return { total: 0, matches: [] }
    },
  }, async () => { throw new Error('任务案例不属于文档待验证') })
  await state.load()
  assert.equal(state.error.value, '')
  assert.deepEqual(calls, [{ pageNum: 1, pageCnt: 100 }, { pageNum: 2, pageCnt: 100 }, { pageNum: 3, pageCnt: 100 }])
  assert.deepEqual(state.filteredReports.value, documents)
  assert.equal(new Set(state.reports.value.map((item) => item.kb_id)).size, 3)
  state.documentFilter.value = 'pending'
  assert.equal(state.filteredReports.value.length, 127)
  assert.ok(state.filteredReports.value.every((item) => item.validation_status === 'pending'))
  state.documentFilter.value = 'all'
  assert.equal(state.filteredReports.value.length, 253)
})

test('已知案例同时加载有效任务与文件案例，保留原分类，不触发文档验证查询', async () => {
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
    fetchDiagnosticReports: async () => { throw new Error('已知案例不混入文档') },
  }, async () => legacy)
  state.props.view = 'library'
  await state.load()
  assert.equal(state.error.value, '')
  assert.deepEqual(queries, [{ scope: 'library', includeStatus: ['confirmed'], pageNum: 1, pageCnt: 200 }])
  assert.equal(state.scopedMatches.value.length, 1)
  assert.deepEqual(state.legacyCases.value, legacy)
  assert.equal(workflow.legacyCaseOrigin(legacy[0]), '任务日志自动生成')
  assert.equal(workflow.legacyCaseOrigin(legacy[1]), '历史文件案例')
  assert.equal(state.reports.value.length, 0)
})

test('已知案例两张表不显示恒定状态列，仍保留已验证筛选及其他字段', async () => {
  const state = createWorkspace({})
  state.props.view = 'library'
  state.matches.value = [
    { case: { id: 'c1', title: '有效案例标题', symptom_summary: '故障现象', status: 'confirmed', verification_json: { closed_loop: true } } },
    { case: { id: 'c2', title: '待验证案例标题', status: 'draft' } },
  ]
  state.legacyCases.value = [{ id: 'l1', root_cause_type: '文件案例' }]
  const html = await state.render()
  const headers = [...html.matchAll(/<thead><tr>(.*?)<\/tr><\/thead>/g)]
    .map((match) => [...match[1].matchAll(/<th>(.*?)<\/th>/g)].map((item) => item[1]))
  assert.deepEqual(headers, [['案例', '来源', '更新时间'], ['案例', '来源', '附件']])
  assert.match(html, /有效案例标题/)
  assert.match(html, /故障现象/)
  assert.match(html, /文件案例/)
  assert.doesNotMatch(html, /待验证案例标题/)
  assert.doesNotMatch(html, /<th>状态<\/th>/)
})

test('文档与案例按编号或标题搜索，历史案例也参与关键词过滤', async () => {
  const state = createWorkspace({
    fetchDiagnosticReports: async () => ({ total: 2, items: [
      { report_id: 'r1', title: '网络故障' },
      { report_id: 'r2', title: '存储故障' },
    ] }),
    searchDiagCases: async () => ({ total: 1, matches: [
      { case: { id: 'case-1', case_no: 'UB-CASE-000123', title: '链路断开', report_id: 'r1', status: 'confirmed', verification_json: { closed_loop: true } } },
    ] }),
  }, async () => [{ id: 'old-1', root_cause_type: '网络故障', description: '历史记录' }])
  await state.load()
  state.query.value = 'ub-case-000123'
  assert.deepEqual(state.filteredReports.value.map((item) => item.report_id), ['r1'])
  state.query.value = '存储'
  assert.deepEqual(state.filteredReports.value.map((item) => item.report_id), ['r2'])
  state.props.view = 'library'
  await state.load()
  state.query.value = '链路 ub-case'
  assert.deepEqual(state.filtered.value.map((item) => item.case.id), ['case-1'])
  state.query.value = 'old-1'
  assert.deepEqual(state.filteredLegacy.value.map((item) => item.id), ['old-1'])
})

test('搜索框和搜索按钮位于文档、案例操作区，且无需打开导入弹窗', async () => {
  const state = createWorkspace({})
  for (const view of ['documents', 'library']) {
    state.props.view = view
    state.importOpen.value = false
    const html = await state.render()
    assert.match(html, /type="search"/)
    assert.match(html, view === 'documents' ? /搜索文档标题、案例 ID 或来源/ : /搜索案例 ID、标题或关键内容/)
    assert.match(html, /role="search"/)
    assert.match(html, /type="submit">搜索<\/button>/)
    assert.ok(html.indexOf('role="search"') < html.indexOf('>刷新</button>'))
    assert.doesNotMatch(html, /role="dialog"/)
  }
})

test('搜索条件变化或提交搜索时重置各列表页码并保留关键词', async () => {
  const state = createWorkspace({})
  state.query.value = 'UB-CASE'
  state.reportPage.value = 3
  state.selection.value.page = 4
  state.legacyPage.value = 5
  const watcher = state.watchers.find((entry) => entry.source === state.query)
  assert.ok(watcher)
  watcher.callback('关键词')
  assert.equal(state.reportPage.value, 1)
  assert.equal(state.selection.value.page, 1)
  assert.equal(state.legacyPage.value, 1)
  await state.render()
  state.reportPage.value = 3
  state.selection.value.page = 4
  state.legacyPage.value = 5
  let prevented = false
  state.renderedSearchForm().props.onSubmit({ preventDefault: () => { prevented = true } })
  assert.equal(prevented, true)
  assert.equal(state.reportPage.value, 1)
  assert.equal(state.selection.value.page, 1)
  assert.equal(state.legacyPage.value, 1)
  assert.equal(state.query.value, 'UB-CASE')
})

test('案例来源保留来源名称与有效文档链接，来源不可用时展示状态', async () => {
  const state = createWorkspace({})
  state.props.view = 'library'
  state.matches.value = [{
    case: { id: 'c1', title: '案例', report_id: 'r1', status: 'confirmed', verification_json: { closed_loop: true } },
    source_report: { status: 'valid' },
  }]
  let html = await state.render()
  assert.match(html, /现场诊断/)
  assert.match(html, /查看来源定界文档/)
  assert.match(html, /case-source-link/)
  state.matches.value[0].source_report.status = 'deleted'
  html = await state.render()
  assert.match(html, /来源定界文档已删除/)
  assert.doesNotMatch(html, /case-source-link/)
})

test('文档待验证只含未完成检验的结论，使用故障去重计数并兼容旧计数', () => {
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
  assert.match(closed, /导入定界报告/)
  assert.doesNotMatch(closed, /role="dialog"/)
  state.toggleImport()
  await Promise.resolve()
  let html = await state.render()
  assert.match(html, /role="dialog" aria-modal="true"/)
  assert.match(html, /class="import-panel"/)
  assert.match(html, /data-close-on-esc="true" data-close-on-overlay="true"/)
  assert.match(html, /data-size="form"/)
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

test('弹窗关闭保留输入与结果，导入期间禁止关闭和重复提交并关闭 Esc 与遮罩关闭能力', async () => {
  let resolveImport
  let imports = 0
  const result = {
    batch_id: 'batch', status: 'partial', file_count: 2,
    summary: { imported: 1, duplicate: 0, failed: 1, cases: { confirmed: 1, draft: 0, skipped: 0, existing: 0 } },
    items: [{ original_name: 'broken.json', status: 'failed', error: '报告格式无效' }],
  }
  const state = createWorkspace({
    fetchImportOptions: async () => ({ path_import_enabled: true, allowed_roots: ['/readonly'] }),
    importCases: async () => { imports++; return new Promise((resolve) => { resolveImport = resolve }) },
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
  const pending = state.submitImport()
  assert.equal(state.importing.value, true)
  state.closeImport()
  state.toggleImport()
  await state.submitImport()
  assert.equal(state.importOpen.value, true)
  assert.equal(imports, 1)
  const html = await state.render()
  assert.match(html, /data-close-on-esc="false" data-close-on-overlay="false"/)
  assert.match(html, /aria-label="关闭" disabled/)
  resolveImport(result)
  await pending
  assert.equal(state.importing.value, false)
  assert.equal(state.importOpen.value, true)
  assert.match(await state.render(), /报告格式无效/)
  state.closeImport()
  state.toggleImport()
  assert.match(await state.render(), /报告格式无效/)
  assert.equal(state.sourceName.value, '团队')
  assert.equal(state.serverPath.value, '/readonly/report.json')
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
