import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildTimelineTicks,
  formatParseTimingCores,
  parseTimingHeadlineLabel,
  parseTimingHeadlineSeconds,
  taskLaneSpanStyle,
  taskLaneTickStyle,
  formatParseTimingRows,
  formatParseTimingSeconds,
  formatParseTimingShare,
  resolveParseTimingReport,
} from '../src/utils/parseTiming.ts'

// 后端冻结契约里的真实样例（[timing] 报告的单行 JSON，同时也是 file.parse_timing 的形状）。
const timingObject = {
  total_s: 11.885,
  rows: 1909790,
  stages: [
    {
      stage: 'scan',
      label: '扫描',
      wall_s: 2.304,
      cpu_s: 18.05,
      cores: 7.83,
      detail: '11 文件 / 1909790 行',
    },
    { stage: 'store', label: '写库', wall_s: 1.2, cpu_s: null, cores: null, detail: '1909790 行' },
  ],
}
const timingMessage = `[timing] ${JSON.stringify(timingObject)}`

test('主来源 file.parse_timing：解析出总时长与分阶段明细', () => {
  const report = resolveParseTimingReport(timingObject, [])
  assert.ok(report)
  assert.equal(report.total_s, 11.885)
  assert.equal(report.rows, 1909790)
  assert.equal(report.stages.length, 2)
  assert.deepEqual(report.stages[0], {
    stage: 'scan',
    label: '扫描',
    wall_s: 2.304,
    cpu_s: 18.05,
    cores: 7.83,
    detail: '11 文件 / 1909790 行',
  })
  // 后端不给 cpu_s / cores 时保持 null（界面显示 —）。
  assert.equal(report.stages[1].cores, null)
  assert.equal(report.stages[1].cpu_s, null)
})

test('主来源为空时兜底：[timing] 报告取最新一条', () => {
  const candidates = [
    { message: 'Log parse completed', time: 3000 },
    { message: '[timing] {"total_s":1.0,"rows":10,"stages":[]}', time: 1000 },
    { message: timingMessage, time: 2000 },
    { message: '[polars][scan] progress=10%', time: 4000 },
  ]
  for (const [fromFile, expectedTotal] of [
    [null, 11.885],
    [undefined, 11.885],
  ]) {
    const report = resolveParseTimingReport(fromFile, candidates)
    assert.ok(report)
    assert.equal(report.total_s, expectedTotal)
    assert.equal(report.stages[0].label, '扫描')
  }
  // 时间戳决定“最新”：把旧报告的时间调到最后，则应取旧的。
  const olderWins = resolveParseTimingReport(null, [
    { message: timingMessage, time: 2000 },
    { message: '[timing] {"total_s":1.0,"rows":10,"stages":[]}', time: 9000 },
  ])
  assert.equal(olderWins?.total_s, 1.0)
})

test('两条来源都没有该报告 → null（整块不渲染）', () => {
  assert.equal(resolveParseTimingReport(null, []), null)
  assert.equal(resolveParseTimingReport(undefined, []), null)
  assert.equal(
    resolveParseTimingReport(null, [
      { message: 'Task running', time: 1000 },
      { message: '[perf] {"x":1}', time: 2000 },
      { message: null, time: 3000 },
      { message: '[polars][scan] progress=10%', time: 4000 },
    ]),
    null,
  )
})

test('JSON 损坏或形状不对 → null，不抛出', () => {
  assert.equal(resolveParseTimingReport(null, [{ message: '[timing] {oops', time: 1 }]), null)
  assert.equal(resolveParseTimingReport(null, [{ message: '[timing] 123', time: 1 }]), null)
  assert.equal(resolveParseTimingReport(null, [{ message: '[timing] null', time: 1 }]), null)
  // 缺 total_s / total_s 非正数 → 不给界面留下空壳。
  assert.equal(resolveParseTimingReport({ rows: 5 }, []), null)
  assert.equal(resolveParseTimingReport({ total_s: 0, stages: [] }, []), null)
  assert.equal(resolveParseTimingReport({ total_s: 'abc' }, []), null)
  assert.equal(resolveParseTimingReport('not-an-object', []), null)
  // stages 缺省 / 非法条目：整体仍然可用，只丢弃坏条目。
  const partial = resolveParseTimingReport({ total_s: 3, stages: [null, { label: '无 stage' }] }, [])
  assert.ok(partial)
  assert.deepEqual(partial.stages, [])
})

test('展示文案：总时长、占比、核数、行数', () => {
  const report = resolveParseTimingReport(timingObject, [])
  assert.ok(report)
  assert.equal(formatParseTimingSeconds(report.total_s), '11.9 s')
  assert.equal(formatParseTimingSeconds(report.stages[0].wall_s), '2.3 s')
  assert.equal(formatParseTimingShare(report.stages[0].wall_s, report.total_s), '19.4%')
  assert.equal(formatParseTimingShare(report.stages[1].wall_s, report.total_s), '10.1%')
  assert.equal(formatParseTimingCores(report.stages[0].cores), '7.83 核')
  assert.equal(formatParseTimingCores(report.stages[1].cores), '—')
  assert.equal(formatParseTimingSeconds(null), '—')
  assert.equal(formatParseTimingShare(null, 10), '—')
  assert.equal(formatParseTimingRows(report.rows), '1,909,790 行')
  assert.equal(formatParseTimingRows(null), '')
})

test('占比重演后端样例口径：各阶段占比之和不超过 100%', () => {
  const report = resolveParseTimingReport(timingObject, [])
  assert.ok(report)
  const sum = report.stages.reduce(
    (acc, stage) => acc + Number(formatParseTimingShare(stage.wall_s, report.total_s).replace('%', '')),
    0,
  )
  assert.ok(sum > 0 && sum <= 100.1, `stages share sum = ${sum}`)
})

// 端到端字段：面板主时长是"任务总计"，阶段之和只是明细。
const withEndToEnd = { ...timingObject, end_to_end_s: 16.4, outside_s: 4.515 }




test('泳道跨度条：任务自己的起止（不铺满整行），右边留白=该任务已结束', () => {
  assert.deepEqual(taskLaneSpanStyle({ offsetS: 0, endS: 2.8 }, 3.7), {
    left: '0.0000%',
    width: '75.6757%',
  })
  assert.deepEqual(taskLaneSpanStyle({ offsetS: 2.0, endS: 3.7 }, 3.7), {
    left: '54.0541%',
    width: '45.9459%',
  })
  // 退化输入不抛：总长 0 → 0 宽
  assert.deepEqual(taskLaneSpanStyle({ offsetS: 0, endS: 1 }, 0), { left: '0%', width: '0%' })
})

test('时间轴刻度：0/¼/½/¾/总长，最后一条落在 100%', () => {
  assert.deepEqual(buildTimelineTicks(3.7), [0, 0.9, 1.9, 2.8, 3.7])
  assert.deepEqual(buildTimelineTicks(0), [])
  assert.deepEqual(taskLaneTickStyle(1.85, 3.7), { left: '50.0000%' })
  assert.deepEqual(taskLaneTickStyle(9, 3.7), { left: '100.0000%' })
})

test('主数口径：有泳道用端到端，无泳道退回解析任务；标签同步', () => {
  const report = resolveParseTimingReport({ ...timingObject, end_to_end_s: 12.5 }, [])
  assert.ok(report)
  assert.equal(parseTimingHeadlineSeconds(report, null), 12.5)
  assert.equal(parseTimingHeadlineLabel(null), '解析任务')
  const timeline = { lanes: [], totalS: 20, endToEndS: 20, running: false }
  assert.equal(parseTimingHeadlineSeconds(report, timeline), 20)
  assert.equal(parseTimingHeadlineLabel(timeline), '端到端（三个任务）')
})
