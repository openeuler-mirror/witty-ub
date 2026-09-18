/**
 * 解析用时（总量 + 分阶段明细）的纯逻辑。
 *
 * 两个来源共用同一份规范化代码：
 *   1. `/log_file/list` 里每个日志文件的 `parse_timing`；
 *   2. 解析任务自己在 `task_reports` 里留下的 `[timing] {json}` 单行报告（兜底）。
 * 任一字段不可用时返回 null，调用方据此整块不渲染。
 */

/** 同一阶段被登记多次时的**一次登记**（后端契约 `stages[].occurrences[]` 的元素）。 */
export interface ParseTimingOccurrence {
  /** 这一次登记相对**本任务 run() 起点**的偏移（秒）；取不到时钟时整个键不存在。 */
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
   * 归一化时整个键就不写进来（键不存在 = 位置未知）。
   */
  start_s?: number | null
  end_s?: number | null
  /**
   * 该阶段**每一次登记**的记录（按登记先后）。只登记一次 → 长度 1；老报告没有这个键
   * （归一化时整个键不写，消费方据此原样回退）。一个有效条目都没有时同样不写。
   */
  occurrences?: ParseTimingOccurrence[]
}

export interface ParseTimingReport {
  /** 这条报告属于哪个任务（`kv_cache_log_parse_worker` 等）；老报告没有 → 键不存在。 */
  task_type?: string | null
  /** 各阶段墙钟之和（秒）——注意它不是任务端到端耗时。 */
  total_s: number
  /** 任务端到端耗时（秒）：run() 起点 → 报告发出，含预处理/调度/收尾；缺省为 null。 */
  end_to_end_s: number | null
  /** 解析行数；缺省为 null。 */
  rows: number | null
  stages: ParseTimingStage[]
}

/** `[timing] {...}` 报告的消息前缀（后端契约要求前缀后跟一个空格 + 单行紧凑 JSON）。 */
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
    // 与阶段级同口径：后端没给偏移就不写这个键 = 该次位置未知。
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
  const report: ParseTimingReport = {
    total_s: totalS,
    end_to_end_s: toTimingNumber(record.end_to_end_s),
    rows: toTimingNumber(record.rows),
    stages,
  }
  if (typeof record.task_type === 'string' && record.task_type) {
    report.task_type = record.task_type
  }
  return report
}

/** 解析 `[timing] {json}` 报告消息；前缀不符、JSON 损坏或形状不对时返回 null（不抛出）。 */
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
 * 决定任务行要展示的解析用时。
 * @param fromFile  `file.parse_timing`（主来源）
 * @param candidates 当前可见任务的报告（兜底来源）
 * @returns 规范化后的报告；两条来源都拿不到、或 JSON 损坏/形状不对 → null（整块不渲染）。
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

  const latest = [...timingCandidates].sort((first, second) => second.time - first.time)[0] ?? null
  return latest ? parseTimingReportFromMessage(latest.message) : null
}

/** 秒 → `11.9 s`；缺值 → `—`。 */
export const formatParseTimingSeconds = (value: number | null): string =>
  value === null ? '—' : `${value.toFixed(1)} s`

/** 主标题的时长：解析任务自己的端到端（老报告没有这个字段时退回阶段之和）。 */
export const parseTimingHeadlineSeconds = (report: ParseTimingReport | null): number | null =>
  report === null ? null : (report.end_to_end_s ?? report.total_s)

/** 主标题右侧的口径标签。 */
export const parseTimingHeadlineLabel = (): string => '解析任务'

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
