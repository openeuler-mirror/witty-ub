import assert from 'node:assert/strict'
import test from 'node:test'
import { countCellTitle, countsSettled, countText } from '../src/utils/inspectionCounts.ts'

test('计数只在整条流水线成功后放出：其余状态显示 —（后端会固定返回 0）', () => {
  // 后端 LogFileService._mask_counts_until_complete：非成功状态一律置 0，
  // 界面若照实渲染 0，用户会读成「没有异常」。
  assert.equal(countsSettled('successful'), true)
  assert.equal(countsSettled('successful_pending_remove'), true)
  for (const status of [
    'pending',
    'running',
    'retrying',
    'failed',
    'failed_pending_remove',
    'cancelled',
    'unknown',
  ]) {
    assert.equal(countsSettled(status), false)
    assert.equal(countText(0, status), '—')
    assert.equal(countText(37, status), '—')
  }
  assert.equal(countText(37, 'successful'), '37')
  assert.equal(countText(undefined, 'successful'), '0')
  assert.equal(countText(null, 'successful_pending_remove'), '0')
})

test('悬停说明按日志类型给出这一列的真实含义', () => {
  assert.match(countCellTitle('latency', 'KVCache'), /时延异常 trace 条数/)
  assert.match(countCellTitle('latency', 'UBSocket'), /profiling 结果文件数/)
  assert.match(countCellTitle('fault', 'KVCache'), /故障 trace 条数/)
  assert.match(countCellTitle('fault', 'UBSocket'), /诊断命中的故障接口数/)
  assert.match(countCellTitle('latency', 'KVCache'), /显示为 —/)
})
