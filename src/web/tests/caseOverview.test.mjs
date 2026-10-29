import assert from 'node:assert/strict'
import test from 'node:test'
import {
  belongsToScope, caseOrigin, collectPages, importForm, matchesClassification, materialKey, populatedLabels,
  matchesKeywords, reportNeedsVerification, selectPrimary, UNCLASSIFIED,
} from '../src/utils/caseWorkflow.ts'

const item = (status, closed_loop) => ({ id: 'case-1', status, verification_json: { closed_loop } })

test('正式案例库仅包含已确认且实际闭环的案例，归档不混入', () => {
  const cases = [item('draft', false), item('confirmed', false), item('confirmed', true), item('archived', true)]
  assert.deepEqual(cases.filter((entry) => belongsToScope(entry, 'library')), [cases[2]])
  assert.deepEqual(cases.filter((entry) => belongsToScope(entry, 'pending')), cases.slice(0, 2))
  assert.equal(belongsToScope({ id: 'old', status: 'confirmed' }, 'library'), false)
  assert.equal(belongsToScope({ id: 'old', status: 'confirmed' }, 'pending'), true)
})

test('同号历史文件与诊断案例隔离，不复用详情身份', () => {
  assert.notEqual(materialKey('legacy', 'same-id'), materialKey('diagnosis', 'same-id'))
})

test('分类标签只保留完整数据中有记录的项，选中一级后不带入其他一级的二级标签', () => {
  assert.deepEqual(populatedLabels(['空分类', '网络', '存储'], ['存储', null, '网络', '网络', '实际分类']), ['网络', '存储', '实际分类'])
  assert.deepEqual(populatedLabels(['空分类'], [null, undefined, '']), [])
  const cases = [
    { first_level_label: '网络', second_level_label: '链路' },
    { first_level_label: '存储', second_level_label: '磁盘' },
  ]
  assert.deepEqual(populatedLabels(['空分类', '磁盘', '链路'], cases.filter((item) => item.first_level_label === '网络').map((item) => item.second_level_label)), ['链路'])
})

test('无来源内部案例使用独立案例口径，不伪装成现场诊断或外部导入', () => {
  assert.equal(caseOrigin({ report_id: null }), '独立案例')
  assert.equal(caseOrigin({ report_id: null, confirmation_source: 'import' }), '外部导入')
  assert.equal(caseOrigin({ report_id: 'report-1' }), '现场诊断')
})

test('待验证报告按全部可验证故障数判断完成，不能确认一条就隐藏多故障报告', () => {
  assert.equal(reportNeedsVerification({ indexable_fault_count: 3, verified_case_count: 1 }), true)
  assert.equal(reportNeedsVerification({ indexable_fault_count: 3, verified_case_count: 3 }), false)
  assert.equal(reportNeedsVerification({ indexable_fault_count: 0, verified_case_count: 0 }), false)
  assert.equal(reportNeedsVerification({ fault_count: 2, verified_case_count: 1 }), true)
  assert.equal(reportNeedsVerification({ fault_count: null }), true)
})

test('全部与未分类含义不同，一级切换重置二级与页码', () => {
  const cases = [{}, { first_level_label: '网络', second_level_label: '链路' }, { second_level_label: '仅二级' }]
  assert.equal(cases.filter((entry) => matchesClassification(entry, '')).length, 3)
  assert.deepEqual(cases.filter((entry) => matchesClassification(entry, UNCLASSIFIED)), [{}])
  assert.equal(matchesClassification(cases[1], '网络', '链路'), true)
  assert.equal(matchesClassification(cases[1], '网络', '路由'), false)
  assert.deepEqual(selectPrimary('存储'), { first: '存储', second: '', page: 1 })
})

test('加载超过两百条材料时取完所有服务端页，不截断尾页', async () => {
  const records = Array.from({ length: 453 }, (_, id) => ({ id }))
  const calls = []
  const result = await collectPages(async (page, size) => {
    calls.push([page, size])
    return { total: records.length, items: records.slice((page - 1) * size, page * size) }
  })
  assert.deepEqual(result, records)
  assert.deepEqual(calls, [[1, 200], [2, 200], [3, 200]])
})

test('服务端总数过期但尾页为空时停止取数', async () => {
  let calls = 0
  const result = await collectPages(async () => ({ total: 999, items: ++calls === 1 ? ['one'] : [] }))
  assert.deepEqual(result, ['one'])
  assert.equal(calls, 2)
})

test('导入仅提交外部来源与人员，不关联资产或任务，未验证声明可显式关闭', () => {
  const file = new File(['{}'], 'partner.json', { type: 'application/json' })
  const form = importForm(file, ' 操作人 ', ' 合作伙伴 ', false)
  assert.equal(form.get('operator'), '操作人')
  assert.equal(form.get('source_name'), '合作伙伴')
  assert.equal(form.get('declared_verified'), 'false')
  assert.equal(form.get('file').name, 'partner.json')
  assert.deepEqual([...form.keys()].sort(), ['declared_verified', 'file', 'operator', 'source_name'])
  assert.equal(importForm(new File(['zip'], 'cases.ZIP'), 'a', 'b', true).get('declared_verified'), 'true')
})

test('无文件、错误扩展名、空人员或来源都不发起导入', () => {
  const file = new File(['{}'], 'cases.json')
  assert.throws(() => importForm(null, 'a', 'b', true), /JSON 或 ZIP/)
  assert.throws(() => importForm(new File(['x'], 'cases.html'), 'a', 'b', true), /JSON 或 ZIP/)
  assert.throws(() => importForm(file, ' ', 'b', true), /操作人/)
  assert.throws(() => importForm(file, 'a', ' ', true), /案例来源/)
})

test('关键词忽略大小写与空白，可同时匹配案例编号、标题和摘要', () => {
  const fields = ['UB-CASE-000123', '网络链路故障', '连接超时']
  assert.equal(matchesKeywords('ub-case-000123 网络', fields), true)
  assert.equal(matchesKeywords('  连接 超时  ', fields), true)
  assert.equal(matchesKeywords('UB-CASE-999999', fields), false)
  assert.equal(matchesKeywords('', []), true)
})
