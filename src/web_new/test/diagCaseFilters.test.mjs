import assert from 'node:assert/strict'
import test from 'node:test'
import {
  matchesClassification, selectPrimary, UNCLASSIFIED, canOpenSource, caseOrigin, populatedLabels, sourceReportLabel,
} from '../src/utils/caseWorkflow.ts'

test('全部包含所有分类，未分类仅包含两级标签都缺失的案例', () => {
  const cases = [{}, { first_level_label: '网络', second_level_label: '链路' }, { second_level_label: '残缺分类' }]
  assert.equal(cases.filter((item) => matchesClassification(item, '')).length, 3)
  assert.deepEqual(cases.filter((item) => matchesClassification(item, UNCLASSIFIED)), [{}])
})

test('二级分类限制在选中一级范围内，切换一级时重置二级与分页', () => {
  const item = { first_level_label: '网络', second_level_label: '链路' }
  assert.equal(matchesClassification(item, '网络', '链路'), true)
  assert.equal(matchesClassification(item, '网络', ''), true)
  assert.equal(matchesClassification(item, '存储', '链路'), false)
  assert.deepEqual(selectPrimary('存储'), { first: '存储', second: '', page: 1 })
  assert.deepEqual(selectPrimary(UNCLASSIFIED), { first: UNCLASSIFIED, second: '', page: 1 })
})

test('只允许有效来源跳转，其他状态使用清楚的解释', () => {
  assert.equal(canOpenSource({ status: 'valid', report_id: 'r' }), true)
  assert.equal(canOpenSource({ status: 'valid', report_id: null }), false)
  for (const status of ['stale', 'deleted', 'unavailable', 'independent']) {
    assert.equal(canOpenSource({ status, report_id: 'r' }), false)
  }
  assert.equal(canOpenSource(null), false)
  assert.equal(sourceReportLabel('stale'), '来源定界文档已变化')
  assert.equal(sourceReportLabel('deleted'), '来源定界文档已删除')
  assert.equal(sourceReportLabel('unavailable'), '来源定界文档暂不可用')
  assert.equal(sourceReportLabel('independent'), '独立案例')
})

test('两级分类只显示完整数据中有案例的标签，保留字典顺序与实际未知标签', () => {
  assert.deepEqual(populatedLabels(['空分类', '网络', '存储'], ['存储', null, '网络', '网络', '实际分类']), ['网络', '存储', '实际分类'])
  assert.deepEqual(populatedLabels(['空分类'], [null, undefined, '']), [])
  const cases = [
    { first_level_label: '网络', second_level_label: '链路' },
    { first_level_label: '存储', second_level_label: '磁盘' },
  ]
  assert.deepEqual(populatedLabels(['空分类', '磁盘', '链路'], cases.filter((item) => item.first_level_label === '网络').map((item) => item.second_level_label)), ['链路'])
})

test('无来源内部案例不标成现场诊断或导入，真实导入保留来源', () => {
  assert.equal(caseOrigin({ report_id: null }), '独立案例')
  assert.equal(caseOrigin({ report_id: null, confirmation_source: 'import' }), '外部导入')
  assert.equal(caseOrigin({ report_id: 'report-1' }), '现场诊断')
})
