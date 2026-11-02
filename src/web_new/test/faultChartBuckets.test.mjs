import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { FAULT_CHART_MAX_POINTS, faultChartMaxPoints } from '../src/utils/faultChartBuckets.ts'

const MINUTE = 60_000
const DAY = 24 * 60 * MINUTE

test('取数上限 = 覆盖跨度的桶数：粒度越细、跨度越大，需要的点位越多', () => {
  // 30 分钟跨度、1 分钟桶 → 30 个桶，低于下限时按下限兜底
  assert.equal(faultChartMaxPoints(30 * MINUTE, 60), 100)
  // 10 小时跨度、1 分钟桶 → 600 个桶
  assert.equal(faultChartMaxPoints(10 * 60 * MINUTE, 60), 600)
  // 10 小时跨度、10 秒桶 → 3600 个桶
  assert.equal(faultChartMaxPoints(10 * 60 * MINUTE, 10), 3600)
})

test('跨度极大时封顶到上限，由后端保峰抽稀', () => {
  // 30 天跨度、10 秒桶 = 25.9 万个桶 → 封顶
  assert.equal(faultChartMaxPoints(30 * DAY, 10), FAULT_CHART_MAX_POINTS)
})

test('跨度未知或非法时用上限值，不做无意义的截断', () => {
  assert.equal(faultChartMaxPoints(null, 60), FAULT_CHART_MAX_POINTS)
  assert.equal(faultChartMaxPoints(0, 60), FAULT_CHART_MAX_POINTS)
  assert.equal(faultChartMaxPoints(10 * MINUTE, 0), FAULT_CHART_MAX_POINTS)
})

// 故障码图的数据由后端按 bucket_seconds 精确分桶：请求里必须带上粒度，
// 且 max_points 用调用方算好的值（不能再写死 1000）。
const analysisSource = readFileSync(new URL('../src/api/analysis.ts', import.meta.url), 'utf8')
const fetchFaultChartSource = analysisSource.slice(
  analysisSource.indexOf('export const fetchFaultChart'),
  analysisSource.indexOf('const FAULT_TRACE_PAGE_CNT'),
)
const fetchFaultChartJs = ts.transpileModule(fetchFaultChartSource.replace('export ', ''), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
}).outputText
const createFetchFaultChart = (request) =>
  new Function('request', `${fetchFaultChartJs}\nreturn fetchFaultChart`)(request)

test('故障码图请求按所选粒度与自适应上限取数', async () => {
  const calls = []
  const request = async (path, init) => {
    calls.push({ path, body: JSON.parse(init.body) })
    return { metrics: { '1': [{ time: '2026-09-23 10:00:00', err_cnt: 3 }] } }
  }
  const chart = await createFetchFaultChart(request)('kb-1', 'get', 600, 720)
  assert.equal(calls[0].path, '/log_failure_event_result/metrics/err_code')
  assert.deepEqual(calls[0].body, {
    kb_id: 'kb-1',
    max_points: 720,
    bucket_seconds: 600,
    operation: 'GET',
  })
  assert.deepEqual(chart, { '1': [{ time: '2026-09-23 10:00:00', err_cnt: 3 }] })
})
