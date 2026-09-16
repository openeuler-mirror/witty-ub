type TaskReportLike = {
  message?: string | null
  created_at?: string | null
  progress?: number | null
}

type TaskProgressSource = {
  overall_status?: string | null
  task?: { status?: string | null; task_reports?: TaskReportLike[] } | null
}

const ignoredReportPrefixes = ['[perf]', '[parse_log]', '[TASK]']

const stageLabels: Record<string, string> = {
  scan: '正在扫描日志',
  trace_frame: '正在构建Trace索引',
  aggregate: '正在聚合分析',
  bucket: '正在计算分位桶',
  detail: '正在生成明细',
  store: '正在写入数据库',
}

const milestoneLabels: Record<string, string> = {
  'Task initialized': '任务已初始化',
  'Task reinitialized': '任务已重新初始化',
  'Task running': '任务运行中',
  'Log parse completed': '日志解析完成',
  'Anomaly detection done': '异常检测完成',
  'Aggregate events done': '聚合事件完成',
  'Fault matching done': '故障匹配完成',
  'Results stored': '结果已入库',
  'Task completed successfully': '解析完成',
  'Task failed': '解析失败',
}

export const humanizeTaskProgressMessage = (message: string): string => {
  const trimmed = message.trim()
  if (!trimmed) return ''

  const stageMatch = trimmed.match(
    /^\[polars\]\[([\w-]+)\](?:\s+progress=\d+(?:\.\d+)?%)?(?:\s+(.*))?$/,
  )
  if (stageMatch) {
    const stageKey = stageMatch[1] ?? 'unknown'
    const label = stageLabels[stageKey] ?? `正在解析（${stageKey}）`
    const detail = (stageMatch[2] ?? '').trim()
    return detail ? `${label}: ${detail}` : label
  }

  for (const [english, chinese] of Object.entries(milestoneLabels)) {
    if (
      trimmed === english ||
      trimmed.startsWith(`${english}:`) ||
      trimmed.startsWith(`${english} `)
    ) {
      return chinese
    }
  }

  return trimmed.replace(/\s*progress=\d+(?:\.\d+)?%/g, '')
}

export const latestTaskReport = (
  file: TaskProgressSource,
  ignoreInternalNoise = false,
): TaskReportLike | undefined =>
  (file.task?.task_reports ?? [])
    .map((report, index) => ({ report, index }))
    .filter(({ report }) => {
      if (!ignoreInternalNoise) return true
      const message = report.message?.trim() ?? ''
      return message && !ignoredReportPrefixes.some((prefix) => message.startsWith(prefix))
    })
    .sort(
      (first, second) =>
        String(second.report.created_at ?? '').localeCompare(
          String(first.report.created_at ?? ''),
        ) || first.index - second.index,
    )[0]?.report

export const taskProgressMessage = (file: TaskProgressSource): string => {
  if (file.overall_status === 'retrying') return '正在重试'

  const latest = latestTaskReport(file, true)?.message

  return latest ? humanizeTaskProgressMessage(latest) : ''
}

const failureReasonStatuses = new Set(['failed', 'failed_pending_remove', 'retrying', 'cancelled'])
const taskFailureMessagePattern = /(?:失败|异常停止|error|failed|exception)/i

// 失败原因不能只取「最新一条报告」：任务失败后仍会继续写入 [polars] 进度报告，
// 会把原因顶掉。这里取最新一条带失败语义的报告。
export const taskFailureReason = (file: TaskProgressSource): string => {
  if (!failureReasonStatuses.has(file.overall_status ?? '')) return ''

  const report = (file.task?.task_reports ?? [])
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => taskFailureMessagePattern.test(item.message?.trim() ?? ''))
    .sort(
      (first, second) =>
        String(second.item.created_at ?? '').localeCompare(String(first.item.created_at ?? '')) ||
        first.index - second.index,
    )[0]?.item

  const message = report?.message?.trim()
  return message ? humanizeTaskProgressMessage(message) : '任务未提供失败原因'
}

// 重试中展示的是上一次失败的原因；其余失败态展示当前状态原因。
export const taskFailureReasonLabel = (file: TaskProgressSource): string =>
  (file.overall_status ?? '') === 'retrying' && file.task?.status !== 'failed_pending_remove'
    ? '上次失败原因'
    : '状态原因'
