import assert from 'node:assert/strict'
import test from 'node:test'
import {
  ASSET_REPORT_DIALOG_PAGE_SIZE,
  assetReportButtonTitle,
  buildAssetReportListNotice,
  isAssetReportButtonDisabled,
  resolveAssetReportButtonState,
} from '../src/utils/assetReport.ts'

test('resolveAssetReportButtonState: 探测中/未知总数为 loading', () => {
  assert.equal(resolveAssetReportButtonState(null), 'loading')
  assert.equal(resolveAssetReportButtonState(undefined), 'loading')
  assert.equal(resolveAssetReportButtonState(Number.NaN), 'loading')
  assert.equal(resolveAssetReportButtonState(3, true), 'loading')
  assert.equal(resolveAssetReportButtonState(-1), 'loading')
})

test('resolveAssetReportButtonState: 0/1/≥2 对应 empty/single/multiple', () => {
  assert.equal(resolveAssetReportButtonState(0), 'empty')
  assert.equal(resolveAssetReportButtonState(1), 'single')
  assert.equal(resolveAssetReportButtonState(2), 'multiple')
  assert.equal(resolveAssetReportButtonState(200), 'multiple')
})

test('只有 loading 态禁用按钮，empty 仍可点（点击后给 Agent 生成提示）', () => {
  assert.equal(isAssetReportButtonDisabled('loading'), true)
  assert.equal(isAssetReportButtonDisabled('empty'), false)
  assert.equal(isAssetReportButtonDisabled('single'), false)
  assert.equal(isAssetReportButtonDisabled('multiple'), false)
  assert.equal(assetReportButtonTitle('loading'), '正在检查该资产库的诊断报告…')
  assert.equal(assetReportButtonTitle('multiple'), '查看诊断报告')
})

test('buildAssetReportListNotice: 超出弹层上限提示跳全局报告库', () => {
  assert.equal(buildAssetReportListNotice(ASSET_REPORT_DIALOG_PAGE_SIZE), null)
  assert.equal(
    buildAssetReportListNotice(ASSET_REPORT_DIALOG_PAGE_SIZE + 1),
    `仅显示最近 ${ASSET_REPORT_DIALOG_PAGE_SIZE} 份，完整列表见「报告库」`,
  )
  assert.equal(buildAssetReportListNotice(3), null)
})
