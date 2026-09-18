/**
 * 任务列表两列计数的口径（与当前后端实现一一对应）：
 *
 * - 时延异常（`anomaly_cnt`）：KVCache 是 `log_file.anomalous_count`（解析判定的异常 trace 数），
 *   UBSocket 是 `brpc_profiling_result` 文件数（`_populate_brpc_counts`）；
 * - 通断异常（`trace_failure_event_cnt`）：KVCache 是 `log_file.failure_count`（落库的故障 trace 数），
 *   UBSocket 是诊断批次 `hit_count`（命中的故障接口数）。
 *
 * 两个数在「整条流水线成功」之前会被后端统一按 0 返回
 * （`LogFileService._mask_counts_until_complete`），所以此时界面要显示 `—`
 * 而不是 `0`，否则会被读成「没有异常」。
 */

const SETTLED_STATUSES = new Set(['successful', 'successful_pending_remove'])

/** 日志级状态是否已到「整条流水线成功」（后端此时才放出真实计数）。 */
export const countsSettled = (overallStatus: string): boolean => SETTLED_STATUSES.has(overallStatus)

/** 计数单元格文案：未跑完显示 `—`，跑完显示真实计数（缺失按 0）。 */
export const countText = (value: number | null | undefined, overallStatus: string): string =>
  countsSettled(overallStatus) ? String(value ?? 0) : '—'

/**
 * 资产卡片的日志文件数：来自 `/log_file/list/{kb}` 的 `total`（真实文件数），
 * 尚未加载到（或该请求失败）时显示 `—`。
 *
 * 不回退到 `LogKnowledgeModel.task_cnt`：那一列由 `refresh_kb_counters` 维护，
 * UBSocket 任务的收尾只 touch 更新时间、不刷新计数，所以只跑过 UBSocket 任务的资产会恒为 0。
 */
export const assetLogFileCountText = (count: number | undefined): string =>
  count === undefined ? '—' : String(count)
