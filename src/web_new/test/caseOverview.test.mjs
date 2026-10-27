import assert from 'node:assert/strict'
import test from 'node:test'
import { belongsToScope, collectPages, importForm, materialKey, reportNeedsVerification } from '../src/utils/caseWorkflow.ts'

test('正式库只展示已确认且闭环案例，待验证包括草稿与未闭环确认案例', () => {
  const cases = [
    { id: 'draft', status: 'draft' },
    { id: 'unverified', status: 'confirmed', verification_json: { closed_loop: false } },
    { id: 'verified', status: 'confirmed', verification_json: { closed_loop: true } },
    { id: 'archived', status: 'archived', verification_json: { closed_loop: true } },
  ]
  assert.deepEqual(cases.filter((item) => belongsToScope(item, 'library')).map((item) => item.id), ['verified'])
  assert.deepEqual(cases.filter((item) => belongsToScope(item, 'pending')).map((item) => item.id), ['draft', 'unverified'])
})

test('历史文件与诊断案例同号时身份不混用', () => {
  assert.notEqual(materialKey('legacy', 'same'), materialKey('diagnosis', 'same'))
})

test('多故障报告在所有可验证结论完成后才退出待验证', () => {
  assert.equal(reportNeedsVerification({ indexable_fault_count: 4, verified_case_count: 1 }), true)
  assert.equal(reportNeedsVerification({ indexable_fault_count: 4, verified_case_count: 4 }), false)
  assert.equal(reportNeedsVerification({ indexable_fault_count: 0, verified_case_count: 0 }), false)
  assert.equal(reportNeedsVerification({ fault_count: 2, verified_case_count: 1 }), true)
  assert.equal(reportNeedsVerification({ fault_count: null }), true)
})

test('超过两百条的案例和报告取完所有页', async () => {
  const records = Array.from({ length: 451 }, (_, id) => ({ id }))
  const calls = []
  assert.deepEqual(await collectPages(async (page, size) => {
    calls.push([page, size])
    return { total: records.length, items: records.slice((page - 1) * size, page * size) }
  }), records)
  assert.deepEqual(calls, [[1, 200], [2, 200], [3, 200]])
})

test('空尾页终止抓取，避免过期总数造成无限请求', async () => {
  let calls = 0
  assert.deepEqual(await collectPages(async () => ({ total: 900, items: ++calls === 1 ? ['a'] : [] })), ['a'])
  assert.equal(calls, 2)
})

test('外部导入携带明确的实操声明，不携带当前资产任务', () => {
  const file = new File(['{}'], 'cases.json')
  const form = importForm(file, ' 人员 ', ' 团队 ', false)
  assert.equal(form.get('operator'), '人员')
  assert.equal(form.get('source_name'), '团队')
  assert.equal(form.get('declared_verified'), 'false')
  assert.equal(form.get('file').name, 'cases.json')
  assert.deepEqual([...form.keys()].sort(), ['declared_verified', 'file', 'operator', 'source_name'])
  assert.equal(importForm(new File(['zip'], 'cases.ZIP'), 'a', 'b', true).get('declared_verified'), 'true')
})

test('导入前拒绝无文件、不支持格式以及空操作人与来源', () => {
  const file = new File(['{}'], 'cases.json')
  assert.throws(() => importForm(null, 'a', 'b', true), /JSON 或 ZIP/)
  assert.throws(() => importForm(new File(['x'], 'cases.html'), 'a', 'b', true), /JSON 或 ZIP/)
  assert.throws(() => importForm(file, ' ', 'b', true), /操作人/)
  assert.throws(() => importForm(file, 'a', ' ', true), /案例来源/)
})
