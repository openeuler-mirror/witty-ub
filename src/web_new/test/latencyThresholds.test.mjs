import assert from 'node:assert/strict'
import test from 'node:test'
import {
  evaluateTraceStage,
  traceStageDefinitions,
} from '../src/utils/latencyThresholds.ts'

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

test('阶段状态由各自的阈值决定，同行阶段互不影响', () => {
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
