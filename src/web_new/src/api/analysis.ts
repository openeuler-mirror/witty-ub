import { request } from './http'
import { extractArray, formatFullTimeLabel, normalizeTraceRow, toQueryString } from '../utils/format'
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
  const result = await request<{ metrics: LatencyPoint[] }>(
    '/log_parse_result/metrics/latency',
    {
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
    },
  )
  return (result.metrics ?? []).map((metric) => ({
    ...metric,
    time: metric.time ?? metric.timestamp ?? metric.created_at,
  }))
}

export const fetchTopSlow = async (kbId: string, op: 'get' | 'set') => {
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
      }),
    },
  )
  return {
    total: result.total ?? 0,
    rows: (result.log_parse_results ?? []).map(normalizeTraceRow),
  }
}

export const fetchParseResultTotal = async (kbId: string, op: 'get' | 'set', isAnomalous?: boolean) => {
  const result = await request<{ total: number }>('/log_parse_result/list', {
    method: 'POST',
    body: JSON.stringify({
      kb_id: kbId,
      page_num: 1,
      page_cnt: 1,
      is_anomalous: isAnomalous,
      operation: op.toUpperCase(),
    }),
  })
  return result.total ?? 0
}

export const fetchAbnormalTraces = async (kbId: string, op: 'get' | 'set') => {
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
      }),
    },
  )
  return {
    total: result.total ?? 0,
    rows: (result.log_parse_results ?? []).map(normalizeTraceRow),
  }
}

export const fetchTimeWindowAggregated = async (
  kbId: string,
  op: 'get' | 'set',
  interval = 60,
) => {
  const result = await request<unknown>('/aggregated_event/list_time_window', {
    method: 'POST',
    body: JSON.stringify({
      kb_id: kbId,
      page_num: 1,
      page_cnt: 2000,
      interval,
      stat_type: 'p99',
      operation: op.toUpperCase(),
    }),
  })
  return extractArray<any>(result, ['events', 'items', 'list', 'time_window_events'])
}

export const fetchFaultChart = async (kbId: string, op: 'get' | 'set') => {
  const result = await request<{
    metrics: Record<string, Array<{ time?: string; timestamp?: string; err_cnt?: number; count?: number }>>
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

export const fetchFaultTraces = async (kbId: string, op: 'get' | 'set') => {
  const result = await request<{ total: number; trace_failure_event_results: any[] }>(
    '/log_failure_event_result/list_trace_events',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        page_num: 1,
        page_cnt: 500,
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

export const fetchTraceLogs = async (kbId: string, traceIds: string[]) =>
  request<{ log_failure_event_results?: any[] }>('/log_failure_event_result/list_log_events', {
    method: 'POST',
    body: JSON.stringify({ kb_id: kbId, trace_ids: traceIds }),
  })

export const fetchTraceLatency = async (kbId: string, traceId: string) => {
  const result = await request<{ total: number; log_parse_results: any[] }>(
    '/log_parse_result/list',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        trace_id: traceId,
        page_num: 1,
        page_cnt: 1,
      }),
    },
  )
  const row = result.log_parse_results?.[0]
  return row ? normalizeTraceRow(row) : null
}

export const fetchLatencyTracesByTraceIds = async (kbId: string, traceIds: string[]) =>
  request<{ total: number; log_parse_results: any[] }>('/log_parse_result/list', {
    method: 'POST',
    body: JSON.stringify({
      kb_id: kbId,
      is_anomalous: true,
      page_cnt: 1000,
      page_num: 1,
      trace_ids: traceIds,
    }),
  })

export const fetchFaultTracesByTraceIds = async (kbId: string, traceIds: string[]) =>
  request<{ total: number; trace_failure_event_results: any[] }>(
    '/log_failure_event_result/list_trace_events',
    {
      method: 'POST',
      body: JSON.stringify({
        kb_id: kbId,
        is_anomalous: true,
        page_cnt: 1000,
        page_num: 1,
        trace_ids: traceIds,
      }),
    },
  )

export const fetchFailureMode = async (failureModeId: string) =>
  request<any>(`/failure_mode/${encodeURIComponent(failureModeId)}`)

export const fetchBrpcProfiling = (logId: string) =>
  request<{ rows: any[] }>(`/brpc_profiling/${logId}`)

export const fetchBrpcBatch = (taskId: string) =>
  request<{ task_id: string; batch_id: string }>(
    `/brpc-diagnosis/task/${encodeURIComponent(taskId)}/batch`,
  )

export const fetchBrpcBatchMeta = (batchId: string) =>
  request<{ batch: any }>(`/brpc-diagnosis/batch/${encodeURIComponent(batchId)}`)

export const fetchBrpcInterfaceTimeline = (
  batchId: string,
  start: Date,
  end: Date,
  windowSize = '1m',
) =>
  request<{ series: any[] }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/interface-timeline?${toQueryString({
      start_time: formatFullTimeLabel(start),
      end_time: formatFullTimeLabel(end),
      window_size: windowSize,
    })}`,
  )

export const fetchBrpcPodEvents = (
  batchId: string,
  start: Date,
  end: Date,
  pageNum: number,
  pageCnt: number,
) =>
  request<{ total: number; events: any[] }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/pod-events?${toQueryString({
      start_time: formatFullTimeLabel(start),
      end_time: formatFullTimeLabel(end),
      window_size: '1m',
      page_num: pageNum,
      page_cnt: pageCnt,
    })}`,
  )

export const fetchBrpcAbnormalThreads = (
  batchId: string,
  start: Date,
  end: Date,
  pageNum: number,
  pageCnt: number,
) =>
  request<{ total: number; threads: any[] }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/abnormal-threads?${toQueryString({
      start_time: formatFullTimeLabel(start),
      end_time: formatFullTimeLabel(end),
      page_num: pageNum,
      page_cnt: pageCnt,
    })}`,
  )

// 线程全部运行日志（含正常行；故障行带 failure_mode_id）
export const fetchBrpcThreadLogs = (
  batchId: string,
  params: { pod_ip: string; thread_id: number; start_time: string; end_time: string; pod_name?: string },
) =>
  request<{ total: number; hits: any[] }>(
    `/brpc-diagnosis/batch/${encodeURIComponent(batchId)}/thread-logs?${toQueryString(params)}`,
  )
