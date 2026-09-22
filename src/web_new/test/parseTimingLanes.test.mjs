import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildTaskLanes,
  collectTimelineLegend,
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

// 真实形状的 fixture：三个任务并行，解析 0 → 12.5s，诊断 13.0 → 15.6s，落库 13.2 → 20.0s。
const parseReport = {
  task_type: PARSE,
  total_s: 12.1,
  end_to_end_s: 12.5,
  rows: 1909790,
  stages: [
    stage('scan', '扫描', 0, 2.3, { cores: 7.83, cpu_s: 18.05, detail: '11 文件 / 1909790 行' }),
    stage('aggregate', '聚合', 5.0, 8.5),
    stage('store', '写库', 11.5, 12.1),
  ],
}

const diagnosisReport = {
  task_type: DIAGNOSIS,
  total_s: 2.2,
  end_to_end_s: 2.6,
  rows: null,
  stages: [
    stage('diagnose_prepare', '定界准备', 0, 0.4),
    stage('diagnose_tool', '定界工具', 0.4, 1.9),
  ],
}

const storeReport = {
  task_type: STORE,
  total_s: 6.4,
  end_to_end_s: 6.8,
  rows: null,
  stages: [
    stage('trace_store_wait', '等待', 0, 4.0),
    stage('trace_store_collect', '取上下文', 4.0, 5.2),
    stage('trace_store_write', '写上下文', 5.2, 6.4),
  ],
}

const fullSpans = [
  { task_type: PARSE, start: at(0), started_at: null, end: at(12.5), duration_s: 12.5 },
  { task_type: DIAGNOSIS, start: at(13.0), started_at: null, end: at(15.6), duration_s: 2.6 },
  { task_type: STORE, start: at(13.2), started_at: null, end: at(20.0), duration_s: 6.8 },
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
  assert.equal(segmentOf(laneOf(timeline, PARSE), 'scan').startS, 0)
  assert.equal(segmentOf(laneOf(timeline, PARSE), 'scan').endS, 2.3)
  assert.equal(segmentOf(laneOf(timeline, DIAGNOSIS), 'diagnose_prepare').startS, 13)
  assert.equal(segmentOf(laneOf(timeline, DIAGNOSIS), 'diagnose_tool').startS, 13.4)
  // 相邻任务之间的空隙保留（解析 12.5 结束 → 诊断 13.0 开始，正是在等）。
  assert.equal(laneOf(timeline, PARSE).endS, 12.5)
  assert.equal(laneOf(timeline, DIAGNOSIS).offsetS - laneOf(timeline, PARSE).endS, 0.5)
  // 端到端 = 最早 start → 最晚 end；泳道右端是各任务自己的总耗时。
  assert.equal(timeline.endToEndS, 20)
  assert.equal(timeline.totalS, 20)
  assert.equal(timeline.running, false)
  assert.equal(laneOf(timeline, PARSE).totalS, 12.5)
  assert.equal(laneOf(timeline, STORE).totalS, 6.8)
  // 位置可信时不加提示；等待类阶段标出来（界面画浅灰）。
  assert.equal(laneOf(timeline, PARSE).note, null)
  assert.equal(segmentOf(laneOf(timeline, STORE), 'trace_store_wait').waiting, true)
  assert.equal(segmentOf(laneOf(timeline, STORE), 'trace_store_collect').waiting, false)
})

test('① 归一化后仍保留 task_type 与阶段偏移', () => {
  const report = normalizeParseTimingReport(parseReport)
  assert.ok(report)
  assert.equal(report.task_type, PARSE)
  assert.equal(report.stages[0].start_s, 0)
  assert.equal(report.stages[0].end_s, 2.3)
})

test('② 只有解析一条：只渲染 1 条泳道，其余不出现', () => {
  const timeline = buildTaskLanes({ [PARSE]: parseReport }, [fullSpans[0]])
  assert.ok(timeline)
  assert.equal(timeline.lanes.length, 1)
  assert.equal(timeline.lanes[0].taskType, PARSE)
})

test('③ 老数据（无 start_s / 无 task_spans）：按 wall_s 顺序铺开并标注位置未知', () => {
  const legacyReport = {
    task_type: PARSE,
    total_s: 3,
    stages: [
      { stage: 'scan', label: '扫描', wall_s: 2, cpu_s: null, cores: null, detail: null },
      { stage: 'store', label: '写库', wall_s: 1, cpu_s: null, cores: null, detail: null },
    ],
  }
  const timeline = buildTaskLanes({ [PARSE]: legacyReport }, null)
  assert.ok(timeline)
  const lane = laneOf(timeline, PARSE)
  assert.equal(lane.positionKnown, false)
  assert.equal(lane.note, '位置未知')
  assert.deepEqual(
    lane.segments.map((segment) => [segment.stage, segment.startS, segment.endS]),
    [
      ['scan', 0, 2],
      ['store', 2, 3],
    ],
  )
  // 位置是假的，段自己也标出来（界面降透明度）。
  assert.equal(segmentOf(lane, 'scan').positionKnown, false)
  // 没有 span 时端到端退回时间轴总长。
  assert.equal(timeline.endToEndS, 3)
})

test('④ 未完成任务（end = null）：泳道画到「现在」并标进行中', () => {
  const timeline = buildTaskLanes(
    { [STORE]: storeReport },
    [{ task_type: STORE, start: at(0), started_at: null, end: null, duration_s: null }],
    { nowMs: T0 + 7000 },
  )
  assert.ok(timeline)
  const lane = laneOf(timeline, STORE)
  assert.equal(lane.running, true)
  // 阶段只画到 6.4s，任务画到「现在」7s（未完成时没有总耗时，只能按已铺开的最远处算）。
  assert.equal(lane.endS, 7)
  assert.equal(lane.totalS, 7)
  assert.equal(timeline.running, true)
})

test('⑤ span 缺 start（后端给 null）：不崩，泳道说明起点对齐不可用', () => {
  const timeline = buildTaskLanes({ [PARSE]: parseReport }, [
    { task_type: PARSE, start: null, started_at: null, end: at(10), duration_s: null },
  ])
  assert.ok(timeline)
  assert.equal(timeline.lanes.length, 1)
  assert.equal(laneOf(timeline, PARSE).note, '起点未知（span 缺 start）')
})

test('⑥ 有 started_at：色块以 started_at 为锚点右移，并画出「排队 / 启动」头部段', () => {
  const timeline = buildTaskLanes(
    { [PARSE]: parseReport },
    [{ task_type: PARSE, start: at(0), started_at: at(1.2), end: at(13.7), duration_s: 13.7 }],
    { nowMs: T0 + 60_000 },
  )
  assert.ok(timeline)
  const lane = laneOf(timeline, PARSE)
  assert.equal(lane.segments[0].stage, '_head')
  assert.equal(lane.segments[0].label, '排队 / 启动')
  assert.equal(lane.segments[0].head, true)
  assert.equal(lane.segments[0].startS, 0)
  assert.equal(lane.segments[0].endS, 1.2)
  // 阶段偏移的原点是 run() 起点（= started_at），所以扫描从 1.2 开始而不是 0。
  assert.equal(segmentOf(lane, 'scan').startS, 1.2)
  // 头部段是图例里的一种颜色，不能只有色块没有说明。
  assert.ok(collectTimelineLegend(timeline).some((item) => item.stage === '_head'))
})

test('⑦ 老数据（无 started_at / 键缺失 / 值为 null）：不出现头部段', () => {
  for (const startedAt of [undefined, null, 'oops']) {
    const timeline = buildTaskLanes({ [PARSE]: parseReport }, [
      { task_type: PARSE, start: at(0), started_at: startedAt, end: at(12.5), duration_s: 12.5 },
    ])
    assert.ok(timeline)
    const lane = laneOf(timeline, PARSE)
    assert.equal(
      lane.segments.some((segment) => segment.head),
      false,
    )
    assert.equal(segmentOf(lane, 'scan').startS, 0)
  }
})

test('⑧ started_at 早于 start（时钟回拨/字段乱序）：锚点夹在泳道起点，色块不跑到左边', () => {
  const timeline = buildTaskLanes({ [PARSE]: parseReport }, [
    { task_type: PARSE, start: at(0), started_at: at(-3), end: at(12.5), duration_s: 12.5 },
  ])
  assert.ok(timeline)
  const lane = laneOf(timeline, PARSE)
  assert.equal(
    lane.segments.some((segment) => segment.head),
    false,
  )
  assert.equal(segmentOf(lane, 'scan').startS, 0)
  assert.ok(lane.segments.every((segment) => segment.startS >= 0))
})

test('⑨ occurrences ≥2：同一阶段逐次各画一块，位置/悬停各归各的登记', () => {
  const report = {
    task_type: STORE,
    total_s: 8,
    end_to_end_s: 10,
    stages: [
      {
        stage: 'trace_store_wait',
        label: '等待',
        wall_s: 6,
        cpu_s: null,
        cores: null,
        detail: '合并跨度',
        start_s: 0,
        end_s: 8,
        occurrences: [
          { start_s: 0, end_s: 4, wall_s: 4, detail: '等定界' },
          { start_s: 6, end_s: 8, wall_s: 2, detail: '等解析' },
        ],
      },
      stage('trace_store_write', '写上下文', 4, 6),
    ],
  }
  const timeline = buildTaskLanes({ [STORE]: report }, [
    { task_type: STORE, start: at(0), started_at: null, end: at(10), duration_s: 10 },
  ])
  assert.ok(timeline)
  const waits = laneOf(timeline, STORE).segments.filter(
    (segment) => segment.stage === 'trace_store_wait',
  )
  assert.deepEqual(
    waits.map((segment) => [segment.startS, segment.endS, segment.durationS, segment.detail]),
    [
      [0, 4, 4, '等定界'],
      [6, 8, 2, '等解析'],
    ],
  )
  // 收尾段从「最后一块画完」算起，不能从阶段级并集（8）之外的位置起飞。
  const tail = laneOf(timeline, STORE).segments.find((segment) => segment.tail)
  assert.equal(tail?.startS, 8)
})

test('⑩ occurrences 是空数组 / 坏值：退回阶段级行为，不炸', () => {
  for (const occurrences of [[], [null, 'x'], [{}]]) {
    const timeline = buildTaskLanes(
      {
        [PARSE]: {
          task_type: PARSE,
          total_s: 3,
          stages: [
            {
              stage: 'scan',
              label: '扫描',
              wall_s: 2,
              cpu_s: null,
              cores: null,
              detail: '扫描 2s',
              start_s: 1,
              end_s: 3,
              occurrences,
            },
          ],
        },
      },
      null,
    )
    assert.ok(timeline)
    const segments = laneOf(timeline, PARSE).segments
    assert.equal(segments.length, 1)
    assert.equal(segments[0].startS, 1)
    assert.equal(segments[0].endS, 3)
    assert.equal(segments[0].detail, '扫描 2s')
  }
})

test('⑪ 色块定位与悬停文案', () => {
  const segment = {
    stage: 'scan',
    label: '扫描',
    startS: 1.2,
    endS: 3.504,
    durationS: 2.304,
    wallS: 2.304,
    cpuS: 18.05,
    cores: 7.83,
    detail: '11 文件 / 1909790 行',
    waiting: false,
    positionKnown: true,
  }
  const style = taskLaneSegmentStyle(segment, 11.885)
  assert.equal(style.left, '10.0968%')
  assert.ok(Math.abs(Number.parseFloat(style.width) - 19.3857) < 0.01)
  assert.equal(
    formatTaskLaneSegmentTitle(segment, 11.885),
    '扫描 · 用时 2.3 s · 占比 19.4% · 7.83 核 · 11 文件 / 1909790 行',
  )
  // 等待类阶段补「（等待）」；标签里已有「等待」就不重复。
  assert.equal(
    formatTaskLaneSegmentTitle({ ...segment, waiting: true, label: 'Trace' }, 10),
    'Trace（等待） · 用时 2.3 s · 占比 23.0% · 7.83 核 · 11 文件 / 1909790 行',
  )
  // 位置未知时悬停要说清楚，不能让人以为位置是真的。
  assert.ok(
    formatTaskLaneSegmentTitle({ ...segment, positionKnown: false }, 10).includes(
      '位置未知（按 wall_s 顺序铺开）',
    ),
  )
  // 退化输入不抛：总长 0 → 0 宽。
  assert.deepEqual(taskLaneSegmentStyle(segment, 0), { left: '0%', width: '0%' })
})
