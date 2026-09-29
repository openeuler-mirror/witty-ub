// 资产库内「查看诊断报告」入口的检查：纯逻辑（按钮三态、弹层提示）+ 真实模板渲染
// （从 App.vue 切出按钮与弹层两段模板，编译后 SSR 渲染再断言语义）。
// 设计依据：docs/design/asset-report-entry.md §5 / §9.1
import assert from 'node:assert/strict'
import test from 'node:test'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { compile } from '@vue/compiler-dom'
import * as Vue from 'vue'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import {
  ASSET_REPORT_DIALOG_PAGE_SIZE,
  assetReportButtonTitle,
  buildAssetReportListNotice,
  isAssetReportButtonDisabled,
  resolveAssetReportButtonState,
} from '../src/utils/assetReport.ts'

const HERE = dirname(fileURLToPath(import.meta.url))

const readAppVue = () => {
  const candidates = [
    resolve(HERE, '../src/App.vue'),
    resolve(process.cwd(), 'src/App.vue'),
    resolve(process.cwd(), 'src/web/src/App.vue'),
  ]
  for (const candidate of candidates) {
    if (existsSync(candidate)) return readFileSync(candidate, 'utf8')
  }
  throw new Error(`找不到 App.vue，试过：${candidates.join(' / ')}（请在 src/web 下运行）`)
}

const APP_VUE = readAppVue()

/** 从某个起始位置按标签配平切出完整元素（含起止标签）。 */
const sliceBalanced = (source, start, tag) => {
  const tags = new RegExp(`<${tag}[\\s>]|</${tag}>`, 'g')
  tags.lastIndex = start
  let depth = 0
  for (let match = tags.exec(source); match; match = tags.exec(source)) {
    depth += match[0] === `</${tag}>` ? -1 : 1
    if (depth === 0) return source.slice(start, match.index + match[0].length)
  }
  throw new Error(`<${tag}> 没有配平`)
}

/** 切出弹层模板（以唯一标识 v-if="assetReportDialogOpen" 定位根 div）。 */
const extractDialog = (source) => {
  const marker = 'v-if="assetReportDialogOpen"'
  const at = source.indexOf(marker)
  assert.notEqual(at, -1, `App.vue 里找不到弹层模板，测试需要同步更新：${marker}`)
  const start = source.lastIndexOf('<div', at)
  return sliceBalanced(source, start, 'div')
}

/** 切出入口按钮模板（以唯一类名定位）。 */
const extractEntryButton = (source) => {
  const marker = 'class="ghost-btn asset-report-entry-btn"'
  const at = source.indexOf(marker)
  assert.notEqual(at, -1, `App.vue 里找不到报告入口按钮，测试需要同步更新：${marker}`)
  return source.slice(
    source.lastIndexOf('<button', at),
    source.indexOf('</button>', at) + '</button>'.length,
  )
}

const compileTemplate = (template, label) => {
  const { code } = compile(template, { mode: 'function', prefixIdentifiers: true })
  const render = new Function('Vue', code)(Vue)
  assert.equal(typeof render, 'function', `${label}模板编译失败`)
  return render
}

const dialogRender = compileTemplate(extractDialog(APP_VUE), '报告弹层')
const entryButtonRender = compileTemplate(extractEntryButton(APP_VUE), '报告入口按钮')

const stripComments = (html) => html.replace(/<!--[\s\S]*?-->/g, '')

const DISPLAY_TEXT = (value) =>
  value === undefined || value === null || value === '' ? '—' : String(value)

const renderDialog = async (overrides = {}, reports = []) =>
  stripComments(
    await renderToString(
      createSSRApp({
        render: dialogRender,
        setup: () => ({
          assetReportDialogOpen: true,
          assetReportDialogTitle: '诊断报告 · kvcache-验收库',
          isAssetReportsLoading: false,
          assetReportsError: '',
          assetReports: reports,
          assetReportListNotice: null,
          diagnosticReportDisplayText: DISPLAY_TEXT,
          openDiagnosticReport: () => {},
          loadAssetReports: () => {},
          closeAssetReportDialog: () => {},
          ...overrides,
        }),
      }),
    ),
  )

/** 渲染入口按钮：状态由纯函数推导，与 App.vue 里的 computed 同源。 */
const renderEntryButton = async (total, loading = false) => {
  const state = resolveAssetReportButtonState(total, loading)
  return stripComments(
    await renderToString(
      createSSRApp({
        render: entryButtonRender,
        setup: () => ({
          assetReportButtonHint: assetReportButtonTitle(state),
          assetReportButtonDisabled: isAssetReportButtonDisabled(state),
          handleAssetReportClick: () => {},
        }),
      }),
    ),
  )
}

const REPORT_A = {
  report_id: 'report_kvcache-验收库_20260923090000',
  title: 'KVCache 通断诊断报告',
  generated_at: '2026-09-23 09:00:00',
  operation: 'GET',
  time_range_start: '2026-09-23 08:00:00',
  time_range_end: '2026-09-23 08:30:00',
  fault_count: 2,
  file_name: 'report_kvcache-验收库_20260923090000.html',
  has_sidecar: true,
}

const REPORT_B = {
  report_id: 'report_kvcache-验收库_20260923080000',
  title: 'KVCache 时延诊断报告',
  generated_at: '2026-09-23 08:00:00',
  operation: 'SET',
  time_range_start: '2026-09-23 07:00:00',
  time_range_end: '2026-09-23 07:30:00',
  fault_count: 1,
  file_name: 'report_kvcache-验收库_20260923080000.html',
  has_sidecar: true,
}

// ---------------------------------------------------------------- 纯逻辑（§5.1 三态）
test('按钮三态：0 份给提示 / 1 份直开 / ≥2 份弹层 / 探测中不可点', () => {
  assert.equal(resolveAssetReportButtonState(0, false), 'empty')
  assert.equal(resolveAssetReportButtonState(1, false), 'single')
  assert.equal(resolveAssetReportButtonState(2, false), 'multiple')
  assert.equal(resolveAssetReportButtonState(9, false), 'multiple')
  // 探测未完成或总数未知时不猜状态
  assert.equal(resolveAssetReportButtonState(0, true), 'loading')
  assert.equal(resolveAssetReportButtonState(3, true), 'loading')
  assert.equal(resolveAssetReportButtonState(null, false), 'loading')
  assert.equal(resolveAssetReportButtonState(undefined, false), 'loading')

  // 0 份不再置灰：按钮可点，点击后由弹层给出「暂无相关诊断报告，可通过 Agent 生成」
  assert.equal(isAssetReportButtonDisabled('empty'), false)
  assert.equal(isAssetReportButtonDisabled('loading'), true)
  assert.equal(isAssetReportButtonDisabled('single'), false)
  assert.equal(isAssetReportButtonDisabled('multiple'), false)

  assert.equal(assetReportButtonTitle('loading'), '正在检查该资产库的诊断报告…')
  assert.equal(assetReportButtonTitle('empty'), '查看诊断报告')
  assert.equal(assetReportButtonTitle('single'), '查看诊断报告')
  assert.equal(assetReportButtonTitle('multiple'), '查看诊断报告')
})

test('弹层末尾提示只在超过上限时出现', () => {
  assert.equal(buildAssetReportListNotice(0), null)
  assert.equal(buildAssetReportListNotice(ASSET_REPORT_DIALOG_PAGE_SIZE), null)
  assert.equal(
    buildAssetReportListNotice(ASSET_REPORT_DIALOG_PAGE_SIZE + 1),
    `仅显示最近 ${ASSET_REPORT_DIALOG_PAGE_SIZE} 份，完整列表见侧栏「诊断报告 → 报告库」`,
  )
  assert.equal(buildAssetReportListNotice(null), null)
})

// ---------------------------------------------------------------- 按钮渲染（§9.1 用例 1/2）
test('用例1：无报告库的按钮不置灰，点击后弹层给出生成指引', async () => {
  const html = await renderEntryButton(0)
  assert.match(html, /查看诊断报告/)
  assert.doesNotMatch(html, /disabled/)
  assert.match(html, /title="查看诊断报告"/)

  // empty 分支：开弹层但不打接口，直接落到弹层空态文案
  const entrySource = extractEntryButton(APP_VUE)
  assert.match(entrySource, /@click="handleAssetReportClick"/)
  const clickHandler = APP_VUE.slice(
    APP_VUE.indexOf('const handleAssetReportClick = ()'),
    APP_VUE.indexOf('const refreshLogFile = async'),
  )
  assert.match(clickHandler, /assetReportDialogOpen\.value = true/)
  assert.match(clickHandler, /assetReportButtonState\.value === 'empty'[\s\S]*?return/)
  assert.match(await renderDialog({}, []), /暂无相关诊断报告，可通过 Agent 生成/)
})

test('用例2：恰好 1 份时按钮可点（直开由 handleAssetReportClick 判定）', async () => {
  const html = await renderEntryButton(1)
  assert.doesNotMatch(html, /disabled/)
  assert.match(html, /title="查看诊断报告"/)
  // 按钮只负责把点击交给处理函数，不在模板里复制「1 份直开」的分支逻辑
  assert.match(extractEntryButton(APP_VUE), /@click="handleAssetReportClick"/)
})

// ---------------------------------------------------------------- 弹层渲染（§9.1 用例 3/4/5/8）
test('用例3：弹层列出该库全部报告，条数一致且关键字段齐全', async () => {
  const html = await renderDialog({}, [REPORT_A, REPORT_B])
  assert.match(html, /诊断报告 · kvcache-验收库/)
  assert.equal((html.match(/class="log-file-item"/g) ?? []).length, 2)
  for (const text of [
    'KVCache 通断诊断报告',
    '生成时间：2026-09-23 09:00:00',
    '故障数：2',
    '操作类型：GET',
    '时间范围：2026-09-23 08:00:00',
    '2026-09-23 08:30:00',
    'KVCache 时延诊断报告',
    '操作类型：SET',
  ]) {
    assert.ok(html.includes(text), `弹层缺少字段：${text}`)
  }
  assert.equal((html.match(/>\s*查看\s*</g) ?? []).length, 2)
  assert.ok(html.includes('刷新'))
  assert.ok(html.includes('关闭'))
})

test('用例4：弹层内查看按钮直连 openDiagnosticReport（弹层不关闭）', async () => {
  // 「查看」按钮块内只调用打开函数，不碰弹层开关 → 连看多份时弹层保持打开
  const dialogSource = extractDialog(APP_VUE)
  const viewAt = dialogSource.indexOf('openDiagnosticReport(report.report_id)')
  assert.notEqual(viewAt, -1, '弹层里找不到「查看」按钮')
  const viewButton = dialogSource.slice(
    dialogSource.lastIndexOf('<button', viewAt),
    dialogSource.indexOf('</button>', viewAt),
  )
  assert.match(viewButton, /@click="openDiagnosticReport\(report\.report_id\)"/)
  assert.doesNotMatch(viewButton, /closeAssetReportDialog/)
  assert.doesNotMatch(viewButton, /assetReportDialogOpen/)
})

test('用例5：侧车缺失的条目标题与故障数显示 —，并带徽标，仍可查看', async () => {
  const html = await renderDialog({}, [
    {
      ...REPORT_B,
      has_sidecar: false,
      title: null,
      fault_count: null,
      operation: null,
      time_range_start: null,
      time_range_end: null,
    },
  ])
  assert.ok(html.includes('无侧车数据'))
  assert.match(html, /故障数：\s*—/)
  // 标题、故障数、操作类型、时间范围（起止各一）都回落占位符
  assert.equal((html.match(/—/g) ?? []).length, 5)
  // 侧车缺失时仍以 report_id 作为悬停标识，且「查看」可用
  assert.match(html, /title="report_kvcache-验收库_20260923080000"/)
  assert.match(html, />\s*查看\s*</)
})

test('用例8：超过上限时列表末尾出现提示', async () => {
  const notice = buildAssetReportListNotice(ASSET_REPORT_DIALOG_PAGE_SIZE + 10)
  const html = await renderDialog({ assetReportListNotice: notice }, [REPORT_A, REPORT_B])
  assert.ok(html.includes(notice))
  const empty = await renderDialog({}, [REPORT_A])
  assert.doesNotMatch(empty, /仅显示最近/)
})

test('弹层加载/错误/空态各自给出提示', async () => {
  assert.match(await renderDialog({ isAssetReportsLoading: true }), /正在加载诊断报告/)
  assert.match(await renderDialog({ assetReportsError: '诊断报告加载失败' }), /诊断报告加载失败/)
  assert.match(await renderDialog({}, []), /暂无相关诊断报告，可通过 Agent 生成/)
})

// ---------------------------------------------------------------- 弹层骨架（§5.3 关闭方式）
test('弹层复用既有 modal 骨架：遮罩点击关闭 + 右上角关闭按钮', async () => {
  const dialogSource = extractDialog(APP_VUE)
  assert.match(dialogSource, /@click\.self="closeAssetReportDialog"/)
  assert.match(dialogSource, /class="close-modal"/)
  const html = await renderDialog({}, [REPORT_A])
  assert.match(html, /role="dialog"/)
  assert.match(html, /aria-modal="true"/)
  assert.match(html, /aria-label="诊断报告 · kvcache-验收库"/)
})

test('切换资产库时清空报告入口状态（含关闭弹层）', () => {
  const detail = APP_VUE.slice(
    APP_VUE.indexOf('const loadAssetDetail = async'),
    APP_VUE.indexOf('const openQueryDialog = ()'),
  )
  assert.match(detail, /resetAssetReportEntry\(\)/)
  assert.match(detail, /probeAssetReports\(assetId\)/)
  const reset = APP_VUE.slice(
    APP_VUE.indexOf('const resetAssetReportEntry = ()'),
    APP_VUE.indexOf('// 探测：只取 total'),
  )
  assert.match(reset, /assetReportDialogOpen\.value = false/)
  assert.match(reset, /assetReportTotal\.value = 0/)
})

test('探测与弹层拉取都按 kb_id 过滤，且探测只取 1 条', () => {
  const entry = APP_VUE.slice(
    APP_VUE.indexOf('const probeAssetReports = async'),
    APP_VUE.indexOf('const refreshLogFile = async'),
  )
  assert.match(entry, /kb_id: kbId, page_num: 1, page_cnt: 1/)
  assert.match(entry, /page_cnt: ASSET_REPORT_DIALOG_PAGE_SIZE/)
  assert.match(entry, /'\/diagnostic_report\/list'/)
})

test('全局报告库页未被改动：仍是不带 kb_id 的跨库列表', () => {
  const loadDiagnosticReports = APP_VUE.slice(
    APP_VUE.indexOf('const loadDiagnosticReports = async'),
    APP_VUE.indexOf('const openDiagnosticReportsPage = ()'),
  )
  assert.doesNotMatch(loadDiagnosticReports, /kb_id/)
  assert.match(loadDiagnosticReports, /page_cnt: diagnosticReportsPageSize/)
})

test('侧栏「诊断报告 → 报告库」入口保留（用例7）', () => {
  assert.ok(APP_VUE.includes('openDiagnosticReportsPage'))
  assert.ok(APP_VUE.includes("activePage === 'reports'"))
})
