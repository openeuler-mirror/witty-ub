import assert from 'node:assert/strict'
import test from 'node:test'
import { collectSkippedFileAlerts, SKIPPED_REPORT_PREFIX } from '../src/utils/skipAlerts.ts'

test('跳过告警：只挑 [skip] 前缀的报告，去掉前缀后原样返回', () => {
  assert.equal(SKIPPED_REPORT_PREFIX, '[skip]')
  assert.deepEqual(
    collectSkippedFileAlerts([
      { message: '[skip] 跳过 2 个坏日志文件：broken.log（编码损坏）' },
      { message: 'Log parse completed' },
      { message: '  [skip] 跳过 1 个坏日志文件：half.log  ' },
    ]),
    ['跳过 2 个坏日志文件：broken.log（编码损坏）', '跳过 1 个坏日志文件：half.log'],
  )
})

test('跳过告警：没有报告 / 空列表 / 空 message / null 都不产生告警', () => {
  assert.deepEqual(collectSkippedFileAlerts(null), [])
  assert.deepEqual(collectSkippedFileAlerts(undefined), [])
  assert.deepEqual(collectSkippedFileAlerts([]), [])
  assert.deepEqual(collectSkippedFileAlerts([{ message: null }, {}, { message: '   ' }]), [])
  // 只有前缀没有正文：去掉前缀是空串，不算一条告警。
  assert.deepEqual(collectSkippedFileAlerts([{ message: '[skip]   ' }]), [])
})

test('跳过告警：前缀必须在开头，正文里出现不算', () => {
  assert.deepEqual(collectSkippedFileAlerts([{ message: '任务失败：[skip] 不是真告警' }]), [])
})
