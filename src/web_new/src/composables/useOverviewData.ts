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
  fetchBrpcThreadEvents,
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
  type BrpcTimelineWindowSize,
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
// 把「options 缺失」的空结果固化进缓存（总览外调用 useOverviewData 触发）
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

  // ============ 总览分析工作台 ============

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

  /**
   * 阶段（yuanrong 分解）字段口径：请求带 stat_type=p99 时，后端只把 p99_<metric> 挂到
   * ip_pair 上；历史口径响应仍可能是 ave_<metric>，所以先 p99 再 ave 回退。
   */
  const pairStageMetric = (pair: any, key: string): number | null => {
    for (const field of [`p99_${key}`, `ave_${key}`]) {
      const value = pair?.[field]
      if (typeof value === 'number' && Number.isFinite(value)) return value
    }
    return null
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
          pairMetricValues[metric.key] = pairStageMetric(pair, metric.key)
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

    // KVCache 时延域按日志文件收窄，logId 参与 key 与请求
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
  // 未选日志时自动兜底第一个已完成任务，不要求用户手选
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

    // 与总览共用 latencyFilter.logId，参与 key 与请求。
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

  // ---------- BRPC 接口监控（/brpc_profiling/knowledge 全量 + 文件客户端过滤） ----------

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

  // 文件选择只客户端过滤已加载 rows，不按文件重拉
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

  // 单接口曲线选择状态
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
  // 两张总览图（成功率 / 时延）共用一套接口勾选——同一批曲线在两个视角下对照，
  // 不再各自渲染一份 21 项清单
  const brpcOverviewSelectedIfaces = ref<string[]>([])
  const brpcSingleIface = ref('')

  // 接口配色与勾选色点一致（21 色覆盖全部接口）
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
    const paletteIndex = index >= 0 ? index % BRPC_INTERFACE_COLORS.length : 20
    return BRPC_INTERFACE_COLORS[paletteIndex] ?? '#6e7074'
  }

  // 单接口监控的指标多选
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
  const isBrpcRateMetric = (metric: string) => metric === 'successRate' || metric === 'failureRate'

  // 时延监控（µs）指标与多接口勾选
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

  // 单接口时延与总览时延同口径——同样的 9 项指标可选，单位统一 µs
  const BRPC_LATENCY_METRIC_COLORS: Record<string, string> = {
    total_ns: '#6366f1',
    avg_ns: '#1E6FFF',
    max_ns: '#F59E0B',
    min_ns: '#94a3b8',
    p50_ns: '#10b981',
    p90_ns: '#06b6d4',
    p95_ns: '#8b5cf6',
    p99_ns: '#EF4444',
    p999_ns: '#db2777',
  }
  const brpcSingleLatencyMetrics = brpcLatencyMetrics
  const brpcSingleLatencySelectedMetrics = ref<string[]>(['avg_ns', 'p99_ns', 'max_ns'])
  const brpcSingleLatencyColor = (metric: string) => BRPC_LATENCY_METRIC_COLORS[metric] ?? '#94a3b8'

  // 横轴标签按点数抽稀（密集时序下旋转标签会互相重叠）
  const brpcAxisLabelStep = (count: number) => Math.max(0, Math.ceil(count / 12) - 1)

  // 每条曲线的数据点画小圆圈：关掉 symbol 就只能看到连线，判断单点取值很吃力
  const brpcLineSymbol = { showSymbol: true, symbol: 'circle' as const, symbolSize: 4 }

  // UBSocket 接口监控 tooltip：
  // 1) 统一 appendToBody（与「最慢请求图」同一套做法），避免被 `.monitor-card` 的 overflow
  //    裁掉，并限制最大高度、允许滚动查看；
  // 2) 悬停在时间轴上列出该时刻的全部曲线；悬停在具体数据点上（光标距点 ≤ 10px）
  //    只显示最近的那一个点，便于读单点取值。
  const BRPC_TOOLTIP_POINT_RADIUS = 10
  const brpcPointerByChart = new WeakMap<ECharts, { x: number; y: number }>()

  const trackBrpcPointer = (chart: ECharts) => {
    if (brpcPointerByChart.has(chart)) return
    const pointer = { x: Number.NaN, y: Number.NaN }
    brpcPointerByChart.set(chart, pointer)
    chart.getZr().on('mousemove', (event: any) => {
      pointer.x = event?.offsetX ?? Number.NaN
      pointer.y = event?.offsetY ?? Number.NaN
    })
    chart.getZr().on('globalout', () => {
      pointer.x = Number.NaN
      pointer.y = Number.NaN
    })
  }

  const brpcAxisTooltip = (chart: ECharts, formatValue: (param: any) => string) => {
    trackBrpcPointer(chart)
    return {
      trigger: 'axis' as const,
      appendToBody: true,
      // 长列表（20+ 条曲线）可把光标移进 tooltip 内滚动查看
      enterable: true,
      // 光标离开图表立即隐藏（不留驻留时间）；淡出动画仍由 transitionDuration 提供。
      // 需要滚长列表时把光标移进 tooltip 内即可钉住，移出后同样是立即隐藏。
      hideDelay: 0,
      // tooltip 保留 ECharts 默认的位移/淡入过渡（transitionDuration 0.4 + displayTransition），
      // 「关闭动画」只针对图表本身，hover 框跟手动画要留着
      extraCssText: 'max-height:62vh;overflow-y:auto;',
      // ECharts 默认按「图表画布」当视口来摆 tooltip：21 条曲线的列表比画布高，
      // 会被顶到视口外。这里按浏览器窗口重新夹取，保证整块 tooltip 始终可见。
      position: (
        point: number[],
        _params: any,
        _dom: any,
        _rect: any,
        size: { contentSize: number[] },
      ) => {
        const gap = 12
        const width = size.contentSize[0] ?? 0
        const height = size.contentSize[1] ?? 0
        const box = chart.getDom().getBoundingClientRect()
        const [px, py] = point as [number, number]
        // 坐标是「图表局部」坐标，所以先把窗口边界换算到同一坐标系
        const minX = gap - box.left
        const maxX = window.innerWidth - box.left - gap - width
        const minY = gap - box.top
        const maxY = window.innerHeight - box.top - gap - height
        const clamp = (value: number, min: number, max: number) =>
          Math.min(Math.max(value, min), Math.max(min, max))
        // 右侧放不下就翻到左侧，下方放不下就翻到上方，最后统一夹进窗口
        const fitsRight = px + gap + width <= window.innerWidth - box.left - gap
        const fitsBelow = py + gap + height <= window.innerHeight - box.top - gap
        return [
          clamp(fitsRight ? px + gap : px - gap - width, minX, maxX),
          clamp(fitsBelow ? py + gap : py - gap - height, minY, maxY),
        ]
      },
      formatter: (params: any) => {
        const list: any[] = Array.isArray(params) ? params : params ? [params] : []
        if (!list.length) return ''
        const pointer = brpcPointerByChart.get(chart)
        let rows = list
        if (pointer && Number.isFinite(pointer.x) && Number.isFinite(pointer.y)) {
          let nearest: any = null
          let nearestDistance = BRPC_TOOLTIP_POINT_RADIUS
          list.forEach((param) => {
            if (typeof param.value !== 'number' || !Number.isFinite(param.value)) return
            const pixel = chart.convertToPixel({ seriesIndex: param.seriesIndex }, [
              param.dataIndex,
              param.value,
            ]) as number[] | undefined
            if (!pixel) return
            const px = pixel[0] ?? Number.NaN
            const py = pixel[1] ?? Number.NaN
            if (!Number.isFinite(px) || !Number.isFinite(py)) return
            const distance = Math.hypot(px - pointer.x, py - pointer.y)
            if (distance <= nearestDistance) {
              nearest = param
              nearestDistance = distance
            }
          })
          // 命中具体数据点 → 只看这一个点；否则视为只悬停时间轴 → 列出全部曲线
          if (nearest) rows = [nearest]
        }
        const sorted = [...rows].sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
        const head = `<div class="brpc-tooltip-head">${escapeChartHtml(
          sorted[0]?.axisValueLabel ?? sorted[0]?.axisValue ?? '',
        )}</div>`
        const body = sorted
          .map(
            (param) =>
              `<div class="brpc-tooltip-row"><span class="brpc-tooltip-dot" style="background:${
                param.color
              }"></span><span class="brpc-tooltip-name">${escapeChartHtml(
                param.seriesName,
              )}</span><span class="brpc-tooltip-value">${formatValue(param)}</span></div>`,
          )
          .join('')
        return `<div class="brpc-tooltip">${head}${body}</div>`
      },
    }
  }

  // 文件存在但该文件没有任何 profiling 行 → 「当前筛选时间范围内无数据」
  const brpcHasRows = computed(() => brpcFileRows.value.length > 0)

  const brpcRowMetric = (row: any, metric: BrpcSuccessMetric): number => {
    const ok = row.success_count ?? 0
    const fail = row.failure_count ?? 0
    const req = ok + fail
    switch (metric) {
      case 'successRate':
        // 该桶没有请求（低流量接口）时记 100%：记 0% 会在曲线上画出并不存在的深谷
        return req ? +((ok / req) * 100).toFixed(2) : 100
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
    brpcOverviewSelectedIfaces.value = brpcOverviewSelectedIfaces.value.filter((name) =>
      names.includes(name),
    )
    if (brpcOverviewSelectedIfaces.value.length === 0) brpcOverviewSelectedIfaces.value = [...names]
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

  // ---------- BRPC 通断故障监控 ----------

  const brpcMonitorTab = ref<'iface' | 'fault'>('iface')
  const brpcFaultTab = ref<'event' | 'thread'>('event')
  const brpcFaultSelectedLogId = ref('')
  // 聚合事件表的时间间隔（服务端支持 1s / 1m / 1h），改变后重拉当前页
  const brpcEventWindowSize = ref<'1s' | '1m' | '1h'>('1m')
  // 聚合指标：Pod IP / 线程 ID
  const brpcEventAggregation = ref<'pod' | 'thread'>('pod')
  const brpcEventAggregationOptions = [
    { value: 'pod', label: 'Pod IP' },
    { value: 'thread', label: '线程 ID' },
  ] as const
  const brpcEventWindowOptions = [
    { value: '1s', label: '秒' },
    { value: '1m', label: '分' },
    { value: '1h', label: '时' },
  ] as const
  const brpcFaultBatch = ref<any>(null)
  const brpcFaultTimelineSeries = ref<any[]>([])
  const brpcAggregatedEvents = ref<any[]>([])
  const brpcAggregatedEventTotal = ref(0)
  const brpcAggregatedEventPage = ref(1)
  // 聚合事件按「时间窗 × 接口」重组成矩阵：窗口行 + 故障维度列 + 展开明细
  const brpcAggregatedEventsTruncated = ref(false)
  const brpcExpandedEventWindow = ref('')
  const BRPC_EVENT_WINDOW_PAGE_SIZE = 10
  // 聚合矩阵需要窗口内的全部 Pod 行；一次取满并在 UI 标注截断（后端 page_cnt 上限 1000）
  const BRPC_EVENT_FETCH_PAGE_CNT = 500

  const brpcEventWindowKey = (row: any) =>
    `${String(row?.window_start_time ?? '')}~${String(row?.window_end_time ?? '')}`

  const brpcEventHitTotalOf = (row: any) =>
    (row?.interface_hits ?? []).reduce(
      (sum: number, hit: any) => sum + (hit?.interface_hit_count ?? 0),
      0,
    )

  const brpcEventWindows = computed(() => {
    const grouped = new Map<
      string,
      {
        key: string
        start: string
        end: string
        total: number
        byInterface: Record<string, number>
        pods: any[]
      }
    >()
    for (const row of brpcAggregatedEvents.value) {
      const key = brpcEventWindowKey(row)
      let entry = grouped.get(key)
      if (!entry) {
        entry = {
          key,
          start: String(row.window_start_time ?? ''),
          end: String(row.window_end_time ?? ''),
          total: 0,
          byInterface: {},
          pods: [],
        }
        grouped.set(key, entry)
      }
      const hitTotal = brpcEventHitTotalOf(row)
      entry.total += hitTotal
      for (const hit of row.interface_hits ?? []) {
        const key = String(hit?.interface_id ?? hit?.interface_name ?? '-')
        entry.byInterface[key] = (entry.byInterface[key] ?? 0) + (hit?.interface_hit_count ?? 0)
      }
      entry.pods.push({ ...row, hitTotal })
    }
    return [...grouped.values()].sort((left, right) => left.start.localeCompare(right.start))
  })

  /** 接口列：带 组件 / 接口名 / 函数名（表头三行信息），并按接口 id 作为聚合键 */
  const brpcEventInterfaceColumns = computed(() => {
    const columns = new Map<
      string,
      { id: string; component: string; interfaceName: string; functionName: string }
    >()
    for (const row of brpcAggregatedEvents.value) {
      for (const hit of row.interface_hits ?? []) {
        const id = String(hit?.interface_id ?? hit?.interface_name ?? '-')
        if (columns.has(id)) continue
        columns.set(id, {
          id,
          component: String(hit?.component ?? ''),
          interfaceName: String(hit?.interface_name ?? '-'),
          functionName: String(hit?.function_name ?? '-'),
        })
      }
    }
    return [...columns.values()].sort((first, second) =>
      first.interfaceName.localeCompare(second.interfaceName),
    )
  })

  const brpcEventWindowPages = computed(() =>
    Math.max(1, Math.ceil(brpcEventWindows.value.length / BRPC_EVENT_WINDOW_PAGE_SIZE)),
  )
  const brpcEventWindowPageRows = computed(() => {
    const page = Math.min(Math.max(1, brpcAggregatedEventPage.value), brpcEventWindowPages.value)
    const start = (page - 1) * BRPC_EVENT_WINDOW_PAGE_SIZE
    return brpcEventWindows.value.slice(start, start + BRPC_EVENT_WINDOW_PAGE_SIZE)
  })
  /** 从一组行（Thread / 事件）的 interface_hits 汇总出接口列（三行表头信息） */
  const brpcInterfaceColumnsOf = (rows: any[]) => {
    const columns = new Map<
      string,
      { id: string; component: string; interfaceName: string; functionName: string }
    >()
    for (const row of rows) {
      for (const hit of row?.interface_hits ?? []) {
        const id = String(hit?.interface_id ?? hit?.interface_name ?? '-')
        if (columns.has(id)) continue
        columns.set(id, {
          id,
          component: String(hit?.component ?? ''),
          interfaceName: String(hit?.interface_name ?? '-'),
          functionName: String(hit?.function_name ?? '-'),
        })
      }
    }
    return [...columns.values()].sort((first, second) =>
      first.interfaceName.localeCompare(second.interfaceName),
    )
  }

  /** 异常 Thread 列表的接口列 */
  const brpcThreadInterfaceColumns = computed(() =>
    brpcInterfaceColumnsOf(brpcAbnormalThreads.value),
  )

  /** 聚合事件详情弹窗内「关联异常 Thread」的接口列 */
  const brpcEventDetailThreadInterfaceColumns = computed(() =>
    brpcInterfaceColumnsOf(brpcEventDetailThreads.value),
  )

  /** 单行（Pod / Thread 事件）在某个接口列上的命中数 */
  const brpcRowInterfaceCountOf = (row: any, interfaceId: string) =>
    (row?.interface_hits ?? [])
      .filter((hit: any) => String(hit?.interface_id ?? hit?.interface_name ?? '-') === interfaceId)
      .reduce((sum: number, hit: any) => sum + (hit?.interface_hit_count ?? 0), 0)

  const toggleBrpcEventWindow = (key: string) => {
    brpcExpandedEventWindow.value = brpcExpandedEventWindow.value === key ? '' : key
  }
  const brpcAbnormalThreads = ref<any[]>([])
  const brpcAbnormalThreadTotal = ref(0)
  const brpcAbnormalThreadPage = ref(1)
  // 翻页/搜索只刷新表格：与首屏 brpcFaultLoading 分开，避免整页被加载态替换
  const brpcThreadListLoading = ref(false)
  const brpcEventListLoading = ref(false)
  // 异常 Thread 服务端搜索（线程 ID / Pod IP / Pod 名）
  const brpcThreadSearchInput = ref('')
  const brpcThreadSearchQuery = ref('')
  const brpcFaultLoading = ref(false)
  const brpcFaultError = ref('')
  /**
   * 详情弹窗栈：聚合事件详情 → 「查看 Thread 日志」压栈；关闭/返回只出栈一层，
   * 保证「查看接口命中 → Thread 日志」能返回上层弹窗而不是一次关完。
   */
  const brpcDetailStack = ref<any[]>([])
  const brpcFaultDetail = computed<any>(() => brpcDetailStack.value.at(-1) ?? null)
  const brpcDetailHasParent = computed(() => brpcDetailStack.value.length > 1)
  const closeBrpcFaultDetail = () => {
    brpcDetailStack.value = brpcDetailStack.value.slice(0, -1)
    if (brpcDetailStack.value.length === 0) {
      brpcThreadLogsRequestSeq += 1
      return
    }
    // 出栈后上层弹窗的 DOM 会被重新创建，图容器也是新节点，需要用保留的数据重绘
    const top = brpcDetailStack.value.at(-1)
    if (top?.thread_key) {
      if (brpcThreadDetail.value) {
        renderBrpcThreadTimeline()
      }
      return
    }
    if (brpcEventDetail.value) {
      renderBrpcEventTimeline()
    }
  }
  const brpcFaultBatchId = ref('')
  const brpcThreadLogs = ref<any[]>([])
  const brpcThreadLogsLoading = ref(false)
  const brpcThreadLogsError = ref('')
  // 线程详情（failure_graph / interface_timeline / failure_modes）
  const brpcThreadDetail = ref<any>(null)
  const brpcThreadDetailLoading = ref(false)
  const brpcThreadDetailError = ref('')
  const brpcSelectedGraphNodeId = ref('')
  let brpcThreadLogsRequestSeq = 0
  let brpcThreadListSeq = 0
  let brpcEventListSeq = 0
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

  // UBSocket 公共 API 故障时序的时间聚合尺度。
  // 聚合尺度必须回查后端预聚合桶：10 秒粒度只能由 window_size=10s 产生，
  // 客户端对 1 分钟点再分桶永远得不到 10 秒细节。
  const brpcFaultScaleOptions = [
    { value: 10, label: '10 秒' },
    { value: 60, label: '1 分钟' },
    { value: 600, label: '10 分钟' },
    { value: 3600, label: '1 小时' },
  ] as const
  const brpcFaultScale = ref<number>(60)
  const brpcFaultWindowSizeByScale: Record<number, BrpcTimelineWindowSize> = {
    10: '10s',
    60: '1m',
    600: '10m',
    3600: '1h',
  }
  const brpcFaultTimelineWindowSize = computed<BrpcTimelineWindowSize>(
    () => brpcFaultWindowSizeByScale[brpcFaultScale.value] ?? '1m',
  )

  const brpcFaultSeriesLabel = (series: any) =>
    String(series.interface_name ?? '') +
    (series.function_name ? `（${series.function_name}）` : '')

  const brpcFaultSeriesOptions = computed(() =>
    brpcFaultTimelineSeries.value.map((series: any, index: number) => ({
      id: String(series.interface_id ?? brpcFaultSeriesLabel(series)),
      label: brpcFaultSeriesLabel(series),
      color: BRPC_INTERFACE_COLORS[index % BRPC_INTERFACE_COLORS.length] ?? '#94a3b8',
    })),
  )
  const brpcFaultVisibleSeriesIds = ref<string[]>([])
  watch(brpcFaultSeriesOptions, (options) => {
    brpcFaultVisibleSeriesIds.value = brpcFaultVisibleSeriesIds.value.filter((id) =>
      options.some((option) => option.id === id),
    )
    if (brpcFaultVisibleSeriesIds.value.length === 0) {
      brpcFaultVisibleSeriesIds.value = options.map((option) => option.id)
    }
  })

  // 直接展示后端按 window_size 预聚合的点，前端不再二次分桶：
  // 二次分桶只能把粗粒度点合并得更粗，且会掩盖「查询粒度与尺度不一致」的问题
  const brpcFaultTimelineView = computed(() =>
    brpcFaultTimelineSeries.value.map((series: any, index: number) => ({
      id: String(series.interface_id ?? brpcFaultSeriesLabel(series)),
      label: brpcFaultSeriesLabel(series),
      color: BRPC_INTERFACE_COLORS[index % BRPC_INTERFACE_COLORS.length] ?? '#94a3b8',
      points: (series.points || [])
        .map((point: any) => ({
          time: String(point.window_start_time ?? ''),
          count: point.interface_hit_count ?? 0,
        }))
        .filter((point: { time: string }) => Number.isFinite(tsToEpochMs(point.time)))
        .sort(
          (a: { time: string }, b: { time: string }) => tsToEpochMs(a.time) - tsToEpochMs(b.time),
        ),
    })),
  )

  const brpcFaultZoomed = ref(false)
  let brpcFaultZoomBound = false

  const renderBrpcFaultTimeline = () => {
    afterDomUpdate(() => {
      const el = brpcFaultTimelineRef.value
      if (!el) return
      const chart = getChart(el)
      const seriesList = brpcFaultTimelineView.value.filter((series) =>
        brpcFaultVisibleSeriesIds.value.includes(series.id),
      )
      const times = [
        ...new Set(
          seriesList.flatMap((series) =>
            series.points.map((point: { time: string }) => point.time),
          ),
        ),
      ].sort()
      setChartOption(chart, {
        tooltip: { trigger: 'axis', order: 'valueDesc' },
        // 图例由卡片内的「曲线选择」承担，避免长接口名把图例挤出行外
        legend: { show: false },
        grid: { left: 56, right: 24, top: 24, bottom: 62 },
        dataZoom: [
          { type: 'inside', start: 0, end: 100 },
          { type: 'slider', height: 16, bottom: 8, start: 0, end: 100 },
        ],
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(String(time))),
          axisLabel: { fontSize: 10, rotate: 30, interval: brpcAxisLabelStep(times.length) },
        },
        yAxis: { type: 'value', name: '故障数', minInterval: 1, axisLabel: { fontSize: 10 } },
        series: seriesList.map((series) => {
          const byTime = new Map(
            series.points.map(
              (point: { time: string; count: number }) => [point.time, point.count] as const,
            ),
          )
          return {
            name: series.label,
            type: 'line',
            smooth: true,
            symbol: 'none',
            connectNulls: true,
            data: times.map((time) => byTime.get(time) ?? 0),
            lineStyle: { width: 2, color: series.color },
            itemStyle: { color: series.color },
          }
        }),
      })
      if (!brpcFaultZoomBound) {
        brpcFaultZoomBound = true
        chart.on('dataZoom', () => {
          const option = chart.getOption() as any
          const zoom = Array.isArray(option?.dataZoom) ? option.dataZoom[0] : null
          brpcFaultZoomed.value = !!zoom && (zoom.start > 0.5 || zoom.end < 99.5)
        })
      }
    })
  }

  const resetBrpcFaultZoom = () => {
    const el = brpcFaultTimelineRef.value
    if (!el) return
    const chart = getInstanceByDom(el)
    chart?.dispatchAction({ type: 'dataZoom', start: 0, end: 100 })
    brpcFaultZoomed.value = false
  }

  const selectAllBrpcFaultSeries = () => {
    brpcFaultVisibleSeriesIds.value = brpcFaultSeriesOptions.value.map((option) => option.id)
  }
  const clearBrpcFaultSeries = () => {
    brpcFaultVisibleSeriesIds.value = []
  }
  const toggleBrpcFaultSeries = (id: string) => {
    brpcFaultVisibleSeriesIds.value = brpcFaultVisibleSeriesIds.value.includes(id)
      ? brpcFaultVisibleSeriesIds.value.filter((item) => item !== id)
      : [...brpcFaultVisibleSeriesIds.value, id]
  }

  // 线程详情：failure_graph 节点/边图（点击节点查看故障模式）
  const brpcSelectedGraphNode = computed(() => {
    const id = brpcSelectedGraphNodeId.value
    if (!id) return null
    return (
      brpcThreadDetail.value?.failure_graph?.nodes?.find((node: any) => node.node_id === id) ?? null
    )
  })

  // 故障模式视图：自绘 DAG（HTML + SVG）
  // 不用 ECharts graph：其 view 坐标系会对节点做补偿缩放（符号缩小、文字不缩），导致边框变形与文字溢出
  const BRPC_GRAPH_NODE_W = 200
  const BRPC_GRAPH_TEXT_MAX_W = 168
  const BRPC_GRAPH_H_GAP = 110
  const BRPC_GRAPH_V_GAP = 24
  const BRPC_GRAPH_MARGIN = 36
  const BRPC_GRAPH_LINE_H = 18

  /** 文本宽度估算：CJK/全角按字号计宽，ASCII 按 0.58 倍；用于换行与节点定尺 */
  const brpcGraphTextWidth = (text: string, fontSize: number) => {
    let width = 0
    for (const char of text) {
      width += /[\u2E80-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]/.test(char) ? fontSize : fontSize * 0.58
    }
    return width
  }

  const brpcGraphWrapText = (value: unknown, fontSize: number, maxWidth: number) => {
    const text = String(value ?? '-') || '-'
    const lines: string[] = []
    let line = ''
    for (const char of text) {
      const candidate = line + char
      if (line && brpcGraphTextWidth(candidate, fontSize) > maxWidth) {
        lines.push(line)
        line = char
      } else {
        line = candidate
      }
    }
    lines.push(line || '-')
    return lines.slice(0, 3)
  }

  const brpcThreadGraphLayout = computed(() => {
    const graph = brpcThreadDetail.value?.failure_graph
    const rawNodes: any[] = graph?.nodes ?? []
    if (!rawNodes.length) return null
    const ids = new Set(rawNodes.map((node) => node.node_id))
    const edges = (graph?.edges ?? []).filter(
      (edge: any) => ids.has(edge.source_node_id) && ids.has(edge.target_node_id),
    )
    // 最长路径分层：固定轮次收敛，避免环形边导致死循环
    const depth = new Map<string, number>()
    rawNodes.forEach((node) => depth.set(node.node_id, 0))
    for (let round = 0; round < rawNodes.length; round += 1) {
      let changed = false
      edges.forEach((edge: any) => {
        const next = (depth.get(edge.source_node_id) ?? 0) + 1
        if (next > (depth.get(edge.target_node_id) ?? 0)) {
          depth.set(edge.target_node_id, next)
          changed = true
        }
      })
      if (!changed) break
    }
    const nodes = rawNodes.map((node) => {
      const idLines = brpcGraphWrapText(node.node_id, 11, BRPC_GRAPH_TEXT_MAX_W)
      const nameLines = brpcGraphWrapText(node.name || node.node_id, 12, BRPC_GRAPH_TEXT_MAX_W)
      const tailLines =
        node.node_type === 'interface'
          ? brpcGraphWrapText(node.function_name || '-', 11, BRPC_GRAPH_TEXT_MAX_W)
          : [`命中 ${node.hit_count ?? 0}`]
      // 上下内边距 8px + 边框 2px，避免最后一行贴边被裁
      const height = 16 + (idLines.length + nameLines.length + tailLines.length) * BRPC_GRAPH_LINE_H
      return {
        id: node.node_id,
        nodeType: node.node_type,
        name: node.name || node.node_id,
        functionName: node.function_name,
        hitCount: node.hit_count ?? 0,
        directlyHit: !!node.directly_hit,
        component: node.component,
        width: BRPC_GRAPH_NODE_W,
        height,
        idLines,
        nameLines,
        tailLines,
        x: 0,
        y: 0,
      }
    })
    const byDepth = new Map<number, typeof nodes>()
    nodes.forEach((node) => {
      const level = depth.get(node.id) ?? 0
      const bucket = byDepth.get(level) ?? []
      bucket.push(node)
      byDepth.set(level, bucket)
    })
    const levels = [...byDepth.keys()].sort((first, second) => first - second)
    const laneHeights = levels.map((level) => {
      const bucket = byDepth.get(level) ?? []
      return (
        bucket.reduce((sum, node) => sum + node.height, 0) +
        Math.max(0, bucket.length - 1) * BRPC_GRAPH_V_GAP
      )
    })
    const maxLaneHeight = Math.max(...laneHeights, 0)
    levels.forEach((level, levelIndex) => {
      const bucket = byDepth.get(level) ?? []
      let y = BRPC_GRAPH_MARGIN + (maxLaneHeight - laneHeights[levelIndex]!) / 2
      bucket.forEach((node) => {
        node.x = BRPC_GRAPH_MARGIN + levelIndex * (BRPC_GRAPH_NODE_W + BRPC_GRAPH_H_GAP)
        node.y = y
        y += node.height + BRPC_GRAPH_V_GAP
      })
    })
    const levelCount = levels.length || 1
    const width =
      BRPC_GRAPH_MARGIN * 2 +
      levelCount * BRPC_GRAPH_NODE_W +
      Math.max(0, levelCount - 1) * BRPC_GRAPH_H_GAP
    const height = BRPC_GRAPH_MARGIN * 2 + Math.max(maxLaneHeight, BRPC_GRAPH_NODE_W / 2)
    const nodeById = new Map(nodes.map((node) => [node.id, node]))
    const links = edges.map((edge: any) => {
      const source = nodeById.get(edge.source_node_id)
      const target = nodeById.get(edge.target_node_id)
      const cross = edge.edge_type === 'cross_component'
      if (!source || !target) return null
      // 出口取源节点右侧中点，入口取目标节点左侧中点；控制点做水平偏移形成缓弯
      const x1 = source.x + source.width
      const y1 = source.y + source.height / 2
      const x2 = target.x
      const y2 = target.y + target.height / 2
      const curve = Math.max(28, Math.abs(x2 - x1) * 0.4)
      return {
        id: `${edge.source_node_id}->${edge.target_node_id}`,
        cross,
        d: `M ${x1} ${y1} C ${x1 + curve} ${y1}, ${x2 - curve} ${y2}, ${x2} ${y2}`,
        x1,
        y1,
        x2,
        y2,
      }
    })
    return {
      width,
      height,
      nodes: nodes.map((node) => ({
        ...node,
        outgoing: links.filter(
          (link: { id: string } | null) => link && link.id.startsWith(`${node.id}->`),
        ).length,
      })),
      links: links.filter(Boolean) as Array<{ id: string; cross: boolean; d: string }>,
    }
  })

  // 线程详情：接口命中时序（1m 粒度）
  const renderBrpcThreadTimeline = () => {
    afterDomUpdate(() => {
      const el = brpcThreadTimelineRef.value
      if (!el) return
      const chart = getChart(el)
      chart.resize()
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
          axisLabel: { fontSize: 10, rotate: 30, interval: brpcAxisLabelStep(times.length) },
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

  // 事件详情：当前窗内接口故障时序（10s 粒度）
  const renderBrpcEventTimeline = () => {
    afterDomUpdate(() => {
      const el = brpcEventTimelineRef.value
      if (!el) return
      const chart = getChart(el)
      chart.resize()
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
          axisLabel: { fontSize: 10, rotate: 30, interval: brpcAxisLabelStep(times.length) },
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

  // 尺度切换只重查时序图：请求按序发放，过期响应丢弃，避免慢请求覆盖新尺度
  const brpcFaultTimelineLoading = ref(false)
  const brpcFaultTimelineError = ref('')
  let brpcFaultTimelineSeq = 0
  let brpcFaultTimelineAbort: AbortController | null = null

  const loadBrpcFaultTimeline = async () => {
    const batch = brpcFaultBatch.value
    const batchId = brpcFaultBatchId.value
    if (!batch || !batchId) return
    const { startDate, endDate } = brpcFaultQueryRange(batch)
    const windowSize = brpcFaultTimelineWindowSize.value
    const seq = ++brpcFaultTimelineSeq
    brpcFaultTimelineAbort?.abort()
    const controller = new AbortController()
    brpcFaultTimelineAbort = controller
    brpcFaultTimelineLoading.value = true
    brpcFaultTimelineError.value = ''
    try {
      const result = await fetchBrpcInterfaceTimeline(batchId, startDate, endDate, windowSize, {
        signal: controller.signal,
      })
      if (seq !== brpcFaultTimelineSeq) return
      brpcFaultTimelineSeries.value = result.series ?? []
      // 重绘会回到全量横轴，缩放标记同步复位，避免「重置缩放」按钮残留
      brpcFaultZoomed.value = false
      renderBrpcFaultTimeline()
    } catch (error) {
      if (seq !== brpcFaultTimelineSeq) return
      if ((error as { name?: string } | null)?.name === 'AbortError') return
      brpcFaultTimelineSeries.value = []
      brpcFaultTimelineError.value = errorText(error)
      brpcFaultZoomed.value = false
      renderBrpcFaultTimeline()
    } finally {
      if (seq === brpcFaultTimelineSeq) {
        brpcFaultTimelineLoading.value = false
        brpcFaultTimelineAbort = null
      }
    }
  }

  const loadBrpcFaultData = async () => {
    const logId = brpcFaultSelectedLogId.value || brpcFaultLogOptions.value[0]?.id
    if (!logId) {
      brpcFaultTimelineSeq += 1
      brpcFaultTimelineAbort?.abort()
      brpcFaultTimelineAbort = null
      brpcFaultTimelineLoading.value = false
      brpcFaultTimelineError.value = ''
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
      // 时序图按当前聚合尺度回查后端预聚合桶；失败在卡片内提示，不拖垮事件/线程列表
      const timelineRequest = loadBrpcFaultTimeline()
      const [eventsResult, threadsResult] = await Promise.all([
        (async (): Promise<{ total?: number; events?: any[]; threads?: any[] }> =>
          (brpcEventAggregation.value === 'thread' ? fetchBrpcThreadEvents : fetchBrpcPodEvents)(
            batchId,
            startDate,
            endDate,
            1,
            BRPC_EVENT_FETCH_PAGE_CNT,
            brpcEventWindowSize.value,
          ))(),
        fetchBrpcAbnormalThreads(
          batchId,
          startDate,
          endDate,
          brpcAbnormalThreadPage.value,
          brpcFaultPageSize,
          { search: brpcThreadSearchQuery.value || undefined },
        ),
      ])
      await timelineRequest
      brpcAggregatedEvents.value = eventsResult.events ?? eventsResult.threads ?? []
      brpcAggregatedEventTotal.value = eventsResult.total ?? 0
      brpcAggregatedEventsTruncated.value = (eventsResult.total ?? 0) > BRPC_EVENT_FETCH_PAGE_CNT
      brpcExpandedEventWindow.value = ''
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

  const changeBrpcEventWindowSize = async () => {
    await loadBrpcAggregatedEvents()
  }

  const changeBrpcEventAggregation = async () => {
    brpcAggregatedEventPage.value = 1
    brpcExpandedEventWindow.value = ''
    await loadBrpcAggregatedEvents()
  }

  const goBrpcFaultEventsPage = async (pageNum: number) => {
    // 窗口矩阵为客户端分页（数据一次取满），翻页不重查
    brpcAggregatedEventPage.value = Math.min(Math.max(1, pageNum), brpcEventWindowPages.value)
    brpcExpandedEventWindow.value = ''
  }

  /** 只重拉异常 Thread 列表（翻页/搜索/清空搜索），不动时序图与聚合事件 */
  const loadBrpcAbnormalThreads = async () => {
    const batchId = brpcFaultBatchId.value
    const batch = brpcFaultBatch.value
    if (!batchId || !batch) return
    const seq = ++brpcThreadListSeq
    brpcThreadListLoading.value = true
    try {
      const { startDate, endDate } = brpcFaultQueryRange(batch)
      const result = await fetchBrpcAbnormalThreads(
        batchId,
        startDate,
        endDate,
        brpcAbnormalThreadPage.value,
        brpcFaultPageSize,
        { search: brpcThreadSearchQuery.value || undefined },
      )
      if (seq !== brpcThreadListSeq) return
      brpcAbnormalThreads.value = result.threads ?? []
      brpcAbnormalThreadTotal.value = result.total ?? 0
    } catch (error) {
      if (seq === brpcThreadListSeq) brpcFaultError.value = errorText(error)
    } finally {
      if (seq === brpcThreadListSeq) brpcThreadListLoading.value = false
    }
  }

  /** 只重拉聚合事件（时间间隔切换），不动时序图与 Thread 列表 */
  const loadBrpcAggregatedEvents = async () => {
    const batchId = brpcFaultBatchId.value
    const batch = brpcFaultBatch.value
    if (!batchId || !batch) return
    const seq = ++brpcEventListSeq
    brpcEventListLoading.value = true
    try {
      const { startDate, endDate } = brpcFaultQueryRange(batch)
      const fetchEvents =
        brpcEventAggregation.value === 'thread' ? fetchBrpcThreadEvents : fetchBrpcPodEvents
      const result: { total?: number; events?: any[]; threads?: any[] } = await fetchEvents(
        batchId,
        startDate,
        endDate,
        1,
        BRPC_EVENT_FETCH_PAGE_CNT,
        brpcEventWindowSize.value,
      )
      if (seq !== brpcEventListSeq) return
      brpcAggregatedEvents.value = result.events ?? result.threads ?? []
      brpcAggregatedEventTotal.value = result.total ?? 0
      brpcAggregatedEventsTruncated.value = (result.total ?? 0) > BRPC_EVENT_FETCH_PAGE_CNT
      brpcAggregatedEventPage.value = 1
      brpcExpandedEventWindow.value = ''
    } catch (error) {
      if (seq === brpcEventListSeq) brpcFaultError.value = errorText(error)
    } finally {
      if (seq === brpcEventListSeq) brpcEventListLoading.value = false
    }
  }

  const goBrpcFaultThreadsPage = async (pageNum: number) => {
    brpcAbnormalThreadPage.value = Math.max(1, pageNum)
    await loadBrpcAbnormalThreads()
  }

  // 异常 Thread 搜索：提交/清空均重置页码并重拉
  const submitBrpcThreadSearch = async () => {
    brpcThreadSearchQuery.value = brpcThreadSearchInput.value.trim()
    brpcAbnormalThreadPage.value = 1
    await loadBrpcAbnormalThreads()
  }

  const clearBrpcThreadSearch = async () => {
    if (!brpcThreadSearchInput.value && !brpcThreadSearchQuery.value) return
    brpcThreadSearchInput.value = ''
    brpcThreadSearchQuery.value = ''
    brpcAbnormalThreadPage.value = 1
    await loadBrpcAbnormalThreads()
  }

  const brpcFaultThreadPages = computed(() =>
    Math.max(1, Math.ceil(brpcAbnormalThreadTotal.value / brpcFaultPageSize)),
  )

  // ---------- 聚合事件详情（组件计数 / 当前窗时序 / 关联线程） ----------

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

  const openBrpcFaultDetail = (row: any, asChild = false) => {
    // 从聚合事件弹窗里打开 Thread 明细时压栈（asChild），从列表打开时重置栈
    brpcDetailStack.value = asChild ? [...brpcDetailStack.value, row] : [row]
    // 聚合事件行（无 thread_key）：只重置事件详情并加载；
    // 不能顺带清空 Thread 侧状态，否则从事件弹窗压栈 Thread 时会把父级数据一起抹掉
    if (row && !row.thread_key) {
      brpcEventDetail.value = null
      brpcEventDetailTimeline.value = []
      brpcEventDetailThreads.value = []
      brpcEventDetailError.value = ''
      void loadBrpcEventDetail(row)
      return
    }
    // Thread 行：只重置 Thread 侧状态（父级聚合事件详情保留，返回时直接复用）
    brpcThreadLogs.value = []
    brpcThreadLogsError.value = ''
    brpcThreadDetail.value = null
    brpcThreadDetailError.value = ''
    brpcSelectedGraphNodeId.value = ''
    // 仅异常 Thread 行（带 thread_key）并行加载运行日志与线程详情
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

  // ---------- 异常概览（拓扑 / Pod 分析） ----------

  const allMetrics = [
    { key: 'total_latency_us', label: '总时延', cat: 'SDK' },
    { key: 'sdk_processing_us', label: 'SDK处理', cat: 'SDK' },
    { key: 'master_processing_us', label: 'Master处理', cat: 'Master/Worker' },
    { key: 'worker_access_latency_us', label: 'Worker端总时延', cat: 'Master/Worker' },
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

  const selectedMetrics = ref([
    'total_latency_us',
    'sdk_processing_us',
    'master_processing_us',
    'worker_access_latency_us',
    'urma_processing_us',
    'urma_inflight_max',
    'remote_worker_processing_us',
  ])

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
   * 两层时间数据：
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

  const activePairs = computed(() => toAggregatedPairs(analysisWindowData.value, realOp.value))

  /** 当前可用的指标：跨所有时段任一 ip_pair 出现过合法值（µs/计数） */
  const availableMetrics = computed(() =>
    allMetrics.filter((metric) =>
      timeBuckets.value.some((bucket) =>
        (bucket.ip_pairs ?? []).some((pair) => {
          const value = pairStageMetric(pair, metric.key)
          return value !== null && value > 0
        }),
      ),
    ),
  )
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
      // 默认按异常数排序：「结果数」不表达故障严重度
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
      // 与 faultActivePairs 同口径：单端 / 自转发不计链路
      const pair =
        trace.src_ip && trace.dst_ip && trace.src_ip !== trace.dst_ip
          ? `${trace.src_ip} → ${trace.dst_ip}`
          : ''
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
            .filter((trace) => trace.src_ip && trace.dst_ip && trace.src_ip !== trace.dst_ip)
            .map((trace) => `${trace.src_ip}→${trace.dst_ip}`),
        ).size,
        endpointCount: endpoints.size,
        worstEndpoint: worst?.[0] ?? '-',
        worstEndpointAnomaly: worst?.[1] ?? 0,
      }
    }
    const rate = kpi.traceTotal ? ((kpi.anomalyTotal / kpi.traceTotal) * 100).toFixed(1) : '0.0'
    // 「当前范围端点数 / 最差端点」：跟随 time/dimensions，不随 focus（口径）
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
      ['worker_access_latency_us', 'Worker端总时延', '#fac858'],
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
    { key: 'worker_access_latency_us', label: 'Worker端总时延', color: '#fac858' },
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
    { key: 'worker_access_latency_us', label: 'Worker端总时延', color: '#fac858' },
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

  /** 完整图例：主阶段 + 子项 */
  const podStageFullLegend = [
    { label: 'SDK处理', color: '#5470c6' },
    { label: 'SDK RPC', color: '#ea7ccc' },
    { label: 'Master处理', color: '#91cc75' },
    { label: 'Master RPC', color: '#c23531' },
    { label: 'Worker端总时延', color: '#fac858' },
    { label: 'SDK RPC·网络', color: '#fc8452' },
    { label: 'SDK RPC·框架', color: '#9a60b4' },
    { label: 'Master RPC·网络', color: '#ff9f7f' },
    { label: 'Master RPC·框架', color: '#ffdb5c' },
    { label: 'Worker内部', color: '#73c0de' },
    { label: 'URMA', color: '#6e7074' },
  ]

  // 与「指标趋势与异常分析」一致的颜色（ECharts 默认色板）
  const _STAGE_BASE: Record<string, string> = {
    sdk_processing_us: '#5470c6',
    sdk_rpc_total_us: '#ea7ccc',
    master_processing_us: '#91cc75',
    master_rpc_total_us: '#c23531',
    worker_access_latency_us: '#fac858',
  }
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
        label: 'Worker端总时延',
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

  // ---------- 通断 Trace ID 服务端查询（独立于已加载数据与截断上限） ----------

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

  // ---------- 故障码时序时间聚合尺度（客户端对秒级点再分桶） ----------

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

  // ---------- 通断聚合事件表（服务端 date_trunc 分桶 × src/dst 子表） ----------
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

  // ---------- 对象详情（窗 × 端点/链路，服务端分页） ----------

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

  // 桶点 IP 对时传入一次性时间窗覆盖，仅影响该次详情请求与标题，不回写 filter
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

  // 通断域入口：按通断接口真实字段发送 endpoint_ip / src+dst
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
  // 桶点 IP 对，以桶窗为时间上下文打开链路故障 Trace（不回写 disconnectFilter.time）
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

  // ---------- Trace 抽屉相关故障语义 ----------
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
  const brpcSuccessOverviewRef = ref<HTMLElement | null>(null)
  const brpcSingleRef = ref<HTMLElement | null>(null)
  const brpcLatencyMonitorRef = ref<HTMLElement | null>(null)
  const brpcLatencyRef = ref<HTMLElement | null>(null)
  const brpcFaultTimelineRef = ref<HTMLElement | null>(null)
  const brpcEventTimelineRef = ref<HTMLElement | null>(null)
  const brpcThreadTimelineRef = ref<HTMLElement | null>(null)

  // 图表容器尺寸变化（窗口缩放 / 侧栏收放 / 弹窗尺寸变化）时自动 resize，
  // 否则 ECharts 会保留初始化时的画布尺寸，内容画到窗口外面。
  const chartEntries = new Map<HTMLElement, ECharts>()
  const pendingChartResize = new Set<HTMLElement>()
  let chartResizeFrame = 0
  let chartResizeObserver: ResizeObserver | null = null
  const flushChartResize = () => {
    chartResizeFrame = 0
    const targets = [...pendingChartResize]
    pendingChartResize.clear()
    targets.forEach((element) => {
      const chart = chartEntries.get(element)
      if (!chart) return
      if (!element.isConnected || element.clientWidth === 0) {
        chartResizeObserver?.unobserve(element)
        chartEntries.delete(element)
        return
      }
      if (!chart.isDisposed()) chart.resize()
    })
  }
  if (typeof ResizeObserver !== 'undefined') {
    chartResizeObserver = new ResizeObserver((entries) => {
      entries.forEach((entry) => pendingChartResize.add(entry.target as HTMLElement))
      if (chartResizeFrame) return
      chartResizeFrame = requestAnimationFrame(flushChartResize)
    })
  }

  const getChart = (element: HTMLElement) => {
    const chart = getInstanceByDom(element) || init(element)
    if (chartEntries.get(element) !== chart) {
      chartEntries.set(element, chart)
      chartResizeObserver?.observe(element)
    }
    return chart
  }

  // 统一关闭动画：统计图直接出结果，不做过渡动画
  const setChartOption = (chart: ECharts, option: any) => {
    chart.setOption({ ...option, animation: false }, { replaceMerge: ['series', 'legend'] })
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
    // nodeWhitelist 只控制本地可视化，不冒充服务端过滤
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

  // focus 是当前分析对象的唯一事实源：点节点/边/空白都在写它
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
    // 点空白：清对象，保留 time
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

      // 点击即分析：点节点/边写 focus，点空白清 focus（保留 time）
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
      // 粗粒度 P95/P99 是 10 秒桶分位值的再聚合近似（文案口径）
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
      // 曲线集合与当前桶数据对齐：无数据的指标不渲染
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

  // 最慢请求图 tooltip 可点击固定，并支持一键复制 Trace ID
  const escapeChartHtml = (value: unknown) =>
    String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;')

  const copyTextToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      const copied = document.execCommand('copy')
      textarea.remove()
      return copied
    }
  }

  let slowTooltipPinned = false
  let slowTooltipBound = false

  const unpinSlowTooltip = (chart: ECharts) => {
    if (!slowTooltipPinned) return
    slowTooltipPinned = false
    chart.setOption({
      tooltip: { alwaysShowContent: false, triggerOn: 'mousemove|click', hideDelay: 0 },
    })
    chart.dispatchAction({ type: 'hideTip' })
    chart.setOption({ tooltip: { hideDelay: 300 } })
  }

  const handleSlowTooltipCopyClick = async (event: MouseEvent) => {
    const target = event.target instanceof Element ? event.target : null
    const button = target?.closest<HTMLButtonElement>('.slow-tooltip-copy')
    if (!button) return
    event.stopPropagation()
    const traceId = button.dataset.traceId
    if (!traceId) return
    const copied = await copyTextToClipboard(traceId)
    button.textContent = copied ? '已复制' : '复制失败'
    window.setTimeout(() => {
      if (button.isConnected) button.textContent = '复制'
    }, 1500)
  }

  const handleSlowTooltipDocumentClick = (event: MouseEvent) => {
    const target = event.target instanceof Element ? event.target : null
    if (target?.closest('.slow-tooltip')) return
    const chart = slowRef.value ? getInstanceByDom(slowRef.value) : null
    if (chart) unpinSlowTooltip(chart)
  }

  const bindSlowTooltipInteractions = (chart: ECharts) => {
    if (slowTooltipBound) return
    slowTooltipBound = true
    chart.on('click', (params: any) => {
      if (params.componentType !== 'series' || params.seriesType !== 'bar') return
      ;(params.event?.event as MouseEvent | undefined)?.stopPropagation()
      slowTooltipPinned = true
      chart.setOption({ tooltip: { alwaysShowContent: true, triggerOn: 'none' } })
      chart.dispatchAction({
        type: 'showTip',
        seriesIndex: params.seriesIndex,
        dataIndex: params.dataIndex,
      })
    })
    document.addEventListener('click', handleSlowTooltipDocumentClick)
    document.addEventListener('click', (event) => {
      void handleSlowTooltipCopyClick(event)
    })
  }

  const renderSlowChart = () => {
    afterDomUpdate(() => {
      const el = slowRef.value
      if (!el) return
      const chart = getChart(el)
      bindSlowTooltipInteractions(chart)
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
          // tooltip 可交互，支持一键复制 Trace ID
          enterable: true,
          hideDelay: 300,
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
            return `<div class="slow-tooltip" style="min-width:260px"><strong>${row.timestampLabel}</strong><div class="slow-tooltip-trace"><small>${escapeChartHtml(row.traceId)} · ${escapeChartHtml(row.operation)}</small><button type="button" class="slow-tooltip-copy" data-trace-id="${escapeChartHtml(row.traceId)}">复制</button></div><div style="margin:6px 0;border-top:1px solid #D9E0E8"></div>${details}<div style="margin-top:6px;display:flex;justify-content:space-between"><span>总时延</span><b style="color:#EF4444">${formatLatency(row.totalLatency / 1000)}</b></div></div>`
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
      // 缺对端或自转发（内部重定向）不构成链路，避免图里出现自环
      if (!src || !dst || src === dst) return
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

  // 无法构成链路的 Trace：端点照常统计，链路视图单独提示
  const faultUnpairedTraceCount = computed(
    () =>
      faultScopedTraces.value.filter((trace) => {
        const src = String(trace.src_ip || '')
        const dst = String(trace.dst_ip || '')
        return !src || !dst || src === dst
      }).length,
  )

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
      // 节点 = 受影响端点（src/dst/pod_names 去重），不用链路反推
      faultPodStats.value.forEach((endpoint) => {
        nodeMap.set(endpoint.ip, {
          ip: endpoint.ip,
          faults: endpoint.faults,
          src: endpoint.src,
          dst: endpoint.dst,
          codes: new Set(endpoint.codes),
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
      const minCount = pairCounts.length ? Math.min(...pairCounts) : 0
      const maxCount = pairCounts.length ? Math.max(...pairCounts) : 0
      const maxNodeFaults = Math.max(1, ...ordered.map((node) => node.faults))

      const nodes = ordered.map((node) => {
        const pos = positions.get(node.ip)
        const color = faultCodeColor(
          faultCodeColorOrder.value.find((code) => node.codes.has(code)) ??
            [...node.codes][0] ??
            '',
        )
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
        const normalized =
          maxCount > minCount
            ? Math.log1p(pair.faults - minCount) / Math.log1p(maxCount - minCount)
            : 1
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

      // 上下留出标签高度（半径 30 + 间距 7 + 标签约 20），避免 IP 标签被裁掉
      const labelSpace = 57
      const graphSize = Math.max(
        200,
        Math.min(el.clientWidth - 80, el.clientHeight - labelSpace * 2),
      )
      const graphLeft = Math.max(40, (el.clientWidth - graphSize) / 2)
      const graphTop = Math.max(labelSpace, (el.clientHeight - graphSize) / 2)

      setChartOption(chart, {
        animation: false,
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => {
            if (params.dataType === 'node') {
              const data = params.data
              const roleText =
                data.src + data.dst > 0
                  ? `出方向(源): ${data.src} &nbsp; 入方向(目标): ${data.dst}`
                  : '仅出现在端点信息（Pod IP）里，日志没有给出对端地址'
              return `<b>${data.name}</b><br/>故障次数: ${data.faults}<br/>${roleText}<br/>关联故障码: ${data.codes.join(', ') || '-'}`
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

      // 点节点/边进入「窗 + 端点/链路」的故障 Trace（按通断接口字段发送）
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
      // 按所选尺度再分桶后的展示数据；原始秒级数据仅用于空态与抽稀判断
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

  // 成功率总览：按勾选接口逐条曲线，指标可切换（成功率/失败率/请求数/成功量/失败量）
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
      const series = brpcOverviewSelectedIfaces.value.map((iface) => {
        const rowByTs = new Map<string, any>()
        brpcFileRows.value.forEach((row) => {
          if (row.interface_name !== iface || !row.timestamp) return
          rowByTs.set(String(row.timestamp).slice(0, 19), row)
        })
        const color = brpcIfaceColor(iface)
        return {
          name: iface,
          type: 'line',
          ...brpcLineSymbol,
          smooth: true,
          lineStyle: { width: 2, color },
          itemStyle: { color },
          data: times.map((time) => {
            const row = rowByTs.get(time)
            return row ? brpcRowMetric(row, metric) : null
          }),
        }
      })
      setChartOption(chart, {
        tooltip: brpcAxisTooltip(chart, (param: any) =>
          typeof param.value === 'number' ? `${param.value}${isRate ? '%' : ''}` : '-',
        ),
        legend: { show: false },
        grid: { left: 64, right: 32, top: 24, bottom: 76 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(time)),
          axisLabel: {
            fontSize: 10,
            rotate: 30,
            interval: brpcAxisLabelStep(times.length),
            hideOverlap: true,
          },
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

  // 单接口监控：指标多选（请求数/成功率/失败率/成功量/失败量），数量与比率分离双轴
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
        // 数量与比率混在同一张图里，逐条曲线按自己的口径带上单位
        tooltip: brpcAxisTooltip(chart, (param: any) => {
          if (typeof param.value !== 'number') return '-'
          const metric = brpcSingleMetrics.find(
            (option) => option.label === param.seriesName,
          )?.value
          return metric && isBrpcRateMetric(metric) ? `${param.value}%` : String(param.value)
        }),
        // 图例居中放，避免与右轴名（比率 %）在右上角重叠
        legend: { left: 'center', top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 64, right: 64, top: 48, bottom: 76 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(time)),
          axisLabel: {
            fontSize: 10,
            rotate: 30,
            interval: brpcAxisLabelStep(times.length),
            hideOverlap: true,
          },
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
            ...brpcLineSymbol,
            smooth: true,
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

  // 单接口时延：与「全接口总览 · 时延」同一批指标（total/avg/min/P50...P999），单位统一 µs；
  // 默认 avg+P99+max，保持原有观感
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
      const selected = brpcSingleLatencySelectedMetrics.value.filter((metric) =>
        brpcSingleLatencyMetrics.some((option) => option.value === metric),
      )
      const metricDefs = brpcSingleLatencyMetrics.filter((option) =>
        selected.includes(option.value),
      )
      setChartOption(chart, {
        tooltip: brpcAxisTooltip(chart, (param: any) =>
          typeof param.value === 'number' ? `${param.value} µs` : '-',
        ),
        legend: { left: 'center', top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 64, right: 40, top: 48, bottom: 76 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(time)),
          axisLabel: {
            fontSize: 10,
            rotate: 30,
            interval: brpcAxisLabelStep(times.length),
            hideOverlap: true,
          },
        },
        yAxis: { type: 'value', name: '时延 (µs)', axisLabel: { fontSize: 10 } },
        series: metricDefs.map((def) => ({
          name: def.label,
          type: 'line',
          ...brpcLineSymbol,
          smooth: true,
          lineStyle: { width: 2, color: brpcSingleLatencyColor(def.value) },
          itemStyle: { color: brpcSingleLatencyColor(def.value) },
          data: times.map((time) => {
            const row = rowByTs.get(time)
            const value = row?.[def.value]
            // profiling 行内时延字段单位为 ns，展示时换算到 µs
            return typeof value === 'number' && Number.isFinite(value)
              ? +(value / 1000).toFixed(1)
              : null
          }),
        })),
      })
    })
  }

  // 时延监控（µs）：指标下拉（total/avg/max/min/P50/P90/P95/P99/P999）+ 多接口曲线勾选
  const renderBrpcLatencyMonitorChart = () => {
    afterDomUpdate(() => {
      const el = brpcLatencyMonitorRef.value
      if (!el) return
      const chart = getChart(el)
      const times = brpcIfaceTimestamps.value
      const metricKey = brpcLatencyMetric.value
      const metricLabel =
        brpcLatencyMetrics.find((item) => item.value === metricKey)?.label ?? metricKey
      const series = brpcOverviewSelectedIfaces.value.map((iface) => {
        const rowByTs = new Map<string, any>()
        brpcFileRows.value.forEach((row) => {
          if (row.interface_name !== iface || !row.timestamp) return
          rowByTs.set(String(row.timestamp).slice(0, 19), row)
        })
        const color = brpcIfaceColor(iface)
        return {
          name: iface,
          type: 'line',
          ...brpcLineSymbol,
          smooth: true,
          lineStyle: { width: 2, color },
          itemStyle: { color },
          data: times.map((time) => {
            const value = rowByTs.get(time)?.[metricKey]
            // profiling 行内时延字段单位为 ns，图表标注 µs，需在 UI 边界换算
            return typeof value === 'number' && Number.isFinite(value)
              ? +(value / 1000).toFixed(2)
              : null
          }),
        }
      })
      setChartOption(chart, {
        tooltip: brpcAxisTooltip(chart, (param: any) =>
          typeof param.value === 'number' ? `${param.value} µs` : '-',
        ),
        legend: { show: false },
        grid: { left: 68, right: 32, top: 24, bottom: 76 },
        xAxis: {
          type: 'category',
          data: times.map((time) => formatChartTs(time)),
          axisLabel: {
            fontSize: 10,
            rotate: 30,
            interval: brpcAxisLabelStep(times.length),
            hideOverlap: true,
          },
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
      brpcOverviewSelectedIfaces.value = []
      brpcSingleIface.value = ''
      brpcSingleSelectedMetrics.value = ['requestCount', 'successRate', 'failureRate']
      brpcSingleLatencySelectedMetrics.value = ['avg_ns', 'p99_ns', 'max_ns']
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
      brpcDetailStack.value = []
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
      [scopeData, brpcInterfaces],
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

    // 故障码时序尺度变化只改展示分桶，不回写 disconnectFilter.time
    watch(faultChartScale, () => {
      if (!isAssetMode.value || isBrpcTask.value || analysisTab.value !== 'disconnect') return
      renderFaultChart()
    })

    // UBSocket 故障时序的聚合尺度变化 → 按新 window_size 回查预聚合桶后重绘
    watch(brpcFaultScale, () => {
      if (!isAssetMode.value || !isBrpcTask.value) return
      void loadBrpcFaultTimeline()
    })

    // 曲线勾选只影响展示，不重查
    watch(brpcFaultVisibleSeriesIds, () => {
      if (!isAssetMode.value || !isBrpcTask.value) return
      renderBrpcFaultTimeline()
    })

    // UBSocket 文件/指标/曲线勾选/单接口变化 → 重绘接口监控图
    watch(
      [
        brpcFileRows,
        brpcSuccessMetric,
        brpcOverviewSelectedIfaces,
        brpcSingleIface,
        brpcSingleSelectedMetrics,
        brpcLatencyMetric,
        brpcSingleLatencySelectedMetrics,
      ],
      () => {
        if (!isAssetMode.value || !isBrpcTask.value) return

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
        // 默认跨任务汇总；仅在已选日志失效时回到“全部任务”
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

    // 用户切换日志文件 → 清缓存并按当前页签重载
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
    allMetrics,
    analysisModule,
    analysisTab,
    assetTypeFilter,
    brpcAbnormalThreadPage,
    brpcAbnormalThreadTotal,
    brpcAbnormalThreads,
    brpcThreadListLoading,
    brpcEventListLoading,
    brpcAggregatedEventPage,
    brpcAggregatedEventTotal,
    brpcAggregatedEventsTruncated,
    brpcEventInterfaceColumns,
    brpcEventWindowPageRows,
    brpcEventWindowPages,
    brpcEventWindows,
    brpcExpandedEventWindow,
    toggleBrpcEventWindow,
    brpcFaultBatch,
    brpcDetailHasParent,
    brpcFaultDetail,
    brpcThreadGraphLayout,
    closeBrpcFaultDetail,
    brpcThreadLogs,
    brpcThreadLogsLoading,
    brpcThreadLogsError,
    brpcFaultError,
    brpcFaultLoading,
    brpcEventAggregation,
    brpcEventAggregationOptions,
    brpcRowInterfaceCountOf,
    brpcThreadInterfaceColumns,
    brpcEventDetailThreadInterfaceColumns,
    brpcEventWindowOptions,
    brpcEventWindowSize,
    changeBrpcEventAggregation,
    changeBrpcEventWindowSize,
    brpcFaultLogOptions,
    brpcFaultScale,
    brpcFaultScaleOptions,
    brpcFaultSelectedLogId,
    brpcFaultSeriesOptions,
    brpcFaultTab,
    brpcFaultThreadPages,
    brpcFaultTimelineRef,
    brpcFaultTimelineError,
    brpcFaultTimelineLoading,
    brpcFaultVisibleSeriesIds,
    brpcFaultZoomed,
    clearBrpcFaultSeries,
    resetBrpcFaultZoom,
    selectAllBrpcFaultSeries,
    toggleBrpcFaultSeries,
    faultActivePairs,
    activeFaultTraces,
    faultCodeSummaries,
    faultCodeColor,
    faultCodeColorOrder,
    faultPodStats,
    faultUnpairedTraceCount,
    faultTopoRef,
    renderFaultTopology,
    latencyFilter,
    disconnectFilter,
    selectedFaultCode,
    clearAnalysisTime,
    analysisWindowLoading,
    timelineTruncated,
    overviewScale,
    overviewScaleOptions,
    timeRangeLabel,
    anomalyRef,
    renderAnomalyChart,
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
    brpcThreadSearchInput,
    brpcThreadSearchQuery,
    brpcThreadTimelineRef,
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
    brpcLoading,
    brpcMonitorError,
    brpcMonitorTab,
    brpcOverviewSelectedIfaces,
    brpcProfilingFiles,
    brpcScopeTasks,
    brpcSelectedFileKey,
    brpcSingleIface,
    brpcSingleLatencyColor,
    brpcSingleLatencyMetrics,
    brpcSingleLatencySelectedMetrics,
    brpcSingleMetricColor,
    brpcSingleMetrics,
    brpcSingleRef,
    brpcSingleSelectedMetrics,
    brpcSuccessMetric,
    brpcSuccessMetricOptions,
    brpcSuccessOverviewRef,
    changeBrpcFaultLog,
    clearBrpcThreadSearch,
    clearFaultRange,
    clearFaultTraceQuery,
    clearTrend,
    currentOp,
    detailDrawerOpen,
    detailDrawerRow,
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
    loadFaultAggPairs,
    objectDetail,
    objectDetailPages,
    objectDetailGoPage,
    closeObjectDetail,
    focusPairs,
    failureModeOf,
    faultChartData,
    faultChartRef,
    faultChartSampled,
    faultChartScale,
    faultChartScaleOptions,
    faultTimeRange,
    faultTraceIdInput,
    faultTracePage,
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
    goBrpcFaultEventsPage,
    goBrpcFaultThreadsPage,
    isBrpcTask,
    kpiData,
    loadBrpcFaultData,
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
    podStageFlow,
    podStageFullLegend,
    podIpCbPage,
    podIpCbPages,
    podPage,
    podPageSize,
    podPages,
    renderAnalysisModules,
    renderBrpcLatencyChart,
    renderBrpcLatencyMonitorChart,
    renderBrpcSingleChart,
    renderBrpcSuccessOverviewChart,
    renderBrpcFaultTimeline,
    submitBrpcThreadSearch,
    renderFaultChart,
    renderSlowChart,
    renderTopology,
    renderTrendChart,
    resetOverviewFilter,
    resetTopologyFilter,
    resetTrend,
    scopeTaskCount,
    scopeTasks,
    selectAllTrend,
    selectedTopologyLink,
    selectedTopologyNode,
    selectTopologyLink,
    selectTopologyNode,
    showLinkEndsOnly,
    setCurrentOp,
    showPodIpCb,
    slowRef,
    slowRows,
    slowTotal,
    toggleTrendSeries,
    topoHiddenCount,
    topoNodeLimit,
    topoShowAll,
    topoTotalCount,
    visibleTopologyLinks,
    topologySummary,
    topoRef,
    traceBreakdownTitle,
    traceCluster,
    traceClusters,
    traceDrawerLogs,
    tracePage,
    tracePages,
    traceRows,
    traceSearch,
    traceSegments,
    relatedFailureModeIdsOf,
    traceFailureModeIdsOf,
    traceStageRows,
    trendAnomalyHint,
    trendChartData,
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
