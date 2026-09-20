// 「解析用时」面板的真实渲染检查：直接从 App.vue 里切出面板那段模板，
// 用 @vue/compiler-dom 编译后 SSR 渲染成 HTML，再断言语义（泳道数、色块位置、
// 悬停文案、老接口回退）。这样模板本身也被测到，而不只是纯函数。
import assert from 'node:assert/strict'
import test from 'node:test'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { compile } from '@vue/compiler-dom'
import * as Vue from 'vue'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import {
  buildTaskLanes,
  buildTimelineTicks,
  collectTimelineLegend,
  formatParseTimingCores,
  formatParseTimingRows,
  formatParseTimingSeconds,
  formatParseTimingShare,
  formatTaskLaneSegmentTitle,
  parseTimingHeadlineSeconds,
  resolveParseTimingReport,
  parseTimingHeadlineLabel,
  taskLaneSegmentStyle,
  taskLaneSpanStyle,
  taskLaneTickStyle,
} from '../src/utils/parseTiming.ts'

const PARSE = 'kv_cache_log_parse_worker'
const DIAGNOSIS = 'kv_cache_log_event_diagnosis_worker'
const STORE = 'store_trace_context_logs_worker'
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

const APP_VUE = resolve(dirname(fileURLToPath(import.meta.url)), '../src/App.vue')
const PANEL_START =
  '<div v-if="getParseTimingReport(file) || hasTaskTimeline(file)" class="log-file-timing">'

/**
 * 找到 App.vue。测试可能被 esbuild 打包到别处再跑（既有跑法就是这样），
 * 那时 import.meta.url 指向产物目录，所以再按 cwd 兜两个位置。
 */
const readAppVue = () => {
  const candidates = [
    APP_VUE,
    resolve(process.cwd(), 'src/App.vue'),
    resolve(process.cwd(), 'src/web/src/App.vue'),
  ]
  for (const candidate of candidates) {
    if (existsSync(candidate)) return readFileSync(candidate, 'utf8')
  }
  throw new Error(`找不到 App.vue，试过：${candidates.join(' / ')}（请在 src/web 下运行）`)
}

/** 从 App.vue 源码里切出「解析用时」面板那一段（按 <div>/</div> 配平）。 */
const extractTimingPanel = (source) => {
  const start = source.indexOf(PANEL_START)
  assert.notEqual(start, -1, `App.vue 里找不到面板模板，测试需要同步更新：${PANEL_START}`)
  const tags = /<div[\s>]|<\/div>/g
  tags.lastIndex = start
  let depth = 0
  for (let match = tags.exec(source); match; match = tags.exec(source)) {
    depth += match[0] === '</div>' ? -1 : 1
    if (depth === 0) return source.slice(start, match.index + match[0].length)
  }
  throw new Error('「解析用时」面板的 <div> 没有配平')
}

const panelTemplate = extractTimingPanel(readAppVue())
// 面板模板不含 TS 语法（偏移量、占比都由 utils/parseTiming.ts 的纯函数算好），
// 所以直接编译成 render 函数即可，不需要再过一次 TS 去类型。
const { code } = compile(panelTemplate, { mode: 'function', prefixIdentifiers: true })
const panelRender = new Function('Vue', code)(Vue)
assert.equal(typeof panelRender, 'function', '面板模板编译失败')

/** 去掉 HTML 注释（模板注释会原样出现在 SSR 输出里），只断言真正渲染出来的东西。 */
const stripComments = (html) => html.replace(/<!--[\s\S]*?-->/g, '')

/** 用 fixture 渲染面板；只注入模板里真正用到的那些函数。 */
const renderPanel = async (file) =>
  stripComments(
    await renderToString(
      createSSRApp({
      render: panelRender,
      setup: () => ({
        file,
        getParseTimingReport: (target) => resolveParseTimingReport(target.parse_timing ?? null, []),
        getTaskTimeline: (target) => buildTaskLanes(target.stage_timings ?? null, target.task_spans ?? null),
        hasTaskTimeline: (target) => buildTaskLanes(target.stage_timings ?? null, target.task_spans ?? null) !== null,
        getTaskLanes: (target) => buildTaskLanes(target.stage_timings ?? null, target.task_spans ?? null)?.lanes ?? [],
        getTaskAxisTotalS: (target) =>
          buildTaskLanes(target.stage_timings ?? null, target.task_spans ?? null)?.totalS ?? 0,
        getTimelineLegend: (target) =>
          collectTimelineLegend(buildTaskLanes(target.stage_timings ?? null, target.task_spans ?? null)),
        getTaskEndToEndS: (target) =>
          buildTaskLanes(target.stage_timings ?? null, target.task_spans ?? null)?.endToEndS ?? null,
        isTaskTimelineRunning: (target) =>
          buildTaskLanes(target.stage_timings ?? null, target.task_spans ?? null)?.running ?? false,
        formatParseTimingSeconds,
        formatParseTimingShare,
        formatParseTimingCores,
        formatParseTimingRows,
        parseTimingHeadlineSeconds,
        parseTimingHeadlineLabel,
        taskLaneSegmentStyle,
        taskLaneSpanStyle,
        taskLaneTickStyle,
        buildTimelineTicks,
        formatTaskLaneSegmentTitle,
        getLogFileProgress: () => 100,
        getLogFileProgressMessage: () => '解析完成',
        }),
      }),
    ),
  )

test('面板渲染：三条泳道 + 端到端 + 悬停文案 + 阶段表收进 details', async () => {
  const html = await renderPanel({
    parse_timing: parseReport,
    stage_timings: { [PARSE]: parseReport, [DIAGNOSIS]: diagnosisReport, [STORE]: storeReport },
    task_spans: fullSpans,
  })

  // 主数就是端到端（不再另起一行，避免"2.8 s 下面又跟个 3.7 s"）。
  assert.match(html, /log-file-timing-total[^>]*>\s*20\.0 s/)
  assert.match(html, /端到端（三个任务）/)
  // 三条泳道，顺序固定。
  assert.equal((html.match(/log-file-timing-lane-track/g) ?? []).length, 3)
  const labels = [...html.matchAll(/log-file-timing-lane-label[^>]*>([^<]+)</g)].map((m) => m[1].trim())
  assert.deepEqual(labels, ['解析', '故障定界', '上下文落库'])
  // 色块真的落在共用时间轴的正确位置上（轴长 20s）：解析首段 0→2.3s，落库等待段 13.2→17.2s。
  assert.match(html, /style="left:0\.0000%;width:11\.5000%/)
  assert.match(html, /style="left:65\.0000%;width:2\.0000%/)
  assert.match(html, /style="left:66\.0000%;width:20\.0000%/)
  // 等待类阶段标浅灰 + 悬停文案（阶段名 / 用时 / 占比 / 核数 / detail）。
  assert.match(html, /log-file-timing-seg[^"]*is-waiting"[^>]*title="等待 · 用时 4\.0 s · 占比 20\.0% · —/)
  assert.match(
    html,
    /title="扫描 · 用时 2\.3 s · 占比 11\.5% · 7\.83 核 · 11 文件 \/ 1909790 行"/,
  )
  // 泳道右端**不放**每任务耗时（容易误读成"条长"）；总时间只在刻度尺右端，
  // 每个任务自己的耗时放在跨度条的悬停文案里。
  assert.equal((html.match(/log-file-timing-lane-total"[^>]*>\s*[\d.]+ s/g) ?? []).length, 0)
  // 「发虚的跨度条」已取消（它就是那个说不清的鬼影）；改成显式的「收尾」段。
  assert.equal((html.match(/log-file-timing-lane-span/g) ?? []).length, 0)
  assert.match(html, /log-file-timing-seg[^"]*is-tail/)
  assert.match(html, /收尾/)
  // 泳道图 + 阶段表都算「解析明细」：一并收进 details，**默认折叠**（没有 open 属性）。
  assert.match(html, /<details[^>]*class="log-file-timing-details"/)
  assert.doesNotMatch(html, /<details[^>]*\sopen(\s|>)/)
  assert.match(html, /<summary[^>]*>\s*任务时间线与解析阶段明细\s*<\/summary>/)
  // 解析泳道逐阶段不同色（色块类名）+ 图例
  for (const stage of ['scan', 'trace_frame', 'aggregate', 'detail', 'bucket', 'store']) {
    assert.match(html, new RegExp(`is-stage-${stage}`))
  }
  // 图例覆盖**三条泳道**出现过的每个阶段（解析 6 + 收尾 1 + 定界 3 + 落库 3）
  assert.equal((html.match(/log-file-timing-legend-dot/g) ?? []).length, 13)
  for (const label of ['扫描', '写库', '收尾', '定界工具', '等待', '写上下文']) {
    assert.ok(html.includes(`</span> ${label}`), `图例缺少 ${label}`)
  }
  assert.equal((html.match(/class="log-file-timing-stage"/g) ?? []).length, 6)
})

test('面板渲染：有 started_at 时头部出现「排队 / 启动」，并自动进图例', async () => {
  const html = await renderPanel({
    parse_timing: parseReport,
    stage_timings: { [PARSE]: parseReport },
    task_spans: [
      {
        task_type: PARSE,
        start: at(0),
        started_at: at(1.1),
        end: at(13.6),
        duration_s: 13.6,
      },
    ],
  })
  // 色块带 is-head，位置从泳道起点铺到 started_at（轴长 13.6s → 1.1s = 8.1%）。
  assert.match(html, /class="log-file-timing-seg[^"]*is-head"[^>]*style="left:0\.0000%;width:8\.0882%/)
  assert.match(html, /title="排队 \/ 启动 · 用时 1\.1 s · 占比 8\.1% · — · 等调度派发 \+ 起进程"/)
  // 扫描跟着右移到 1.1s 之后（改前是贴着左边 0 → 2.3s）。
  assert.match(html, /style="left:8\.0882%;width:16\.9118%/)
  // 图例是按泳道里出现过的阶段动态生成的 → 「排队 / 启动」自动进来，无需改模板。
  assert.match(html, /log-file-timing-legend-dot[^"]*is-stage-_head/)
  assert.ok(html.includes('</span> 排队 / 启动'), '图例缺少 排队 / 启动')
})

test('面板渲染：未完成任务画到「现在」并标进行中', async () => {
  const storeRunningReport = {
    task_type: STORE,
    total_s: 1.8,
    end_to_end_s: null,
    outside_s: null,
    rows: null,
    stages: [stage('trace_store_wait', '等待', 0, 1.2), stage('trace_store_collect', '取上下文', 1.2, 1.8)],
  }
  // buildTaskLanes 的「现在」跟随真实时钟：fixture 的 span 起点取真实 now - 1.8s，
  // 这样不依赖测试什么时候跑。
  const nowMs = Date.now()
  const html = await renderPanel({
    parse_timing: parseReport,
    stage_timings: { [PARSE]: parseReport, [STORE]: storeRunningReport },
    task_spans: [
      { task_type: PARSE, start: new Date(nowMs - 30_000).toISOString(), end: at(12.5), duration_s: 12.5 },
      { task_type: STORE, start: new Date(nowMs - 1800).toISOString(), end: null, duration_s: null },
    ],
  })
  // 主数按「现在」算：约 30 s，不可能是 12.5 s（那只算已完成的那条）。
  assert.match(html, /log-file-timing-total[^>]*>\s*30\.[01] s/)
  assert.equal((html.match(/log-file-timing-running">进行中</g) ?? []).length, 1)
  assert.equal((html.match(/log-file-timing-lane-track/g) ?? []).length, 2)
})

test('面板渲染：老接口（只有 parse_timing）退回原样，不白屏不报错', async () => {
  const html = await renderPanel({
    parse_timing: {
      total_s: 11.885,
      rows: 1909790,
      stages: [
        { stage: 'scan', label: '扫描', wall_s: 2.304, cpu_s: 18.05, cores: 7.83, detail: '11 文件' },
        { stage: 'store', label: '写库', wall_s: 1.2 },
      ],
    },
  })
  assert.match(html, /解析用时/)
  assert.doesNotMatch(html, /阶段合计/)
  // 副标题（阶段合计/其它）与「解析任务已完成」都已按评审删掉
  assert.doesNotMatch(html, /阶段合计/)
  assert.doesNotMatch(html, /解析任务已完成/)
  // 没有泳道、没有端到端一行，也没有 details 折叠壳（表格按原样直接渲染）。
  assert.equal((html.match(/log-file-timing-lane-track/g) ?? []).length, 0)
  assert.equal((html.match(/端到端/g) ?? []).length, 0)
  assert.doesNotMatch(html, /<details/)
  assert.match(html, /<div class="log-file-timing-details">/)
  // 原来那张分阶段表还在。
  assert.equal((html.match(/class="log-file-timing-stage"/g) ?? []).length, 2)
  assert.match(html, /扫描/)
  assert.match(html, /11\.9 s/)
})

test('面板渲染：没有任何用时数据时整块不渲染', async () => {
  const html = await renderPanel({})
  assert.doesNotMatch(html, /解析用时/)
  assert.doesNotMatch(html, /log-file-timing/)
})

// ---------------------------------------------------------------------------
// occurrences（契约新增键）：同一阶段登记多次 → 模板里逐次各渲染一块
// ---------------------------------------------------------------------------
const occurrence = (startS, endS, wallS, detail) => ({
  start_s: startS,
  end_s: endS,
  wall_s: wallS,
  detail,
})

const repeatedStoreReport = {
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

/** 取出某一阶段渲染出来的所有色块标签（属性顺序无关）。 */
const segmentTags = (html, stage) =>
  [...html.matchAll(new RegExp(`<span class="log-file-timing-seg[^"]*is-stage-${stage}[^"]*"[^>]*>`, 'g'))].map(
    (match) => match[0],
  )
const attrOf = (tag, name) => (tag.match(new RegExp(`${name}="([^"]*)"`)) ?? [])[1]

test('面板渲染：同一阶段登记多次 → 逐次各一块，位置/悬停各归各的登记', async () => {
  const html = await renderPanel({
    stage_timings: { [STORE]: repeatedStoreReport },
    task_spans: [{ task_type: STORE, start: at(0), end: at(2.7), duration_s: 2.7 }],
  })
  // 轴长 2.7s。等待段两块：0.053→1.060 与 1.070→2.094（旧画法是一块 0.053→2.094 的并集）。
  const wait = segmentTags(html, 'trace_store_wait')
  assert.equal(wait.length, 2, '两次登记该渲染两块')
  // （SSR 输出的 style 属性带结尾分号。）
  assert.deepEqual(
    wait.map((tag) => attrOf(tag, 'style')),
    ['left:1.9630%;width:37.2963%;', 'left:39.6296%;width:37.9259%;'],
  )
  // 同一阶段同色：两块都带 is-stage-trace_store_wait / is-waiting，没有多出第三种颜色。
  assert.equal(wait.every((tag) => tag.includes('is-stage-trace_store_wait')), true)
  assert.equal(wait.every((tag) => tag.includes('is-waiting')), true)
  // 悬停用各自那次登记的 detail。
  assert.match(attrOf(wait[0], 'title'), /等故障定界完成$/)
  assert.match(attrOf(wait[1], 'title'), /等解析完成$/)
  assert.doesNotMatch(attrOf(wait[0], 'title'), /等解析完成/)
  // 块之间不重叠：第一块右边界 1.9630+37.2963=39.2593% < 第二块左边界 39.6296%。
  assert.ok(1.963 + 37.2963 < 39.6296)
  // 不再压着写库：「等待」第一块的右边界落在「写上下文」第一块的左边（旧画法会盖住）。
  const write = segmentTags(html, 'trace_store_write')
  assert.equal(write.length, 2)
  assert.deepEqual(
    write.map((tag) => attrOf(tag, 'style')),
    ['left:39.4815%;width:7.4444%;', 'left:77.5556%;width:18.5185%;'],
  )
  assert.match(attrOf(write[1], 'title'), /时延异常 trace 2 条落库$/)
  const waitFirstRight = 1.963 + 37.2963
  const writeFirstLeft = 39.4815
  assert.ok(waitFirstRight < writeFirstLeft, '「等待」第一块不该压到「写上下文」上')
  // 取上下文也是两块（第二次登记的详情以前根本看不到）。
  assert.equal(segmentTags(html, 'trace_store_collect').length, 2)
  // 图例按出现过的阶段去重：4 个阶段（等待/取上下文/写上下文/收尾），不是 7 块。
  assert.equal((html.match(/log-file-timing-legend-dot/g) ?? []).length, 4)
})
