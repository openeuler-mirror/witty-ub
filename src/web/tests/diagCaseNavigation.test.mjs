import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), 'utf8')

const APP = read('../src/App.vue')
const WORKBENCH = read('../src/components/ReportWorkbench.vue')
const DETAIL = read('../src/components/DiagCaseDetail.vue')
const PANEL = read('../src/components/DiagCasePanel.vue')

test('案例详情覆盖五种来源状态', () => {
  for (const [status, text] of [
    ['valid', '源报告当前版本有效'],
    ['stale', '源报告版本已变化'],
    ['deleted', '源报告不可用'],
    ['unavailable', '暂时无法校验源报告'],
    ['independent', '无关联报告'],
  ]) {
    assert.ok(DETAIL.includes(`${status}: '${text}'`), `缺少来源状态：${status}`)
  }
})

test('只有有效来源才允许跳转报告', () => {
  assert.match(DETAIL, /if \(source\.value\?\.status !== 'valid' \|\| !source\.value\.report_id\) return/)
  assert.match(DETAIL, /emit\('open-report', source\.value\.report_id, source\.value\.source_fault_id \?\? ''\)/)
})

test('案例到报告先关详情再开工作台', () => {
  assert.match(
    APP,
    /const openReportFromCase = \(reportId: string, faultId: string\) => \{\s*closeDiagCaseDetail\(\)\s*openReportWorkbench\(reportId, faultId\)/,
  )
  assert.match(APP, /@open-report="openReportFromCase"/)
})

test('案例确认或验证后工作台刷新', () => {
  assert.match(APP, /@changed="bumpWorkbench"/)
  assert.match(APP, /:refresh-token="workbenchRefreshToken"/)
  assert.match(WORKBENCH, /watch\(\s*\(\) => props\.refreshToken/)
})

test('关闭详情也会触发工作台刷新', () => {
  assert.match(
    APP,
    /const closeDiagCaseDetail = \(\) => \{\s*diagCaseDetailOpen\.value = false\s*bumpWorkbench\(\)/,
  )
})

test('案例列表可打开详情与来源报告', () => {
  assert.match(PANEL, /@click="emit\('open-case', item\.case\.id\)"/)
  assert.match(PANEL, /item\.case\.report_id && item\.source_report\?\.status === 'valid'/)
  assert.match(PANEL, /@click="emit\('open-report', item\.case\.report_id, item\.case\.source_fault_id \|\| ''\)"/)
})

test('案例列表确认后重新加载并支持翻页', () => {
  assert.match(PANEL, /watch\(\s*\(\) => props\.refreshToken/)
  assert.match(PANEL, /watch\(page, \(\) => void load\(\)\)/)
  assert.match(PANEL, /const PAGE_SIZE = 50/)
  assert.match(PANEL, /共 \{\{ total \}\} 条/)
})
