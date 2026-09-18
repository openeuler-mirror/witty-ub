import type { ParseTimingReport } from '../utils/parseTiming'

export type ApiResponse<T> = {
  code?: number
  message?: string
  result?: T
  data?: T
}

export type LogKnowledge = {
  id: string
  name: string
  description: string
  task_cnt?: number
  log_file_cnt?: number
  anomaly_cnt?: number
  created_at?: string
  updated_at?: string
  existed_status?: boolean
}

export type TaskReport = {
  task_id: string
  progress: number
  message?: string | null
  created_at?: string
}

export type TaskModel = {
  id: string
  kb_id?: string
  op_id?: string
  task_name?: string
  task_type?: string
  task_reports?: TaskReport[]
  status?: string
  existed_status?: boolean
  created_at?: string
  completed_at?: string | null
  duration_seconds?: number | null
}

export type LogType = 'KVCache' | 'UBSocket'

export type LogFileModel = {
  id: string
  kb_id: string
  name: string
  overall_status: string
  file_path: string
  file_size: number
  anomaly_cnt: number
  trace_failure_event_cnt?: number
  log_type: LogType
  task: TaskModel | null
  overall_progress?: number
  /** 解析任务最新一条 `[timing]` 报告（= stage_timings 里解析任务那一项）。 */
  parse_timing?: ParseTimingReport | null
  existed_status: boolean
  created_at: string
}

export type Toast = {
  id: number
  text: string
  type: 'success' | 'error' | 'info'
}

export type AssetModalMode = 'create' | 'edit'

export type LatencyPoint = Record<string, any>

export type AggregatedPair = {
  key: string
  src: string
  dst: string
  total: number
  anomaly: number
  get: number
  set: number
  queryMeta?: number | null
  urmaTotal?: number | null
  urmaLink?: number | null
  c2w?: number | null
  w2w?: number | null
  /** 元戎分阶段指标均值（key 为 allMetrics 的 key，值为均值，µs，urma_inflight_max 为计数） */
  metricValues?: Record<string, number | null>
  /** 该 IP 对所属的时间窗口开始时间（当来自单窗口时存在） */
  bucketStart?: string
  /** 该 IP 对所属的时间窗口结束时间 */
  bucketEnd?: string
}

export type TimeWindowIpPair = {
  src_ip: string
  dst_ip: string
  log_parse_result_cnt: number
  anomaly_cnt: number
  [key: string]: any
}

export type TimeWindowBucket = {
  start_time: string
  end_time: string
  total_cnt: number
  anomaly_cnt: number
  ave_total_latency: number | null
  p99_total_latency: number | null
  ip_pairs: TimeWindowIpPair[]
  [key: string]: any
}

export type ScopeData = {
  kpi: {
    get: { traceTotal: number; anomalyTotal: number; latencyTotal: number; podCount: number }
    set: { traceTotal: number; anomalyTotal: number; latencyTotal: number; podCount: number }
    faultTraceSetTotal: number
    faultSetTotal: number
  }
  latency: Record<'get' | 'set', Record<'p99' | 'p9999' | 'pmax' | 'ave', LatencyPoint[]>>
  topSlow: any[]
  abnormal: any[]
  aggregated: AggregatedPair[]
  faultChart: Record<string, Array<{ time: string; err_cnt: number }>>
  faultTraces: any[]
  /** 按操作类型缓存的时间窗聚合桶（含 ip_pairs 与 ave_* 指标），保留时域信息 */
  timeWindows: Record<'get' | 'set', TimeWindowBucket[]>
}
