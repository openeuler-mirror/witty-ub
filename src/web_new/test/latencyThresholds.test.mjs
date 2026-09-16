import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import {
  UBSOCKET_P99_ABNORMAL_THRESHOLD_US,
  evaluateTraceStage,
  traceStageDefinitions,
} from '../src/utils/latencyThresholds.ts'

const source = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')
const stageOf = (defs, name) => defs.find((def) => def.name === name)

test('阶段阈值对齐上游分列口径，总时延取解析配置', () => {
  const defs = traceStageDefinitions(5)

  assert.equal(defs[0].name, '总时延')
  assert.equal(defs[0].thresholdMs, 5)
  assert.equal(stageOf(defs, '查询元数据时延').thresholdMs, 1)
  assert.equal(stageOf(defs, 'URMA建链时延').thresholdMs, 1)
  assert.equal(stageOf(defs, 'Master RPC总时延').thresholdMs, 1)
  assert.equal(stageOf(defs, 'SDK处理时延').thresholdMs, 1.5)
  assert.equal(stageOf(defs, '本地Worker锁时延').thresholdMs, 1.5)
  assert.equal(stageOf(defs, '远端Worker RPC时延').thresholdMs, 1.5)

  // 配置改了，总时延阈值跟着走，其余阶段不受影响
  assert.equal(traceStageDefinitions(2)[0].thresholdMs, 2)
  assert.equal(stageOf(traceStageDefinitions(2), 'SDK处理时延').thresholdMs, 1.5)
})

test('阶段状态由各自阈值决定，不再继承整行 is_anomalous', () => {
  const defs = traceStageDefinitions(5)

  assert.equal(evaluateTraceStage(defs[0], 5.6).status, '异常')
  assert.equal(evaluateTraceStage(defs[0], 4.9).status, '正常')
  assert.equal(evaluateTraceStage(stageOf(defs, '查询元数据时延'), 1.2).status, '异常')
  assert.equal(evaluateTraceStage(stageOf(defs, '查询元数据时延'), 0.9).status, '正常')
  assert.equal(evaluateTraceStage(stageOf(defs, 'SDK处理时延'), 1.6).status, '异常')
  assert.equal(evaluateTraceStage(stageOf(defs, 'SDK处理时延'), 1.4).status, '正常')
  // 6.5ms 的 SDK 处理时延按 1.5ms 阈值判异常（同一行内各阶段互不影响）
  assert.equal(evaluateTraceStage(stageOf(defs, 'SDK处理时延'), 6.5).abnormal, true)
})

test('缺失值与失真值不参与阈值判定', () => {
  const total = traceStageDefinitions(5)[0]

  const missing = evaluateTraceStage(total, null)
  assert.equal(missing.status, '日志不存在该时延项目')
  assert.equal(missing.abnormal, false)
  assert.equal(missing.value, null)

  const negative = evaluateTraceStage(total, -1)
  assert.equal(negative.status, '由总时延被截断引起，该时延值已失真')
  assert.equal(negative.abnormal, false)

  // 后端可能把数值序列化成字符串
  assert.equal(evaluateTraceStage(total, '6.5').status, '异常')
  assert.equal(evaluateTraceStage(total, '').status, '日志不存在该时延项目')
})

test('UBSocket 单接口偏高阈值只有一处定义', () => {
  assert.equal(UBSOCKET_P99_ABNORMAL_THRESHOLD_US, 2000)

  const composable = source('../src/composables/useOverviewData.ts')
  const component = source('../src/components/overview/BRPCInterfaceMonitor.vue')

  assert.match(
    composable,
    /p99_ns \/ 1e3 > UBSOCKET_P99_ABNORMAL_THRESHOLD_US/,
    '接口状态按常量判定',
  )
  assert.match(component, /UBSOCKET_P99_ABNORMAL_THRESHOLD_US/, '表格取值与提示共用同一常量')
  assert.ok(!composable.includes('p99_ns / 1e6 > 2'), '不得再出现 2ms 魔法值')
  assert.ok(!component.includes('p99_ns / 1e6 > 2'), '不得再出现 2ms 魔法值')
  assert.ok(!component.includes('2000 µs'), '阈值文案由常量生成')
})

test('KVCache 时延明细改用逐项阈值', () => {
  const composable = source('../src/composables/useOverviewData.ts')

  assert.match(composable, /traceStageDefinitions\(latencyThresholds\.p99\)/, '总时延阈值来自配置')
  assert.match(composable, /evaluateTraceStage\(def, row \? row\[def\.key\] : null\)/)
  assert.ok(!composable.includes("row.is_anomalous\n"), '阶段状态不再依赖整行 is_anomalous')
})
