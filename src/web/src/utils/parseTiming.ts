// 解析用时（总时长 + 分阶段明细）的类型与纯逻辑。
// 两个来源共用同一份规范化代码：
//   1. 日志列表接口里的 `file.parse_timing`（后端直接给出对象）；
//   2. 解析任务自身在 `task_reports` 里留下的 `[timing] {json}` 单行报告（兜底）。
// 任何一个字段不可用时返回 null，调用方据此整块不渲染。

/**
 * 同一个阶段被登记多次时的**一次登记**（冻结契约 `stages[].occurrences[]` 的元素）。
 * 落库任务的三段各走两遍（第一轮等定界、第二轮等解析），阶段级的 `start_s/end_s`
 * 只是两次的并集，画出来会重叠、悬停也只剩第一轮的说明 —— 靠这个数组逐次画。
 */
export interface ParseTimingOccurrence {
  /** 这一次登记相对**本任务 run() 起点**的偏移（秒）；取不到时钟时整个键不写。 */
  start_s?: number | null
  /** 这一次登记的结束偏移（秒），语义同 `start_s`。 */
  end_s?: number | null
  /** 这一次登记的墙钟耗时（秒）。 */
  wall_s: number | null
  /** 这一次登记的说明；后端没写时为 null。 */
  detail: string | null
}

export interface ParseTimingStage {
  stage: string
  label: string
  /** 该阶段墙钟耗时（秒）；字段缺失时为 null。 */
  wall_s: number | null
  /** 该阶段 CPU 时间（秒）；后端可能不提供。 */
  cpu_s: number | null
  /** 平均占用核数；后端可能不提供。 */
  cores: number | null
  detail: string | null
  /**
   * 该阶段相对**本任务 run() 起点**的偏移（秒）；老报告没有这两个字段，
   * 归一化时整个键就不写进来（`undefined` = 位置未知）。
   */
  start_s?: number | null
  /** 阶段结束偏移（秒），语义同 `start_s`。 */
  end_s?: number | null
  /**
   * 该阶段**每一次登记**的记录（按登记先后）。只登记一次 → 长度 1；老报告没有这个键
   * （归一化时整个键不写，消费方据此原样回退）。一个有效条目都没有时同样不写。
   */
  occurrences?: ParseTimingOccurrence[]
}

export interface ParseTimingReport {
  /** 这条报告属于哪个任务（`kv_cache_log_parse_worker` 等）；老报告没有 → null。 */
  task_type?: string | null
  /** 六个阶段的墙钟之和（秒）——注意它不是任务端到端耗时。 */
  total_s: number
  /** 任务端到端耗时（秒）：run() 起点 → 报告发出，含预处理/调度/收尾；老报告没有这个字段时为 null。 */
  end_to_end_s: number | null
  /** 端到端 − 阶段之和 = 预处理/调度/配置读取/收尾那部分（秒）；缺省为 null。 */
  outside_s: number | null
  /** 解析行数；缺省为 null。 */
  rows: number | null
  stages: ParseTimingStage[]
}

/** `[timing] {...}` 报告的消息前缀。 */
export const PARSE_TIMING_MESSAGE_PREFIX = '[timing]'

const toTimingNumber = (value: unknown): number | null => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

/**
 * 归一化一次登记；不是对象、或四个字段一个都没给出（`{}`、`['x']` 这类坏条目）→ null，
 * 调用方据此把这个条目丢掉，当它没登记过。
 */
const normalizeParseTimingOccurrence = (raw: unknown): ParseTimingOccurrence | null => {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const record = raw as Record<string, unknown>
  const startS = toTimingNumber(record.start_s)
  const endS = toTimingNumber(record.end_s)
  const wallS = toTimingNumber(record.wall_s)
  const detail = typeof record.detail === 'string' ? record.detail : null
  if (startS === null && endS === null && wallS === null && detail === null) return null
  return {
    // 与阶段级同口径：后端没给偏移就保持「键不存在」= 该次位置未知。
    ...(startS === null ? {} : { start_s: startS }),
    ...(endS === null ? {} : { end_s: endS }),
    wall_s: wallS,
    detail,
  }
}

const normalizeParseTimingStage = (raw: unknown): ParseTimingStage | null => {
  if (!raw || typeof raw !== 'object') return null
  const record = raw as Record<string, unknown>
  const stage = typeof record.stage === 'string' && record.stage ? record.stage : null
  if (!stage) return null
  const startS = toTimingNumber(record.start_s)
  const endS = toTimingNumber(record.end_s)
  // 逐次登记：坏条目直接丢；一条有效记录都没有（空数组 / 键只给了垃圾）= 键不写出，
  // 消费方就走老路径，与「后端没给这个键」逐字段一致。
  const occurrences = (Array.isArray(record.occurrences) ? record.occurrences : [])
    .map((entry) => normalizeParseTimingOccurrence(entry))
    .filter((entry): entry is ParseTimingOccurrence => entry !== null)
  return {
    stage,
    label: typeof record.label === 'string' && record.label ? record.label : stage,
    wall_s: toTimingNumber(record.wall_s),
    cpu_s: toTimingNumber(record.cpu_s),
    cores: toTimingNumber(record.cores),
    detail: typeof record.detail === 'string' ? record.detail : null,
    // 只有在后端真的给了偏移时才写这两个键：老报告保持「键不存在」= 位置未知。
    ...(startS === null ? {} : { start_s: startS }),
    ...(endS === null ? {} : { end_s: endS }),
    ...(occurrences.length === 0 ? {} : { occurrences }),
  }
}

/**
 * 规范化任意来源的解析用时对象；形状不对（非对象、缺 total_s、total_s <= 0）时返回 null。
 */
export const normalizeParseTimingReport = (raw: unknown): ParseTimingReport | null => {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const record = raw as Record<string, unknown>
  const totalS = toTimingNumber(record.total_s)
  if (totalS === null || totalS <= 0) return null
  const stages = Array.isArray(record.stages)
    ? record.stages
        .map((entry) => normalizeParseTimingStage(entry))
        .filter((stage): stage is ParseTimingStage => stage !== null)
    : []
  const endToEnd = toTimingNumber(record.end_to_end_s)
  let outside = toTimingNumber(record.outside_s)
  if (outside === null && endToEnd !== null) {
    outside = Math.max(0, Number((endToEnd - totalS).toFixed(3)))
  }
  const report: ParseTimingReport = {
    total_s: totalS,
    end_to_end_s: endToEnd,
    outside_s: outside,
    rows: toTimingNumber(record.rows),
    stages,
  }
  if (typeof record.task_type === 'string' && record.task_type) {
    report.task_type = record.task_type
  }
  return report
}

/**
 * 解析 `[timing] {json}` 报告消息；前缀不符、JSON 损坏或形状不对时返回 null（不抛出）。
 */
export const parseTimingReportFromMessage = (message: unknown): ParseTimingReport | null => {
  if (typeof message !== 'string') return null
  const trimmed = message.trim()
  if (!trimmed.startsWith(PARSE_TIMING_MESSAGE_PREFIX)) return null
  try {
    return normalizeParseTimingReport(
      JSON.parse(trimmed.slice(PARSE_TIMING_MESSAGE_PREFIX.length)) as unknown,
    )
  } catch {
    return null
  }
}

/** 兜底来源：任务报告里的原始 message 及其时间戳（毫秒 epoch，用于挑最新一条）。 */
export interface ParseTimingReportCandidate {
  message?: string | null
  time: number
}

/**
 * 决定日志卡片要展示的解析用时。
 * @param fromFile  `file.parse_timing`（主来源）
 * @param candidates 当前可见任务的报告（兜底来源）
 * @returns 规范化后的报告；两条来源都拿不到、或 JSON 损坏/形状不对 → null（界面整块不渲染）。
 */
export const resolveParseTimingReport = (
  fromFile: unknown,
  candidates: readonly ParseTimingReportCandidate[],
): ParseTimingReport | null => {
  const primary = normalizeParseTimingReport(fromFile)
  if (primary) return primary

  const timingCandidates = candidates.filter((candidate) =>
    (candidate.message ?? '').trim().startsWith(PARSE_TIMING_MESSAGE_PREFIX),
  )
  if (timingCandidates.length === 0) return null

  const latest =
    [...timingCandidates].sort((first, second) => second.time - first.time)[0] ?? null
  return latest ? parseTimingReportFromMessage(latest.message) : null
}

/** 秒 → `11.9 s`；缺值 → `—`。 */
export const formatParseTimingSeconds = (value: number | null): string =>
  value === null ? '—' : `${value.toFixed(1)} s`

/**
 * 面板主标题的时长：**有泳道（三任务）时用端到端，否则退回解析任务自己的时长**。
 * 主数只有一个口径，避免"2.8 s 下面又跟个 3.7 s"这种打架。
 */
export const parseTimingHeadlineSeconds = (
  report: ParseTimingReport | null,
  timeline?: TaskTimeline | null,
): number | null => {
  if (timeline && Number.isFinite(timeline.endToEndS) && timeline.endToEndS > 0) {
    return timeline.endToEndS
  }
  return report === null ? null : (report.end_to_end_s ?? report.total_s)
}

/**
 * 主标题右侧的口径标签：有泳道 → `端到端（三个任务）`，否则 `解析任务`。
 */
export const parseTimingHeadlineLabel = (timeline?: TaskTimeline | null): string =>
  timeline && Number.isFinite(timeline.endToEndS) && timeline.endToEndS > 0
    ? '端到端（三个任务）'
    : '解析任务'

/** 占比 = 阶段墙钟 / 总时长；缺值 → `—`。 */
export const formatParseTimingShare = (wallS: number | null, totalS: number): string => {
  if (wallS === null || !Number.isFinite(totalS) || totalS <= 0) return '—'
  return `${((wallS / totalS) * 100).toFixed(1)}%`
}

/** 核数；后端不提供时 → `—`。 */
export const formatParseTimingCores = (cores: number | null): string =>
  cores === null ? '—' : `${cores.toFixed(2)} 核`

/** 行数，用于表头副标题；缺值 → 空串（调用方据此隐藏）。 */
export const formatParseTimingRows = (rows: number | null): string =>
  rows === null ? '' : `${rows.toLocaleString('en-US')} 行`

// ---------------------------------------------------------------------------
// 三条并行泳道：解析 / 故障定界 / 上下文落库
//
// 数据来源是 `/log_file/list` 上每个 log_file 的两个新字段：
//   stage_timings: { task_type → 该任务最新一条 [timing] 报告 }
//   task_spans:    [{ task_type, start, started_at, end, duration_s }]（同一批任务各自的起止）
//
// **两个时间原点（这次改动的根因，别删）**
//   ① 泳道起点：`task_spans[].start` = 任务板上的注册时刻（"Task initialized"）；
//   ② 阶段偏移的原点：`task_spans[].started_at` = worker 真正进 `run()` 的时刻。
//   报告里的 `start_s/end_s` 是相对 ② 量的，而色块以前是画在 `① + start_s` 上：
//   两个原点混用，于是 ①→② 那段（等调度派发 + 起进程冷启动，实测 1.0~1.9 s）
//   被挤到了泳道右边，长得像一段灰色的「收尾」块 —— 可它物理上发生在扫描**之前**。
//   现在色块的锚点改成 `started_at ?? start`（老报告没有 started_at 就退回 ①，
//   行为与改动前完全一致），并把 [①, ②] 这段单独画成一个「排队 / 启动」头部段。
//
// 老数据（没有 span、阶段也没有偏移）只能按 wall_s 从任务起点顺序铺开，
// 位置是假的 —— 这种情况会被标成「位置未知」，而不是假装对齐。
// ---------------------------------------------------------------------------

/** 解析任务（scan/trace_frame/aggregate/detail/bucket/store 六段）。 */
export const TASK_TYPE_PARSE = 'kv_cache_log_parse_worker'
/** 故障定界任务（diagnose_prepare/diagnose_tool/diagnose_persist）。 */
export const TASK_TYPE_DIAGNOSIS = 'kv_cache_log_event_diagnosis_worker'
/** 上下文落库任务（trace_store_wait/trace_store_collect/trace_store_write）。 */
export const TASK_TYPE_STORE = 'store_trace_context_logs_worker'

/** 泳道的固定顺序：解析在最上，和「谁是大头」的阅读顺序一致。 */
export const TASK_LANE_ORDER: readonly string[] = [
  TASK_TYPE_PARSE,
  TASK_TYPE_DIAGNOSIS,
  TASK_TYPE_STORE,
]

const TASK_LANE_LABELS: Record<string, string> = {
  [TASK_TYPE_PARSE]: '解析',
  [TASK_TYPE_DIAGNOSIS]: '故障定界',
  [TASK_TYPE_STORE]: '上下文落库',
}

/** 等待类阶段：本任务这一段时间没干活（等别的任务/等锁/等 IO），画成浅灰。 */
const TASK_WAITING_STAGES = new Set(['trace_store_wait'])

/** 后端 `/log_file/list` 里 `task_spans[]` 的形状（冻结契约）。 */
export interface TaskSpan {
  task_type: string
  /** 任务的绝对起点 = 任务注册时刻（"Task initialized"）；取不到报告时间时后端给 null。 */
  start: string | null
  /**
   * worker 真正进 `run()` 的墙钟时刻，也就是 `start_s/end_s` 这两个偏移的原点。
   * `started_at - start` 就是「等调度派发 + 起进程」那段（画成「排队 / 启动」段）。
   * 老报告没有这个键 → null，此时退回用 `start` 当锚点（与改动前行为一致）。
   */
  started_at: string | null
  /** 未完成时为 null —— 泳道按「画到现在」处理并标进行中。 */
  end: string | null
  duration_s: number | null
}

/** 泳道里的一段色块。时间单位一律是「本时间轴上的秒」，不是日期。 */
export interface TaskLaneSegment {
  stage: string
  label: string
  /** 相对时间轴原点的起止（秒）。 */
  startS: number
  endS: number
  /** 画出来的宽度（秒）：优先用 start_s/end_s 之差，老数据等于 wall_s。 */
  durationS: number
  wallS: number | null
  cpuS: number | null
  cores: number | null
  detail: string | null
  /** 等待类阶段（见 TASK_WAITING_STAGES）。 */
  waiting: boolean
  /** false = 后端没给偏移，位置是按 wall_s 顺序铺出来的（假的）。 */
  positionKnown: boolean
  /** true = 不是后端打点的阶段，而是"最后一段活干完 → 任务被标记完成"的收尾段
   *  （状态更新 / 下一次调度 tick）。以前它画成低透明度的跨度条尾巴，像鬼影；
   *  现在亮明身份单独成段。 */
  tail?: boolean
  /** true = 不是后端打点的阶段，而是泳道起点 → 阶段偏移原点之间的「排队 / 启动」段
   *  （任务注册到 worker 真正进 run()：等调度派发 + 起进程冷启动）。
   *  它和 `tail` 一样属于"非后端阶段"的补充段，只是位置在头部而不是尾部：
   *  阶段偏移的原点是 run() 起点，跟泳道起点差了这一截，不画出来就会被误读成
   *  "任务一开始就在扫描"，或者反过来在泳道右边多出一段看着像收尾的灰块。 */
  head?: boolean
}

/** 一条泳道 = 一个任务在共用时间轴上的工作分布。 */
export interface TaskLane {
  taskType: string
  label: string
  segments: TaskLaneSegment[]
  /** 相对时间轴原点的起点（秒）。 */
  offsetS: number
  /** 相对时间轴原点的终点（秒）——进行中的任务画到「现在」。 */
  endS: number
  /** 该任务总耗时（秒）：span.duration_s → 报告端到端 → 实际铺开的宽度。 */
  totalS: number
  /** 未完成（span.end === null）。 */
  running: boolean
  /** 泳道内是否所有阶段位置都可信。 */
  positionKnown: boolean
  /** 泳道旁的提示（「位置未知」等），没有则为 null。 */
  note: string | null
}

export interface TaskTimeline {
  lanes: TaskLane[]
  /** 时间轴总长（秒）。 */
  totalS: number
  /** 端到端墙钟：所有 span 最早 start → 最晚 end（未完成时到「现在」）。 */
  endToEndS: number
  /** 是否有任务还在跑。 */
  running: boolean
}

/** 三位小数，避免浮点尾巴（0.2 + 13.0 = 13.399999999999999）。 */
const roundSeconds = (value: number): number => Number(value.toFixed(3))

/** `2026-09-15T10:00:00Z` / `2026-09-15 10:00:00` → 毫秒 epoch；认不出来 → null。 */
const parseTimingInstant = (value: unknown): number | null => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value !== 'string' || value.trim() === '') return null
  const raw = value.trim()
  const direct = Date.parse(raw)
  if (!Number.isNaN(direct)) return direct
  const isoish = Date.parse(raw.replace(' ', 'T'))
  return Number.isNaN(isoish) ? null : isoish
}

/** 泳道里要画一次的输入：一次登记（或老路径下的整个阶段）。 */
interface LaneEntry {
  offsetStartS: number | null
  offsetEndS: number | null
  wallS: number | null
  detail: string | null
}

/**
 * 一个阶段要画几块：`occurrences` 里有 ≥2 次有效登记 → 每次一块（同一阶段同色，位置
 * 各按该次的偏移）；其余情况（没有这个键 / 长度 1 / 全是坏条目）→ 一块，字段仍取
 * 阶段级的那套，与改动前逐字段一致。
 */
const stageLaneEntries = (stage: ParseTimingStage): LaneEntry[] => {
  const occurrences = stage.occurrences
  if (occurrences && occurrences.length >= 2) {
    return occurrences.map((occurrence) => ({
      offsetStartS: occurrence.start_s ?? null,
      offsetEndS: occurrence.end_s ?? null,
      wallS: occurrence.wall_s,
      detail: occurrence.detail,
    }))
  }
  return [
    {
      offsetStartS: stage.start_s ?? null,
      offsetEndS: stage.end_s ?? null,
      wallS: stage.wall_s,
      detail: stage.detail,
    },
  ]
}

/**
 * 按 report.stages 铺出泳道里的色块；没有偏移的按 wall_s 从泳道起点顺序铺。
 * 同一阶段登记多次时逐次各铺一块（块的位置就是各次的真实偏移，不会重叠）。
 *
 * @param laneStartS **阶段偏移的原点**在时间轴上的秒数，也就是 `started_at` 的位置
 *   （不是泳道起点 `start`）。老报告没有 `started_at` 时调用方传的就是泳道起点，
 *   与改动前的行为一致。
 */
const buildLaneSegments = (
  report: ParseTimingReport | null,
  laneStartS: number,
): { segments: TaskLaneSegment[]; positionKnown: boolean } => {
  const segments: TaskLaneSegment[] = []
  let cursorS = laneStartS
  let positionKnown = true

  for (const stage of report?.stages ?? []) {
    const entries = stageLaneEntries(stage)
    // 拆成多次登记时，「用时」按该次自己的墙钟报（契约：悬停用该次的 wall_s/detail）；
    // 没拆（老报告 / 只登记一次）时照旧用两端之差 —— 逐字段与改动前一致。
    const split = entries.length > 1

    for (const entry of entries) {
      const wallS = entry.wallS
      const offsetStartS = entry.offsetStartS
      const offsetEndS = entry.offsetEndS
      let startS: number
      let endS: number

      if (offsetStartS === null) {
        // 老报告：没有偏移，只能按 wall_s 顺序铺开（位置是假的）。
        positionKnown = false
        startS = cursorS
        endS = startS + Math.max(0, wallS ?? 0)
        cursorS = endS
      } else {
        startS = laneStartS + offsetStartS
        if (offsetEndS !== null && offsetEndS >= offsetStartS) endS = laneStartS + offsetEndS
        else if (wallS !== null && wallS > 0) endS = startS + wallS
        else endS = startS
        cursorS = Math.max(cursorS, endS)
      }
      if (endS < startS) endS = startS

      segments.push({
        stage: stage.stage,
        label: stage.label,
        startS: roundSeconds(startS),
        endS: roundSeconds(endS),
        durationS: split && wallS !== null ? roundSeconds(wallS) : roundSeconds(endS - startS),
        wallS,
        cpuS: stage.cpu_s,
        cores: stage.cores,
        detail: entry.detail,
        waiting: TASK_WAITING_STAGES.has(stage.stage),
        positionKnown: offsetStartS !== null,
      })
    }
  }

  return { segments, positionKnown }
}

/**
 * 把 `stage_timings` + `task_spans` 合成共用时间轴上的三条泳道。
 *
 * - 时间轴原点 = 所有 `task_spans[].start` 里最早的那个；三个任务各自的阶段偏移
 *   （相对自己 run() 起点 = `started_at`）加上 `started_at` 在轴上的位置，就落在一起了。
 *   `started_at` 缺失（老报告）时退回用 `start` 当偏移原点 —— 与改动前完全一致。
 * - 泳道起点到 `started_at` 之间的空档（等调度 / 起进程）会单独画成「排队 / 启动」段。
 * - 没有 spans 时退回各泳道自己的阶段偏移（原点按 0 算），泳道旁标注起点不可对齐。
 * - 两个字段都没有（老接口）→ 返回 null，调用方退回原来的「只有一张阶段表」。
 * - 不修改入参；认不出的条目直接丢掉，不抛异常。
 */
export const buildTaskLanes = (
  stageTimings: Record<string, ParseTimingReport> | null | undefined,
  taskSpans: readonly TaskSpan[] | null | undefined,
  options: { nowMs?: number } = {},
): TaskTimeline | null => {
  const nowMs = options.nowMs ?? Date.now()

  const reports = new Map<string, ParseTimingReport>()
  if (stageTimings && typeof stageTimings === 'object') {
    for (const [key, raw] of Object.entries(stageTimings)) {
      const report = normalizeParseTimingReport(raw)
      if (!report) continue
      const taskType = report.task_type ?? key
      if (taskType) reports.set(taskType, report)
    }
  }

  const spans: Array<{
    taskType: string
    startMs: number
    /** worker 进 run() 的墙钟毫秒（阶段偏移的原点）；老报告没有这个键 → null。 */
    startedAtMs: number | null
    endMs: number | null
    durationS: number | null
  }> = []
  const rawSpanCount = Array.isArray(taskSpans) ? taskSpans.length : 0
  if (Array.isArray(taskSpans)) {
    for (const raw of taskSpans) {
      if (!raw || typeof raw !== 'object') continue
      const taskType = typeof raw.task_type === 'string' ? raw.task_type : ''
      const startMs = parseTimingInstant(raw.start)
      if (!taskType || startMs === null) continue
      spans.push({
        taskType,
        startMs,
        // 老报告没有 started_at（或值解析不出来）→ null，这时锚点退回 start。
        startedAtMs: parseTimingInstant(raw.started_at),
        endMs: parseTimingInstant(raw.end),
        durationS: toTimingNumber(raw.duration_s),
      })
    }
  }
  // 后端给了 spans 但一个 start 都用不了（start=null）→ 时间轴没法真对齐，要说清楚。
  const noUsableSpan = rawSpanCount > 0 && spans.length === 0

  const originMs = spans.length === 0 ? null : Math.min(...spans.map((span) => span.startMs))
  let latestEndMs = originMs
  for (const span of spans) {
    const endMs = span.endMs ?? nowMs
    if (latestEndMs === null || endMs > latestEndMs) latestEndMs = endMs
  }

  const extraTypes = [...reports.keys(), ...spans.map((span) => span.taskType)].filter(
    (taskType) => !TASK_LANE_ORDER.includes(taskType),
  )
  const taskTypes = [...TASK_LANE_ORDER, ...new Set(extraTypes)]

  const lanes: TaskLane[] = []
  for (const taskType of taskTypes) {
    const report = reports.get(taskType) ?? null
    const span = spans.find((entry) => entry.taskType === taskType) ?? null
    if (!report && !span) continue

    const offsetS = span !== null && originMs !== null ? Math.max(0, (span.startMs - originMs) / 1000) : 0
    const running = span !== null && span.endMs === null
    // 阶段偏移的原点 = worker 进 run() 的时刻（started_at）在时间轴上的秒数。
    // 老报告没有 started_at → 退回泳道起点 offsetS，与改动前一致；
    // 时钟回拨/字段乱序让 started_at 早于 start 时夹到泳道起点，色块不会跑到泳道左边。
    const anchorS =
      span !== null && originMs !== null && span.startedAtMs !== null
        ? Math.max(offsetS, (span.startedAtMs - originMs) / 1000)
        : offsetS
    const { segments, positionKnown } = buildLaneSegments(report, anchorS)
    // 后端打点的阶段铺完的末尾；「收尾」段从这里算起，所以要在插入头部段之前取。
    const lastStageEndS = segments.reduce((acc, segment) => Math.max(acc, segment.endS), anchorS)

    // 头部段：泳道起点（任务注册）→ 锚点（worker 进 run()）。
    // 这里装着「等调度派发 + 起进程冷启动」，物理上在扫描之前，所以画在最左边而不是
    // 挤到泳道右边冒充收尾。阈值与「收尾」段一致（0.05 s 以内不值得画）。
    const headDurationS = anchorS - offsetS
    if (headDurationS > 0.05) {
      segments.unshift({
        stage: '_head',
        label: '排队 / 启动',
        startS: roundSeconds(offsetS),
        endS: roundSeconds(anchorS),
        durationS: roundSeconds(headDurationS),
        // 后端没有为这段打点，所以墙钟/CPU/核数都没有：用时按两端之差显示。
        wallS: null,
        cpuS: null,
        cores: null,
        detail: '等调度派发 + 起进程',
        waiting: false,
        positionKnown: true,
        head: true,
      })
    }

    const lastSegmentEndS = segments.reduce((acc, segment) => Math.max(acc, segment.endS), offsetS)
    // 该任务的总耗时：span 的 duration_s 最可信，其次是报告里的端到端/阶段之和；
    // 进行中的任务没有总耗时，只能画到「现在」。
    const reportedTotalS =
      span?.durationS ?? (running ? null : (report?.end_to_end_s ?? report?.total_s ?? null))
    // 任务自己的 span 给的是绝对时间，换算成时间轴上的秒；进行中的任务取「现在」。
    const spanEndS =
      span !== null && originMs !== null ? ((span.endMs ?? nowMs) - originMs) / 1000 : null
    const spanTailS = span !== null && spanEndS !== null && !running ? spanEndS : null
  const reachedEndS = Math.max(
      offsetS,
      lastSegmentEndS,
      spanEndS ?? Number.NEGATIVE_INFINITY,
      reportedTotalS === null ? Number.NEGATIVE_INFINITY : offsetS + reportedTotalS,
    )
    const totalS = reportedTotalS ?? Math.max(0, reachedEndS - offsetS)

    // 收尾段：最后一段阶段结束 → 任务被标记完成（状态更新 / 下一 tick 调度）
    const tailEndS = spanTailS ?? reachedEndS
    if (!running && tailEndS - lastStageEndS > 0.05) {
      segments.push({
        stage: '_tail',
        label: '收尾',
        startS: roundSeconds(lastStageEndS),
        endS: roundSeconds(tailEndS),
        durationS: roundSeconds(tailEndS - lastStageEndS),
        wallS: null,
        cpuS: null,
        cores: null,
        detail: '状态更新 / 调度延迟',
        waiting: false,
        positionKnown: true,
        tail: true,
      })
    }

    lanes.push({
      taskType,
      label: TASK_LANE_LABELS[taskType] ?? taskType,
      segments,
      offsetS: roundSeconds(offsetS),
      endS: roundSeconds(reachedEndS),
      totalS: roundSeconds(totalS),
      running,
      positionKnown,
      note: !positionKnown
        ? '位置未知'
        : span === null
          ? noUsableSpan
            ? '起点未知（span 缺 start）'
            : '起点按任务自身偏移（无 span）'
          : null,
    })
  }

  if (lanes.length === 0) return null

  const axisTotalS = lanes.reduce((acc, lane) => Math.max(acc, lane.endS), 0)
  const endToEndS =
    originMs !== null && latestEndMs !== null ? Math.max(0, (latestEndMs - originMs) / 1000) : axisTotalS

  return {
    lanes,
    totalS: roundSeconds(Math.max(axisTotalS, endToEndS)),
    endToEndS: roundSeconds(endToEndS),
    running: lanes.some((lane) => lane.running),
  }
}

/** 色块的绝对定位样式（左偏移 + 宽度，按时间轴总长归一化成百分比）。 */
export const taskLaneSegmentStyle = (
  segment: TaskLaneSegment,
  totalS: number,
): { left: string; width: string } => {
  if (!Number.isFinite(totalS) || totalS <= 0) return { left: '0%', width: '0%' }
  const left = Math.min(100, Math.max(0, (segment.startS / totalS) * 100))
  const width = Math.min(100 - left, Math.max(0, ((segment.endS - segment.startS) / totalS) * 100))
  return { left: `${left.toFixed(4)}%`, width: `${width.toFixed(4)}%` }
}

/**
 * 泳道「任务跨度条」的定位：该任务从 offsetS 到 endS（= 自己结束的时刻）。
 * 它**不铺满整行**——右边留白就是「这个任务已经结束、别的任务还在跑」，
 * 用铺满的底槽会让人误读成"进度条没走满"。
 */
export const taskLaneSpanStyle = (
  lane: Pick<TaskLane, 'offsetS' | 'endS'>,
  totalS: number,
): { left: string; width: string } => {
  if (!Number.isFinite(totalS) || totalS <= 0) return { left: '0%', width: '0%' }
  const start = Math.min(totalS, Math.max(0, lane.offsetS))
  const end = Math.min(totalS, Math.max(start, lane.endS))
  const left = (start / totalS) * 100
  const width = ((end - start) / totalS) * 100
  return { left: `${left.toFixed(4)}%`, width: `${Math.max(width, 0.4).toFixed(4)}%` }
}

/** 时间轴刻度：0 / ¼ / ½ / ¾ / 总长（秒，1 位小数）。 */
export const buildTimelineTicks = (totalS: number, count = 4): number[] => {
  if (!Number.isFinite(totalS) || totalS <= 0 || count < 1) return []
  const ticks: number[] = []
  for (let i = 0; i <= count; i += 1) {
    ticks.push(Number(((totalS * i) / count).toFixed(1)))
  }
  return ticks
}

/** 刻度文字的定位（与段色块同一套百分比口径）。 */
export const taskLaneTickStyle = (
  tickS: number,
  totalS: number,
): { left: string } => {
  if (!Number.isFinite(totalS) || totalS <= 0) return { left: '0%' }
  const left = Math.min(100, Math.max(0, (tickS / totalS) * 100))
  return { left: `${left.toFixed(4)}%` }
}

/**
 * 图例：把三条泳道里**出现过的阶段**按出现顺序去重列出（含「排队 / 启动」与「收尾」
 * 这两个非后端打点的补充段）。这样图例覆盖图上每一种颜色，不会只解释解析那一条。
 */
export const collectTimelineLegend = (
  timeline: TaskTimeline | null,
): Array<{ stage: string; label: string }> => {
  if (!timeline) return []
  const seen = new Set<string>()
  const items: Array<{ stage: string; label: string }> = []
  for (const lane of timeline.lanes) {
    for (const segment of lane.segments) {
      if (seen.has(segment.stage)) continue
      seen.add(segment.stage)
      items.push({ stage: segment.stage, label: segment.label })
    }
  }
  return items
}

/** 色块的悬停说明：`扫描 · 用时 2.3 s · 占比 12.3% · 7.83 核 · 11 文件 / 1909790 行`。 */
export const formatTaskLaneSegmentTitle = (segment: TaskLaneSegment, totalS: number): string => {
  const waitingSuffix = segment.waiting && !segment.label.includes('等待') ? '（等待）' : ''
  const parts = [`${segment.label}${waitingSuffix}`]
  parts.push(`用时 ${formatParseTimingSeconds(segment.durationS)}`)
  parts.push(`占比 ${formatParseTimingShare(segment.durationS, totalS)}`)
  parts.push(formatParseTimingCores(segment.cores))
  if (segment.detail) parts.push(segment.detail)
  if (!segment.positionKnown) parts.push('位置未知（按 wall_s 顺序铺开）')
  return parts.join(' · ')
}
