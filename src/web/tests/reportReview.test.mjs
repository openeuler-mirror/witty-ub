import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), 'utf8')

const APP = read('../src/App.vue')
const WORKBENCH = read('../src/components/ReportWorkbench.vue')
const API = read('../src/api/diagCase.ts')

test('报告列表展示审核状态与已验证案例数', () => {
  for (const text of ['未确认', '已确认', '确认过期', '不可校验']) {
    assert.ok(APP.includes(`'${text}'`) || APP.includes(`: '${text}'`), `缺少审核文案：${text}`)
  }
  assert.match(APP, /diagnosticReportReviewLabel\(report\.review_status\)/)
  assert.match(APP, /diagnosticReportReviewBadgeClass\(report\.review_status\)/)
  assert.match(APP, /已验证 \{\{ report\.verified_case_count \}\}/)
})

test('报告列表区分工作台与原文入口', () => {
  assert.equal(APP.match(/openReportWorkbench\(report\.report_id\)/g).length, 2)
  assert.equal(APP.match(/openDiagnosticReport\(report\.report_id\)/g).length, 2)
  assert.match(APP, />\s*工作台\s*</)
  assert.match(APP, />\s*原文\s*</)
})

test('确认报告提交页面所见哈希与操作人', () => {
  assert.match(API, /expected_sidecar_hash: expectedSidecarHash/)
  assert.match(API, /reviewed_by: reviewedBy/)
  assert.match(WORKBENCH, /const hash = report\.value\?\.current_sidecar_hash/)
  assert.match(WORKBENCH, /confirmReport\(props\.reportId, hash, operator\.value\)/)
})

test('工作台未确认时不能生成案例草稿', () => {
  assert.match(WORKBENCH, /report\.review_status !== 'confirmed'/)
  assert.match(WORKBENCH, /报告需人工确认后才能从故障生成案例/)
})

test('操作人保存在本地并在缺失时拒绝确认', () => {
  assert.match(WORKBENCH, /localStorage\.getItem\('witty-operator'\)/)
  assert.match(WORKBENCH, /localStorage\.setItem\('witty-operator', operator\.value\)/)
  assert.match(WORKBENCH, /请先填写操作人/)
})

test('逐故障展示案例状态、验证标签与来源版本', () => {
  for (const text of ['已验证', '已确认未验证', '来源版本已变化', '暂无关联案例']) {
    assert.ok(WORKBENCH.includes(text), `缺少文案：${text}`)
  }
  assert.match(WORKBENCH, /item\.is_current_version/)
  assert.match(WORKBENCH, /item\.verification/)
})
