import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const app = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const useAssets = readFileSync(
  new URL('../src/composables/useAssets.ts', import.meta.url),
  'utf8',
)

test('资产卡片展示真实任务信息，不再展示后端不可靠的异常计数', () => {
  assert.match(app, /assetTaskBadge\(asset\.id\)/, '卡片状态徽标取自最近任务摘要')
  assert.match(app, /asset\.task_cnt/, '卡片展示任务数')
  assert.ok(!app.includes('asset.anomaly_cnt'), '卡片不得展示 anomaly_cnt')
})

test('卡片摘要按资产只取最新一条任务', () => {
  assert.match(useAssets, /page_cnt: 1/, '每个资产只取 1 条任务')
  assert.match(useAssets, /created_sorted_desc: true/, '按创建时间倒序取最新')
})

test('任务列表移除无用的「更新」按钮与失败原因大色块', () => {
  assert.ok(!app.includes('⟳ 更新'), '更新按钮已移除')
  assert.ok(!app.includes('refreshOneLogFile'), '更新按钮的处理函数已移除')
  assert.match(app, /taskRowHint\(file\)/, '失败原因合并进行内单行提示')
  assert.ok(!app.includes('task-status-reason'), '不再使用大色块样式')
})
