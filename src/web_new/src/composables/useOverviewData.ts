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
  errorText,
  formatChartTs,
  formatFullTimeLabel,
  normalizeFaultCodes,
  paginate,
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
  fetchFaultTracesByTraceIds,
  fetchFaultTraces,
  fetchLatencyTracesByTraceIds,
  fetchLatencyMetrics,
  fetchParseResultTotal,
  fetchTimeWindowAggregated,
  fetchTopSlow,
  fetchTraceLatency,
  fetchTraceLogs,
} from '../api/analysis'

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
  const hasRealData = true
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
        timeWindows = await fetchTimeWindowAggregated(asset.id, op, overviewScale.value)
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
  const showMetricCb = ref(false)
  const showPodIpCb = ref(false)
  const selectedPodIps = ref<string[]>([])
  const podIpCbPage = ref(1)
  const podIpCbPageSize = 20

  const timeBuckets = computed(() => scopeData.value.timeWindows[realOp.value] || [])
  const epochOf = (value: string) => new Date(String(value).replace(' ', 'T')).getTime()

  const overviewScaleOptions = [
    { value: 10, label: '10秒' },
    { value: 60, label: '1分钟' },
    { value: 600, label: '10分钟' },
    { value: 3600, label: '1小时' },
  ]
  const overviewScale = ref(600)
  const anomalyRef = ref<HTMLElement | null>(null)
  /** 框选聚焦的时间范围（epoch ms） */
  const overviewBrushRange = ref<{ start: number; end: number } | null>(null)

  const timeRangeLabel = computed(() => {
    if (!overviewBrushRange.value) return '全部时段'
    const fmt = (ms: number) => {
      const d = new Date(ms)
      const p = (n: number) => String(n).padStart(2, '0')
      return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
    }
    return `${fmt(overviewBrushRange.value.start)} ~ ${fmt(overviewBrushRange.value.end)}`
  })

  const clearOverviewBrush = () => {
    overviewBrushRange.value = null
  }
  const applyOverviewBrush = (range: { start: number; end: number }) => {
    overviewBrushRange.value = range
  }

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

  /** 按框选范围过滤后的时段 */
  const filteredTimeBuckets = computed(() => {
    const range = overviewBrushRange.value
    if (!range) return timeBuckets.value
    return timeBuckets.value.filter((bucket) => {
      const t = epochOf(bucket.start_time)
      return t >= range.start && t < range.end
    })
  })

  const activePairs = computed(() => toAggregatedPairs(filteredTimeBuckets.value, realOp.value))

  /** 时段异常强度（供 brush 时间轴使用，含 epoch） */
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
      label: String(bucket.start_time).slice(11, 19),
      total: bucket.total_cnt ?? 0,
      anomaly: bucket.anomaly_cnt ?? 0,
      p99: bucket.p99_total_latency ?? null,
      statValue: bucket[overviewStatField.value] ?? null,
    })),
  )

  /** 故障类型过滤：all / latency / disconnect */
  const faultTypeFilter = ref<'all' | 'latency' | 'disconnect'>('all')

  /** 统一故障时序：在每个时延桶上叠加「时延异常数 + 通断故障数」，并给 P99 */
  const _unifiedFaultSeries = computed(() => {
    const disconnectByTime = new Map<number, number>()
    Object.values(scopeData.value.faultChart || {}).forEach((points) => {
      ;(points || []).forEach((p) => {
        const t = epochOf(String(p.time || ''))
        if (Number.isNaN(t)) return
        disconnectByTime.set(t, (disconnectByTime.get(t) || 0) + (p.err_cnt || 0))
      })
    })
    return timeBuckets.value.map((bucket) => {
      const start = epochOf(bucket.start_time)
      const end = epochOf(bucket.end_time)
      let disconnect = 0
      disconnectByTime.forEach((cnt, t) => {
        if (t >= start && t < end) disconnect += cnt
      })
      return {
        time: start,
        start: bucket.start_time,
        end: bucket.end_time,
        label: String(bucket.start_time).slice(11, 19),
        total: bucket.total_cnt ?? 0,
        latencyAnomaly: bucket.anomaly_cnt ?? 0,
        disconnect,
        p99: bucket.p99_total_latency ?? null,
      }
    })
  })

  const epochInRange = (t: number) => {
    const range = overviewBrushRange.value
    return !range || (t >= range.start && t < range.end)
  }

  const pairMetricValues = (pair: any) => {
