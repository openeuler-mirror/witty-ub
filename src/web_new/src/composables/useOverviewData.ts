import {
  computed,
  effectScope,
  getCurrentScope,
  nextTick,
  reactive,
  ref,
  shallowRef,
  watch,
} from 'vue'
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
  LogType,
  ScopeData,
  TimeWindowBucket,
} from '../types'
import {
  epochMsToTs,
  errorText,
  formatChartTs,
  formatFullTimeLabel,
  normalizeFaultCodes,
  normalizeFailureModeErrorCode,
  paginate,
  tsToEpochMs,
} from '../utils/format'
import {
  fetchAbnormalTraces,
  fetchBrpcAbnormalThreads,
  fetchBrpcBatch,
  fetchBrpcBatchMeta,
  fetchBrpcEventDetail,
  fetchBrpcInterfaceTimeline,
  fetchBrpcPodEvents,
  fetchBrpcProfilingKnowledge,
  fetchBrpcThreadDetail,
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
  fetchSrcDstAggregatedFailureEvents,
  fetchTimeAggregatedFailureEvents,
  fetchTimeWindowAggregated,
  fetchTopSlow,
  fetchTraceLatency,
  fetchTraceLogs,
  searchFaultTracesByTraceId,
} from '../api/analysis'
import { createAnalysisFilter, type AnalysisFocus } from './useAnalysisFilter'

export type UseOverviewDataOptions = {
  getAsset: () => LogKnowledge | null
  getLogFiles: () => LogFileModel[]
  // 当前任务列表所属的资产库 id（切库瞬间用于判定任务与资产是否匹配）
  getLogFilesAssetId?: () => string
  // 任务列表是否仍在加载（未返回前不发按库查询）
  getLogFilesLoading?: () => boolean
}

// dataOptions 用 shallowRef 承载：computed 依赖它，避免 state 先于 options 创建时
// 把「options 缺失」的空结果固化进缓存（P1.1 总览外调用 useOverviewData 触发）
const dataOptionsRef = shallowRef<UseOverviewDataOptions | null>(null)
const dataOptions = computed(() => dataOptionsRef.value)
let overviewState: ReturnType<typeof createOverviewStateInner> | null = null

export function useOverviewData(options?: UseOverviewDataOptions) {
  if (options) dataOptionsRef.value = options
  if (!overviewState) overviewState = createOverviewState()
  return overviewState
}

/**
 * 总览状态是模块级单例，但 OverviewPanel 会随「返回资产列表 / 切到任务页」卸载。
 * 因此所有 watcher 必须挂在脱离组件实例的 effect scope 上：
 * 否则首次挂载创建的 watcher 会在卸载时被 Vue 自动停止，而 bindOverviewWatchers
 * 的幂等守卫不会再次绑定，导致再次进入资产库后不再自动加载（串数据 / 图表丢失）。
 */
function createOverviewState() {
  const scope = effectScope(true)
  return scope.run(() => createOverviewStateInner())!
}

function createOverviewStateInner() {
  // 状态创建时所在的 effect scope：createOverviewState 传入的是脱离组件的 scope，
  // bindOverviewWatchers 必须在这个 scope 里绑定 watcher（它由组件调用，
  // 否则 watcher 会挂到组件实例上，组件卸载即失效）。
  const overviewScope = getCurrentScope() ?? effectScope(true)
  const selectedAsset = computed(() => dataOptions.value?.getAsset() ?? null)
  const logFiles = computed(() => dataOptions.value?.getLogFiles() ?? [])
  // 任务列表所属资产库：与 selectedAsset 不一致时（切库后新任务列表尚未到达）
  // 一律不做按库查询，避免用上一个资产库的任务当分析口径
  const scopedAssetId = computed(() => dataOptions.value?.getLogFilesAssetId?.() ?? '')
  const tracksLogFilesOwner = computed(() => Boolean(dataOptions.value?.getLogFilesAssetId))
  // 任务列表是否仍在返回：为真时任何按库查询都推迟到 logFiles watcher
  const logFilesPending = computed(() =>
    Boolean(dataOptions.value?.getLogFilesLoading?.() ?? false),
  )
  const assetScoped = computed(() => {
    const asset = selectedAsset.value
    if (!asset) return false
    // 未提供属主 getter 的调用方（单测等）按“已匹配”处理
    if (!tracksLogFilesOwner.value) return true
    return scopedAssetId.value === asset.id
  })
  const view = ref<'assets' | 'home'>('home')
  const assetTab = ref<'overview' | 'tasks'>('overview')
  const { toast } = useToast()
  const isSuccess = (file: LogFileModel) =>
    ['successful', 'successful_pending_remove'].includes(file.overall_status || '')

  // ============ 图表绘制调度（必须排在 DOM 补丁之后） ============
  // 直接调用 nextTick 可能在「loading 占位 → 真实图表容器」这次 flush 之前执行，
  // 此时模板 ref 仍为 null，图表会被静默丢弃（表现为图区空白）。
  // 统一用 post 阶段 watcher 收口：数据/占位状态与 DOM 都稳定后才绘制。
  const pendingChartRenders = new Set<() => void>()
  const chartRenderTicket = ref(0)
  const afterDomUpdate = (draw: () => void) => {
    pendingChartRenders.add(draw)
    chartRenderTicket.value += 1
  }
  watch(
    chartRenderTicket,
    () => {
      const scheduled = [...pendingChartRenders]
      pendingChartRenders.clear()
      scheduled.forEach((draw) => draw())
    },
    { flush: 'post' },
  )

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
    faultTraces: new Map<string, { total: number; rows: any[]; truncated: boolean }>(),
  }
  let lastLogFilesKey = ''
  // 切库后等新任务列表到达，再决定默认数据域（见 logFiles watcher）
  let domainAutoSelectPending = false
  let overviewRequestGeneration = 0
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
  const faultTracesTruncated = ref(false)

  const assetTypeFilter = ref<'kvcache' | 'brpc'>('kvcache')
  const analysisTab = ref<'latency' | 'disconnect'>('latency')
  const analysisModule = reactive({
    latency: 'overview',
    disconnect: 'faults' as 'faults' | 'events',
  })
  const latencyOp = ref('GET')
  const faultOp = ref('GET')
  const currentOp = computed(() =>
    analysisTab.value === 'latency' ? latencyOp.value : faultOp.value,
  )
  const realOp = computed<'get' | 'set'>(() => currentOp.value.toLowerCase() as 'get' | 'set')
  const isAssetMode = computed(() => view.value === 'home' && assetTab.value === 'overview')
  const isBrpcTask = computed(() => assetTypeFilter.value === 'brpc')
  const selectedLogType = computed<LogType>(() =>
    assetTypeFilter.value === 'brpc' ? 'UBSocket' : 'KVCache',
  )
  const scopeTasks = computed(() =>
    assetScoped.value
      ? logFiles.value.filter((file) => file.log_type === selectedLogType.value && isSuccess(file))
      : [],
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
    faultTracesTruncated.value = false
  }

  const loadOverviewSection = async (op: 'get' | 'set', generation = overviewRequestGeneration) => {
    const asset = selectedAsset.value
    if (!asset) return

    // P1.5：KVCache 时延域按日志文件收窄，logId 参与 key 与请求
    const logId = latencyFilter.logId.value
    // 缓存 key 必须带资产库 id：切库后同一个 op/尺度不能复用上一个库的聚合结果
    const scaleKey = `${asset.id}:${op}:${overviewScale.value}:${logId ?? ''}`
    let timeWindows = sectionCaches.timeWindows.get(scaleKey)
    if (!timeWindows) {
      overviewLoading.value = true
      overviewError.value = ''
      try {
        const { rows, truncated } = await fetchTimeWindowAggregated(asset.id, op, {
          interval: overviewScale.value,
          logId,
        })
        if (generation !== overviewRequestGeneration) return
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

    let kpi = sectionCaches.kpi.get(scaleKey)
    if (!kpi) {
      const podSet = new Set<string>()
      aggregated.forEach((pair) => {
        podSet.add(pair.src)
        podSet.add(pair.dst)
      })
      const [traceTotal, anomalyTotal] = await Promise.all([
        fetchParseResultTotal(asset.id, op, undefined, logId),
        fetchParseResultTotal(asset.id, op, true, logId),
      ])
      if (generation !== overviewRequestGeneration) return
      kpi = { traceTotal, anomalyTotal, podCount: podSet.size }
      sectionCaches.kpi.set(scaleKey, kpi)
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

  // 趋势分位数据必须单日志（后端 metrics/latency 分位统计表按日志物化，无法跨任务合并）。
  // 对齐旧版：未选日志时自动兜底第一个已完成任务，而不是要求用户手选
  const trendLogId = computed(() => latencyFilter.logId.value ?? scopeTasks.value[0]?.id)
  const trendLogLabel = computed(() => {
    const id = trendLogId.value
    if (!id) return ''
    const file = logFiles.value.find((item) => item.id === id)
    return file?.name || id
  })

  const loadTrendSection = async (
    op: 'get' | 'set',
    pct: string,
    generation = overviewRequestGeneration,
  ) => {
    const asset = selectedAsset.value
    if (!asset) return

    // P1.5：与总览共用 latencyFilter.logId，参与 key 与请求。
    // 趋势分位曲线单日志取数（未选时 trendLogId 兜底首个已完成任务）；
    // 最慢请求与异常 Trace 列表不受影响，仍按用户选择支持跨任务汇总
    const logId = latencyFilter.logId.value
    const effectiveLogId = trendLogId.value
    let latency: any[] = []
    if (effectiveLogId) {
      const latencyKey = `${asset.id}:${op}:${pct}:${trendScale.value}:${effectiveLogId}`
      if (sectionCaches.latency.has(latencyKey)) {
        latency = sectionCaches.latency.get(latencyKey)!
      } else {
        latency = await fetchLatencyMetrics(asset.id, op, pct, effectiveLogId, trendScale.value)
        if (generation !== overviewRequestGeneration) return
        sectionCaches.latency.set(latencyKey, latency)
      }
    }

    const trendListKey = `${asset.id}:${op}:${logId ?? ''}`
    let topSlow = sectionCaches.topSlow.get(trendListKey)
    if (!topSlow) {
      topSlow = await fetchTopSlow(asset.id, op, logId)
      if (generation !== overviewRequestGeneration) return
      sectionCaches.topSlow.set(trendListKey, topSlow)
    }

    let abnormal = sectionCaches.abnormal.get(trendListKey)
    if (!abnormal) {
      abnormal = await fetchAbnormalTraces(asset.id, op, logId)
      if (generation !== overviewRequestGeneration) return
      sectionCaches.abnormal.set(trendListKey, abnormal)
    }
    if (overlapLoadedFor.latency !== op) {
      const traceIds = (abnormal?.rows ?? [])
        .map((row: any) => row.trace_id)
        .filter((id: string | undefined): id is string => !!id)
      if (traceIds.length > 0) {
        try {
          const faultResult = await fetchFaultTracesByTraceIds(asset.id, traceIds, logId)
          if (generation !== overviewRequestGeneration) return
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

    if (generation !== overviewRequestGeneration) return

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

  const loadFaultSection = async (op: 'get' | 'set', generation = overviewRequestGeneration) => {
    const asset = selectedAsset.value
    if (!asset) return

    const faultKey = `${asset.id}:${op}`
    let faultChart = sectionCaches.faultChart.get(faultKey)
    if (!faultChart) {
      faultChart = await fetchFaultChart(asset.id, op)
      if (generation !== overviewRequestGeneration) return
      sectionCaches.faultChart.set(faultKey, faultChart)
    }

    let faultTraces = sectionCaches.faultTraces.get(faultKey)
    if (!faultTraces) {
      faultTraces = await fetchFaultTraces(asset.id, op)
      if (generation !== overviewRequestGeneration) return
      sectionCaches.faultTraces.set(faultKey, faultTraces)
    }
    faultTracesTruncated.value = faultTraces.truncated
    if (overlapLoadedFor.fault !== op) {
      const traceIds = (faultTraces?.rows ?? [])
        .map((row: any) => row.trace_id)
        .filter((id: string | undefined): id is string => !!id)
      if (traceIds.length > 0) {
        try {
          const latencyResult = await fetchLatencyTracesByTraceIds(asset.id, traceIds)
          if (generation !== overviewRequestGeneration) return
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

    if (generation !== overviewRequestGeneration) return

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

  // ---------- BRPC 接口监控（/brpc_profiling/knowledge 全量 + 文件客户端过滤，P2.1） ----------

  const brpcScopeTasks = computed(() =>
    assetScoped.value
      ? logFiles.value.filter((file) => file.log_type === 'UBSocket' && isSuccess(file))
      : [],
  )
  const brpcLoading = ref(false)
  const brpcMonitorError = ref('')

  type BrpcProfilingFileOption = {
    log_id: string
    log_name?: string | null
    source_file?: string | null
  }
  const brpcProfilingFiles = ref<BrpcProfilingFileOption[]>([])
  const brpcAllProfilingRows = ref<any[]>([])
  const brpcSelectedFileKey = ref('')
  let brpcProfilingSeq = 0

  const brpcFileKey = (file: BrpcProfilingFileOption) =>
    JSON.stringify([file.log_id, file.source_file ?? ''])
  const brpcFileLabel = (file: BrpcProfilingFileOption) =>
    `${file.log_name || file.log_id} / ${file.source_file || '未命名 profiling 文件'}`

  // 与旧版一致：文件选择只客户端过滤已加载 rows，不按文件重拉
  const brpcFileRows = computed(() => {
    const selected = brpcProfilingFiles.value.find(
      (file) => brpcFileKey(file) === brpcSelectedFileKey.value,
    )
    if (!selected) return []
    return brpcAllProfilingRows.value.filter(
      (row) =>
        row.log_id === selected.log_id && (row.source_file ?? '') === (selected.source_file ?? ''),
    )
  })

  // 当前文件 rows → 接口明细表与两张总趋势
  const brpcInterfaces = computed(() => {
    const ifaceMap = new Map<string, any>()
    for (const row of brpcFileRows.value) {
      const iface = row.interface_name
      if (!iface) continue
      const req = (row.success_count ?? 0) + (row.failure_count ?? 0)
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
      item.successCount += row.success_count ?? 0
      item.failureCount += row.failure_count ?? 0
      item.avg_ns = Math.max(item.avg_ns, row.avg_ns ?? 0)
      item.p99_ns = Math.max(item.p99_ns, row.p99_ns ?? 0)
      item.max_ns = Math.max(item.max_ns, row.max_ns ?? 0)
    }
    return [...ifaceMap.values()]
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
  })

  const brpcTrend = computed(() => {
    const timeMap = new Map<string, { req: number; ok: number; p99: number }>()
    for (const row of brpcFileRows.value) {
      const ts = row.timestamp
      if (!ts) continue
      const key = String(ts).slice(0, 19)
      if (!timeMap.has(key)) timeMap.set(key, { req: 0, ok: 0, p99: 0 })
      const bucket = timeMap.get(key)!
      const req = (row.success_count ?? 0) + (row.failure_count ?? 0)
      bucket.req += req
      bucket.ok += row.success_count ?? 0
      bucket.p99 = Math.max(bucket.p99, (row.p99_ns ?? 0) / 1e6)
    }
    const times = [...timeMap.keys()].sort()
    return {
      times: times.map((time) => formatChartTs(time)),
      success: times.map((time) => {
        const bucket = timeMap.get(time)!
        return bucket.req ? +((bucket.ok / bucket.req) * 100).toFixed(2) : 0
      }),
      p99: times.map((time) => timeMap.get(time)!.p99),
    }
  })

  // 单接口曲线选择状态（P2.1）
  type BrpcSuccessMetric =
    | 'successRate'
    | 'failureRate'
    | 'requestCount'
    | 'successCount'
    | 'failureCount'
  const brpcSuccessMetric = ref<BrpcSuccessMetric>('successRate')
  const brpcSuccessMetricOptions: Array<{ value: BrpcSuccessMetric; label: string }> = [
    { value: 'successRate', label: '成功率' },
    { value: 'failureRate', label: '失败率' },
    { value: 'requestCount', label: '请求数' },
    { value: 'successCount', label: '成功量' },
    { value: 'failureCount', label: '失败量' },
  ]
  const brpcIfaceNames = computed(() =>
    [...new Set(brpcFileRows.value.map((row) => row.interface_name).filter(Boolean))].sort(),
  )
  const brpcSuccessSelectedIfaces = ref<string[]>([])
  const brpcSingleIface = ref('')

  // U1：接口配色与勾选色点一致（对齐旧版 BRPC_INTERFACE_COLORS，21 色覆盖全部接口）
  const BRPC_INTERFACE_COLORS = [
    '#5470c6',
    '#91cc75',
    '#fac858',
    '#ee6666',
    '#73c0de',
    '#3ba272',
    '#fc8452',
    '#9a60b4',
    '#ea7ccc',
    '#48b8d0',
    '#f6a25c',
    '#6f7bd7',
    '#c15c5c',
    '#6aa0d8',
    '#b5c46b',
    '#d48265',
    '#91c7ae',
    '#749f83',
    '#ca8622',
    '#bda29a',
    '#6e7074',
  ]
  const brpcIfaceColor = (iface: string) => {
    const index = brpcIfaceNames.value.indexOf(iface)
    return BRPC_INTERFACE_COLORS[index >= 0 ? index % BRPC_INTERFACE_COLORS.length : 20]
  }

  // U1b：单接口监控的指标多选（对齐旧版 brpcSingleMetrics）
  const BRPC_SINGLE_METRIC_COLORS: Record<string, string> = {
    requestCount: '#5470c6',
    successRate: '#91cc75',
    failureRate: '#ee6666',
    successCount: '#fac858',
    failureCount: '#73c0de',
  }
  const brpcSingleMetrics = brpcSuccessMetricOptions
  const brpcSingleSelectedMetrics = ref<string[]>(['requestCount', 'successRate', 'failureRate'])
  const brpcSingleMetricColor = (metric: string) => BRPC_SINGLE_METRIC_COLORS[metric] ?? '#94a3b8'
  const isBrpcRateMetric = (metric: string) =>
    metric === 'successRate' || metric === 'failureRate'

  // U1c：时延监控（µs）指标与多接口勾选（对齐旧版 brpcLatencyMetrics）
  const brpcLatencyMetrics = [
    { value: 'total_ns', label: 'total' },
    { value: 'avg_ns', label: 'avg' },
    { value: 'max_ns', label: 'max' },
    { value: 'min_ns', label: 'min' },
    { value: 'p50_ns', label: 'P50' },
    { value: 'p90_ns', label: 'P90' },
    { value: 'p95_ns', label: 'P95' },
    { value: 'p99_ns', label: 'P99' },
    { value: 'p999_ns', label: 'P999' },
  ]
  const brpcLatencyMetric = ref('avg_ns')
  const brpcLatencySelectedIfaces = ref<string[]>([])

  // 文件存在但该文件没有任何 profiling 行 → 「当前筛选时间范围内无数据」（对齐上游 0e663a22）
  const brpcHasRows = computed(() => brpcFileRows.value.length > 0)

  const brpcRowMetric = (row: any, metric: BrpcSuccessMetric): number => {
    const ok = row.success_count ?? 0
    const fail = row.failure_count ?? 0
    const req = ok + fail
    switch (metric) {
      case 'successRate':
        return req ? +((ok / req) * 100).toFixed(2) : 0
      case 'failureRate':
        return req ? +((fail / req) * 100).toFixed(2) : 0
      case 'requestCount':
        return req
      case 'successCount':
        return ok
      case 'failureCount':
        return fail
    }
  }

  const brpcIfaceTimestamps = computed(() =>
    [
      ...new Set(
        brpcFileRows.value.map((row) => String(row.timestamp ?? '').slice(0, 19)).filter(Boolean),
      ),
    ].sort(),
  )

  const loadBrpcData = async () => {
    const asset = selectedAsset.value
    if (!asset) return
    const seq = ++brpcProfilingSeq
    brpcLoading.value = true
    brpcMonitorError.value = ''
    // 无已完成 UBSocket 任务时不发请求（必然 404），空态由 brpcScopeTasks 判断承载
    if (brpcScopeTasks.value.length === 0) {
      brpcProfilingFiles.value = []
      brpcAllProfilingRows.value = []
      brpcSelectedFileKey.value = ''
      brpcLoading.value = false
      await loadBrpcFaultData()
      renderAnalysisModules()
      return
    }
    try {
      const result = await fetchBrpcProfilingKnowledge(asset.id)
      if (seq !== brpcProfilingSeq) return
      brpcProfilingFiles.value = result.files ?? []
      brpcAllProfilingRows.value = result.rows ?? []
      // 默认选择第一个 profiling 文件；日志包 ID 参与 key，避免同名文件混合
      if (
        brpcProfilingFiles.value.length > 0 &&
        !brpcProfilingFiles.value.some((file) => brpcFileKey(file) === brpcSelectedFileKey.value)
      ) {
        brpcSelectedFileKey.value = brpcFileKey(brpcProfilingFiles.value[0]!)
      }
    } catch (error) {
      if (seq !== brpcProfilingSeq) return
      // 「数据不存在」对资产是正常空态（任务未产生 profiling），不作为错误展示
      const message = errorText(error)
      if (!message.includes('数据不存在')) brpcMonitorError.value = message
      brpcProfilingFiles.value = []
      brpcAllProfilingRows.value = []
      brpcSelectedFileKey.value = ''
    } finally {
      if (seq === brpcProfilingSeq) brpcLoading.value = false
    }
    await loadBrpcFaultData()
    renderAnalysisModules()
  }

  // 文件变化：曲线勾选与单接口选择重置为当前文件接口全集/首个
  watch(brpcIfaceNames, (names) => {
    brpcSuccessSelectedIfaces.value = brpcSuccessSelectedIfaces.value.filter((name) =>
      names.includes(name),
    )
    if (brpcSuccessSelectedIfaces.value.length === 0) brpcSuccessSelectedIfaces.value = [...names]
    brpcLatencySelectedIfaces.value = brpcLatencySelectedIfaces.value.filter((name) =>
      names.includes(name),
    )
    if (brpcLatencySelectedIfaces.value.length === 0) brpcLatencySelectedIfaces.value = [...names]
    if (!names.includes(brpcSingleIface.value)) brpcSingleIface.value = names[0] ?? ''
  })

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
  // P2.4 异常 Thread 服务端搜索（线程 ID / Pod IP / Pod 名）
  const brpcThreadSearchInput = ref('')
  const brpcThreadSearchQuery = ref('')
  const brpcFaultLoading = ref(false)
  const brpcFaultError = ref('')
  const brpcFaultDetail = ref<any>(null)
  const brpcFaultBatchId = ref('')
  const brpcThreadLogs = ref<any[]>([])
  const brpcThreadLogsLoading = ref(false)
  const brpcThreadLogsError = ref('')
  // P2.3 线程详情（failure_graph / interface_timeline / failure_modes）
  const brpcThreadDetail = ref<any>(null)
  const brpcThreadDetailLoading = ref(false)
  const brpcThreadDetailError = ref('')
  const brpcSelectedGraphNodeId = ref('')
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
    afterDomUpdate(() => {
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

  // P2.3 线程详情：failure_graph 节点/边图（点击节点查看故障模式）
  const brpcSelectedGraphNode = computed(() => {
    const id = brpcSelectedGraphNodeId.value
    if (!id) return null
    return (
      brpcThreadDetail.value?.failure_graph?.nodes?.find((node: any) => node.node_id === id) ?? null
    )
  })

  const renderBrpcThreadGraph = () => {
    afterDomUpdate(() => {
      const el = brpcThreadGraphRef.value
      if (!el) return
      const chart = getChart(el)
      const graph = brpcThreadDetail.value?.failure_graph
      if (!graph || !graph.nodes?.length) {
        chart.clear()
        return
      }
      const maxHits = Math.max(...graph.nodes.map((node: any) => node.hit_count ?? 0), 1)
      setChartOption(chart, {
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => {
            if (params.dataType !== 'node') return ''
            const data = params.data
            return data.nodeType === 'interface'
              ? `<b>${data.nodeName}</b>${data.functionName ? `<br/>${data.functionName}` : ''}`
              : `<b>${data.nodeName}</b><br/>命中 ${data.hitCount ?? 0} 次`
          },
        },
        series: [
          {
            type: 'graph',
            layout: 'force',
            roam: true,
            draggable: true,
            edgeSymbol: ['none', 'arrow'],
            edgeSymbolSize: 7,
            force: { repulsion: 420, edgeLength: [90, 210], gravity: 0.12 },
            data: graph.nodes.map((node: any) => ({
              name: node.node_id,
              nodeId: node.node_id,
              nodeType: node.node_type,
              nodeName: node.name || node.node_id,
              functionName: node.function_name,
              hitCount: node.hit_count,
              symbolSize:
                node.node_type === 'interface' ? 28 : 22 + ((node.hit_count ?? 0) / maxHits) * 30,
              itemStyle: {
                color: node.node_type === 'interface' ? '#1E6FFF' : '#EF4444',
                borderColor: node.directly_hit ? '#7f1d1d' : undefined,
                borderWidth: node.directly_hit ? 3 : 1,
              },
              label: {
                show: true,
                fontSize: 10,
                formatter: (param: any) => String(param.data.nodeName ?? '').slice(0, 18),
              },
            })),
            links: (graph.edges || []).map((edge: any) => ({
              source: edge.source_node_id,
              target: edge.target_node_id,
              lineStyle: {
                curveness: 0.15,
                opacity: 0.85,
                width: edge.edge_type === 'cross_component' ? 2.4 : 1.4,
              },
            })),
            emphasis: { focus: 'adjacency' },
          },
        ],
      })
      chart.off('click')
      chart.on('click', (params: any) => {
        if (params.dataType !== 'node') return
        brpcSelectedGraphNodeId.value =
          brpcSelectedGraphNodeId.value === params.data.nodeId ? '' : params.data.nodeId
      })
    })
  }

  // P2.3 线程详情：接口命中时序（1m 粒度）
  const renderBrpcThreadTimeline = () => {
    afterDomUpdate(() => {
      const el = brpcThreadTimelineRef.value
      if (!el) return
      const chart = getChart(el)
      const seriesList = brpcThreadDetail.value?.interface_timeline ?? []
      const times = [
        ...new Set(
          seriesList.flatMap((series: any) =>
            (series.points || []).map((point: any) => point.window_start_time),
          ),
        ),
      ].sort()
      setChartOption(chart, {
        tooltip: { trigger: 'axis' },
        legend: { right: 0, top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 56, right: 20, top: 32, bottom: 42 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(String(time))),
          axisLabel: { fontSize: 10, rotate: 30 },
        },
        yAxis: { type: 'value', name: '命中数', minInterval: 1, axisLabel: { fontSize: 10 } },
        series: seriesList.map((series: any) => ({
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

  // P2.2 事件详情：当前窗内接口故障时序（10s 粒度）
  const renderBrpcEventTimeline = () => {
    afterDomUpdate(() => {
      const el = brpcEventTimelineRef.value
      if (!el) return
      const chart = getChart(el)
      const seriesList = brpcEventDetailTimeline.value
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
        grid: { left: 56, right: 20, top: 32, bottom: 42 },
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
          { search: brpcThreadSearchQuery.value || undefined },
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

  // P2.4 异常 Thread 搜索：提交/清空均重置页码并重拉
  const submitBrpcThreadSearch = async () => {
    brpcThreadSearchQuery.value = brpcThreadSearchInput.value.trim()
    brpcAbnormalThreadPage.value = 1
    await loadBrpcFaultData()
  }

  const clearBrpcThreadSearch = async () => {
    if (!brpcThreadSearchInput.value && !brpcThreadSearchQuery.value) return
    brpcThreadSearchInput.value = ''
    brpcThreadSearchQuery.value = ''
    brpcAbnormalThreadPage.value = 1
    await loadBrpcFaultData()
  }

  const brpcFaultEventPages = computed(() =>
    Math.max(1, Math.ceil(brpcAggregatedEventTotal.value / brpcFaultPageSize)),
  )
  const brpcFaultThreadPages = computed(() =>
    Math.max(1, Math.ceil(brpcAbnormalThreadTotal.value / brpcFaultPageSize)),
  )

  // ---------- P2.2 聚合事件详情（组件计数 / 当前窗时序 / 关联线程） ----------

  const brpcEventDetail = ref<any>(null)
  const brpcEventDetailTimeline = ref<any[]>([])
  const brpcEventDetailThreads = ref<any[]>([])
  const brpcEventDetailLoading = ref(false)
  const brpcEventDetailError = ref('')
  let brpcEventDetailSeq = 0

  const loadBrpcEventDetail = async (row: any) => {
    const batchId = brpcFaultBatchId.value
    if (!batchId || !row?.event_id) return
    const startMs = tsToEpochMs(row.window_start_time)
    const endMs = tsToEpochMs(row.window_end_time)
    if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) {
      brpcEventDetailError.value = '聚合事件窗口时间无效'
      return
    }
    const seq = ++brpcEventDetailSeq
    brpcEventDetailLoading.value = true
    brpcEventDetailError.value = ''
    brpcEventDetail.value = null
    brpcEventDetailTimeline.value = []
    brpcEventDetailThreads.value = []
    try {
      const scope = {
        podIp: row.pod_ip,
        podName: row.pod_name || undefined,
      }
      const [detail, threadsResult, timelineResult] = await Promise.all([
        fetchBrpcEventDetail(batchId, row.event_id, {
          window_start_time: row.window_start_time,
          window_end_time: row.window_end_time,
          pod_ip: row.pod_ip,
          pod_name: row.pod_name || undefined,
          thread_id: typeof row.thread_id === 'number' ? row.thread_id : undefined,
        }),
        fetchBrpcAbnormalThreads(batchId, new Date(startMs), new Date(endMs), 1, 100, scope),
        fetchBrpcInterfaceTimeline(batchId, new Date(startMs), new Date(endMs), '10s', scope),
      ])
      if (seq !== brpcEventDetailSeq) return
      brpcEventDetail.value = detail
      brpcEventDetailThreads.value = (threadsResult.threads ?? []).filter(
        (thread: any) => typeof row.thread_id !== 'number' || thread.thread_id === row.thread_id,
      )
      brpcEventDetailTimeline.value = timelineResult.series ?? []
      renderBrpcEventTimeline()
    } catch (error) {
      if (seq !== brpcEventDetailSeq) return
      brpcEventDetailError.value = errorText(error)
    } finally {
      if (seq === brpcEventDetailSeq) brpcEventDetailLoading.value = false
    }
  }

  const openBrpcFaultDetail = (row: any) => {
    brpcFaultDetail.value = row
    brpcThreadLogs.value = []
    brpcThreadLogsError.value = ''
    brpcEventDetail.value = null
    brpcEventDetailTimeline.value = []
    brpcEventDetailThreads.value = []
    brpcEventDetailError.value = ''
    brpcThreadDetail.value = null
    brpcThreadDetailError.value = ''
    brpcSelectedGraphNodeId.value = ''
    // 聚合事件行（无 thread_key）：加载组件计数 / 当前窗时序 / 关联线程（P2.2）
    if (row && !row.thread_key) {
      void loadBrpcEventDetail(row)
      return
    }
    // 仅异常 Thread 行（带 thread_key）并行加载运行日志与 P2.3 线程详情
    if (!row?.thread_key || row?.thread_id == null || !row?.pod_ip) return
    const batch = brpcFaultBatch.value
    const batchId = brpcFaultBatchId.value
    if (!batch || !batchId) return
    const seq = ++brpcThreadLogsRequestSeq
    brpcThreadLogsLoading.value = true
    brpcThreadDetailLoading.value = true
    void (async () => {
      try {
        const { startDate, endDate } = brpcFaultQueryRange(batch)
        const startTime = formatFullTimeLabel(startDate)
        const endTime = formatFullTimeLabel(endDate)
        const [logsResult, detailResult] = await Promise.all([
          fetchBrpcThreadLogs(batchId, {
            pod_ip: row.pod_ip,
            thread_id: Number(row.thread_id),
            start_time: startTime,
            end_time: endTime,
            pod_name: row.pod_name || undefined,
          }),
          fetchBrpcThreadDetail(batchId, row.thread_key, {
            pod_ip: row.pod_ip,
            thread_id: Number(row.thread_id),
            start_time: startTime,
            end_time: endTime,
            window_size: '1m',
            pod_name: row.pod_name || undefined,
          }),
        ])
        if (seq !== brpcThreadLogsRequestSeq) return
        brpcThreadLogs.value = logsResult.hits ?? []
        brpcThreadDetail.value = detailResult
        renderBrpcThreadGraph()
        renderBrpcThreadTimeline()
      } catch (error) {
        if (seq !== brpcThreadLogsRequestSeq) return
        brpcThreadDetailError.value = errorText(error)
      } finally {
        if (seq === brpcThreadLogsRequestSeq) {
          brpcThreadLogsLoading.value = false
          brpcThreadDetailLoading.value = false
        }
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
    const seq = ++analysisWindowSeq
    const window = latencyFilter.timeWindow.value
    if (!window) {
      analysisWindowBuckets.value = null
      analysisWindowLoading.value = false
      return
    }
    const asset = selectedAsset.value
    if (!asset) return
    analysisWindowLoading.value = true
    try {
      const { rows } = await fetchTimeWindowAggregated(asset.id, realOp.value, {
        interval: overviewScale.value,
        startTime: epochMsToTs(window.start),
        endTime: epochMsToTs(window.end),
        logId: latencyFilter.logId.value,
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
    analysisWindowTimer = setTimeout(() => {
      analysisWindowTimer = null
      void loadAnalysisWindow()
    }, 300)
  }

  const clearAnalysisTime = () => {
    latencyFilter.clearTime()
    if (analysisWindowTimer) clearTimeout(analysisWindowTimer)
    analysisWindowTimer = null
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

  /** 通断页当前时间窗内的唯一数据源，统一使用 epoch ms 半开区间 [start, end)。 */
  const activeFaultTraces = computed(() => {
    const rows = scopeData.value.faultTraces || []
    const window = disconnectFilter.timeWindow.value
    if (!window) return rows
    return rows.filter((row) => {
      const timestamp = tsToEpochMs(String(row.timestamp || ''))
      return Number.isFinite(timestamp) && timestamp >= window.start && timestamp < window.end
    })
  })

  /** 通断主视图以故障码为第一分析维度；空字符串表示当前时段内的全部故障。 */
  const selectedFaultCode = ref('')
  const faultCodeSummaries = computed(() => {
    const summaries = new Map<
      string,
      {
        code: string
        traceCount: number
        endpoints: Set<string>
        pairs: Set<string>
        modeIds: Set<string>
        firstSeen: string
        lastSeen: string
      }
    >()
    activeFaultTraces.value.forEach((trace) => {
      const endpoints = [trace.src_ip, trace.dst_ip, ...(trace.pod_names || [])].filter(Boolean)
      const pair = trace.src_ip && trace.dst_ip ? `${trace.src_ip} → ${trace.dst_ip}` : ''
      const modeIds = String(trace.failure_mode || '')
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean)
      normalizeFaultCodes(trace.status_code).forEach((code) => {
        if (!summaries.has(code)) {
          summaries.set(code, {
            code,
            traceCount: 0,
            endpoints: new Set(),
            pairs: new Set(),
            modeIds: new Set(),
            firstSeen: '',
            lastSeen: '',
          })
        }
        const summary = summaries.get(code)!
        summary.traceCount += 1
        endpoints.forEach((ip: string) => summary.endpoints.add(ip))
        if (pair) summary.pairs.add(pair)
        modeIds.forEach((id) => summary.modeIds.add(id))
        const timestamp = String(trace.timestamp || '').slice(0, 19)
        if (timestamp && (!summary.firstSeen || timestamp < summary.firstSeen)) {
          summary.firstSeen = timestamp
        }
        if (timestamp && (!summary.lastSeen || timestamp > summary.lastSeen)) {
          summary.lastSeen = timestamp
        }
      })
    })
    return [...summaries.values()]
      .sort((a, b) => b.traceCount - a.traceCount || a.code.localeCompare(b.code))
      .map((summary) => ({
        code: summary.code,
        traceCount: summary.traceCount,
        endpointCount: summary.endpoints.size,
        pairCount: summary.pairs.size,
        modeIds: [...summary.modeIds],
        firstSeen: summary.firstSeen,
        lastSeen: summary.lastSeen,
      }))
  })
  const faultScopedTraces = computed(() => {
    if (!selectedFaultCode.value) return activeFaultTraces.value
    return activeFaultTraces.value.filter((trace) =>
      normalizeFaultCodes(trace.status_code).includes(selectedFaultCode.value),
    )
  })

  const kpiData = computed(() => {
    const kpi = scopeData.value.kpi[realOp.value] || {
      traceTotal: 0,
      anomalyTotal: 0,
      podCount: 0,
    }
    if (analysisTab.value === 'disconnect') {
      const codes = new Set<string>()
      const endpoints = new Set<string>()
      const endpointFaults = new Map<string, number>()
      activeFaultTraces.value.forEach((trace) => {
        normalizeFaultCodes(trace.status_code).forEach((code) => codes.add(code))
        const traceEndpoints = new Set<string>(
          [trace.src_ip, trace.dst_ip, ...(trace.pod_names || [])].filter(Boolean),
        )
        traceEndpoints.forEach((ip) => {
          endpoints.add(ip)
          endpointFaults.set(ip, (endpointFaults.get(ip) || 0) + 1)
        })
      })
      const worst = [...endpointFaults.entries()].sort((a, b) => b[1] - a[1])[0]
      return {
        totalTraces: activeFaultTraces.value.length,
        anomalyTraces: codes.size,
        anomalyRate: '—' as string | number,
        linkCount: new Set(
          activeFaultTraces.value
            .filter((trace) => trace.src_ip && trace.dst_ip)
            .map((trace) => `${trace.src_ip}→${trace.dst_ip}`),
        ).size,
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
      linkCount: 0,
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
    if (analysisWindowTimer) clearTimeout(analysisWindowTimer)
    analysisWindowTimer = null
    void loadAnalysisWindow()
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
  const faultTimeRange = computed(() => {
    const window = disconnectFilter.timeWindow.value
    return window ? { start: epochMsToTs(window.start), end: epochMsToTs(window.end) } : null
  })
  const faultTraceTotal = computed(() => scopeData.value.kpi.faultTraceSetTotal || 0)
  const faultTraceLoadedCount = computed(() => faultTraces.value.length)
  const clearFaultRange = () => {
    disconnectFilter.clearTime()
    const el = faultChartRef.value
    const chart = el && getInstanceByDom(el)
    if (chart) chart.dispatchAction({ type: 'brush', areas: [] })
  }

  // ---------- P1.6 通断 Trace ID 服务端查询（独立于已加载数据与截断上限） ----------

  const faultTraceIdInput = ref('')
  const faultTraceQuery = ref<{ id: string; rows: any[]; total: number } | null>(null)
  const faultTraceQueryLoading = ref(false)
  const faultTraceQueryError = ref('')
  let faultTraceQuerySeq = 0

  const queryFaultTraceById = async () => {
    const traceId = faultTraceIdInput.value.trim()
    const asset = selectedAsset.value
    if (!traceId || !asset) return
    const seq = ++faultTraceQuerySeq
    faultTraceQueryLoading.value = true
    faultTraceQueryError.value = ''
    try {
      const result = await searchFaultTracesByTraceId(asset.id, traceId, realOp.value)
      if (seq !== faultTraceQuerySeq) return
      faultTraceQuery.value = { id: traceId, rows: result.rows, total: result.total }
      faultTracePage.value = 1
    } catch (error) {
      if (seq !== faultTraceQuerySeq) return
      faultTraceQueryError.value = errorText(error)
    } finally {
      if (seq === faultTraceQuerySeq) faultTraceQueryLoading.value = false
    }
  }

  const clearFaultTraceQuery = () => {
    faultTraceQuerySeq += 1
    faultTraceQuery.value = null
    faultTraceQueryError.value = ''
    faultTraceIdInput.value = ''
    faultTracePage.value = 1
  }

  // 查询态覆盖主列表；退出查询态恢复 disconnectFilter.time 联动
  const filteredFaultTraces = computed(() => {
    const rows = faultTraceQuery.value?.rows ?? faultScopedTraces.value
    if (!selectedFaultCode.value || !faultTraceQuery.value) return rows
    return rows.filter((trace) =>
      normalizeFaultCodes(trace.status_code).includes(selectedFaultCode.value),
    )
  })

  const faultTracePageSize = 10
  const faultTracePage = ref(1)
  const faultTracePages = computed(() =>
    Math.max(1, Math.ceil(filteredFaultTraces.value.length / faultTracePageSize)),
  )
  const pagedFaultTraces = computed(() =>
    paginate(filteredFaultTraces.value, faultTracePage.value, faultTracePageSize),
  )

  watch([() => disconnectFilter.time.value, currentOp], () => {
    faultTracePage.value = 1
    // 新的时间/操作选择打断查询态
    if (faultTraceQuery.value) clearFaultTraceQuery()
  })

  // ---------- P1.6 故障码时序时间聚合尺度（客户端对秒级点再分桶，设计 1.8） ----------

  // 与 api fetchFaultChart 的 max_points 对齐：单码秒级点达上限说明后端已峰保抽稀
  const FAULT_CHART_MAX_POINTS = 1000
  const faultChartScale = ref<10 | 60 | 600 | 3600>(60)
  const faultChartScaleOptions = [
    { value: 10, label: '10 秒' },
    { value: 60, label: '1 分钟' },
    { value: 600, label: '10 分钟' },
    { value: 3600, label: '1 小时' },
  ] as const

  const faultChartDisplayData = computed(() => {
    const scaleMs = faultChartScale.value * 1000
    const out: Record<string, Array<{ time: string; err_cnt: number }>> = {}
    for (const [code, points] of Object.entries(faultChartData.value)) {
      const buckets = new Map<number, number>()
      ;(points ?? []).forEach((point) => {
        const ms = tsToEpochMs(point.time)
        if (!Number.isFinite(ms)) return
        const bucketStart = Math.floor(ms / scaleMs) * scaleMs
        buckets.set(bucketStart, (buckets.get(bucketStart) ?? 0) + (point.err_cnt ?? 0))
      })
      out[code] = [...buckets.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([ms, err_cnt]) => ({ time: epochMsToTs(ms), err_cnt }))
    }
    return out
  })

  // 已抽稀时再分桶求和不再精确，UI 必须标注近似
  const faultChartSampled = computed(() =>
    Object.values(faultChartData.value).some(
      (points) => (points ?? []).length >= FAULT_CHART_MAX_POINTS,
    ),
  )

  // ---------- P1.7 通断聚合事件表（服务端 date_trunc 分桶 × src/dst 子表） ----------
  // 两接口无 log_id：不随日志文件选择收窄；时间为闭区间 <=，与主视图半开区间口径不同（UI 注明）。
  // 组件卸载后自动重查（再次挂载；不同步 interval/排序/分页），时间/op 变化重置并惰性重查。

  type FaultAggBucket = {
    start_time: string
    end_time: string
    status_code_cnt: Record<string, number>
  }
  type FaultAggPair = { src_ip: string; dst_ip: string; status_code_cnt: Record<string, number> }

  const FAULT_AGG_PAGE_SIZE = 10
  const faultAggInterval = ref<'second' | 'minute' | 'hour'>('minute')
  const faultAggIntervalOptions = [
    { value: 'second', label: '按秒' },
    { value: 'minute', label: '按分钟' },
    { value: 'hour', label: '按小时' },
  ] as const
  const faultAggSortField = ref('timestamp') // 'timestamp' 或故障码（含 all）
  const faultAggSortDesc = ref(false)
  const faultAggRows = ref<FaultAggBucket[]>([])
  const faultAggErrCodes = ref<string[]>([])
  const faultAggTotal = ref(0)
  const faultAggPage = ref(1)
  const faultAggLoading = ref(false)
  const faultAggError = ref('')
  let faultAggSeq = 0

  const faultAggPages = computed(() =>
    Math.max(1, Math.ceil(faultAggTotal.value / FAULT_AGG_PAGE_SIZE)),
  )

  const loadFaultAggEvents = async (page = faultAggPage.value) => {
    const asset = selectedAsset.value
    if (!asset) return
    const seq = ++faultAggSeq
    faultAggLoading.value = true
    faultAggError.value = ''
    try {
      const window = disconnectFilter.timeWindow.value
      const result = await fetchTimeAggregatedFailureEvents(asset.id, {
        op: realOp.value,
        interval: faultAggInterval.value,
        startTime: window ? epochMsToTs(window.start) : undefined,
        endTime: window ? epochMsToTs(window.end) : undefined,
        sortField: faultAggSortField.value,
        sortDesc: faultAggSortDesc.value,
        pageNum: page,
        pageCnt: FAULT_AGG_PAGE_SIZE,
      })
      if (seq !== faultAggSeq) return
      faultAggRows.value = result.rows
      faultAggErrCodes.value = result.errCodes
      faultAggTotal.value = result.total
      faultAggPage.value = page
      // 排序字段若因 errCodes 变化失效，回退 timestamp
      if (
        faultAggSortField.value !== 'timestamp' &&
        !result.errCodes.includes(faultAggSortField.value)
      ) {
        faultAggSortField.value = 'timestamp'
        faultAggSortDesc.value = false
      }
      // 重置展开子表
      faultAggExpandedKey.value = ''
      faultAggPairs.value = []
      faultAggPairsTotal.value = 0
    } catch (error) {
      if (seq !== faultAggSeq) return
      faultAggError.value = errorText(error)
      faultAggRows.value = []
      faultAggTotal.value = 0
    } finally {
      if (seq === faultAggSeq) faultAggLoading.value = false
    }
  }

  // 主表点击表头排序：同列再点翻转方向，换列用该列默认方向
  const faultAggSortBy = (field: string) => {
    if (faultAggSortField.value === field) {
      faultAggSortDesc.value = !faultAggSortDesc.value
    } else {
      faultAggSortField.value = field
      faultAggSortDesc.value = field !== 'timestamp'
    }
    void loadFaultAggEvents(1)
  }

  // ---------- 桶内 src/dst IP 对子表 ----------
  const faultAggExpandedKey = ref('') // `${start_time}|${end_time}`，'' = 全部收起
  const faultAggPairs = ref<FaultAggPair[]>([])
  const faultAggPairsErrCodes = ref<string[]>([])
  const faultAggPairsTotal = ref(0)
  const faultAggPairsPage = ref(1)
  const faultAggPairsLoading = ref(false)
  const faultAggPairsSortField = ref('all')
  const faultAggPairsSortDesc = ref(true)
  let faultAggPairsSeq = 0

  const faultAggPairsPages = computed(() =>
    Math.max(1, Math.ceil(faultAggPairsTotal.value / FAULT_AGG_PAGE_SIZE)),
  )
  const faultAggExpandedBucket = computed(() => {
    if (!faultAggExpandedKey.value) return null
    return faultAggRows.value.find(
      (row) => `${row.start_time}|${row.end_time}` === faultAggExpandedKey.value,
    )
  })

  const loadFaultAggPairs = async (page = faultAggPairsPage.value) => {
    const asset = selectedAsset.value
    const bucket = faultAggExpandedBucket.value
    if (!asset || !bucket) return
    const seq = ++faultAggPairsSeq
    faultAggPairsLoading.value = true
    try {
      const result = await fetchSrcDstAggregatedFailureEvents(asset.id, {
        op: realOp.value,
        startTime: bucket.start_time,
        endTime: bucket.end_time,
        sortField: faultAggPairsSortField.value,
        sortDesc: faultAggPairsSortDesc.value,
        pageNum: page,
        pageCnt: FAULT_AGG_PAGE_SIZE,
      })
      if (seq !== faultAggPairsSeq) return
      faultAggPairs.value = result.rows
      faultAggPairsTotal.value = result.total
      faultAggPairsPage.value = page
      // 子表动态码列与主表一致（同时间窗同 op 下故障码集合一致）
      faultAggPairsErrCodes.value = faultAggErrCodes.value
    } finally {
      if (seq === faultAggPairsSeq) faultAggPairsLoading.value = false
    }
  }

  const toggleFaultAggBucket = (bucket: FaultAggBucket) => {
    const key = `${bucket.start_time}|${bucket.end_time}`
    if (faultAggExpandedKey.value === key) {
      faultAggExpandedKey.value = ''
      faultAggPairsSeq += 1
      return
    }
    faultAggExpandedKey.value = key
    faultAggPairsSortField.value = 'all'
    faultAggPairsSortDesc.value = true
    void loadFaultAggPairs(1)
  }

  const faultAggPairsSortBy = (field: string) => {
    if (faultAggPairsSortField.value === field) {
      faultAggPairsSortDesc.value = !faultAggPairsSortDesc.value
    } else {
      faultAggPairsSortField.value = field
      faultAggPairsSortDesc.value = true
    }
    void loadFaultAggPairs(1)
  }

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
    focus: { kind: 'none' } as AnalysisFocus,
    statusCodes: [] as string[],
    timeOverride: null as { start: number; end: number; label: string } | null,
  })
  let objectDetailSeq = 0

  const objectDetailPages = computed(() =>
    Math.max(1, Math.ceil(objectDetail.total / objectDetail.pageSize)),
  )

  const fetchObjectDetailPage = async () => {
    const asset = selectedAsset.value
    if (!asset) return
    const filter = objectDetail.domain === 'latency' ? latencyFilter : disconnectFilter
    const focus = objectDetail.focus
    const window = objectDetail.timeOverride ?? filter.timeWindow.value
    const seq = ++objectDetailSeq
    objectDetail.loading = true
    objectDetail.error = ''
    try {
      const baseQuery = {
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
          ? await fetchLatencyTracePage(asset.id, {
              ...baseQuery,
              logId: latencyFilter.logId.value,
            })
          : await fetchFaultTracePage(asset.id, {
              ...baseQuery,
              statusCodes: objectDetail.statusCodes,
            })
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

  // P1.7：桶点 IP 对时传入一次性时间窗覆盖，仅影响该次详情请求与标题，不回写 filter
  type ObjectDetailOverride = { start: number; end: number; label: string }

  const openObjectDetail = (
    domain: ObjectDetailDomain,
    focus: AnalysisFocus,
    timeOverride?: ObjectDetailOverride,
    statusCodes: string[] = [],
    syncFocus = true,
  ) => {
    if (focus.kind === 'none') {
      toast('请先在拓扑或列表中选择端点或链路', 'info')
      return
    }
    const filter = domain === 'latency' ? latencyFilter : disconnectFilter
    if (syncFocus && focus.kind === 'pod') filter.setFocusPod(focus.ip)
    else if (syncFocus && focus.kind === 'link') filter.setFocusLink(focus.src, focus.dst)
    objectDetail.domain = domain
    objectDetail.focus = focus
    objectDetail.statusCodes = [...statusCodes]
    const objectTitle =
      focus.kind === 'pod'
        ? `端点 ${focus.ip}`
        : focus.kind === 'link'
          ? `链路 ${focus.src} → ${focus.dst}`
          : '对象详情'
    objectDetail.title =
      domain === 'disconnect' && statusCodes.length
        ? `故障码 ${statusCodes.join(' / ')} · ${objectTitle}`
        : objectTitle
    objectDetail.windowLabel = timeOverride?.label ?? filter.timeLabel.value
    objectDetail.timeOverride = timeOverride ?? null
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
    openObjectDetail(
      'disconnect',
      { kind: 'pod', ip },
      undefined,
      selectedFaultCode.value ? [selectedFaultCode.value] : [],
    )
  }
  const enterFaultLinkDetail = (src: string, dst: string) => {
    openObjectDetail(
      'disconnect',
      { kind: 'link', src, dst },
      undefined,
      selectedFaultCode.value ? [selectedFaultCode.value] : [],
    )
  }
  // P1.7：桶点 IP 对，以桶窗为时间上下文打开链路故障 Trace（不回写 disconnectFilter.time）
  const enterFaultAggPairDetail = (src: string, dst: string, bucket: FaultAggBucket) => {
    const start = tsToEpochMs(bucket.start_time)
    const end = tsToEpochMs(bucket.end_time)
    if (!Number.isFinite(start) || !Number.isFinite(end)) return
    openObjectDetail(
      'disconnect',
      { kind: 'link', src, dst },
      {
        start,
        end,
        label: `${bucket.start_time} ~ ${bucket.end_time}`,
      },
      [],
      false,
    )
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
  let traceDrawerRequestSeq = 0

  const openTraceDrawer = async (row: any) => {
    const seq = ++traceDrawerRequestSeq
    detailDrawerRow.value = row
    drawerKind.value = 'trace'
    detailDrawerOpen.value = true
    traceDrawerLogs.value = []
    const asset = selectedAsset.value
    if (!asset || !row?.trace_id) return
    const logId = row.log_id ?? latencyFilter.logId.value
    try {
      const result = await fetchTraceLogs(asset.id, [row.trace_id], logId)
      if (seq !== traceDrawerRequestSeq) return
      traceDrawerLogs.value = result.log_failure_event_results ?? []
    } catch {
      if (seq !== traceDrawerRequestSeq) return
      traceDrawerLogs.value = []
    }
    if (!row.total_latency && !row.total_latency_us) {
      try {
        const latencyRow = await fetchTraceLatency(asset.id, row.trace_id, logId)
        if (seq !== traceDrawerRequestSeq) return
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

  // ---------- P1.2 Trace 抽屉相关故障语义 ----------
  // 该 trace 已命中的故障模式 id：trace 行 failure_mode + 运行日志事件 failure_mode_id
  const splitFailureModeIds = (value: unknown): string[] =>
    String(value ?? '')
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)

  const traceFailureModeIdsOf = (row: any): string[] => {
    const ids = new Set<string>()
    splitFailureModeIds(row?.failure_mode).forEach((id) => ids.add(id))
    traceDrawerLogs.value.forEach((log) => {
      splitFailureModeIds(log?.failure_mode_id ?? log?.failure_mode).forEach((id) => ids.add(id))
    })
    return [...ids]
  }

  // 相关故障：子故障 children ∩ trace 已命中模式；交集为空时只在已命中模式中筛同码项
  // （排除自身），不从知识库收集全量同码故障。
  // KVCache 时延 trace 行没有 failure_mode 字段，主模式回退为 trace 命中集合的第一个。
  const relatedFailureModeIdsOf = (row: any): string[] => {
    const traceIds = traceFailureModeIdsOf(row)
    const primaryId = splitFailureModeIds(row?.failure_mode)[0] ?? traceIds[0]
    const primary = failureModeOf(primaryId)
    const childIds = splitFailureModeIds(primary?.children_failure_mode_ids).filter((id) =>
      traceIds.includes(id),
    )
    if (childIds.length > 0) return childIds
    const errorCode = normalizeFailureModeErrorCode(primary?.error_code)
    if (!errorCode) return []
    return traceIds.filter((id) => {
      if (id === primaryId) return false
      return normalizeFailureModeErrorCode(failureModeOf(id)?.error_code) === errorCode
    })
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
  const faultTopoRef = ref<HTMLElement | null>(null)
  const brpcSuccessRef = ref<HTMLElement | null>(null)
  const brpcSuccessOverviewRef = ref<HTMLElement | null>(null)
  const brpcSingleRef = ref<HTMLElement | null>(null)
  const brpcLatencyMonitorRef = ref<HTMLElement | null>(null)
  const brpcLatencyRef = ref<HTMLElement | null>(null)
  const brpcFaultTimelineRef = ref<HTMLElement | null>(null)
  const brpcEventTimelineRef = ref<HTMLElement | null>(null)
  const brpcThreadGraphRef = ref<HTMLElement | null>(null)
  const brpcThreadTimelineRef = ref<HTMLElement | null>(null)

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
    afterDomUpdate(() => {
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
          link.symbolSize = [0, Math.min(18, Math.max(14, Math.round(width * 2 + 7)))]
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
        const size = 30 + Math.sqrt(node.total / maxTotal) * 28
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
            // 数据包围盒宽高比未必是 1（如“仅显示链路两端”后只剩 2-3 个节点），
            // 若直接把非正方形 DataRect 拉进正方形 ViewRect，圆环会被拉伸成椭圆；
            // preserveAspect 让视图矩形按数据包围盒比例 letterbox，保证等比映射
            preserveAspect: true,
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
    afterDomUpdate(() => {
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
    afterDomUpdate(() => {
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
    afterDomUpdate(() => {
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
    const map = new Map<
      string,
      { src: string; dst: string; faults: number; codes: string[]; codeCounts: Map<string, number> }
    >()
    faultScopedTraces.value.forEach((trace) => {
      const src = trace.src_ip
      const dst = trace.dst_ip
      if (!src || !dst) return
      const key = `${src}|${dst}`
      if (!map.has(key)) map.set(key, { src, dst, faults: 0, codes: [], codeCounts: new Map() })
      const pair = map.get(key)!
      pair.faults += 1
      normalizeFaultCodes(trace.status_code).forEach((code) => {
        pair.codeCounts.set(code, (pair.codeCounts.get(code) ?? 0) + 1)
        if (!pair.codes.includes(code)) pair.codes.push(code)
      })
    })
    return [...map.values()]
      .map((pair) => ({
        ...pair,
        // 故障码按计数降序，便于链路/拓扑按主导故障码着色与展示
        codes: [...pair.codeCounts.entries()]
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
          .map(([code]) => code),
      }))
      .sort((a, b) => b.faults - a.faults)
  })

  const faultPodStats = computed(() => {
    const map = new Map<
      string,
      { ip: string; faults: number; src: number; dst: number; codes: string[] }
    >()
    faultScopedTraces.value.forEach((trace) => {
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

  // 故障码 → 颜色：按当前范围故障 Trace 数降序分配调色板，时序图与拓扑图共用同一映射
  const faultCodeColors = ['#EF4444', '#F59E0B', '#1E6FFF', '#8B5CF6', '#00B365']
  const faultCodeColorOrder = computed(() => {
    const counts = new Map<string, number>()
    faultScopedTraces.value.forEach((trace) => {
      normalizeFaultCodes(trace.status_code).forEach((code) => {
        counts.set(code, (counts.get(code) ?? 0) + 1)
      })
    })
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([code]) => code)
  })
  const faultCodeColor = (code: string) => {
    const index = faultCodeColorOrder.value.indexOf(code)
    return faultCodeColors[index >= 0 ? index % faultCodeColors.length : 0]
  }

  const renderFaultTopology = () => {
    afterDomUpdate(() => {
      const el = faultTopoRef.value
      if (!el) return
      const chart = getChart(el)
      const nodeMap = new Map<
        string,
        { ip: string; faults: number; src: number; dst: number; codes: Set<string> }
      >()
      faultActivePairs.value.forEach((pair) => {
        ;(
          [
            ['src', pair.src],
            ['dst', pair.dst],
          ] as const
        ).forEach(([role, ip]) => {
          if (!nodeMap.has(ip)) nodeMap.set(ip, { ip, faults: 0, src: 0, dst: 0, codes: new Set() })
          const node = nodeMap.get(ip)!
          node.faults += pair.faults
          pair.codes.forEach((code) => node.codes.add(code))
          if (role === 'src') node.src += pair.faults
          else node.dst += pair.faults
        })
      })
      if (nodeMap.size === 0) {
        chart.clear()
        return
      }

      // 与时延拓扑同款等比环形布局：坐标落在正方形绘图区，避免横向画布拉伸变形
      const ordered = [...nodeMap.values()].sort(
        (a, b) => b.faults - a.faults || a.ip.localeCompare(b.ip),
      )
      const positions = new Map<string, { x: number; y: number }>()
      ordered.forEach((node, index) => {
        const angle = -Math.PI / 2 + (index / ordered.length) * Math.PI * 2
        positions.set(node.ip, { x: Math.cos(angle), y: Math.sin(angle) })
      })

      const pairCounts = faultActivePairs.value.map((pair) => pair.faults)
      const minCount = Math.min(...pairCounts)
      const maxCount = Math.max(...pairCounts)
      const maxNodeFaults = Math.max(...ordered.map((node) => node.faults))

      const nodes = ordered.map((node) => {
        const pos = positions.get(node.ip)
        const color = faultCodeColor([...node.codes][0] ?? '')
        return {
          name: node.ip,
          faults: node.faults,
          src: node.src,
          dst: node.dst,
          codes: [...node.codes],
          x: pos?.x,
          y: pos?.y,
          symbol: 'circle',
          symbolSize: 26 + Math.sqrt(node.faults / maxNodeFaults) * 34,
          cursor: 'pointer',
          itemStyle: {
            color,
            borderColor: 'rgba(0,0,0,0.18)',
            borderWidth: 1.5,
            shadowBlur: 6,
            shadowColor: 'rgba(31, 64, 117, 0.25)',
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

      const links = faultActivePairs.value.map((pair) => {
        const normalized = Math.log1p(pair.faults - minCount) / Math.log1p(maxCount - minCount || 1)
        const width = 2 + normalized * 4.5
        return {
          source: pair.src,
          target: pair.dst,
          faults: pair.faults,
          codes: pair.codes,
          value: pair.faults,
          lineStyle: {
            color: faultCodeColor(pair.codes[0] ?? ''),
            width,
            opacity: 0.9,
            curveness: pair.src < pair.dst ? 0.1 : -0.1,
          },
          symbolSize: [0, 7 + normalized * 6],
        }
      })

      const graphSize = Math.max(200, Math.min(el.clientWidth - 40, el.clientHeight - 30))
      const graphLeft = Math.max(30, (el.clientWidth - graphSize) / 2)
      const graphTop = Math.max(20, (el.clientHeight - graphSize) / 2)

      setChartOption(chart, {
        animation: false,
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => {
            if (params.dataType === 'node') {
              const data = params.data
              return `<b>${data.name}</b><br/>故障次数: ${data.faults}<br/>出方向(源): ${data.src} &nbsp; 入方向(目标): ${data.dst}<br/>关联故障码: ${data.codes.join(', ') || '-'}`
            }
            if (params.dataType === 'edge') {
              const data = params.data
              return `<b>${data.source} → ${data.target}</b><br/>故障次数: ${data.faults}<br/>故障码: ${data.codes.join(', ') || '-'}<br/><span style="color:#94a3b8">点击查看该链路故障 Trace</span>`
            }
            return ''
          },
        },
        series: [
          {
            type: 'graph',
            layout: 'none',
            preserveAspect: true,
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
            links,
            emphasis: {
              focus: 'adjacency',
              lineStyle: { width: 7, opacity: 1 },
              itemStyle: { shadowBlur: 14 },
            },
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

  const renderFaultChart = () => {
    afterDomUpdate(() => {
      const el = faultChartRef.value
      if (!el) return
      const chart = getChart(el)
      // P1.6：按所选尺度再分桶后的展示数据；原始秒级数据仅用于空态与抽稀判断
      const displayData = faultChartDisplayData.value
      const codes = selectedFaultCode.value
        ? Object.prototype.hasOwnProperty.call(displayData, selectedFaultCode.value)
          ? [selectedFaultCode.value]
          : []
        : Object.keys(displayData)
      if (codes.length === 0) {
        chart.clear()
        return
      }
      const times = [
        ...new Set(codes.flatMap((code) => (displayData[code] ?? []).map((point) => point.time))),
      ].sort()
      const series = codes.map((code) => ({
        name: `故障码 ${code}`,
        type: 'line',
        smooth: true,
        stack: 'fault',
        lineStyle: { width: 2, color: faultCodeColor(code) },
        itemStyle: { color: faultCodeColor(code) },
        data: times.map((time) => {
          const point = (displayData[code] ?? []).find((item) => item.time === time)
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
          data: times.map((time) => formatChartTs(time)),
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
          disconnectFilter.clearTime()
          return
        }
        const xRange = Array.isArray(area.coordRange[0]) ? area.coordRange[0] : area.coordRange
        const startIndex = Math.max(0, Math.floor(xRange[0]))
        const endIndex = Math.min(times.length - 1, Math.ceil(xRange[1]))
        if (startIndex > endIndex || times.length === 0) {
          disconnectFilter.clearTime()
          return
        }
        const startTime = times[startIndex]
        const endTime = times[endIndex]
        if (startTime && endTime) {
          // 通断域 time 同步为半开区间 [start, end)：end = 图中所见末桶起点 + 当前尺度桶宽
          disconnectFilter.setTimeRange(
            tsToEpochMs(startTime),
            tsToEpochMs(endTime) + faultChartScale.value * 1000,
          )
        }
      })
    })
  }

  const renderBrpcCharts = () => {
    afterDomUpdate(() => {
      const trend = brpcTrend.value
      const el = brpcSuccessRef.value
      if (!el) return
      const chart = getChart(el)
      // 全接口聚合趋势：左轴成功率(%)、右轴 P99(ms)，避免两个单线图各自难以对照
      setChartOption(chart, {
        tooltip: { trigger: 'axis' },
        // 双轴图例居中，避免与右轴名（P99 (ms)）在右上角重叠
        legend: { left: 'center', top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 56, right: 56, top: 46, bottom: 42 },
        xAxis: {
          type: 'category',
          data: trend.times,
          axisLabel: { fontSize: 10, rotate: 30 },
        },
        yAxis: [
          {
            type: 'value',
            name: '成功率 %',
            min: 0,
            max: 100,
            axisLabel: { fontSize: 10 },
          },
          {
            type: 'value',
            name: 'P99 (ms)',
            axisLabel: { fontSize: 10 },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: '平均成功率',
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: { width: 2, color: '#00B365' },
            itemStyle: { color: '#00B365' },
            yAxisIndex: 0,
            data: trend.success,
          },
          {
            name: '最高 P99',
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: { width: 2, color: '#EF4444' },
            itemStyle: { color: '#EF4444' },
            yAxisIndex: 1,
            data: trend.p99,
          },
        ],
      })
    })
  }

  // P2.1 成功率总览：按勾选接口逐条曲线，指标可切换（成功率/失败率/请求数/成功量/失败量）
  const renderBrpcSuccessOverviewChart = () => {
    afterDomUpdate(() => {
      const el = brpcSuccessOverviewRef.value
      if (!el) return
      const chart = getChart(el)
      const times = brpcIfaceTimestamps.value
      const metric = brpcSuccessMetric.value
      const metricLabel =
        brpcSuccessMetricOptions.find((option) => option.value === metric)?.label ?? metric
      const isRate = metric === 'successRate' || metric === 'failureRate'
      const series = brpcSuccessSelectedIfaces.value.map((iface) => {
        const rowByTs = new Map<string, any>()
        brpcFileRows.value.forEach((row) => {
          if (row.interface_name !== iface || !row.timestamp) return
          rowByTs.set(String(row.timestamp).slice(0, 19), row)
        })
        const color = brpcIfaceColor(iface)
        return {
          name: iface,
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2, color },
          itemStyle: { color },
          data: times.map((time) => {
            const row = rowByTs.get(time)
            return row ? brpcRowMetric(row, metric) : null
          }),
        }
      })
      setChartOption(chart, {
        tooltip: {
          trigger: 'axis',
          order: 'valueDesc',
          valueFormatter: (value: unknown) =>
            typeof value === 'number' ? `${value}${isRate ? '%' : ''}` : '-',
        },
        legend: { show: false },
        grid: { left: 56, right: 20, top: 24, bottom: 42 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(time)),
          axisLabel: { fontSize: 10, rotate: 30 },
        },
        yAxis: {
          type: 'value',
          name: isRate ? `${metricLabel} %` : metricLabel,
          max: isRate ? 100 : undefined,
          axisLabel: { fontSize: 10 },
        },
        series,
      })
    })
  }

  // U1b 单接口监控：指标多选（请求数/成功率/失败率/成功量/失败量），数量与比率分离双轴
  const renderBrpcSingleChart = () => {
    afterDomUpdate(() => {
      const el = brpcSingleRef.value
      if (!el) return
      const chart = getChart(el)
      const iface = brpcSingleIface.value
      const times = brpcIfaceTimestamps.value
      const rowByTs = new Map<string, any>()
      brpcFileRows.value.forEach((row) => {
        if (row.interface_name !== iface || !row.timestamp) return
        rowByTs.set(String(row.timestamp).slice(0, 19), row)
      })
      const selectedMetrics = brpcSingleSelectedMetrics.value.filter((metric) =>
        brpcSingleMetrics.some((option) => option.value === metric),
      )
      setChartOption(chart, {
        tooltip: { trigger: 'axis', order: 'valueDesc' },
        // 图例居中放，避免与右轴名（比率 %）在右上角重叠
        legend: { left: 'center', top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 56, right: 56, top: 46, bottom: 42 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(time)),
          axisLabel: { fontSize: 10, rotate: 30 },
        },
        yAxis: [
          {
            type: 'value',
            name: '数量',
            axisLabel: { fontSize: 10 },
          },
          {
            type: 'value',
            name: '比率 %',
            min: 0,
            max: 100,
            axisLabel: { fontSize: 10 },
            splitLine: { show: false },
          },
        ],
        series: selectedMetrics.map((metric) => {
          const color = brpcSingleMetricColor(metric)
          return {
            name: brpcSingleMetrics.find((option) => option.value === metric)?.label ?? metric,
            type: 'line',
            smooth: true,
            symbol: 'none',
            lineStyle: { width: 2, color },
            itemStyle: { color },
            yAxisIndex: isBrpcRateMetric(metric) ? 1 : 0,
            data: times.map((time) => {
              const row = rowByTs.get(time)
              return row ? brpcRowMetric(row, metric as BrpcSuccessMetric) : null
            }),
          }
        }),
      })
    })
  }

  // P2.1 单接口时延：avg / P99 / max（ms）
  const renderBrpcLatencyChart = () => {
    afterDomUpdate(() => {
      const el = brpcLatencyRef.value
      if (!el) return
      const chart = getChart(el)
      const iface = brpcSingleIface.value
      const times = brpcIfaceTimestamps.value
      const rowByTs = new Map<string, any>()
      brpcFileRows.value.forEach((row) => {
        if (row.interface_name !== iface || !row.timestamp) return
        rowByTs.set(String(row.timestamp).slice(0, 19), row)
      })
      const metricDefs = [
        { name: 'avg', key: 'avg_ns', color: '#1E6FFF' },
        { name: 'P99', key: 'p99_ns', color: '#EF4444' },
        { name: 'max', key: 'max_ns', color: '#F59E0B' },
      ]
      setChartOption(chart, {
        tooltip: { trigger: 'axis' },
        legend: { right: 0, top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 56, right: 20, top: 32, bottom: 42 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(time)),
          axisLabel: { fontSize: 10, rotate: 30 },
        },
        yAxis: { type: 'value', name: 'ms', axisLabel: { fontSize: 10 } },
        series: metricDefs.map((def) => ({
          name: def.name,
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2, color: def.color },
          itemStyle: { color: def.color },
          data: times.map((time) => {
            const row = rowByTs.get(time)
            return row ? +(((row[def.key] ?? 0) as number) / 1e6).toFixed(3) : null
          }),
        })),
      })
    })
  }

  // U1c 时延监控（µs）：指标下拉（total/avg/max/min/P50/P90/P95/P99/P999）+ 多接口曲线勾选
  const renderBrpcLatencyMonitorChart = () => {
    afterDomUpdate(() => {
      const el = brpcLatencyMonitorRef.value
      if (!el) return
      const chart = getChart(el)
      const times = brpcIfaceTimestamps.value
      const metricKey = brpcLatencyMetric.value
      const metricLabel = brpcLatencyMetrics.find((item) => item.value === metricKey)?.label ?? metricKey
      const series = brpcLatencySelectedIfaces.value.map((iface) => {
        const rowByTs = new Map<string, any>()
        brpcFileRows.value.forEach((row) => {
          if (row.interface_name !== iface || !row.timestamp) return
          rowByTs.set(String(row.timestamp).slice(0, 19), row)
        })
        const color = brpcIfaceColor(iface)
        return {
          name: iface,
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2, color },
          itemStyle: { color },
          data: times.map((time) => {
            const value = rowByTs.get(time)?.[metricKey]
            // profiling 行内时延字段单位为 ns，图表标注 µs，需在 UI 边界换算（旧版同口径）
            return typeof value === 'number' && Number.isFinite(value)
              ? +(value / 1000).toFixed(2)
              : null
          }),
        }
      })
      setChartOption(chart, {
        tooltip: {
          trigger: 'axis',
          order: 'valueDesc',
          valueFormatter: (value: unknown) =>
            typeof value === 'number' ? `${value} µs` : String(value ?? '-'),
        },
        legend: { show: false },
        grid: { left: 62, right: 20, top: 24, bottom: 42 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(time)),
          axisLabel: { fontSize: 10, rotate: 30 },
        },
        yAxis: { type: 'value', name: `${metricLabel} (µs)`, axisLabel: { fontSize: 10 } },
        series,
      })
    })
  }

  const renderAnalysisModules = () => {
    nextTick(() => {
      if (!isAssetMode.value) return
      if (isBrpcTask.value) {
        renderBrpcCharts()
        renderBrpcSuccessOverviewChart()
        renderBrpcSingleChart()
        renderBrpcLatencyMonitorChart()
        renderBrpcLatencyChart()
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
        renderFaultChart()
      }
    })
  }

  const loadOverviewForTab = async () => {
    const generation = ++overviewRequestGeneration
    if (!isAssetMode.value) return
    // 任务列表还停留在上一个资产库时不发按库查询，等日志列表 watcher 再触发
    if (!assetScoped.value) return
    if (assetTypeFilter.value === 'brpc') {
      await loadBrpcData()
      if (brpcMonitorTab.value === 'fault') await loadBrpcFaultData()
      return
    } else {
      const op = realOp.value
      await loadOverviewSection(op, generation)
      if (generation !== overviewRequestGeneration) return
      if (analysisTab.value === 'latency') {
        if (analysisModule.latency === 'trend') {
          await loadTrendSection(op, trendPercentile.value, generation)
          if (generation !== overviewRequestGeneration) return
          renderTrendChart()
          renderSlowChart()
        } else {
          renderAnomalyChart()
          renderTopology()
        }
      } else {
        await loadFaultSection(op, generation)
        if (generation !== overviewRequestGeneration) return
        renderFaultTopology()
        renderFaultChart()
      }
    }
  }

  let overviewWatchersBound = false
  const bindOverviewWatchers = () => {
    if (overviewWatchersBound) return
    overviewWatchersBound = true
    overviewScope.run(() => bindOverviewWatchersInScope())
  }

  const bindOverviewWatchersInScope = () => {
    const resetLatencyScope = () => {
      latencyFilter.clearTime()
      latencyFilter.clearFocus()
      latencyFilter.clearWhitelist()
      if (analysisWindowTimer) clearTimeout(analysisWindowTimer)
      analysisWindowTimer = null
      void loadAnalysisWindow()
    }
    const resetDisconnectScope = () => {
      disconnectFilter.clearTime()
      disconnectFilter.clearFocus()
      selectedFaultCode.value = ''
      clearFaultTraceQuery()
    }

    // 切库重置：所有按资产聚合的状态必须清空，且让在途请求全部失效，
    // 否则上一个资产库的结果会残留到新资产库（串数据）。
    const resetAssetScope = () => {
      ++overviewRequestGeneration
      ++analysisWindowSeq
      ++objectDetailSeq
      ++traceDrawerRequestSeq
      ++brpcProfilingSeq
      ++brpcThreadLogsRequestSeq
      if (analysisWindowTimer) clearTimeout(analysisWindowTimer)
      analysisWindowTimer = null
      analysisWindowBuckets.value = null
      analysisWindowLoading.value = false
      timelineTruncated.value = false
      scopeData.value = emptyScopeData()
      clearSectionCaches()
      lastLogFilesKey = ''
      domainAutoSelectPending = true
      faultTraceIdsWithLatency.get.clear()
      faultTraceIdsWithLatency.set.clear()
      latencyTraceIdsWithFault.get.clear()
      latencyTraceIdsWithFault.set.clear()
      latencyFilter.clearTime()
      latencyFilter.clearFocus()
      latencyFilter.clearWhitelist()
      latencyFilter.logId.value = undefined
      disconnectFilter.clearTime()
      disconnectFilter.clearFocus()
      disconnectFilter.logId.value = undefined
      selectedFaultCode.value = ''
      clearFaultTraceQuery()
      objectDetail.open = false
      detailDrawerOpen.value = false
      detailDrawerRow.value = null
      traceDrawerLogs.value = []
      overviewLoading.value = false
      overviewError.value = ''
      // UBSocket（BRPC）监控状态
      brpcLoading.value = false
      brpcMonitorError.value = ''
      brpcProfilingFiles.value = []
      brpcAllProfilingRows.value = []
      brpcSelectedFileKey.value = ''
      brpcSuccessSelectedIfaces.value = []
      brpcLatencySelectedIfaces.value = []
      brpcSingleIface.value = ''
      brpcSingleSelectedMetrics.value = ['requestCount', 'successRate', 'failureRate']
      brpcLatencyMetric.value = 'avg_ns'
      brpcFaultSelectedLogId.value = ''
      brpcFaultBatch.value = null
      brpcFaultBatchId.value = ''
      brpcFaultTimelineSeries.value = []
      brpcAggregatedEvents.value = []
      brpcAggregatedEventTotal.value = 0
      brpcAggregatedEventPage.value = 1
      brpcAbnormalThreads.value = []
      brpcAbnormalThreadTotal.value = 0
      brpcAbnormalThreadPage.value = 1
      brpcThreadSearchInput.value = ''
      brpcThreadSearchQuery.value = ''
      brpcFaultLoading.value = false
      brpcFaultError.value = ''
      brpcFaultDetail.value = null
      brpcThreadLogs.value = []
      brpcThreadDetail.value = null
      brpcSelectedGraphNodeId.value = ''
    }

    watch([assetTypeFilter, assetTab], () => {
      if (!isAssetMode.value) return
      resetLatencyScope()
      resetDisconnectScope()
      void loadOverviewForTab()
    })
    watch([latencyOp, overviewScale], () => {
      if (!isAssetMode.value || isBrpcTask.value || analysisTab.value !== 'latency') return
      resetLatencyScope()
      void loadOverviewForTab()
    })
    watch(faultOp, () => {
      if (!isAssetMode.value || isBrpcTask.value || analysisTab.value !== 'disconnect') return
      resetDisconnectScope()
      void loadOverviewForTab()
    })
    watch(analysisTab, () => {
      if (isAssetMode.value && !isBrpcTask.value) void loadOverviewForTab()
    })
    watch(
      () => analysisModule.latency,
      () => {
        if (isAssetMode.value && !isBrpcTask.value && analysisTab.value === 'latency') {
          void loadOverviewForTab()
        }
      },
    )

    watch([trendVisible, trendPercentile, trendScale, trendRange], () => {
      if (isAssetMode.value && !isBrpcTask.value && analysisModule.latency === 'trend') {
        const generation = ++overviewRequestGeneration
        void loadTrendSection(realOp.value, trendPercentile.value, generation).then(() => {
          if (generation === overviewRequestGeneration) renderTrendChart()
        })
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
    // 注意：overview 是 reactive 对象，直接取值不是合法 watch source（永远不触发）
    watch([() => overview.topK, () => overview.sortBy], () => {
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

    // 通断时间窗与故障码共同驱动趋势、拓扑、端点、链路和实例列表。
    watch(
      [() => disconnectFilter.time.value, selectedFaultCode],
      () => {
        if (!isAssetMode.value || isBrpcTask.value || analysisTab.value !== 'disconnect') return
        renderFaultTopology()
        renderFaultChart()
      },
      { deep: true },
    )

    // P1.6：故障码时序尺度变化只改展示分桶，不回写 disconnectFilter.time
    watch(faultChartScale, () => {
      if (!isAssetMode.value || isBrpcTask.value || analysisTab.value !== 'disconnect') return
      renderFaultChart()
    })

    // U1：UBSocket 文件/指标/曲线勾选/单接口变化 → 重绘接口监控图
    watch(
      [
        brpcFileRows,
        brpcSuccessMetric,
        brpcSuccessSelectedIfaces,
        brpcSingleIface,
        brpcSingleSelectedMetrics,
        brpcLatencyMetric,
        brpcLatencySelectedIfaces,
      ],
      () => {
        if (!isAssetMode.value || !isBrpcTask.value) return
        renderBrpcCharts()
        renderBrpcSuccessOverviewChart()
        renderBrpcSingleChart()
        renderBrpcLatencyMonitorChart()
        renderBrpcLatencyChart()
      },
      { deep: true },
    )

    watch(availableMetrics, (list) => {
      const present = new Set(list.map((metric) => metric.key))
      const kept = selectedMetrics.value.filter((key) => present.has(key))
      selectedMetrics.value = kept.length ? kept : list.map((metric) => metric.key)
    })

    watch(
      () => dataOptions.value?.getAsset()?.id,
      (assetId, previousAssetId) => {
        if (assetId !== previousAssetId) resetAssetScope()
        // 任务列表尚未返回：交给 logFiles watcher 在拿到列表后再加载
        if (logFilesPending.value) return
        void loadOverviewForTab()
      },
      { immediate: true },
    )
    watch(
      [
        () => dataOptions.value?.getLogFiles(),
        () => dataOptions.value?.getLogFilesAssetId?.() ?? '',
        () => dataOptions.value?.getLogFilesLoading?.() ?? false,
      ],
      ([files, filesAssetId, logFilesLoading]) => {
        const list = files ?? []
        const ownerMatches = Boolean(filesAssetId) && filesAssetId === selectedAsset.value?.id
        // 任务列表还没返回：等 loading 结束再决定数据域并发请求
        if (ownerMatches && logFilesLoading) return
        // 首次拿到该资产库的任务列表时，把数据域落到真正有已完成任务的域，
        // 避免「上一个库停在 UBSocket，新库只有 KVCache」这类空壳页面
        let domainSwitched = false
        if (domainAutoSelectPending && ownerMatches) {
          domainAutoSelectPending = false
          const hasKvcache = list.some(
            (file) => file.log_type === 'KVCache' && isSuccess(file as LogFileModel),
          )
          const hasUbsocket = list.some(
            (file) => file.log_type === 'UBSocket' && isSuccess(file as LogFileModel),
          )
          if (assetTypeFilter.value === 'kvcache' && !hasKvcache && hasUbsocket) {
            assetTypeFilter.value = 'brpc'
            domainSwitched = true
          } else if (assetTypeFilter.value === 'brpc' && !hasUbsocket && hasKvcache) {
            assetTypeFilter.value = 'kvcache'
            domainSwitched = true
          }
        }
        const key =
          `${filesAssetId}|` +
          (files ?? []).map((file) => `${file.id}:${file.overall_status}`).join('|')
        // P1.5：默认跨任务汇总；仅在已选日志失效时回到“全部任务”
        const tasks = scopeTasks.value
        const current = latencyFilter.logId.value
        if (current && !tasks.some((file) => file.id === current)) {
          latencyFilter.logId.value = undefined
        }
        if (key !== lastLogFilesKey) {
          clearSectionCaches()
          lastLogFilesKey = key
        }
        // 域已切换时由 assetTypeFilter watcher 触发加载，避免同一次进入资产库重复请求
        if (isAssetMode.value && !domainSwitched) void loadOverviewForTab()
      },
      // immediate：OverviewPanel 是异步组件，挂载可能晚于任务列表返回，
      // 首评必须用「当前已加载的任务列表」判定数据域并按页签加载
      { immediate: true },
    )

    // P1.5：用户切换日志文件 → 清缓存并按当前页签重载
    watch(latencyFilter.logId, (logId, oldLogId) => {
      if (logId === oldLogId) return
      if (!isAssetMode.value || isBrpcTask.value) return
      ++overviewRequestGeneration
      ++analysisWindowSeq
      ++objectDetailSeq
      ++traceDrawerRequestSeq
      if (analysisWindowTimer) clearTimeout(analysisWindowTimer)
      analysisWindowTimer = null
      analysisWindowBuckets.value = null
      analysisWindowLoading.value = false
      timelineTruncated.value = false
      scopeData.value = emptyScopeData()
      objectDetail.open = false
      detailDrawerOpen.value = false
      detailDrawerRow.value = null
      traceDrawerLogs.value = []
      clearSectionCaches()
      void loadOverviewForTab()
    })

    watch(detailDrawerOpen, (open) => {
      if (!open) ++traceDrawerRequestSeq
    })
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
    activeFaultTraces,
    faultCodeSummaries,
    faultCodeColor,
    faultCodeColorOrder,
    faultPodStats,
    faultTopoRef,
    renderFaultTopology,
    latencyFilter,
    disconnectFilter,
    selectedFaultCode,
    faultScopedTraces,
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
    brpcEventDetail,
    brpcEventDetailError,
    brpcEventDetailLoading,
    brpcEventDetailThreads,
    brpcEventDetailTimeline,
    brpcEventTimelineRef,
    brpcSelectedGraphNode,
    brpcSelectedGraphNodeId,
    brpcThreadDetail,
    brpcThreadDetailError,
    brpcThreadDetailLoading,
    brpcThreadGraphRef,
    brpcThreadSearchInput,
    brpcThreadSearchQuery,
    brpcThreadTimelineRef,
    brpcFaultTimelineSeries,
    brpcFileKey,
    brpcFileLabel,
    brpcHasRows,
    brpcIfaceColor,
    brpcIfaceNames,
    brpcInterfaces,
    brpcKpi,
    brpcLatencyMetric,
    brpcLatencyMetrics,
    brpcLatencyMonitorRef,
    brpcLatencyRef,
    brpcLatencySelectedIfaces,
    brpcLoading,
    brpcMonitorError,
    brpcMonitorTab,
    brpcProfilingFiles,
    brpcScopeTasks,
    brpcSelectedFileKey,
    brpcSingleIface,
    brpcSingleMetricColor,
    brpcSingleMetrics,
    brpcSingleRef,
    brpcSingleSelectedMetrics,
    brpcSuccessMetric,
    brpcSuccessMetricOptions,
    brpcSuccessOverviewRef,
    brpcSuccessRef,
    brpcSuccessSelectedIfaces,
    brpcTrend,
    changeBrpcFaultLog,
    clearBrpcThreadSearch,
    clearFaultRange,
    clearFaultTraceQuery,
    clearTrend,
    currentOp,
    detailDrawerOpen,
    detailDrawerRow,
    drawerKind,
    enterPodDetail,
    enterLinkDetail,
    enterFaultDetail,
    enterFaultLinkDetail,
    enterFaultAggPairDetail,
    faultAggInterval,
    faultAggIntervalOptions,
    faultAggSortField,
    faultAggSortDesc,
    faultAggSortBy,
    faultAggRows,
    faultAggErrCodes,
    faultAggTotal,
    faultAggPage,
    faultAggPages,
    faultAggLoading,
    faultAggError,
    loadFaultAggEvents,
    faultAggExpandedKey,
    faultAggExpandedBucket,
    toggleFaultAggBucket,
    faultAggPairs,
    faultAggPairsErrCodes,
    faultAggPairsTotal,
    faultAggPairsPage,
    faultAggPairsPages,
    faultAggPairsLoading,
    faultAggPairsSortField,
    faultAggPairsSortDesc,
    faultAggPairsSortBy,
    loadFaultAggPairs,
    objectDetail,
    objectDetailPages,
    objectDetailGoPage,
    closeObjectDetail,
    focusPairs,
    failureModeCache,
    failureModeOf,
    faultChartData,
    faultChartDisplayData,
    faultChartRef,
    faultChartSampled,
    faultChartScale,
    faultChartScaleOptions,
    faultOp,
    faultTimeRange,
    faultTraceIdInput,
    faultTracePage,
    faultTracePageSize,
    faultTracePages,
    faultTraceQuery,
    faultTraceQueryError,
    faultTraceQueryLoading,
    faultTraces,
    faultTracesTruncated,
    faultTraceTotal,
    faultTraceLoadedCount,
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
    queryFaultTraceById,
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
    renderBrpcEventTimeline,
    renderBrpcLatencyChart,
    renderBrpcLatencyMonitorChart,
    renderBrpcSingleChart,
    renderBrpcSuccessOverviewChart,
    renderBrpcThreadGraph,
    renderBrpcThreadTimeline,
    renderBrpcFaultTimeline,
    submitBrpcThreadSearch,
    renderFaultChart,
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
    relatedFailureModeIdsOf,
    traceFailureModeIdsOf,
    traceStageRows,
    trendAnomalyHint,
    trendBuckets,
    trendCenter,
    trendChartData,
    trendLogId,
    trendLogLabel,
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
