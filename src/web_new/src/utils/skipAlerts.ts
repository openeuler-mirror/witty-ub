/**
 * 坏日志文件被跳过的告警：从任务报告里挑出后端的 `[skip] ...` 文案。
 *
 * 后端解析时遇到读不出来的日志文件会跳过，并上报一条任务报告；用户需要看到
 * 「这次跳过了谁、为什么」。前缀常量与后端 `kv_cache_log_parse_worker` 一致。
 */
export const SKIPPED_REPORT_PREFIX = '[skip]'

export type SkipReportLike = { message?: string | null }

/** 取出跳过告警（去掉 `[skip]` 前缀，已是可直接展示的中文文案）。 */
export const collectSkippedFileAlerts = (
  reports: readonly SkipReportLike[] | null | undefined,
): string[] =>
  (reports ?? [])
    .map((report) => (report?.message ?? '').trim())
    .filter((message) => message.startsWith(SKIPPED_REPORT_PREFIX))
    .map((message) => message.slice(SKIPPED_REPORT_PREFIX.length).trim())
    .filter((message) => message.length > 0)
