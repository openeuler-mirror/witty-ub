import type { LogType } from '../types'

/**
 * 任务列表两列计数的口径（与当前后端实现一一对应）：
 *
 * | 列 | KVCache | UBSocket |
 * | --- | --- | --- |
 * | 时延异常（`anomaly_cnt`） | `log_file.anomalous_count`：解析判定的异常 trace 条数 | `brpc_profiling_result` 文件数（`_populate_brpc_counts`） |
 * | 通断异常（`trace_failure_event_cnt`） | `log_file.failure_count`：落库的故障 trace 条数 | 诊断批次 `hit_count`：命中的故障接口数 |
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

/** 单行悬停说明：把该行类型下这一列的真实含义讲清楚。 */
export const countCellTitle = (kind: 'latency' | 'fault', logType: LogType): string => {
  const byType =
    kind === 'latency'
      ? {
          KVCache: '解析判定的时延异常 trace 条数',
          UBSocket: 'profiling 结果文件数',
        }
      : {
          KVCache: '落库的故障 trace 条数',
          UBSocket: '诊断命中的故障接口数',
        }
  return `${logType}：${byType[logType]}（任务整条流水线完成前后端固定返回 0，这里显示为 —）`
}
