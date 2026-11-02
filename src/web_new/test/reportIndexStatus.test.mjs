import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), 'utf8')

const API_MODEL = read('../src/api/diagnosticReport.ts')
const REPORTS_PANEL = read('../src/views/assets/AssetReportsPanel.vue')

test('报告模型包含现象索引与案例绑定字段', () => {
  for (const field of [
    'index_status',
    'index_error',
    'status_counts',
    'indexable_fault_count',
    'confirmed_fault_count',
    'case_count',
    'verified_case_count',
    'report_available',
  ]) {
    assert.match(API_MODEL, new RegExp(`\\b${field}\\b`), `模型缺少字段：${field}`)
  }
})

test('报告表格展示索引状态与关联案例数', () => {
  assert.match(REPORTS_PANEL, /<th>现象索引<\/th>/)
  assert.match(REPORTS_PANEL, /<th class="num">案例<\/th>/)
  assert.match(REPORTS_PANEL, /report\.index_status/)
  assert.match(REPORTS_PANEL, /report\.case_count/)
  assert.match(REPORTS_PANEL, /report\.index_error/)
})

test('索引状态覆盖全部后端口径', () => {
  for (const label of ['已索引', '部分索引', '待索引', '索引失败', '无需索引']) {
    assert.ok(REPORTS_PANEL.includes(label), `缺少状态文案：${label}`)
  }
})
