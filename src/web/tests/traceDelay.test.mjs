import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

// 执行详情页实际使用的取值、格式化和状态函数，覆盖两个弹窗的共用逻辑。
const app = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const script = app.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
const names = [
  'getLatencySeriesConfig',
  'totalLatencyP99AbnormalThresholdMs',
  'traceDelayThresholdsUs',
  'traceDelayColumns',
  'formatMetricValue',
  'formatTraceDelayColumnValue',
  'getTraceDelayValue',
  'hasTruncatedTotalLatency',
  'isTraceDelayAbnormal',
  'getTraceDelayStatusLabel',
]
const source = ts.createSourceFile('App.ts', script, ts.ScriptTarget.Latest, true)
const declarations = source.statements.filter((statement) =>
  ts.isVariableStatement(statement) && statement.declarationList.declarations.some((declaration) =>
    names.includes(declaration.name.getText(source)),
  ),
)
assert.equal(declarations.length, names.length)
const js = ts.transpileModule(declarations.map((statement) => statement.getText(source)).join('\n'), {
  compilerOptions: { target: ts.ScriptTarget.ES2022 },
}).outputText
const {
  traceDelayColumns,
  formatTraceDelayColumnValue,
  getTraceDelayValue,
  hasTruncatedTotalLatency,
  isTraceDelayAbnormal,
  getTraceDelayStatusLabel,
} = new Function(`${js}\nreturn { ${names.join(', ')} }`)()
const sched = traceDelayColumns.find((column) => column.key === 'urma_sched_us')

test('调度时延回绕值按缺失数据展示，不标红或误报总时延截断', () => {
  for (const value of [2 ** 63, Number('18446744073709551615')]) {
    for (const trace of [
      { raw: { total_latency_us: 2000, urma_sched_us: value }, urma_sched_us: 7 },
      { raw: { total_latency_us: 2000 }, urma_sched_us: value },
    ]) {
      const actual = getTraceDelayValue(trace, sched)
      assert.equal(actual, null)
      assert.equal(formatTraceDelayColumnValue(actual, sched), '-')
      assert.equal(getTraceDelayStatusLabel(trace, sched), '日志不存在该时延项目')
      assert.equal(isTraceDelayAbnormal(trace, sched), false)
      assert.equal(hasTruncatedTotalLatency(trace), false)
    }
  }
})

test('正常调度值及阈值以下最近可表示值保持原样，raw 优先于备用字段', () => {
  // Number 在 2^63 附近无法逐个表示整数；边界下一个可表示值相差 1024。
  for (const value of [0, 7, 1500, 1501, 2 ** 63 - 1024]) {
    assert.equal(getTraceDelayValue({ raw: { urma_sched_us: value }, urma_sched_us: 99 }, sched), value)
    assert.equal(getTraceDelayValue({ urma_sched_us: value }, sched), value)
  }
  assert.equal(formatTraceDelayColumnValue(7, sched), '7.000 us')
  assert.equal(getTraceDelayStatusLabel({ raw: { urma_sched_us: 1500 } }, sched), '正常')
  assert.equal(getTraceDelayStatusLabel({ raw: { urma_sched_us: 1501 } }, sched), '异常')
})

test('缺失或非有限调度值仍按缺失处理，其他指标不应用调度上界', () => {
  for (const value of [null, undefined, NaN, Infinity, -Infinity]) {
    assert.equal(getTraceDelayValue({ raw: { urma_sched_us: value } }, sched), null)
  }
  const sdk = traceDelayColumns.find((column) => column.key === 'sdk_processing_us')
  assert.equal(getTraceDelayValue({ raw: { sdk_processing_us: 2 ** 63 } }, sdk), 2 ** 63)
  const trace = { raw: { total_latency_us: 2000, sdk_processing_us: 3000, urma_sched_us: 2 ** 63 } }
  assert.equal(hasTruncatedTotalLatency(trace), true)
  assert.equal(isTraceDelayAbnormal(trace, sdk), true)
})
