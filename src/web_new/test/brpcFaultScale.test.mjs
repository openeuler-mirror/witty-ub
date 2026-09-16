import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const srcDir = fileURLToPath(new URL('../src', import.meta.url))
const read = (path) => readFileSync(path, 'utf8')

// 取某个顶层 const 的函数体/表达式（兼容类型注解），直到下一个顶层 const 声明
const constBody = (source, name) => {
  const start = source.indexOf(`const ${name}`)
  assert.ok(start > 0, `找不到 ${name}`)
  const next = source.indexOf('\n  const ', start + 1)
  return source.slice(start, next === -1 ? source.length : next)
}

// 回归：UBSocket 公共 API 故障时序分布图的 10 秒与 1 分钟视图必须取到各自粒度的数据。
// 若始终按 window_size=1m 取数再在客户端二次分桶，1 分钟点永远分不出 10 秒细节。
// 守住「聚合尺度必须回查后端预聚合桶」。
test('UBSocket 故障时序按聚合尺度回查后端 window_size', () => {
  const source = read(join(srcDir, 'composables/useOverviewData.ts'))

  assert.match(
    constBody(source, 'brpcFaultWindowSizeByScale'),
    /10: '10s'/,
    '10 秒必须映射到 window_size=10s',
  )
  assert.match(
    constBody(source, 'brpcFaultWindowSizeByScale'),
    /60: '1m'/,
    '1 分钟必须映射到 window_size=1m',
  )

  const loader = constBody(source, 'loadBrpcFaultTimeline')
  assert.match(
    loader,
    /brpcFaultTimelineWindowSize\.value/,
    '加载时序必须按当前尺度取 window_size',
  )
  assert.match(
    loader,
    /fetchBrpcInterfaceTimeline\(\s*batchId,\s*startDate,\s*endDate,\s*windowSize/,
    '加载时序必须把尺度映射出的 window_size 传给接口，不得使用默认值',
  )
  assert.doesNotMatch(
    loader,
    /fetchBrpcInterfaceTimeline\(\s*batchId,\s*startDate,\s*endDate\s*\)/,
    '禁止不带 window_size 的取数（会退化成固定 1 分钟）',
  )

  // 尺度切换必须重新取数；曲线勾选只需重绘
  assert.match(
    source,
    /watch\(brpcFaultScale, \(\) => \{[^}]*void loadBrpcFaultTimeline\(\)/s,
    '切换聚合尺度必须重新查询后端',
  )
})

test('UBSocket 故障时序不在客户端二次分桶', () => {
  const source = read(join(srcDir, 'composables/useOverviewData.ts'))
  const view = constBody(source, 'brpcFaultTimelineView')

  assert.doesNotMatch(
    view,
    /Math\.floor\(/,
    '客户端二次分桶会掩盖查询粒度与尺度不一致：10 秒与 1 分钟都会取到同一份 1 分钟点',
  )
  assert.match(
    view,
    /window_start_time/,
    '应直接使用后端按 window_size 返回的桶起点',
  )
})

test('接口封装接受 10s/1m/10m/1h 四档 window_size', () => {
  const api = read(join(srcDir, 'api/analysis.ts'))

  assert.match(api, /BrpcTimelineWindowSize = '10s' \| '1m' \| '10m' \| '1h'/)
  assert.match(
    api,
    /fetchBrpcInterfaceTimeline = \(\s*batchId: string,\s*start: Date,\s*end: Date,\s*windowSize: BrpcTimelineWindowSize/,
    'fetchBrpcInterfaceTimeline 的 window_size 必须是显式参数',
  )
})
