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
    const out: Record<string, number | null> = {}
    allMetrics.forEach((metric) => {
      const value = pair[`ave_${metric.key}`]
      out[metric.key] = typeof value === 'number' && Number.isFinite(value) ? value : null
    })
    return out
  }

  /** 统一的聚合故障事件：按(时间窗, src→dst)聚合「时延异常」与「通断故障」，做唯一明细源 */
  const _aggregatedFaultEvents = computed(() => {
    const events: any[] = []
    const bucketInRange = (start: number, _end: number) => {
      const range = overviewBrushRange.value
      return !range || start >= range.start
    }
    if (faultTypeFilter.value !== 'disconnect') {
      timeBuckets.value.forEach((bucket) => {
        const start = epochOf(bucket.start_time)
        const end = epochOf(bucket.end_time)
        if (!bucketInRange(start, end)) return
        ;(bucket.ip_pairs || []).forEach((pair) => {
          if (!pair.src_ip || !pair.dst_ip) return
          events.push({
            key: `lat-${bucket.start_time}-${pair.src_ip}-${pair.dst_ip}`,
            type: 'latency',
            timeMs: start,
            timeLabel: `${bucket.start_time} ~ ${bucket.end_time}`,
            src: pair.src_ip,
            dst: pair.dst_ip,
            total: pair.log_parse_result_cnt ?? 0,
            anomaly: pair.anomaly_cnt ?? 0,
            valueMs: pair.p99_total_latency ?? pair.ave_total_latency,
            codes: pair.anomaly_cnt > 0 ? ['异常'] : [],
            metricValues: pairMetricValues(pair),
            raw: pair,
          })
        })
      })
    }
    if (faultTypeFilter.value !== 'latency') {
      const map = new Map<string, any>()
      ;(scopeData.value.faultTraces || []).forEach((r) => {
        const t = epochOf(String(r.timestamp || r.window_start_time || ''))
        if (Number.isNaN(t) || !epochInRange(t)) return
        const src = r.src_ip || ''
        const dst = r.dst_ip || ''
        const key = `${t}-${src}-${dst}`
        if (!map.has(key)) {
          map.set(key, {
            key: `fault-${t}-${src}-${dst}`,
            type: 'disconnect',
            timeMs: t,
            timeLabel: String(r.timestamp || r.window_start_time || ''),
            src,
            dst,
            total: 0,
            anomaly: 0,
            valueMs: null,
            codes: new Set<string>(),
            metricValues: null,
            traces: [],
          })
        }
        const e = map.get(key)!
        e.total += 1
        e.anomaly += 1
        normalizeFaultCodes(r.status_code).forEach((code) => e.codes.add(code))
        e.traces.push(r)
      })
      map.forEach((e) => {
        events.push({ ...e, codes: [...e.codes] })
      })
    }
    let result = events.sort((a, b) => b.timeMs - a.timeMs)
    if (selectedPodIps.value.length > 0) {
      const selected = new Set(selectedPodIps.value)
      result = result.filter((e) => selected.has(e.src) || selected.has(e.dst))
    }
    return result
  })

  const selectedFaultEvent = ref<any>(null)
  const _selectFaultEvent = (event: any) => {
    selectedFaultEvent.value = event
  }

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
    if (selectedPodIps.value.length > 0) {
      list = list.filter((stat) => selectedPodIps.value.includes(stat.ip))
    }
    if (overview.sortBy) {
      const parts = overview.sortBy.split('_')
      const field = parts[0] ?? ''
      const order = parts[1] ?? ''
      list = [...list].sort((a, b) =>
        order === 'desc' ? (b[field] || 0) - (a[field] || 0) : (a[field] || 0) - (b[field] || 0),
      )
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
      return {
        totalTraces: scopeData.value.kpi.faultTraceSetTotal || 0,
        anomalyTraces: codes.length,
        anomalyRate: '—' as string | number,
        podIpCount: kpi.podCount || 0,
        worstPodIp: codes.length ? '故障码 ' + codes.join(' / ') : '—',
        worstP99: codes.length ? 'SET' : '',
      }
    }
    const rate = kpi.traceTotal ? ((kpi.anomalyTotal / kpi.traceTotal) * 100).toFixed(1) : '0.0'
    const worst = activePairs.value.reduce(
      (best, pair) => (Number(pair.urmaTotal) > Number(best.urmaTotal) ? pair : best),
      activePairs.value[0] || ({} as AggregatedPair),
    )
    return {
      totalTraces: kpi.traceTotal,
      anomalyTraces: kpi.anomalyTotal,
      anomalyRate: rate,
      podIpCount: kpi.podCount,
      worstPodIp: worst.src || '-',
      worstP99: worst.urmaTotal != null ? String(worst.urmaTotal) : '-',
    }
  })

  const resetOverviewFilter = () => {
    overview.topK = 10
    overview.operation = ''
    overview.sortBy = ''
    overview.statType = 'p99'
    selectedPodIps.value = []
    overviewScale.value = 600
    overviewBrushRange.value = null
    faultTypeFilter.value = 'all'
    topoShowAll.value = false
    selectedTopologyLinkKey.value = ''
    selectedTopologyNodeIp.value = ''
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

  const getAdaptiveBucketMs = (times: number[]) => {
    if (times.length <= 1) return 10000
    const span = Math.max(Math.max(...times) - Math.min(...times), 10000)
    const candidates = [1000, 2000, 5000, 10000, 30000, 60000, 300000, 600000, 1800000, 3600000]
    return (
      candidates.find((bucket) => {
        const count = Math.ceil(span / bucket)
        return count >= 2 && count <= 120
      }) ??
      candidates.find((bucket) => Math.ceil(span / bucket) <= 120) ??
      3600000
    )
  }

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
