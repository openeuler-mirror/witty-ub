import { request } from './http'
import {
  extractArray,
  formatFullTimeLabel,
  normalizeTraceRow,
  toQueryString,
} from '../utils/format'
import type { LatencyPoint } from '../types'

const LATENCY_SAMPLE_MODES: Record<string, string> = {
  p99: 'p99',
  p9999: 'p9999',
  pmax: 'max',
  ave: 'avg',
}

export const fetchLatencyMetrics = async (
  kbId: string,
  op: 'get' | 'set',
  pct: string,
  logId?: string,
  bucketSeconds = 60,
) => {
  const result = await request<{ metrics: LatencyPoint[] }>('/log_parse_result/metrics/latency', {
    method: 'POST',
    body: JSON.stringify({
      kb_id: kbId,
      max_points: 1000,
      sample_mode: LATENCY_SAMPLE_MODES[pct] ?? pct,
      sort_by: 'timestamp',
      sort_order: 'asc',
      operation: op.toUpperCase(),
      bucket_seconds: bucketSeconds,
      log_id: logId,
    }),
  })
  return (result.metrics ?? []).map((metric) => ({
    ...metric,
    time: metric.time ?? metric.timestamp ?? metric.created_at,
  }))
}

export const fetchTopSlow = async (kbId: string, op: 'get' | 'set', logId?: string) => {
  const result = await request<{ total: number; log_parse_results: any[] }>(
    '/log_parse_result/list',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        page_num: 1,
        page_cnt: 1000,
        sort_fields: [
          { field: 'total_latency', order: 'desc' },
          { field: 'timestamp', order: 'asc' },
        ],
        operation: op.toUpperCase(),
        log_id: logId,
      }),
    },
  )
  return {
    total: result.total ?? 0,
    rows: (result.log_parse_results ?? []).map(normalizeTraceRow),
  }
}

export const fetchParseResultTotal = async (
  kbId: string,
  op: 'get' | 'set',
  isAnomalous?: boolean,
  logId?: string,
) => {
  const result = await request<{ total: number }>('/log_parse_result/list', {
    method: 'POST',
    body: JSON.stringify({
      kb_id: kbId,
      page_num: 1,
      page_cnt: 1,
      is_anomalous: isAnomalous,
      operation: op.toUpperCase(),
      log_id: logId,
    }),
  })
  return result.total ?? 0
}

export const fetchAbnormalTraces = async (kbId: string, op: 'get' | 'set', logId?: string) => {
  const result = await request<{ total: number; log_parse_results: any[] }>(
    '/log_parse_result/list',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        page_num: 1,
        page_cnt: 200,
        is_anomalous: true,
        operation: op.toUpperCase(),
        log_id: logId,
      }),
    },
  )
  return {
    total: result.total ?? 0,
    rows: (result.log_parse_results ?? []).map(normalizeTraceRow),
  }
}

export interface TimeWindowQuery {
  interval?: number
  startTime?: string
  endTime?: string
  logId?: string
}

const TIME_WINDOW_PAGE_CNT = 2000
// 短期完整加载上限：5 页 × 2000。超过则标记截断，UI 不得宣称全域最高值
const TIME_WINDOW_MAX_PAGES = 5

// 返回 total 与 rows：按 total 分页取全（短期方案），超出上限时标记截断
export const fetchTimeWindowAggregated = async (
  kbId: string,
  op: 'get' | 'set',
  query: TimeWindowQuery = {},
) => {
  const interval = query.interval ?? 60
  const baseBody = {
    kb_id: kbId,
    page_cnt: TIME_WINDOW_PAGE_CNT,
    interval,
    stat_type: 'p99',
    operation: op.toUpperCase(),
    start_time: query.startTime,
    end_time: query.endTime,
    log_id: query.logId,
  }
  const readPage = async (pageNum: number) => {
    const result = await request<{ total?: number } & Record<string, unknown>>(
      '/aggregated_event/list_time_window',
      {
        method: 'POST',
        body: JSON.stringify({ ...baseBody, page_num: pageNum }),
      },
    )
    const rows = extractArray<any>(result, ['events', 'items', 'list', 'time_window_events'])
    const total =
      typeof (result as any)?.total === 'number'
        ? (result as any).total
        : (result as any)?.result?.total
    return { total: total ?? 0, rows }
  }

  const first = await readPage(1)
  const rows = [...first.rows]
  const totalPages = Math.min(Math.ceil(first.total / TIME_WINDOW_PAGE_CNT), TIME_WINDOW_MAX_PAGES)
  for (let page = 2; page <= totalPages; page++) {
    const next = await readPage(page)
    rows.push(...next.rows)
  }
  return { total: first.total, rows, truncated: rows.length < first.total }
}

// 对象详情（窗 × Pod/链路）的服务端分页时延 Trace 查询
export interface LatencyTracePageQuery {
  op?: 'get' | 'set'
  startTime?: string
  endTime?: string
  srcIp?: string
  dstIp?: string
  endpointIp?: string
  logId?: string
  pageNum: number
  pageCnt: number
}

export const fetchLatencyTracePage = async (kbId: string, query: LatencyTracePageQuery) => {
  const result = await request<{ total?: number; log_parse_results?: any[] }>(
    '/log_parse_result/list',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        is_anomalous: true,
        operation: query.op ? query.op.toUpperCase() : undefined,
        start_time: query.startTime,
        end_time: query.endTime,
        src_ip: query.srcIp,
        dst_ip: query.dstIp,
        endpoint_ip: query.endpointIp,
        log_id: query.logId,
        page_num: query.pageNum,
        page_cnt: query.pageCnt,
      }),
    },
  )
  return {
    total: result.total ?? 0,
    rows: (result.log_parse_results ?? []).map(normalizeTraceRow),
  }
}

// 通断对象详情（窗 × 端点/链路）的服务端分页故障 Trace 查询
export interface FaultTracePageQuery {
  op?: 'get' | 'set'
  startTime?: string
  endTime?: string
  srcIp?: string
  dstIp?: string
  endpointIp?: string
  statusCodes?: string[]
  pageNum: number
  pageCnt: number
}

export const fetchFaultTracePage = async (kbId: string, query: FaultTracePageQuery) => {
  const result = await request<{ total?: number; trace_failure_event_results?: any[] }>(
    '/log_failure_event_result/list_trace_events',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        is_anomalous: true,
        operation: query.op ? query.op.toUpperCase() : undefined,
        start_time: query.startTime,
        end_time: query.endTime,
        src_ip: query.srcIp,
        dst_ip: query.dstIp,
        endpoint_ip: query.endpointIp,
        status_codes: query.statusCodes,
        page_num: query.pageNum,
        page_cnt: query.pageCnt,
      }),
    },
  )
  return {
    total: result.total ?? 0,
    rows: result.trace_failure_event_results ?? [],
  }
}

// 通断异常 Trace 的服务端 Trace ID 查询：独立于主视图已加载数据，不受分页加载上限影响
export const searchFaultTracesByTraceId = async (
  kbId: string,
  traceId: string,
  op: 'get' | 'set',
) => {
  const result = await request<{ total?: number; trace_failure_event_results?: any[] }>(
    '/log_failure_event_result/list_trace_events',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        is_anomalous: true,
        operation: op.toUpperCase(),
        trace_ids: [traceId],
        page_num: 1,
        page_cnt: 100,
      }),
    },
  )
  return { total: result.total ?? 0, rows: result.trace_failure_event_results ?? [] }
}

export const fetchFaultChart = async (kbId: string, op: 'get' | 'set') => {
  const result = await request<{
    metrics: Record<
      string,
      Array<{ time?: string; timestamp?: string; err_cnt?: number; count?: number }>
    >
  }>('/log_failure_event_result/metrics/err_code', {
    method: 'POST',
    body: JSON.stringify({ kb_id: kbId, max_points: 1000, operation: op.toUpperCase() }),
  })
  const out: Record<string, Array<{ time: string; err_cnt: number }>> = {}
  for (const [code, points] of Object.entries(result.metrics ?? {})) {
    out[code] = (points ?? []).map((point) => ({
      time: point.time ?? point.timestamp ?? '',
      err_cnt: point.err_cnt ?? point.count ?? 0,
    }))
  }
  return out
}

const FAULT_TRACE_PAGE_CNT = 500
const FAULT_TRACE_MAX_PAGES = 5

export const fetchFaultTraces = async (kbId: string, op: 'get' | 'set') => {
  const readPage = async (pageNum: number) => {
    const result = await request<{ total: number; trace_failure_event_results: any[] }>(
      '/log_failure_event_result/list_trace_events',
      {
        method: 'POST',
        body: JSON.stringify({
          kb_id: kbId,
          page_num: pageNum,
          page_cnt: FAULT_TRACE_PAGE_CNT,
          is_anomalous: true,
          operation: op.toUpperCase(),
        }),
      },
    )
    return {
      total: result.total ?? 0,
      rows: result.trace_failure_event_results ?? [],
    }
  }

  const first = await readPage(1)
  const rows = [...first.rows]
  const totalPages = Math.min(Math.ceil(first.total / FAULT_TRACE_PAGE_CNT), FAULT_TRACE_MAX_PAGES)
  for (let page = 2; page <= totalPages; page++) {
    const next = await readPage(page)
    rows.push(...next.rows)
  }
  return { total: first.total, rows, truncated: rows.length < first.total }
}

// 通断聚合事件表（时间桶矩阵）：服务端 date_trunc 分桶，响应 total 分页，无 log_id 参数
export interface TimeAggFailureQuery {
  op?: 'get' | 'set'
  interval: 'second' | 'minute' | 'hour'
  startTime?: string
  endTime?: string
  sortField?: string // 'timestamp' 或 err_codes 中的码（含 all）
  sortDesc?: boolean
  pageNum: number
  pageCnt: number
}

export const fetchTimeAggregatedFailureEvents = async (
  kbId: string,
  query: TimeAggFailureQuery,
) => {
  const result = await request<{ total?: number; err_codes?: string[]; events?: any[] }>(
    '/log_failure_event_result/list_time_aggregated_failure_events',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        operation: query.op ? query.op.toUpperCase() : undefined,
        interval: query.interval,
        start_time: query.startTime,
        end_time: query.endTime,
        sort_fields: query.sortField
          ? [{ field: query.sortField, order: query.sortDesc ? 'desc' : 'asc' }]
          : undefined,
        page_num: query.pageNum,
        page_cnt: query.pageCnt,
      }),
    },
  )
  return { total: result.total ?? 0, errCodes: result.err_codes ?? [], rows: result.events ?? [] }
}

// 桶内 src/dst IP 对子表：按码计数、服务端排序分页
export const fetchSrcDstAggregatedFailureEvents = async (
  kbId: string,
  query: Omit<TimeAggFailureQuery, 'interval'>,
) => {
  const result = await request<{ total?: number; events?: any[] }>(
    '/log_failure_event_result/list_src_dst_aggregated_failure_events',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        operation: query.op ? query.op.toUpperCase() : undefined,
        start_time: query.startTime,
        end_time: query.endTime,
        sort_fields: query.sortField
          ? [{ field: query.sortField, order: query.sortDesc ? 'desc' : 'asc' }]
          : undefined,
        page_num: query.pageNum,
        page_cnt: query.pageCnt,
      }),
    },
  )
  return { total: result.total ?? 0, rows: result.events ?? [] }
}

export const fetchTraceLogs = async (kbId: string, traceIds: string[], logId?: string) =>
  request<{ log_failure_event_results?: any[] }>('/log_failure_event_result/list_log_events', {
    method: 'POST',
    body: JSON.stringify({ kb_id: kbId, trace_ids: traceIds, log_id: logId }),
  })

export const fetchTraceLatency = async (kbId: string, traceId: string, logId?: string) => {
  const result = await request<{ total: number; log_parse_results: any[] }>(
    '/log_parse_result/list',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        log_id: logId,
        trace_id: traceId,
        page_num: 1,
        page_cnt: 1,
      }),
    },
  )
  const row = result.log_parse_results?.[0]
  return row ? normalizeTraceRow(row) : null
}

export const fetchLatencyTracesByTraceIds = async (
  kbId: string,
  traceIds: string[],
  logId?: string,
) =>
  request<{ total: number; log_parse_results: any[] }>('/log_parse_result/list', {
    method: 'POST',
    body: JSON.stringify({
      kb_id: kbId,
      log_id: logId,
      is_anomalous: true,
      page_cnt: 1000,
      page_num: 1,
      trace_ids: traceIds,
    }),
  })

export const fetchFaultTracesByTraceIds = async (
  kbId: string,
  traceIds: string[],
  logId?: string,
) =>
  request<{ total: number; trace_failure_event_results: any[] }>(
    '/log_failure_event_result/list_trace_events',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        log_id: logId,
        is_anomalous: true,
        page_cnt: 1000,
        page_num: 1,
        trace_ids: traceIds,
      }),
    },
  )

export const fetchFailureMode = async (failureModeId: string) =>
  request<any>(`/failure_mode/${encodeURIComponent(failureModeId)}`)

// 资产级 profiling 全量（files + rows），文件选择由前端客户端过滤
export const fetchBrpcProfilingKnowledge = (kbId: string) =>
  request<{ files?: any[]; rows?: any[] }>(`/brpc_profiling/knowledge/${encodeURIComponent(kbId)}`)

export const fetchBrpcBatch = (taskId: string) =>
  request<{ task_id: string; batch_id: string }>(
    `/brpc-diagnosis/task/${encodeURIComponent(taskId)}/batch`,
  )

export const fetchBrpcBatchMeta = (batchId: string) =>
  request<{ batch: any }>(`/brpc-diagnosis/batch/${encodeURIComponent(batchId)}`)

export type BrpcTimelineWindowSize = '10s' | '1m' | '10m' | '1h'

export const fetchBrpcInterfaceTimeline = (
  batchId: string,
  start: Date,
  end: Date,
  windowSize: BrpcTimelineWindowSize = '1m',
  extra?: { podIp?: string; podName?: string; signal?: AbortSignal },
) =>
  request<{ series: any[] }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/interface-timeline?${toQueryString({
      start_time: formatFullTimeLabel(start),
      end_time: formatFullTimeLabel(end),
      window_size: windowSize,
      pod_ip: extra?.podIp,
      pod_name: extra?.podName,
    })}`,
    { signal: extra?.signal },
  )

export const fetchBrpcPodEvents = (
  batchId: string,
  start: Date,
  end: Date,
  pageNum: number,
  pageCnt: number,
  windowSize: '1s' | '1m' | '1h' = '1m',
) =>
  request<{ total: number; events: any[] }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/pod-events?${toQueryString({
      start_time: formatFullTimeLabel(start),
      end_time: formatFullTimeLabel(end),
      window_size: windowSize,
      page_num: pageNum,
      page_cnt: pageCnt,
    })}`,
  )

// 聚合指标=线程 ID：按 窗口 × Pod × 线程 聚合（字段含 thread_id）
export const fetchBrpcThreadEvents = (
  batchId: string,
  start: Date,
  end: Date,
  pageNum: number,
  pageCnt: number,
  windowSize: '1s' | '1m' | '1h' = '1m',
) =>
  request<{ total: number; events?: any[]; threads?: any[] }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/thread-events?${toQueryString({
      start_time: formatFullTimeLabel(start),
      end_time: formatFullTimeLabel(end),
      window_size: windowSize,
      page_num: pageNum,
      page_cnt: pageCnt,
    })}`,
  )

// 聚合事件详情：组件计数（failure_modes）+ hit_total
export const fetchBrpcEventDetail = (
  batchId: string,
  eventId: string,
  params: {
    window_start_time: string
    window_end_time: string
    pod_ip: string
    pod_name?: string
    thread_id?: number
  },
) =>
  request<{ event?: any; failure_modes?: any[]; hit_total?: number }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/pod-events/${encodeURIComponent(eventId)}?${toQueryString({ ...params, page_num: 1, page_cnt: 100 })}`,
  )

export const fetchBrpcAbnormalThreads = (
  batchId: string,
  start: Date,
  end: Date,
  pageNum: number,
  pageCnt: number,
  extra?: { podIp?: string; podName?: string; search?: string },
) =>
  request<{ total: number; threads: any[] }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/abnormal-threads?${toQueryString({
      start_time: formatFullTimeLabel(start),
      end_time: formatFullTimeLabel(end),
      page_num: pageNum,
      page_cnt: pageCnt,
      pod_ip: extra?.podIp,
      pod_name: extra?.podName,
      search: extra?.search,
    })}`,
  )

// 异常 Thread 详情：failure_graph + interface_timeline + failure_modes + hits
export const fetchBrpcThreadDetail = (
  batchId: string,
  threadKey: string,
  params: {
    pod_ip: string
    thread_id: number
    start_time: string
    end_time: string
    window_size?: string
    pod_name?: string
  },
) =>
  request<{
    thread?: any
    interface_timeline?: any[]
    failure_modes?: any[]
    failure_graph?: { nodes: any[]; edges: any[] }
    hit_total?: number
    hits?: any[]
  }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/abnormal-threads/${encodeURIComponent(threadKey)}?${toQueryString({ ...params, page_num: 1, page_cnt: 1 })}`,
  )

// 线程全部运行日志（含正常行；故障行带 failure_mode_id）
export const fetchBrpcThreadLogs = (
  batchId: string,
  params: {
    pod_ip: string
    thread_id: number
    start_time: string
    end_time: string
    pod_name?: string
  },
) =>
  request<{ total: number; hits: any[] }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/thread-logs?${toQueryString(params)}`,
  )
