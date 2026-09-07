import { computed, nextTick, reactive, ref, watch } from 'vue'
import { getInstanceByDom, init, use, type ECharts } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, GraphChart, HeatmapChart, LineChart, PieChart } from 'echarts/charts'
import {
  BrushComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  ToolboxComponent,
  TooltipComponent,
} from 'echarts/components'
use([
  CanvasRenderer,
  BarChart,
  GraphChart,
  HeatmapChart,
  LineChart,
  PieChart,
  BrushComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  ToolboxComponent,
  TooltipComponent,
])
import rawDiagnosisConfig from '../../../../config/diagnosis_config.toml'
import { useToast } from './useToast'
import type {
  AggregatedPair,
  LatencyPoint,
  LogFileModel,
  LogKnowledge,
  ScopeData,
  TimeWindowBucket,
} from '../types'
import {
  epochMsToTs,
  errorText,
  formatChartTs,
  formatFullTimeLabel,
  normalizeFaultCodes,
  paginate,
  tsToEpochMs,
} from '../utils/format'
import {
  fetchAbnormalTraces,
  fetchBrpcAbnormalThreads,
  fetchBrpcBatch,
  fetchBrpcBatchMeta,
  fetchBrpcInterfaceTimeline,
  fetchBrpcPodEvents,
  fetchBrpcProfiling,
  fetchBrpcThreadLogs,
  fetchFailureMode,
  fetchFaultChart,
  fetchFaultTracePage,
  fetchFaultTracesByTraceIds,
  fetchFaultTraces,
  fetchLatencyTracePage,
  fetchLatencyTracesByTraceIds,
  fetchLatencyMetrics,
  fetchParseResultTotal,
  fetchTimeWindowAggregated,
  fetchTopSlow,
  fetchTraceLatency,
  fetchTraceLogs,
} from '../api/analysis'
import { createAnalysisFilter, type AnalysisFocus } from './useAnalysisFilter'

export type UseOverviewDataOptions = {
  getAsset: () => LogKnowledge | null
  getLogFiles: () => LogFileModel[]
}

let dataOptions: UseOverviewDataOptions | null = null
let overviewState: ReturnType<typeof createOverviewState> | null = null

export function useOverviewData(options?: UseOverviewDataOptions) {
  if (options) dataOptions = options
  if (!overviewState) overviewState = createOverviewState()
  return overviewState
}

function createOverviewState() {
  const selectedAsset = computed(() => dataOptions?.getAsset() ?? null)
  const logFiles = computed(() => dataOptions?.getLogFiles() ?? [])
  const view = ref<'assets' | 'home'>('home')
  const assetTab = ref<'overview' | 'tasks'>('overview')
  const { toast } = useToast()
  const isSuccess = (file: LogFileModel) =>
    ['successful', 'successful_pending_remove'].includes(file.overall_status || '')

  const diagnosisConfig = rawDiagnosisConfig as any
  const latencyThresholds = {
    p99: diagnosisConfig.log_analyzer_params?.total_p99_threshold_ms ?? 5,
    p9999: diagnosisConfig.log_analyzer_params?.total_p9999_threshold_ms ?? 5,
    pmax: diagnosisConfig.log_analyzer_params?.total_pmax_threshold_ms ?? 5,
    ave: diagnosisConfig.log_analyzer_params?.total_ave_threshold_ms ?? 5,
  }

  // ============ 总览分析工作台（demo_new 设计 + 真实后端数据） ============

  const emptyScopeData = (): ScopeData => ({
    kpi: {
      get: { traceTotal: 0, anomalyTotal: 0, latencyTotal: 0, podCount: 0 },
      set: { traceTotal: 0, anomalyTotal: 0, latencyTotal: 0, podCount: 0 },
      faultTraceSetTotal: 0,
      faultSetTotal: 0,
    },
    latency: {
      get: { p99: [], p9999: [], pmax: [], ave: [] },
      set: { p99: [], p9999: [], pmax: [], ave: [] },
    },
    topSlow: [],
    abnormal: [],
    aggregated: [],
    faultChart: {},
    faultTraces: [],
    timeWindows: { get: [], set: [] },
  })

  const scopeData = ref<ScopeData>(emptyScopeData())
  const sectionCaches = {
    aggregated: new Map<string, AggregatedPair[]>(),
    timeWindows: new Map<string, TimeWindowBucket[]>(),
    kpi: new Map<string, { traceTotal: number; anomalyTotal: number; podCount: number }>(),
    latency: new Map<string, LatencyPoint[]>(),
    topSlow: new Map<string, { total: number; rows: any[] }>(),
    abnormal: new Map<string, { total: number; rows: any[] }>(),
    faultChart: new Map<string, Record<string, Array<{ time: string; err_cnt: number }>>>(),
    faultTraces: new Map<string, { total: number; rows: any[] }>(),
  }
  let lastLogFilesKey = ''
  const faultTraceIdsWithLatency = reactive<Record<'get' | 'set', Set<string>>>({
    get: new Set(),
    set: new Set(),
  })
  const latencyTraceIdsWithFault = reactive<Record<'get' | 'set', Set<string>>>({
    get: new Set(),
    set: new Set(),
  })
  let overlapLoadedFor: { fault: 'get' | 'set' | null; latency: 'get' | 'set' | null } = {
    fault: null,
    latency: null,
  }
  const overviewLoading = ref(false)
  const overviewError = ref('')

  const assetTypeFilter = ref<'kvcache' | 'brpc'>('kvcache')
  const analysisTab = ref<'latency' | 'disconnect'>('latency')
  const analysisModule = reactive({ latency: 'overview', fault: 'chart' })
  const latencyOp = ref('GET')
  const faultOp = ref('GET')
  const currentOp = computed(() =>
    analysisTab.value === 'latency' ? latencyOp.value : faultOp.value,
  )
  const realOp = computed<'get' | 'set'>(() => currentOp.value.toLowerCase() as 'get' | 'set')
  const isAssetMode = computed(() => view.value === 'home' && assetTab.value === 'overview')
  const isBrpcTask = computed(() => assetTypeFilter.value === 'brpc')
  const scopeTasks = computed(() =>
    logFiles.value.filter(
      (file) =>
        (file.log_type || 'kv-cache') ===
          (assetTypeFilter.value === 'brpc' ? 'brpc' : 'kv-cache') && isSuccess(file),
    ),
  )
  const scopeTaskCount = computed(() => scopeTasks.value.length)

  const setCurrentOp = (op: string) => {
    if (analysisTab.value === 'latency') latencyOp.value = op
    else faultOp.value = op
  }

  // ============ 统一分析过滤器：时延与通断各自持有实例 ============
  const latencyFilter = createAnalysisFilter()
  const disconnectFilter = createAnalysisFilter()
  watch(realOp, (op) => {
    latencyFilter.scaleSec.value = overviewScale.value as 10 | 60 | 600 | 3600
    void op
  })

  // 全域时间轴是否被截断（total 超出加载上限）
  const timelineTruncated = ref(false)

  const toAggregatedPairs = (events: TimeWindowBucket[], op: 'get' | 'set'): AggregatedPair[] => {
    const pairs: AggregatedPair[] = []
    let key = 0
    for (const event of events) {
      for (const pair of event.ip_pairs ?? []) {
        const src = pair.src_ip
        const dst = pair.dst_ip
        if (!src || !dst) continue
        const total = pair.log_parse_result_cnt ?? pair.anomaly_cnt ?? 0
        const pairMetricValues: Record<string, number | null> = {}
        allMetrics.forEach((metric) => {
          const value = pair[`ave_${metric.key}`]
          pairMetricValues[metric.key] =
            typeof value === 'number' && Number.isFinite(value) ? value : null
        })
        pairs.push({
          key: String(key++),
          src,
          dst,
          total,
          anomaly: pair.anomaly_cnt ?? pair.anomaly_log_parse_result_cnt ?? 0,
          get: op === 'get' ? total : 0,
          set: op === 'set' ? total : 0,
          queryMeta: pair.p99_query_meta_latency ?? pair.ave_query_meta_latency,
          urmaTotal: pair.p99_urma_total_latency ?? pair.ave_urma_total_latency,
          urmaLink: pair.p99_urma_link_latency ?? pair.ave_urma_link_latency,
          c2w: pair.p99_c2w_urma_latency ?? pair.ave_c2w_urma_latency,
          w2w: pair.p99_w2w_urma_latency ?? pair.ave_w2w_urma_latency,
          metricValues: pairMetricValues,
          bucketStart: event.start_time,
          bucketEnd: event.end_time,
        })
      }
    }
    return pairs
  }

  const clearSectionCaches = () => {
    Object.values(sectionCaches).forEach((cache) => cache.clear())
    overlapLoadedFor = { fault: null, latency: null }
  }

  const loadOverviewSection = async (op: 'get' | 'set') => {
    const asset = selectedAsset.value
    if (!asset) return

    const scaleKey = `${op}:${overviewScale.value}`
    let timeWindows = sectionCaches.timeWindows.get(scaleKey)
    if (!timeWindows) {
      overviewLoading.value = true
      overviewError.value = ''
      try {
        const { rows, truncated } = await fetchTimeWindowAggregated(asset.id, op, {
          interval: overviewScale.value,
        })
        timeWindows = rows
        timelineTruncated.value = truncated
        sectionCaches.timeWindows.set(scaleKey, timeWindows)
      } finally {
        overviewLoading.value = false
      }
    }

    let aggregated = sectionCaches.aggregated.get(scaleKey)
    if (!aggregated) {
      overviewLoading.value = true
      overviewError.value = ''
      try {
        aggregated = toAggregatedPairs(timeWindows, op)
        sectionCaches.aggregated.set(scaleKey, aggregated)
      } finally {
        overviewLoading.value = false
      }
    }

    let kpi = sectionCaches.kpi.get(op)
    if (!kpi) {
      const podSet = new Set<string>()
      aggregated.forEach((pair) => {
        podSet.add(pair.src)
        podSet.add(pair.dst)
      })
      const [traceTotal, anomalyTotal] = await Promise.all([
        fetchParseResultTotal(asset.id, op),
        fetchParseResultTotal(asset.id, op, true),
      ])
      kpi = { traceTotal, anomalyTotal, podCount: podSet.size }
      sectionCaches.kpi.set(op, kpi)
    }

    scopeData.value = {
      ...scopeData.value,
      aggregated,
      timeWindows: {
        ...scopeData.value.timeWindows,
        [op]: timeWindows,
      },
      kpi: {
        ...scopeData.value.kpi,
        [op]: { ...kpi, latencyTotal: 0 },
      },
    }
  }

  const loadTrendSection = async (op: 'get' | 'set', pct: string) => {
    const asset = selectedAsset.value
    if (!asset) return

    const latencyKey = `${op}:${pct}:${trendScale.value}`
    let latency = sectionCaches.latency.get(latencyKey)
    if (!latency) {
      const latencyLogId = scopeTasks.value[0]?.id
      latency = await fetchLatencyMetrics(asset.id, op, pct, latencyLogId, trendScale.value)
      sectionCaches.latency.set(latencyKey, latency)
    }

    let topSlow = sectionCaches.topSlow.get(op)
    if (!topSlow) {
      topSlow = await fetchTopSlow(asset.id, op)
      sectionCaches.topSlow.set(op, topSlow)
    }

    let abnormal = sectionCaches.abnormal.get(op)
    if (!abnormal) {
      abnormal = await fetchAbnormalTraces(asset.id, op)
      sectionCaches.abnormal.set(op, abnormal)
    }
    if (overlapLoadedFor.latency !== op) {
      const traceIds = (abnormal?.rows ?? [])
        .map((row: any) => row.trace_id)
        .filter((id: string | undefined): id is string => !!id)
      if (traceIds.length > 0) {
        try {
          const faultResult = await fetchFaultTracesByTraceIds(asset.id, traceIds)
          latencyTraceIdsWithFault[op] = new Set(
            (faultResult.trace_failure_event_results ?? [])
              .map((row: any) => row.trace_id)
              .filter(Boolean),
          )
        } catch {
          latencyTraceIdsWithFault[op] = new Set()
        }
      } else {
        latencyTraceIdsWithFault[op] = new Set()
      }
      overlapLoadedFor.latency = op
    }

    const pctKey = pct as 'p99' | 'p9999' | 'pmax' | 'ave'
    scopeData.value = {
      ...scopeData.value,
      latency: {
        ...scopeData.value.latency,
        [op]: { ...scopeData.value.latency[op], [pctKey]: latency },
      },
      topSlow: topSlow.rows,
      abnormal: abnormal.rows,
    }
  }

  const loadFaultSection = async (op: 'get' | 'set') => {
    const asset = selectedAsset.value
    if (!asset) return

    let faultChart = sectionCaches.faultChart.get(op)
    if (!faultChart) {
      faultChart = await fetchFaultChart(asset.id, op)
      sectionCaches.faultChart.set(op, faultChart)
    }

    let faultTraces = sectionCaches.faultTraces.get(op)
    if (!faultTraces) {
      faultTraces = await fetchFaultTraces(asset.id, op)
      sectionCaches.faultTraces.set(op, faultTraces)
    }
    if (overlapLoadedFor.fault !== op) {
      const traceIds = (faultTraces?.rows ?? [])
        .map((row: any) => row.trace_id)
        .filter((id: string | undefined): id is string => !!id)
      if (traceIds.length > 0) {
        try {
          const latencyResult = await fetchLatencyTracesByTraceIds(asset.id, traceIds)
          faultTraceIdsWithLatency[op] = new Set(
            (latencyResult.log_parse_results ?? []).map((row: any) => row.trace_id).filter(Boolean),
          )
        } catch {
          faultTraceIdsWithLatency[op] = new Set()
        }
      } else {
        faultTraceIdsWithLatency[op] = new Set()
      }
      overlapLoadedFor.fault = op
    }

    scopeData.value = {
      ...scopeData.value,
      faultChart,
      faultTraces: faultTraces.rows,
      kpi: {
        ...scopeData.value.kpi,
        faultTraceSetTotal: faultTraces.total,
        faultSetTotal: Object.keys(faultChart).length,
      },
    }
  }

  // ---------- BRPC 接口监控（真实后端 /brpc_profiling） ----------

  const brpcScopeTasks = computed(() =>
    logFiles.value.filter((file) => file.log_type === 'brpc' && isSuccess(file)),
  )
  const brpcInterfaces = ref<any[]>([])
  const brpcTrend = ref<{ times: string[]; success: number[]; p99: number[] }>({
    times: [],
    success: [],
    p99: [],
  })
  const brpcLoading = ref(false)
  const brpcMonitorError = ref('')

  const loadBrpcData = async () => {
    const asset = selectedAsset.value
    if (!asset) return
    brpcLoading.value = true
    brpcMonitorError.value = ''
    try {
      const allRows: any[] = []
      for (const log of brpcScopeTasks.value) {
        try {
          const result = await fetchBrpcProfiling(log.id)
          allRows.push(...(result.rows ?? []))
        } catch {
          // 单个日志无 profiling 结果时跳过
        }
      }

      const ifaceMap = new Map<string, any>()
      const timeMap = new Map<string, { req: number; ok: number; p99: number }>()
      for (const row of allRows) {
        const iface = row.interface_name
        const ts = row.timestamp
        if (!iface) continue
        const req = (row.success_count ?? 0) + (row.failure_count ?? 0)
        const ok = row.success_count ?? 0
        const p99ms = (row.p99_ns ?? 0) / 1e6
        if (!ifaceMap.has(iface)) {
          ifaceMap.set(iface, {
            name: iface,
            requestCount: 0,
            successCount: 0,
            failureCount: 0,
            avg_ns: 0,
            p99_ns: 0,
            max_ns: 0,
          })
        }
        const item = ifaceMap.get(iface)
        item.requestCount += req
        item.successCount += ok
        item.failureCount += row.failure_count ?? 0
        item.avg_ns = Math.max(item.avg_ns, row.avg_ns ?? 0)
        item.p99_ns = Math.max(item.p99_ns, row.p99_ns ?? 0)
        item.max_ns = Math.max(item.max_ns, row.max_ns ?? 0)
        if (ts) {
          const key = String(ts).slice(0, 19)
          if (!timeMap.has(key)) timeMap.set(key, { req: 0, ok: 0, p99: 0 })
          const bucket = timeMap.get(key)!
          bucket.req += req
          bucket.ok += ok
          bucket.p99 = Math.max(bucket.p99, p99ms)
        }
      }

      brpcInterfaces.value = [...ifaceMap.values()]
        .map((item) => ({
          ...item,
          successRate: item.requestCount
            ? +((item.successCount / item.requestCount) * 100).toFixed(2)
            : 0,
          failureRate: item.requestCount
            ? +((item.failureCount / item.requestCount) * 100).toFixed(2)
            : 0,
          status: item.p99_ns / 1e6 > 2 ? '偏高' : '正常',
        }))
        .sort((a, b) => b.requestCount - a.requestCount)

      const times = [...timeMap.keys()].sort()
      brpcTrend.value = {
        times: times.map((time) => formatChartTs(time)),
        success: times.map((time) => {
          const bucket = timeMap.get(time)!
          return bucket.req ? +((bucket.ok / bucket.req) * 100).toFixed(2) : 0
        }),
        p99: times.map((time) => timeMap.get(time)!.p99),
      }
    } catch (error) {
      brpcMonitorError.value = errorText(error)
    } finally {
      brpcLoading.value = false
    }
    await loadBrpcFaultData()
    renderAnalysisModules()
  }

  const brpcKpi = computed(() => {
    const list = brpcInterfaces.value
    return {
      ifaceCount: list.length,
      totalReq: list.reduce((sum, item) => sum + item.requestCount, 0),
      avgSuccess: list.length
        ? +(list.reduce((sum, item) => sum + item.successRate, 0) / list.length).toFixed(2)
        : null,
      p99Max: list.length ? Math.max(...list.map((item) => item.p99_ns)) / 1e6 : null,
      failIface: list.filter((item) => item.status !== '正常').length,
    }
  })

  // ---------- BRPC 通断故障监控（对齐原版功能） ----------

  const brpcMonitorTab = ref<'iface' | 'fault'>('iface')
  const brpcFaultTab = ref<'event' | 'thread'>('event')
  const brpcFaultSelectedLogId = ref('')
  const brpcFaultBatch = ref<any>(null)
  const brpcFaultTimelineSeries = ref<any[]>([])
  const brpcAggregatedEvents = ref<any[]>([])
  const brpcAggregatedEventTotal = ref(0)
  const brpcAggregatedEventPage = ref(1)
  const brpcAbnormalThreads = ref<any[]>([])
  const brpcAbnormalThreadTotal = ref(0)
  const brpcAbnormalThreadPage = ref(1)
  const brpcFaultLoading = ref(false)
  const brpcFaultError = ref('')
  const brpcFaultDetail = ref<any>(null)
  const brpcFaultBatchId = ref('')
  const brpcThreadLogs = ref<any[]>([])
  const brpcThreadLogsLoading = ref(false)
  const brpcThreadLogsError = ref('')
  let brpcThreadLogsRequestSeq = 0
  const brpcFaultPageSize = 10

  const brpcFaultLogOptions = computed(() =>
    brpcScopeTasks.value
      .filter((file) => file.task?.id)
      .map((file) => ({
        id: file.id,
        name: file.name,
        taskId: file.task!.id!,
      })),
  )

  const resolveBrpcFaultBatch = async (logId: string) => {
    const option = brpcFaultLogOptions.value.find((item) => item.id === logId)
    if (!option) throw new Error('所选日志暂无可用的 UBSocket 诊断任务')
    const batchResult = await fetchBrpcBatch(option.taskId)
    const metadataResult = await fetchBrpcBatchMeta(batchResult.batch_id)
    return { batchId: batchResult.batch_id, batch: metadataResult.batch }
  }

  const brpcFaultQueryRange = (batch: any) => {
    const startDate = new Date(String(batch.start_time || '').replace(' ', 'T'))
    const endDate = new Date(String(batch.end_time || '').replace(' ', 'T'))
    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
      throw new Error('UBSocket 诊断批次时间范围无效')
    }
    return { startDate, endDate }
  }

  const renderBrpcFaultTimeline = () => {
    nextTick(() => {
      const el = brpcFaultTimelineRef.value
      if (!el) return
      const chart = getChart(el)
      const seriesList = brpcFaultTimelineSeries.value
      const times = [
        ...new Set(
          seriesList.flatMap((series) =>
            (series.points || []).map((point: any) => point.window_start_time),
          ),
        ),
      ].sort()
      setChartOption(chart, {
        tooltip: { trigger: 'axis' },
        legend: { right: 0, top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 56, right: 20, top: 42, bottom: 42 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(String(time))),
          axisLabel: { fontSize: 10, rotate: 30 },
        },
        yAxis: { type: 'value', name: '故障数', minInterval: 1, axisLabel: { fontSize: 10 } },
        series: seriesList.map((series) => ({
          name: series.interface_name + (series.function_name ? `（${series.function_name}）` : ''),
          type: 'line',
          smooth: true,
          data: times.map((time) => {
            const point = (series.points || []).find((item: any) => item.window_start_time === time)
            return point?.interface_hit_count ?? 0
          }),
          lineStyle: { width: 2 },
        })),
      })
    })
  }

  const loadBrpcFaultData = async () => {
    const logId = brpcFaultSelectedLogId.value || brpcFaultLogOptions.value[0]?.id
    if (!logId) {
      brpcFaultBatch.value = null
      brpcFaultBatchId.value = ''
      brpcFaultTimelineSeries.value = []
      brpcAggregatedEvents.value = []
      brpcAggregatedEventTotal.value = 0
      brpcAbnormalThreads.value = []
      brpcAbnormalThreadTotal.value = 0
      return
    }
    brpcFaultSelectedLogId.value = logId
    brpcFaultLoading.value = true
    brpcFaultError.value = ''
    try {
      const { batchId, batch } = await resolveBrpcFaultBatch(logId)
      brpcFaultBatch.value = batch
      brpcFaultBatchId.value = batchId
      const { startDate, endDate } = brpcFaultQueryRange(batch)
      const [timelineResult, eventsResult, threadsResult] = await Promise.all([
        fetchBrpcInterfaceTimeline(batchId, startDate, endDate),
        fetchBrpcPodEvents(
          batchId,
          startDate,
          endDate,
          brpcAggregatedEventPage.value,
          brpcFaultPageSize,
        ),
        fetchBrpcAbnormalThreads(
          batchId,
          startDate,
          endDate,
          brpcAbnormalThreadPage.value,
          brpcFaultPageSize,
        ),
      ])
      brpcFaultTimelineSeries.value = timelineResult.series ?? []
      brpcAggregatedEvents.value = eventsResult.events ?? []
      brpcAggregatedEventTotal.value = eventsResult.total ?? 0
      brpcAbnormalThreads.value = threadsResult.threads ?? []
      brpcAbnormalThreadTotal.value = threadsResult.total ?? 0
      renderBrpcFaultTimeline()
    } catch (error) {
      brpcFaultError.value = errorText(error)
    } finally {
      brpcFaultLoading.value = false
    }
  }

  const changeBrpcFaultLog = async () => {
    brpcAggregatedEventPage.value = 1
    brpcAbnormalThreadPage.value = 1
    await loadBrpcFaultData()
  }

  const goBrpcFaultEventsPage = async (pageNum: number) => {
    brpcAggregatedEventPage.value = pageNum
    await loadBrpcFaultData()
  }

  const goBrpcFaultThreadsPage = async (pageNum: number) => {
    brpcAbnormalThreadPage.value = pageNum
    await loadBrpcFaultData()
  }

  const brpcFaultEventPages = computed(() =>
    Math.max(1, Math.ceil(brpcAggregatedEventTotal.value / brpcFaultPageSize)),
  )
  const brpcFaultThreadPages = computed(() =>
    Math.max(1, Math.ceil(brpcAbnormalThreadTotal.value / brpcFaultPageSize)),
  )

  const openBrpcFaultDetail = (row: any) => {
    brpcFaultDetail.value = row
    brpcThreadLogs.value = []
    brpcThreadLogsError.value = ''
    // 仅异常 Thread 行（带 thread_key）加载全部运行日志
    if (!row?.thread_key || row?.thread_id == null || !row?.pod_ip) return
    const batch = brpcFaultBatch.value
    const batchId = brpcFaultBatchId.value
    if (!batch || !batchId) return
    const seq = ++brpcThreadLogsRequestSeq
    brpcThreadLogsLoading.value = true
    void (async () => {
      try {
        const { startDate, endDate } = brpcFaultQueryRange(batch)
        const result = await fetchBrpcThreadLogs(batchId, {
          pod_ip: row.pod_ip,
          thread_id: Number(row.thread_id),
          start_time: formatFullTimeLabel(startDate),
          end_time: formatFullTimeLabel(endDate),
          pod_name: row.pod_name || undefined,
        })
        if (seq !== brpcThreadLogsRequestSeq) return
        brpcThreadLogs.value = result.hits ?? []
      } catch (error) {
        if (seq !== brpcThreadLogsRequestSeq) return
        brpcThreadLogsError.value = errorText(error)
      } finally {
        if (seq === brpcThreadLogsRequestSeq) brpcThreadLogsLoading.value = false
      }
    })()
  }

  const brpcEventHitTotal = (event: any) =>
    (event.interface_hits || []).reduce(
      (sum: number, hit: any) => sum + (hit.interface_hit_count || 0),
      0,
    )

  // ---------- 异常概览（拓扑 / Pod 分析） ----------

  const allMetrics = [
    { key: 'total_latency_us', label: '总时延', cat: 'SDK' },
    { key: 'sdk_processing_us', label: 'SDK处理', cat: 'SDK' },
    { key: 'master_processing_us', label: 'Master处理', cat: 'Master/Worker' },
    { key: 'worker_access_latency_us', label: 'Worker Access时延', cat: 'Master/Worker' },
    { key: 'remote_worker_internal_us', label: 'Remote Worker内部', cat: 'Master/Worker' },
    { key: 'local_worker_internal_us', label: 'Local Worker内部', cat: 'Master/Worker' },
    {
      key: 'local_worker_internal_active_us',
      label: 'Local Worker内部时间2',
      cat: 'Master/Worker',
    },
    { key: 'sdk_rpc_network_us', label: 'SDK RPC网络', cat: 'RPC远端' },
    { key: 'sdk_rpc_framework_us', label: 'SDK RPC框架', cat: 'RPC远端' },
    { key: 'sdk_rpc_total_us', label: 'SDK RPC总时延', cat: 'RPC远端' },
    { key: 'master_rpc_network_us', label: 'Master RPC网络', cat: 'RPC远端' },
    { key: 'master_rpc_framework_us', label: 'Master RPC框架', cat: 'RPC远端' },
    { key: 'master_rpc_total_us', label: 'Master RPC总时延', cat: 'RPC远端' },
    { key: 'remote_worker_rpc_network_us', label: 'Remote Worker RPC网络', cat: 'RPC远端' },
    { key: 'remote_worker_rpc_framework_us', label: 'Remote Worker RPC框架', cat: 'RPC远端' },
    { key: 'remote_worker_rpc_total_us', label: 'Remote Worker RPC总时延', cat: 'RPC远端' },
    { key: 'urma_processing_us', label: 'URMA处理', cat: 'URMA' },
    { key: 'urma_inflight_max', label: 'URMA并发数', cat: 'URMA' },
    { key: 'remote_worker_processing_us', label: 'Remote Worker处理', cat: 'URMA' },
    { key: 'client_master_rpc_network_us', label: 'Client Master RPC网络', cat: 'Client Direct' },
    { key: 'client_master_rpc_framework_us', label: 'Client Master RPC框架', cat: 'Client Direct' },
    { key: 'client_master_rpc_total_us', label: 'Client Master RPC总时延', cat: 'Client Direct' },
    { key: 'client_remote_rpc_network_us', label: 'Client Remote RPC网络', cat: 'Client Direct' },
    { key: 'client_remote_rpc_framework_us', label: 'Client Remote RPC框架', cat: 'Client Direct' },
    { key: 'client_remote_rpc_total_us', label: 'Client Remote RPC总时延', cat: 'Client Direct' },
  ]

  const metricCats = computed(() => {
    const cats: Record<string, Array<{ key: string; label: string; cat: string }>> = {}
    allMetrics.forEach((metric) => {
      cats[metric.cat] = cats[metric.cat] ?? []
      cats[metric.cat]!.push(metric)
    })
    return Object.entries(cats).map(([name, metrics]) => ({ name, metrics }))
  })

  const selectedMetrics = ref([
    'total_latency_us',
    'sdk_processing_us',
    'master_processing_us',
    'worker_access_latency_us',
    'urma_processing_us',
    'urma_inflight_max',
    'remote_worker_processing_us',
  ])

  const metricLabel = (key: string) => allMetrics.find((metric) => metric.key === key)?.label || key

  const metricCategoryColor: Record<string, string> = {
    SDK: '#5470c6',
    'Master/Worker': '#00B365',
    RPC远端: '#fc8452',
    URMA: '#8B5CF6',
    'Client Direct': '#bda29a',
  }
  const metricCategoryOf = (key: string) =>
    allMetrics.find((metric) => metric.key === key)?.cat || ''
  const metricCategoryColorOf = (key: string) =>
    metricCategoryColor[metricCategoryOf(key)] || '#94a3b8'
  const metricIsCount = (key: string) => key === 'urma_inflight_max'
  const metricUnit = (key: string) => (metricIsCount(key) ? '个' : 'ms')
  const metricValueText = (value: number | null | undefined, key: string) => {
    if (value == null || !Number.isFinite(value) || value <= 0) return '-'
    if (metricIsCount(key)) return value.toFixed(1)
    // µs → ms
    return (value / 1000).toFixed(2)
  }

  const overview = reactive({ topK: 10, operation: '', sortBy: '', statType: 'p99' })
  const showPodIpCb = ref(false)
  const podIpCbPage = ref(1)
  const podIpCbPageSize = 20

  const timeBuckets = computed(() => scopeData.value.timeWindows[realOp.value] || [])
  const epochOf = (value: string) => tsToEpochMs(String(value))

  const overviewScaleOptions = [
    { value: 10, label: '10秒' },
    { value: 60, label: '1分钟' },
    { value: 600, label: '10分钟' },
    { value: 3600, label: '1小时' },
  ]
  const overviewScale = ref(600)
  const anomalyRef = ref<HTMLElement | null>(null)
  // 粒度下拉是 AnalysisFilter.scaleSec 的写入口
  watch(overviewScale, (value) => {
    latencyFilter.scaleSec.value = value as 10 | 60 | 600 | 3600
  })

  /**
   * 两层时间数据（P0.3）：
   * - timelineData（timeBuckets）：全域导航数据，不随 time 选择自我收窄
   * - analysisWindowBuckets：按 time 重新请求的数据，驱动拓扑/排名/Pod 表/inspector
   * time.mode = 'all' 时复用 timelineData。
   */
  const analysisWindowBuckets = ref<TimeWindowBucket[] | null>(null)
  const analysisWindowLoading = ref(false)
  let analysisWindowSeq = 0
  let analysisWindowTimer: ReturnType<typeof setTimeout> | null = null

  const loadAnalysisWindow = async () => {
    const window = latencyFilter.timeWindow.value
    if (!window) {
      analysisWindowBuckets.value = null
      return
    }
    const asset = selectedAsset.value
    if (!asset) return
    const seq = ++analysisWindowSeq
    analysisWindowLoading.value = true
    try {
      const { rows } = await fetchTimeWindowAggregated(asset.id, realOp.value, {
        interval: overviewScale.value,
        startTime: epochMsToTs(window.start),
        endTime: epochMsToTs(window.end),
      })
      if (seq === analysisWindowSeq) analysisWindowBuckets.value = rows
    } catch (error) {
      if (seq === analysisWindowSeq) {
        analysisWindowBuckets.value = []
        overviewError.value = errorText(error)
      }
    } finally {
      if (seq === analysisWindowSeq) analysisWindowLoading.value = false
    }
  }

  // dataZoom 防抖：快速缩放时只加载最后一次选择
  const scheduleAnalysisWindow = () => {
    if (analysisWindowTimer) clearTimeout(analysisWindowTimer)
    analysisWindowTimer = setTimeout(() => void loadAnalysisWindow(), 300)
  }

  const clearAnalysisTime = () => {
    latencyFilter.clearTime()
    if (analysisWindowTimer) clearTimeout(analysisWindowTimer)
    void loadAnalysisWindow()
  }

  /** 当前范围（time 选择）内的桶：all 复用全域，range/bucket 用服务端窗口结果 */
  const analysisWindowData = computed(() => analysisWindowBuckets.value ?? timeBuckets.value)

  const timeRangeLabel = computed(() => latencyFilter.timeLabel.value)

  /** 按当前窗过滤后的全域桶（用于时间轴高亮等本地场景） */
  const filteredTimeBuckets = computed(() => {
    const window = latencyFilter.timeWindow.value
    if (!window) return timeBuckets.value
    return timeBuckets.value.filter((bucket) => {
      const t = epochOf(bucket.start_time)
      return t >= window.start && t < window.end
    })
  })

  const activePairs = computed(() => toAggregatedPairs(analysisWindowData.value, realOp.value))

  /** 当前可用的指标：跨所有时段任一 ip_pair 出现过合法值（µs/计数） */
  const availableMetrics = computed(() =>
    allMetrics.filter((metric) =>
      timeBuckets.value.some((bucket) =>
        (bucket.ip_pairs ?? []).some((pair) => {
          const value = pair[`ave_${metric.key}`]
          return typeof value === 'number' && Number.isFinite(value) && value > 0
        }),
      ),
    ),
  )
  const availableMetricCats = computed(() => {
    const present = new Set(availableMetrics.value.map((metric) => metric.key))
    return metricCats.value
      .map((cat) => ({
        ...cat,
        metrics: cat.metrics.filter((metric) => present.has(metric.key)),
      }))
      .filter((cat) => cat.metrics.length > 0)
  })

  /** 时段异常强度（时间轴数据源 = 全域导航数据） */
  const statFieldMap: Record<string, string> = {
    ave: 'ave_total_latency',
    p95: 'p95_total_latency',
    p99: 'p99_total_latency',
    min: 'min_total_latency',
    max: 'max_total_latency',
  }
  const overviewStatField = computed(() => statFieldMap[overview.statType] || 'ave_total_latency')

  const anomalySeries = computed(() =>
    timeBuckets.value.map((bucket) => ({
      time: epochOf(bucket.start_time),
      start: bucket.start_time,
      end: bucket.end_time,
      label: formatChartTs(bucket.start_time),
      total: bucket.total_cnt ?? 0,
      anomaly: bucket.anomaly_cnt ?? 0,
      p99: bucket.p99_total_latency ?? null,
      statValue: bucket[overviewStatField.value] ?? null,
    })),
  )

  const podIpStats = computed(() => {
    const map = new Map<string, any>()
    activePairs.value.forEach((pair) => {
      ;(
        [
          ['src', pair.src],
          ['dst', pair.dst],
        ] as const
      ).forEach(([role, ip]) => {
        if (!map.has(ip)) {
          map.set(ip, {
            ip,
            total: 0,
            anomaly: 0,
            srcCount: 0,
            dstCount: 0,
            get: 0,
            set: 0,
            qm: 0,
            ut: 0,
            ul: 0,
            c2w: 0,
            w2w: 0,
            metricSum: {} as Record<string, number>,
            metricDen: {} as Record<string, number>,
          })
        }
        const stat = map.get(ip)
        stat.total += pair.total
        stat.anomaly += pair.anomaly
        if (role === 'src') stat.srcCount += pair.total
        else stat.dstCount += pair.total
        stat.get += pair.get
        stat.set += pair.set
        stat.qm += (pair.queryMeta || 0) * pair.total
        stat.ut += (pair.urmaTotal || 0) * pair.total
        stat.ul += (pair.urmaLink || 0) * pair.total
        stat.c2w += (pair.c2w || 0) * pair.total
        stat.w2w += (pair.w2w || 0) * pair.total
        const metricValues = pair.metricValues || {}
        Object.entries(metricValues).forEach(([metricKey, value]) => {
          if (typeof value === 'number' && Number.isFinite(value)) {
            stat.metricSum[metricKey] = (stat.metricSum[metricKey] || 0) + value * pair.total
            stat.metricDen[metricKey] = (stat.metricDen[metricKey] || 0) + pair.total
          }
        })
      })
    })
    const format = (value: number) => (Number.isFinite(value) && value > 0 ? value.toFixed(1) : '-')
    return [...map.values()].map((stat) => {
      const metricValues: Record<string, number | null> = {}
      Object.keys(stat.metricSum).forEach((metricKey) => {
        const den = stat.metricDen[metricKey]
        metricValues[metricKey] = den ? stat.metricSum[metricKey] / den : null
      })
      return {
        ...stat,
        queryMeta: format(stat.qm / stat.total),
        urmaTotal: format(stat.ut / stat.total),
        urmaLink: format(stat.ul / stat.total),
        c2w: format(stat.c2w / stat.total),
        w2w: format(stat.w2w / stat.total),
        metricValues,
        anomalyRate: stat.total ? +((stat.anomaly / stat.total) * 100).toFixed(1) : 0,
      }
    })
  })

  const uniquePodIps = computed(() => podIpStats.value.map((stat) => stat.ip))
  const podIpCbPages = computed(() => Math.ceil(uniquePodIps.value.length / podIpCbPageSize))
  const pagedPodIpsCb = computed(() =>
    uniquePodIps.value.slice(
      (podIpCbPage.value - 1) * podIpCbPageSize,
      podIpCbPage.value * podIpCbPageSize,
    ),
  )

  const filteredPodStats = computed(() => {
    let list = podIpStats.value
    if (overview.sortBy) {
      const parts = overview.sortBy.split('_')
      const field = parts[0] ?? ''
      const order = parts[1] ?? ''
      list = [...list].sort((a, b) =>
        order === 'desc' ? (b[field] || 0) - (a[field] || 0) : (a[field] || 0) - (b[field] || 0),
      )
    } else {
      // 默认按异常数排序（P0.6）：「结果数」不表达故障严重度
      list = [...list].sort((a, b) => b.anomaly - a.anomaly || b.total - a.total)
    }
    if (overview.topK > 0 && overview.topK < list.length) {
      list = list.slice(0, overview.topK)
    }
    return list
  })

  const podPage = ref(1)
  const podPageSize = 8
  const podPages = computed(() => Math.ceil(filteredPodStats.value.length / podPageSize))
  const pagedPodStats = computed(() =>
    filteredPodStats.value.slice((podPage.value - 1) * podPageSize, podPage.value * podPageSize),
  )

  const kpiData = computed(() => {
    const kpi = scopeData.value.kpi[realOp.value] || {
      traceTotal: 0,
      anomalyTotal: 0,
      podCount: 0,
    }
    if (analysisTab.value === 'disconnect') {
      const codes = Object.keys(scopeData.value.faultChart || {})
      const endpoints = new Set<string>()
      const endpointFaults = new Map<string, number>()
      faultTraces.value.forEach((trace) => {
        ;[trace.src_ip, trace.dst_ip].forEach((ip) => {
          if (!ip) return
          endpoints.add(ip)
          endpointFaults.set(ip, (endpointFaults.get(ip) || 0) + 1)
        })
      })
      const worst = [...endpointFaults.entries()].sort((a, b) => b[1] - a[1])[0]
      return {
        totalTraces: scopeData.value.kpi.faultTraceSetTotal || 0,
        anomalyTraces: codes.length,
        anomalyRate: '—' as string | number,
        endpointCount: endpoints.size,
        worstEndpoint: worst?.[0] ?? '-',
        worstEndpointAnomaly: worst?.[1] ?? 0,
      }
    }
    const rate = kpi.traceTotal ? ((kpi.anomalyTotal / kpi.traceTotal) * 100).toFixed(1) : '0.0'
    // 「当前范围端点数 / 最差端点」：跟随 time/dimensions，不随 focus（P0.6 口径）
    const endpointSet = new Set<string>()
    const endpointAnomaly = new Map<string, number>()
    activePairs.value.forEach((pair) => {
      endpointSet.add(pair.src)
      endpointSet.add(pair.dst)
      endpointAnomaly.set(pair.src, (endpointAnomaly.get(pair.src) || 0) + pair.anomaly)
      endpointAnomaly.set(pair.dst, (endpointAnomaly.get(pair.dst) || 0) + pair.anomaly)
    })
    const worst = [...endpointAnomaly.entries()].sort((a, b) => b[1] - a[1])[0]
    return {
      totalTraces: kpi.traceTotal,
      anomalyTraces: kpi.anomalyTotal,
      anomalyRate: rate,
      endpointCount: endpointSet.size,
      worstEndpoint: worst?.[0] ?? '-',
      worstEndpointAnomaly: worst?.[1] ?? 0,
    }
  })

  const resetOverviewFilter = () => {
    overview.topK = 10
    overview.operation = ''
    overview.sortBy = ''
    overview.statType = 'p99'
    latencyFilter.reset()
    overviewScale.value = 600
    analysisWindowBuckets.value = null
    topoShowAll.value = false
    podIpCbPage.value = 1
    podPage.value = 1
  }

  // ---------- 指标趋势 / 最慢请求 / 异常 Trace ----------

  const trendMetrics = (
    [
      ['total_latency_us', '总时延', '#d32f2f'],
      ['sdk_processing_us', 'SDK处理', '#5470c6'],
      ['master_processing_us', 'Master处理', '#91cc75'],
      ['worker_access_latency_us', 'Worker Access时延', '#fac858'],
      ['remote_worker_internal_us', 'Remote Worker内部', '#ee6666'],
      ['local_worker_internal_us', 'Local Worker内部', '#73c0de'],
      ['local_worker_internal_active_us', 'Local Worker内部时间2', '#3ba272'],
      ['sdk_rpc_network_us', 'SDK RPC网络', '#fc8452'],
      ['sdk_rpc_framework_us', 'SDK RPC框架', '#9a60b4'],
      ['sdk_rpc_total_us', 'SDK RPC总时延', '#ea7ccc'],
      ['master_rpc_network_us', 'Master RPC网络', '#ff9f7f'],
      ['master_rpc_framework_us', 'Master RPC框架', '#ffdb5c'],
      ['master_rpc_total_us', 'Master RPC总时延', '#c23531'],
      ['remote_worker_rpc_network_us', 'Remote Worker RPC网络', '#2f4554'],
      ['remote_worker_rpc_framework_us', 'Remote Worker RPC框架', '#61a0a8'],
      ['remote_worker_rpc_total_us', 'Remote Worker RPC总时延', '#bda29a'],
      ['urma_processing_us', 'URMA+UDMA+交换机+OS处理', '#6e7074'],
      ['urma_inflight_max', 'URMA并发数', '#749f83'],
      ['remote_worker_processing_us', 'Remote Worker处理', '#ca8622'],
      ['client_master_rpc_network_us', 'Client Master RPC网络', '#bda29a'],
      ['client_master_rpc_framework_us', 'Client Master RPC框架', '#6e7074'],
      ['client_master_rpc_total_us', 'Client Master RPC总时延', '#546570'],
      ['client_remote_rpc_network_us', 'Client Remote RPC网络', '#c4ccd3'],
      ['client_remote_rpc_framework_us', 'Client Remote RPC框架', '#f05b72'],
      ['client_remote_rpc_total_us', 'Client Remote RPC总时延', '#d53a35'],
    ] as Array<[string, string, string]>
  ).map(([key, label, color]) => ({ key, label, color }))

  const trendPercentileOptions = [
    { value: 'p99', label: 'P99', abnormalThreshold: latencyThresholds.p99 },
    { value: 'p9999', label: 'P99.99', abnormalThreshold: latencyThresholds.p9999 },
    { value: 'pmax', label: 'Pmax', abnormalThreshold: latencyThresholds.pmax },
    { value: 'ave', label: '均值', abnormalThreshold: latencyThresholds.ave },
  ]

  const trendScaleOptions = [
    { value: 10, label: '10秒' },
    { value: 60, label: '1分钟' },
    { value: 600, label: '10分钟' },
    { value: 3600, label: '1小时' },
  ]

  const trendPercentile = ref('p99')
  const trendScale = ref(60)
  const trendCenter = ref<number | null>(null)
  const trendVisible = ref(new Set(['total_latency_us', 'sdk_processing_us', 'urma_processing_us']))
  // 点击数据点后显示的半窗口（单位：桶）。15 桶 × 当前尺度，形成清晰可辨的聚焦范围。
  const trendHalfSpan: Record<number, number> = { 10: 15, 60: 15, 600: 15, 3600: 15 }
  const trendRange = computed(() => {
    if (trendCenter.value == null) return null
    const half = (trendHalfSpan[trendScale.value] ?? 60) * trendScale.value * 1000
    return {
      center: trendCenter.value,
      start: trendCenter.value - half,
      end: trendCenter.value + half,
    }
  })
  const trendAnomalyHint = computed(() => {
    const config = trendPercentileOptions.find((item) => item.value === trendPercentile.value)
    return `🔴 红色区域 = ${config?.label ?? ''} 总时延 > ${config?.abnormalThreshold ?? 5}ms`
  })

  const selectAllTrend = () => {
    trendVisible.value = new Set(trendMetrics.map((metric) => metric.key))
  }
  const resetTrend = () => {
    trendCenter.value = null
  }
  const clearTrend = () => {
    trendVisible.value = new Set<string>()
  }
  const toggleTrendSeries = (key: string) => {
    const next = new Set(trendVisible.value)
    if (next.has(key)) {
      next.delete(key)
    } else {
      next.add(key)
    }
    trendVisible.value = next
  }

  const trendChartData = computed(() => {
    const percentile = trendPercentile.value as 'p99' | 'p9999' | 'pmax' | 'ave'
    return scopeData.value.latency[realOp.value]?.[percentile] || []
  })

  const formatFullTime = (time: number) => {
    const date = new Date(time)
    const pad = (value: number) => String(value).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  }

  const trendBuckets = computed(() => {
    const config = trendPercentileOptions.find((item) => item.value === trendPercentile.value)
    const points = trendChartData.value
      .map((point) => {
        const time = point.time ?? point.timestamp ?? point.created_at
        const date = new Date(String(time || '').replace(' ', 'T'))
        return { date, values: point }
      })
      .filter((point) => !Number.isNaN(point.date.getTime()))
    if (!points.length) return []
    const bucketMs = trendScale.value * 1000
    const map = new Map<number, Record<string, number>>()
    points.forEach((point) => {
      const time = point.date.getTime()
      const bucket = bucketMs > 0 ? Math.floor(time / bucketMs) * bucketMs : time
      if (!map.has(bucket)) map.set(bucket, {})
      const values = map.get(bucket)!
      trendMetrics.forEach((metric) => {
        let value = point.values[metric.key]
        if (typeof value === 'number' && Number.isFinite(value)) {
          if (metric.key.endsWith('_us')) value = value / 1000
          values[metric.key] = Math.max(values[metric.key] || 0, value)
        }
      })
      const totalLatency = point.values.total_latency
      if (typeof totalLatency === 'number' && Number.isFinite(totalLatency)) {
        values.total_latency = totalLatency
      }
    })
    return [...map.keys()]
      .sort((a, b) => a - b)
      .map((time) => {
        const values = map.get(time)!
        return {
          time,
          label: formatFullTime(time),
          values,
          abnormal:
            typeof values.total_latency === 'number' &&
            values.total_latency > (config?.abnormalThreshold ?? 5),
        }
      })
  })

  const topSlowSegmentConfig = [
    { key: 'sdk_processing_us', label: 'SDK处理', color: '#5470c6' },
    { key: 'master_processing_us', label: 'Master处理', color: '#91cc75' },
    { key: 'worker_access_latency_us', label: 'Worker Access时延', color: '#fac858' },
    { key: 'remote_worker_internal_us', label: 'Remote Worker内部', color: '#ee6666' },
    { key: 'local_worker_internal_us', label: 'Local Worker内部', color: '#73c0de' },
    { key: 'sdk_rpc_network_us', label: 'SDK RPC网络', color: '#fc8452' },
    { key: 'sdk_rpc_framework_us', label: 'SDK RPC框架', color: '#9a60b4' },
    { key: 'master_rpc_network_us', label: 'Master RPC网络', color: '#ff9f7f' },
    { key: 'master_rpc_framework_us', label: 'Master RPC框架', color: '#ffdb5c' },
    { key: 'remote_worker_rpc_network_us', label: 'Remote Worker RPC网络', color: '#2f4554' },
    { key: 'remote_worker_rpc_framework_us', label: 'Remote Worker RPC框架', color: '#61a0a8' },
    { key: 'urma_processing_us', label: 'URMA+UDMA+交换机+OS处理', color: '#6e7074' },
    { key: 'urma_inflight_max', label: 'URMA并发数', color: '#749f83', unit: 'count' },
    { key: 'remote_worker_processing_us', label: 'Remote Worker处理', color: '#ca8622' },
    { key: 'client_master_rpc_network_us', label: 'Client Master RPC网络', color: '#bda29a' },
    { key: 'client_master_rpc_framework_us', label: 'Client Master RPC框架', color: '#6e7074' },
    { key: 'client_remote_rpc_network_us', label: 'Client Remote RPC网络', color: '#c4ccd3' },
    { key: 'client_remote_rpc_framework_us', label: 'Client Remote RPC框架', color: '#f05b72' },
  ]

  const slowRows = computed(() => scopeData.value.topSlow || [])
  const slowTotal = computed(() => scopeData.value.kpi[realOp.value].traceTotal || 0)

  const slowChartRows = computed(() =>
    slowRows.value
      .map((row) => {
        const date = new Date(String(row.timestamp || '').replace(' ', 'T'))
        if (Number.isNaN(date.getTime())) return null
        const totalLatency =
          typeof row.total_latency_us === 'number' && Number.isFinite(row.total_latency_us)
            ? row.total_latency_us
            : 0
        if (totalLatency <= 0) return null
        const segments: Record<string, number> = {}
        let displayed = 0
        topSlowSegmentConfig.forEach((segment) => {
          const value =
            typeof row[segment.key] === 'number' && Number.isFinite(row[segment.key])
              ? row[segment.key]
              : 0
          segments[segment.key] = value
          if (segment.unit !== 'count') displayed += value
        })
        return {
          raw: row,
          traceId: row.trace_id || '-',
          timestamp: date.getTime(),
          timestampLabel: formatFullTime(date.getTime()),
          operation: row.operation || currentOp.value,
          totalLatency,
          otherLatency: Math.max(totalLatency - displayed, 0),
          segments,
        }
      })
      .filter((row): row is NonNullable<typeof row> => row !== null)
      .sort((a, b) => a.timestamp - b.timestamp),
  )

  const traceSearch = ref('')
  const traceCluster = ref('')
  const traceClusters = computed(() =>
    [
      ...new Set((scopeData.value.abnormal || []).map((row) => row.cluster_name).filter(Boolean)),
    ].sort(),
  )
  const traceRows = computed(() => {
    let list = scopeData.value.abnormal || []
    const keyword = traceSearch.value.trim().toLowerCase()
    if (keyword) {
      list = list.filter(
        (row) =>
          String(row.trace_id || '')
            .toLowerCase()
            .includes(keyword) ||
          (row.pod_ips || []).some((ip: string) => String(ip).toLowerCase().includes(keyword)),
      )
    }
    if (traceCluster.value) list = list.filter((row) => row.cluster_name === traceCluster.value)
    return list
  })

  const traceBreakdownKeys = [
    { key: 'sdk_processing_us', label: 'SDK处理', color: '#5470c6' },
    { key: 'master_processing_us', label: 'Master处理', color: '#91cc75' },
    { key: 'worker_access_latency_us', label: 'Worker Access', color: '#fac858' },
    { key: 'remote_worker_internal_us', label: 'Remote Worker内部', color: '#ee6666' },
    { key: 'local_worker_internal_us', label: 'Local Worker内部', color: '#73c0de' },
    { key: 'sdk_rpc_network_us', label: 'SDK RPC网络', color: '#ea7ccc' },
    { key: 'sdk_rpc_framework_us', label: 'SDK RPC框架', color: '#bda29a' },
    { key: 'master_rpc_network_us', label: 'Master RPC网络', color: '#c23531' },
    { key: 'master_rpc_framework_us', label: 'Master RPC框架', color: '#ff9f7f' },
    { key: 'urma_processing_us', label: 'URMA+UDMA+交换机+OS处理', color: '#6e7074' },
    { key: 'remote_worker_processing_us', label: 'Remote Worker处理', color: '#ca8622' },
  ]

  const traceSegments = (row: any) => {
    const total = Number(row.total_latency_us) || 0
    const segments: any[] = []
    traceBreakdownKeys.forEach((item) => {
      const value = Number(row[item.key]) || 0
      if (value > 0) {
        segments.push({
          key: item.key,
          label: item.label,
          shortLabel: item.label.replace('+UDMA+交换机+OS', ''),
          value,
          color: item.color,
          width: total ? Math.max(1, (value / total) * 100) : 0,
        })
      }
    })
    return segments
  }

  const traceBreakdownTitle = (row: any) => {
    const segments = traceSegments(row)
    if (!segments.length) return '各阶段时延分解：暂无阶段数据'
    return (
      '各阶段时延分解（µs）\n' +
      segments.map((s) => `${s.label} ${s.value.toFixed(0)}µs`).join('\n')
    )
  }

  /** POD 级各阶段时延分解：复用趋势页的关键阶段 + 颜色，仅展示已勾选且有数据的阶段 */
  const podBreakdownSegments = (stat: any) => {
    const selected = new Set(selectedMetrics.value)
    const all = traceBreakdownKeys
      .filter((key) => selected.has(key.key))
      .map((key) => ({
        key: key.key,
        label: key.label,
        color: key.color,
        value: Number(stat.metricValues?.[key.key]) || 0,
      }))
      .filter((item) => item.value > 0)
      .sort((a, b) => b.value - a.value)
    if (!all.length) return []
    // 各阶段为相互包含的独立跨度（非可加分区），条长相对该 Pod 最大阶段，避免伪“占比”。
    const maxVal = all[0]?.value || 1
    const top = all.slice(0, 6)
    const segments = top.map((item) => ({
      ...item,
      shortLabel: item.label.replace('+UDMA+交换机+OS', ''),
      valueMs: item.value / 1000,
      width: Math.max(2, (item.value / maxVal) * 100),
    }))
    return segments
  }

  const podBreakdownTotal = (stat: any) => {
    const total = Number(stat.metricValues?.['total_latency_us']) || 0
    return total > 0 ? (total / 1000).toFixed(2) : '-'
  }

  const podBreakdownTitle = (stat: any) => {
    const segments = podBreakdownSegments(stat)
    if (!segments.length) return '各阶段时延分解：暂无阶段数据'
    return (
      '各阶段时延（ms，各阶段为相互包含的独立测量，非可加分区）\n' +
      segments.map((s) => `${s.label} ${s.valueMs.toFixed(2)}ms`).join('\n')
    )
  }

  /** 请求链路 + 嵌套包含 的阶段结构（用于单元格内的树形呈现） */
  const podStageTree = (stat: any) => podStageTreeFromMetricValues(stat.metricValues)

  const podStageTreeFromMetricValues = (metricValues: Record<string, number | null> | null) => {
    const mv = (key: string) => {
      const v = Number(metricValues?.[key])
      return Number.isFinite(v) && v > 0 ? v : null
    }
    const workerInternal = Math.max(
      mv('remote_worker_internal_us') ?? 0,
      mv('local_worker_internal_us') ?? 0,
    )
    const colorOf = (key: string) =>
      traceBreakdownKeys.find((k) => k.key === key)?.color ||
      metricCategoryColorOf(key) ||
      '#94a3b8'

    const groups: Array<{
      level: number
      key: string
      label: string
      value: number | null
      children?: Array<{ key: string; label: string; value: number | null }>
    }> = []
    const push = (
      level: number,
      key: string,
      label: string,
      value: number | null,
      children?: Array<{ key: string; label: string; value: number | null }>,
    ) => {
      if (value == null) return
      groups.push({ level, key, label, value, children })
    }

    push(0, 'sdk_processing_us', 'SDK处理', mv('sdk_processing_us'))
    push(0, 'sdk_rpc_total_us', 'SDK RPC', mv('sdk_rpc_total_us'), [
      { key: 'sdk_rpc_network_us', label: '网络', value: mv('sdk_rpc_network_us') },
      { key: 'sdk_rpc_framework_us', label: '框架', value: mv('sdk_rpc_framework_us') },
    ])
    push(0, 'master_rpc_total_us', 'Master RPC', mv('master_rpc_total_us'), [
      { key: 'master_rpc_network_us', label: '网络', value: mv('master_rpc_network_us') },
      { key: 'master_rpc_framework_us', label: '框架', value: mv('master_rpc_framework_us') },
    ])
    push(0, 'worker_access_latency_us', 'Worker Access', mv('worker_access_latency_us'), [
      {
        key: '__worker_internal',
        label: 'Worker 内部',
        value: workerInternal > 0 ? workerInternal : null,
      },
      { key: 'urma_processing_us', label: 'URMA', value: mv('urma_processing_us') },
    ])

    // 展平为带缩进层级的行，并取最大值为条长基准
    const rows: Array<{
      level: number
      key: string
      label: string
      valueMs: number
      color: string
      width: number
    }> = []
    const flatten = (
      level: number,
      key: string,
      label: string,
      value: number | null,
      children?: Array<{ key: string; label: string; value: number | null }>,
    ) => {
      if (value == null) return
      rows.push({ level, key, label, valueMs: value / 1000, color: colorOf(key), width: 0 })
      children?.forEach((child) => {
        if (child.value != null) flatten(level + 1, child.key, child.label, child.value)
      })
    }
    groups.forEach((g) => flatten(g.level, g.key, g.label, g.value, g.children))
    const maxVal = rows.reduce((max, r) => Math.max(max, r.valueMs), 0) || 1
    return rows.map((r) => ({ ...r, width: Math.max(2, (r.valueMs / maxVal) * 100) }))
  }

  const podStageTreeTitle = (stat: any) => {
    const rows = podStageTree(stat)
    if (!rows.length) return '暂无阶段数据'
    return (
      '阶段时延（ms，缩进=包含关系；各阶段为独立测量，非可加）\n' +
      rows.map((r) => `${'  '.repeat(r.level)}${r.label} ${r.valueMs.toFixed(2)}ms`).join('\n')
    )
  }

  const _podStageTreeTitleFromMetricValues = (
    metricValues: Record<string, number | null> | null,
  ) => {
    const rows = podStageTreeFromMetricValues(metricValues)
    if (!rows.length) return '暂无阶段数据'
    return (
      '阶段时延（ms，缩进=包含关系；各阶段为独立测量，非可加）\n' +
      rows.map((r) => `${'  '.repeat(r.level)}${r.label} ${r.valueMs.toFixed(2)}ms`).join('\n')
    )
  }

  /** 流水线式阶段网格：主顺序阶段一行，子指标对齐到父阶段正下方 */
  const podStageMain = [
    { key: 'sdk_processing_us', label: 'SDK处理', color: '#5470c6' },
    { key: 'sdk_rpc_total_us', label: 'SDK RPC', color: '#fc8452' },
    { key: 'master_processing_us', label: 'Master处理', color: '#91cc75' },
    { key: 'master_rpc_total_us', label: 'Master RPC', color: '#c23531' },
    { key: 'worker_access_latency_us', label: 'Worker Access', color: '#8B5CF6' },
  ]

  const podStageLegend = podStageMain.map((s) => ({ label: s.label, color: s.color }))

  const podStageGrid = (stat: any) => {
    const mv = (key: string) => {
      const v = Number(stat.metricValues?.[key])
      return Number.isFinite(v) && v > 0 ? v : null
    }
    const workerInternal = Math.max(
      mv('remote_worker_internal_us') ?? 0,
      mv('local_worker_internal_us') ?? 0,
    )
    const subColor = (label: string) =>
      label === '网络'
        ? '#1E6FFF'
        : label === '框架'
          ? '#F59E0B'
          : label === 'URMA'
            ? '#EF4444'
            : '#00B365'
    const build = (
      key: string,
      label: string,
      color: string,
      childrenLabels?: string[],
      childKeys?: string[][],
    ) => {
      const value = mv(key)
      const children = childrenLabels
        ? childrenLabels.map((cl, i) => {
            const ck = childKeys?.[i] ?? []
            let cv: number | null = null
            for (const k of ck) {
              const v = mv(k)
              if (v != null) {
                cv = v
                break
              }
            }
            return { label: cl, value: cv, color: subColor(cl) }
          })
        : []
      return { key, label, color, value, children }
    }
    const stages = [
      build('sdk_processing_us', 'SDK处理', '#5470c6'),
      build(
        'sdk_rpc_total_us',
        'SDK RPC',
        '#fc8452',
        ['网络', '框架'],
        [['sdk_rpc_network_us'], ['sdk_rpc_framework_us']],
      ),
      build('master_processing_us', 'Master处理', '#91cc75'),
      build(
        'master_rpc_total_us',
        'Master RPC',
        '#c23531',
        ['网络', '框架'],
        [['master_rpc_network_us'], ['master_rpc_framework_us']],
      ),
      build(
        'worker_access_latency_us',
        'Worker Access',
        '#8B5CF6',
        ['Worker内部', 'URMA'],
        [[], ['urma_processing_us']],
      ),
    ]
    // Worker内部 (合并 remote/local 内部) 单独填
    const workerStage = stages[4]
    if (workerStage && workerStage.children[0]) {
      workerStage.children[0].value = workerInternal > 0 ? workerInternal : null
    }
    const maxVal = stages.reduce((m, s) => Math.max(m, s.value ?? 0), 0) || 1
    const toMs = (v: number | null) => (v != null ? +(v / 1000).toFixed(2) : null)
    return {
      maxVal,
      stages: stages.map((s) => ({
        ...s,
        valueMs: toMs(s.value),
        width: s.value != null ? Math.max(2, (s.value / maxVal) * 100) : 0,
        children: s.children.map((c) => ({
          ...c,
          valueMs: toMs(c.value),
          width: c.value != null ? Math.max(2, (c.value / maxVal) * 100) : 0,
        })),
      })),
    }
  }

  const podStageGridTitle = (stat: any) => {
    const grid = podStageGrid(stat)
    const lines = grid.stages.flatMap((s) => [
      `${s.label} ${s.valueMs != null ? s.valueMs + 'ms' : '-'}`,
      ...s.children.filter((c) => c.valueMs != null).map((c) => `  └ ${c.label} ${c.valueMs}ms`),
    ])
    return lines.join('\n')
  }

  /** 完整图例：主阶段 + 子项 */
  const podStageFullLegend = [
    { label: 'SDK处理', color: '#5470c6' },
    { label: 'SDK RPC', color: '#ea7ccc' },
    { label: 'Master处理', color: '#91cc75' },
    { label: 'Master RPC', color: '#c23531' },
    { label: 'Worker Access', color: '#fac858' },
    { label: 'SDK RPC·网络', color: '#fc8452' },
    { label: 'SDK RPC·框架', color: '#9a60b4' },
    { label: 'Master RPC·网络', color: '#ff9f7f' },
    { label: 'Master RPC·框架', color: '#ffdb5c' },
    { label: 'Worker内部', color: '#73c0de' },
    { label: 'URMA', color: '#6e7074' },
  ]

  const _hexRgb = (hex: string) => {
    const n = parseInt(hex.replace('#', ''), 16)
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
  }
  const _rgbHex = (r: number, g: number, b: number) =>
    '#' +
    [r, g, b]
      .map((x) =>
        Math.round(Math.max(0, Math.min(255, x)))
          .toString(16)
          .padStart(2, '0'),
      )
      .join('')
  const _mix = (hex: string, amount: number, toward: number) => {
    const rgb = _hexRgb(hex)
    const r = rgb[0] ?? 0
    const g = rgb[1] ?? 0
    const b = rgb[2] ?? 0
    return _rgbHex(r + (toward - r) * amount, g + (toward - g) * amount, b + (toward - b) * amount)
  }
  const _lighten = (hex: string, amount: number) => _mix(hex, amount, 255)
  const _darken = (hex: string, amount: number) => _mix(hex, amount, 0)

  // 与「指标趋势与异常分析」一致的颜色（ECharts 默认色板）
  const _STAGE_BASE: Record<string, string> = {
    sdk_processing_us: '#5470c6',
    sdk_rpc_total_us: '#ea7ccc',
    master_processing_us: '#91cc75',
    master_rpc_total_us: '#c23531',
    worker_access_latency_us: '#fac858',
  }
  const _STAGE_ORDER: Array<{ key: string; label: string }> = [
    { key: 'sdk_processing_us', label: 'SDK处理' },
    { key: 'sdk_rpc_total_us', label: 'SDK RPC' },
    { key: 'master_processing_us', label: 'Master处理' },
    { key: 'master_rpc_total_us', label: 'Master RPC' },
    { key: 'worker_access_latency_us', label: 'Worker Access' },
  ]
  const _TREND_COLOR: Record<string, string> = {
    sdk_rpc_network_us: '#fc8452',
    sdk_rpc_framework_us: '#9a60b4',
    master_rpc_network_us: '#ff9f7f',
    master_rpc_framework_us: '#ffdb5c',
    remote_worker_internal_us: '#ee6666',
    local_worker_internal_us: '#73c0de',
    urma_processing_us: '#6e7074',
  }

  const podStageFlow = (stat: any) => {
    const mv = (key: string) => {
      const v = Number(stat.metricValues?.[key])
      return Number.isFinite(v) && v > 0 ? v : null
    }
    const workerInternal = Math.max(
      mv('remote_worker_internal_us') ?? 0,
      mv('local_worker_internal_us') ?? 0,
    )
    const colorOf = (key: string) => _STAGE_BASE[key] ?? '#94a3b8'
    const subColor = (label: string, colorKey: string) => _TREND_COLOR[colorKey] ?? '#94a3b8'
    const sub = (label: string, colorKey: string, keys: string[]) => {
      let value: number | null = null
      for (const k of keys) {
        const v = mv(k)
        if (v != null) {
          value = v
          break
        }
      }
      return { label, value, color: subColor(label, colorKey) }
    }
    const stages = [
      {
        key: 'sdk_processing_us',
        label: 'SDK处理',
        color: colorOf('sdk_processing_us'),
        value: mv('sdk_processing_us'),
        children: [] as any[],
      },
      {
        key: 'sdk_rpc_total_us',
        label: 'SDK RPC',
        color: colorOf('sdk_rpc_total_us'),
        value: mv('sdk_rpc_total_us'),
        children: [
          sub('网络', 'sdk_rpc_network_us', ['sdk_rpc_network_us']),
          sub('框架', 'sdk_rpc_framework_us', ['sdk_rpc_framework_us']),
        ],
      },
      {
        key: 'master_processing_us',
        label: 'Master处理',
        color: colorOf('master_processing_us'),
        value: mv('master_processing_us'),
        children: [] as any[],
      },
      {
        key: 'master_rpc_total_us',
        label: 'Master RPC',
        color: colorOf('master_rpc_total_us'),
        value: mv('master_rpc_total_us'),
        children: [
          sub('网络', 'master_rpc_network_us', ['master_rpc_network_us']),
          sub('框架', 'master_rpc_framework_us', ['master_rpc_framework_us']),
        ],
      },
      {
        key: 'worker_access_latency_us',
        label: 'Worker Access',
        color: colorOf('worker_access_latency_us'),
        value: mv('worker_access_latency_us'),
        children: [
          sub('Worker内部', 'local_worker_internal_us', ['__worker_internal']),
          sub('URMA', 'urma_processing_us', ['urma_processing_us']),
        ],
      },
    ]
    const workerStage = stages[4]
    if (workerStage && workerStage.children[0] && workerInternal > 0) {
      workerStage.children[0].value = workerInternal
    }
    // 主条分母 = 出现的各阶段之和（归一化到 100%）
    const total = stages.reduce((sum, s) => sum + (s.value ?? 0), 0) || 1
    const toMs = (v: number | null) => (v != null ? +(v / 1000).toFixed(2) : null)
    return {
      maxChildren: Math.max(0, ...stages.map((s) => s.children.length)),
      stages: stages.map((s) => ({
        ...s,
        pct: s.value != null ? (s.value / total) * 100 : 0,
        valueMs: toMs(s.value),
        children: s.children.map((c) => ({
          ...c,
          valueMs: toMs(c.value),
          // 子项相对父阶段的比例（网络+框架≈父，内部/URMA 可能≈父，因重叠）
          rel: s.value != null && c.value != null ? Math.min(100, (c.value / s.value) * 100) : 0,
        })),
      })),
    }
  }

  const _podStageFlowTitle = (stat: any) => {
    const flow = podStageFlow(stat)
    const lines = flow.stages.flatMap((s) => [
      `${s.label} ${s.valueMs != null ? s.valueMs + 'ms' : '-'} (${s.pct.toFixed(0)}%)`,
      ...s.children.filter((c) => c.valueMs != null).map((c) => `  └ ${c.label} ${c.valueMs}ms`),
    ])
    return lines.join('\n')
  }

  const tracePageSize = 10
  const tracePage = ref(1)
  const tracePages = computed(() => Math.max(1, Math.ceil(traceRows.value.length / tracePageSize)))
  const pagedTraceRows = computed(() => paginate(traceRows.value, tracePage.value, tracePageSize))

  watch([traceSearch, traceCluster], () => {
    tracePage.value = 1
  })

  // ---------- 通断故障监控 ----------

  const faultChartData = computed(() => scopeData.value.faultChart || {})
  const faultTraces = computed(() => scopeData.value.faultTraces || [])
  const faultTimeRange = ref<{ start: string; end: string } | null>(null)
  const clearFaultRange = () => {
    faultTimeRange.value = null
    // 通断域 time 与框选同步（P0.7）
    disconnectFilter.clearTime()
    const el = faultChartRef.value
    const chart = el && getInstanceByDom(el)
    if (chart) chart.dispatchAction({ type: 'brush', areas: [] })
  }

  const faultPodAgg = computed(() => {
    const map = new Map<string, { ip: string; faults: number; codes: Set<string> }>()
    faultTraces.value.forEach((trace) => {
      const ips = [
        ...new Set([trace.src_ip, trace.dst_ip, ...(trace.pod_names || [])].filter(Boolean)),
      ]
      ips.forEach((ip: string) => {
        if (!ip) return
        if (!map.has(ip)) map.set(ip, { ip, faults: 0, codes: new Set() })
        const stat = map.get(ip)!
        stat.faults += 1
        normalizeFaultCodes(trace.status_code).forEach((code) => stat.codes.add(code))
      })
    })
    return [...map.values()]
      .sort((a, b) => b.faults - a.faults)
      .slice(0, 10)
      .map((stat) => ({ ip: stat.ip, faults: stat.faults, codes: [...stat.codes] }))
  })

  const filteredFaultTraces = computed(() => {
    const rows = faultTraces.value
    if (!faultTimeRange.value) return rows
    return rows.filter((row) => {
      const time = (row.timestamp || '').slice(11, 19)
      return time >= faultTimeRange.value!.start && time <= faultTimeRange.value!.end
    })
  })

  const faultTracePageSize = 10
  const faultTracePage = ref(1)
  const faultTracePages = computed(() =>
    Math.max(1, Math.ceil(filteredFaultTraces.value.length / faultTracePageSize)),
  )
  const pagedFaultTraces = computed(() =>
    paginate(filteredFaultTraces.value, faultTracePage.value, faultTracePageSize),
  )

  watch([faultTimeRange, currentOp], () => {
    faultTracePage.value = 1
  })

  // ---------- 对象详情（窗 × 端点/链路，服务端分页，P0.5） ----------

  type ObjectDetailDomain = 'latency' | 'disconnect'

  const objectDetail = reactive({
    open: false,
    domain: 'latency' as ObjectDetailDomain,
    title: '',
    windowLabel: '全部时段',
    loading: false,
    error: '',
    rows: [] as any[],
    total: 0,
    page: 1,
    pageSize: 10,
  })
  let objectDetailSeq = 0

  const objectDetailPages = computed(() =>
    Math.max(1, Math.ceil(objectDetail.total / objectDetail.pageSize)),
  )

  const fetchObjectDetailPage = async () => {
    const asset = selectedAsset.value
    if (!asset) return
    const filter = objectDetail.domain === 'latency' ? latencyFilter : disconnectFilter
    const focus = filter.focus.value
    const window = filter.timeWindow.value
    const seq = ++objectDetailSeq
    objectDetail.loading = true
    objectDetail.error = ''
    try {
      const query = {
        op: realOp.value,
        startTime: window ? epochMsToTs(window.start) : undefined,
        endTime: window ? epochMsToTs(window.end) : undefined,
        srcIp: focus.kind === 'link' ? focus.src : undefined,
        dstIp: focus.kind === 'link' ? focus.dst : undefined,
        endpointIp: focus.kind === 'pod' ? focus.ip : undefined,
        pageNum: objectDetail.page,
        pageCnt: objectDetail.pageSize,
      }
      const result =
        objectDetail.domain === 'latency'
          ? await fetchLatencyTracePage(asset.id, query)
          : await fetchFaultTracePage(asset.id, query)
      if (seq !== objectDetailSeq) return
      objectDetail.rows = result.rows
      objectDetail.total = result.total
    } catch (error) {
      if (seq !== objectDetailSeq) return
      objectDetail.error = errorText(error)
      objectDetail.rows = []
      objectDetail.total = 0
    } finally {
      if (seq === objectDetailSeq) objectDetail.loading = false
    }
  }

  const openObjectDetail = (domain: ObjectDetailDomain, focus: AnalysisFocus) => {
    if (focus.kind === 'none') {
      toast('请先在拓扑或列表中选择端点或链路', 'info')
      return
    }
    const filter = domain === 'latency' ? latencyFilter : disconnectFilter
    if (focus.kind === 'pod') filter.setFocusPod(focus.ip)
    else if (focus.kind === 'link') filter.setFocusLink(focus.src, focus.dst)
    objectDetail.domain = domain
    objectDetail.title =
      focus.kind === 'pod'
        ? `端点 ${focus.ip}`
        : focus.kind === 'link'
          ? `链路 ${focus.src} → ${focus.dst}`
          : '对象详情'
    objectDetail.windowLabel = filter.timeLabel.value
    objectDetail.page = 1
    objectDetail.rows = []
    objectDetail.total = 0
    objectDetail.error = ''
    objectDetail.open = true
    void fetchObjectDetailPage()
  }

  const objectDetailGoPage = (page: number) => {
    objectDetail.page = page
    void fetchObjectDetailPage()
  }
  const closeObjectDetail = () => {
    objectDetail.open = false
  }

  // 时延域：预加载跨域标签所需数据后打开详情（保持 podRowTags 口径完整）
  const enterPodDetail = async (ip: string) => {
    const op = realOp.value
    const latencyKey = `${op}:${trendPercentile.value}`
    const needTrend =
      !sectionCaches.abnormal.has(op) ||
      !sectionCaches.topSlow.has(op) ||
      !sectionCaches.latency.has(latencyKey)
    const needFault = !sectionCaches.faultTraces.has(op)
    if (needTrend) await loadTrendSection(op, trendPercentile.value)
    if (needFault) await loadFaultSection(op)
    openObjectDetail('latency', { kind: 'pod', ip })
  }

  const enterLinkDetail = (src: string, dst: string) => {
    openObjectDetail('latency', { kind: 'link', src, dst })
  }

  // 通断域入口（P0.7）：按通断接口真实字段发送 endpoint_ip / src+dst
  const enterFaultDetail = (ip: string) => {
    openObjectDetail('disconnect', { kind: 'pod', ip })
  }
  const enterFaultLinkDetail = (src: string, dst: string) => {
    openObjectDetail('disconnect', { kind: 'link', src, dst })
  }

  /** 点节点时 inspector 的 src/dst 对列表（旧「展开行」，仅选中后出现） */
  const focusPairs = computed(() => {
    const focus = latencyFilter.focus.value
    if (focus.kind !== 'pod') return []
    const map = new Map<string, { src: string; dst: string; total: number; anomaly: number }>()
    activePairs.value.forEach((pair) => {
      if (pair.src !== focus.ip && pair.dst !== focus.ip) return
      const key = `${pair.src}→${pair.dst}`
      const current = map.get(key)
      if (current) {
        current.total += pair.total
        current.anomaly += pair.anomaly
      } else {
        map.set(key, { src: pair.src, dst: pair.dst, total: pair.total, anomaly: pair.anomaly })
      }
    })
    return [...map.values()].sort((a, b) => b.anomaly - a.anomaly || b.total - a.total)
  })

  // ---------- Trace 抽屉 / 故障模式 ----------

  const detailDrawerOpen = ref(false)
  const detailDrawerRow = ref<any>(null)
  const drawerKind = ref<'log' | 'trace'>('log')
  const traceDrawerLogs = ref<any[]>([])

  const openTraceDrawer = async (row: any) => {
    detailDrawerRow.value = row
    drawerKind.value = 'trace'
    detailDrawerOpen.value = true
    traceDrawerLogs.value = []
    const asset = selectedAsset.value
    if (!asset || !row?.trace_id) return
    try {
      const result = await fetchTraceLogs(asset.id, [row.trace_id])
      traceDrawerLogs.value = result.log_failure_event_results ?? []
    } catch {
      traceDrawerLogs.value = []
    }
    if (!row.total_latency && !row.total_latency_us) {
      try {
        const latencyRow = await fetchTraceLatency(asset.id, row.trace_id)
        if (latencyRow) {
          detailDrawerRow.value = { ...row, ...latencyRow }
        }
      } catch {
        // 无时延明细时保持原样
      }
    }
  }

  const failureModeCache = reactive<Record<string, any>>({})
  const loadFailureMode = async (id: string) => {
    if (id in failureModeCache) return
    try {
      const result = await fetchFailureMode(id)
      failureModeCache[id] = result.failure_mode ?? result.failure_mode_knowledge ?? null
    } catch {
      failureModeCache[id] = null
    }
  }
  const failureModeOf = (id?: string | null) => {
    if (!id) return null
    if (!(id in failureModeCache)) void loadFailureMode(id)
    return failureModeCache[id] ?? null
  }

  const traceStageRows = (row: any) => {
    const defs = [
      { name: '总时延', key: 'total_latency' },
      { name: '查询元数据时延', key: 'worker_query_meta_latency' },
      { name: 'URMA总时延', key: 'urma_total_latency' },
      { name: 'URMA建链时延', key: 'urma_link_latency' },
      { name: 'C2W URMA时延', key: 'c2w_urma_latency' },
      { name: 'W2W URMA时延', key: 'w2w_urma_latency' },
      { name: 'SDK处理时延', key: 'sdk_process' },
      { name: 'SDK RPC时延', key: 'sdk_rpc' },
      { name: '本地Worker处理时延', key: 'local_worker_cost' },
      { name: '本地Worker锁时延', key: 'local_worker_lock' },
      { name: '远端Worker处理时延', key: 'remote_worker_cost' },
      { name: '远端Worker RPC时延', key: 'remote_worker_rpc' },
      { name: 'Master处理时延', key: 'master_process' },
      { name: 'Master RPC总时延', key: 'master_rpc_total' },
    ]
    return defs.map((def) => {
      const value = row ? row[def.key] : null
      const status = value == null ? '未解析' : row.is_anomalous ? '异常' : '正常'
      return { name: def.name, value, status }
    })
  }

  // ---------- 图表渲染 ----------

  const topoRef = ref<HTMLElement | null>(null)
  const ipRowRefs: Record<string, HTMLElement | null> = {}
  const trendRef = ref<HTMLElement | null>(null)
  const slowRef = ref<HTMLElement | null>(null)
  const faultChartRef = ref<HTMLElement | null>(null)
  const faultPodRef = ref<HTMLElement | null>(null)
  const faultTopoRef = ref<HTMLElement | null>(null)
  const faultPieRefs: Record<string, HTMLElement | null> = {}
  const brpcSuccessRef = ref<HTMLElement | null>(null)
  const brpcP99Ref = ref<HTMLElement | null>(null)
  const brpcFaultTimelineRef = ref<HTMLElement | null>(null)

  const getChart = (element: HTMLElement) => getInstanceByDom(element) || init(element)

  const setChartOption = (chart: ECharts, option: any) => {
    chart.setOption(option, { replaceMerge: ['series', 'legend'] })
  }

  const highlightRow = (ip: string) => {
    const el = ipRowRefs[ip]
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('highlight-row')
    window.setTimeout(() => el.classList.remove('highlight-row'), 2000)
  }

  const jumpToPod = (ip: string) => {
    if (!podIpStats.value.some((stat) => stat.ip === ip)) {
      toast(`未找到端点 IP ${ip}`, 'info')
      return
    }
    if (!filteredPodStats.value.some((stat) => stat.ip === ip)) {
      latencyFilter.clearWhitelist()
      podIpCbPage.value = 1
      toast('目标端点不在当前筛选内，已显示全部端点', 'info')
    }
    nextTick(() => {
      const index = filteredPodStats.value.findIndex((stat) => stat.ip === ip)
      if (index < 0) return
      podPage.value = Math.floor(index / podPageSize) + 1
      nextTick(() => highlightRow(ip))
    })
  }

  // 拓扑边异常率色阶：保证一般异常和高异常率在浅色画布上都有足够对比度。
  const severityColor = (ratio: number, healthy: string) =>
    ratio > 0.1 ? '#DC2626' : ratio > 0.02 ? '#EA580C' : ratio > 0 ? '#D97706' : healthy

  const topoNodeLimit = 30
  const topoShowAll = ref(false)
  const topoHiddenCount = ref(0)
  const topoTotalCount = ref(0)
  let topologyBlankClickHandler: ((event: any) => void) | null = null

  type TopologyLink = {
    key: string
    source: string
    target: string
    action: string
    totalCount: number
    anomalyCount: number
    anomalyRate: number
    queryMeta: number | null | undefined
    urmaTotal: number | null | undefined
    urmaLink: number | null | undefined
    c2w: number | null | undefined
    w2w: number | null | undefined
  }

  // 将多个时间桶内同一方向的 IP 对合并为一条可比较链路，供图、排名和详情共用。
  const topologyLinks = computed<TopologyLink[]>(() => {
    const links = new Map<string, TopologyLink>()
    activePairs.value.forEach((pair) => {
      const key = `${pair.src}→${pair.dst}`
      const totalCount = currentOp.value === 'GET' ? pair.get : pair.set
      if (!totalCount) return
      const anomalyCount = pair.anomaly
      const current = links.get(key)
      if (!current) {
        links.set(key, {
          key,
          source: pair.src,
          target: pair.dst,
          action: currentOp.value,
          totalCount,
          anomalyCount,
          anomalyRate: totalCount ? anomalyCount / totalCount : 0,
          queryMeta: pair.queryMeta,
          urmaTotal: pair.urmaTotal,
          urmaLink: pair.urmaLink,
          c2w: pair.c2w,
          w2w: pair.w2w,
        })
        return
      }
      ;(['queryMeta', 'urmaTotal', 'urmaLink', 'c2w', 'w2w'] as const).forEach((field) => {
        const previousValue = current[field]
        const nextValue = pair[field]
        if (typeof previousValue === 'number' && typeof nextValue === 'number') {
          current[field] =
            (previousValue * current.totalCount + nextValue * totalCount) /
            (current.totalCount + totalCount)
        } else if (typeof nextValue === 'number') {
          current[field] = nextValue
        }
      })
      current.totalCount += totalCount
      current.anomalyCount += anomalyCount
      current.anomalyRate = current.totalCount ? current.anomalyCount / current.totalCount : 0
    })
    return [...links.values()].sort(
      (a, b) =>
        b.anomalyCount - a.anomalyCount ||
        b.anomalyRate - a.anomalyRate ||
        b.totalCount - a.totalCount ||
        a.key.localeCompare(b.key),
    )
  })

  const visibleTopologyLinks = computed(() => {
    // nodeWhitelist 只控制本地可视化，不冒充服务端过滤（P0.2）
    if (!latencyFilter.nodeWhitelist.value.length) return topologyLinks.value
    const allowed = new Set(latencyFilter.nodeWhitelist.value)
    return topologyLinks.value.filter(
      (link) => allowed.has(link.source) || allowed.has(link.target),
    )
  })

  const topologySummary = computed(() => {
    const links = visibleTopologyLinks.value
    const nodes = new Set(links.flatMap((link) => [link.source, link.target]))
    return {
      nodeCount: nodes.size,
      linkCount: links.length,
      totalCount: links.reduce((sum, link) => sum + link.totalCount, 0),
      anomalyCount: links.reduce((sum, link) => sum + link.anomalyCount, 0),
    }
  })

  // focus 是当前分析对象的唯一事实源（P0.4）：点节点/边/空白都在写它
  const selectedTopologyLink = computed(() => {
    const focus = latencyFilter.focus.value
    if (focus.kind !== 'link') return null
    return topologyLinks.value.find((link) => link.key === `${focus.src}→${focus.dst}`) ?? null
  })
  const selectedTopologyNode = computed(() => {
    const focus = latencyFilter.focus.value
    if (focus.kind !== 'pod') return null
    return podIpStats.value.find((node) => node.ip === focus.ip) ?? null
  })
  const selectTopologyLink = (link: TopologyLink) => {
    const focus = latencyFilter.focus.value
    if (focus.kind === 'link' && focus.src === link.source && focus.dst === link.target) {
      latencyFilter.clearFocus()
    } else {
      latencyFilter.setFocusLink(link.source, link.target)
    }
  }
  const selectTopologyNode = (ip: string) => {
    const focus = latencyFilter.focus.value
    if (focus.kind === 'pod' && focus.ip === ip) {
      latencyFilter.clearFocus()
    } else {
      latencyFilter.setFocusPod(ip)
    }
  }
  const clearTopologyFocus = () => {
    // 点空白：清对象，保留 time（P0.4）
    latencyFilter.clearFocus()
  }
  const showLinkEndsOnly = (link: TopologyLink) => {
    // 「只显示两端节点」：仅改变拓扑可见节点，不改变服务端查询
    latencyFilter.showOnlyNodes([link.source, link.target])
  }

  // 等比环形布局：坐标始终落在正方形绘图区，避免横向画布将圆环和节点拉伸变形。
  const layoutTopoNodes = (nodes: { ip: string; total: number; src: number; dst: number }[]) => {
    const ordered = [...nodes].sort((a, b) => b.total - a.total || a.ip.localeCompare(b.ip))
    const positions = new Map<string, { x: number; y: number }>()
    ordered.forEach((node, index) => {
      const angle = -Math.PI / 2 + (index / Math.max(ordered.length, 1)) * Math.PI * 2
      positions.set(node.ip, { x: Math.cos(angle), y: Math.sin(angle) })
    })
    return positions
  }

  const renderTopology = () => {
    nextTick(() => {
      const el = topoRef.value
      if (!el) return
      const chart = getChart(el)

      const nodeMap = new Map<string, any>()
      visibleTopologyLinks.value.forEach((link) => {
        ;(
          [
            ['src', link.source],
            ['dst', link.target],
          ] as const
        ).forEach(([role, ip]) => {
          if (!nodeMap.has(ip)) nodeMap.set(ip, { ip, total: 0, anomaly: 0, src: 0, dst: 0 })
          const node = nodeMap.get(ip)
          node.total += link.totalCount
          node.anomaly += link.anomalyCount
          if (role === 'src') node.src += link.totalCount
          else node.dst += link.totalCount
        })
      })

      let aggregatedLinks: any[] = visibleTopologyLinks.value.map((link) => ({
        ...link,
        value: link.totalCount,
      }))

      // 节点过多时只保留通信量 Top N，其余连同边隐藏
      const involved = new Set(aggregatedLinks.flatMap((link) => [link.source, link.target]))
      const allNodes = [...nodeMap.values()].filter((node) => involved.has(node.ip))
      let visibleNodes = allNodes
      if (!topoShowAll.value && allNodes.length > topoNodeLimit) {
        const keep = new Set(
          [...allNodes]
            .sort((a, b) => b.total - a.total || a.ip.localeCompare(b.ip))
            .slice(0, topoNodeLimit)
            .map((node) => node.ip),
        )
        visibleNodes = allNodes.filter((node) => keep.has(node.ip))
        aggregatedLinks = aggregatedLinks.filter(
          (link) => keep.has(link.source) && keep.has(link.target),
        )
      }
      topoTotalCount.value = allNodes.length
      topoHiddenCount.value = topoShowAll.value ? 0 : allNodes.length - visibleNodes.length

      // 边宽轻量表达通信量，色彩表达异常率；双向边反向弯曲避免重叠。
      if (aggregatedLinks.length > 0) {
        const counts = aggregatedLinks.map((link) => link.totalCount)
        const minCount = Math.min(...counts)
        const maxCount = Math.max(...counts)
        aggregatedLinks.forEach((link) => {
          const normalized =
            Math.log1p(link.totalCount - minCount) / Math.log1p(maxCount - minCount || 1)
          const width = 3.5 + normalized * 2
          const ratio = link.anomalyRate
          const healthy = ratio <= 0
          const selected = selectedTopologyLink.value?.key === link.key
          link.lineStyle = {
            color: selected ? '#6D28D9' : severityColor(ratio, '#64748B'),
            width: selected ? width + 2 : healthy ? Math.max(2.5, width * 0.75) : width,
            opacity: selected ? 1 : healthy ? 0.65 : 0.9,
            curveness: link.source < link.target ? 0.08 : -0.08,
            shadowBlur: selected ? 6 : 0,
            shadowColor: selected ? 'rgba(109,40,217,0.35)' : 'transparent',
          }
          link.symbolSize = [0, Math.min(13, Math.max(10, Math.round(width + 7)))]
        })
      }

      const positions = layoutTopoNodes(visibleNodes)
      const graphSize = Math.max(220, Math.min(el.clientWidth - 150, el.clientHeight - 70))
      const graphLeft = Math.max(75, (el.clientWidth - graphSize) / 2)
      const graphTop = Math.max(35, (el.clientHeight - graphSize) / 2)
      const maxTotal = Math.max(...visibleNodes.map((node) => node.total), 1)
      const nodes = visibleNodes.map((node) => {
        const pos = positions.get(node.ip)
        const selectedLink = selectedTopologyLink.value
        const focused =
          selectedTopologyNode.value?.ip === node.ip ||
          selectedLink?.source === node.ip ||
          selectedLink?.target === node.ip
        const size = 34 + Math.sqrt(node.total / maxTotal) * 12
        return {
          name: node.ip,
          x: pos?.x,
          y: pos?.y,
          total: node.total,
          anomaly: node.anomaly,
          src: node.src,
          dst: node.dst,
          symbol: 'circle',
          symbolSize: size,
          cursor: 'pointer',
          itemStyle: {
            color: focused ? '#1E40AF' : '#4F8EF7',
            borderColor: focused ? '#172554' : '#1D4ED8',
            borderWidth: focused ? 4 : 2,
            shadowBlur: focused ? 12 : 5,
            shadowColor: focused ? 'rgba(30,64,175,0.45)' : 'rgba(29,78,216,0.24)',
          },
          label: {
            show: true,
            position:
              pos && pos.x > 0.35
                ? 'right'
                : pos && pos.x < -0.35
                  ? 'left'
                  : pos && pos.y > 0
                    ? 'bottom'
                    : 'top',
            distance: 7,
            formatter: node.ip,
            color: '#1E293B',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 11,
            fontWeight: 600,
            backgroundColor: 'rgba(255,255,255,0.96)',
            borderRadius: 3,
            padding: [2, 4],
          },
        }
      })

      setChartOption(chart, {
        animation: false,
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => {
            if (params.dataType === 'node') {
              const data = params.data
              return `<b>${data.name}</b><br/>总通信次数: ${data.total.toLocaleString()}<br/>出方向(源): ${data.src.toLocaleString()} &nbsp; 入方向(目标): ${data.dst.toLocaleString()}<br/>异常数: ${data.anomaly}<br/>异常率: ${data.total ? ((data.anomaly / data.total) * 100).toFixed(1) : 0}%`
            }
            if (params.dataType === 'edge') {
              const data = params.data
              const fmt = (value: unknown) =>
                value == null || value === '-' ? '-' : Number(value).toFixed(1)
              return `<b>${data.action} · ${data.source} → ${data.target}</b><br/>通信次数: ${data.totalCount.toLocaleString()}<br/>异常数: ${data.anomalyCount} (${data.totalCount ? ((data.anomalyCount / data.totalCount) * 100).toFixed(1) : 0}%)<br/><br/>时延指标 (ms):<br/>查询元数据: ${fmt(data.queryMeta)}<br/>URMA总: ${fmt(data.urmaTotal)}<br/>URMA建链: ${fmt(data.urmaLink)}<br/>C2W: ${fmt(data.c2w)}<br/>W2W: ${fmt(data.w2w)}`
            }
            return ''
          },
        },
        series: [
          {
            type: 'graph',
            layout: 'none',
            roam: true,
            draggable: false,
            cursor: 'pointer',
            left: graphLeft,
            top: graphTop,
            width: graphSize,
            height: graphSize,
            edgeSymbol: ['none', 'arrow'],
            labelLayout: { hideOverlap: true },
            data: nodes,
            links: aggregatedLinks,
            emphasis: {
              focus: 'adjacency',
              lineStyle: { opacity: 0.95, width: 4.8 },
              itemStyle: { shadowBlur: 16 },
            },
          },
        ],
      })

      // 点击即分析（P0.4）：点节点/边写 focus，点空白清 focus（保留 time）
      chart.off('click')
      chart.on('click', (params: any) => {
        if (params.dataType === 'edge') {
          selectTopologyLink(params.data)
        } else if (params.dataType === 'node') {
          selectTopologyNode(params.data.name)
        }
      })
      if (topologyBlankClickHandler) {
        chart.getZr().off('click', topologyBlankClickHandler)
      }
      topologyBlankClickHandler = (event: any) => {
        if (!event.target) {
          clearTopologyFocus()
        }
      }
      chart.getZr().on('click', topologyBlankClickHandler)
    })
  }

  const resetTopologyFilter = () => {
    latencyFilter.clearWhitelist()
    topoShowAll.value = false
    podIpCbPage.value = 1
  }

  const pctToIndex = (pct: number, n: number) =>
    Math.max(0, Math.min(n - 1, Math.round((pct / 100) * (n - 1))))

  const renderAnomalyChart = () => {
    nextTick(() => {
      const el = anomalyRef.value
      if (!el) return
      const chart = getChart(el)
      const buckets = anomalySeries.value
      if (!buckets.length) {
        chart.clear()
        return
      }
      const times = buckets.map((b) => b.time)
      const n = buckets.length
      const toPct = (time: number) => {
        if (!times.length) return [0, 100] as const
        const min = times[0] ?? 0
        const max = times[n - 1] ?? min
        const span = max - min || 1
        const start = Math.max(0, ((time - min) / span) * 100)
        return [start, 100] as const
      }
      const timeWindow = latencyFilter.timeWindow.value
      const [pctStart, pctEnd] = timeWindow ? toPct(timeWindow.start) : ([0, 100] as const)
      const statLabelMap: Record<string, string> = {
        ave: '均值',
        p95: 'P95',
        p99: 'P99',
        min: '最小',
        max: '最大',
      }
      const statLabel = statLabelMap[overview.statType] || '均值'
      // 粗粒度 P95/P99 是 10 秒桶分位值的再聚合近似（P0.3 文案口径）
      const approximate = overviewScale.value >= 60 && ['p95', 'p99'].includes(overview.statType)
      const statSuffix = approximate ? '，粗粒度近似' : ''

      setChartOption(chart, {
        animation: false,
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params: any) => {
            const index = (Array.isArray(params) ? params : [])[0]?.dataIndex
            const bucket = buckets[index]
            if (!bucket) return ''
            return `<b>开始 ${formatChartTs(bucket.start)}<br/>结束 ${formatChartTs(bucket.end)}</b><br/>请求数: ${bucket.total}<br/>异常请求数: <span style="color:#EF4444">${bucket.anomaly}</span><br/>总时延(${statLabel}${statSuffix}): ${bucket.statValue != null ? bucket.statValue.toFixed(2) + ' ms' : '-'}<br/><span style="color:#94a3b8">点击柱体选中该时段</span>`
          },
        },
        grid: { left: 54, right: 70, top: 48, bottom: 56 },
        xAxis: { type: 'time', axisLabel: { fontSize: 10 } },
        yAxis: [
          {
            type: 'value',
            name: '异常数',
            nameTextStyle: { color: '#EF4444' },
            minInterval: 1,
            axisLabel: { fontSize: 10 },
          },
          {
            type: 'value',
            name: '总时延(ms)',
            nameTextStyle: { color: '#1E6FFF' },
            axisLabel: { fontSize: 10 },
            splitLine: { show: false },
          },
        ],
        legend: {
          top: 0,
          right: 8,
          itemWidth: 14,
          itemHeight: 8,
          itemGap: 12,
          textStyle: { fontSize: 10 },
        },
        dataZoom: [
          {
            type: 'inside',
            start: pctStart,
            end: pctEnd,
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
          },
          { type: 'slider', start: pctStart, end: pctEnd, bottom: 12, height: 18 },
        ],
        series: [
          {
            name: '异常请求数',
            type: 'bar',
            barMaxWidth: 28,
            cursor: 'pointer',
            itemStyle: { color: '#EF4444', borderRadius: [3, 3, 0, 0] },
            data: buckets.map((b) => [b.time, b.anomaly]),
          },
          {
            name: `总时延·${statLabel}`,
            type: 'line',
            yAxisIndex: 1,
            smooth: true,
            symbol: 'circle',
            symbolSize: 5,
            data: buckets.map((b) => [b.time, b.statValue]),
            lineStyle: { color: '#1E6FFF', width: 2 },
            itemStyle: { color: '#1E6FFF' },
            z: 3,
          },
        ],
      })

      // 点柱 = 选中该窗（time.mode = 'bucket'）
      chart.off('click')
      chart.on('click', (params: any) => {
        const index = params?.dataIndex
        const bucket = buckets[index]
        if (!bucket) return
        latencyFilter.setTimeBucket(epochOf(bucket.start), epochOf(bucket.end))
        void loadAnalysisWindow()
      })

      // dataZoom → time.mode = 'range'；防抖后按窗重新请求，不覆盖全域 timelineData
      chart.off('datazoom')
      chart.on('datazoom', (params: any) => {
        const batch = (params && (params.batch || [params])[0]) || {}
        const start = typeof batch.start === 'number' ? batch.start : 0
        const end = typeof batch.end === 'number' ? batch.end : 100
        if (start <= 0.5 && end >= 99.5) {
          latencyFilter.clearTime()
          void loadAnalysisWindow()
        } else {
          const i0 = pctToIndex(start, n)
          const i1 = pctToIndex(end, n)
          const startTime = times[i0] ?? times[0] ?? 0
          const endTime = times[i1] ?? times[n - 1] ?? startTime
          const prev = times[Math.max(0, i1 - 1)] ?? endTime
          latencyFilter.setTimeRange(startTime, endTime + (endTime - prev || 1))
          scheduleAnalysisWindow()
        }
        renderTopology()
      })
    })
  }

  const renderTrendChart = () => {
    nextTick(() => {
      const el = trendRef.value
      if (!el) return
      const chart = getChart(el)
      const buckets = trendBuckets.value
      if (!buckets.length) {
        chart.clear()
        return
      }
      const labels = buckets.map((bucket) => bucket.label)
      // 曲线集合与当前桶数据对齐：无数据的指标不渲染（旧前端 2feac6a1 同款口径）
      const visible = trendMetrics.filter(
        (metric) =>
          trendVisible.value.has(metric.key) &&
          buckets.some((bucket) => bucket.values[metric.key] != null),
      )
      const ranges: Array<Array<{ xAxis: number }>> = []
      let start: number | null = null
      buckets.forEach((bucket, index) => {
        if (bucket.abnormal && start === null) start = index
        if ((!bucket.abnormal || index === buckets.length - 1) && start !== null) {
          const end = bucket.abnormal && index === buckets.length - 1 ? index : index - 1
          ranges.push([{ xAxis: start }, { xAxis: end }])
          start = null
        }
      })
      const xStep = labels.length <= 10 ? 1 : Math.ceil(labels.length / 10)
      // 聚焦窗口：由点击点的时间范围推导 dataZoom 百分比，使 x 轴收窄到该区域
      let dzStart = 0
      let dzEnd = 100
      const range = trendRange.value
      if (range) {
        const times = buckets.map((bucket) => bucket.time)
        let i0 = times.findIndex((t) => t >= range.start)
        if (i0 < 0) i0 = 0
        let i1 = 0
        for (let i = times.length - 1; i >= 0; i--) {
          if ((times[i] ?? Infinity) <= range.end) {
            i1 = i
            break
          }
        }
        const n = buckets.length
        dzStart = Math.max(0, (i0 / n) * 100)
        dzEnd = Math.min(100, ((i1 + 1) / n) * 100)
        if (dzEnd <= dzStart) dzEnd = dzStart + 1
      }
      setChartOption(chart, {
        animation: false,
        color: visible.map((series) => series.color as string),
        tooltip: {
          trigger: 'axis',
          appendToBody: true,
          valueFormatter: (value: unknown) =>
            typeof value === 'number' ? `${value.toFixed(2)} ms` : String(value ?? '-'),
        },
        legend: {
          data: visible.map((series) => series.label),
          top: 0,
          itemGap: 18,
          itemWidth: 18,
          itemHeight: 10,
          textStyle: { fontSize: 11 },
        },
        grid: { top: 58, right: 68, bottom: 15, left: 54, containLabel: true },
        xAxis: {
          type: 'category',
          data: labels,
          name: '时间',
          axisLabel: {
            interval: (index: number) =>
              labels.length <= 10 ||
              index === 0 ||
              index === labels.length - 1 ||
              index % xStep === 0,
            fontSize: 10,
            rotate: 38,
            margin: 6,
          },
        },
        yAxis: { type: 'value', name: '时延 (ms)', min: 0, axisLabel: { fontSize: 10 } },
        dataZoom: [
          {
            type: 'inside',
            start: dzStart,
            end: dzEnd,
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
          },
          { type: 'slider', start: dzStart, end: dzEnd, bottom: 14, height: 18 },
        ],
        series: visible.map((series, index) => ({
          name: series.label,
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2 },
          data: buckets.map((bucket) => bucket.values[series.key]),
          ...(index === 0
            ? {
                markArea: {
                  silent: false,
                  data: ranges,
                  itemStyle: {
                    color: 'rgba(239,68,68,0.25)',
                    borderColor: '#ef4444',
                    borderWidth: 1,
                  },
                },
              }
            : {}),
        })),
      })
      chart.off('click')
      chart.on('click', (params: any) => {
        if (typeof params.dataIndex === 'number') {
          const bucket = buckets[params.dataIndex]
          if (bucket) {
            trendCenter.value = bucket.time
            renderTrendChart()
          }
        }
      })
    })
  }

  const renderSlowChart = () => {
    nextTick(() => {
      const el = slowRef.value
      if (!el) return
      const chart = getChart(el)
      const rows = slowChartRows.value
      const labels = rows.map((row) => row.timestampLabel)
      const initialEnd = Math.min(100, (50 / rows.length) * 100)
      const hasOther = rows.some((row) => row.otherLatency > 0)
      const barSeries = topSlowSegmentConfig.map((segment) => ({
        name: segment.label,
        type: 'bar',
        stack: 'latency-components',
        barMaxWidth: 22,
        emphasis: { focus: 'series' },
        itemStyle: { color: segment.color },
        data: rows.map((row) => {
          const value = row.segments[segment.key]
          return typeof value === 'number' ? value / 1000 : 0
        }),
      }))
      if (hasOther) {
        barSeries.push({
          name: '其他',
          type: 'bar',
          stack: 'latency-components',
          barMaxWidth: 22,
          emphasis: { focus: 'series' },
          itemStyle: { color: '#94a3b8' },
          data: rows.map((row) => row.otherLatency / 1000),
        })
      }
      const formatLatency = (value: number) => `${value.toFixed(2)} ms`
      // 计数类分段（如 URMA并发数）堆叠值同样被 /1000 缩放到不可见，tooltip 展示原始个数
      const formatMetric = (seriesName: string | undefined, value: number) => {
        const segment = topSlowSegmentConfig.find((item) => item.label === seriesName)
        return segment?.unit === 'count' ? `${Math.round(value * 1000)} 个` : formatLatency(value)
      }
      setChartOption(chart, {
        animation: rows.length <= 300,
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          appendToBody: true,
          formatter: (params: any) => {
            const items = Array.isArray(params) ? params : []
            const row = rows[items[0]?.dataIndex]
            if (!row) return ''
            const details = items
              .filter(
                (item: any) =>
                  item.seriesName !== '总时延' &&
                  typeof item.value === 'number' &&
                  Number.isFinite(item.value) &&
                  item.value > 0,
              )
              .map(
                (item: any) =>
                  `<div style="display:flex;justify-content:space-between;gap:16px"><span><i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${item.color};margin-right:6px"></i>${item.seriesName}</span><b>${formatMetric(item.seriesName, item.value)}</b></div>`,
              )
              .join('')
            return `<div style="min-width:260px"><strong>${row.timestampLabel}</strong><br/><small>${row.traceId} · ${row.operation}</small><div style="margin:6px 0;border-top:1px solid #D9E0E8"></div>${details}<div style="margin-top:6px;display:flex;justify-content:space-between"><span>总时延</span><b style="color:#EF4444">${formatLatency(row.totalLatency / 1000)}</b></div></div>`
          },
        },
        legend: {
          type: 'scroll',
          top: 0,
          left: 8,
          right: 8,
          data: [
            ...topSlowSegmentConfig.map((segment) => segment.label),
            ...(hasOther ? ['其他'] : []),
            '总时延',
          ],
          textStyle: { fontSize: 11 },
        },
        grid: { top: 58, right: 24, bottom: 92, left: 62, containLabel: true },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { fontSize: 10, rotate: 42, interval: 0 },
        },
        yAxis: { type: 'value', name: '时延 (ms)', min: 0, axisLabel: { fontSize: 10 } },
        dataZoom: [
          {
            type: 'inside',
            start: 0,
            end: initialEnd,
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
          },
          { type: 'slider', start: 0, end: initialEnd, bottom: 48, height: 20 },
        ],
        series: [
          ...barSeries,
          {
            name: '总时延',
            type: 'line',
            symbol: 'none',
            lineStyle: { color: '#dc2626', width: 2 },
            itemStyle: { color: '#dc2626' },
            z: 10,
            data: rows.map((row) => row.totalLatency / 1000),
          },
        ],
      })
      chart.off('click')
      chart.on('click', (params: any) => {
        const row = rows[params.dataIndex]
        if (row && row.raw && row.raw.trace_id) void openTraceDrawer(row.raw)
      })
    })
  }

  const faultActivePairs = computed(() => {
    const map = new Map<string, { src: string; dst: string; faults: number; codes: string[] }>()
    faultTraces.value.forEach((trace) => {
      const src = trace.src_ip
      const dst = trace.dst_ip
      if (!src || !dst) return
      const key = `${src}|${dst}`
      if (!map.has(key)) map.set(key, { src, dst, faults: 0, codes: [] })
      const pair = map.get(key)!
      pair.faults += 1
      normalizeFaultCodes(trace.status_code).forEach((code) => {
        if (!pair.codes.includes(code)) pair.codes.push(code)
      })
    })
    return [...map.values()].sort((a, b) => b.faults - a.faults)
  })

  const faultPodStats = computed(() => {
    const map = new Map<
      string,
      { ip: string; faults: number; src: number; dst: number; codes: string[] }
    >()
    faultTraces.value.forEach((trace) => {
      const ips = [
        ...new Set([trace.src_ip, trace.dst_ip, ...(trace.pod_names || [])].filter(Boolean)),
      ]
      ips.forEach((ip: string) => {
        if (!map.has(ip)) map.set(ip, { ip, faults: 0, src: 0, dst: 0, codes: [] })
        const stat = map.get(ip)!
        stat.faults += 1
        if (trace.src_ip === ip) stat.src += 1
        if (trace.dst_ip === ip) stat.dst += 1
        normalizeFaultCodes(trace.status_code).forEach((code) => {
          if (!stat.codes.includes(code)) stat.codes.push(code)
        })
      })
    })
    return [...map.values()].sort((a, b) => b.faults - a.faults)
  })

  const renderFaultTopology = () => {
    nextTick(() => {
      const el = faultTopoRef.value
      if (!el) return
      const chart = getChart(el)
      const nodeMap = new Map<string, { ip: string; faults: number; src: number; dst: number }>()
      faultActivePairs.value.forEach((pair) => {
        ;(
          [
            ['src', pair.src],
            ['dst', pair.dst],
          ] as const
        ).forEach(([role, ip]) => {
          if (!nodeMap.has(ip)) nodeMap.set(ip, { ip, faults: 0, src: 0, dst: 0 })
          const node = nodeMap.get(ip)!
          node.faults += pair.faults
          if (role === 'src') node.src += pair.faults
          else node.dst += pair.faults
        })
      })
      const maxFaults = Math.max(...[...nodeMap.values()].map((node) => node.faults), 1)
      const nodes = [...nodeMap.values()].map((node) => ({
        name: node.ip,
        faults: node.faults,
        src: node.src,
        dst: node.dst,
        symbolSize: 16 + (node.faults / maxFaults) * 44,
        itemStyle: {
          color: node.faults > 20 ? '#EF4444' : node.faults > 5 ? '#F59E0B' : '#1E6FFF',
        },
        label: { show: true, fontSize: 11, formatter: '{b}' },
      }))
      const links = faultActivePairs.value.map((pair) => ({
        source: pair.src,
        target: pair.dst,
        faults: pair.faults,
        codes: pair.codes,
        value: pair.faults,
        lineStyle: {
          color: '#EF4444',
          width: 1 + (pair.faults / maxFaults) * 5,
          curveness: 0.2,
          opacity: 0.85,
        },
      }))
      setChartOption(chart, {
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => {
            if (params.dataType === 'node') {
              const data = params.data
              return `<b>${data.name}</b><br/>故障次数: ${data.faults}<br/>出方向: ${data.src} &nbsp; 入方向: ${data.dst}`
            }
            if (params.dataType === 'edge') {
              const data = params.data
              return `<b>${data.source} → ${data.target}</b><br/>故障次数: ${data.faults}<br/>故障码: ${data.codes.join(', ') || '-'}`
            }
            return ''
          },
        },
        series: [
          {
            type: 'graph',
            layout: 'force',
            roam: true,
            draggable: true,
            edgeSymbol: ['none', 'arrow'],
            edgeSymbolSize: 8,
            force: { repulsion: 520, edgeLength: [130, 280], gravity: 0.12 },
            data: nodes,
            links,
            emphasis: { focus: 'adjacency', lineStyle: { width: 7 } },
          },
        ],
      })

      // P0.7：点节点/边进入「窗 + 端点/链路」的故障 Trace（按通断接口字段发送）
      chart.off('click')
      chart.on('click', (params: any) => {
        if (params.dataType === 'edge') {
          enterFaultLinkDetail(params.data.source, params.data.target)
        } else if (params.dataType === 'node') {
          enterFaultDetail(params.data.name)
        }
      })
    })
  }

  const renderFaultPieCharts = () => {
    nextTick(() => {
      const faultEl = faultPieRefs['faults']
      if (faultEl) {
        const chart = getChart(faultEl)
        setChartOption(chart, {
          tooltip: { trigger: 'item', formatter: '{b}<br/>故障: {c} ({d}%)' },
          series: [
            {
              type: 'pie',
              radius: ['40%', '70%'],
              data: faultPodStats.value.map((stat) => ({ name: stat.ip, value: stat.faults })),
              label: { fontSize: 11 },
            },
          ],
        })
      }
      const codeEl = faultPieRefs['codes']
      if (codeEl) {
        const chart = getChart(codeEl)
        const codeMap = new Map<string, number>()
        faultTraces.value.forEach((trace) => {
          const codes = normalizeFaultCodes(trace.status_code)
          if (codes.length === 0) {
            codeMap.set('0', (codeMap.get('0') || 0) + 1)
            return
          }
          codes.forEach((code) => codeMap.set(code, (codeMap.get(code) || 0) + 1))
        })
        setChartOption(chart, {
          tooltip: { trigger: 'item', formatter: '{b}<br/>次数: {c} ({d}%)' },
          series: [
            {
              type: 'pie',
              radius: ['40%', '70%'],
              data: [...codeMap.entries()].map(([code, count]) => ({
                name: code === '0' ? '无故障码' : `故障码 ${code}`,
                value: count,
              })),
              label: { fontSize: 11 },
            },
          ],
        })
      }
    })
  }

  const abnormalTraceIdSet = computed(
    () => new Set((scopeData.value.abnormal || []).map((row: any) => row.trace_id).filter(Boolean)),
  )
  const faultTraceIdSet = computed(
    () =>
      new Set((scopeData.value.faultTraces || []).map((row: any) => row.trace_id).filter(Boolean)),
  )

  const traceTags = (traceId: string, source: 'fault' | 'latency') => {
    const op = realOp.value
    const tags: Array<{ type: 'fault' | 'latency'; label: string }> = []
    if (source === 'fault') {
      tags.push({ type: 'fault', label: '通断' })
      if (faultTraceIdsWithLatency[op].has(traceId)) tags.push({ type: 'latency', label: '时延' })
    } else {
      tags.push({ type: 'latency', label: '时延' })
      if (latencyTraceIdsWithFault[op].has(traceId)) tags.push({ type: 'fault', label: '通断' })
    }
    return tags
  }

  const podRowTags = (row: any) => {
    const op = realOp.value
    const tags: Array<{ type: 'fault' | 'latency'; label: string }> = []
    const traceId = row?.trace_id
    const isFault =
      normalizeFaultCodes(row?.status_code).length > 0 ||
      (traceId ? faultTraceIdSet.value.has(traceId) : false)
    const hasLatency =
      row?.total_latency ||
      row?.total_latency_us ||
      (traceId ? abnormalTraceIdSet.value.has(traceId) : false) ||
      (traceId ? faultTraceIdsWithLatency[op].has(traceId) : false)
    if (isFault) tags.push({ type: 'fault', label: '通断' })
    if (hasLatency) tags.push({ type: 'latency', label: '时延' })
    return tags
  }

  const renderFaultPodChart = () => {
    nextTick(() => {
      const el = faultPodRef.value
      if (!el) return
      const chart = getChart(el)
      const rows = [...faultPodAgg.value].reverse()
      setChartOption(chart, {
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => `<b>${params.name}</b><br/>故障次数：${params.value}`,
        },
        grid: { left: 118, right: 24, top: 12, bottom: 28 },
        xAxis: { type: 'value', name: '故障次数', axisLabel: { fontSize: 10 } },
        yAxis: {
          type: 'category',
          data: rows.map((row) => row.ip),
          axisLabel: { fontSize: 10, fontFamily: 'monospace' },
        },
        series: [
          {
            type: 'bar',
            barMaxWidth: 18,
            data: rows.map((row) => ({
              name: row.ip,
              value: row.faults,
              itemStyle: { color: row.faults > 5 ? '#EF4444' : '#F59E0B' },
            })),
          },
        ],
      })
      chart.off('click')
      chart.on('click', (params: any) => {
        if (params.name) enterFaultDetail(params.name)
      })
    })
  }

  const renderFaultChart = () => {
    nextTick(() => {
      const el = faultChartRef.value
      if (!el) return
      const chart = getChart(el)
      const codes = Object.keys(faultChartData.value)
      if (codes.length === 0) {
        chart.clear()
        return
      }
      const colors = ['#EF4444', '#F59E0B', '#1E6FFF', '#8B5CF6', '#00B365']
      const times = [
        ...new Set(
          codes.flatMap((code) => (faultChartData.value[code] ?? []).map((point) => point.time)),
        ),
      ].sort()
      const series = codes.map((code, index) => ({
        name: `故障码 ${code}`,
        type: 'line',
        smooth: true,
        stack: 'fault',
        lineStyle: { width: 2, color: colors[index % colors.length] ?? '#EF4444' },
        itemStyle: { color: colors[index % colors.length] ?? '#EF4444' },
        data: times.map((time) => {
          const point = (faultChartData.value[code] ?? []).find((item) => item.time === time)
          return point ? point.err_cnt : 0
        }),
      }))
      const xStep = times.length <= 10 ? 1 : Math.ceil(times.length / 10)
      setChartOption(chart, {
        tooltip: { trigger: 'axis' },
        legend: { right: 0, top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 56, right: 20, top: 32, bottom: 42 },
        xAxis: {
          type: 'category',
          data: times.map((time) => time.slice(11, 19)),
          axisLabel: {
            interval: (index: number) =>
              times.length <= 10 ||
              index === 0 ||
              index === times.length - 1 ||
              index % xStep === 0,
            fontSize: 10,
            rotate: 30,
          },
        },
        yAxis: { type: 'value', name: '次数', axisLabel: { fontSize: 10 } },
        dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 4 }],
        series,
        toolbox: {
          show: true,
          feature: {
            brush: { type: ['rect', 'clear'], title: { rect: '框选时间', clear: '清除框选' } },
          },
          right: 8,
        },
        brush: {
          xAxisIndex: 0,
          brushType: 'rect',
          brushLink: 'all',
          throttleType: 'debounce',
          throttleDelay: 300,
        },
      })
      chart.dispatchAction({
        type: 'takeGlobalCursor',
        key: 'brush',
        brushOption: { brushType: 'rect', brushMode: 'single' },
      })
      chart.off('brushEnd')
      chart.on('brushEnd', (params: any) => {
        const area = (params.areas || [])[0]
        if (!area || !Array.isArray(area.coordRange)) {
          faultTimeRange.value = null
          return
        }
        const xRange = Array.isArray(area.coordRange[0]) ? area.coordRange[0] : area.coordRange
        const startIndex = Math.max(0, Math.floor(xRange[0]))
        const endIndex = Math.min(times.length - 1, Math.ceil(xRange[1]))
        if (startIndex > endIndex || times.length === 0) {
          faultTimeRange.value = null
          return
        }
        const startTime = times[startIndex]
        const endTime = times[endIndex]
        if (startTime && endTime) {
          faultTimeRange.value = {
            start: startTime.slice(11, 19),
            end: endTime.slice(11, 19),
          }
          // 通断域 time 同步为半开区间 [start, end)：end 取下一桶起点
          const nextTime = times[endIndex + 1]
          const step = nextTime
            ? Math.max(1000, tsToEpochMs(nextTime) - tsToEpochMs(endTime))
            : 60000
          disconnectFilter.setTimeRange(tsToEpochMs(startTime), tsToEpochMs(endTime) + step)
        }
      })
    })
  }

  const renderBrpcCharts = () => {
    nextTick(() => {
      const trend = brpcTrend.value
      ;[
        { ref: brpcSuccessRef, yName: '成功率 %', data: trend.success, color: '#00B365' },
        { ref: brpcP99Ref, yName: 'P99 (ms)', data: trend.p99, color: '#EF4444' },
      ].forEach(({ ref, yName, data, color }) => {
        const el = ref.value
        if (!el) return
        const chart = getChart(el)
        setChartOption(chart, {
          tooltip: { trigger: 'axis' },
          grid: { left: 56, right: 20, top: 24, bottom: 40 },
          xAxis: { type: 'category', data: trend.times, axisLabel: { fontSize: 10 } },
          yAxis: { type: 'value', name: yName, axisLabel: { fontSize: 10 } },
          series: [
            {
              type: 'line',
              smooth: true,
              symbol: 'none',
              lineStyle: { width: 2, color },
              itemStyle: { color },
              data,
            },
          ],
        })
      })
    })
  }

  const renderAnalysisModules = () => {
    nextTick(() => {
      if (!isAssetMode.value) return
      if (isBrpcTask.value) {
        renderBrpcCharts()
        return
      }
      if (analysisTab.value === 'latency') {
        if (analysisModule.latency === 'overview') {
          renderAnomalyChart()
          renderTopology()
        } else {
          renderTrendChart()
          renderSlowChart()
        }
      } else {
        renderFaultTopology()
        renderFaultPieCharts()
        renderFaultChart()
        renderFaultPodChart()
      }
    })
  }

  const loadOverviewForTab = async () => {
    if (!isAssetMode.value) return
    if (assetTypeFilter.value === 'brpc') {
      await loadBrpcData()
      if (brpcMonitorTab.value === 'fault') await loadBrpcFaultData()
      return
    } else {
      const op = realOp.value
      await loadOverviewSection(op)
      if (analysisTab.value === 'latency') {
        if (analysisModule.latency === 'trend') {
          await loadTrendSection(op, trendPercentile.value)
          renderTrendChart()
          renderSlowChart()
        } else {
          renderAnomalyChart()
          renderTopology()
        }
      } else {
        await loadFaultSection(op)
        renderFaultTopology()
        renderFaultPieCharts()
        renderFaultChart()
        renderFaultPodChart()
      }
    }
  }

  const bindOverviewWatchers = () => {
    watch(
      [
        currentOp,
        assetTypeFilter,
        assetTab,
        analysisTab,
        () => analysisModule.latency,
        () => analysisModule.fault,
        overviewScale,
      ],
      () => {
        if (!isAssetMode.value) return
        // 操作/粒度/页签切换：重置时延域时间与对象，恢复全域时间轴
        latencyFilter.clearTime()
        latencyFilter.clearFocus()
        latencyFilter.clearWhitelist()
        analysisWindowBuckets.value = null
        void loadOverviewForTab()
      },
    )

    watch([trendVisible, trendPercentile, trendScale, trendRange], () => {
      if (isAssetMode.value && !isBrpcTask.value && analysisModule.latency === 'trend') {
        void loadTrendSection(realOp.value, trendPercentile.value).then(() => renderTrendChart())
      }
    })

    watch(
      [scopeData, brpcInterfaces, brpcTrend],
      () => {
        if (!isAssetMode.value) return
        // 概览页拓扑/时间图由下方专用 watcher 驱动，避免补数据(如进 Pod 详情)时整图重绘
        if (
          !isBrpcTask.value &&
          analysisTab.value === 'latency' &&
          analysisModule.latency === 'overview'
        ) {
          return
        }
        renderAnalysisModules()
      },
      { deep: true },
    )

    // 时间桶变化（数据加载/时间尺度/操作类型）→ 重绘时段异常强度
    watch(
      timeBuckets,
      () => {
        if (
          isAssetMode.value &&
          !isBrpcTask.value &&
          analysisTab.value === 'latency' &&
          analysisModule.latency === 'overview'
        ) {
          renderAnomalyChart()
        }
      },
      { deep: true },
    )

    // 统计方式变化 → 重绘时段异常强度（总时延线）
    watch(
      () => overview.statType,
      () => {
        if (
          isAssetMode.value &&
          !isBrpcTask.value &&
          analysisTab.value === 'latency' &&
          analysisModule.latency === 'overview'
        ) {
          renderAnomalyChart()
        }
      },
    )

    // TopK / 排序 变化 → 重算 Pod 列表并回到第 1 页
    watch([overview.topK, overview.sortBy], () => {
      podPage.value = 1
      if (
        isAssetMode.value &&
        !isBrpcTask.value &&
        analysisTab.value === 'latency' &&
        analysisModule.latency === 'overview'
      ) {
        renderTopology()
      }
    })

    // 拓扑输入或查看焦点变化 → 重绘拓扑
    watch(
      [visibleTopologyLinks, () => latencyFilter.time.value, () => latencyFilter.focus.value],
      () => {
        if (!isAssetMode.value || isBrpcTask.value) return
        if (analysisTab.value === 'latency' && analysisModule.latency === 'overview') {
          renderTopology()
        }
      },
      { deep: true },
    )

    watch(availableMetrics, (list) => {
      const present = new Set(list.map((metric) => metric.key))
      const kept = selectedMetrics.value.filter((key) => present.has(key))
      selectedMetrics.value = kept.length ? kept : list.map((metric) => metric.key)
    })

    watch(
      () => dataOptions?.getAsset()?.id,
      () => {
        clearSectionCaches()
        void loadOverviewForTab()
      },
      { immediate: true },
    )
    watch(
      () => dataOptions?.getLogFiles(),
      () => {
        const files = dataOptions?.getLogFiles() ?? []
        const key = files.map((file) => `${file.id}:${file.overall_status}`).join('|')
        if (key !== lastLogFilesKey) {
          clearSectionCaches()
          lastLogFilesKey = key
        }
        if (isAssetMode.value) void loadOverviewForTab()
      },
    )
  }

  return {
    toast,
    bindOverviewWatchers,
    selectedAsset,
    view,
    assetTab,
    ipRowRefs,
    activePairs,
    allMetrics,
    analysisModule,
    analysisTab,
    assetTypeFilter,
    brpcAbnormalThreadPage,
    brpcAbnormalThreadTotal,
    brpcAbnormalThreads,
    brpcAggregatedEventPage,
    brpcAggregatedEventTotal,
    brpcAggregatedEvents,
    brpcEventHitTotal,
    brpcFaultBatch,
    brpcFaultDetail,
    brpcThreadLogs,
    brpcThreadLogsLoading,
    brpcThreadLogsError,
    brpcFaultError,
    brpcFaultEventPages,
    brpcFaultLoading,
    brpcFaultLogOptions,
    brpcFaultPageSize,
    brpcFaultQueryRange,
    brpcFaultSelectedLogId,
    brpcFaultTab,
    brpcFaultThreadPages,
    brpcFaultTimelineRef,
    faultActivePairs,
    faultPodStats,
    faultTopoRef,
    faultPieRefs,
    renderFaultTopology,
    renderFaultPieCharts,
    latencyFilter,
    disconnectFilter,
    clearAnalysisTime,
    analysisWindowData,
    analysisWindowLoading,
    timelineTruncated,
    overviewScale,
    overviewScaleOptions,
    timeRangeLabel,
    availableMetrics,
    availableMetricCats,
    anomalySeries,
    filteredTimeBuckets,
    anomalyRef,
    timeBuckets,
    metricCategoryColor,
    metricCategoryColorOf,
    metricCategoryOf,
    metricIsCount,
    metricUnit,
    metricValueText,
    renderAnomalyChart,
    faultTraceIdsWithLatency,
    latencyTraceIdsWithFault,
    traceTags,
    podRowTags,
    brpcFaultTimelineSeries,
    brpcInterfaces,
    brpcKpi,
    brpcLoading,
    brpcMonitorError,
    brpcMonitorTab,
    brpcP99Ref,
    brpcScopeTasks,
    brpcSuccessRef,
    brpcTrend,
    changeBrpcFaultLog,
    clearFaultRange,
    clearTrend,
    currentOp,
    detailDrawerOpen,
    detailDrawerRow,
    drawerKind,
    enterPodDetail,
    enterLinkDetail,
    enterFaultDetail,
    enterFaultLinkDetail,
    objectDetail,
    objectDetailPages,
    objectDetailGoPage,
    closeObjectDetail,
    focusPairs,
    failureModeCache,
    failureModeOf,
    faultChartData,
    faultChartRef,
    faultOp,
    faultPodAgg,
    faultPodRef,
    faultTimeRange,
    faultTracePage,
    faultTracePageSize,
    faultTracePages,
    faultTraces,
    filteredFaultTraces,
    filteredPodStats,
    formatFullTime,
    getChart,
    goBrpcFaultEventsPage,
    goBrpcFaultThreadsPage,
    highlightRow,
    isAssetMode,
    isBrpcTask,
    jumpToPod,
    kpiData,
    latencyOp,
    loadBrpcData,
    loadBrpcFaultData,
    loadFailureMode,
    loadOverviewForTab,
    metricCats,
    metricLabel,
    openBrpcFaultDetail,
    openTraceDrawer,
    overview,
    overviewError,
    overviewLoading,
    pagedFaultTraces,
    pagedPodIpsCb,
    pagedPodStats,
    pagedTraceRows,
    podBreakdownSegments,
    podBreakdownTotal,
    podBreakdownTitle,
    podStageTree,
    podStageTreeTitle,
    podStageGrid,
    podStageLegend,
    podStageGridTitle,
    podStageFlow,
    podStageFullLegend,
    podIpCbPage,
    podIpCbPageSize,
    podIpCbPages,
    podIpStats,
    podPage,
    podPageSize,
    podPages,
    realOp,
    renderAnalysisModules,
    renderBrpcCharts,
    renderBrpcFaultTimeline,
    renderFaultChart,
    renderFaultPodChart,
    renderSlowChart,
    renderTopology,
    renderTrendChart,
    resetOverviewFilter,
    resetTopologyFilter,
    resetTrend,
    resolveBrpcFaultBatch,
    scopeData,
    scopeTaskCount,
    scopeTasks,
    selectAllTrend,
    selectedMetrics,
    selectedTopologyLink,
    selectedTopologyNode,
    selectTopologyLink,
    selectTopologyNode,
    showLinkEndsOnly,
    setChartOption,
    setCurrentOp,
    showPodIpCb,
    slowChartRows,
    slowRef,
    slowRows,
    slowTotal,
    toAggregatedPairs,
    toggleTrendSeries,
    topSlowSegmentConfig,
    topoHiddenCount,
    topoNodeLimit,
    topoShowAll,
    topoTotalCount,
    topologyLinks,
    visibleTopologyLinks,
    topologySummary,
    topoRef,
    traceBreakdownKeys,
    traceBreakdownTitle,
    traceCluster,
    traceClusters,
    traceDrawerLogs,
    tracePage,
    tracePageSize,
    tracePages,
    traceRows,
    traceSearch,
    traceSegments,
    traceStageRows,
    trendAnomalyHint,
    trendBuckets,
    trendCenter,
    trendChartData,
    trendMetrics,
    trendPercentile,
    trendPercentileOptions,
    trendRange,
    trendRef,
    trendScale,
    trendScaleOptions,
    trendVisible,
    uniquePodIps,
  }
}
