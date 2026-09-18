import assert from 'node:assert/strict'
import test from 'node:test'
import { assetLogFileCountText, countsSettled, countText } from '../src/utils/inspectionCounts.ts'

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

test('资产卡片计数只在拿到真实文件数后显示，0 是合法值而「没取到」不是', () => {
  // 计数来自 /log_file/list/{kb} 的 total；取不到就显示 —，
  // 不拿 task_cnt 兜底（UBSocket 资产的该列恒为 0）。
  assert.equal(assetLogFileCountText(undefined), '—')
  assert.equal(assetLogFileCountText(0), '0')
  assert.equal(assetLogFileCountText(2), '2')
})
