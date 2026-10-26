import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), 'utf8')

const APP = read('../src/App.vue')
const OVERVIEW = read('../src/components/CaseOverview.vue')

test('案例库为统一入口并保留三个来源视图', () => {
  assert.match(APP, /<strong>案例库<\/strong>/)
  assert.match(APP, /诊断案例与文件案例统一入口/)
  for (const label of ['全部来源', '诊断案例', '文件案例']) {
    assert.ok(APP.includes(`>\n            ${label}\n          <`), `缺少来源入口：${label}`)
  }
  assert.match(APP, /:class="\{ active: caseSource === 'all' \}"/)
})

test('文件案例只读，诊断案例才可打开详情', () => {
  assert.match(OVERVIEW, /if \(row\.source === 'diagnosis'\) emit\('open-case', row\.id\)/)
  assert.match(OVERVIEW, /v-if="row\.source === 'diagnosis'"[\s\S]*?openRow\(row\)/)
  assert.doesNotMatch(OVERVIEW, /row\.source === 'legacy'[\s\S]{0,80}open-case/)
})

test('聚合行标识带来源前缀，避免新旧 ID 混用', () => {
  assert.match(OVERVIEW, /key: `diagnosis:\$\{match\.case\.id\}`/)
  assert.match(OVERVIEW, /key: `legacy:\$\{item\.id\}`/)
})

test('文件案例沿用旧分类与固定信任标签', () => {
  assert.match(
    OVERVIEW,
    /\[item\.case_category \|\| '未分类', item\.root_cause_type\]/,
  )
  assert.match(OVERVIEW, /trust: '旧案例未验证'/)
})

test('旧案例只聚合文件案例，全部来源聚合两类', () => {
  assert.match(OVERVIEW, /props\.source === 'legacy' \? legacyRows : \[\.\.\.diagRows, \.\.\.legacyRows\]/)
  assert.match(OVERVIEW, /request<LegacyCase\[\]>\('\/case_library\/list'\)/)
})

test('来源切换与案例变更都会重新加载', () => {
  assert.match(OVERVIEW, /watch\(\s*\(\) => props\.source,[\s\S]*?void load\(\)/)
  assert.match(OVERVIEW, /watch\(\s*\(\) => props\.refreshToken,[\s\S]*?void load\(\)/)
  assert.match(APP, /:source="caseSource === 'legacy' \? 'legacy' : 'all'"/)
  assert.match(APP, /:refresh-token="workbenchRefreshToken"/)
})

test('统一列表逐页取完诊断案例并提供翻页', () => {
  assert.match(OVERVIEW, /const DIAG_PAGE_SIZE = 200/)
  assert.match(OVERVIEW, /do \{[\s\S]*page_num: pageNum[\s\S]*page_cnt: DIAG_PAGE_SIZE/)
  assert.match(OVERVIEW, /while \(collected\.length < total\)/)
  assert.match(OVERVIEW, /const PAGE_SIZE = 50/)
  assert.match(OVERVIEW, /v-for="row in pagedRows"/)
  assert.match(OVERVIEW, /共 \{\{ rows\.length \}\} 条/)
})

test('来源报告只在当前版本有效时提供链接', () => {
  assert.match(OVERVIEW, /reportStatus: match\.source_report\?\.status \?\? 'unavailable'/)
  assert.match(OVERVIEW, /row\.reportId && row\.reportStatus === 'valid'/)
  assert.match(OVERVIEW, /reportStatusText\(row\.reportStatus\)/)
})

test('来源报告跳转与诊断列表共用事件', () => {
  assert.match(OVERVIEW, /emit\('open-report', row\.reportId, row\.faultId \?\? ''\)/)
  assert.match(APP, /@open-report="openReportWorkbench"/)
})
