import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildTaskLanes,
  formatTaskLaneSegmentTitle,
  normalizeParseTimingReport,
  taskLaneSegmentStyle,
} from '../src/utils/parseTiming.ts'

// 冻结契约里的三个 task_type（见 /log_file/list 的 stage_timings / task_spans）。
const PARSE = 'kv_cache_log_parse_worker'
const DIAGNOSIS = 'kv_cache_log_event_diagnosis_worker'
const STORE = 'store_trace_context_logs_worker'

// 时间轴原点用固定的绝对时刻，测试不依赖运行时钟。
const T0 = Date.parse('2026-09-15T10:00:00.000Z')
const at = (offsetS) => new Date(T0 + offsetS * 1000).toISOString()

// 真实形状的 fixture：三个任务并行，解析 0 → 12.5s，诊断 13.0 → 15.6s，落库 13.2 → 20.0s。
// 每个阶段带相对本任务 run() 起点的 start_s / end_s。
const stage = (name, label, startS, endS, extra = {}) => ({
  stage: name,
  label,
  wall_s: Number((endS - startS).toFixed(3)),
  cpu_s: null,
  cores: null,
  detail: null,
  start_s: startS,
  end_s: endS,
  ...extra,
})

const parseReport = {
  task_type: PARSE,
  total_s: 12.1,
  end_to_end_s: 12.5,
  outside_s: 0.4,
  rows: 1909790,
  stages: [
    stage('scan', '扫描', 0, 2.3, { cores: 7.83, cpu_s: 18.05, detail: '11 文件 / 1909790 行' }),
    stage('trace_frame', '组帧', 2.3, 5.0),
    stage('aggregate', '聚合', 5.0, 8.5),
    stage('detail', '明细', 8.5, 10.0),
    stage('bucket', '分桶', 10.0, 11.5),
    stage('store', '写库', 11.5, 12.1),
  ],
}

const diagnosisReport = {
  task_type: DIAGNOSIS,
  total_s: 2.2,
  end_to_end_s: 2.6,
  outside_s: 0.4,
  rows: null,
  stages: [
    stage('diagnose_prepare', '定界准备', 0, 0.4),
    stage('diagnose_tool', '定界工具', 0.4, 1.9),
    stage('diagnose_persist', '定界落库', 1.9, 2.2),
  ],
}

const storeReport = {
  task_type: STORE,
  total_s: 6.4,
  end_to_end_s: 6.8,
  outside_s: 0.4,
  rows: null,
  stages: [
    stage('trace_store_wait', '等待', 0, 4.0),
    stage('trace_store_collect', '取上下文', 4.0, 5.2),
    stage('trace_store_write', '写上下文', 5.2, 6.4),
  ],
}

const fullSpans = [
  { task_type: PARSE, start: at(0), end: at(12.5), duration_s: 12.5 },
  { task_type: DIAGNOSIS, start: at(13.0), end: at(15.6), duration_s: 2.6 },
  { task_type: STORE, start: at(13.2), end: at(20.0), duration_s: 6.8 },
]

const fullTimings = { [PARSE]: parseReport, [DIAGNOSIS]: diagnosisReport, [STORE]: storeReport }

const laneOf = (timeline, taskType) => timeline.lanes.find((lane) => lane.taskType === taskType)
const segmentOf = (lane, stageName) => lane.segments.find((segment) => segment.stage === stageName)

test('① 三条都有数据：3 条泳道，共用一条时间轴，各段相对位置正确', () => {
  const timeline = buildTaskLanes(fullTimings, fullSpans, { nowMs: T0 + 60_000 })
  assert.ok(timeline)
  assert.equal(timeline.lanes.length, 3)
  // 泳道顺序固定：解析 → 故障定界 → 上下文落库。
  assert.deepEqual(
    timeline.lanes.map((lane) => lane.label),
    ['解析', '故障定界', '上下文落库'],
  )
  // 时间轴原点 = 最早的 span.start（解析任务 0s 处），其余任务按自己的 span 起点平移。
  assert.equal(laneOf(timeline, PARSE).offsetS, 0)
  assert.equal(laneOf(timeline, DIAGNOSIS).offsetS, 13)
  assert.equal(laneOf(timeline, STORE).offsetS, 13.2)
  // 同一轴上的绝对位置：解析第一段贴轴起点，诊断第一段落在 13.0，落库的等待段 13.2 → 17.2。
  assert.equal(segmentOf(laneOf(timeline, PARSE), 'scan').startS, 0)
  assert.equal(segmentOf(laneOf(timeline, PARSE), 'scan').endS, 2.3)
  assert.equal(segmentOf(laneOf(timeline, DIAGNOSIS), 'diagnose_prepare').startS, 13)
  assert.equal(segmentOf(laneOf(timeline, DIAGNOSIS), 'diagnose_tool').startS, 13.4)
  assert.equal(segmentOf(laneOf(timeline, STORE), 'trace_store_wait').startS, 13.2)
  assert.equal(segmentOf(laneOf(timeline, STORE), 'trace_store_wait').endS, 17.2)
  assert.equal(segmentOf(laneOf(timeline, STORE), 'trace_store_write').endS, 19.6)
  // 阶段之间的空隙保留（解析 12.5 结束 → 诊断 13.0 开始，闲着 0.5s，正是「在等」）。
  assert.equal(laneOf(timeline, PARSE).endS, 12.5)
  assert.equal(laneOf(timeline, DIAGNOSIS).offsetS - laneOf(timeline, PARSE).endS, 0.5)
  // 端到端 = 最早 start → 最晚 end；泳道右端是各任务自己的总耗时。
  assert.equal(timeline.endToEndS, 20)
  assert.equal(timeline.totalS, 20)
  assert.equal(timeline.running, false)
  assert.equal(laneOf(timeline, PARSE).totalS, 12.5)
  assert.equal(laneOf(timeline, DIAGNOSIS).totalS, 2.6)
  assert.equal(laneOf(timeline, STORE).totalS, 6.8)
  // 位置可信时不加提示。
  assert.equal(laneOf(timeline, PARSE).note, null)
  // 等待类阶段（trace_store_wait）标记出来，界面画浅灰。
  assert.equal(segmentOf(laneOf(timeline, STORE), 'trace_store_wait').waiting, true)
  assert.equal(segmentOf(laneOf(timeline, STORE), 'trace_store_collect').waiting, false)
  // 各段全部带偏移 → 泳道位置可信。
  assert.equal(laneOf(timeline, PARSE).positionKnown, true)
  assert.equal(laneOf(timeline, DIAGNOSIS).positionKnown, true)
})

test('① 归一化后仍保留 task_type 与阶段偏移', () => {
  const report = normalizeParseTimingReport(parseReport)
  assert.ok(report)
  assert.equal(report.task_type, PARSE)
  assert.equal(report.stages[0].start_s, 0)
  assert.equal(report.stages[0].end_s, 2.3)
  // 老报告没有这两个字段时键不存在（= 位置未知），而不是 0。
  const legacy = normalizeParseTimingReport({ total_s: 3, stages: [{ stage: 'scan', label: '扫描', wall_s: 3 }] })
  assert.ok(legacy)
  assert.equal(legacy.task_type, undefined)
  assert.equal('start_s' in legacy.stages[0], false)
})

test('② 只有解析一条：只渲染 1 条泳道，其余不出现', () => {
  const timeline = buildTaskLanes(
    { [PARSE]: parseReport },
    [{ task_type: PARSE, start: at(0), end: at(12.5), duration_s: 12.5 }],
    { nowMs: T0 + 60_000 },
  )
  assert.ok(timeline)
  assert.equal(timeline.lanes.length, 1)
  assert.equal(timeline.lanes[0].taskType, PARSE)
  assert.equal(timeline.lanes[0].label, '解析')
  // 6 个打点阶段 + 1 个「收尾」段（最后一段阶段结束 → 任务被标记完成的间隙）
  assert.equal(timeline.lanes[0].segments.length, 7)
  assert.equal(timeline.lanes[0].segments[6].label, '收尾')
  assert.equal(timeline.lanes[0].segments[6].tail, true)
  assert.equal(timeline.endToEndS, 12.5)
  assert.equal(timeline.running, false)
})

test('③ 老数据（只有 parse_timing、无 start_s / 无 task_spans）：按 wall_s 顺序铺开并标注位置未知', () => {
  const legacyReport = {
    total_s: 11.885,
    stages: [
      { stage: 'scan', label: '扫描', wall_s: 2.304, cpu_s: 18.05, cores: 7.83, detail: '11 文件' },
      { stage: 'store', label: '写库', wall_s: 1.2 },
    ],
  }
  const timeline = buildTaskLanes({ [PARSE]: legacyReport }, null, { nowMs: T0 })
  assert.ok(timeline)
  assert.equal(timeline.lanes.length, 1)
  const lane = timeline.lanes[0]
  assert.equal(lane.offsetS, 0)
  assert.equal(lane.positionKnown, false)
  assert.equal(lane.note, '位置未知')
  // 从 0 起顺次铺：0 → 2.304 → 3.504。
  assert.equal(lane.segments[0].startS, 0)
  assert.equal(lane.segments[0].endS, 2.304)
  assert.equal(lane.segments[1].startS, 2.304)
  assert.equal(lane.segments[1].endS, 3.504)
  assert.equal(lane.segments[0].positionKnown, false)
  // 没有 span：泳道右端用报告里的端到端（这里老报告只有阶段之和 11.885s），
  // 时间轴也跟着拉满，色块只占前面 3.504s（其余是没打点的预处理/收尾）。
  assert.equal(lane.totalS, 11.885)
  assert.equal(lane.endS, 11.885)
  assert.equal(timeline.endToEndS, 11.885)
  // taskSpans 缺省 / 空 / 老接口整块没有 → 不抛异常。
  assert.equal(buildTaskLanes({ [PARSE]: legacyReport }, []).lanes.length, 1)
  assert.equal(buildTaskLanes({ [PARSE]: legacyReport }, undefined).lanes.length, 1)
  assert.equal(buildTaskLanes(null, null), null)
  assert.equal(buildTaskLanes({}, []), null)
  assert.equal(
    buildTaskLanes({ [PARSE]: { rows: 3 } }, [
      { task_type: PARSE, start: 'not-a-date', end: null, duration_s: 1 },
    ]),
    null,
  )
})

test('④ 未完成任务（end = null）：泳道画到「现在」并标进行中', () => {
  const nowMs = T0 + 15_000
  // 进行中的落库任务：最新一条报告只到已经跑完的 1.8s（13.2 → 15.0 = 现在）。
  const storeRunningReport = {
    task_type: STORE,
    total_s: 1.8,
    end_to_end_s: null,
    outside_s: null,
    rows: null,
    stages: [
      stage('trace_store_wait', '等待', 0, 1.2),
      stage('trace_store_collect', '取上下文', 1.2, 1.8),
    ],
  }
  const timeline = buildTaskLanes(
    { [PARSE]: parseReport, [STORE]: storeRunningReport },
    [
      { task_type: PARSE, start: at(0), end: at(12.5), duration_s: 12.5 },
      { task_type: STORE, start: at(13.2), end: null, duration_s: null },
    ],
    { nowMs },
  )
  assert.ok(timeline)
  assert.equal(timeline.running, true)
  const storeLane = laneOf(timeline, STORE)
  assert.equal(storeLane.running, true)
  // 落库任务 13.2s 起跑，现在 15.0s → 泳道右端画到 15.0，总耗时 = 已经跑了 1.8s。
  assert.equal(storeLane.offsetS, 13.2)
  assert.equal(storeLane.endS, 15)
  assert.equal(storeLane.totalS, 1.8)
  assert.equal(segmentOf(storeLane, 'trace_store_collect').endS, 15)
  // 端到端也按「现在」算，而不是等它结束。
  assert.equal(timeline.endToEndS, 15)
  // 已完成的那条泳道不受影响。
  assert.equal(laneOf(timeline, PARSE).running, false)
  assert.equal(laneOf(timeline, PARSE).totalS, 12.5)
})

test('⑤ span 缺 start（后端给 null）：不崩，泳道说明起点对齐不可用', () => {
  const timeline = buildTaskLanes(
    fullTimings,
    [
      { task_type: PARSE, start: null, end: at(12.5), duration_s: 12.5 },
      { task_type: STORE, start: null, end: at(20), duration_s: 6.8 },
    ],
    { nowMs: T0 + 60_000 },
  )
  assert.ok(timeline)
  assert.equal(timeline.lanes.length, 3)
  // 没有可用的 span → 各泳道退回自己的阶段偏移（0 起），并在泳道旁说明。
  assert.equal(timeline.lanes[0].offsetS, 0)
  assert.equal(timeline.lanes[0].note, '起点未知（span 缺 start）')
  assert.equal(timeline.lanes[0].totalS, 12.5)
  assert.equal(timeline.lanes[1].taskType, DIAGNOSIS)
  assert.equal(timeline.lanes[1].note, '起点未知（span 缺 start）')
  assert.equal(timeline.lanes[2].totalS, 6.8)
  // 时间轴长度退回各泳道铺开的宽度（解析那条最远到 12.5s）。
  assert.equal(timeline.endToEndS, 12.5)
  assert.equal(timeline.running, false)
})

test('色块定位与悬停文案', () => {
  const timeline = buildTaskLanes(fullTimings, fullSpans, { nowMs: T0 + 60_000 })
  assert.ok(timeline)
  const storeWait = segmentOf(laneOf(timeline, STORE), 'trace_store_wait')
  // 轴长 20s，等待段 13.2 → 17.2 → 左偏移 66%、宽 20%。
  assert.deepEqual(taskLaneSegmentStyle(storeWait, timeline.totalS), { left: '66.0000%', width: '20.0000%' })
  // 轴长非法时退化成不画，不产生 NaN%。
  assert.deepEqual(taskLaneSegmentStyle(storeWait, 0), { left: '0%', width: '0%' })
  const scan = segmentOf(laneOf(timeline, PARSE), 'scan')
  const title = formatTaskLaneSegmentTitle(scan, timeline.totalS)
  assert.match(title, /^扫描 · 用时 2\.3 s · 占比 11\.5% · 7\.83 核 · 11 文件 \/ 1909790 行$/)
  // 等待类阶段在悬停文案里点明「等待」（label 已经叫「等待」就不重复加）；缺核数显示 —。
  assert.match(formatTaskLaneSegmentTitle(storeWait, timeline.totalS), /^等待 · 用时 4\.0 s · 占比 20\.0% · —$/)
})

// ---------------------------------------------------------------------------
// started_at（阶段偏移的原点）：冻结契约里的真实样例
//   start      = 2026-09-15T23:15:34.934  任务注册（"Task initialized"）
//   started_at = 2026-09-15T23:15:36.032  worker 真正进 run() = 阶段偏移的原点
//   end        = 2026-09-15T23:15:37.237  duration_s = 2.303（= end − start）
// 阶段偏移相对 started_at，所以色块要画在 1.098s 之后，而不是贴着泳道起点。
// ---------------------------------------------------------------------------
const startedAt = (offsetS) => new Date(T0 + offsetS * 1000).toISOString()

const contractReport = {
  task_type: PARSE,
  total_s: 1.205,
  end_to_end_s: 1.205,
  outside_s: 0,
  rows: 11,
  stages: [stage('scan', '扫描', 0, 1.205, { cores: 7.83, detail: '11 文件' })],
}

test('⑥ 有 started_at：色块以 started_at 为锚点右移，并画出「排队 / 启动」头部段', () => {
  const spans = [
    {
      task_type: PARSE,
      start: startedAt(0),
      started_at: startedAt(1.098),
      end: startedAt(2.303),
      duration_s: 2.303,
    },
  ]
  const timeline = buildTaskLanes({ [PARSE]: contractReport }, spans, { nowMs: T0 + 60_000 })
  assert.ok(timeline)
  const lane = laneOf(timeline, PARSE)

  // 头部段：泳道起点 → started_at，标成「排队 / 启动」。
  const head = lane.segments[0]
  assert.equal(head.stage, '_head')
  assert.equal(head.label, '排队 / 启动')
  assert.equal(head.detail, '等调度派发 + 起进程')
  assert.equal(head.head, true)
  assert.equal(head.tail, undefined)
  assert.equal(head.positionKnown, true)
  assert.equal(head.startS, 0)
  assert.equal(head.endS, 1.098)
  assert.equal(head.durationS, 1.098)
  assert.equal(head.wallS, null)

  // 阶段段右移到 started_at 之后：扫描 1.098 → 2.303（改前是 0 → 1.205）。
  const scan = segmentOf(lane, 'scan')
  assert.equal(scan.startS, 1.098)
  assert.equal(scan.endS, 2.303)

  // 头尾对上了：灰色「收尾」段自然缩到 0，不再出现（以前那 1.1s 就是被画到右边当收尾的）。
  assert.equal(lane.segments.length, 2)
  assert.equal(segmentOf(lane, '_tail'), undefined)
  assert.equal(lane.offsetS, 0)
  assert.equal(lane.endS, 2.303)
  assert.equal(lane.totalS, 2.303)

  // 同一份数据、只把 started_at 去掉 = 改动前的样子：色块贴左边，右边多出 1.1s 灰「收尾」。
  const legacy = buildTaskLanes(
    { [PARSE]: contractReport },
    [{ task_type: PARSE, start: startedAt(0), end: startedAt(2.303), duration_s: 2.303 }],
    { nowMs: T0 + 60_000 },
  )
  assert.ok(legacy)
  assert.equal(laneOf(legacy, PARSE).segments[0].stage, 'scan')
  assert.equal(segmentOf(laneOf(legacy, PARSE), 'scan').startS, 0)
  const legacyTail = segmentOf(laneOf(legacy, PARSE), '_tail')
  assert.equal(legacyTail.startS, 1.205)
  assert.equal(legacyTail.endS, 2.303)
  assert.equal(legacyTail.durationS, 1.098)
})

test('⑦ 老数据（无 started_at / 键缺失 / 值为 null）：与改动前完全一致，不出现头部段', () => {
  const nowMs = T0 + 60_000
  const baseSpan = { task_type: PARSE, start: at(0), end: at(12.5), duration_s: 12.5 }
  const before = buildTaskLanes({ [PARSE]: parseReport }, [baseSpan], { nowMs })
  const nullKey = buildTaskLanes({ [PARSE]: parseReport }, [{ ...baseSpan, started_at: null }], { nowMs })
  assert.ok(before)
  assert.ok(nullKey)
  // 键不存在与键为 null 走同一条回退路径。
  assert.deepEqual(nullKey, before)
  // 形状与改动前一致：6 个打点阶段 + 1 个「收尾」，没有头部段，首段仍贴泳道起点。
  const lane = laneOf(before, PARSE)
  assert.equal(lane.segments.length, 7)
  assert.equal(lane.segments.some((segment) => segment.head === true), false)
  assert.equal(segmentOf(lane, 'scan').startS, 0)
  assert.equal(segmentOf(lane, 'store').endS, 12.1)
  assert.equal(lane.segments[6].label, '收尾')
  assert.equal(lane.segments[6].tail, true)
  assert.equal(lane.endS, 12.5)
  assert.equal(lane.totalS, 12.5)
})

test('⑧ started_at 解析不出来（垃圾值）时也不炸，退回泳道起点', () => {
  const nowMs = T0 + 60_000
  const baseSpan = { task_type: PARSE, start: at(0), end: at(12.5), duration_s: 12.5 }
  const expected = buildTaskLanes({ [PARSE]: parseReport }, [baseSpan], { nowMs })
  for (const garbage of ['not-a-date', '', '   ', '2026-13-45T99:99:99', {}, [], true]) {
    const timeline = buildTaskLanes(
      { [PARSE]: parseReport },
      [{ ...baseSpan, started_at: garbage }],
      { nowMs },
    )
    assert.ok(timeline, `started_at=${JSON.stringify(garbage)} 不该让整条时间线消失`)
    assert.deepEqual(timeline, expected, `started_at=${JSON.stringify(garbage)} 该退回泳道起点`)
  }
})

test('⑨ started_at 早于 start（时钟回拨/字段乱序）：锚点夹在泳道起点，色块不跑到左边', () => {
  const spans = [
    // 解析任务注册在 1s（时间轴原点由另一条 span 决定），但 started_at 早于自己的 start。
    { task_type: PARSE, start: at(1), started_at: at(0), end: at(13.5), duration_s: 12.5 },
    { task_type: DIAGNOSIS, start: at(0), end: at(2.6), duration_s: 2.6 },
  ]
  const timeline = buildTaskLanes(
    { [PARSE]: parseReport, [DIAGNOSIS]: diagnosisReport },
    spans,
    { nowMs: T0 + 60_000 },
  )
  assert.ok(timeline)
  const lane = laneOf(timeline, PARSE)
  assert.equal(lane.offsetS, 1)
  // 负的差距不画头部段，也没有任何色块落在泳道起点左边。
  assert.equal(lane.segments.some((segment) => segment.head === true), false)
  assert.equal(segmentOf(lane, 'scan').startS, 1)
})

// ---------------------------------------------------------------------------
// occurrences（冻结契约新增键）：同一阶段被登记多次时逐次各画一块
//
// 落库任务的三段各走两遍（第一轮等定界完成、第二轮等解析完成），阶段级的
// start_s/end_s 只是两次的并集 —— 旧画法里「等待」块会一路盖到 2.094s，
// 压在「写上下文」的 1.066s 上，看着像两块重叠；悬停也只剩第一轮的说明。
// 下面这份 fixture 按契约里的真实 payload 形状写（demo6 实测：等待 0.053→2.094、
// 取上下文 1.065→2.097、写上下文 1.066→2.594），三段各补上两次登记。
// ---------------------------------------------------------------------------
const occurrence = (startS, endS, wallS, detail) => ({
  start_s: startS,
  end_s: endS,
  wall_s: wallS,
  detail,
})

const storeRepeatedReport = {
  task_type: STORE,
  total_s: 2.538,
  end_to_end_s: 2.7,
  outside_s: 0.162,
  rows: null,
  stages: [
    {
      stage: 'trace_store_wait',
      label: '等待',
      wall_s: 2.031,
      cpu_s: null,
      cores: null,
      detail: '等故障定界完成',
      start_s: 0.053,
      end_s: 2.094,
      occurrences: [
        occurrence(0.053, 1.06, 1.007, '等故障定界完成'),
        occurrence(1.07, 2.094, 1.024, '等解析完成'),
      ],
    },
    {
      stage: 'trace_store_collect',
      label: '取上下文',
      wall_s: 0.006,
      cpu_s: null,
      cores: null,
      detail: '定界产出 0 个故障 trace',
      start_s: 1.065,
      end_s: 2.549,
      occurrences: [
        // 契约实测的形状：这一段「登记跨度」1.3s 起、墙钟只有 0.003s。
        occurrence(1.065, 1.517, 0.003, '定界产出 0 个故障 trace'),
        occurrence(2.097, 2.549, 0.003, '解析产出 2 个故障 trace'),
      ],
    },
    {
      stage: 'trace_store_write',
      label: '写上下文',
      wall_s: 0.501,
      cpu_s: null,
      cores: null,
      detail: '故障 trace 0 条落库',
      start_s: 1.066,
      end_s: 2.594,
      occurrences: [
        occurrence(1.066, 1.267, 0.201, '故障 trace 0 条落库'),
        occurrence(2.094, 2.594, 0.3, '时延异常 trace 2 条落库'),
      ],
    },
  ],
}

const storeRepeatedSpan = [{ task_type: STORE, start: at(0), end: at(2.7), duration_s: 2.7 }]
const nowMs = T0 + 60_000

test('⑩ occurrences 长度 ≥2：落库三段各画两块，位置用各次的偏移、悬停用各次的 wall_s/detail', () => {
  const timeline = buildTaskLanes(
    { [STORE]: storeRepeatedReport },
    storeRepeatedSpan,
    { nowMs },
  )
  assert.ok(timeline)
  assert.equal(timeline.lanes.length, 1)
  const lane = timeline.lanes[0]
  assert.equal(lane.label, '上下文落库')
  // 6 块（三段各两块）+ 1 个「收尾」段；没有头部段（这份 span 没给 started_at）。
  assert.equal(lane.segments.length, 7)
  assert.equal(lane.segments.filter((segment) => segment.stage === 'trace_store_wait').length, 2)
  assert.equal(lane.segments.filter((segment) => segment.stage === 'trace_store_collect').length, 2)
  assert.equal(lane.segments.filter((segment) => segment.stage === 'trace_store_write').length, 2)
  assert.equal(lane.segments[6].label, '收尾')

  // 每块的位置 = 该次登记自己的 start_s/end_s（相对 run() 起点，本 fixture 锚点在 0）。
  const byStage = (name) => lane.segments.filter((segment) => segment.stage === name)
  const spans = (name) => byStage(name).map((segment) => [segment.startS, segment.endS])
  assert.deepEqual(spans('trace_store_wait'), [
    [0.053, 1.06],
    [1.07, 2.094],
  ])
  assert.deepEqual(spans('trace_store_collect'), [
    [1.065, 1.517],
    [2.097, 2.549],
  ])
  assert.deepEqual(spans('trace_store_write'), [
    [1.066, 1.267],
    [2.094, 2.594],
  ])

  // 同一阶段的块之间不许重叠：按时间先后排列，前一块的终点 ≤ 后一块的起点。
  for (const name of ['trace_store_wait', 'trace_store_collect', 'trace_store_write']) {
    const ordered = [...byStage(name)].sort((a, b) => a.startS - b.startS)
    for (let i = 1; i < ordered.length; i += 1) {
      assert.ok(
        ordered[i - 1].endS <= ordered[i].startS,
        `${name} 第 ${i} 块与第 ${i + 1} 块重叠：${ordered[i - 1].endS} > ${ordered[i].startS}`,
      )
    }
  }
  // 旧画法的病根：阶段级并集 0.053→2.094 会盖住「写上下文」的 1.066。
  // 现在第一块「等待」在 1.060 就收手了，不再压着写库。
  assert.equal(byStage('trace_store_wait')[0].endS, 1.06)
  assert.ok(byStage('trace_store_wait')[0].endS < byStage('trace_store_write')[0].startS)
  // 同一阶段同色：stage 名不变 → 色块类名与图例都还是同一个阶段。
  assert.deepEqual(
    [...new Set(lane.segments.map((segment) => segment.stage))],
    ['trace_store_wait', 'trace_store_collect', 'trace_store_write', '_tail'],
  )
  assert.equal(byStage('trace_store_wait').every((segment) => segment.waiting), true)
  assert.equal(byStage('trace_store_write').every((segment) => segment.waiting), false)
  assert.equal(lane.positionKnown, true)

  // 悬停：用时/说明都取这一块自己那次登记的 wall_s / detail（旧代码里第二轮被吞掉）。
  const titles = byStage('trace_store_wait').map((segment) =>
    formatTaskLaneSegmentTitle(segment, timeline.totalS),
  )
  assert.deepEqual(titles, [
    '等待 · 用时 1.0 s · 占比 37.3% · — · 等故障定界完成',
    '等待 · 用时 1.0 s · 占比 37.9% · — · 等解析完成',
  ])
  // 「取上下文」第二次登记的详情（旧代码里根本读不到）现在各归各的块。
  assert.deepEqual(
    byStage('trace_store_collect').map((segment) =>
      formatTaskLaneSegmentTitle(segment, timeline.totalS),
    ),
    [
      '取上下文 · 用时 0.0 s · 占比 0.1% · — · 定界产出 0 个故障 trace',
      '取上下文 · 用时 0.0 s · 占比 0.1% · — · 解析产出 2 个故障 trace',
    ],
  )
  assert.deepEqual(
    byStage('trace_store_write').map((segment) =>
      formatTaskLaneSegmentTitle(segment, timeline.totalS),
    ),
    [
      '写上下文 · 用时 0.2 s · 占比 7.4% · — · 故障 trace 0 条落库',
      '写上下文 · 用时 0.3 s · 占比 11.1% · — · 时延异常 trace 2 条落库',
    ],
  )
  // 「用时」按该次自己的 wall_s（不是块宽）：取上下文那两次墙钟都是 0.003s，
  // 但第二块的宽度是真实跨度 —— 位置用偏移、用时用墙钟，两回事。
  const collectSecond = byStage('trace_store_collect')[1]
  assert.equal(collectSecond.durationS, 0.003)
  assert.equal(collectSecond.wallS, 0.003)
  assert.ok(collectSecond.endS - collectSecond.startS > 0.4, '块宽照旧是两次偏移之差')

  // 泳道右端 / 「收尾」段按**所有块的最大 endS** 算（= 2.594，最后一块写上下文）。
  const maxBlockEndS = lane.segments
    .filter((segment) => !segment.tail && !segment.head)
    .reduce((acc, segment) => Math.max(acc, segment.endS), 0)
  assert.equal(maxBlockEndS, 2.594)
  assert.equal(segmentOf(lane, '_tail').startS, 2.594)
  assert.equal(segmentOf(lane, '_tail').endS, 2.7)
  assert.equal(lane.endS, 2.7)
  assert.equal(timeline.totalS, 2.7)

  // 块的位置与颜色类名一致地落在一根轴上：轴长 2.7s 时第一块「等待」占 1.96% → 37.30%。
  assert.deepEqual(taskLaneSegmentStyle(byStage('trace_store_wait')[0], timeline.totalS), {
    left: '1.9630%',
    width: '37.2963%',
  })
})

test('⑩b 只有出现过的块参与「收尾」起点：最后一块结束到任务结束之间才画收尾', () => {
  // span 就在最后一块的终点收住 → 没有收尾段，泳道右端 = 最大块 endS。
  const timeline = buildTaskLanes(
    { [STORE]: storeRepeatedReport },
    [{ task_type: STORE, start: at(0), end: at(2.594), duration_s: 2.594 }],
    { nowMs },
  )
  assert.ok(timeline)
  const lane = timeline.lanes[0]
  assert.equal(segmentOf(lane, '_tail'), undefined)
  assert.equal(lane.endS, 2.594)
  assert.equal(lane.totalS, 2.594)
  assert.equal(lane.segments.length, 6)
})

test('⑪ 老数据（没有 occurrences）与只登记一次（长度 1）：逐字段与改动前一致', () => {
  // 契约样例的「并集」形态：三段各一次，没有 occurrences 键 —— 旧画法原样保留。
  const legacyReport = {
    task_type: STORE,
    total_s: 2.538,
    end_to_end_s: 2.7,
    outside_s: 0.162,
    rows: null,
    stages: [
      {
        stage: 'trace_store_wait',
        label: '等待',
        wall_s: 2.031,
        cpu_s: null,
        cores: null,
        detail: '等故障定界完成',
        start_s: 0.053,
        end_s: 2.094,
      },
      {
        stage: 'trace_store_collect',
        label: '取上下文',
        wall_s: 0.006,
        cpu_s: null,
        cores: null,
        detail: '定界产出 0 个故障 trace',
        start_s: 1.065,
        end_s: 2.1,
      },
      {
        stage: 'trace_store_write',
        label: '写上下文',
        wall_s: 0.501,
        cpu_s: null,
        cores: null,
        detail: '故障 trace 0 条落库',
        start_s: 1.066,
        end_s: 2.594,
      },
    ],
  }
  const timeline = buildTaskLanes({ [STORE]: legacyReport }, storeRepeatedSpan, { nowMs })
  assert.ok(timeline)
  // 改动前的输出逐字段钉死：阶段级并集跨度、durationS = 两端之差（不是 wall_s）、
  // 悬停说明仍是第一轮那条 detail，末尾一个「收尾」段。
  assert.deepEqual(timeline, {
    lanes: [
      {
        taskType: STORE,
        label: '上下文落库',
        segments: [
          {
            stage: 'trace_store_wait',
            label: '等待',
            startS: 0.053,
            endS: 2.094,
            durationS: 2.041,
            wallS: 2.031,
            cpuS: null,
            cores: null,
            detail: '等故障定界完成',
            waiting: true,
            positionKnown: true,
          },
          {
            stage: 'trace_store_collect',
            label: '取上下文',
            startS: 1.065,
            endS: 2.1,
            durationS: 1.035,
            wallS: 0.006,
            cpuS: null,
            cores: null,
            detail: '定界产出 0 个故障 trace',
            waiting: false,
            positionKnown: true,
          },
          {
            stage: 'trace_store_write',
            label: '写上下文',
            startS: 1.066,
            endS: 2.594,
            durationS: 1.528,
            wallS: 0.501,
            cpuS: null,
            cores: null,
            detail: '故障 trace 0 条落库',
            waiting: false,
            positionKnown: true,
          },
          {
            stage: '_tail',
            label: '收尾',
            startS: 2.594,
            endS: 2.7,
            durationS: 0.106,
            wallS: null,
            cpuS: null,
            cores: null,
            detail: '状态更新 / 调度延迟',
            waiting: false,
            positionKnown: true,
            tail: true,
          },
        ],
        offsetS: 0,
        endS: 2.7,
        totalS: 2.7,
        running: false,
        positionKnown: true,
        note: null,
      },
    ],
    totalS: 2.7,
    endToEndS: 2.7,
    running: false,
  })

  // 长度 = 1：同一条报告带上一条与阶段级同值的 occurrence → 结果必须逐字段相同
  // （不做任何分段，也不改写阶段级字段）。
  const withSingle = {
    ...legacyReport,
    stages: legacyReport.stages.map((stage) => ({
      ...stage,
      occurrences: [
        occurrence(stage.start_s, stage.end_s, stage.wall_s, stage.detail),
      ],
    })),
  }
  assert.deepEqual(buildTaskLanes({ [STORE]: withSingle }, storeRepeatedSpan, { nowMs }), timeline)

  // 老数据（连偏移都没有）：也逐字段不受影响。
  const noOffsets = {
    total_s: 3.5,
    stages: [
      { stage: 'scan', label: '扫描', wall_s: 2.3 },
      { stage: 'store', label: '写库', wall_s: 1.2 },
    ],
  }
  const noOffsetTimeline = buildTaskLanes({ [PARSE]: noOffsets }, null, { nowMs })
  assert.ok(noOffsetTimeline)
  assert.deepEqual(
    noOffsetTimeline.lanes[0].segments.map((segment) => [
      segment.startS,
      segment.endS,
      segment.durationS,
      segment.detail,
    ]),
    [
      [0, 2.3, 2.3, null],
      [2.3, 3.5, 1.2, null],
    ],
  )
  assert.equal(noOffsetTimeline.lanes[0].note, '位置未知')
})

test('⑫ occurrences 是空数组 / 坏值：不炸，退回改动前行为', () => {
  const base = {
    task_type: STORE,
    total_s: 2.538,
    end_to_end_s: 2.7,
    outside_s: 0.162,
    rows: null,
    stages: [
      {
        stage: 'trace_store_wait',
        label: '等待',
        wall_s: 2.031,
        cpu_s: null,
        cores: null,
        detail: '等故障定界完成',
        start_s: 0.053,
        end_s: 2.094,
      },
    ],
  }
  const expected = buildTaskLanes({ [STORE]: base }, storeRepeatedSpan, { nowMs })
  assert.ok(expected)
  assert.equal(expected.lanes[0].segments.length, 2)
  assert.equal(expected.lanes[0].segments[0].detail, '等故障定界完成')
  assert.equal(expected.lanes[0].segments[0].durationS, 2.041)

  const withOccurrences = (value) => ({
    ...base,
    stages: [{ ...base.stages[0], occurrences: value }],
  })
  const valid = occurrence(0.053, 2.094, 2.031, '等故障定界完成')
  const badValues = [
    [],
    'nope',
    null,
    7,
    {},
    [null, 'junk', 7, [], ['x']],
    [null, { start_s: 'not-a-number' }],
    // 只有一条有效条目（另一个是垃圾）→ 仍按一条走老路径。
    [valid, null],
    [{}, {}],
  ]
  for (const bad of badValues) {
    const timeline = buildTaskLanes({ [STORE]: withOccurrences(bad) }, storeRepeatedSpan, { nowMs })
    assert.ok(timeline, `occurrences=${JSON.stringify(bad)} 不该让整条时间线消失`)
    assert.deepEqual(
      timeline,
      expected,
      `occurrences=${JSON.stringify(bad)} 该逐字段退回改动前行为`,
    )
  }

  // 归一化层面：一条有效条目都没有 → 键根本不写出来（= 后端没给这个键）。
  const legacyShape = normalizeParseTimingReport({
    total_s: 3,
    stages: [{ stage: 'scan', label: '扫描', wall_s: 3, start_s: 0, end_s: 3 }],
  })
  assert.ok(legacyShape)
  for (const bad of [[], 'nope', null, [null, 'junk'], {}, [['x']]]) {
    const report = normalizeParseTimingReport({
      total_s: 3,
      stages: [
        { stage: 'scan', label: '扫描', wall_s: 3, start_s: 0, end_s: 3, occurrences: bad },
      ],
    })
    assert.ok(report, `occurrences=${JSON.stringify(bad)} 不该让整份报告作废`)
    assert.equal(
      'occurrences' in report.stages[0],
      false,
      `occurrences=${JSON.stringify(bad)} 该保持「键不存在」`,
    )
    assert.deepEqual(report, legacyShape)
  }

  // 部分坏条目被丢掉、剩下 ≥2 条有效 → 照常逐次画，坏条目不生成块。
  const partiallyBad = buildTaskLanes(
    {
      [STORE]: withOccurrences([
        occurrence(0.053, 1.06, 1.007, '等故障定界完成'),
        'junk',
        null,
        occurrence(1.07, 2.094, 1.024, '等解析完成'),
      ]),
    },
    storeRepeatedSpan,
    { nowMs },
  )
  assert.ok(partiallyBad)
  const waitBlocks = partiallyBad.lanes[0].segments.filter(
    (segment) => segment.stage === 'trace_store_wait',
  )
  assert.equal(waitBlocks.length, 2)
  assert.deepEqual(
    waitBlocks.map((segment) => [segment.startS, segment.endS, segment.detail]),
    [
      [0.053, 1.06, '等故障定界完成'],
      [1.07, 2.094, '等解析完成'],
    ],
  )

  // 一次登记里 offset 是 null（取不到时钟）：不炸，退回按 wall_s 顺次铺开并标位置未知。
  const nullOffsets = buildTaskLanes(
    {
      [STORE]: withOccurrences([
        { start_s: null, end_s: null, wall_s: 1.007, detail: '等故障定界完成' },
        { wall_s: 1.024, detail: '等解析完成' },
      ]),
    },
    storeRepeatedSpan,
    { nowMs },
  )
  assert.ok(nullOffsets)
  const lane = nullOffsets.lanes[0]
  assert.equal(lane.positionKnown, false)
  assert.equal(lane.note, '位置未知')
  assert.deepEqual(
    lane.segments
      .filter((segment) => segment.stage === 'trace_store_wait')
      .map((segment) => [segment.startS, segment.endS]),
    [
      [0, 1.007],
      [1.007, 2.031],
    ],
  )
})

