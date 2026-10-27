import assert from 'node:assert/strict'
import test from 'node:test'
import { canOpenSource, sourceReportLabel } from '../src/utils/caseWorkflow.ts'

test('来源报告仅在当前版本有效且有报告标识时允许打开', () => {
  assert.equal(canOpenSource({ status: 'valid', report_id: 'r' }), true)
  assert.equal(canOpenSource({ status: 'valid', report_id: null }), false)
  for (const status of ['stale', 'deleted', 'unavailable', 'independent']) {
    assert.equal(canOpenSource({ status, report_id: 'r' }), false)
  }
  assert.equal(canOpenSource(null), false)
})

test('来源过期、删除、不可用与独立案例分别解释，不暴露技术状态', () => {
  assert.equal(sourceReportLabel('stale'), '来源定界文档已变化')
  assert.equal(sourceReportLabel('deleted'), '来源定界文档已删除')
  assert.equal(sourceReportLabel('unavailable'), '来源定界文档暂不可用')
  assert.equal(sourceReportLabel('independent'), '独立案例')
  assert.equal(sourceReportLabel(undefined), '无关联定界文档')
})
