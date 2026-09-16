// 时延阈值口径集中在这里：解析配置只覆盖 KVCache 总时延，
// 其余阶段与 UBSocket 单接口用显式常量，界面上通过 title 展示取值。

/** UBSocket 单接口 P99 偏高阈值（µs，2000 µs = 2 ms） */
export const UBSOCKET_P99_ABNORMAL_THRESHOLD_US = 2000

export type TraceStageDef = {
  name: string
  key: string
  thresholdMs: number
}

export type TraceStageRow = {
  name: string
  value: number | null
  status: string
  thresholdMs: number
  abnormal: boolean
}

// 阶段阈值对齐上游分列定义：URMA / 元数据 / Master RPC 等链路级阶段 1ms，
// SDK / Worker / Master 的处理与锁阶段 1.5ms。
const TRACE_STAGE_DEFS: TraceStageDef[] = [
  { name: '查询元数据时延', key: 'worker_query_meta_latency', thresholdMs: 1 },
  { name: 'URMA总时延', key: 'urma_total_latency', thresholdMs: 1 },
  { name: 'URMA建链时延', key: 'urma_link_latency', thresholdMs: 1 },
  { name: 'C2W URMA时延', key: 'c2w_urma_latency', thresholdMs: 1 },
  { name: 'W2W URMA时延', key: 'w2w_urma_latency', thresholdMs: 1 },
  { name: 'SDK处理时延', key: 'sdk_process', thresholdMs: 1.5 },
  { name: 'SDK RPC时延', key: 'sdk_rpc', thresholdMs: 1.5 },
  { name: '本地Worker处理时延', key: 'local_worker_cost', thresholdMs: 1.5 },
  { name: '本地Worker锁时延', key: 'local_worker_lock', thresholdMs: 1.5 },
  { name: '远端Worker处理时延', key: 'remote_worker_cost', thresholdMs: 1.5 },
  { name: '远端Worker RPC时延', key: 'remote_worker_rpc', thresholdMs: 1.5 },
  { name: 'Master处理时延', key: 'master_process', thresholdMs: 1.5 },
  { name: 'Master RPC总时延', key: 'master_rpc_total', thresholdMs: 1 },
]

/** 总时延阈值来自解析配置（未配置时用 5ms），其余阶段用固定分列阈值。 */
export const traceStageDefinitions = (totalLatencyThresholdMs: number): TraceStageDef[] => [
  { name: '总时延', key: 'total_latency', thresholdMs: totalLatencyThresholdMs },
  ...TRACE_STAGE_DEFS,
]

export const evaluateTraceStage = (def: TraceStageDef, rawValue: unknown): TraceStageRow => {
  const numeric = rawValue == null || rawValue === '' ? Number.NaN : Number(rawValue)
  const value = Number.isFinite(numeric) ? numeric : null
  const abnormal = value != null && value >= 0 && value > def.thresholdMs
  const status =
    value == null
      ? '日志不存在该时延项目'
      : value < 0
        ? '由总时延被截断引起，该时延值已失真'
        : abnormal
          ? '异常'
          : '正常'
  return { name: def.name, value, status, thresholdMs: def.thresholdMs, abnormal }
}
