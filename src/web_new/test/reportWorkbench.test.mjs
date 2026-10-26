import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), 'utf8')

const API_MODEL = read('../src/api/diagnosticReport.ts')
const WORKBENCH = read('../src/components/report/ReportWorkbenchModal.vue')

test('报告模型包含审核状态、当前版本哈希与逐故障案例', () => {
  for (const field of [
    'review_status',
    'current_sidecar_hash',
    'review_confirmed_by',
    'review_confirmed_at',
    'case_refs',
    'fault_summaries',
    'verified_case_count',
  ]) {
    assert.match(API_MODEL, new RegExp(`\\b${field}\\b`), `模型缺少字段：${field}`)
  }
})

test('确认报告提交页面所见哈希与操作人', () => {
  assert.match(API_MODEL, /\/confirm`/)
  assert.match(API_MODEL, /expected_sidecar_hash: expectedSidecarHash/)
  assert.match(API_MODEL, /reviewed_by: reviewedBy/)
  assert.match(WORKBENCH, /report\.value\.current_sidecar_hash/)
})

test('未确认报告不能建案，确认按钮受当前版本哈希约束', () => {
  assert.match(
    WORKBENCH,
    /:disabled="report\.review_status !== 'confirmed' \|\| previewLoading"/,
  )
  assert.match(WORKBENCH, /:disabled="confirming \|\| !report\.current_sidecar_hash"/)
  assert.match(WORKBENCH, /报告需要人工确认后才能从故障生成案例/)
})

test('确认与建案都必须先填写操作人', () => {
  assert.equal(WORKBENCH.match(/requireOperator\(\)/g).length, 2)
  assert.equal(WORKBENCH.match(/请先填写操作人/g).length, 2)
})

test('逐故障展示关联案例状态与来源版本', () => {
  for (const text of [
    '来源版本已变化',
    '已确认未验证',
    '已验证',
    '暂无关联案例',
  ]) {
    assert.ok(WORKBENCH.includes(text), `缺少文案：${text}`)
  }
  assert.match(WORKBENCH, /item\.is_current_version/)
  assert.match(WORKBENCH, /item\.closed_loop/)
})

test('案例变更后工作台重新加载', () => {
  assert.match(WORKBENCH, /watch\(caseVersion,/)
  assert.match(WORKBENCH, /if \(open\.value\) void load\(\)/)
})

test('建案预览展示缺失项与分类快照', () => {
  assert.match(WORKBENCH, /preview\.missing_fields\.map\(missingLabel\)/)
  assert.match(WORKBENCH, /preview\.classification\.first_level_label/)
  assert.match(WORKBENCH, /缺少可匹配信号/)
})
