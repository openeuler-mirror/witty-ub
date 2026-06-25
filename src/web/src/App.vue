<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { ECharts, EChartsOption } from 'echarts'
import { useTableSort, type SortField } from './composables/useTableSort'

type LogKnowledge = {
  id: string
  name: string
  description: string
  existed_status?: boolean
  task_cnt?: number
  log_file_cnt?: number
  anomaly_cnt?: number
  created_at?: string
  updated_at?: string
}

type TaskReportModel = {
  task_id?: string
  progress?: number | string | null
  message?: string | null
  created_at?: string | null
}

type TaskModel = {
  id: string
  status?: string
  task_type?: string
  task_reports?: TaskReportModel[]
  created_at?: string
  completed_at?: string | null
  duration_seconds?: number | null
}

type LogFileModel = {
  id: string
  log_file_id?: string
  kb_id: string
  name: string
  parse_status: string
  file_path: string
  file_size: number
  anomaly_cnt: number
  trace_failure_event_cnt?: number
  task: TaskModel | null
  existed_status: boolean
  created_at: string
}

type LogParseResultModel = {
  id: string
  anomalous_event_id?: string | null
  is_anomalous?: boolean | number | null
  anomaly_reason?: string | null
  remark?: string | null
  timestamp?: string | null
  created_at?: string
  trace_id?: string | null
  cluster_name?: string | null
  host?: string | null
  src_ip?: string | null
  dst_ip?: string | null
  pod_ip?: string | null
  pod_id?: string | null
  pod_name?: string | null
  log_level?: string | null
  level?: string | null
  filename?: string | null
  pid_tid?: string | null
  message?: string | null
  operation?: string | null
  total_latency?: number | null
  worker_query_meta_latency?: number | null
  urma_total_latency?: number | null
  urma_link_latency?: number | null
  c2w_urma_latency?: number | null
  w2w_urma_latency?: number | null
  sdk_process?: number | null
  sdk_rpc?: number | null
  local_worker_cost?: number | null
  local_worker_lock?: number | null
  remote_worker_cost?: number | null
  remote_worker_rpc?: number | null
  master_process?: number | null
  master_rpc_total?: number | null
  [key: string]: unknown
}

type LatencyMetricItem = {
  time?: string | null
  timestamp?: string | null
  created_at?: string
  total_latency?: number | null
  worker_query_meta_latency?: number | null
  urma_total_latency?: number | null
  sdk_process?: number | null
  sdk_rpc?: number | null
  local_worker_cost?: number | null
  local_worker_lock?: number | null
  remote_worker_cost?: number | null
  remote_worker_rpc?: number | null
  master_process?: number | null
  master_rpc_total?: number | null
  [key: string]: unknown
}

type ErrCodeMetricItem = {
  time?: string | null
  timestamp?: string | null
  created_at?: string
  err_cnt?: number | null
  count?: number | null
  value?: number | null
  [key: string]: unknown
}

type AggregatedEventModel = {
  id: string
  src_ip?: string | null
  dst_ip?: string | null
  log_parse_result_cnt?: number | null
  anomaly_log_parse_result_cnt?: number | null
  ave_total_latency?: number | null
  min_total_latency?: number | null
  max_total_latency?: number | null
  p99_total_latency?: number | null
  p95_total_latency?: number | null
  ave_query_meta_latency?: number | null
  min_query_meta_latency?: number | null
  max_query_meta_latency?: number | null
  p99_query_meta_latency?: number | null
  p95_query_meta_latency?: number | null
  ave_urma_total_latency?: number | null
  min_urma_total_latency?: number | null
  max_urma_total_latency?: number | null
  p99_urma_total_latency?: number | null
  p95_urma_total_latency?: number | null
  ave_urma_link_latency?: number | null
  min_urma_link_latency?: number | null
  max_urma_link_latency?: number | null
  p99_urma_link_latency?: number | null
  p95_urma_link_latency?: number | null
  ave_c2w_urma_latency?: number | null
  min_c2w_urma_latency?: number | null
  max_c2w_urma_latency?: number | null
  p99_c2w_urma_latency?: number | null
  p95_c2w_urma_latency?: number | null
  ave_w2w_urma_latency?: number | null
  min_w2w_urma_latency?: number | null
  max_w2w_urma_latency?: number | null
  p99_w2w_urma_latency?: number | null
  p95_w2w_urma_latency?: number | null
  [key: string]: unknown
}

type LatencyDetailRow = {
  id: string
  sourceHost: string
  targetHost: string
  traceCount: number
  anomalyTraceCount: number
  event: AggregatedEventModel
}

type TraceDetailRow = {
  traceId: string
  clusterName?: string
  host?: string
  podIp: string
  time: string
  sdkMs: number | null
  reqDelay: number | null
  respDelay: number | null
  urmaLinkLatency: number | null
  c2wUrmaLatency: number | null
  w2wUrmaLatency: number | null
  sdkProcess: number | null
  sdkRpc: number | null
  localWorkerCost: number | null
  localWorkerLock: number | null
  remoteWorkerCost: number | null
  remoteWorkerRpc: number | null
  masterProcess: number | null
  masterRpcTotal: number | null
  faultCode?: string
  faultType?: string
  faultDomain?: string
}

type FaultTraceTableRow = TraceDetailRow & {
  id: string
  podNames: string[]
  hostNames: string[]
  clusterNames: string[]
  failureModeId?: string
  failureMode?: FailureModeKnowledgeModel | null
}

type TraceFilterTarget = {
  traceId: string
  clusterName?: string
  host?: string
  podIp: string
  faultCode?: string
}

type FaultDetailRow = {
  id: string
  sourceHost: string
  targetHost: string
  total: number
  faultCodes: string[]
}

type FaultAggregatedEventRow = {
  id: string
  startTime: string
  endTime: string
  faultCodeCounts: Record<string, number>
}

type FaultAggregatedEventPodRow = {
  id: string
  podIp: string
  faultCodeCounts: Record<string, number>
}

type FaultAggregatedEventDetail = {
  eventRow: FaultAggregatedEventRow
  podRow: FaultAggregatedEventPodRow
}

type TimeAggregatedFailureEventModel = {
  start_time: string
  end_time: string
  status_code_cnt: Record<string, number>
}

type ListTimeAggregatedFailureEventMsg = {
  total: number
  err_codes: string[]
  events: TimeAggregatedFailureEventModel[]
}

type PodAggregatedFailureEventModel = {
  pod_name: string
  status_code_cnt: Record<string, number>
}

type ListPodAggregatedFailureEventMsg = {
  total: number
  events: PodAggregatedFailureEventModel[]
}

type FaultAggregateInterval = 'hour' | 'minute' | 'second'

type TraceRawLogColumn = {
  label: string
  value: string
}

type TraceLogRow = {
  time: string
  level: 'INFO' | 'ERROR'
  filename: string
  podIp: string
  pidTid: string
  traceId: string
  clusterName: string
  message: string
  failureModeIds: string[]
  faultType?: string
  faultDomain?: string
  rawText: string
  formatName: string
  rawColumns: TraceRawLogColumn[]
}

type LogFailureEventResultModel = {
  id: string
  log_id?: string
  log_file?: string
  raw_text?: string
  host_name?: string
  timestamp?: string
  level?: string
  filename?: string
  pod_name?: string
  pid?: string
  tid?: string
  trace_id?: string
  cluster_name?: string
  message?: string
  status_code?: string
  failure_mode?: string[]
  [key: string]: unknown
}

type TraceFailureEventResultModel = {
  id: string
  trace_id?: string
  log_id?: string
  pod_names?: string[]
  host_names?: string[]
  cluster_names?: string[]
  timestamp?: string
  status_code?: string
  failure_mode?: string
  [key: string]: unknown
}

type FailureModeKnowledgeModel = {
  id: string
  name?: string
  symptom?: string
  root_cause?: string
  solution?: string
  failure_domain?: string
  children_failure_mode_ids?: string
  [key: string]: unknown
}

type ParseResultTableRow = {
  id: string
  logStatus: LogDisplayStatus
  statusReason: string
  time: string
  traceId: string
  podIp: string
  operation: string
  clusterName: string
  host: string
  totalLatency: number | null
  queryMetaLatency: number | null
  urmaTotalLatency: number | null
  urmaLinkLatency: number | null
  c2wUrmaLatency: number | null
  w2wUrmaLatency: number | null
  sdkProcess: number | null
  sdkRpc: number | null
  localWorkerCost: number | null
  localWorkerLock: number | null
  remoteWorkerCost: number | null
  remoteWorkerRpc: number | null
  masterProcess: number | null
  masterRpcTotal: number | null
  raw: LogParseResultModel
}

type LogDisplayStatus = 'failed' | 'timeout' | 'normal'

type AbnormalTraceRow = {
  id: string
  logStatus: LogDisplayStatus
  statusReason: string
  time: string
  traceId: string
  podIp: string
  operation: string
  clusterName: string
  host: string
  totalLatency: number | null
  queryMetaLatency: number | null
  urmaTotalLatency: number | null
  urmaLinkLatency: number | null
  c2wUrmaLatency: number | null
  w2wUrmaLatency: number | null
  sdkProcess: number | null
  sdkRpc: number | null
  localWorkerCost: number | null
  localWorkerLock: number | null
  remoteWorkerCost: number | null
  remoteWorkerRpc: number | null
  masterProcess: number | null
  masterRpcTotal: number | null
  raw: LogParseResultModel
}

type LatencyChartRange = {
  centerTime: number
  startTime: number
  endTime: number
  label: string
}

type LatencyPercentileValue = 'p99' | 'p9999'

type AnomalousEventChainModel = {
  id: string
  anomalous_event_id?: string | null
  anomaly_code?: string | null
  anomaly_desc?: string | null
  anomaly_description?: string | null
  anomaly_domain?: string | null
  src_ip?: string | null
  dst_ip?: string | null
  pod_ip?: string | null
  pod_id?: string | null
  trace_id?: string | null
  timestamp?: string | null
  created_at?: string
  [key: string]: unknown
}

type ApiResponse<T> = {
  code?: number
  message?: string
  result?: T
  data?: T
}

type UploadLogFilesResult = {
  log_file_ids?: string[]
}

type GetLogFileResult = {
  log_file?: LogFileModel | null
}

type LogParseOptions = {
  clusters?: string[]
  hosts?: string[]
}

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const assetPageSize = 5
const logFilesPageSize = 10
const abnormalTracesPageSize = 30
const faultAggregatedEventPageSize = 20
const faultAggregatedEventPodPageSize = 10
const faultTraceEventsPageSize = 30
const logFilesPollIntervalMs = 3_000
const severeLogTimeoutThresholdMs = 150
const isFaultCodeFeatureEnabled = true
const toFaultAggregatedEventRows = (
  events: TimeAggregatedFailureEventModel[],
): FaultAggregatedEventRow[] =>
  events.map((event, index) => ({
    id: `${event.start_time}-${event.end_time}-${index}`,
    startTime: event.start_time,
    endTime: event.end_time,
    faultCodeCounts: event.status_code_cnt,
  }))

const assets = ref<LogKnowledge[]>([])
const selectedAsset = ref<LogKnowledge | null>(null)
const selectedAssetId = ref<string | null>(null)
const assetPage = ref(1)
const assetTotal = ref(0)
const activePage = ref<'asset' | 'abnormal'>('asset')
const isListLoading = ref(false)
const isDetailLoading = ref(false)
const isSaving = ref(false)
const isQuerying = ref(false)
const errorMessage = ref('')

const logSourceInput = ref('')
const isUploadingLog = ref(false)
const uploadLogError = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)
const logFiles = ref<LogFileModel[]>([])
const isLogFilesLoading = ref(false)
const isLogFilesPolling = ref(false)
const logFilesPage = ref(1)
const logFilesTotal = ref(0)
const togglingFileIds = ref<Set<string>>(new Set())
const refreshingFileIds = ref<Set<string>>(new Set())
const uploadedLogFileIdsBySource = ref<Record<string, string>>({})
const taskDetailsById = ref<Record<string, TaskModel>>({})
const loadingTaskDetailIds = ref<Set<string>>(new Set())
const logFileAnomalyCntById = ref<Record<string, number>>({})
const logFileTraceFailureEventCntById = ref<Record<string, number>>({})
const loadedAnomalyLogFileIds = ref<Set<string>>(new Set())
const loadingAnomalyLogFileIds = ref<Set<string>>(new Set())
const latencyResults = ref<LogParseResultModel[]>([])
const latencyMetricsByPercentile = reactive<Record<LatencyPercentileValue, LatencyMetricItem[]>>({
  p99: [],
  p9999: [],
})
const isLatencyResultsLoading = ref(false)
const isLatencyChartLoading = ref(false)
const latencyChartError = ref('')
const aggregatedEvents = ref<AggregatedEventModel[]>([])
const isLatencyDetailLoading = ref(false)
const latencyDetailError = ref('')
const aggregateEventPage = ref(1)
const aggregateEventTotal = ref(0)
const selectedLatencyPercentile = ref<LatencyPercentileValue>('p99')
const selectedLatencyStat = ref<'total' | 'p99' | 'p95' | 'ave' | 'min' | 'max'>('p99')

// 聚合事件列表排序状态
const aggregateEventSort = useTableSort(
  [{ field: 'total_latency', order: 'desc' }],
  () => {
    // 排序变化时重新加载数据（重置到第一页）
    aggregateEventPage.value = 1
    void loadLatencyDetail(1)
  }
)

// 异常Trace列表排序状态
const abnormalTraceSort = useTableSort(
  [{ field: 'total_latency', order: 'desc' }],
  () => {
    // 排序变化时重新加载数据（重置到第一页）
    abnormalTracesPage.value = 1
    void loadAbnormalTraces(1)
  }
)

// 聚合事件详情表格排序状态
const detailParseResultSort = useTableSort(
  [{ field: 'total_latency', order: 'desc' }],
  () => {
    // 排序变化时重新加载数据（重置到第一页）
    if (selectedAggregatedEvent.value) {
      detailParseResultsPage.value = 1
      void loadDetailParseResults(selectedAggregatedEvent.value, 1)
    }
  }
)

// 故障聚合事件列表排序状态
const faultAggregatedEventSort = useTableSort(
  [{ field: 'all', order: 'desc' }],
  () => {
    faultAggregatedEventPage.value = 1
    void loadFaultAggregatedEvents(1)
  },
)
const faultAggregatedEventPodSort = useTableSort([{ field: 'all', order: 'desc' }])

const selectedAggregatedEvent = ref<LatencyDetailRow | null>(null)
const activeAggregateTab = ref<'event' | 'trace'>('event')
const activeFaultMonitorTab = ref<'event' | 'trace'>('event')
const selectedFaultAggregateInterval = ref<FaultAggregateInterval>('minute')
const abnormalTraceRows = ref<AbnormalTraceRow[]>([])
const isAbnormalTracesLoading = ref(false)
const abnormalTracesError = ref('')
const abnormalTracesPage = ref(1)
const abnormalTracesTotal = ref(0)
const faultAggregatedEventPage = ref(1)
const faultAggregatedEventTotal = ref(0)
const isFaultAggregatedEventsLoading = ref(false)
const faultAggregatedEventsError = ref('')
const expandedFaultAggregatedEventId = ref('')
const faultTraceEventsPage = ref(1)
const faultTraceEventsTotal = ref(0)
const detailLatencyMetrics = ref<LatencyMetricItem[]>([])
const isDetailLatencyChartLoading = ref(false)
const detailLatencyChartError = ref('')
const detailParseResults = ref<LogParseResultModel[]>([])
const isDetailParseResultsLoading = ref(false)
const detailParseResultsError = ref('')
const detailParseResultsPage = ref(1)
const detailParseResultsTotal = ref(0)
const faultDetailTraceRows = ref<FaultTraceTableRow[]>([])
const isFaultDetailTraceEventsLoading = ref(false)
const faultDetailTraceEventsError = ref('')
const faultDetailTraceEventsPage = ref(1)
const faultDetailTraceEventsTotal = ref(0)
const assetPageInput = ref('')
const logFilesPageInput = ref('')
const aggregateEventPageInput = ref('')
const abnormalTracesPageInput = ref('')
const faultAggregatedEventPageInput = ref('')
const faultTraceEventsPageInput = ref('')
const detailParseResultsPageInput = ref('')
const faultDetailTraceEventsPageInput = ref('')
const latencyChartRef = ref<HTMLDivElement | null>(null)
const detailLatencyChartRef = ref<HTMLDivElement | null>(null)
const faultChartRef = ref<HTMLDivElement | null>(null)
const faultDetailChartRef = ref<HTMLDivElement | null>(null)
const logFilesPollingTimer = ref<ReturnType<typeof window.setInterval> | null>(null)
const anomalousEventChains = ref<AnomalousEventChainModel[]>([])
const isFaultChartLoading = ref(false)
const faultChartError = ref('')
const faultChartMetrics = ref<Record<string, ErrCodeMetricItem[]>>({})
const isFaultDetailChartLoading = ref(false)
const faultDetailChartError = ref('')
const faultDetailChartMetrics = ref<Record<string, ErrCodeMetricItem[]>>({})
const faultTraceRows = ref<FaultTraceTableRow[]>([])
const faultAggregatedEventCodes = ref<string[]>([])
const faultAggregatedEventRows = ref<FaultAggregatedEventRow[]>([])
const faultAggregatedEventPodRowsByEventId = ref<Record<string, FaultAggregatedEventPodRow[]>>({})
const faultAggregatedEventPodTotalsByEventId = ref<Record<string, number>>({})
const faultAggregatedEventPodPagesByEventId = ref<Record<string, number>>({})
const faultAggregatedEventPodPageInputsByEventId = ref<Record<string, string>>({})
const loadingFaultAggregatedEventPodIds = ref<Set<string>>(new Set())
const faultAggregatedEventPodErrors = ref<Record<string, string>>({})
const isFaultTraceEventsLoading = ref(false)
const faultTraceEventsError = ref('')
const failureModeDetailsById = ref<Record<string, FailureModeKnowledgeModel | null>>({})
const selectedTrace = ref<TraceDetailRow | null>(null)
const selectedFaultTrace = ref<TraceDetailRow | null>(null)
const selectedFaultAggregatedEventDetail = ref<FaultAggregatedEventDetail | null>(null)
const selectedFaultTraceFailureModeId = ref('')
const selectedChildFailureModeId = ref('')
const traceFailureLogsByTrace = ref<Record<string, TraceLogRow[]>>({})
const traceFailureEventsByTrace = ref<Record<string, LogFailureEventResultModel[]>>({})
const isTraceLogsLoading = ref(false)
const traceLogsError = ref('')
const latencyChartRange = ref<LatencyChartRange | null>(null)
const faultChartRange = ref<LatencyChartRange | null>(null)
type GlobalFilterState = {
  startTime: string
  endTime: string
  clusters: string[]
  hosts: string[]
  sourceHosts: string[]
  targetHosts: string[]
  faultCodes: string[]
  traceBoards: string[]
}

const createEmptyFilters = (): GlobalFilterState => ({
  startTime: '',
  endTime: '',
  clusters: [],
  hosts: [],
  sourceHosts: [],
  targetHosts: [],
  faultCodes: [],
  traceBoards: [],
})

const filterDraftInput = reactive({
  cluster: '',
  host: '',
  sourceHost: '',
  targetHost: '',
  faultCode: '',
})
const globalFilters = reactive<GlobalFilterState>(createEmptyFilters())
const appliedFilters = ref<GlobalFilterState>(createEmptyFilters())
const filterApplyMessage = ref('')
const traceFilterDialog = reactive({
  open: false,
  trace: null as TraceFilterTarget | null,
  addCluster: false,
  addHost: false,
  addTraceBoard: false,
  addFaultCode: false,
})

const abnormalTraceFilterDialog = reactive({
  open: false,
  clusters: [] as string[],
  hosts: [] as string[],
  selectedClusterName: '',
  selectedHost: '',
  isLoading: false,
  error: '',
})

const latencyHostFilterDialog = reactive({
  open: false,
  row: null as LatencyDetailRow | FaultDetailRow | null,
  addSourceHost: false,
  addTargetHost: false,
})

const timePointDialog = reactive({
  open: false,
  bucket: null as Pick<LatencyChartBucket, 'time' | 'label'> | null,
  source: 'latency' as 'latency' | 'fault',
  customBefore: '10',
  customAfter: '10',
  error: '',
})

const dialog = reactive({
  open: false,
  mode: 'create' as 'create' | 'edit',
  name: '',
  description: '',
  error: '',
})

const queryDialog = reactive({
  open: false,
  name: '',
  description: '',
  createdAtStart: '',
  createdAtEnd: '',
  sortOrder: 'desc' as 'desc' | 'asc',
  error: '',
})

const resultsDialog = reactive({
  open: false,
  assets: [] as LogKnowledge[],
})

const dialogTitle = computed(() => (dialog.mode === 'create' ? '添加资产库' : '编辑资产库'))
const assetPageCount = computed(() => Math.max(1, Math.ceil(assetTotal.value / assetPageSize)))
const logFilesPageCount = computed(() =>
  Math.max(1, Math.ceil(logFilesTotal.value / logFilesPageSize)),
)
const aggregateEventPageCount = computed(() =>
  Math.max(1, Math.ceil(aggregateEventTotal.value / 10)),
)
const abnormalTracesPageCount = computed(() =>
  Math.max(1, Math.ceil(abnormalTracesTotal.value / abnormalTracesPageSize)),
)
const faultAggregatedEventPageCount = computed(() =>
  Math.max(1, Math.ceil(faultAggregatedEventTotal.value / faultAggregatedEventPageSize)),
)
const faultTraceEventsPageCount = computed(() =>
  Math.max(1, Math.ceil(faultTraceEventsTotal.value / faultTraceEventsPageSize)),
)
const getPageWindow = (currentPage: number, pageCount: number) => {
  const start = Math.max(1, currentPage - 5)
  const end = Math.min(pageCount, currentPage + 5)
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
}
const assetPageWindow = computed(() => getPageWindow(assetPage.value, assetPageCount.value))
const logFilesPageWindow = computed(() =>
  getPageWindow(logFilesPage.value, logFilesPageCount.value),
)
const aggregateEventPageWindow = computed(() =>
  getPageWindow(aggregateEventPage.value, aggregateEventPageCount.value),
)
const abnormalTracesPageWindow = computed(() =>
  getPageWindow(abnormalTracesPage.value, abnormalTracesPageCount.value),
)
const faultAggregatedEventPageWindow = computed(() =>
  getPageWindow(faultAggregatedEventPage.value, faultAggregatedEventPageCount.value),
)
const faultTraceEventsPageWindow = computed(() =>
  getPageWindow(faultTraceEventsPage.value, faultTraceEventsPageCount.value),
)
const isAbnormalMonitorPage = computed(() => activePage.value === 'abnormal')
const isLatencyTraceListFilterMode = computed(
  () => isAbnormalMonitorPage.value && activeAggregateTab.value === 'trace',
)
const isLatencyEventListFilterMode = computed(
  () => isAbnormalMonitorPage.value && activeAggregateTab.value === 'event',
)
const shouldShowTraceListFilters = computed(
  () => activePage.value === 'asset' || isAbnormalMonitorPage.value,
)
const shouldShowFaultCodeFilter = computed(
  () => isFaultCodeFeatureEnabled && isAbnormalMonitorPage.value,
)
const latencySeriesConfig = [
  {
    key: 'total_latency',
    label: '总时延',
    color: '#5470c6',
  },
  {
    key: 'worker_query_meta_latency',
    label: '查询元数据时延',
    color: '#91cc75',
  },
  {
    key: 'urma_total_latency',
    label: 'URMA总时延',
    color: '#fac858',
  },
  {
    key: 'sdk_process',
    label: 'SDK处理时延',
    color: '#ee6666',
  },
  {
    key: 'sdk_rpc',
    label: 'SDK RPC时延',
    color: '#73c0de',
  },
  {
    key: 'local_worker_cost',
    label: '本地Worker处理时延',
    color: '#3ba272',
  },
  {
    key: 'local_worker_lock',
    label: '本地Worker锁时延',
    color: '#fc8452',
  },
  {
    key: 'remote_worker_cost',
    label: '远程Worker处理时延',
    color: '#9a60b4',
  },
  {
    key: 'remote_worker_rpc',
    label: '远程Worker RPC时延',
    color: '#ea7ccc',
  },
  {
    key: 'master_process',
    label: 'Master处理时延',
    color: '#48b8d0',
  },
  {
    key: 'master_rpc_total',
    label: 'Master RPC总时延',
    color: '#7b9ce1',
  },
] as const

type LatencyMetricKey = (typeof latencySeriesConfig)[number]['key']

const defaultVisibleLatencyKeys = new Set<LatencyMetricKey>([
  'total_latency',
  'worker_query_meta_latency',
  'urma_total_latency',
])
const visibleLatencyKeys = ref<Set<LatencyMetricKey>>(new Set(defaultVisibleLatencyKeys))

const toggleLatencySeriesVisibility = (key: LatencyMetricKey) => {
  const next = new Set(visibleLatencyKeys.value)
  if (next.has(key)) {
    if (next.size > 1) {
      next.delete(key)
    }
  } else {
    next.add(key)
  }
  visibleLatencyKeys.value = next
}

const isLatencySeriesVisible = (key: LatencyMetricKey) => visibleLatencyKeys.value.has(key)

const selectAllLatencySeries = () => {
  visibleLatencyKeys.value = new Set(latencySeriesConfig.map((s) => s.key))
}

const deselectAllLatencySeries = () => {
  visibleLatencyKeys.value = new Set<LatencyMetricKey>([latencySeriesConfig[0].key])
}

const latencyPercentileOptions = [
  { value: 'p99', label: 'P99', abnormalThreshold: 2 },
  { value: 'p9999', label: 'P9999', abnormalThreshold: 5 },
] as const

const latencySampleModeMap = {
  p99: 'p99',
  p9999: 'p9999',
} as const

const latencyMetrics = computed(() => latencyMetricsByPercentile[selectedLatencyPercentile.value])

const selectedLatencyPercentileConfig = computed(
  () =>
    latencyPercentileOptions.find((option) => option.value === selectedLatencyPercentile.value) ??
    latencyPercentileOptions[0],
)

const latencyAnomalyHint = computed(
  () =>
    `🔴 红色区域 = ${selectedLatencyPercentileConfig.value.label} 总时延 > ${selectedLatencyPercentileConfig.value.abnormalThreshold}ms`,
)

const detailLatencyAbnormalThreshold = 2

const isLatencyChartBucketAbnormal = (values: Record<LatencyMetricKey, number | null>) => {
  const totalLatency = values.total_latency
  return (
    typeof totalLatency === 'number' &&
    Number.isFinite(totalLatency) &&
    totalLatency > selectedLatencyPercentileConfig.value.abnormalThreshold
  )
}

const isDetailLatencyChartBucketAbnormal = (values: Record<LatencyMetricKey, number | null>) => {
  const totalLatency = values.total_latency
  return (
    typeof totalLatency === 'number' &&
    Number.isFinite(totalLatency) &&
    totalLatency > detailLatencyAbnormalThreshold
  )
}

const isDetailP99LatencyAbnormal = (value?: number | null) =>
  typeof value === 'number' && Number.isFinite(value) && value > detailLatencyAbnormalThreshold

const latencyStatOptions = [
  { value: 'total', label: '总延迟' },
  { value: 'p99', label: 'P99' },
  { value: 'p95', label: 'P95' },
  { value: 'ave', label: '平均延迟' },
  { value: 'min', label: '最小延迟' },
  { value: 'max', label: '最大延迟' },
] as const

type LatencyStatValue = (typeof latencyStatOptions)[number]['value']

const aggregatedLatencyColumns = [
  { key: 'total_latency', label: '总时延 (ms)', threshold: 150 },
  { key: 'query_meta_latency', label: '查询元数据时延 (ms)', threshold: 150 },
  { key: 'urma_total_latency', label: 'URMA总时延 (ms)', threshold: 150 },
  { key: 'urma_link_latency', label: 'URMA建链时延 (ms)', threshold: 150 },
  { key: 'c2w_urma_latency', label: 'C2W URMA时延 (ms)', threshold: 100 },
  { key: 'w2w_urma_latency', label: 'W2W URMA时延 (ms)', threshold: 100 },
] as const

type AggregatedLatencyKey = (typeof aggregatedLatencyColumns)[number]['key']

type ProblemLogLatencyKey =
  | 'totalLatency'
  | 'queryMetaLatency'
  | 'urmaTotalLatency'
  | 'urmaLinkLatency'
  | 'c2wUrmaLatency'
  | 'w2wUrmaLatency'

const problemLogLatencyColumns = [
  { key: 'totalLatency', label: '总时延 (ms)', metric: 'total_latency' },
  { key: 'queryMetaLatency', label: '查询元数据时延 (ms)', metric: 'query_meta_latency' },
  { key: 'urmaTotalLatency', label: 'URMA总时延 (ms)', metric: 'urma_total_latency' },
  { key: 'urmaLinkLatency', label: 'URMA建链时延 (ms)', metric: 'urma_link_latency' },
  { key: 'c2wUrmaLatency', label: 'C2W URMA时延 (ms)', metric: 'c2w_urma_latency' },
  { key: 'w2wUrmaLatency', label: 'W2W URMA时延 (ms)', metric: 'w2w_urma_latency' },
] as const satisfies readonly {
  key: ProblemLogLatencyKey
  label: string
  metric: AggregatedLatencyKey
}[]

type ProblemLogLatencyColumn = (typeof problemLogLatencyColumns)[number]

type TraceDelayKey =
  | 'sdkMs'
  | 'reqDelay'
  | 'respDelay'
  | 'urmaLinkLatency'
  | 'c2wUrmaLatency'
  | 'w2wUrmaLatency'
  | 'sdkProcess'
  | 'sdkRpc'
  | 'localWorkerCost'
  | 'localWorkerLock'
  | 'remoteWorkerCost'
  | 'remoteWorkerRpc'
  | 'masterProcess'
  | 'masterRpcTotal'

const traceDelayColumns = [
  { key: 'sdkMs', label: '总时延 (ms)', metric: 'total_latency', threshold: 150, unit: 'ms' },
  {
    key: 'reqDelay',
    label: '查询元数据时延 (ms)',
    metric: 'query_meta_latency',
    threshold: 150,
    unit: 'ms',
  },
  {
    key: 'respDelay',
    label: 'URMA总时延 (ms)',
    metric: 'urma_total_latency',
    threshold: 150,
    unit: 'ms',
  },
  {
    key: 'urmaLinkLatency',
    label: 'URMA建链时延 (ms)',
    metric: 'urma_link_latency',
    threshold: 150,
    unit: 'ms',
  },
  {
    key: 'c2wUrmaLatency',
    label: 'C2W URMA时延 (ms)',
    metric: 'c2w_urma_latency',
    threshold: 100,
    unit: 'ms',
  },
  {
    key: 'w2wUrmaLatency',
    label: 'W2W URMA时延 (ms)',
    metric: 'w2w_urma_latency',
    threshold: 100,
    unit: 'ms',
  },
  { key: 'sdkProcess', label: 'SDK处理时延 (ms)', threshold: 150, unit: 'ms' },
  { key: 'sdkRpc', label: 'SDK RPC时延 (ms)', threshold: 150, unit: 'ms' },
  { key: 'localWorkerCost', label: '本地Worker处理时延 (ms)', threshold: 150, unit: 'ms' },
  { key: 'localWorkerLock', label: '本地Worker锁时延 (ms)', threshold: 150, unit: 'ms' },
  { key: 'remoteWorkerCost', label: '远端Worker处理时延 (ms)', threshold: 150, unit: 'ms' },
  { key: 'remoteWorkerRpc', label: '远端Worker RPC时延 (ms)', threshold: 150, unit: 'ms' },
  { key: 'masterProcess', label: 'Master处理时延 (ms)', threshold: 150, unit: 'ms' },
  { key: 'masterRpcTotal', label: 'Master RPC总时延 (us)', threshold: 150000, unit: 'us' },
] as const satisfies readonly {
  key: TraceDelayKey
  label: string
  metric?: AggregatedLatencyKey
  threshold: number
  unit: 'ms' | 'us'
}[]

type TraceDelayColumn = (typeof traceDelayColumns)[number]

type LatencyChartBucket = {
  time: number
  label: string
  values: Record<LatencyMetricKey, number | null>
  abnormal: boolean
}

type FaultChartBucket = {
  time: number
  label: string
  counts: Record<string, number>
}

const chartWidth = 1200
const chartHeight = 360
const chartPadding = {
  top: 34,
  right: 54,
  bottom: 66,
  left: 72,
}

const maxBucketMetricValue = (values: number[]) => {
  if (values.length === 0) return null
  return Math.max(...values)
}

const createEmptyLatencyMetricBuckets = (): Record<LatencyMetricKey, number[]> =>
  latencySeriesConfig.reduce(
    (acc, series) => {
      acc[series.key] = []
      return acc
    },
    {} as Record<LatencyMetricKey, number[]>,
  )

const parseMetricDate = (result: {
  time?: string | null
  timestamp?: string | null
  created_at?: string | null
}) => {
  const raw = result.time || result.timestamp || result.created_at
  if (!raw) return null
  const parsed = new Date(raw.replace(' ', 'T'))
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

const formatTimeLabel = (date: Date) =>
  date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })

const padDatePart = (value: number) => String(value).padStart(2, '0')

const formatFullTimeLabel = (date: Date) =>
  [
    `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`,
    `${padDatePart(date.getHours())}:${padDatePart(date.getMinutes())}:${padDatePart(date.getSeconds())}`,
  ].join(' ')

const formatMetricValue = (value?: number | null) =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : '-'

const formatNullableMetricValue = (value?: number | null) =>
  value === null ? 'null' : formatMetricValue(value)

const formatTraceDelayColumnValue = (
  value: number | null | undefined,
  column: TraceDelayColumn,
) => (typeof value === 'number' && Number.isFinite(value) ? `${formatMetricValue(value)} ${column.unit}` : '未解析')

const getAggregatedLatencyValue = (
  row: LatencyDetailRow,
  metric: AggregatedLatencyKey,
  stat: LatencyStatValue = selectedLatencyStat.value,
) => {
  const record = row.event as Record<string, unknown>
  const keys = stat === 'total' ? [metric, `p99_${metric}`] : [`${stat}_${metric}`]

  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
  }

  return null
}

const isLatencyMetricAbnormal = (metric: AggregatedLatencyKey, value?: number | null) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return false
  const column = aggregatedLatencyColumns.find((item) => item.key === metric)
  return value > (column?.threshold ?? 150)
}

const anomalyListLatencyThresholds = {
  total_latency: 2,
  query_meta_latency: 1,
  urma_total_latency: 1,
  urma_link_latency: 1,
  c2w_urma_latency: 1,
  w2w_urma_latency: 1,
} satisfies Record<AggregatedLatencyKey, number>

const getProblemLogLatencyValue = (
  row: AbnormalTraceRow | ParseResultTableRow,
  column: ProblemLogLatencyColumn,
) => row[column.key]

const isBackendLatencyAnomalyRow = (row: { raw: LogParseResultModel }) =>
  row.raw.is_anomalous === true || row.raw.is_anomalous === 1 || Boolean(row.raw.anomalous_event_id)

const isAnomalyListLatencyMetricAbnormal = (
  row: { raw: LogParseResultModel },
  metric: AggregatedLatencyKey,
  value?: number | null,
) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return false
  if (metric === 'total_latency' && isBackendLatencyAnomalyRow(row)) return true
  return value > anomalyListLatencyThresholds[metric]
}

const getTraceDelayValue = (trace: TraceDetailRow | null | undefined, column: TraceDelayColumn) =>
  trace ? trace[column.key] : null

const isTraceDelayAbnormal = (
  trace: TraceDetailRow | null | undefined,
  column: TraceDelayColumn,
) => {
  const value = getTraceDelayValue(trace, column)
  if (typeof value !== 'number' || !Number.isFinite(value)) return false
  if ('metric' in column && column.metric) return isLatencyMetricAbnormal(column.metric, value)
  return value > column.threshold
}

const getTraceDelayStatusLabel = (
  trace: TraceDetailRow | null | undefined,
  column: TraceDelayColumn,
) => {
  const value = getTraceDelayValue(trace, column)
  if (typeof value !== 'number' || !Number.isFinite(value)) return '未解析'
  return isTraceDelayAbnormal(trace, column) ? '异常' : '正常'
}

const getTraceDelayLabel = (column: TraceDelayColumn) =>
  column.label.replace(/\s*\((?:ms|us)\)$/, '')

const minuteMs = 60 * 1000
const latencyBucketCandidatesMs = [
  minuteMs,
  5 * minuteMs,
  10 * minuteMs,
  30 * minuteMs,
  60 * minuteMs,
  2 * 60 * minuteMs,
  3 * 60 * minuteMs,
  4 * 60 * minuteMs,
  6 * 60 * minuteMs,
  12 * 60 * minuteMs,
  24 * 60 * minuteMs,
]

const getAdaptiveLatencyBucketMs = (times: number[]) => {
  if (times.length <= 1) return minuteMs

  const minTime = Math.min(...times)
  const maxTime = Math.max(...times)
  const timeSpan = Math.max(maxTime - minTime, minuteMs)
  const targetBucketCount = Math.max(4, Math.floor(chartPlotWidth.value / 48))

  return (
    latencyBucketCandidatesMs.find(
      (candidate) => Math.ceil(timeSpan / candidate) <= targetBucketCount,
    ) ?? latencyBucketCandidatesMs[latencyBucketCandidatesMs.length - 1]!
  )
}

const latencyChartBuckets = computed<LatencyChartBucket[]>(() => {
  const chartRange = latencyChartRange.value
  const allMetricPoints = latencyMetrics.value
    .map((result) => ({
      result,
      date: parseMetricDate(result),
    }))
    .filter((point): point is { result: LatencyMetricItem; date: Date } => {
      return point.date !== null
    })

  if (allMetricPoints.length === 0) return []

  const allTimes = allMetricPoints.map((point) => point.date.getTime())
  const bucketMs = getAdaptiveLatencyBucketMs(allTimes)
  const minTime = chartRange?.startTime ?? Math.min(...allTimes)
  const maxTime = chartRange?.endTime ?? Math.max(...allTimes)
  const firstBucketStart = Math.floor(minTime / bucketMs) * bucketMs
  const lastBucketStart = Math.floor(maxTime / bucketMs) * bucketMs
  const buckets = new Map<number, Record<LatencyMetricKey, number[]>>()

  allMetricPoints.forEach(({ result, date }) => {
    const time = date.getTime()
    if (chartRange && (time < chartRange.startTime || time > chartRange.endTime)) return

    const bucketStart = Math.floor(date.getTime() / bucketMs) * bucketMs
    const bucket = buckets.get(bucketStart) ?? createEmptyLatencyMetricBuckets()

    latencySeriesConfig.forEach((series) => {
      let value = result[series.key]
      if (typeof value === 'number' && Number.isFinite(value)) {
        if (series.key === 'master_rpc_total') {
          value = value / 1000
        }
        bucket[series.key].push(value)
      }
    })

    buckets.set(bucketStart, bucket)
  })

  const chartBuckets: LatencyChartBucket[] = []
  for (let time = firstBucketStart; time <= lastBucketStart; time += bucketMs) {
    const groupedValues = buckets.get(time) ?? createEmptyLatencyMetricBuckets()

    const values = latencySeriesConfig.reduce(
      (acc, series) => {
        acc[series.key] = maxBucketMetricValue(groupedValues[series.key])
        return acc
      },
      {} as Record<LatencyMetricKey, number | null>,
    )

    chartBuckets.push({
      time,
      label: formatFullTimeLabel(new Date(time)),
      values,
      abnormal: isLatencyChartBucketAbnormal(values),
    })
  }

  return chartBuckets
})

const chartPlotWidth = computed(() => chartWidth - chartPadding.left - chartPadding.right)
const chartPlotHeight = computed(() => chartHeight - chartPadding.top - chartPadding.bottom)

const getSmoothChartPath = (points: { x: number; y: number }[]) => {
  if (points.length === 0) return ''
  if (points.length === 1) return `M ${points[0]!.x.toFixed(1)},${points[0]!.y.toFixed(1)}`

  const clampControlY = (value: number, firstY: number, secondY: number) =>
    Math.min(Math.max(value, Math.min(firstY, secondY)), Math.max(firstY, secondY))

  const commands = [`M ${points[0]!.x.toFixed(1)},${points[0]!.y.toFixed(1)}`]
  for (let index = 0; index < points.length - 1; index += 1) {
    const previousPoint = points[index - 1] ?? points[index]!
    const currentPoint = points[index]!
    const nextPoint = points[index + 1]!
    const nextNextPoint = points[index + 2] ?? nextPoint
    const controlPointOne = {
      x: currentPoint.x + (nextPoint.x - previousPoint.x) / 6,
      y: clampControlY(
        currentPoint.y + (nextPoint.y - previousPoint.y) / 6,
        currentPoint.y,
        nextPoint.y,
      ),
    }
    const controlPointTwo = {
      x: nextPoint.x - (nextNextPoint.x - currentPoint.x) / 6,
      y: clampControlY(
        nextPoint.y - (nextNextPoint.y - currentPoint.y) / 6,
        currentPoint.y,
        nextPoint.y,
      ),
    }

    commands.push(
      `C ${controlPointOne.x.toFixed(1)},${controlPointOne.y.toFixed(1)} ${controlPointTwo.x.toFixed(1)},${controlPointTwo.y.toFixed(1)} ${nextPoint.x.toFixed(1)},${nextPoint.y.toFixed(1)}`,
    )
  }

  return commands.join(' ')
}

const getEndpointSmoothChartPath = (points: { x: number; y: number }[]) => {
  if (points.length === 0) return ''
  if (points.length === 1) return `M ${points[0]!.x.toFixed(1)},${points[0]!.y.toFixed(1)}`

  const commands = [`M ${points[0]!.x.toFixed(1)},${points[0]!.y.toFixed(1)}`]
  for (let index = 0; index < points.length - 1; index += 1) {
    const currentPoint = points[index]!
    const nextPoint = points[index + 1]!
    const controlOffset = (nextPoint.x - currentPoint.x) * 0.35

    commands.push(
      `C ${(currentPoint.x + controlOffset).toFixed(1)},${currentPoint.y.toFixed(1)} ${(nextPoint.x - controlOffset).toFixed(1)},${nextPoint.y.toFixed(1)} ${nextPoint.x.toFixed(1)},${nextPoint.y.toFixed(1)}`,
    )
  }

  return commands.join(' ')
}

type LatencySeriesPoint = {
  key: string
  seriesKey: LatencyMetricKey
  seriesLabel: string
  color: string
  bucket: LatencyChartBucket
  value: number
  x: number
  y: number
}

const detailLatencyChartBuckets = computed<LatencyChartBucket[]>(() =>
  detailLatencyMetrics.value
    .map((metric) => {
      const date = parseMetricDate(metric)
      if (!date) return null

      const values = latencySeriesConfig.reduce(
        (acc, series) => {
          let value = metric[series.key]
          if (typeof value === 'number' && Number.isFinite(value)) {
            if (series.key === 'master_rpc_total') {
              value = value / 1000
            }
            acc[series.key] = value
          } else {
            acc[series.key] = null
          }
          return acc
        },
        {} as Record<LatencyMetricKey, number | null>,
      )

      return {
        time: date.getTime(),
        label: formatFullTimeLabel(date),
        values,
        abnormal: isDetailLatencyChartBucketAbnormal(values),
      }
    })
    .filter((bucket): bucket is LatencyChartBucket => bucket !== null)
    .sort((first, second) => first.time - second.time),
)

const detailLatencyChartMax = computed(() => {
  const values = detailLatencyChartBuckets.value.flatMap((bucket) =>
    latencySeriesConfig
      .map((series) => bucket.values[series.key])
      .filter((value): value is number => typeof value === 'number'),
  )
  const maxValue = Math.max(0, ...values, 150)
  return Math.ceil((maxValue * 1.15) / 50) * 50
})

const getDetailChartBandWidth = (bucketCount: number) =>
  bucketCount > 0 ? chartPlotWidth.value / bucketCount : chartPlotWidth.value

const getDetailChartX = (index: number) => {
  const bandWidth = getDetailChartBandWidth(detailLatencyChartBuckets.value.length)
  return chartPadding.left + bandWidth * (index + 0.5)
}

const getDetailChartBoundaryX = (index: number) => {
  const bandWidth = getDetailChartBandWidth(detailLatencyChartBuckets.value.length)
  return chartPadding.left + bandWidth * index
}

const getDetailChartY = (value: number) =>
  chartPadding.top +
  chartPlotHeight.value -
  (value / detailLatencyChartMax.value) * chartPlotHeight.value

const detailLatencySeriesPaths = computed(() =>
  latencySeriesConfig.map((series) => {
    const points = detailLatencyChartBuckets.value
      .map((bucket, index) => {
        const value = bucket.values[series.key]
        if (typeof value !== 'number') return null
        return {
          x: getDetailChartX(index),
          y: getDetailChartY(value),
        }
      })
      .filter((point): point is { x: number; y: number } => point !== null)

    return {
      ...series,
      path: getSmoothChartPath(points),
    }
  }),
)

const detailLatencySeriesPoints = computed<LatencySeriesPoint[]>(() => {
  const points: LatencySeriesPoint[] = []

  latencySeriesConfig.forEach((series) => {
    detailLatencyChartBuckets.value.forEach((bucket, index) => {
      const value = bucket.values[series.key]
      if (typeof value !== 'number') return
      points.push({
        key: `detail-${series.key}-${bucket.time}`,
        seriesKey: series.key,
        seriesLabel: series.label,
        color: series.color,
        bucket,
        value,
        x: getDetailChartX(index),
        y: getDetailChartY(value),
      })
    })
  })

  return points
})

const detailYAxisTicks = computed(() => {
  const ticks = []
  for (let value = 0; value <= detailLatencyChartMax.value; value += 50) {
    ticks.push({
      value,
      y: getDetailChartY(value),
    })
  }
  return ticks
})

const detailXAxisLabels = computed(() => {
  const buckets = detailLatencyChartBuckets.value
  const step = buckets.length <= 8 ? 1 : Math.ceil(buckets.length / 8)

  return buckets
    .map((bucket, index) => ({
      bucket,
      index,
      x: getDetailChartX(index),
      y: chartHeight - chartPadding.bottom + 22,
    }))
    .filter(({ index }) => index === 0 || index === buckets.length - 1 || index % step === 0)
})

const detailAnomalyRegions = computed(() =>
  detailLatencyChartBuckets.value
    .map((bucket, index) => {
      if (!bucket.abnormal) return null
      const bandWidth = getDetailChartBandWidth(detailLatencyChartBuckets.value.length)
      const startX = chartPadding.left + bandWidth * index
      const endX = startX + bandWidth
      return {
        x: startX,
        width: Math.max(endX - startX, 0),
      }
    })
    .filter((region): region is { x: number; width: number } => region !== null),
)

let latencyChartInstance: ECharts | null = null
let detailLatencyChartInstance: ECharts | null = null
let faultChartInstance: ECharts | null = null
let faultDetailChartInstance: ECharts | null = null

const getLatencyMarkAreas = (buckets: LatencyChartBucket[]) => {
  const ranges: Array<[Record<string, number>, Record<string, number>]> = []
  let startIndex: number | null = null

  buckets.forEach((bucket, index) => {
    if (bucket.abnormal && startIndex === null) {
      startIndex = index
    }
    if ((!bucket.abnormal || index === buckets.length - 1) && startIndex !== null) {
      const endIndex = bucket.abnormal && index === buckets.length - 1 ? index : index - 1
      ranges.push([{ xAxis: startIndex }, { xAxis: endIndex }])
      startIndex = null
    }
  })

  return ranges
}

const createLatencyEchartsOption = (buckets: LatencyChartBucket[]): EChartsOption => {
  const labels = buckets.map((bucket) => bucket.label)
  const markAreaData = getLatencyMarkAreas(buckets)
  const xAxisLabelStep = labels.length <= 10 ? 1 : Math.ceil(labels.length / 10)
  const visibleSeries = latencySeriesConfig.filter((s) => isLatencySeriesVisible(s.key))

  return {
    color: visibleSeries.map((series) => series.color),
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) =>
        typeof value === 'number' ? `${formatMetricValue(value)} ms` : String(value ?? '-'),
    },
    legend: {
      data: visibleSeries.map((series) => series.label),
      top: 0,
      itemGap: 18,
      itemWidth: 18,
      itemHeight: 10,
      textStyle: {
        color: '#334155',
        fontSize: 12,
        fontWeight: 400,
      },
    },
    grid: {
      top: 58,
      right: 68,
      bottom: 15,
      left: 54,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: labels,
      name: '时间',
      boundaryGap: true,
      axisTick: {
        show: true,
        alignWithLabel: true,
        length: 6,
        lineStyle: {
          color: '#94a3b8',
          width: 1,
        },
      },
      axisLine: {
        lineStyle: {
          color: '#94a3b8',
        },
      },
      axisLabel: {
        interval: (index: number) =>
          labels.length <= 10 ||
          index === 0 ||
          index === labels.length - 1 ||
          index % xAxisLabelStep === 0,
        color: '#64748b',
        fontSize: 12,
        rotate: 38,
        margin: 6,
      },
      nameTextStyle: {
        color: '#475569',
        fontSize: 12,
      },
    },
    yAxis: {
      type: 'value',
      name: '延迟(ms)',
      min: 0,
      splitLine: {
        lineStyle: {
          color: '#e2e8f0',
        },
      },
      axisLabel: {
        color: '#64748b',
        fontSize: 12,
      },
      nameTextStyle: {
        color: '#475569',
        fontSize: 12,
      },
    },
    series: visibleSeries.map((series, index) => ({
      name: series.label,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 2,
      },
      data: buckets.map((bucket) => bucket.values[series.key]),
      ...(index === 0
        ? {
            markArea: {
              silent: false,
              data: markAreaData,
              itemStyle: {
                color: 'rgba(239,68,68,0.25)',
                borderColor: '#ef4444',
                borderWidth: 1,
              },
            },
          }
        : {}),
    })),
  }
}

const createDetailLatencyEchartsOption = (points: LatencyChartBucket[]): EChartsOption => {
  const labels = points.map((point) => point.label)
  const markAreaData = getLatencyMarkAreas(points)

  return {
    ...createLatencyEchartsOption(points),
    xAxis: {
      type: 'category',
      data: labels,
      name: '时间',
      boundaryGap: false,
      axisTick: {
        show: true,
        alignWithLabel: true,
        interval: 'auto',
        length: 6,
        lineStyle: {
          color: '#94a3b8',
          width: 1,
        },
      },
      axisLine: {
        lineStyle: {
          color: '#94a3b8',
        },
      },
      axisLabel: {
        interval: 'auto',
        color: '#64748b',
        fontSize: 12,
        rotate: 38,
        margin: 6,
      },
      nameTextStyle: {
        color: '#475569',
        fontSize: 12,
      },
    },
    series: latencySeriesConfig.filter((s) => isLatencySeriesVisible(s.key)).map((series, index) => ({
      name: series.label,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 2,
      },
      data: points.map((point) => point.values[series.key]),
      ...(index === 0
        ? {
            markArea: {
              silent: true,
              data: markAreaData,
              itemStyle: {
                color: 'rgba(239,68,68,0.25)',
                borderColor: '#ef4444',
                borderWidth: 1,
              },
            },
          }
        : {}),
    })),
  }
}

const createFaultEchartsOption = (
  buckets: FaultChartBucket[],
  codes = faultCodes.value,
): EChartsOption => {
  const labels = buckets.map((bucket) => bucket.label)
  const seriesNames = codes.map((code) => `故障码${code}`)

  return {
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      data: seriesNames,
      top: 0,
    },
    grid: {
      top: 58,
      right: 68,
      bottom: 15,
      left: 80,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: labels,
      name: '时间',
      axisLabel: {
        color: '#64748b',
        fontSize: 12,
        rotate: 38,
        margin: 6,
      },
    },
    yAxis: {
      type: 'value',
      name: '故障计数',
      minInterval: 1,
      axisLabel: {
        formatter: (value: number) => String(Math.trunc(value)),
      },
    },
    series: codes.map((code) => ({
      name: `故障码${code}`,
      type: 'line',
      data: buckets.map((bucket) => bucket.counts[code] ?? 0),
      smooth: true,
    })),
  }
}

const renderLatencyEchart = () => {
  if (!isAbnormalMonitorPage.value || isLatencyChartLoading.value || latencyChartError.value)
    return
  const element = latencyChartRef.value
  if (!element || latencyChartBuckets.value.length === 0) return

  if (latencyChartInstance && latencyChartInstance.getDom() !== element) {
    latencyChartInstance.dispose()
    latencyChartInstance = null
  }
  latencyChartInstance ??= echarts.init(element)
  latencyChartInstance.setOption(createLatencyEchartsOption(latencyChartBuckets.value), true)
  latencyChartInstance.off('click')
  latencyChartInstance.on('click', (params: unknown) => {
    const event = params as { componentType?: string; dataIndex?: number }
    if (event.componentType === 'series' && typeof event.dataIndex === 'number') {
      const bucket = latencyChartBuckets.value[event.dataIndex]
      if (bucket) openTimePointDialog(bucket)
    }
  })
  latencyChartInstance.resize()
}

const renderDetailLatencyEchart = () => {
  if (isDetailLatencyChartLoading.value || detailLatencyChartError.value) return
  const element = detailLatencyChartRef.value
  if (!element || detailLatencyChartBuckets.value.length === 0) return

  if (detailLatencyChartInstance && detailLatencyChartInstance.getDom() !== element) {
    detailLatencyChartInstance.dispose()
    detailLatencyChartInstance = null
  }
  detailLatencyChartInstance ??= echarts.init(element)
  detailLatencyChartInstance.setOption(
    createDetailLatencyEchartsOption(detailLatencyChartBuckets.value),
    true,
  )
  detailLatencyChartInstance.off('click')
  detailLatencyChartInstance.resize()
}

const renderFaultEchart = () => {
  if (!isAbnormalMonitorPage.value || isFaultChartLoading.value || faultChartError.value) return
  const element = faultChartRef.value
  if (!element || faultChartBuckets.value.length === 0 || faultCodes.value.length === 0) return

  if (faultChartInstance && faultChartInstance.getDom() !== element) {
    faultChartInstance.dispose()
    faultChartInstance = null
  }
  faultChartInstance ??= echarts.init(element)
  faultChartInstance.setOption(createFaultEchartsOption(faultChartBuckets.value), true)
  faultChartInstance.off('click')
  faultChartInstance.on('click', (params: unknown) => {
    const event = params as { componentType?: string; dataIndex?: number }
    if (event.componentType === 'series' && typeof event.dataIndex === 'number') {
      const bucket = faultChartBuckets.value[event.dataIndex]
      if (bucket) openTimePointDialog(bucket, 'fault')
    }
  })
  faultChartInstance.resize()
}

const renderFaultDetailEchart = () => {
  if (
    isFaultDetailChartLoading.value ||
    faultDetailChartError.value ||
    !selectedFaultAggregatedEventDetail.value
  )
    return
  const element = faultDetailChartRef.value
  const codes = selectedFaultDetailChartCodes.value
  if (!element || faultDetailChartBuckets.value.length === 0 || codes.length === 0) return

  if (faultDetailChartInstance && faultDetailChartInstance.getDom() !== element) {
    faultDetailChartInstance.dispose()
    faultDetailChartInstance = null
  }
  faultDetailChartInstance ??= echarts.init(element)
  faultDetailChartInstance.setOption(
    createFaultEchartsOption(faultDetailChartBuckets.value, codes),
    true,
  )
  faultDetailChartInstance.resize()
}

const resizeLatencyCharts = () => {
  latencyChartInstance?.resize()
  detailLatencyChartInstance?.resize()
  faultChartInstance?.resize()
  faultDetailChartInstance?.resize()
}

const openTimePointDialog = (
  bucket: Pick<LatencyChartBucket, 'time' | 'label'>,
  source: 'latency' | 'fault' = 'latency',
) => {
  timePointDialog.bucket = bucket
  timePointDialog.source = source
  timePointDialog.customBefore = '10'
  timePointDialog.customAfter = '10'
  timePointDialog.error = ''
  timePointDialog.open = true
}

const closeTimePointDialog = () => {
  timePointDialog.open = false
}

const resetLatencyChartRange = () => {
  latencyChartRange.value = null
}

const resetFaultChartRange = () => {
  faultChartRange.value = null
}

const applyTimePointRange = async (beforeMinutes: number, afterMinutes: number) => {
  const bucket = timePointDialog.bucket
  if (!bucket) return

  if (
    !Number.isFinite(beforeMinutes) ||
    !Number.isFinite(afterMinutes) ||
    beforeMinutes < 0 ||
    afterMinutes < 0
  ) {
    timePointDialog.error = '请输入有效的分钟数'
    return
  }

  const range = {
    centerTime: bucket.time,
    startTime: bucket.time - beforeMinutes * 60 * 1000,
    endTime: bucket.time + afterMinutes * 60 * 1000,
    label: bucket.label,
  }
  const targetSectionId = timePointDialog.source === 'fault' ? 'kv-fault' : 'kv-latency'

  if (timePointDialog.source === 'fault') {
    faultChartRange.value = range
  } else {
    latencyChartRange.value = range
  }
  activePage.value = 'abnormal'
  timePointDialog.open = false

  await nextTick()
  document.getElementById(targetSectionId)?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

const applyPresetTimePointRange = (minutes: 5 | 10 | 15) => {
  void applyTimePointRange(minutes, minutes)
}

const confirmCustomTimePointRange = () => {
  void applyTimePointRange(
    Number.parseInt(timePointDialog.customBefore, 10),
    Number.parseInt(timePointDialog.customAfter, 10),
  )
}

type AnomalyInfo = {
  code: string
  description: string
}

const getFaultDomainByCode = (code?: string) => {
  if (!code) return ''
  return ['1004', '1006', '1008', '1009', '1010'].includes(code) ? 'URMA' : 'KVCache'
}

const anomalyInfoByEventId = computed(() => {
  const mapping = new Map<string, AnomalyInfo>()
  anomalousEventChains.value.forEach((chain) => {
    if (!chain.anomaly_code) return
    const record = chain as Record<string, unknown>
    const anomalousEventId = getRecordString(
      record,
      ['anomalous_event_id', 'anomaly_event_id', 'event_id', 'id'],
      '',
    )
    if (anomalousEventId) {
      mapping.set(anomalousEventId, {
        code: chain.anomaly_code,
        description: getRecordString(
          record,
          ['description', 'anomaly_desc', 'anomaly_description'],
          '',
        ),
      })
    }
  })
  return mapping
})

const getLogResultAnomalyInfo = (result: LogParseResultModel) => {
  const record = result as Record<string, unknown>
  const anomalousEventId = getRecordString(record, ['anomalous_event_id', 'anomaly_event_id'], '')
  if (!anomalousEventId) return null
  return anomalyInfoByEventId.value.get(anomalousEventId) ?? null
}

const getLogResultAnomalyCode = (result: LogParseResultModel) => {
  return getLogResultAnomalyInfo(result)?.code ?? null
}

const faultCodes = computed(() =>
  Object.keys(faultChartMetrics.value).sort((a, b) => a.localeCompare(b)),
)
const faultAggregatedEventCodeColumnMaxWidth = 132
const faultAggregatedEventCodeGridStyle = computed(() => {
  const columnCount = Math.max(1, faultAggregatedEventCodes.value.length)
  const width = columnCount * faultAggregatedEventCodeColumnMaxWidth
  return {
    gridTemplateColumns: `repeat(${columnCount}, ${faultAggregatedEventCodeColumnMaxWidth}px)`,
    width: `${width}px`,
    minWidth: `${width}px`,
  }
})
const paginatedFaultAggregatedEventRows = computed(() => faultAggregatedEventRows.value)
const getFaultAggregatedEventCodeValue = (row: FaultAggregatedEventRow, code: string) =>
  row.faultCodeCounts[code] ?? 0
const getFaultAggregatedEventCodeLabel = (code: string) =>
  code === 'all' ? '故障总数' : `故障码${code}`
const getNextFaultAggregatedEventPodSortFields = (field: string): SortField[] => {
  const nextFields = faultAggregatedEventPodSort.getSortFields.value.map((sortField) => ({
    ...sortField,
  }))
  const existingIndex = nextFields.findIndex((sortField) => sortField.field === field)
  const existingField = existingIndex === -1 ? null : nextFields[existingIndex]

  if (existingIndex === -1) {
    nextFields.push({ field, order: 'desc' })
  } else if (existingField?.order === 'desc') {
    nextFields[existingIndex] = { field, order: 'asc' }
  } else {
    nextFields.splice(existingIndex, 1)
  }

  return nextFields
}
const handleFaultAggregatedEventPodSortHeaderClick = (
  row: FaultAggregatedEventRow,
  field: string,
) => {
  faultAggregatedEventPodSort.setSortFields(getNextFaultAggregatedEventPodSortFields(field))
  setFaultAggregatedEventPodPageInput(row, '')
  void loadFaultAggregatedEventPodRows(row, 1)
}
const isFaultAggregatedEventExpanded = (row: FaultAggregatedEventRow) =>
  expandedFaultAggregatedEventId.value === row.id
const getFaultAggregatedEventPodRows = (row: FaultAggregatedEventRow) =>
  faultAggregatedEventPodRowsByEventId.value[row.id] ?? []
const getFaultAggregatedEventPodCodeValue = (row: FaultAggregatedEventPodRow, code: string) =>
  row.faultCodeCounts[code] ?? 0
const isFaultAggregatedEventPodLoading = (row: FaultAggregatedEventRow) =>
  loadingFaultAggregatedEventPodIds.value.has(row.id)
const getFaultAggregatedEventPodError = (row: FaultAggregatedEventRow) =>
  faultAggregatedEventPodErrors.value[row.id] ?? ''
const getFaultAggregatedEventPodTotal = (row: FaultAggregatedEventRow) =>
  faultAggregatedEventPodTotalsByEventId.value[row.id] ?? 0
const getFaultAggregatedEventPodPage = (row: FaultAggregatedEventRow) =>
  faultAggregatedEventPodPagesByEventId.value[row.id] ?? 1
const getFaultAggregatedEventPodPageCount = (row: FaultAggregatedEventRow) =>
  Math.max(1, Math.ceil(getFaultAggregatedEventPodTotal(row) / faultAggregatedEventPodPageSize))
const getFaultAggregatedEventPodPageWindow = (row: FaultAggregatedEventRow) =>
  getPageWindow(getFaultAggregatedEventPodPage(row), getFaultAggregatedEventPodPageCount(row))
const getFaultAggregatedEventPodPageInput = (row: FaultAggregatedEventRow) =>
  faultAggregatedEventPodPageInputsByEventId.value[row.id] ?? ''
const setFaultAggregatedEventPodPageInput = (row: FaultAggregatedEventRow, value: string) => {
  faultAggregatedEventPodPageInputsByEventId.value = {
    ...faultAggregatedEventPodPageInputsByEventId.value,
    [row.id]: value,
  }
}

const selectedFaultDetailCodeCounts = computed(() => {
  const detail = selectedFaultAggregatedEventDetail.value
  if (!detail) return []

  const counts = detail.podRow.faultCodeCounts
  const total =
    counts.all ??
    Object.entries(counts).reduce((sum, [code, count]) => (code === 'all' ? sum : sum + count), 0)
  const codes = faultAggregatedEventCodes.value.filter((code) => code !== 'all')

  return [
    {
      code: 'all',
      label: '故障总数',
      count: total,
    },
    ...codes
      .map((code) => ({
        code,
        label: getFaultAggregatedEventCodeLabel(code),
        count: counts[code] ?? 0,
      }))
      .filter((item) => item.count > 0),
  ]
})
const selectedFaultDetailChartCodes = computed(() =>
  selectedFaultDetailCodeCounts.value
    .filter((item) => item.code !== 'all' && item.count > 0)
    .map((item) => item.code),
)
const faultChartBuckets = computed<FaultChartBucket[]>(() => {
  const buckets = new Map<number, Record<string, number>>()
  const chartRange = faultChartRange.value

  Object.entries(faultChartMetrics.value).forEach(([code, metrics]) => {
    metrics.forEach((metric) => {
      const parsed = parseMetricDate(metric)
      if (!parsed) return

      const time = parsed.getTime()
      if (chartRange && (time < chartRange.startTime || time > chartRange.endTime)) return

      const value = metric.err_cnt ?? metric.count ?? metric.value
      const bucket = buckets.get(time) ?? {}
      bucket[code] = typeof value === 'number' && Number.isFinite(value) ? value : 0
      buckets.set(time, bucket)
    })
  })

  const chartBuckets = [...buckets.entries()]
    .sort(([a], [b]) => a - b)
    .map(([time, counts]) => ({
      time,
      label: formatFullTimeLabel(new Date(time)),
      counts,
    }))

  return chartBuckets
})

const faultDetailChartBuckets = computed<FaultChartBucket[]>(() => {
  const buckets = new Map<number, Record<string, number>>()

  Object.entries(faultDetailChartMetrics.value).forEach(([code, metrics]) => {
    metrics.forEach((metric) => {
      const parsed = parseMetricDate(metric)
      if (!parsed) return

      const value = metric.err_cnt ?? metric.count ?? metric.value
      const time = parsed.getTime()
      const bucket = buckets.get(time) ?? {}
      bucket[code] = typeof value === 'number' && Number.isFinite(value) ? value : 0
      buckets.set(time, bucket)
    })
  })

  return [...buckets.entries()]
    .sort(([a], [b]) => a - b)
    .map(([time, counts]) => ({
      time,
      label: formatFullTimeLabel(new Date(time)),
      counts,
    }))
})

const latencyDetailRows = computed<LatencyDetailRow[]>(() => {
  const rows: LatencyDetailRow[] = []

  aggregatedEvents.value.forEach((event) => {
    rows.push({
      id: event.id,
      sourceHost: stripHostPort(event.src_ip),
      targetHost: stripHostPort(event.dst_ip),
      traceCount: event.log_parse_result_cnt ?? 0,
      anomalyTraceCount: event.anomaly_log_parse_result_cnt ?? 0,
      event,
    })
  })

  return rows
})

const getLatencyPairKey = (firstHost: string, secondHost: string) => `${firstHost}->${secondHost}`

const stripHostPort = (value?: string | null) => {
  const host = value?.trim()
  if (!host || host === '-') return '-'

  const bracketedIpv6 = host.match(/^\[([^\]]+)\](?::\d+)?$/)
  if (bracketedIpv6?.[1]) return bracketedIpv6[1]

  const hostWithPort = host.match(/^(.+):\d+$/)
  if (hostWithPort?.[1] && !hostWithPort[1].includes(':')) return hostWithPort[1]

  return host
}

const getRecordString = (record: Record<string, unknown>, keys: string[], fallback = '-') => {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value
    if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  }
  return fallback
}

const stringifyDetailValue = (value: unknown) => {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    return getRecordString(
      record,
      ['name', 'fault_name', 'failure_name', 'mode_name', 'code', 'id', 'description'],
      JSON.stringify(value),
    )
  }
  return ''
}

const getRecordStringList = (record: Record<string, unknown>, keys: string[]) => {
  for (const key of keys) {
    const value = record[key]
    if (Array.isArray(value)) {
      return value.map(stringifyDetailValue).filter(Boolean)
    }

    const text = stringifyDetailValue(value)
    if (text) return [text]
  }
  return []
}

const getFailureModeIds = (record: Record<string, unknown>) =>
  getRecordStringList(record, [
    'failure_mode_id',
    'failureModeId',
    'failure_mode_ids',
    'failureModeIds',
    'failure_mode',
    'failureMode',
    'failure_modes',
    'failureModes',
  ])
    .flatMap((value) => value.split(','))
    .map((value) => value.trim())
    .filter(Boolean)

const getRecordArray = (record: Record<string, unknown>, keys: string[]) => {
  const values = getRecordStringList(record, keys)
  return values.length > 0 ? values : ['-']
}

const getRecordNumber = (record: Record<string, unknown>, keys: string[], fallback = 0) => {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) {
      return Number(value)
    }
  }
  return fallback
}

const getRecordNullableNumber = (record: Record<string, unknown>, keys: string[]) => {
  for (const key of keys) {
    const value = record[key]
    if (value === null) return null
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) {
      return Number(value)
    }
  }
  return null
}

const latencyMetricRecordKeys: Record<AggregatedLatencyKey, string[]> = {
  total_latency: ['total_latency'],
  query_meta_latency: ['query_meta_latency', 'worker_query_meta_latency'],
  urma_total_latency: ['urma_total_latency'],
  urma_link_latency: ['urma_link_latency'],
  c2w_urma_latency: ['c2w_urma_latency'],
  w2w_urma_latency: ['w2w_urma_latency'],
}

const getLogFailureReason = (record: Record<string, unknown>) => {
  const remark = getRecordString(record, ['remark'], '').trim()
  if (remark && remark.toUpperCase() !== 'OK') return remark

  const anomalyReason = getRecordString(record, ['anomaly_reason'], '').trim()
  if (anomalyReason && !anomalyReason.toLowerCase().includes('threshold')) return anomalyReason

  const level = getRecordString(record, ['log_level', 'level'], '').toUpperCase()
  if (level === 'ERROR') {
    return getRecordString(record, ['message', 'msg', 'content'], 'ERROR')
  }

  return ''
}

const getSevereTimeoutMetric = (record: Record<string, unknown>) => {
  const candidates: Array<{ key: AggregatedLatencyKey; label: string; value: number }> = []

  aggregatedLatencyColumns.forEach((column) => {
    const value = getRecordNullableNumber(record, latencyMetricRecordKeys[column.key])
    if (
      typeof value === 'number' &&
      Number.isFinite(value) &&
      isLatencyMetricAbnormal(column.key, value)
    ) {
      candidates.push({
        key: column.key,
        label: column.label,
        value,
      })
    }
  })

  candidates.sort((first, second) => second.value - first.value)

  return candidates[0] ?? null
}

const getLogDisplayStatus = (record: Record<string, unknown>): LogDisplayStatus => {
  if (getLogFailureReason(record)) return 'failed'
  if (getSevereTimeoutMetric(record)) return 'timeout'
  return 'normal'
}

const getLogDisplayReason = (record: Record<string, unknown>) => {
  const failureReason = getLogFailureReason(record)
  if (failureReason) return failureReason

  const timeoutMetric = getSevereTimeoutMetric(record)
  if (timeoutMetric) {
    return `${timeoutMetric.label} ${formatMetricValue(timeoutMetric.value)} ms`
  }

  return 'OK'
}

const getLogStatusLabel = (status: LogDisplayStatus) => {
  const labels: Record<LogDisplayStatus, string> = {
    failed: '失败',
    timeout: '严重超时',
    normal: '正常',
  }
  return labels[status]
}

const normalizeTraceOperation = (operation: string) => {
  const normalized = operation.trim().toUpperCase()
  if (normalized.includes('GET')) return 'GET'
  if (normalized.includes('SET')) return 'SET'
  return '-'
}

const normalizeTimeText = (value: string) => value.replace('T', ' ').replace(/Z$/, '')

const getLogResultTrace = (result: LogParseResultModel): TraceDetailRow => {
  const record = result as Record<string, unknown>
  return {
    traceId: getRecordString(record, ['trace_id', 'traceId', 'span_id', 'id']),
    clusterName: getRecordString(record, ['cluster_name', 'clusterName', 'cluster'], ''),
    host: getRecordString(record, ['host'], ''),
    podIp: getRecordString(record, ['pod_ip', 'pod_id', 'pod_name', 'podId', 'pod']),
    time: normalizeTimeText(getRecordString(record, ['timestamp', 'created_at', 'time'], '')),
    sdkMs: getRecordNullableNumber(record, ['total_latency', 'sdk_ms', 'sdkMs', 'latency']),
    reqDelay: getRecordNullableNumber(record, [
      'worker_query_meta_latency',
      'query_meta_latency',
      'req_delay',
      'reqDelay',
    ]),
    respDelay: getRecordNullableNumber(record, [
      'urma_total_latency',
      'rsp_delay',
      'respDelay',
      'rspDelay',
    ]),
    urmaLinkLatency: getRecordNullableNumber(record, ['urma_link_latency']),
    c2wUrmaLatency: getRecordNullableNumber(record, ['c2w_urma_latency']),
    w2wUrmaLatency: getRecordNullableNumber(record, ['w2w_urma_latency']),
    sdkProcess: getRecordNullableNumber(record, ['sdk_process']),
    sdkRpc: getRecordNullableNumber(record, ['sdk_rpc']),
    localWorkerCost: getRecordNullableNumber(record, ['local_worker_cost']),
    localWorkerLock: getRecordNullableNumber(record, ['local_worker_lock']),
    remoteWorkerCost: getRecordNullableNumber(record, ['remote_worker_cost']),
    remoteWorkerRpc: getRecordNullableNumber(record, ['remote_worker_rpc']),
    masterProcess: getRecordNullableNumber(record, ['master_process']),
    masterRpcTotal: getRecordNullableNumber(record, ['master_rpc_total']),
  }
}

const detailParseResultRows = computed<ParseResultTableRow[]>(() =>
  detailParseResults.value
    .map((result) => {
      const record = result as Record<string, unknown>
      return {
        id: getRecordString(record, ['id', 'trace_id', 'traceId']),
        logStatus: getLogDisplayStatus(record),
        statusReason: getLogDisplayReason(record),
        time: normalizeTimeText(getRecordString(record, ['timestamp', 'created_at', 'time'], '')),
        traceId: getRecordString(record, ['trace_id', 'traceId', 'span_id', 'id']),
        podIp: getRecordString(record, ['pod_ip', 'pod_id', 'pod_name', 'podId', 'pod']),
        operation: normalizeTraceOperation(
          getRecordString(record, ['operation', 'op_type', 'operation_type', 'method']),
        ),
        clusterName: getRecordString(record, ['cluster_name'], 'null'),
        host: getRecordString(record, ['host'], 'null'),
        totalLatency: getRecordNullableNumber(record, [
          'total_latency',
          'sdk_ms',
          'sdkMs',
          'latency',
        ]),
        queryMetaLatency: getRecordNullableNumber(record, [
          'worker_query_meta_latency',
          'query_meta_latency',
          'req_delay',
          'reqDelay',
        ]),
        urmaTotalLatency: getRecordNullableNumber(record, [
          'urma_total_latency',
          'rsp_delay',
          'respDelay',
          'rspDelay',
        ]),
        urmaLinkLatency: getRecordNullableNumber(record, ['urma_link_latency']),
        c2wUrmaLatency: getRecordNullableNumber(record, ['c2w_urma_latency']),
        w2wUrmaLatency: getRecordNullableNumber(record, ['w2w_urma_latency']),
        sdkProcess: getRecordNullableNumber(record, ['sdk_process']),
        sdkRpc: getRecordNullableNumber(record, ['sdk_rpc']),
        localWorkerCost: getRecordNullableNumber(record, ['local_worker_cost']),
        localWorkerLock: getRecordNullableNumber(record, ['local_worker_lock']),
        remoteWorkerCost: getRecordNullableNumber(record, ['remote_worker_cost']),
        remoteWorkerRpc: getRecordNullableNumber(record, ['remote_worker_rpc']),
        masterProcess: getRecordNullableNumber(record, ['master_process']),
        masterRpcTotal: getRecordNullableNumber(record, ['master_rpc_total']),
        raw: result,
      }
    }),
)

const detailParseResultsPageCount = computed(() =>
  Math.max(1, Math.ceil(detailParseResultsTotal.value / 20)),
)
const detailParseResultsPageWindow = computed(() =>
  getPageWindow(detailParseResultsPage.value, detailParseResultsPageCount.value),
)

const detailParseResultsBadgeCount = computed(() => detailParseResultsTotal.value)

const faultDetailTraceEventsPageCount = computed(() =>
  Math.max(1, Math.ceil(faultDetailTraceEventsTotal.value / 20)),
)
const faultDetailTraceEventsPageWindow = computed(() =>
  getPageWindow(faultDetailTraceEventsPage.value, faultDetailTraceEventsPageCount.value),
)
const selectedFaultDetailErrorLogTotal = computed(() => faultDetailTraceEventsTotal.value)

const faultTraceByLatencyPair = computed<Record<string, TraceDetailRow[]>>(() => {
  const grouped: Record<string, TraceDetailRow[]> = {}
  latencyResults.value.forEach((result) => {
    const anomalyInfo = getLogResultAnomalyInfo(result)
    if (!anomalyInfo) return

    const record = result as Record<string, unknown>
    const sourceHost = stripHostPort(getRecordString(record, ['src_ip', 'source_ip', 'sourceHost']))
    const targetHost = stripHostPort(
      getRecordString(record, ['dst_ip', 'destination_ip', 'targetHost']),
    )
    const key = getLatencyPairKey(sourceHost, targetHost)
    const traces = grouped[key] ?? []
    traces.push({
      ...getLogResultTrace(result),
      faultCode: anomalyInfo.code,
      faultType: anomalyInfo.description,
      faultDomain: getFaultDomainByCode(anomalyInfo.code),
    })
    grouped[key] = traces
  })

  Object.values(grouped).forEach((traces) => {
    traces.sort(
      (a, b) =>
        (parseFilterDate(a.time)?.getTime() ?? 0) - (parseFilterDate(b.time)?.getTime() ?? 0),
    )
  })

  return grouped
})

const faultDetailRows = computed<FaultDetailRow[]>(() =>
  aggregatedEvents.value.map((event) => {
    const sourceHost = stripHostPort(event.src_ip)
    const targetHost = stripHostPort(event.dst_ip)
    const key = getLatencyPairKey(sourceHost, targetHost)
    const traces = faultTraceByLatencyPair.value[key] ?? []
    const faultCodesForRow = [
      ...new Set(
        traces.map((trace) => trace.faultCode).filter((code): code is string => Boolean(code)),
      ),
    ].sort((a, b) => a.localeCompare(b))

    return {
      id: event.id,
      sourceHost,
      targetHost,
      total: getRecordNumber(event as Record<string, unknown>, ['anomaly_log_parse_result_cnt'], 0),
      faultCodes: faultCodesForRow,
    }
  }),
)

const getTraceLogTimeValue = (log: TraceLogRow) => parseFilterDate(log.time)?.getTime() ?? 0

const sortTraceLogsByFile = (logs: TraceLogRow[]) =>
  [...logs].sort(
    (a, b) =>
      a.filename.localeCompare(b.filename, undefined, { numeric: true }) ||
      getTraceLogTimeValue(a) - getTraceLogTimeValue(b) ||
      a.pidTid.localeCompare(b.pidTid, undefined, { numeric: true }) ||
      a.message.localeCompare(b.message),
  )

const getTraceLogDisplayFilename = (record: Record<string, unknown>) =>
  getRecordString(record, ['log_file', 'source_file', 'file_path', 'filename', 'file_name'], '-')

const runLogHeaders = [
  'Time',
  'level',
  'filename',
  'pod_name',
  'pid:tid',
  'trace_id',
  'cluster_name',
  'message',
]

const accessLogHeaders = [
  'Time',
  'level',
  'filename',
  'pod_name',
  'pid:tid',
  'trace_id',
  'cluster_name',
  'status_code',
  'action',
  'cost',
  'data size',
  'request param',
  'response param',
]

const resourceLogHeaders = [
  'Time',
  'level',
  'filename',
  'pod_name',
  'pid:tid',
  'trace_id',
  'cluster_name',
  'shm info',
  'spill disk info',
  'client nums',
  'object nums',
  'object total datasize',
  'WorkerOcService threadpool',
  'WorkerWorkerOcService threadpool',
  'MasterWorkerOcService threadpool',
  'MasterOcService threadpool',
  'write ETCD queue',
  'ETCDrequest success rate',
  'OBSrequest success rate',
  'Master AsyncTask threadpool',
  'stream nums',
  'ClientWorkerSCService threadpool',
  'WorkerWorkerSCService threadpool',
  'MasterWorkerSCService threadpool',
  'MasterSCService threadpool',
  'remote stream push success rate',
  'shared disk info',
  'scLocalCache info',
  'Cache Hit Info',
]

const streamCacheMetricHeaders = [
  'Time',
  'level',
  'filename',
  'pod_name',
  'pid:tid',
  'trace_id',
  'cluster_name',
  'sc_metric',
]

const splitRawLogText = (rawText: string) =>
  rawText
    .split(/\s*\|\s*/)
    .map((part) => part.trim())
    .filter((part, index, parts) => part || index < parts.length - 1)

const normalizeTraceLogColumns = (headers: string[], fields: string[]) => {
  const normalizedHeaders = [...headers]
  while (normalizedHeaders.length < fields.length) {
    normalizedHeaders.push(`extra_${normalizedHeaders.length - headers.length + 1}`)
  }
  return fields.map((value, index) => ({
    label: normalizedHeaders[index] || `field_${index + 1}`,
    value: value || '-',
  }))
}

const buildTraceRawColumns = (
  rawText: string,
  logFile: string,
  sourceFilename: string,
): { formatName: string; columns: TraceRawLogColumn[] } => {
  const fields = splitRawLogText(rawText)
  if (fields.length === 0) {
    return {
      formatName: '原始日志',
      columns: [{ label: 'raw_text', value: rawText || '-' }],
    }
  }

  if (fields.length >= resourceLogHeaders.length) {
    return {
      formatName: '资源日志',
      columns: normalizeTraceLogColumns(resourceLogHeaders, fields),
    }
  }

  if (fields.length >= accessLogHeaders.length) {
    return {
      formatName: '访问日志',
      columns: normalizeTraceLogColumns(accessLogHeaders, [
        ...fields.slice(0, accessLogHeaders.length - 1),
        fields.slice(accessLogHeaders.length - 1).join(' | '),
      ]),
    }
  }

  const hint = `${logFile} ${sourceFilename} ${fields[7] ?? ''}`.toLowerCase()
  if (fields.length === streamCacheMetricHeaders.length && hint.includes('sc')) {
    return {
      formatName: '流缓存数据日志',
      columns: normalizeTraceLogColumns(streamCacheMetricHeaders, fields),
    }
  }

  if (fields.length >= runLogHeaders.length) {
    return {
      formatName: '运行日志',
      columns: normalizeTraceLogColumns(runLogHeaders, [
        ...fields.slice(0, runLogHeaders.length - 1),
        fields.slice(runLogHeaders.length - 1).join(' | '),
      ]),
    }
  }

  return {
    formatName: '未知格式日志',
    columns: normalizeTraceLogColumns(
      Array.from({ length: fields.length }, (_, index) => `field_${index + 1}`),
      fields,
    ),
  }
}

const toTraceLogRow = (result: LogFailureEventResultModel): TraceLogRow => {
  const record = result as Record<string, unknown>
  const level = getRecordString(record, ['level', 'log_level'], 'INFO').toUpperCase()
  const pid = getRecordString(record, ['pid'], '')
  const tid = getRecordString(record, ['tid'], '')
  const logFile = getTraceLogDisplayFilename(record)
  const sourceFilename = getRecordString(record, ['filename', 'file_name'], '-')
  const rawText = getRecordString(record, ['raw_text', 'rawText', 'content'], '')
  const rawLog = buildTraceRawColumns(rawText, logFile, sourceFilename)
  const failureModes = Array.isArray(result.failure_mode)
    ? result.failure_mode.filter((item): item is string => typeof item === 'string' && Boolean(item))
    : []

  return {
    time: normalizeTimeText(getRecordString(record, ['timestamp', 'created_at', 'time'], '')),
    level: level === 'ERROR' ? 'ERROR' : 'INFO',
    filename: logFile,
    podIp: getRecordString(record, ['pod_ip', 'pod_name', 'pod_id', 'podId', 'pod']),
    pidTid: pid || tid ? `${pid || '-'}:${tid || '-'}` : getRecordString(record, ['pid_tid'], '-'),
    traceId: getRecordString(record, ['trace_id', 'traceId']),
    clusterName: getRecordString(record, ['cluster_name', 'clusterName', 'cluster'], '-'),
    message: getRecordString(record, ['message', 'raw_text', 'msg', 'content'], ''),
    failureModeIds: failureModes,
    faultType: failureModes.join(', '),
    faultDomain: getRecordString(record, ['status_code'], ''),
    rawText,
    formatName: rawLog.formatName,
    rawColumns: rawLog.columns,
  }
}

const getTraceLogFailureModeLabels = (log: TraceLogRow) =>
  log.failureModeIds
    .map((id) => ({
      id,
      label: failureModeDetailsById.value[id]?.name || id,
    }))
    .filter((item) => item.id && item.label)

const getTraceLogs = (trace?: TraceDetailRow | null) => {
  if (!trace) return []
  const traceId = trace.traceId
  return Object.prototype.hasOwnProperty.call(traceFailureLogsByTrace.value, traceId)
    ? sortTraceLogsByFile(traceFailureLogsByTrace.value[traceId] ?? [])
    : []
}

const getSelectedTraceLogs = () => getTraceLogs(selectedTrace.value)

const getTraceFailureEvents = (trace?: TraceDetailRow | null) => {
  if (!trace) return []
  const traceId = trace.traceId
  return traceFailureEventsByTrace.value[traceId] ?? []
}

const getSelectedFaultTraceLogs = () => getTraceLogs(selectedFaultTrace.value)

const selectedFaultTraceFailureModeIds = computed<string[]>(() => {
  const events = getTraceFailureEvents(selectedFaultTrace.value)
  const ids = new Set<string>()
  events.forEach((event) => {
    getFailureModeIds(event as Record<string, unknown>).forEach((id) => ids.add(id))
  })
  return [...ids]
})

const selectedFaultTraceFailureModes = computed<(FailureModeKnowledgeModel & { _id: string })[]>(() =>
  selectedFaultTraceFailureModeIds.value
    .map((id) => {
      const detail = failureModeDetailsById.value[id]
      return { ...detail, _id: id }
    })
    .filter((item) => item.id || item.name || item._id) as (FailureModeKnowledgeModel & { _id: string })[],
)

const selectedFaultTraceFailureMode = computed<(FailureModeKnowledgeModel & { _id: string }) | null>(() => {
  const selectedId = selectedFaultTraceFailureModeId.value
  if (!selectedId) return null
  return selectedFaultTraceFailureModes.value.find((failureMode) => failureMode._id === selectedId) ?? null
})

const selectedChildFailureMode = computed<(FailureModeKnowledgeModel & { _id: string }) | null>(() => {
  const selectedId = selectedChildFailureModeId.value
  if (!selectedId) return null
  const detail = failureModeDetailsById.value[selectedId]
  if (!detail) return null
  return { ...detail, _id: selectedId }
})

const selectFaultTraceFailureMode = (failureModeId: string) => {
  selectedFaultTraceFailureModeId.value = failureModeId
  selectedChildFailureModeId.value = ''
  void loadFailureModeChildrenDetails(failureModeId)
}

const getFailureModeChildren = (failureMode?: FailureModeKnowledgeModel | null) =>
  failureMode?.children_failure_mode_ids
    ?.split(',')
    .map((childId) => childId.trim())
    .filter(Boolean) ?? []

const hasFailureModeDetailResult = (failureModeId: string) =>
  Object.prototype.hasOwnProperty.call(failureModeDetailsById.value, failureModeId)

const getFailureModeChildLabel = (childId: string) => {
  if (!hasFailureModeDetailResult(childId)) {
    return '加载中...'
  }
  return failureModeDetailsById.value[childId]?.name || '未知子故障'
}

const loadFailureModeChildrenDetails = async (failureModeId: string) => {
  const parentFailureMode =
    failureModeDetailsById.value[failureModeId] ?? (await loadFailureModeDetail(failureModeId))
  const childIds = getFailureModeChildren(parentFailureMode)
  await Promise.all(childIds.map((childId) => loadFailureModeDetail(childId)))
}

const selectChildFailureMode = async (childId: string) => {
  selectedChildFailureModeId.value =
    selectedChildFailureModeId.value === childId ? '' : childId
  if (selectedChildFailureModeId.value) {
    await loadFailureModeDetail(childId)
  }
}

const normalizeFilterText = (value: string) => value.trim()

const parseFilterDate = (value: string) => {
  if (!value) return null
  const parsed = new Date(value.replace(' ', 'T'))
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

const isTraceTimeMatched = (trace: Pick<TraceDetailRow, 'time'>, filters: GlobalFilterState) => {
  const traceDate = parseFilterDate(trace.time)
  if (!traceDate) return true

  const startDate = parseFilterDate(filters.startTime)
  const endDate = parseFilterDate(filters.endTime)
  if (startDate && traceDate < startDate) return false
  if (endDate && traceDate > endDate) return false
  return true
}

const matchesLatencyRowHostFilters = (row: LatencyDetailRow) => {
  const { sourceHosts, targetHosts } = appliedFilters.value
  if (sourceHosts.length > 0 && !sourceHosts.includes(row.sourceHost)) return false
  if (targetHosts.length > 0 && !targetHosts.includes(row.targetHost)) return false
  return true
}

const getFilteredLatencyRows = () =>
  isLatencyEventListFilterMode.value
    ? latencyDetailRows.value
    : latencyDetailRows.value.filter(matchesLatencyRowHostFilters)

const matchesAbnormalTraceFilters = (row: AbnormalTraceRow) => {
  const filters = appliedFilters.value
  if (!isTraceTimeMatched(row, filters)) return false
  if (filters.clusters.length > 0 && !filters.clusters.includes(row.clusterName)) return false
  if (filters.hosts.length > 0 && !filters.hosts.includes(row.host)) return false
  return true
}

const getFilteredAbnormalTraceRows = () =>
  abnormalTraceRows.value.filter(matchesAbnormalTraceFilters)

const getFaultRowTraces = (row: FaultDetailRow) =>
  faultTraceByLatencyPair.value[getLatencyPairKey(row.sourceHost, row.targetHost)] ?? []

const matchesFaultRowHostFilters = (row: FaultDetailRow) => {
  const { hosts } = appliedFilters.value
  return hosts.length === 0 || hosts.includes(row.sourceHost) || hosts.includes(row.targetHost)
}

const getFilteredFaultRows = () => faultDetailRows.value.filter(matchesFaultRowHostFilters)

const getFaultCodeMatchedTraceIds = (faultCodesToMatch: string[]) => {
  if (faultCodesToMatch.length === 0) return new Set<string>()

  return new Set(
    Object.values(faultTraceByLatencyPair.value)
      .flat()
      .filter((trace) => trace.faultCode && faultCodesToMatch.includes(trace.faultCode))
      .map((trace) => trace.traceId),
  )
}

const matchesAppliedTraceFilters = (trace: TraceDetailRow, source: 'latency' | 'fault') => {
  const filters = appliedFilters.value

  if (filters.clusters.length > 0 && !filters.clusters.includes(trace.clusterName ?? ''))
    return false
  if (filters.faultCodes.length > 0) {
    const isDirectFaultCodeMatch = Boolean(
      trace.faultCode && filters.faultCodes.includes(trace.faultCode),
    )
    const isTraceIdLinkedMatch =
      source === 'latency' && getFaultCodeMatchedTraceIds(filters.faultCodes).has(trace.traceId)

    if (!isDirectFaultCodeMatch && !isTraceIdLinkedMatch) return false
  }
  return isTraceTimeMatched(trace, filters)
}

const getFilteredFaultRowTraces = (row: FaultDetailRow) =>
  getFaultRowTraces(row).filter((trace) => matchesAppliedTraceFilters(trace, 'fault'))

const getFilteredFaultTraces = () =>
  getFilteredFaultRows().flatMap((row) =>
    getFilteredFaultRowTraces(row).map((trace) => ({
      ...trace,
      rowId: row.id,
    })),
  )

const toFaultTraceTableRow = (result: TraceFailureEventResultModel): FaultTraceTableRow => {
  const record = result as Record<string, unknown>
  const podNames = getRecordArray(record, ['pod_names', 'podNames'])
  const hostNames = getRecordArray(record, ['host_names', 'hostNames'])
  const clusterNames = getRecordArray(record, ['cluster_names', 'clusterNames'])
  const failureModeId = getFailureModeIds(record)[0] ?? ''
  const failureMode = failureModeId ? failureModeDetailsById.value[failureModeId] : null

  return {
    id: getRecordString(record, ['id', 'trace_id', 'traceId']),
    traceId: getRecordString(record, ['trace_id', 'traceId']),
    podIp: podNames[0] ?? '-',
    podNames,
    host: hostNames[0] ?? '-',
    hostNames,
    clusterName: clusterNames[0] ?? '-',
    clusterNames,
    time: normalizeTimeText(getRecordString(record, ['timestamp', 'created_at', 'time'], '')),
    sdkMs: null,
    reqDelay: null,
    respDelay: null,
    urmaLinkLatency: null,
    c2wUrmaLatency: null,
    w2wUrmaLatency: null,
    sdkProcess: null,
    sdkRpc: null,
    localWorkerCost: null,
    localWorkerLock: null,
    remoteWorkerCost: null,
    remoteWorkerRpc: null,
    masterProcess: null,
    masterRpcTotal: null,
    faultCode: getRecordString(record, ['status_code', 'statusCode'], ''),
    faultType: failureMode?.name || '-',
    faultDomain: failureMode?.failure_domain || '-',
    failureModeId,
    failureMode,
  }
}

const getFilteredFaultTraceRows = () => faultTraceRows.value

const getFaultTraceFailureModeLabel = (row: FaultTraceTableRow) =>
  row.failureMode?.name || row.failureModeId || row.faultType || '-'

const openTraceDialog = (trace: TraceDetailRow) => {
  selectedTrace.value = trace
}

const closeTraceDialog = () => {
  selectedTrace.value = null
}

const openFaultTraceDialog = async (trace: TraceDetailRow) => {
  selectedFaultTrace.value = trace
  selectedFaultTraceFailureModeId.value = ''
  selectedChildFailureModeId.value = ''
  await loadTraceFailureLogs(trace.traceId, true)
  const events = traceFailureEventsByTrace.value[trace.traceId] ?? []
  const failureModeIds = new Set<string>()
  events.forEach((event) => {
    getFailureModeIds(event as Record<string, unknown>).forEach((id) => failureModeIds.add(id))
  })
  await Promise.all([...failureModeIds].map((id) => loadFailureModeDetail(id)))
}

const closeFaultTraceDialog = () => {
  selectedFaultTrace.value = null
  selectedFaultTraceFailureModeId.value = ''
  selectedChildFailureModeId.value = ''
}

const openParseResultChain = (row: ParseResultTableRow) => {
  const record = row.raw as Record<string, unknown>
  openTraceDialog({
    traceId: row.traceId,
    podIp: row.podIp,
    time: row.time,
    sdkMs: row.totalLatency,
    reqDelay: getRecordNullableNumber(record, [
      'worker_query_meta_latency',
      'query_meta_latency',
      'req_delay',
      'reqDelay',
    ]),
    respDelay: getRecordNullableNumber(record, [
      'urma_total_latency',
      'rsp_delay',
      'respDelay',
      'rspDelay',
    ]),
    urmaLinkLatency: row.urmaLinkLatency,
    c2wUrmaLatency: row.c2wUrmaLatency,
    w2wUrmaLatency: row.w2wUrmaLatency,
    sdkProcess: row.sdkProcess,
    sdkRpc: row.sdkRpc,
    localWorkerCost: row.localWorkerCost,
    localWorkerLock: row.localWorkerLock,
    remoteWorkerCost: row.remoteWorkerCost,
    remoteWorkerRpc: row.remoteWorkerRpc,
    masterProcess: row.masterProcess,
    masterRpcTotal: row.masterRpcTotal,
  })
  void loadTraceFailureLogs(row.traceId)
}

type FilterTagCategory = 'cluster' | 'host' | 'sourceHost' | 'targetHost' | 'faultCode'

type GlobalFilterListKey = 'clusters' | 'hosts' | 'sourceHosts' | 'targetHosts' | 'faultCodes'

const filterTagCollections: Record<FilterTagCategory, GlobalFilterListKey> = {
  cluster: 'clusters',
  host: 'hosts',
  sourceHost: 'sourceHosts',
  targetHost: 'targetHosts',
  faultCode: 'faultCodes',
}

const addUniqueFilterItem = (category: FilterTagCategory, value: string) => {
  const normalized = value.trim()
  if (!normalized) return

  const key = filterTagCollections[category]
  if (!globalFilters[key].includes(normalized)) {
    globalFilters[key].push(normalized)
  }
  filterApplyMessage.value = ''
}

const setSingleFilterItem = (category: 'cluster' | 'host', value: string) => {
  const normalized = value.trim()
  if (!normalized) return

  const key = filterTagCollections[category]
  globalFilters[key] = [normalized]
  filterApplyMessage.value = ''
}

const setSingleIpFilterItem = (category: 'sourceHost' | 'targetHost', value: string) => {
  const normalized = value.trim()
  if (!normalized) return

  const key = filterTagCollections[category]
  globalFilters[key] = [normalized]
  filterApplyMessage.value = ''
}

const addFilterValue = (category: FilterTagCategory) => {
  const value = filterDraftInput[category].trim()
  if (!value) return

  if (category === 'cluster' || category === 'host') {
    addUniqueFilterItem(category, value)
  } else if (category === 'sourceHost' || category === 'targetHost') {
    setSingleIpFilterItem(category, value)
  } else {
    addUniqueFilterItem(category, value)
  }
  filterDraftInput[category] = ''
}

const removeFilterValue = (category: FilterTagCategory, value: string) => {
  const key = filterTagCollections[category]
  globalFilters[key] = globalFilters[key].filter((item) => item !== value)
}

const resetFilterCategory = (category: FilterTagCategory | 'time' | 'traceBoard') => {
  if (category === 'time') {
    globalFilters.startTime = ''
    globalFilters.endTime = ''
  } else if (category === 'traceBoard') {
    globalFilters.traceBoards = []
  } else {
    const key = filterTagCollections[category]
    globalFilters[key] = [] as never
    filterDraftInput[category] = ''
  }
  filterApplyMessage.value = ''
}

const resetAllFilters = () => {
  globalFilters.startTime = ''
  globalFilters.endTime = ''
  globalFilters.clusters = []
  globalFilters.hosts = []
  globalFilters.sourceHosts = []
  globalFilters.targetHosts = []
  globalFilters.faultCodes = []
  filterDraftInput.cluster = ''
  filterDraftInput.host = ''
  filterDraftInput.sourceHost = ''
  filterDraftInput.targetHost = ''
  filterDraftInput.faultCode = ''
  filterApplyMessage.value = ''
}

const addHostFilter = (host: string) => {
  setSingleFilterItem('host', host)
}

const addSourceHostFilter = (host: string) => {
  setSingleIpFilterItem('sourceHost', host)
}

const addTargetHostFilter = (host: string) => {
  setSingleIpFilterItem('targetHost', host)
}

const openLatencyHostFilterDialog = (row: LatencyDetailRow | FaultDetailRow) => {
  latencyHostFilterDialog.row = row
  latencyHostFilterDialog.addSourceHost = false
  latencyHostFilterDialog.addTargetHost = false
  latencyHostFilterDialog.open = true
}

const openAggregatedEventDetail = (row: LatencyDetailRow) => {
  selectedAggregatedEvent.value = row
  detailParseResultsPage.value = 1
  void loadDetailLatencyChart(row)
  void loadDetailParseResults(row, 1)
}

const closeAggregatedEventDetail = () => {
  selectedAggregatedEvent.value = null
  detailLatencyMetrics.value = []
  detailLatencyChartError.value = ''
  detailParseResults.value = []
  detailParseResultsError.value = ''
  detailParseResultsTotal.value = 0
  detailParseResultsPage.value = 1
  detailLatencyChartInstance?.dispose()
  detailLatencyChartInstance = null
}

const loadFaultAggregatedEventDetailTraceEvents = async (
  detail: FaultAggregatedEventDetail,
  pageNum = faultDetailTraceEventsPage.value,
) => {
  if (!selectedAssetId.value) {
    faultDetailTraceRows.value = []
    faultDetailTraceEventsTotal.value = 0
    faultDetailTraceEventsPage.value = 1
    faultDetailTraceEventsError.value = ''
    isFaultDetailTraceEventsLoading.value = false
    return
  }

  const detailKey = `${detail.eventRow.id}-${detail.podRow.id}`
  isFaultDetailTraceEventsLoading.value = true
  faultDetailTraceEventsError.value = ''

  try {
    const result = await request<{
      total: number
      trace_failure_event_results: TraceFailureEventResultModel[]
    }>('/log_failure_event_result/list_trace_events', {
      method: 'POST',
      body: JSON.stringify({
        kb_id: selectedAssetId.value,
        pod_names: [detail.podRow.podIp],
        is_anomalous: true,
        created_at_start: detail.eventRow.startTime,
        created_at_end: detail.eventRow.endTime,
        page_cnt: 20,
        page_num: pageNum,
      }),
    })

    if (
      `${selectedFaultAggregatedEventDetail.value?.eventRow.id}-${selectedFaultAggregatedEventDetail.value?.podRow.id}` !==
      detailKey
    ) {
      return
    }

    const events = result.trace_failure_event_results ?? []
    const total = result.total ?? 0
    const pageCount = Math.max(1, Math.ceil(total / 20))

    if (pageNum > pageCount) {
      isFaultDetailTraceEventsLoading.value = false
      await loadFaultAggregatedEventDetailTraceEvents(detail, pageCount)
      return
    }

    const failureModeIds = [
      ...new Set(events.flatMap((event) => getFailureModeIds(event as Record<string, unknown>))),
    ]
    await Promise.all(failureModeIds.map((failureModeId) => loadFailureModeDetail(failureModeId)))

    if (
      `${selectedFaultAggregatedEventDetail.value?.eventRow.id}-${selectedFaultAggregatedEventDetail.value?.podRow.id}` ===
      detailKey
    ) {
      faultDetailTraceRows.value = events.map(toFaultTraceTableRow)
      faultDetailTraceEventsTotal.value = total
      faultDetailTraceEventsPage.value = pageNum
    }
  } catch (error) {
    if (
      `${selectedFaultAggregatedEventDetail.value?.eventRow.id}-${selectedFaultAggregatedEventDetail.value?.podRow.id}` ===
      detailKey
    ) {
      faultDetailTraceRows.value = []
      faultDetailTraceEventsTotal.value = 0
      faultDetailTraceEventsPage.value = pageNum
      faultDetailTraceEventsError.value =
        error instanceof Error ? error.message : '加载错误日志失败'
    }
  } finally {
    if (
      `${selectedFaultAggregatedEventDetail.value?.eventRow.id}-${selectedFaultAggregatedEventDetail.value?.podRow.id}` ===
      detailKey
    ) {
      isFaultDetailTraceEventsLoading.value = false
    }
  }
}

const loadFaultAggregatedEventDetailChart = async (detail: FaultAggregatedEventDetail) => {
  if (!selectedAssetId.value) {
    faultDetailChartMetrics.value = {}
    faultDetailChartError.value = ''
    isFaultDetailChartLoading.value = false
    return
  }

  const errCodes = selectedFaultDetailChartCodes.value
  if (errCodes.length === 0) {
    faultDetailChartMetrics.value = {}
    faultDetailChartError.value = ''
    isFaultDetailChartLoading.value = false
    return
  }

  const detailKey = `${detail.eventRow.id}-${detail.podRow.id}`
  isFaultDetailChartLoading.value = true
  faultDetailChartError.value = ''
  faultDetailChartMetrics.value = {}

  try {
    const result = await request<{
      total: number
      metrics: Record<string, ErrCodeMetricItem[]>
    }>('/log_failure_event_result/metrics/err_code', {
      method: 'POST',
      body: JSON.stringify({
        kb_id: selectedAssetId.value,
        err_codes: errCodes,
        pod_names: [detail.podRow.podIp],
        start_time: detail.eventRow.startTime,
        end_time: detail.eventRow.endTime,
        max_points: 1000,
      }),
    })

    if (
      `${selectedFaultAggregatedEventDetail.value?.eventRow.id}-${selectedFaultAggregatedEventDetail.value?.podRow.id}` ===
      detailKey
    ) {
      faultDetailChartMetrics.value = result.metrics ?? {}
    }
  } catch (error) {
    if (
      `${selectedFaultAggregatedEventDetail.value?.eventRow.id}-${selectedFaultAggregatedEventDetail.value?.podRow.id}` ===
      detailKey
    ) {
      faultDetailChartMetrics.value = {}
      faultDetailChartError.value =
        error instanceof Error ? error.message : '加载故障码计数趋势失败'
    }
  } finally {
    if (
      `${selectedFaultAggregatedEventDetail.value?.eventRow.id}-${selectedFaultAggregatedEventDetail.value?.podRow.id}` ===
      detailKey
    ) {
      isFaultDetailChartLoading.value = false
    }
  }
}

const openFaultAggregatedEventDetail = (
  eventRow: FaultAggregatedEventRow,
  podRow: FaultAggregatedEventPodRow,
) => {
  const detail = {
    eventRow,
    podRow,
  }
  selectedFaultAggregatedEventDetail.value = detail
  faultDetailTraceRows.value = []
  faultDetailTraceEventsTotal.value = 0
  faultDetailTraceEventsPage.value = 1
  faultDetailTraceEventsPageInput.value = ''
  faultDetailTraceEventsError.value = ''
  faultDetailChartMetrics.value = {}
  faultDetailChartError.value = ''
  void loadFaultAggregatedEventDetailTraceEvents(detail, 1)
  void loadFaultAggregatedEventDetailChart(detail)
}

const closeFaultAggregatedEventDetail = () => {
  selectedFaultAggregatedEventDetail.value = null
  faultDetailTraceRows.value = []
  faultDetailTraceEventsTotal.value = 0
  faultDetailTraceEventsPage.value = 1
  faultDetailTraceEventsPageInput.value = ''
  faultDetailTraceEventsError.value = ''
  isFaultDetailTraceEventsLoading.value = false
  faultDetailChartMetrics.value = {}
  faultDetailChartError.value = ''
  isFaultDetailChartLoading.value = false
  faultDetailChartInstance?.dispose()
  faultDetailChartInstance = null
}

const viewAbnormalTraceLink = (row: AbnormalTraceRow) => {
  const traceRow: TraceDetailRow = {
    traceId: row.traceId,
    podIp: row.podIp,
    time: row.time,
    sdkMs: row.totalLatency,
    reqDelay: row.queryMetaLatency,
    respDelay: row.urmaTotalLatency,
    urmaLinkLatency: row.urmaLinkLatency,
    c2wUrmaLatency: row.c2wUrmaLatency,
    w2wUrmaLatency: row.w2wUrmaLatency,
    sdkProcess: row.sdkProcess,
    sdkRpc: row.sdkRpc,
    localWorkerCost: row.localWorkerCost,
    localWorkerLock: row.localWorkerLock,
    remoteWorkerCost: row.remoteWorkerCost,
    remoteWorkerRpc: row.remoteWorkerRpc,
    masterProcess: row.masterProcess,
    masterRpcTotal: row.masterRpcTotal,
  }
  openTraceDialog(traceRow)
  void loadTraceFailureLogs(row.traceId)
}

const closeLatencyHostFilterDialog = () => {
  latencyHostFilterDialog.open = false
  latencyHostFilterDialog.row = null
}

const confirmLatencyHostFilterDialog = () => {
  const row = latencyHostFilterDialog.row
  if (!row) return

  if (latencyHostFilterDialog.addSourceHost) {
    addSourceHostFilter(row.sourceHost)
  }
  if (latencyHostFilterDialog.addTargetHost) {
    addTargetHostFilter(row.targetHost)
  }

  closeLatencyHostFilterDialog()
}

const removeTraceBoardValue = (traceId: string) => {
  globalFilters.traceBoards = globalFilters.traceBoards.filter((item) => item !== traceId)
  filterApplyMessage.value = ''
}

const addTraceBoardValue = (traceId: string) => {
  if (!globalFilters.traceBoards.includes(traceId)) {
    globalFilters.traceBoards.push(traceId)
  }
  filterApplyMessage.value = ''
}

const isTraceFilterValueAvailable = (value?: string) =>
  Boolean(value && value !== 'null' && value !== '-')

const openTraceFilterDialog = (trace: TraceFilterTarget) => {
  traceFilterDialog.trace = trace
  traceFilterDialog.addCluster = false
  traceFilterDialog.addHost = false
  traceFilterDialog.addTraceBoard = false
  traceFilterDialog.addFaultCode = false
  traceFilterDialog.open = true
}

const closeTraceFilterDialog = () => {
  traceFilterDialog.open = false
  traceFilterDialog.trace = null
}

const confirmTraceFilterDialog = () => {
  const trace = traceFilterDialog.trace
  if (!trace) return

  if (traceFilterDialog.addCluster && isTraceFilterValueAvailable(trace.clusterName)) {
    setSingleFilterItem('cluster', trace.clusterName ?? '')
  }
  if (traceFilterDialog.addHost && isTraceFilterValueAvailable(trace.host)) {
    setSingleFilterItem('host', trace.host ?? '')
  }
  if (traceFilterDialog.addTraceBoard) {
    addTraceBoardValue(trace.traceId)
  }
  const faultCode = trace.faultCode ?? ''
  if (
    isFaultCodeFeatureEnabled &&
    traceFilterDialog.addFaultCode &&
    isTraceFilterValueAvailable(faultCode)
  ) {
    addUniqueFilterItem('faultCode', faultCode)
  }

  closeTraceFilterDialog()
}

const snapshotCurrentFilters = (): GlobalFilterState => ({
  startTime: globalFilters.startTime,
  endTime: globalFilters.endTime,
  clusters: globalFilters.clusters.map(normalizeFilterText).filter(Boolean),
  hosts: globalFilters.hosts.map(normalizeFilterText).filter(Boolean),
  sourceHosts: globalFilters.sourceHosts.map(normalizeFilterText).filter(Boolean),
  targetHosts: globalFilters.targetHosts.map(normalizeFilterText).filter(Boolean),
  faultCodes: globalFilters.faultCodes.map(normalizeFilterText).filter(Boolean),
  traceBoards: [],
})

const getActiveFilterCount = (filters: GlobalFilterState) => {
  const traceFilterCount =
    (filters.startTime || filters.endTime ? 1 : 0) + filters.clusters.length + filters.hosts.length
  const latencyEventFilterCount = isLatencyEventListFilterMode.value
    ? filters.sourceHosts.length + filters.targetHosts.length
    : 0

  if (shouldShowFaultCodeFilter.value) {
    return traceFilterCount + latencyEventFilterCount + filters.faultCodes.length
  }

  return traceFilterCount + latencyEventFilterCount
}

const clearFilterApplyMessage = () => {
  filterApplyMessage.value = ''
}

const applyGlobalFilters = () => {
  const nextFilters = snapshotCurrentFilters()
  appliedFilters.value = nextFilters

  const activeCount = getActiveFilterCount(nextFilters)

  filterApplyMessage.value = activeCount > 0 ? `已确认 ${activeCount} 个筛选条件` : '已清空筛选条件'

  if (isAbnormalMonitorPage.value) {
    if (activeAggregateTab.value === 'trace') {
      void loadAbnormalTraces(1)
    } else {
      void loadLatencyDetail(1)
    }
    if (isFaultCodeFeatureEnabled) {
      void loadFaultAggregatedEvents(1)
      void loadFaultChart()
      void loadFaultTraceEvents(1)
    }
  }
}

const setActiveAggregateTab = (tab: 'event' | 'trace') => {
  if (activeAggregateTab.value === tab) return
  activeAggregateTab.value = tab
  clearFilterApplyMessage()
}

const request = async <T,>(path: string, init: RequestInit = {}) => {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init.headers,
    },
  })

  const data = (await response.json().catch(() => null)) as ApiResponse<T> | null

  if (!response.ok || !data) {
    throw new Error(data?.message || `请求失败：${response.status}`)
  }

  if (typeof data.code === 'number' && data.code !== 200) {
    throw new Error(data.message || '接口返回异常')
  }

  return (data.result ?? data.data ?? data) as T
}

const loadTraceFailureLogs = async (traceId: string, shouldLoadFailureModes = false) => {
  if (!selectedAssetId.value || !traceId || traceId === '-') return

  isTraceLogsLoading.value = true
  traceLogsError.value = ''
  traceFailureLogsByTrace.value = {
    ...traceFailureLogsByTrace.value,
    [traceId]: [],
  }
  traceFailureEventsByTrace.value = {
    ...traceFailureEventsByTrace.value,
    [traceId]: [],
  }

  try {
    const result = await request<{
      total: number
      log_failure_event_results: LogFailureEventResultModel[]
    }>('/log_failure_event_result/list_log_events', {
      method: 'POST',
      body: JSON.stringify({
        kb_id: selectedAssetId.value,
        trace_ids: [traceId],
      }),
    })

    const events = result.log_failure_event_results ?? []
    if (shouldLoadFailureModes) {
      const failureModeIds = [
        ...new Set(
          events.flatMap((event) => getFailureModeIds(event as Record<string, unknown>)),
        ),
      ]

      await Promise.all(failureModeIds.map((failureModeId) => loadFailureModeDetail(failureModeId)))
    }

    traceFailureEventsByTrace.value = {
      ...traceFailureEventsByTrace.value,
      [traceId]: events,
    }
    traceFailureLogsByTrace.value = {
      ...traceFailureLogsByTrace.value,
      [traceId]: sortTraceLogsByFile(events.map(toTraceLogRow)),
    }
  } catch (error) {
    traceFailureLogsByTrace.value = {
      ...traceFailureLogsByTrace.value,
      [traceId]: [],
    }
    traceFailureEventsByTrace.value = {
      ...traceFailureEventsByTrace.value,
      [traceId]: [],
    }
    traceLogsError.value = error instanceof Error ? error.message : '加载运行日志失败'
  } finally {
    isTraceLogsLoading.value = false
  }
}

const loadFailureModeDetail = async (failureModeId: string) => {
  if (!failureModeId || failureModeId === '-') return null
  const cachedFailureMode = failureModeDetailsById.value[failureModeId]
  if (cachedFailureMode) {
    return cachedFailureMode
  }

  try {
    const result = await request<
      | FailureModeKnowledgeModel
      | {
          failure_mode?: FailureModeKnowledgeModel | null
          failure_mode_knowledge?: FailureModeKnowledgeModel | null
        }
    >(`/failure_mode/${encodeURIComponent(failureModeId)}`)
    const resultRecord = result as Record<string, unknown>
    const failureMode =
      (resultRecord.failure_mode as FailureModeKnowledgeModel | null | undefined) ??
      (resultRecord.failure_mode_knowledge as FailureModeKnowledgeModel | null | undefined) ??
      ((resultRecord.id || resultRecord.name || resultRecord.failure_domain
        ? (result as FailureModeKnowledgeModel)
        : null) as FailureModeKnowledgeModel | null)
    failureModeDetailsById.value = {
      ...failureModeDetailsById.value,
      [failureModeId]: failureMode,
    }
    return failureMode
  } catch {
    failureModeDetailsById.value = {
      ...failureModeDetailsById.value,
      [failureModeId]: null,
    }
    return null
  }
}

const loadFaultTraceEvents = async (pageNum = faultTraceEventsPage.value) => {
  if (!selectedAssetId.value) {
    faultTraceRows.value = []
    faultTraceEventsTotal.value = 0
    faultTraceEventsPage.value = 1
    return
  }

  isFaultTraceEventsLoading.value = true
  faultTraceEventsError.value = ''

  try {
    const filters = appliedFilters.value
    const requestBody: Record<string, unknown> = {
      kb_id: selectedAssetId.value,
      is_anomalous: true,
      page_cnt: faultTraceEventsPageSize,
      page_num: pageNum,
    }

    if (filters.startTime) {
      requestBody.created_at_start = formatDateTime(filters.startTime)
    }
    if (filters.endTime) {
      requestBody.created_at_end = formatDateTime(filters.endTime)
    }
    if (filters.clusters.length > 0) {
      requestBody.cluster_names = filters.clusters
    }
    if (filters.hosts.length > 0) {
      requestBody.host_names = filters.hosts
    }
    if (filters.faultCodes.length > 0) {
      requestBody.status_codes = filters.faultCodes
    }

    const result = await request<{
      total: number
      trace_failure_event_results: TraceFailureEventResultModel[]
    }>('/log_failure_event_result/list_trace_events', {
      method: 'POST',
      body: JSON.stringify(requestBody),
    })

    const events = result.trace_failure_event_results ?? []
    const total = result.total ?? 0
    const pageCount = Math.max(1, Math.ceil(total / faultTraceEventsPageSize))

    if (pageNum > pageCount) {
      isFaultTraceEventsLoading.value = false
      await loadFaultTraceEvents(pageCount)
      return
    }

    const failureModeIds = [
      ...new Set(
        events.flatMap((event) => getFailureModeIds(event as Record<string, unknown>)),
      ),
    ]

    await Promise.all(failureModeIds.map((failureModeId) => loadFailureModeDetail(failureModeId)))

    faultTraceRows.value = events.map(toFaultTraceTableRow)
    faultTraceEventsTotal.value = total
    faultTraceEventsPage.value = pageNum
  } catch (error) {
    faultTraceRows.value = []
    faultTraceEventsTotal.value = 0
    faultTraceEventsPage.value = 1
    faultTraceEventsError.value =
      error instanceof Error ? error.message : '加载错误日志列表失败'
  } finally {
    isFaultTraceEventsLoading.value = false
  }
}

const loadFaultChart = async () => {
  if (!selectedAssetId.value) {
    faultChartMetrics.value = {}
    faultChartError.value = ''
    isFaultChartLoading.value = false
    return
  }

  isFaultChartLoading.value = true
  faultChartError.value = ''

  try {
    const filters = appliedFilters.value
    const requestBody: Record<string, unknown> = {
      kb_id: selectedAssetId.value,
      max_points: 1000,
    }

    if (filters.startTime) {
      requestBody.start_time = formatDateTime(filters.startTime)
    }
    if (filters.endTime) {
      requestBody.end_time = formatDateTime(filters.endTime)
    }
    if (filters.clusters.length > 0) {
      requestBody.cluster_names = filters.clusters
    }
    if (filters.hosts.length > 0) {
      requestBody.host_names = filters.hosts
    }
    if (filters.faultCodes.length > 0) {
      requestBody.err_codes = filters.faultCodes
    }

    const result = await request<{
      total: number
      metrics: Record<string, ErrCodeMetricItem[]>
    }>('/log_failure_event_result/metrics/err_code', {
      method: 'POST',
      body: JSON.stringify(requestBody),
    })

    faultChartMetrics.value = result.metrics ?? {}
  } catch (error) {
    faultChartMetrics.value = {}
    faultChartError.value = error instanceof Error ? error.message : '加载故障码计数时序分布失败'
  } finally {
    isFaultChartLoading.value = false
  }
}

const formatDateTime = (value: string) => {
  if (!value) return undefined
  return `${value.replace('T', ' ')}:00`
}

const listLogKbs = async (body: Record<string, unknown>) => {
  const result = await request<{ total: number; kbs: LogKnowledge[] }>('/log_kb/list', {
    method: 'POST',
    body: JSON.stringify({
      page_cnt: assetPageSize,
      page_num: 1,
      ...body,
    }),
  })

  return {
    total: result.total ?? 0,
    assets: (result.kbs ?? []).filter((asset) => asset.existed_status !== false),
  }
}

const extractListItems = <T,>(payload: unknown, keys: string[]) => {
  if (Array.isArray(payload)) return payload as T[]
  if (!payload || typeof payload !== 'object') return []

  const record = payload as Record<string, unknown>
  for (const key of keys) {
    if (Array.isArray(record[key])) return record[key] as T[]
  }

  const firstArray = Object.values(record).find(Array.isArray)
  return (firstArray ?? []) as T[]
}

const listAll = async <T,>(path: string, keys: string[], body: Record<string, unknown> = {}) => {
  const result = await request<unknown>(path, {
    method: 'POST',
    body: JSON.stringify({
      page_cnt: 10000,
      page_num: 1,
      created_sorted_desc: false,
      ...body,
    }),
  })

  return extractListItems<T>(result, keys)
}

const loadLatencyResults = async () => {
  if (!selectedAssetId.value) {
    latencyResults.value = []
    isLatencyResultsLoading.value = false
    return
  }

  const assetId = selectedAssetId.value
  isLatencyResultsLoading.value = true

  try {
    latencyResults.value = await listAll<LogParseResultModel>(
      '/log_parse_result/list',
      ['log_parse_results', 'log_parse_result', 'results', 'items', 'list'],
      {
        kb_id: assetId,
      },
    )
  } catch {
    latencyResults.value = []
  } finally {
    isLatencyResultsLoading.value = false
  }
}

const loadLatencyChart = async () => {
  if (!selectedAssetId.value) {
    latencyPercentileOptions.forEach((option) => {
      latencyMetricsByPercentile[option.value] = []
    })
    latencyChartError.value = ''
    isLatencyChartLoading.value = false
    return
  }

  const assetId = selectedAssetId.value
  isLatencyChartLoading.value = true
  latencyChartError.value = ''

  try {
    const results = await Promise.all(
      latencyPercentileOptions.map(async (option) => {
        const result = await request<{ total: number; metrics: LatencyMetricItem[] }>(
          '/log_parse_result/metrics/latency',
          {
            method: 'POST',
            body: JSON.stringify({
              kb_id: assetId,
              max_points: 1000,
              sample_mode: latencySampleModeMap[option.value],
              sort_by: 'timestamp',
              sort_order: 'asc',
            }),
          },
        )

        return {
          percentile: option.value,
          metrics: result.metrics ?? [],
        }
      }),
    )

    results.forEach((result) => {
      latencyMetricsByPercentile[result.percentile] = result.metrics
    })
  } catch (error) {
    latencyPercentileOptions.forEach((option) => {
      latencyMetricsByPercentile[option.value] = []
    })
    latencyChartError.value = error instanceof Error ? error.message : '加载延迟趋势失败'
  } finally {
    isLatencyChartLoading.value = false
  }
}

const loadDetailLatencyChart = async (row: LatencyDetailRow) => {
  if (!selectedAssetId.value) {
    detailLatencyMetrics.value = []
    detailLatencyChartError.value = ''
    isDetailLatencyChartLoading.value = false
    return
  }

  const assetId = selectedAssetId.value
  isDetailLatencyChartLoading.value = true
  detailLatencyChartError.value = ''
  detailLatencyMetrics.value = []

  try {
    const result = await request<{ total: number; metrics: LatencyMetricItem[] }>(
      '/log_parse_result/metrics/latency',
      {
        method: 'POST',
        body: JSON.stringify({
          kb_id: assetId,
          src_ip: row.sourceHost === '-' ? undefined : row.sourceHost,
          dst_ip: row.targetHost === '-' ? undefined : row.targetHost,
          max_points: 30,
          sort_by: 'timestamp',
          sort_order: 'asc',
        }),
      },
    )
    if (selectedAggregatedEvent.value?.id === row.id) {
      detailLatencyMetrics.value = result.metrics ?? []
    }
  } catch (error) {
    if (selectedAggregatedEvent.value?.id === row.id) {
      detailLatencyMetrics.value = []
      detailLatencyChartError.value =
        error instanceof Error ? error.message : '加载明细延迟趋势失败'
    }
  } finally {
    if (selectedAggregatedEvent.value?.id === row.id) {
      isDetailLatencyChartLoading.value = false
    }
  }
}

const loadDetailParseResults = async (
  row: LatencyDetailRow,
  pageNum = detailParseResultsPage.value,
) => {
  if (!selectedAssetId.value) {
    detailParseResults.value = []
    detailParseResultsTotal.value = 0
    detailParseResultsError.value = ''
    isDetailParseResultsLoading.value = false
    detailParseResultSort.releaseSortLock()
    return
  }

  const assetId = selectedAssetId.value
  isDetailParseResultsLoading.value = true
  detailParseResultsError.value = ''

  try {
    // 构建排序参数
    const sortFields = detailParseResultSort.getSortFields.value
    
    const result = await request<{ total: number; log_parse_results: LogParseResultModel[] }>(
      '/log_parse_result/list',
      {
        method: 'POST',
        body: JSON.stringify({
          kb_id: assetId,
          aggregated_event_id: row.id,
          src_ip: row.sourceHost === '-' ? undefined : row.sourceHost,
          dst_ip: row.targetHost === '-' ? undefined : row.targetHost,
          page_cnt: 20,
          page_num: pageNum,
          sort_fields: sortFields.length > 0 ? sortFields : undefined,
          is_anomalous: true,
        }),
        signal: detailParseResultSort.getAbortSignal(),
      },
    )

    if (selectedAggregatedEvent.value?.id === row.id) {
      detailParseResults.value = result.log_parse_results ?? []
      detailParseResultsTotal.value = result.total ?? detailParseResults.value.length
      detailParseResultsPage.value = pageNum
    }
  } catch (error) {
    // 忽略取消请求的错误
    if (error instanceof DOMException && error.name === 'AbortError') {
      return
    }
    if (selectedAggregatedEvent.value?.id === row.id) {
      detailParseResults.value = []
      detailParseResultsTotal.value = 0
      detailParseResultsPage.value = pageNum
      detailParseResultsError.value = error instanceof Error ? error.message : '加载解析结果失败'
    }
  } finally {
    if (selectedAggregatedEvent.value?.id === row.id) {
      isDetailParseResultsLoading.value = false
    }
    detailParseResultSort.releaseSortLock()
  }
}

const normalizePageInput = (value: string, pageCount: number) => {
  const nextPage = Number.parseInt(value, 10)
  if (!Number.isFinite(nextPage)) return null
  return Math.min(Math.max(1, nextPage), pageCount)
}

const goDetailParseResultsPage = (pageNum: number) => {
  const row = selectedAggregatedEvent.value
  if (!row) return
  const nextPage = Math.min(Math.max(1, pageNum), detailParseResultsPageCount.value)
  if (nextPage === detailParseResultsPage.value || isDetailParseResultsLoading.value) return
  void loadDetailParseResults(row, nextPage)
}

const jumpDetailParseResultsPage = () => {
  const nextPage = normalizePageInput(
    detailParseResultsPageInput.value,
    detailParseResultsPageCount.value,
  )
  if (nextPage === null) return
  detailParseResultsPageInput.value = ''
  goDetailParseResultsPage(nextPage)
}

const goFaultDetailTraceEventsPage = (pageNum: number) => {
  const detail = selectedFaultAggregatedEventDetail.value
  if (!detail) return
  const nextPage = Math.min(Math.max(1, pageNum), faultDetailTraceEventsPageCount.value)
  if (nextPage === faultDetailTraceEventsPage.value || isFaultDetailTraceEventsLoading.value)
    return
  void loadFaultAggregatedEventDetailTraceEvents(detail, nextPage)
}

const jumpFaultDetailTraceEventsPage = () => {
  const nextPage = normalizePageInput(
    faultDetailTraceEventsPageInput.value,
    faultDetailTraceEventsPageCount.value,
  )
  if (nextPage === null) return
  faultDetailTraceEventsPageInput.value = ''
  goFaultDetailTraceEventsPage(nextPage)
}

const loadLatencyDetail = async (pageNum = aggregateEventPage.value) => {
  if (!selectedAssetId.value) {
    aggregatedEvents.value = []
    aggregateEventTotal.value = 0
    aggregateEventPage.value = 1
    latencyDetailError.value = ''
    isLatencyDetailLoading.value = false
    return
  }

  const assetId = selectedAssetId.value
  isLatencyDetailLoading.value = true
  latencyDetailError.value = ''

  try {
    const filters = appliedFilters.value
    
    // 构建排序参数
    const sortFields = aggregateEventSort.getSortFields.value
    
    // 根据选择的统计类型映射排序字段
    const statType = selectedLatencyStat.value === 'total' ? 'p99' : selectedLatencyStat.value
    
    const result = await request<unknown>('/aggregated_event/list', {
      method: 'POST',
      body: JSON.stringify({
        kb_id: assetId,
        page_num: pageNum,
        page_cnt: 10,
        stat_type: statType,
        sort_fields: sortFields.length > 0 ? sortFields : undefined,
        src_ip: getLogParseFilterValue(filters.sourceHosts),
        dst_ip: getLogParseFilterValue(filters.targetHosts),
      }),
      signal: aggregateEventSort.getAbortSignal(),
    })
    const events = extractListItems<AggregatedEventModel>(result, [
      'aggregated_events',
      'aggregated_event',
      'events',
      'items',
      'list',
    ])
    const total =
      result && typeof result === 'object'
        ? ((result as Record<string, unknown>).total as number | undefined)
        : undefined
    const nextTotal = total ?? events.length
    const nextPageCount = Math.max(1, Math.ceil(nextTotal / 10))

    if (pageNum > nextPageCount) {
      isLatencyDetailLoading.value = false
      aggregateEventSort.releaseSortLock()
      await loadLatencyDetail(nextPageCount)
      return
    }

    aggregatedEvents.value = events
    aggregateEventTotal.value = nextTotal
    aggregateEventPage.value = pageNum
  } catch (error) {
    // 忽略取消请求的错误
    if (error instanceof DOMException && error.name === 'AbortError') {
      return
    }
    aggregatedEvents.value = []
    aggregateEventTotal.value = 0
    aggregateEventPage.value = 1
    latencyDetailError.value = error instanceof Error ? error.message : '加载聚合事件失败'
  } finally {
    isLatencyDetailLoading.value = false
    aggregateEventSort.releaseSortLock()
  }
}

const goAggregateEventPage = (pageNum: number) => {
  const nextPage = Math.min(Math.max(1, pageNum), aggregateEventPageCount.value)
  if (nextPage === aggregateEventPage.value || isLatencyDetailLoading.value) return
  void loadLatencyDetail(nextPage)
}

const jumpAggregateEventPage = () => {
  const nextPage = normalizePageInput(aggregateEventPageInput.value, aggregateEventPageCount.value)
  if (nextPage === null) return
  aggregateEventPageInput.value = ''
  goAggregateEventPage(nextPage)
}

const toAbnormalTraceRow = (result: LogParseResultModel): AbnormalTraceRow => {
  const record = result as Record<string, unknown>
  return {
    id: result.id,
    logStatus: getLogDisplayStatus(record),
    statusReason: getLogDisplayReason(record),
    time: result.timestamp ?? result.created_at ?? '-',
    traceId: result.trace_id ?? '-',
    podIp: result.pod_ip ?? '-',
    operation: normalizeTraceOperation(
      getRecordString(record, ['operation', 'op_type', 'operation_type', 'method']),
    ),
    clusterName: getRecordString(record, ['cluster_name'], 'null'),
    host: getRecordString(record, ['host'], 'null'),
    totalLatency: getRecordNullableNumber(record, ['total_latency']),
    queryMetaLatency: getRecordNullableNumber(record, ['worker_query_meta_latency']),
    urmaTotalLatency: getRecordNullableNumber(record, ['urma_total_latency']),
    urmaLinkLatency: getRecordNullableNumber(record, ['urma_link_latency']),
    c2wUrmaLatency: getRecordNullableNumber(record, ['c2w_urma_latency']),
    w2wUrmaLatency: getRecordNullableNumber(record, ['w2w_urma_latency']),
    sdkProcess: getRecordNullableNumber(record, ['sdk_process']),
    sdkRpc: getRecordNullableNumber(record, ['sdk_rpc']),
    localWorkerCost: getRecordNullableNumber(record, ['local_worker_cost']),
    localWorkerLock: getRecordNullableNumber(record, ['local_worker_lock']),
    remoteWorkerCost: getRecordNullableNumber(record, ['remote_worker_cost']),
    remoteWorkerRpc: getRecordNullableNumber(record, ['remote_worker_rpc']),
    masterProcess: getRecordNullableNumber(record, ['master_process']),
    masterRpcTotal: getRecordNullableNumber(record, ['master_rpc_total']),
    raw: result,
  }
}

const loadAbnormalTraceFilterOptions = async () => {
  if (!selectedAssetId.value) {
    abnormalTraceFilterDialog.clusters = []
    abnormalTraceFilterDialog.hosts = []
    abnormalTraceFilterDialog.error = ''
    abnormalTraceFilterDialog.isLoading = false
    return
  }

  const assetId = selectedAssetId.value
  abnormalTraceFilterDialog.isLoading = true
  abnormalTraceFilterDialog.error = ''

  try {
    const result = await request<LogParseOptions>(
      `/log_parse_result/options?kb_id=${encodeURIComponent(assetId)}`,
    )
    abnormalTraceFilterDialog.clusters = [...new Set(result.clusters ?? [])].filter(Boolean)
    abnormalTraceFilterDialog.hosts = [...new Set(result.hosts ?? [])].filter(Boolean)
  } catch (error) {
    abnormalTraceFilterDialog.clusters = []
    abnormalTraceFilterDialog.hosts = []
    abnormalTraceFilterDialog.error =
      error instanceof Error ? error.message : '加载集群/主机选项失败'
  } finally {
    abnormalTraceFilterDialog.isLoading = false
  }
}

const openAbnormalTraceFilterDialog = () => {
  abnormalTraceFilterDialog.open = true
  abnormalTraceFilterDialog.selectedClusterName = globalFilters.clusters[0] ?? ''
  abnormalTraceFilterDialog.selectedHost = globalFilters.hosts[0] ?? ''
  void loadAbnormalTraceFilterOptions()
}

const closeAbnormalTraceFilterDialog = () => {
  abnormalTraceFilterDialog.open = false
}

const confirmAbnormalTraceFilterDialog = () => {
  if (abnormalTraceFilterDialog.selectedClusterName) {
    setSingleFilterItem('cluster', abnormalTraceFilterDialog.selectedClusterName)
  }
  if (abnormalTraceFilterDialog.selectedHost) {
    setSingleFilterItem('host', abnormalTraceFilterDialog.selectedHost)
  }
  closeAbnormalTraceFilterDialog()
}

const getLogParseFilterValue = (values: string[]) => {
  if (values.length === 0) return undefined
  return values[0]
}

const loadAbnormalTraces = async (pageNum = abnormalTracesPage.value) => {
  if (!selectedAssetId.value) {
    abnormalTraceRows.value = []
    abnormalTracesTotal.value = 0
    abnormalTracesPage.value = 1
    abnormalTracesError.value = ''
    isAbnormalTracesLoading.value = false
    return
  }

  const assetId = selectedAssetId.value
  isAbnormalTracesLoading.value = true
  abnormalTracesError.value = ''

  try {
    const filters = appliedFilters.value
    
    // 构建排序参数
    const sortFields = abnormalTraceSort.getSortFields.value
    
    const body: Record<string, unknown> = {
      kb_id: assetId,
      page_cnt: abnormalTracesPageSize,
      page_num: pageNum,
      sort_fields: sortFields.length > 0 ? sortFields : undefined,
      is_anomalous: true,
      created_at_start: formatDateTime(filters.startTime),
      created_at_end: formatDateTime(filters.endTime),
      cluster_name: getLogParseFilterValue(filters.clusters),
      host: getLogParseFilterValue(filters.hosts),
    }

    const result = await request<{ total: number; log_parse_results: LogParseResultModel[] }>(
      '/log_parse_result/list',
      {
        method: 'POST',
        body: JSON.stringify(body),
        signal: abnormalTraceSort.getAbortSignal(),
      },
    )
    const total = result.total ?? 0
    const pageCount = Math.max(1, Math.ceil(total / abnormalTracesPageSize))

    if (pageNum > pageCount) {
      isAbnormalTracesLoading.value = false
      abnormalTraceSort.releaseSortLock()
      await loadAbnormalTraces(pageCount)
      return
    }

    abnormalTraceRows.value = (result.log_parse_results ?? []).map(toAbnormalTraceRow)
    abnormalTracesTotal.value = total
    abnormalTracesPage.value = pageNum
  } catch (error) {
    // 忽略取消请求的错误
    if (error instanceof DOMException && error.name === 'AbortError') {
      return
    }
    abnormalTraceRows.value = []
    abnormalTracesTotal.value = 0
    abnormalTracesPage.value = 1
    abnormalTracesError.value = error instanceof Error ? error.message : '加载时延异常列表失败'
  } finally {
    isAbnormalTracesLoading.value = false
    abnormalTraceSort.releaseSortLock()
  }
}

const goAbnormalTracesPage = (pageNum: number) => {
  const nextPage = Math.min(Math.max(1, pageNum), abnormalTracesPageCount.value)
  if (nextPage === abnormalTracesPage.value || isAbnormalTracesLoading.value) return
  void loadAbnormalTraces(nextPage)
}

const jumpAbnormalTracesPage = () => {
  const nextPage = normalizePageInput(abnormalTracesPageInput.value, abnormalTracesPageCount.value)
  if (nextPage === null) return
  abnormalTracesPageInput.value = ''
  goAbnormalTracesPage(nextPage)
}

const applyFaultAggregatedEventResult = (
  result: ListTimeAggregatedFailureEventMsg,
  pageNum: number,
) => {
  expandedFaultAggregatedEventId.value = ''
  faultAggregatedEventPodRowsByEventId.value = {}
  faultAggregatedEventPodTotalsByEventId.value = {}
  faultAggregatedEventPodPagesByEventId.value = {}
  faultAggregatedEventPodPageInputsByEventId.value = {}
  faultAggregatedEventPodErrors.value = {}
  loadingFaultAggregatedEventPodIds.value = new Set()
  faultAggregatedEventCodes.value = result.err_codes ?? []
  faultAggregatedEventRows.value = toFaultAggregatedEventRows(result.events ?? [])
  faultAggregatedEventTotal.value = result.total ?? 0
  faultAggregatedEventPage.value = pageNum
}

const toFaultAggregatedEventPodRows = (
  eventId: string,
  events: PodAggregatedFailureEventModel[],
): FaultAggregatedEventPodRow[] =>
  events.map((event, index) => ({
    id: `${eventId}-pod-api-${event.pod_name || index}`,
    podIp: event.pod_name || '-',
    faultCodeCounts: event.status_code_cnt ?? {},
  }))

const loadFaultAggregatedEventPodRows = async (row: FaultAggregatedEventRow, pageNum = 1) => {
  if (!selectedAssetId.value) {
    faultAggregatedEventPodRowsByEventId.value = {
      ...faultAggregatedEventPodRowsByEventId.value,
      [row.id]: [],
    }
    faultAggregatedEventPodTotalsByEventId.value = {
      ...faultAggregatedEventPodTotalsByEventId.value,
      [row.id]: 0,
    }
    faultAggregatedEventPodPagesByEventId.value = {
      ...faultAggregatedEventPodPagesByEventId.value,
      [row.id]: 1,
    }
    faultAggregatedEventPodErrors.value = {
      ...faultAggregatedEventPodErrors.value,
      [row.id]: '',
    }
    return
  }

  loadingFaultAggregatedEventPodIds.value = new Set([
    ...loadingFaultAggregatedEventPodIds.value,
    row.id,
  ])
  faultAggregatedEventPodErrors.value = {
    ...faultAggregatedEventPodErrors.value,
    [row.id]: '',
  }

  try {
    const sortFields = faultAggregatedEventPodSort.getSortFields.value
    const result = await request<ListPodAggregatedFailureEventMsg>(
      '/log_failure_event_result/list_pod_aggregated_failure_events',
      {
        method: 'POST',
        body: JSON.stringify({
          kb_id: selectedAssetId.value,
          created_at_start: row.startTime,
          created_at_end: row.endTime,
          sort_fields: sortFields.length > 0 ? sortFields : undefined,
          sort_by: 'all',
          created_sorted_desc: true,
          page_cnt: faultAggregatedEventPodPageSize,
          page_num: pageNum,
        }),
      },
    )

    const total = result.total ?? 0
    const pageCount = Math.max(1, Math.ceil(total / faultAggregatedEventPodPageSize))
    if (pageNum > pageCount) {
      await loadFaultAggregatedEventPodRows(row, pageCount)
      return
    }

    if ((result.total ?? 0) === 0 || (result.events ?? []).length === 0) {
      faultAggregatedEventPodRowsByEventId.value = {
        ...faultAggregatedEventPodRowsByEventId.value,
        [row.id]: [],
      }
      faultAggregatedEventPodTotalsByEventId.value = {
        ...faultAggregatedEventPodTotalsByEventId.value,
        [row.id]: total,
      }
      faultAggregatedEventPodPagesByEventId.value = {
        ...faultAggregatedEventPodPagesByEventId.value,
        [row.id]: pageNum,
      }
      faultAggregatedEventPodErrors.value = {
        ...faultAggregatedEventPodErrors.value,
        [row.id]: '',
      }
      return
    }

    faultAggregatedEventPodRowsByEventId.value = {
      ...faultAggregatedEventPodRowsByEventId.value,
      [row.id]: toFaultAggregatedEventPodRows(row.id, result.events ?? []),
    }
    faultAggregatedEventPodTotalsByEventId.value = {
      ...faultAggregatedEventPodTotalsByEventId.value,
      [row.id]: total,
    }
    faultAggregatedEventPodPagesByEventId.value = {
      ...faultAggregatedEventPodPagesByEventId.value,
      [row.id]: pageNum,
    }
  } catch (error) {
    faultAggregatedEventPodRowsByEventId.value = {
      ...faultAggregatedEventPodRowsByEventId.value,
      [row.id]: [],
    }
    faultAggregatedEventPodTotalsByEventId.value = {
      ...faultAggregatedEventPodTotalsByEventId.value,
      [row.id]: 0,
    }
    faultAggregatedEventPodPagesByEventId.value = {
      ...faultAggregatedEventPodPagesByEventId.value,
      [row.id]: pageNum,
    }
    faultAggregatedEventPodErrors.value = {
      ...faultAggregatedEventPodErrors.value,
      [row.id]: error instanceof Error ? error.message : 'Pod聚合接口加载失败',
    }
  } finally {
    const nextLoadingIds = new Set(loadingFaultAggregatedEventPodIds.value)
    nextLoadingIds.delete(row.id)
    loadingFaultAggregatedEventPodIds.value = nextLoadingIds
  }
}

const toggleFaultAggregatedEventRow = (row: FaultAggregatedEventRow) => {
  const willExpand = !isFaultAggregatedEventExpanded(row)
  expandedFaultAggregatedEventId.value = willExpand ? row.id : ''
  if (willExpand) {
    void loadFaultAggregatedEventPodRows(row, 1)
  }
}

const goFaultAggregatedEventPodPage = (row: FaultAggregatedEventRow, pageNum: number) => {
  const nextPage = Math.min(Math.max(1, pageNum), getFaultAggregatedEventPodPageCount(row))
  if (
    nextPage === getFaultAggregatedEventPodPage(row) ||
    isFaultAggregatedEventPodLoading(row)
  )
    return
  void loadFaultAggregatedEventPodRows(row, nextPage)
}

const jumpFaultAggregatedEventPodPage = (row: FaultAggregatedEventRow) => {
  const nextPage = normalizePageInput(
    getFaultAggregatedEventPodPageInput(row),
    getFaultAggregatedEventPodPageCount(row),
  )
  if (nextPage === null) return
  setFaultAggregatedEventPodPageInput(row, '')
  goFaultAggregatedEventPodPage(row, nextPage)
}

const loadFaultAggregatedEvents = async (pageNum = faultAggregatedEventPage.value) => {
  if (!selectedAssetId.value) {
    faultAggregatedEventsError.value = ''
    applyFaultAggregatedEventResult(
      {
        total: 0,
        err_codes: [],
        events: [],
      },
      1,
    )
    faultAggregatedEventSort.releaseSortLock()
    return
  }

  isFaultAggregatedEventsLoading.value = true
  faultAggregatedEventsError.value = ''

  try {
    const filters = appliedFilters.value
    const sortFields = faultAggregatedEventSort.getSortFields.value
    const requestBody: Record<string, unknown> = {
      kb_id: selectedAssetId.value,
      interval: selectedFaultAggregateInterval.value,
      sort_fields: sortFields.length > 0 ? sortFields : undefined,
      sort_by: 'timestamp',
      created_sorted_desc: false,
      page_cnt: faultAggregatedEventPageSize,
      page_num: pageNum,
    }

    if (filters.startTime) {
      requestBody.created_at_start = formatDateTime(filters.startTime)
    }
    if (filters.endTime) {
      requestBody.created_at_end = formatDateTime(filters.endTime)
    }

    const result = await request<ListTimeAggregatedFailureEventMsg>(
      '/log_failure_event_result/list_time_aggregated_failure_events',
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
        signal: faultAggregatedEventSort.getAbortSignal(),
      },
    )
    const nextTotal = result.total ?? 0
    if (nextTotal === 0 || (result.events ?? []).length === 0) {
      applyFaultAggregatedEventResult(
        {
          total: nextTotal,
          err_codes: result.err_codes ?? [],
          events: [],
        },
        pageNum,
      )
      return
    }

    const nextPageCount = Math.max(1, Math.ceil(nextTotal / faultAggregatedEventPageSize))

    if (pageNum > nextPageCount) {
      isFaultAggregatedEventsLoading.value = false
      faultAggregatedEventSort.releaseSortLock()
      await loadFaultAggregatedEvents(nextPageCount)
      return
    }

    applyFaultAggregatedEventResult(result, pageNum)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return
    }
    faultAggregatedEventsError.value =
      error instanceof Error ? error.message : '加载聚合事件失败'
    applyFaultAggregatedEventResult(
      {
        total: 0,
        err_codes: [],
        events: [],
      },
      1,
    )
  } finally {
    isFaultAggregatedEventsLoading.value = false
    faultAggregatedEventSort.releaseSortLock()
  }
}

const goFaultAggregatedEventPage = (pageNum: number) => {
  const nextPage = Math.min(Math.max(1, pageNum), faultAggregatedEventPageCount.value)
  if (nextPage === faultAggregatedEventPage.value || isFaultAggregatedEventsLoading.value) return
  void loadFaultAggregatedEvents(nextPage)
}

const jumpFaultAggregatedEventPage = () => {
  const nextPage = normalizePageInput(
    faultAggregatedEventPageInput.value,
    faultAggregatedEventPageCount.value,
  )
  if (nextPage === null) return
  faultAggregatedEventPageInput.value = ''
  goFaultAggregatedEventPage(nextPage)
}

const changeFaultAggregateInterval = () => {
  faultAggregatedEventPageInput.value = ''
  void loadFaultAggregatedEvents(1)
}

const goFaultTraceEventsPage = (pageNum: number) => {
  const nextPage = Math.min(Math.max(1, pageNum), faultTraceEventsPageCount.value)
  if (nextPage === faultTraceEventsPage.value || isFaultTraceEventsLoading.value) return
  void loadFaultTraceEvents(nextPage)
}

const jumpFaultTraceEventsPage = () => {
  const nextPage = normalizePageInput(
    faultTraceEventsPageInput.value,
    faultTraceEventsPageCount.value,
  )
  if (nextPage === null) return
  faultTraceEventsPageInput.value = ''
  goFaultTraceEventsPage(nextPage)
}

const loadAssets = async (pageNum = assetPage.value) => {
  isListLoading.value = true
  errorMessage.value = ''

  try {
    const result = await listLogKbs({
      page_num: pageNum,
      created_sorted_desc: true,
    })
    const nextTotal = result.total
    const nextPageCount = Math.max(1, Math.ceil(nextTotal / assetPageSize))

    if (pageNum > nextPageCount) {
      isListLoading.value = false
      await loadAssets(nextPageCount)
      return
    }

    assets.value = result.assets
    assetTotal.value = nextTotal
    assetPage.value = pageNum
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '资产库列表加载失败'
  } finally {
    isListLoading.value = false
  }
}

const goAssetPage = (pageNum: number) => {
  const nextPage = Math.min(Math.max(1, pageNum), assetPageCount.value)
  if (nextPage === assetPage.value || isListLoading.value) return
  void loadAssets(nextPage)
}

const jumpAssetPage = () => {
  const nextPage = normalizePageInput(assetPageInput.value, assetPageCount.value)
  if (nextPage === null) return
  assetPageInput.value = ''
  goAssetPage(nextPage)
}

const loadAssetDetail = async (assetId: string) => {
  activePage.value = 'asset'
  selectedAssetId.value = assetId
  selectedAsset.value = null
  selectedTrace.value = null
  selectedFaultTrace.value = null
  faultTraceRows.value = []
  faultTraceEventsTotal.value = 0
  faultTraceEventsPage.value = 1
  faultTraceEventsPageInput.value = ''
  faultTraceEventsError.value = ''
  traceFailureLogsByTrace.value = {}
  traceFailureEventsByTrace.value = {}
  traceLogsError.value = ''
  logFilesPage.value = 1
  logFilesPageInput.value = ''
  isDetailLoading.value = true
  errorMessage.value = ''

  try {
    const result = await request<{ kb: LogKnowledge | null }>(`/log_kb/${assetId}`)
    selectedAsset.value = result.kb
    await loadLogFiles(assetId, 1)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '资产库详情加载失败'
  } finally {
    isDetailLoading.value = false
  }
}

const openQueryDialog = () => {
  queryDialog.name = ''
  queryDialog.description = ''
  queryDialog.createdAtStart = ''
  queryDialog.createdAtEnd = ''
  queryDialog.sortOrder = 'desc'
  queryDialog.error = ''
  queryDialog.open = true
}

const closeQueryDialog = () => {
  if (isQuerying.value) return
  queryDialog.open = false
}

const submitQuery = async () => {
  isQuerying.value = true
  queryDialog.error = ''

  try {
    const result = await listLogKbs({
      name: queryDialog.name.trim() || undefined,
      description: queryDialog.description.trim() || undefined,
      created_at_start: formatDateTime(queryDialog.createdAtStart),
      created_at_end: formatDateTime(queryDialog.createdAtEnd),
      created_sorted_desc: queryDialog.sortOrder === 'desc',
    })
    resultsDialog.assets = result.assets
    queryDialog.open = false
    resultsDialog.open = true
  } catch (error) {
    queryDialog.error = error instanceof Error ? error.message : '查询资产库失败'
  } finally {
    isQuerying.value = false
  }
}

const viewQueryResult = async (assetId: string) => {
  resultsDialog.open = false
  await loadAssetDetail(assetId)
}

const openCreateDialog = () => {
  dialog.mode = 'create'
  dialog.name = ''
  dialog.description = ''
  dialog.error = ''
  dialog.open = true
}

const openEditDialog = () => {
  if (!selectedAsset.value) return

  dialog.mode = 'edit'
  dialog.name = selectedAsset.value.name
  dialog.description = selectedAsset.value.description
  dialog.error = ''
  dialog.open = true
}

const closeDialog = () => {
  if (isSaving.value) return
  dialog.open = false
}

const saveDialog = async () => {
  const name = dialog.name.trim()
  const description = dialog.description.trim()

  if (!name) {
    dialog.error = '请填写资产库名称'
    return
  }
  if (!description) {
    dialog.error = '请填写资产库描述'
    return
  }

  isSaving.value = true
  errorMessage.value = ''
  dialog.error = ''

  try {
    if (dialog.mode === 'create') {
      await request('/log_kb', {
        method: 'POST',
        body: JSON.stringify({ name, description }),
      })
      selectedAssetId.value = null
      selectedAsset.value = null
    } else if (selectedAssetId.value) {
      await request(`/log_kb/${selectedAssetId.value}`, {
        method: 'PUT',
        body: JSON.stringify({ name, description }),
      })
      await loadAssetDetail(selectedAssetId.value)
    }

    dialog.open = false
    await loadAssets()
  } catch (error) {
    dialog.error = error instanceof Error ? error.message : '保存资产库失败'
  } finally {
    isSaving.value = false
  }
}

const deleteAsset = async (asset: LogKnowledge) => {
  const shouldDelete = window.confirm(`确认删除资产库「${asset.name}」？`)
  if (!shouldDelete) return

  errorMessage.value = ''

  try {
    const result = await request<{ kb_id: string | null }>(`/log_kb/${asset.id}`, {
      method: 'DELETE',
    })

    if (!result.kb_id) {
      throw new Error('删除资产库失败')
    }

    if (selectedAssetId.value === asset.id) {
      selectedAssetId.value = null
      selectedAsset.value = null
    }

    assets.value = assets.value.filter((item) => item.id !== asset.id)
    await loadAssets()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '删除资产库失败'
  }
}

const detectSourceType = (input: string): 'local' | 'remote' | null => {
  const trimmed = input.trim()
  if (/^https?:\/\//i.test(trimmed)) return 'remote'
  if (/^\/|^~\/|^[A-Za-z]:\\/i.test(trimmed)) return 'local'
  return null
}

const statusLabel = (s: string) => {
  if (!s) return '-'

  const map: Record<string, string> = {
    pending: '待解析',
    running: '解析中',
    cancelled: '已取消',
    successful: '解析成功',
    failed: '解析失败',
    successful_pending_remove: '解析成功，待移除',
    failed_pending_remove: '解析失败，待移除',
  }
  return map[s] || s
}

const statusBadgeClass = (s: string) => {
  const map: Record<string, string> = {
    pending: 'status-pending',
    running: 'status-running',
    cancelled: 'status-cancelled',
    successful: 'status-successful',
    failed: 'status-failed',
    successful_pending_remove: 'status-successful-pending-remove',
    failed_pending_remove: 'status-failed-pending-remove',
  }
  return map[s] || 'status-pending'
}

const getDetailedLogFileTask = (file: LogFileModel) =>
  file.task?.id ? (taskDetailsById.value[file.task.id] ?? file.task) : file.task

const getLogFileTaskStatus = (file: LogFileModel) =>
  getDetailedLogFileTask(file)?.status ?? file.parse_status ?? ''

const clampProgress = (value: number) => Math.min(100, Math.max(0, value))

const getTaskReportProgress = (report: TaskReportModel | null) => {
  if (!report) return null
  const value = report.progress
  if (typeof value === 'number' && Number.isFinite(value)) return clampProgress(value)
  if (typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) {
    return clampProgress(Number(value))
  }
  return null
}

const getTaskReportTime = (report: TaskReportModel) => {
  if (!report.created_at) return 0
  const time = Date.parse(report.created_at)
  return Number.isFinite(time) ? time : 0
}

const ignoredTaskReportPrefixes = ['[perf]', '[parse_log]', '[TASK]']
const logFileTaskMilestoneMessages = new Set([
  'Task initialized',
  'Task reinitialized',
  'Task running',
  'Log parse completed',
  'Anomaly detection done',
  'Aggregate events done',
  'Fault matching done',
  'Results stored',
  'Task completed successfully',
  '初始化任务',
  '重新初始化任务',
  '运行任务',
  '运行诊断工具',
  '诊断工具运行完成',
  '运行定界工具',
  '定界工具运行完成',
  '故障事件解析完成',
  'Trace故障解析完成',
  '任务成功',
])

const isIgnoredTaskReportMessage = (message: string) =>
  ignoredTaskReportPrefixes.some((prefix) => message.startsWith(prefix))

const isLogFileTaskMilestoneReport = (report: TaskReportModel) => {
  const message = report.message?.trim()
  if (!message || isIgnoredTaskReportMessage(message)) return false
  if (logFileTaskMilestoneMessages.has(message)) return true
  return message.startsWith('Trace context logs stored:')
}

const getLogFileTaskReports = (file: LogFileModel) =>
  getDetailedLogFileTask(file)?.task_reports ?? []

const getValidLogFileTaskReports = (file: LogFileModel) =>
  getLogFileTaskReports(file).filter(isLogFileTaskMilestoneReport)

const getLatestLogFileTaskReport = (file: LogFileModel) => {
  const reports = getValidLogFileTaskReports(file)
  if (reports.length === 0) return null
  return (
    [...reports].sort(
      (first, second) => getTaskReportTime(second) - getTaskReportTime(first),
    )[0] ?? null
  )
}

const getLogFileProgress = (file: LogFileModel) => {
  const validProgressValues = getValidLogFileTaskReports(file)
    .map(getTaskReportProgress)
    .filter((progress): progress is number => progress !== null)
  const maxReportProgress =
    validProgressValues.length > 0 ? Math.max(...validProgressValues) : null

  const status = getLogFileTaskStatus(file)
  if (status === 'successful' || status === 'successful_pending_remove') return 100
  if (maxReportProgress !== null) {
    return status === 'running' ? Math.max(5, maxReportProgress) : maxReportProgress
  }
  if (status === 'running') return 5
  return 0
}

const getLogFileProgressText = (file: LogFileModel) =>
  `${Math.round(getLogFileProgress(file))}%`

const getLogFileProgressMessage = (file: LogFileModel) => {
  const latestReport = getLatestLogFileTaskReport(file)
  const message = latestReport?.message?.trim()
  if (message) return message
  return statusLabel(getLogFileTaskStatus(file))
}

const shouldShowLogFileProgress = (file: LogFileModel) =>
  Boolean(file.task || getLogFileTaskStatus(file))

const getLogFileProgressClass = (file: LogFileModel) => {
  const status = getLogFileTaskStatus(file)
  if (status === 'failed' || status === 'failed_pending_remove') return 'failed'
  if (status === 'successful' || status === 'successful_pending_remove') return 'successful'
  if (status === 'cancelled') return 'cancelled'
  if (status === 'running') return 'running'
  return 'pending'
}

const getLogFileId = (file: LogFileModel) => file.log_file_id || file.id

const getUploadedLogFileIdForSource = (file: LogFileModel) => {
  const sourceKeys = [file.file_path, file.name].filter(Boolean)
  for (const sourceKey of sourceKeys) {
    const uploadedId = uploadedLogFileIdsBySource.value[sourceKey]
    if (uploadedId) return uploadedId
  }
  return ''
}

const normalizeLogFile = (file: LogFileModel): LogFileModel => {
  const logFileId = file.log_file_id || getUploadedLogFileIdForSource(file) || file.id
  return {
    ...file,
    log_file_id: logFileId,
    anomaly_cnt: logFileAnomalyCntById.value[logFileId] ?? file.anomaly_cnt,
    trace_failure_event_cnt:
      logFileTraceFailureEventCntById.value[logFileId] ?? file.trace_failure_event_cnt,
  }
}

const isSuccessfulLogFileTask = (file: LogFileModel) =>
  getLogFileTaskStatus(file) === 'successful'

const isLogFileDetailLoaded = (file: LogFileModel) =>
  loadedAnomalyLogFileIds.value.has(getLogFileId(file))

const getLogFileAnomalyCountText = (file: LogFileModel) =>
  `时延异常数：${file.anomaly_cnt}`

const getLogFileTraceFailureEventCountText = (file: LogFileModel) =>
  `通断故障数：${file.trace_failure_event_cnt ?? 0}`

const getLogFileAnomalyCountClass = (file: LogFileModel) => {
  if (!isLogFileDetailLoaded(file)) return ''
  return file.anomaly_cnt > 0 ? 'anomaly-danger' : 'anomaly-ok'
}

const getLogFileTraceFailureEventCountClass = (file: LogFileModel) => {
  if (!isLogFileDetailLoaded(file)) return ''
  return (file.trace_failure_event_cnt ?? 0) > 0 ? 'anomaly-danger' : 'anomaly-ok'
}

const updateLogFileInList = (logFile: LogFileModel) => {
  const logFileId = getLogFileId(logFile)
  logFiles.value = logFiles.value.map((file) => {
    if (getLogFileId(file) !== logFileId && file.id !== logFile.id) return file
    return normalizeLogFile({
      ...file,
      ...logFile,
      log_file_id: logFileId || getLogFileId(file),
    })
  })
}

const loadLogFileAnomalyCount = async (file: LogFileModel) => {
  const logFileId = getLogFileId(file)
  if (!logFileId || loadedAnomalyLogFileIds.value.has(logFileId)) return
  if (loadingAnomalyLogFileIds.value.has(logFileId)) return

  loadingAnomalyLogFileIds.value = new Set(loadingAnomalyLogFileIds.value).add(logFileId)
  try {
    const result = await request<GetLogFileResult>(`/log_file/${logFileId}`)
    if (result.log_file) {
      logFileAnomalyCntById.value = {
        ...logFileAnomalyCntById.value,
        [logFileId]: result.log_file.anomaly_cnt,
      }
      logFileTraceFailureEventCntById.value = {
        ...logFileTraceFailureEventCntById.value,
        [logFileId]: result.log_file.trace_failure_event_cnt ?? 0,
      }
      updateLogFileInList({
        ...result.log_file,
        log_file_id: logFileId,
      })
      loadedAnomalyLogFileIds.value = new Set(loadedAnomalyLogFileIds.value).add(logFileId)
    }
  } catch {
  } finally {
    const next = new Set(loadingAnomalyLogFileIds.value)
    next.delete(logFileId)
    loadingAnomalyLogFileIds.value = next
  }
}

const loadSuccessfulLogFileAnomalyCounts = (files: LogFileModel[]) => {
  files.forEach((file) => {
    if (isSuccessfulLogFileTask(file)) {
      void loadLogFileAnomalyCount(file)
    }
  })
}

const loadTaskDetail = async (taskId: string) => {
  if (!taskId || loadingTaskDetailIds.value.has(taskId)) return

  loadingTaskDetailIds.value = new Set(loadingTaskDetailIds.value).add(taskId)
  try {
    const result = await request<{ task: TaskModel | null }>(`/task/${taskId}`)
    if (result.task) {
      taskDetailsById.value = {
        ...taskDetailsById.value,
        [taskId]: result.task,
      }
    }
  } catch {
  } finally {
    const next = new Set(loadingTaskDetailIds.value)
    next.delete(taskId)
    loadingTaskDetailIds.value = next
  }
}

const loadTaskDetailsForLogFiles = (files: LogFileModel[]) => {
  const taskIds = new Set<string>()
  files.forEach((file) => {
    if (file.task?.id) {
      taskIds.add(file.task.id)
    }
  })
  taskIds.forEach((taskId) => {
    void loadTaskDetail(taskId)
  })
}

const loadLogFiles = async (
  kbId: string,
  pageNum = logFilesPage.value,
  options: { silent?: boolean } = {},
) => {
  if (!options.silent) {
    isLogFilesLoading.value = true
  }
  try {
    const result = await request<{ total: number; log_files: LogFileModel[] }>(
      `/log_file/list/${kbId}`,
      {
        method: 'POST',
        body: JSON.stringify({
          page_cnt: logFilesPageSize,
          page_num: pageNum,
          created_sorted_desc: true,
        }),
      },
    )
    const nextTotal = result.total ?? 0
    const nextPageCount = Math.max(1, Math.ceil(nextTotal / logFilesPageSize))

    if (pageNum > nextPageCount) {
      if (!options.silent) {
        isLogFilesLoading.value = false
      }
      await loadLogFiles(kbId, nextPageCount, options)
      return
    }

    const nextLogFiles = (result.log_files ?? [])
      .filter((f) => f.existed_status !== false)
      .map(normalizeLogFile)
    logFiles.value = nextLogFiles
    logFilesTotal.value = nextTotal
    logFilesPage.value = pageNum
    loadTaskDetailsForLogFiles(nextLogFiles)
    loadSuccessfulLogFileAnomalyCounts(nextLogFiles)
  } catch {
    if (!options.silent) {
      logFiles.value = []
      logFilesTotal.value = 0
      logFilesPage.value = 1
    }
  } finally {
    if (!options.silent) {
      isLogFilesLoading.value = false
    }
  }
}

const pollLogFiles = async () => {
  if (!selectedAssetId.value || activePage.value !== 'asset') return
  if (isLogFilesLoading.value || isLogFilesPolling.value) return

  isLogFilesPolling.value = true
  try {
    await loadLogFiles(selectedAssetId.value, logFilesPage.value, { silent: true })
  } finally {
    isLogFilesPolling.value = false
  }
}

const stopLogFilesPolling = () => {
  if (logFilesPollingTimer.value === null) return
  window.clearInterval(logFilesPollingTimer.value)
  logFilesPollingTimer.value = null
}

const startLogFilesPolling = () => {
  stopLogFilesPolling()
  if (!selectedAssetId.value || activePage.value !== 'asset') return
  logFilesPollingTimer.value = window.setInterval(() => {
    void pollLogFiles()
  }, logFilesPollIntervalMs)
}

const goLogFilesPage = (pageNum: number) => {
  if (!selectedAssetId.value) return
  const nextPage = Math.min(Math.max(1, pageNum), logFilesPageCount.value)
  if (nextPage === logFilesPage.value || isLogFilesLoading.value) return
  void loadLogFiles(selectedAssetId.value, nextPage)
}

const jumpLogFilesPage = () => {
  const nextPage = normalizePageInput(logFilesPageInput.value, logFilesPageCount.value)
  if (nextPage === null) return
  logFilesPageInput.value = ''
  goLogFilesPage(nextPage)
}

const toggleParse = async (fileId: string, run: boolean) => {
  togglingFileIds.value = new Set(togglingFileIds.value).add(fileId)
  try {
    await request(`/log_file/run/${fileId}?run=${run}`, { method: 'PUT' })
    await refreshLogFile(fileId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '操作失败'
  } finally {
    const next = new Set(togglingFileIds.value)
    next.delete(fileId)
    togglingFileIds.value = next
  }
}

const refreshLogFile = async (fileId: string) => {
  refreshingFileIds.value = new Set(refreshingFileIds.value).add(fileId)
  try {
    if (selectedAssetId.value) {
      await loadLogFiles(selectedAssetId.value, logFilesPage.value)
    }
  } catch {
  } finally {
    const next = new Set(refreshingFileIds.value)
    next.delete(fileId)
    refreshingFileIds.value = next
  }
}

const submitLogSource = async () => {
  const input = logSourceInput.value.trim()
  if (!input) return
  if (!selectedAssetId.value) return

  const sourceType = detectSourceType(input)
  if (!sourceType) {
    uploadLogError.value =
      '请输入有效的本地路径（如 /var/log/）或远程 URL（如 https://example.com/log.zip）'
    return
  }

  isUploadingLog.value = true
  uploadLogError.value = ''

  try {
    const result = await request<UploadLogFilesResult>(
      `/log_file/${selectedAssetId.value}`,
      {
        method: 'POST',
        body: JSON.stringify({
          upload_log_file_configs: [
            {
              name: input.split('/').pop() || input,
              source_type: sourceType,
              source: input,
            },
          ],
        }),
      },
    )
    const uploadedLogFileId = result.log_file_ids?.[0]
    if (uploadedLogFileId) {
      uploadedLogFileIdsBySource.value = {
        ...uploadedLogFileIdsBySource.value,
        [input]: uploadedLogFileId,
        [input.split('/').pop() || input]: uploadedLogFileId,
      }
    }
    logSourceInput.value = ''
  } catch (error) {
    uploadLogError.value = error instanceof Error ? error.message : '添加日志文件失败'
  } finally {
    isUploadingLog.value = false
    if (selectedAssetId.value) {
      await loadAssetDetail(selectedAssetId.value)
      await loadAssets()
    }
  }
}

const triggerFileUpload = () => {
  fileInputRef.value?.click()
}

const loadLatencyPage = async () => {
  const requests: Promise<void>[] = []

  if (!isLatencyChartLoading.value) {
    requests.push(loadLatencyChart())
  }
  if (!isLatencyDetailLoading.value) {
    requests.push(loadLatencyDetail())
  }
  if (!isAbnormalTracesLoading.value) {
    requests.push(loadAbnormalTraces())
  }

  await Promise.all(requests)
}

const loadFaultPage = async () => {
  const requests: Promise<void>[] = []

  if (!isFaultChartLoading.value) {
    requests.push(loadFaultChart())
  }
  if (!isFaultAggregatedEventsLoading.value) {
    requests.push(loadFaultAggregatedEvents(1))
  }
  if (!isFaultTraceEventsLoading.value) {
    requests.push(loadFaultTraceEvents(1))
  }

  await Promise.all(requests)
}

const loadAbnormalMonitorPage = async () => {
  if (isFaultCodeFeatureEnabled) {
    await Promise.all([loadLatencyPage(), loadFaultPage()])
    return
  }
  await loadLatencyPage()
}

const openMonitorPage = async (section: 'latency' | 'fault' = 'latency') => {
  if (!selectedAssetId.value) return
  const targetSection = isFaultCodeFeatureEnabled ? section : 'latency'
  const shouldLoadMonitorData = !isAbnormalMonitorPage.value

  if (shouldLoadMonitorData) {
    clearFilterApplyMessage()
  }
  activePage.value = 'abnormal'

  if (shouldLoadMonitorData) {
    await loadAbnormalMonitorPage()
  }

  await nextTick()
  document.getElementById(targetSection === 'fault' ? 'kv-fault' : 'kv-latency')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

const handleFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  if (!selectedAssetId.value) return

  isUploadingLog.value = true
  uploadLogError.value = ''

  try {
    const formData = new FormData()
    formData.append(
      'upload_log_file_configs',
      JSON.stringify([
        {
          name: file.name,
          source_type: 'upload',
          source: file.name,
        },
      ]),
    )
    formData.append('file', file)

    const response = await fetch(`${apiBase}/log_file/${selectedAssetId.value}`, {
      method: 'POST',
      body: formData,
    })

    const data = (await response.json().catch(() => null)) as
      | ApiResponse<UploadLogFilesResult>
      | null

    if (!response.ok || !data) {
      throw new Error(data?.message || `请求失败：${response.status}`)
    }

    if (typeof data.code === 'number' && data.code !== 200) {
      throw new Error(data.message || '接口返回异常')
    }

    const uploadedLogFileId = (data.result ?? data.data)?.log_file_ids?.[0]
    if (uploadedLogFileId) {
      uploadedLogFileIdsBySource.value = {
        ...uploadedLogFileIdsBySource.value,
        [file.name]: uploadedLogFileId,
      }
    }
  } catch (error) {
    uploadLogError.value = error instanceof Error ? error.message : '上传文件失败'
  } finally {
    isUploadingLog.value = false
    target.value = ''
    if (selectedAssetId.value) {
      await loadAssetDetail(selectedAssetId.value)
      await loadAssets()
    }
  }
}

const syncAggregateLatencyScroll = (event: Event) => {
  const source = event.currentTarget as HTMLElement | null
  const panel = source?.closest('.aggregate-latency-scroll')
  if (!source || !panel) return

  panel.querySelectorAll<HTMLElement>('.aggregate-latency-sync').forEach((target) => {
    if (target !== source && target.scrollLeft !== source.scrollLeft) {
      target.scrollLeft = source.scrollLeft
    }
  })
}

watch(
  [latencyChartBuckets, isLatencyChartLoading, latencyChartError, activePage, visibleLatencyKeys],
  () => {
    void nextTick(renderLatencyEchart)
  },
  { deep: true },
)

watch(
  [
    detailLatencyChartBuckets,
    isDetailLatencyChartLoading,
    detailLatencyChartError,
    selectedAggregatedEvent,
    visibleLatencyKeys,
  ],
  () => {
    void nextTick(renderDetailLatencyEchart)
  },
  { deep: true },
)

watch(
  [faultChartBuckets, faultCodes, isFaultChartLoading, faultChartError, activePage],
  () => {
    void nextTick(renderFaultEchart)
  },
  { deep: true },
)

watch(
  [
    faultDetailChartBuckets,
    selectedFaultDetailChartCodes,
    isFaultDetailChartLoading,
    faultDetailChartError,
    selectedFaultAggregatedEventDetail,
  ],
  () => {
    void nextTick(renderFaultDetailEchart)
  },
  { deep: true },
)

watch([selectedAssetId, activePage], () => {
  if (selectedAssetId.value && activePage.value === 'asset') {
    startLogFilesPolling()
  } else {
    stopLogFilesPolling()
  }
})

onMounted(() => {
  void loadAssets()
  window.addEventListener('resize', resizeLatencyCharts)
})

onBeforeUnmount(() => {
  stopLogFilesPolling()
  window.removeEventListener('resize', resizeLatencyCharts)
  latencyChartInstance?.dispose()
  detailLatencyChartInstance?.dispose()
  faultChartInstance?.dispose()
  faultDetailChartInstance?.dispose()
})
</script>

<template>
  <div class="app-layout">
    <aside class="asset-sidebar">
      <section class="nav-section">
        <div class="nav-title-row">
          <span class="nav-title">资产管理</span>
          <span class="nav-actions">
            <button
              class="icon-btn primary add-btn"
              type="button"
              title="添加资产库"
              aria-label="添加资产库"
              @click="openCreateDialog"
            ></button>
            <button
              class="icon-btn query-btn search-icon-btn"
              type="button"
              title="查询资产库"
              aria-label="查询资产库"
              @click="openQueryDialog"
            ></button>
          </span>
        </div>

        <div v-if="isListLoading" class="state-text">正在加载资产库...</div>
        <div v-else-if="assets.length === 0" class="state-text">暂无资产库</div>

        <div v-else class="nav-list">
          <div
            v-for="asset in assets"
            :key="asset.id"
            class="nav-asset-item"
            :class="{ selected: selectedAssetId === asset.id }"
            role="button"
            tabindex="0"
            @click="loadAssetDetail(asset.id)"
            @keydown.enter="loadAssetDetail(asset.id)"
            @keydown.space.prevent="loadAssetDetail(asset.id)"
          >
            <span class="asset-item-main">
              <strong>{{ asset.name }}</strong>
              <small>{{ asset.description }}</small>
            </span>
          </div>
        </div>
        <div v-if="assetTotal > assetPageSize" class="asset-pagination">
          <button
            class="asset-page-btn"
            type="button"
            :disabled="assetPage <= 1 || isListLoading"
            @click="goAssetPage(assetPage - 1)"
          >
            上一页
          </button>
          <span class="pagination-pages" aria-label="资产库页码">
            <button
              v-for="pageNum in assetPageWindow"
              :key="`asset-page-${pageNum}`"
              class="pagination-page-btn"
              :class="{ active: pageNum === assetPage }"
              type="button"
              :disabled="pageNum === assetPage || isListLoading"
              @click="goAssetPage(pageNum)"
            >
              {{ pageNum }}
            </button>
          </span>
          <button
            class="asset-page-btn"
            type="button"
            :disabled="assetPage >= assetPageCount || isListLoading"
            @click="goAssetPage(assetPage + 1)"
          >
            下一页
          </button>
          <span class="pagination-jump">
            <span>{{ assetPage }} / {{ assetPageCount }}</span>
            <input
              v-model="assetPageInput"
              class="pagination-jump-input"
              type="number"
              min="1"
              :max="assetPageCount"
              aria-label="跳转资产库页码"
              @keyup.enter="jumpAssetPage"
            />
            <button
              class="pagination-jump-btn"
              type="button"
              :disabled="isListLoading"
              @click="jumpAssetPage"
            >
              跳转
            </button>
          </span>
        </div>
      </section>

      <section class="nav-section monitor-nav-section">
        <div class="nav-title">章节导航</div>
        <div class="monitor-nav-list">
          <button
            v-if="isFaultCodeFeatureEnabled"
            class="monitor-nav-item"
            :class="{ disabled: !selectedAssetId }"
            type="button"
            :disabled="!selectedAssetId"
            @click="openMonitorPage('latency')"
          >
            📊 时延监控
          </button>
          <button
            class="monitor-nav-item"
            :class="{ disabled: !selectedAssetId }"
            type="button"
            :disabled="!selectedAssetId"
            @click="openMonitorPage('fault')"
          >
            ⚠️ 故障监控
          </button>
        </div>
      </section>

      <section class="filter-panel" aria-label="筛选条件">
        <div class="filter-header">
          <span>筛选条件</span>
          <button
            class="reset-category-btn reset-all-filter-btn"
            type="button"
            @click="resetAllFilters"
          >
            重置全部
          </button>
        </div>
        <div class="filter-scroll">
          <div v-if="shouldShowTraceListFilters" class="filter-section">
            <div class="filter-section-title">
              <span>🕒 按时间</span>
              <button class="reset-category-btn" type="button" @click="resetFilterCategory('time')">
                重置
              </button>
            </div>
            <div class="time-range-input">
              <label class="time-item">
                <span>起始时间</span>
                <input v-model="globalFilters.startTime" type="datetime-local" />
              </label>
              <label class="time-item">
                <span>终止时间</span>
                <input v-model="globalFilters.endTime" type="datetime-local" />
              </label>
            </div>
          </div>

          <div v-if="shouldShowTraceListFilters" class="filter-section">
            <div class="filter-section-title">
              <span>🏭 按集群</span>
              <button
                class="reset-category-btn"
                type="button"
                @click="resetFilterCategory('cluster')"
              >
                重置
              </button>
            </div>
            <div class="filter-entry-row">
              <input
                v-model="filterDraftInput.cluster"
                type="text"
                placeholder="输入集群名称"
                @keydown.enter.prevent="addFilterValue('cluster')"
              />
              <button type="button" @click="addFilterValue('cluster')">添加</button>
            </div>
            <div class="selected-tags">
              <span v-for="cluster in globalFilters.clusters" :key="cluster" class="filter-tag">
                {{ cluster }}
                <button
                  type="button"
                  class="remove-tag"
                  @click="removeFilterValue('cluster', cluster)"
                >
                  ×
                </button>
              </span>
              <span v-if="globalFilters.clusters.length === 0" class="empty-hint">
                未选择集群
              </span>
            </div>
          </div>

          <div v-if="shouldShowTraceListFilters" class="filter-section">
            <div class="filter-section-title">
              <span>🖥️ 按主机</span>
              <button class="reset-category-btn" type="button" @click="resetFilterCategory('host')">
                重置
              </button>
            </div>
            <div class="filter-entry-row">
              <input
                v-model="filterDraftInput.host"
                type="text"
                placeholder="输入主机 IP"
                @keydown.enter.prevent="addFilterValue('host')"
              />
              <button type="button" @click="addFilterValue('host')">添加</button>
            </div>
            <div class="selected-tags">
              <span v-for="host in globalFilters.hosts" :key="host" class="filter-tag">
                {{ host }}
                <button type="button" class="remove-tag" @click="removeFilterValue('host', host)">
                  ×
                </button>
              </span>
              <span v-if="globalFilters.hosts.length === 0" class="empty-hint">未选择主机</span>
            </div>
          </div>

          <div v-if="isLatencyEventListFilterMode" class="filter-section">
            <div class="filter-section-title">
              <span>⬅️ 按源IP</span>
              <button
                class="reset-category-btn"
                type="button"
                @click="resetFilterCategory('sourceHost')"
              >
                重置
              </button>
            </div>
            <div class="filter-entry-row">
              <input
                v-model="filterDraftInput.sourceHost"
                type="text"
                placeholder="输入源 IP"
                @keydown.enter.prevent="addFilterValue('sourceHost')"
              />
              <button type="button" @click="addFilterValue('sourceHost')">添加</button>
            </div>
            <div class="selected-tags">
              <span
                v-for="sourceHost in globalFilters.sourceHosts"
                :key="sourceHost"
                class="filter-tag"
              >
                {{ sourceHost }}
                <button
                  type="button"
                  class="remove-tag"
                  @click="removeFilterValue('sourceHost', sourceHost)"
                >
                  ×
                </button>
              </span>
              <span v-if="globalFilters.sourceHosts.length === 0" class="empty-hint"
                >未选择源IP</span
              >
            </div>
          </div>

          <div v-if="isLatencyEventListFilterMode" class="filter-section">
            <div class="filter-section-title">
              <span>➡️ 按目标IP</span>
              <button
                class="reset-category-btn"
                type="button"
                @click="resetFilterCategory('targetHost')"
              >
                重置
              </button>
            </div>
            <div class="filter-entry-row">
              <input
                v-model="filterDraftInput.targetHost"
                type="text"
                placeholder="输入目标 IP"
                @keydown.enter.prevent="addFilterValue('targetHost')"
              />
              <button type="button" @click="addFilterValue('targetHost')">添加</button>
            </div>
            <div class="selected-tags">
              <span
                v-for="targetHost in globalFilters.targetHosts"
                :key="targetHost"
                class="filter-tag"
              >
                {{ targetHost }}
                <button
                  type="button"
                  class="remove-tag"
                  @click="removeFilterValue('targetHost', targetHost)"
                >
                  ×
                </button>
              </span>
              <span v-if="globalFilters.targetHosts.length === 0" class="empty-hint"
                >未选择目标IP</span
              >
            </div>
          </div>

          <div v-if="shouldShowFaultCodeFilter" class="filter-section">
            <div class="filter-section-title">
              <span>🔢 按故障码</span>
              <button
                class="reset-category-btn"
                type="button"
                @click="resetFilterCategory('faultCode')"
              >
                重置
              </button>
            </div>
            <div class="filter-entry-row">
              <input
                v-model="filterDraftInput.faultCode"
                type="text"
                placeholder="输入故障码"
                @keydown.enter.prevent="addFilterValue('faultCode')"
              />
              <button type="button" @click="addFilterValue('faultCode')">添加</button>
            </div>
            <div class="selected-tags">
              <span
                v-for="code in globalFilters.faultCodes"
                :key="code"
                class="filter-tag fault-filter-tag"
              >
                {{ code }}
                <button
                  type="button"
                  class="remove-tag"
                  @click="removeFilterValue('faultCode', code)"
                >
                  ×
                </button>
              </span>
              <span v-if="globalFilters.faultCodes.length === 0" class="empty-hint"
                >未选择故障码</span
              >
            </div>
          </div>

          <div class="filter-footer">
            <p v-if="filterApplyMessage" class="filter-apply-message">{{ filterApplyMessage }}</p>
            <div class="filter-footer-actions">
              <button class="apply-filter-btn" type="button" @click="applyGlobalFilters">
                确认筛选
              </button>
            </div>
          </div>
        </div>
      </section>

      <section class="trace-board-panel" aria-label="Trace看板">
        <div class="filter-header">
          <span>Trace看板</span>
          <button
            class="reset-category-btn reset-all-filter-btn"
            type="button"
            @click="resetFilterCategory('traceBoard')"
          >
            重置
          </button>
        </div>
        <div class="trace-board-body">
          <div class="selected-tags">
            <span
              v-for="traceId in globalFilters.traceBoards"
              :key="traceId"
              class="filter-tag trace-filter-tag"
            >
              {{ traceId }}
              <button type="button" class="remove-tag" @click="removeTraceBoardValue(traceId)">
                ×
              </button>
            </span>
            <span v-if="globalFilters.traceBoards.length === 0" class="empty-hint"
              >未添加Trace</span
            >
          </div>
        </div>
        <div class="trace-board-footer">
          <button class="show-trace-view-btn" type="button">展示视图</button>
        </div>
      </section>
    </aside>

    <main class="asset-detail">
      <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

      <div v-if="activePage === 'abnormal'" class="monitor-page">
        <section id="kv-latency" class="monitor-section">
          <header class="monitor-header">
            <div class="monitor-header-top">
              <h1>时延监控</h1>
            </div>
            <p class="monitor-sub">
              支持 11 项时延指标曲线，可交互选择展示
            </p>
          </header>

          <div class="monitor-grid">
            <article class="monitor-card chart-slot">
              <div class="monitor-card-title">
                <span>📈 关键时延指标趋势</span>
                <span class="danger-chip">{{ latencyAnomalyHint }}</span>
                <div class="chart-title-actions">
                  <label class="latency-percentile-select">
                    <select v-model="selectedLatencyPercentile" aria-label="时延百分位">
                      <option
                        v-for="option in latencyPercentileOptions"
                        :key="option.value"
                        :value="option.value"
                      >
                        {{ option.label }}
                      </option>
                    </select>
                  </label>
                  <button
                    v-if="latencyChartRange"
                    class="chart-reset-btn"
                    type="button"
                    @click="resetLatencyChartRange"
                  >
                    重置
                  </button>
                </div>
              </div>
              <div class="latency-series-toggle">
                <span class="latency-series-toggle-label">曲线选择：</span>
                <button
                  class="latency-series-toggle-btn latency-series-toggle-all"
                  type="button"
                  @click="selectAllLatencySeries"
                >
                  全选
                </button>
                <button
                  class="latency-series-toggle-btn latency-series-toggle-none"
                  type="button"
                  @click="deselectAllLatencySeries"
                >
                  清空
                </button>
                <label
                  v-for="series in latencySeriesConfig"
                  :key="series.key"
                  class="latency-series-checkbox"
                >
                  <input
                    type="checkbox"
                    :checked="isLatencySeriesVisible(series.key)"
                    @change="toggleLatencySeriesVisibility(series.key)"
                  />
                  <span
                    class="latency-series-color-dot"
                    :style="{ backgroundColor: series.color }"
                  ></span>
                  {{ series.label }}
                </label>
              </div>
              <div class="latency-chart-panel">
                <div v-if="isLatencyChartLoading" class="chart-state">
                  正在加载关键时延指标趋势...
                </div>
                <div v-else-if="latencyChartError" class="chart-state chart-error">
                  {{ latencyChartError }}
                </div>
                <div v-else-if="latencyChartBuckets.length === 0" class="chart-state">
                  暂无时延数据
                </div>
                <div
                  v-else
                  ref="latencyChartRef"
                  class="echarts-latency-chart"
                  role="img"
                  aria-label="关键时延指标趋势"
                ></div>
              </div>
            </article>

            <article class="monitor-card host-slot">
              <div class="monitor-card-title aggregate-title">
                <div class="aggregate-tab-list">
                  <button
                    class="aggregate-tab-item"
                    :class="{ active: activeAggregateTab === 'event' }"
                    type="button"
                    @click="setActiveAggregateTab('event')"
                  >
                    聚合事件列表
                  </button>
                  <button
                    class="aggregate-tab-item"
                    :class="{ active: activeAggregateTab === 'trace' }"
                    type="button"
                    @click="setActiveAggregateTab('trace')"
                  >
                    时延异常列表
                  </button>
                </div>
                <label v-if="activeAggregateTab === 'event'" class="latency-stat-select">
                  <span>延迟指标</span>
                  <select v-model="selectedLatencyStat">
                    <option
                      v-for="option in latencyStatOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </option>
                  </select>
                </label>
                <div v-else class="abnormal-trace-filter-actions">
                  <span class="log-sort-hint">仅后端检测器异常 · 阶段时延已展示</span>
                  <button
                    class="ghost-btn compact-action-btn"
                    type="button"
                    :disabled="isAbnormalTracesLoading"
                    @click="openAbnormalTraceFilterDialog"
                  >
                    按集群/主机过滤
                  </button>
                </div>
              </div>

              <div v-if="activeAggregateTab === 'event'" class="aggregate-table">
                <div class="aggregate-table-frame">
                  <div class="aggregate-fixed-left">
                    <div class="aggregate-left-grid aggregate-table-header">
                      <div class="aggregate-cell ip-cell">源 IP</div>
                      <div class="aggregate-cell ip-cell">目标 IP</div>
                      <div class="aggregate-cell count-cell">结果数</div>
                      <div class="aggregate-cell count-cell aggregate-sortable-cell" @click="aggregateEventSort.handleHeaderClick('anomaly_log_parse_result_cnt')">
                        <span class="sort-header-content">
                          异常数
                          <span class="sort-icons">
                            <span class="sort-icon-up" :class="{ 'sort-icon-active': aggregateEventSort.getSortOrder('anomaly_log_parse_result_cnt') === 'asc' }">▲</span>
                            <span class="sort-icon-down" :class="{ 'sort-icon-active': aggregateEventSort.getSortOrder('anomaly_log_parse_result_cnt') === 'desc' }">▼</span>
                          </span>
                        </span>
                      </div>
                    </div>
                    <template
                      v-if="
                        !isLatencyDetailLoading &&
                        !latencyDetailError &&
                        latencyDetailRows.length > 0 &&
                        getFilteredLatencyRows().length > 0
                      "
                    >
                      <div
                        v-for="row in getFilteredLatencyRows()"
                        :key="`${row.id}-fixed`"
                        class="aggregate-left-grid aggregate-body-row"
                      >
                        <div class="aggregate-cell ip-cell">{{ row.sourceHost }}</div>
                        <div class="aggregate-cell ip-cell">{{ row.targetHost }}</div>
                        <div class="aggregate-cell count-cell">{{ row.traceCount }}</div>
                        <div class="aggregate-cell count-cell anomaly-count">
                          {{ row.anomalyTraceCount }}
                        </div>
                      </div>
                    </template>
                  </div>

                  <div class="aggregate-latency-scroll">
                    <div class="aggregate-latency-head aggregate-latency-sync">
                      <div class="aggregate-latency-grid aggregate-table-header">
                        <div
                          v-for="column in aggregatedLatencyColumns"
                          :key="column.key"
                          class="aggregate-cell aggregate-sortable-cell"
                          @click="aggregateEventSort.handleHeaderClick(column.key)"
                        >
                          <span class="sort-header-content">
                            {{ column.label }}
                            <span class="sort-icons">
                              <span class="sort-icon-up" :class="{ 'sort-icon-active': aggregateEventSort.getSortOrder(column.key) === 'asc' }">▲</span>
                              <span class="sort-icon-down" :class="{ 'sort-icon-active': aggregateEventSort.getSortOrder(column.key) === 'desc' }">▼</span>
                            </span>
                          </span>
                        </div>
                      </div>
                    </div>
                    <div
                      class="aggregate-latency-scrollbar aggregate-latency-sync"
                      @scroll="syncAggregateLatencyScroll"
                    >
                      <div class="aggregate-latency-scrollbar-spacer"></div>
                    </div>
                    <div
                      class="aggregate-latency-body aggregate-latency-sync"
                      @scroll="syncAggregateLatencyScroll"
                    >
                      <template
                        v-if="
                          !isLatencyDetailLoading &&
                          !latencyDetailError &&
                          latencyDetailRows.length > 0 &&
                          getFilteredLatencyRows().length > 0
                        "
                      >
                        <div
                          v-for="row in getFilteredLatencyRows()"
                          :key="`${row.id}-latency`"
                          class="aggregate-latency-grid aggregate-body-row"
                        >
                          <div
                            v-for="column in aggregatedLatencyColumns"
                            :key="column.key"
                            class="aggregate-cell"
                          >
                            <span
                              class="metric-value"
                              :class="{
                                abnormal: isLatencyMetricAbnormal(
                                  column.key,
                                  getAggregatedLatencyValue(row, column.key),
                                ),
                              }"
                            >
                              {{ formatMetricValue(getAggregatedLatencyValue(row, column.key)) }}
                            </span>
                          </div>
                        </div>
                      </template>
                    </div>
                  </div>

                  <div class="aggregate-fixed-actions">
                    <div class="aggregate-cell action-cell aggregate-table-header">
                      聚合事件分析
                    </div>
                    <template
                      v-if="
                        !isLatencyDetailLoading &&
                        !latencyDetailError &&
                        latencyDetailRows.length > 0 &&
                        getFilteredLatencyRows().length > 0
                      "
                    >
                      <div
                        v-for="row in getFilteredLatencyRows()"
                        :key="`${row.id}-action`"
                        class="aggregate-cell action-cell trace-actions aggregate-body-row"
                      >
                        <button
                          class="metric-action-btn detail-action-btn"
                          type="button"
                          @click="openAggregatedEventDetail(row)"
                        >
                          📄详情
                        </button>
                        <button
                          class="metric-action-btn"
                          type="button"
                          @click="openLatencyHostFilterDialog(row)"
                        >
                          ➕筛选
                        </button>
                      </div>
                    </template>
                  </div>
                </div>

                <div v-if="isLatencyDetailLoading" class="aggregate-table-state">
                  正在加载时延明细...
                </div>
                <div
                  v-else-if="latencyDetailError"
                  class="aggregate-table-state metric-table-error"
                >
                  {{ latencyDetailError }}
                </div>
                <div v-else-if="latencyDetailRows.length === 0" class="aggregate-table-state">
                  暂无时延明细数据
                </div>
                <div
                  v-else-if="getFilteredLatencyRows().length === 0"
                  class="aggregate-table-state"
                >
                  无匹配聚合事件
                </div>
                <div v-if="aggregateEventTotal > 10" class="aggregate-pagination">
                  <button
                    class="ghost-btn"
                    type="button"
                    :disabled="aggregateEventPage <= 1 || isLatencyDetailLoading"
                    @click="goAggregateEventPage(aggregateEventPage - 1)"
                  >
                    上一页
                  </button>
                  <span class="pagination-pages" aria-label="聚合事件页码">
                    <button
                      v-for="pageNum in aggregateEventPageWindow"
                      :key="`aggregate-event-page-${pageNum}`"
                      class="pagination-page-btn"
                      :class="{ active: pageNum === aggregateEventPage }"
                      type="button"
                      :disabled="pageNum === aggregateEventPage || isLatencyDetailLoading"
                      @click="goAggregateEventPage(pageNum)"
                    >
                      {{ pageNum }}
                    </button>
                  </span>
                  <button
                    class="ghost-btn"
                    type="button"
                    :disabled="
                      aggregateEventPage >= aggregateEventPageCount || isLatencyDetailLoading
                    "
                    @click="goAggregateEventPage(aggregateEventPage + 1)"
                  >
                    下一页
                  </button>
                  <span class="pagination-jump">
                    <span>第 {{ aggregateEventPage }} / {{ aggregateEventPageCount }} 页</span>
                    <input
                      v-model="aggregateEventPageInput"
                      class="pagination-jump-input"
                      type="number"
                      min="1"
                      :max="aggregateEventPageCount"
                      aria-label="跳转聚合事件页码"
                      @keyup.enter="jumpAggregateEventPage"
                    />
                    <button
                      class="pagination-jump-btn"
                      type="button"
                      :disabled="isLatencyDetailLoading"
                      @click="jumpAggregateEventPage"
                    >
                      跳转
                    </button>
                  </span>
                </div>
              </div>

              <div v-else-if="activeAggregateTab === 'trace'" class="aggregate-table">
                <div class="aggregate-table-frame abnormal-trace-frame">
                  <div class="aggregate-fixed-left">
                    <div class="abnormal-left-grid latency-anomaly-left-grid aggregate-table-header">
                      <div class="aggregate-cell">时间</div>
                      <div class="aggregate-cell">Trace ID</div>
                      <div class="aggregate-cell">Pod IP</div>
                      <div class="aggregate-cell">操作类型</div>
                      <div class="aggregate-cell">集群</div>
                      <div class="aggregate-cell">主机 IP</div>
                    </div>
                    <template
                      v-if="
                        !isAbnormalTracesLoading &&
                        !abnormalTracesError &&
                        getFilteredAbnormalTraceRows().length > 0
                      "
                    >
                      <div
                        v-for="row in getFilteredAbnormalTraceRows()"
                        :key="`${row.id}-fixed`"
                        class="abnormal-left-grid latency-anomaly-left-grid aggregate-body-row"
                      >
                        <div class="aggregate-cell">{{ row.time }}</div>
                        <div class="aggregate-cell trace-id">{{ row.traceId }}</div>
                        <div class="aggregate-cell">{{ row.podIp }}</div>
                        <div class="aggregate-cell">{{ row.operation }}</div>
                        <div class="aggregate-cell">{{ row.clusterName }}</div>
                        <div class="aggregate-cell">{{ row.host }}</div>
                      </div>
                    </template>
                  </div>

                  <div class="aggregate-latency-scroll">
                    <div class="aggregate-latency-head aggregate-latency-sync">
                      <div class="abnormal-latency-grid aggregate-table-header">
                        <div class="aggregate-cell aggregate-sortable-cell" @click="abnormalTraceSort.handleHeaderClick('total_latency')">
                          <span class="sort-header-content">
                            总时延 (ms)
                            <span class="sort-icons">
                              <span class="sort-icon-up" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('total_latency') === 'asc' }">▲</span>
                              <span class="sort-icon-down" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('total_latency') === 'desc' }">▼</span>
                            </span>
                          </span>
                        </div>
                        <div class="aggregate-cell aggregate-sortable-cell" @click="abnormalTraceSort.handleHeaderClick('query_meta_latency')">
                          <span class="sort-header-content">
                            查询元数据时延 (ms)
                            <span class="sort-icons">
                              <span class="sort-icon-up" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('query_meta_latency') === 'asc' }">▲</span>
                              <span class="sort-icon-down" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('query_meta_latency') === 'desc' }">▼</span>
                            </span>
                          </span>
                        </div>
                        <div class="aggregate-cell aggregate-sortable-cell" @click="abnormalTraceSort.handleHeaderClick('urma_total_latency')">
                          <span class="sort-header-content">
                            URMA总时延 (ms)
                            <span class="sort-icons">
                              <span class="sort-icon-up" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('urma_total_latency') === 'asc' }">▲</span>
                              <span class="sort-icon-down" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('urma_total_latency') === 'desc' }">▼</span>
                            </span>
                          </span>
                        </div>
                        <div class="aggregate-cell aggregate-sortable-cell" @click="abnormalTraceSort.handleHeaderClick('urma_link_latency')">
                          <span class="sort-header-content">
                            URMA建链时延 (ms)
                            <span class="sort-icons">
                              <span class="sort-icon-up" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('urma_link_latency') === 'asc' }">▲</span>
                              <span class="sort-icon-down" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('urma_link_latency') === 'desc' }">▼</span>
                            </span>
                          </span>
                        </div>
                        <div class="aggregate-cell aggregate-sortable-cell" @click="abnormalTraceSort.handleHeaderClick('c2w_urma_latency')">
                          <span class="sort-header-content">
                            C2W URMA时延 (ms)
                            <span class="sort-icons">
                              <span class="sort-icon-up" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('c2w_urma_latency') === 'asc' }">▲</span>
                              <span class="sort-icon-down" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('c2w_urma_latency') === 'desc' }">▼</span>
                            </span>
                          </span>
                        </div>
                        <div class="aggregate-cell aggregate-sortable-cell" @click="abnormalTraceSort.handleHeaderClick('w2w_urma_latency')">
                          <span class="sort-header-content">
                            W2W URMA时延 (ms)
                            <span class="sort-icons">
                              <span class="sort-icon-up" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('w2w_urma_latency') === 'asc' }">▲</span>
                              <span class="sort-icon-down" :class="{ 'sort-icon-active': abnormalTraceSort.getSortOrder('w2w_urma_latency') === 'desc' }">▼</span>
                            </span>
                          </span>
                        </div>
                      </div>
                    </div>
                    <div
                      class="aggregate-latency-scrollbar aggregate-latency-sync"
                      @scroll="syncAggregateLatencyScroll"
                    >
                      <div class="aggregate-latency-scrollbar-spacer"></div>
                    </div>
                    <div
                      class="aggregate-latency-body aggregate-latency-sync"
                      @scroll="syncAggregateLatencyScroll"
                    >
                      <template
                        v-if="
                          !isAbnormalTracesLoading &&
                          !abnormalTracesError &&
                          getFilteredAbnormalTraceRows().length > 0
                        "
                      >
                        <div
                          v-for="row in getFilteredAbnormalTraceRows()"
                          :key="`${row.id}-latency`"
                          class="abnormal-latency-grid aggregate-body-row"
                        >
                          <div class="aggregate-cell">
                            <span
                              class="metric-value"
                              :class="{
                                abnormal: isAnomalyListLatencyMetricAbnormal(
                                  row,
                                  'total_latency',
                                  row.totalLatency,
                                ),
                              }"
                            >
                              {{ formatNullableMetricValue(row.totalLatency) }}
                            </span>
                          </div>
                          <div class="aggregate-cell">
                            <span
                              class="metric-value"
                              :class="{
                                abnormal: isAnomalyListLatencyMetricAbnormal(
                                  row,
                                  'query_meta_latency',
                                  row.queryMetaLatency,
                                ),
                              }"
                            >
                              {{ formatNullableMetricValue(row.queryMetaLatency) }}
                            </span>
                          </div>
                          <div class="aggregate-cell">
                            <span
                              class="metric-value"
                              :class="{
                                abnormal: isAnomalyListLatencyMetricAbnormal(
                                  row,
                                  'urma_total_latency',
                                  row.urmaTotalLatency,
                                ),
                              }"
                            >
                              {{ formatNullableMetricValue(row.urmaTotalLatency) }}
                            </span>
                          </div>
                          <div class="aggregate-cell">
                            <span
                              class="metric-value"
                              :class="{
                                abnormal: isAnomalyListLatencyMetricAbnormal(
                                  row,
                                  'urma_link_latency',
                                  row.urmaLinkLatency,
                                ),
                              }"
                            >
                              {{ formatNullableMetricValue(row.urmaLinkLatency) }}
                            </span>
                          </div>
                          <div class="aggregate-cell">
                            <span
                              class="metric-value"
                              :class="{
                                abnormal: isAnomalyListLatencyMetricAbnormal(
                                  row,
                                  'c2w_urma_latency',
                                  row.c2wUrmaLatency,
                                ),
                              }"
                            >
                              {{ formatNullableMetricValue(row.c2wUrmaLatency) }}
                            </span>
                          </div>
                          <div class="aggregate-cell">
                            <span
                              class="metric-value"
                              :class="{
                                abnormal: isAnomalyListLatencyMetricAbnormal(
                                  row,
                                  'w2w_urma_latency',
                                  row.w2wUrmaLatency,
                                ),
                              }"
                            >
                              {{ formatNullableMetricValue(row.w2wUrmaLatency) }}
                            </span>
                          </div>
                        </div>
                      </template>
                    </div>
                  </div>

                  <div class="aggregate-fixed-actions">
                    <div class="aggregate-cell action-cell aggregate-table-header">Trace分析</div>
                    <template
                      v-if="
                        !isAbnormalTracesLoading &&
                        !abnormalTracesError &&
                        getFilteredAbnormalTraceRows().length > 0
                      "
                    >
                      <div
                        v-for="row in getFilteredAbnormalTraceRows()"
                        :key="`${row.id}-action`"
                        class="aggregate-cell action-cell trace-analysis-actions aggregate-body-row"
                      >
                        <button
                          class="metric-action-btn detail-action-btn"
                          type="button"
                          @click="viewAbnormalTraceLink(row)"
                        >
                          查看链路
                        </button>
                        <button
                          class="metric-action-btn"
                          type="button"
                          @click="openTraceFilterDialog(row)"
                        >
                          ➕筛选
                        </button>
                      </div>
                    </template>
                  </div>
                </div>

                <div v-if="isAbnormalTracesLoading" class="aggregate-table-state">
                  正在加载时延异常...
                </div>
                <div
                  v-else-if="abnormalTracesError"
                  class="aggregate-table-state metric-table-error"
                >
                  {{ abnormalTracesError }}
                </div>
                <div v-else-if="abnormalTraceRows.length === 0" class="aggregate-table-state">
                  暂无时延异常
                </div>
                <div
                  v-else-if="getFilteredAbnormalTraceRows().length === 0"
                  class="aggregate-table-state"
                >
                  无匹配时延异常
                </div>
                <div v-if="abnormalTracesTotal > abnormalTracesPageSize" class="aggregate-pagination">
                  <button
                    class="ghost-btn"
                    type="button"
                    :disabled="abnormalTracesPage <= 1 || isAbnormalTracesLoading"
                    @click="goAbnormalTracesPage(abnormalTracesPage - 1)"
                  >
                    上一页
                  </button>
                  <span class="pagination-pages" aria-label="时延异常页码">
                    <button
                      v-for="pageNum in abnormalTracesPageWindow"
                      :key="`abnormal-traces-page-${pageNum}`"
                      class="pagination-page-btn"
                      :class="{ active: pageNum === abnormalTracesPage }"
                      type="button"
                      :disabled="pageNum === abnormalTracesPage || isAbnormalTracesLoading"
                      @click="goAbnormalTracesPage(pageNum)"
                    >
                      {{ pageNum }}
                    </button>
                  </span>
                  <button
                    class="ghost-btn"
                    type="button"
                    :disabled="
                      abnormalTracesPage >= abnormalTracesPageCount || isAbnormalTracesLoading
                    "
                    @click="goAbnormalTracesPage(abnormalTracesPage + 1)"
                  >
                    下一页
                  </button>
                  <span class="pagination-jump">
                    <span>第 {{ abnormalTracesPage }} / {{ abnormalTracesPageCount }} 页</span>
                    <input
                      v-model="abnormalTracesPageInput"
                      class="pagination-jump-input"
                      type="number"
                      min="1"
                      :max="abnormalTracesPageCount"
                      aria-label="跳转时延异常页码"
                      @keyup.enter="jumpAbnormalTracesPage"
                    />
                    <button
                      class="pagination-jump-btn"
                      type="button"
                      :disabled="isAbnormalTracesLoading"
                      @click="jumpAbnormalTracesPage"
                    >
                      跳转
                    </button>
                  </span>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section v-if="isFaultCodeFeatureEnabled" id="kv-fault" class="monitor-section">
          <header class="monitor-header">
            <div class="monitor-header-top">
              <h1>故障监控</h1>
            </div>
            <p class="monitor-sub">
              故障码 / 故障名称 / 故障域
            </p>
          </header>

          <div class="monitor-grid">
            <article class="monitor-card chart-slot">
              <div class="monitor-card-title">
                <span>📈 故障码计数时序分布</span>
                <button
                  v-if="faultChartRange"
                  class="chart-reset-btn"
                  type="button"
                  @click="resetFaultChartRange"
                >
                  重置
                </button>
              </div>
              <div class="latency-chart-panel">
                <div v-if="isFaultChartLoading" class="chart-state">
                  正在加载故障码计数时序分布...
                </div>
                <div v-else-if="faultChartError" class="chart-state chart-error">
                  {{ faultChartError }}
                </div>
                <div
                  v-else-if="faultChartBuckets.length === 0 || faultCodes.length === 0"
                  class="chart-state"
                >
                  暂无故障码数据
                </div>
                <div
                  v-else
                  ref="faultChartRef"
                  class="echarts-latency-chart"
                  aria-label="故障码计数时序分布"
                ></div>
              </div>
            </article>

            <article class="monitor-card host-slot">
              <div class="monitor-card-title aggregate-title">
                <div class="aggregate-tab-list">
                  <button
                    class="aggregate-tab-item"
                    :class="{ active: activeFaultMonitorTab === 'event' }"
                    type="button"
                    @click="activeFaultMonitorTab = 'event'"
                  >
                    聚合事件列表
                  </button>
                  <button
                    class="aggregate-tab-item"
                    :class="{ active: activeFaultMonitorTab === 'trace' }"
                    type="button"
                    @click="activeFaultMonitorTab = 'trace'"
                  >
                    错误日志列表
                  </button>
                </div>
                <label v-if="activeFaultMonitorTab === 'event'" class="latency-stat-select">
                  <span>时间间隔</span>
                  <select
                    v-model="selectedFaultAggregateInterval"
                    @change="changeFaultAggregateInterval"
                  >
                    <option value="hour">时</option>
                    <option value="minute">分</option>
                    <option value="second">秒</option>
                  </select>
                </label>
              </div>

              <div
                v-if="activeFaultMonitorTab === 'event'"
                class="aggregate-table fault-aggregate-table"
              >
                <div class="aggregate-table-frame fault-aggregate-frame">
                  <div class="aggregate-fixed-left">
                    <div class="fault-aggregate-time-grid aggregate-table-header">
                      <div class="aggregate-cell fault-expand-cell"></div>
                      <div class="aggregate-cell">开始时间</div>
                      <div class="aggregate-cell">结束时间</div>
                    </div>
                    <template v-if="paginatedFaultAggregatedEventRows.length > 0">
                      <template
                        v-for="row in paginatedFaultAggregatedEventRows"
                        :key="`${row.id}-time`"
                      >
                        <div
                          class="fault-aggregate-time-grid aggregate-body-row fault-aggregate-main-row"
                          :class="{ expanded: isFaultAggregatedEventExpanded(row) }"
                          @click="toggleFaultAggregatedEventRow(row)"
                        >
                          <div class="aggregate-cell fault-expand-cell">
                            <span class="fault-expand-indicator">
                              {{ isFaultAggregatedEventExpanded(row) ? '🔽' : '▶️' }}
                            </span>
                          </div>
                          <div class="aggregate-cell">{{ row.startTime }}</div>
                          <div class="aggregate-cell">{{ row.endTime }}</div>
                        </div>
                        <div
                          v-if="isFaultAggregatedEventExpanded(row)"
                          class="fault-aggregate-time-grid aggregate-body-row fault-aggregate-sub-row"
                        >
                          <div class="fault-aggregate-sub-left">
                            <div class="aggregate-cell fault-expand-cell"></div>
                            <div class="aggregate-cell fault-aggregate-sub-pod-head">Pod IP</div>
                            <template
                              v-if="
                                isFaultAggregatedEventPodLoading(row) &&
                                getFaultAggregatedEventPodRows(row).length === 0
                              "
                            >
                              <div class="aggregate-cell fault-expand-cell"></div>
                              <div class="aggregate-cell fault-aggregate-sub-pod-cell">
                                加载中...
                              </div>
                            </template>
                            <template
                              v-else-if="
                                getFaultAggregatedEventPodRows(row).length === 0
                              "
                            >
                              <div class="aggregate-cell fault-expand-cell"></div>
                              <div class="aggregate-cell fault-aggregate-sub-pod-cell">
                                {{ getFaultAggregatedEventPodError(row) || '暂无Pod聚合数据' }}
                              </div>
                            </template>
                            <template
                              v-for="podRow in getFaultAggregatedEventPodRows(row)"
                              :key="`${podRow.id}-pod-ip`"
                            >
                              <div class="aggregate-cell fault-expand-cell"></div>
                              <div class="aggregate-cell fault-aggregate-sub-pod-cell">
                                {{ podRow.podIp }}
                              </div>
                            </template>
                            <div
                              v-if="
                                getFaultAggregatedEventPodTotal(row) >
                                faultAggregatedEventPodPageSize
                              "
                              class="fault-aggregate-sub-pagination fault-aggregate-sub-pagination-side"
                            >
                              第 {{ getFaultAggregatedEventPodPage(row) }} /
                              {{ getFaultAggregatedEventPodPageCount(row) }} 页
                            </div>
                          </div>
                        </div>
                      </template>
                    </template>
                  </div>

                  <div class="aggregate-latency-scroll fault-code-scroll">
                    <div class="aggregate-latency-head aggregate-latency-sync">
                      <div
                        class="fault-code-grid aggregate-table-header"
                        :style="faultAggregatedEventCodeGridStyle"
                      >
                        <template v-if="faultAggregatedEventCodes.length > 0">
                          <div
                            v-for="code in faultAggregatedEventCodes"
                            :key="`fault-aggregate-code-head-${code}`"
                            class="aggregate-cell aggregate-sortable-cell"
                            @click.stop="faultAggregatedEventSort.handleHeaderClick(code)"
                          >
                            <span class="sort-header-content">
                              {{ getFaultAggregatedEventCodeLabel(code) }}
                              <span class="sort-icons">
                                <span
                                  class="sort-icon-up"
                                  :class="{
                                    'sort-icon-active':
                                      faultAggregatedEventSort.getSortOrder(code) === 'asc',
                                  }"
                                >
                                  ▲
                                </span>
                                <span
                                  class="sort-icon-down"
                                  :class="{
                                    'sort-icon-active':
                                      faultAggregatedEventSort.getSortOrder(code) === 'desc',
                                  }"
                                >
                                  ▼
                                </span>
                              </span>
                            </span>
                          </div>
                        </template>
                        <div v-else class="aggregate-cell">故障码</div>
                      </div>
                    </div>
                    <div
                      class="aggregate-latency-scrollbar aggregate-latency-sync"
                      @scroll="syncAggregateLatencyScroll"
                    >
                      <div
                        class="aggregate-latency-scrollbar-spacer fault-code-scrollbar-spacer"
                        :style="{ width: faultAggregatedEventCodeGridStyle.minWidth }"
                      ></div>
                    </div>
                    <div
                      class="aggregate-latency-body aggregate-latency-sync"
                      @scroll="syncAggregateLatencyScroll"
                    >
                      <template v-if="paginatedFaultAggregatedEventRows.length > 0">
                        <template
                          v-for="row in paginatedFaultAggregatedEventRows"
                          :key="`${row.id}-fault-codes`"
                        >
                          <div
                            class="fault-code-grid aggregate-body-row fault-aggregate-main-row"
                            :class="{ expanded: isFaultAggregatedEventExpanded(row) }"
                            :style="faultAggregatedEventCodeGridStyle"
                            @click="toggleFaultAggregatedEventRow(row)"
                          >
                            <template v-if="faultAggregatedEventCodes.length > 0">
                              <div
                                v-for="code in faultAggregatedEventCodes"
                                :key="`${row.id}-fault-code-${code}`"
                                class="aggregate-cell"
                              >
                                {{ getFaultAggregatedEventCodeValue(row, code) }}
                              </div>
                            </template>
                            <div v-else class="aggregate-cell">-</div>
                          </div>
                          <div
                            v-if="isFaultAggregatedEventExpanded(row)"
                            class="aggregate-body-row fault-aggregate-sub-row fault-aggregate-sub-code-panel"
                            :style="{ minWidth: faultAggregatedEventCodeGridStyle.minWidth }"
                          >
                            <div
                              class="fault-code-grid aggregate-table-header fault-aggregate-sub-code-grid"
                              :style="faultAggregatedEventCodeGridStyle"
                            >
                              <div
                                v-for="code in faultAggregatedEventCodes"
                                :key="`${row.id}-sub-head-${code}`"
                                class="aggregate-cell aggregate-sortable-cell"
                                @click.stop="handleFaultAggregatedEventPodSortHeaderClick(row, code)"
                              >
                                <span class="sort-header-content">
                                  {{ getFaultAggregatedEventCodeLabel(code) }}
                                  <span class="sort-icons">
                                    <span
                                      class="sort-icon-up"
                                      :class="{
                                        'sort-icon-active':
                                          faultAggregatedEventPodSort.getSortOrder(code) === 'asc',
                                      }"
                                    >
                                      ▲
                                    </span>
                                    <span
                                      class="sort-icon-down"
                                      :class="{
                                        'sort-icon-active':
                                          faultAggregatedEventPodSort.getSortOrder(code) === 'desc',
                                      }"
                                    >
                                      ▼
                                    </span>
                                  </span>
                                </span>
                              </div>
                            </div>
                            <div
                              v-if="
                                isFaultAggregatedEventPodLoading(row) &&
                                getFaultAggregatedEventPodRows(row).length === 0
                              "
                              class="fault-code-grid aggregate-body-row fault-aggregate-sub-code-grid"
                              :style="faultAggregatedEventCodeGridStyle"
                            >
                              <div
                                class="aggregate-cell"
                                :style="{ gridColumn: `span ${Math.max(1, faultAggregatedEventCodes.length)}` }"
                              >
                                正在加载Pod聚合数据...
                              </div>
                            </div>
                            <div
                              v-else-if="getFaultAggregatedEventPodRows(row).length === 0"
                              class="fault-code-grid aggregate-body-row fault-aggregate-sub-code-grid"
                              :style="faultAggregatedEventCodeGridStyle"
                            >
                              <div
                                class="aggregate-cell"
                                :style="{ gridColumn: `span ${Math.max(1, faultAggregatedEventCodes.length)}` }"
                              >
                                {{ getFaultAggregatedEventPodError(row) || '暂无Pod聚合数据' }}
                              </div>
                            </div>
                            <div
                              v-for="podRow in getFaultAggregatedEventPodRows(row)"
                              :key="`${podRow.id}-fault-codes`"
                              class="fault-code-grid aggregate-body-row fault-aggregate-sub-code-grid"
                              :style="faultAggregatedEventCodeGridStyle"
                            >
                              <div
                                v-for="code in faultAggregatedEventCodes"
                                :key="`${podRow.id}-fault-code-${code}`"
                                class="aggregate-cell"
                              >
                                {{ getFaultAggregatedEventPodCodeValue(podRow, code) }}
                              </div>
                            </div>
                              <div
                                v-if="
                                  getFaultAggregatedEventPodTotal(row) >
                                  faultAggregatedEventPodPageSize
                                "
                                class="fault-aggregate-sub-pagination"
                              >
                                <button
                                  class="pagination-page-btn"
                                  type="button"
                                  :disabled="
                                    getFaultAggregatedEventPodPage(row) <= 1 ||
                                    isFaultAggregatedEventPodLoading(row)
                                  "
                                  @click.stop="
                                    goFaultAggregatedEventPodPage(
                                      row,
                                      getFaultAggregatedEventPodPage(row) - 1,
                                    )
                                  "
                                >
                                  上一页
                                </button>
                                <span
                                  class="pagination-pages"
                                  aria-label="故障聚合事件Pod副表页码"
                                >
                                  <button
                                    v-for="pageNum in getFaultAggregatedEventPodPageWindow(row)"
                                    :key="`${row.id}-pod-page-${pageNum}`"
                                    class="pagination-page-btn"
                                    :class="{
                                      active: pageNum === getFaultAggregatedEventPodPage(row),
                                    }"
                                    type="button"
                                    :disabled="
                                      pageNum === getFaultAggregatedEventPodPage(row) ||
                                      isFaultAggregatedEventPodLoading(row)
                                    "
                                    @click.stop="goFaultAggregatedEventPodPage(row, pageNum)"
                                  >
                                    {{ pageNum }}
                                  </button>
                                </span>
                                <button
                                  class="pagination-page-btn"
                                  type="button"
                                  :disabled="
                                    getFaultAggregatedEventPodPage(row) >=
                                      getFaultAggregatedEventPodPageCount(row) ||
                                    isFaultAggregatedEventPodLoading(row)
                                  "
                                  @click.stop="
                                    goFaultAggregatedEventPodPage(
                                      row,
                                      getFaultAggregatedEventPodPage(row) + 1,
                                    )
                                  "
                                >
                                  下一页
                                </button>
                                <span class="pagination-jump fault-aggregate-sub-jump">
                                  <span>
                                    第 {{ getFaultAggregatedEventPodPage(row) }} /
                                    {{ getFaultAggregatedEventPodPageCount(row) }} 页
                                  </span>
                                  <input
                                    class="pagination-jump-input"
                                    type="number"
                                    min="1"
                                    :max="getFaultAggregatedEventPodPageCount(row)"
                                    :value="getFaultAggregatedEventPodPageInput(row)"
                                    aria-label="跳转故障聚合事件Pod副表页码"
                                    @input="
                                      setFaultAggregatedEventPodPageInput(
                                        row,
                                        ($event.target as HTMLInputElement).value,
                                      )
                                    "
                                    @keyup.enter="jumpFaultAggregatedEventPodPage(row)"
                                  />
                                  <button
                                    class="pagination-jump-btn"
                                    type="button"
                                    :disabled="isFaultAggregatedEventPodLoading(row)"
                                    @click.stop="jumpFaultAggregatedEventPodPage(row)"
                                  >
                                    跳转
                                  </button>
                                </span>
                              </div>
                          </div>
                        </template>
                      </template>
                    </div>
                  </div>

                  <div class="aggregate-fixed-actions">
                    <div class="aggregate-cell action-cell aggregate-table-header">
                      聚合事件分析
                    </div>
                    <template v-if="paginatedFaultAggregatedEventRows.length > 0">
                      <template
                        v-for="row in paginatedFaultAggregatedEventRows"
                        :key="`${row.id}-action`"
                      >
                        <div
                          class="aggregate-cell action-cell aggregate-body-row fault-aggregate-main-row"
                          :class="{ expanded: isFaultAggregatedEventExpanded(row) }"
                          @click="toggleFaultAggregatedEventRow(row)"
                        ></div>
                        <div
                          v-if="isFaultAggregatedEventExpanded(row)"
                          class="aggregate-cell action-cell aggregate-body-row fault-aggregate-sub-row fault-aggregate-sub-action"
                        >
                          <div class="fault-aggregate-sub-action-head"></div>
                          <div
                            v-if="
                              isFaultAggregatedEventPodLoading(row) &&
                              getFaultAggregatedEventPodRows(row).length === 0
                            "
                            class="fault-aggregate-sub-action-body"
                          ></div>
                          <div
                            v-else-if="getFaultAggregatedEventPodRows(row).length === 0"
                            class="fault-aggregate-sub-action-body"
                          ></div>
                          <div
                            v-for="podRow in getFaultAggregatedEventPodRows(row)"
                            :key="`${podRow.id}-action`"
                            class="fault-aggregate-sub-action-body"
                          >
                            <button
                              class="metric-action-btn detail-action-btn"
                              type="button"
                              @click.stop="openFaultAggregatedEventDetail(row, podRow)"
                            >
                              📄详情
                            </button>
                          </div>
                          <div
                            v-if="
                              getFaultAggregatedEventPodTotal(row) >
                              faultAggregatedEventPodPageSize
                            "
                            class="fault-aggregate-sub-pagination fault-aggregate-sub-pagination-actions"
                          ></div>
                        </div>
                      </template>
                    </template>
                  </div>
                </div>
                <div v-if="isFaultAggregatedEventsLoading" class="aggregate-table-state">
                  正在加载聚合事件...
                </div>
                <div
                  v-else-if="faultAggregatedEventsError"
                  class="aggregate-table-state metric-table-error"
                >
                  {{ faultAggregatedEventsError }}
                </div>
                <div
                  v-else-if="faultAggregatedEventRows.length === 0"
                  class="aggregate-table-state"
                >
                  暂无聚合事件数据
                </div>
                <div v-if="faultAggregatedEventTotal > 0" class="aggregate-pagination">
                  <button
                    class="ghost-btn"
                    type="button"
                    :disabled="faultAggregatedEventPage <= 1 || isFaultAggregatedEventsLoading"
                    @click="goFaultAggregatedEventPage(faultAggregatedEventPage - 1)"
                  >
                    上一页
                  </button>
                  <span class="pagination-pages" aria-label="故障聚合事件页码">
                    <button
                      v-for="pageNum in faultAggregatedEventPageWindow"
                      :key="`fault-aggregate-event-page-${pageNum}`"
                      class="pagination-page-btn"
                      :class="{ active: pageNum === faultAggregatedEventPage }"
                      type="button"
                      :disabled="
                        pageNum === faultAggregatedEventPage || isFaultAggregatedEventsLoading
                      "
                      @click="goFaultAggregatedEventPage(pageNum)"
                    >
                      {{ pageNum }}
                    </button>
                  </span>
                  <button
                    class="ghost-btn"
                    type="button"
                    :disabled="
                      faultAggregatedEventPage >= faultAggregatedEventPageCount ||
                      isFaultAggregatedEventsLoading
                    "
                    @click="goFaultAggregatedEventPage(faultAggregatedEventPage + 1)"
                  >
                    下一页
                  </button>
                  <span class="pagination-jump">
                    <span>
                      第 {{ faultAggregatedEventPage }} / {{ faultAggregatedEventPageCount }} 页
                    </span>
                    <input
                      v-model="faultAggregatedEventPageInput"
                      class="pagination-jump-input"
                      type="number"
                      min="1"
                      :max="faultAggregatedEventPageCount"
                      aria-label="跳转故障聚合事件页码"
                      @keyup.enter="jumpFaultAggregatedEventPage"
                    />
                    <button
                      class="pagination-jump-btn"
                      type="button"
                      :disabled="isFaultAggregatedEventsLoading"
                      @click="jumpFaultAggregatedEventPage"
                    >
                      跳转
                    </button>
                  </span>
                </div>
              </div>

              <div v-else class="metric-table-wrapper">
                <table class="metric-table fault-detail-table">
                  <thead>
                    <tr>
                      <th>时间</th>
                      <th>Trace ID</th>
                      <th>Pod IP</th>
                      <th>集群</th>
                      <th>主机 IP</th>
                      <th>故障码</th>
                      <th>故障名称</th>
                      <th>故障域</th>
                      <th>故障分析</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="isFaultTraceEventsLoading">
                      <td colspan="9" class="metric-table-state">正在加载错误日志...</td>
                    </tr>
                    <tr v-else-if="faultTraceEventsError">
                      <td colspan="9" class="metric-table-state metric-table-error">
                        {{ faultTraceEventsError }}
                      </td>
                    </tr>
                    <tr v-else-if="faultTraceRows.length === 0">
                      <td colspan="9" class="metric-table-state">暂无错误日志数据</td>
                    </tr>
                    <tr v-else-if="getFilteredFaultTraceRows().length === 0">
                      <td colspan="9" class="metric-table-state">无匹配错误日志</td>
                    </tr>
                    <template v-else>
                      <tr
                        v-for="trace in getFilteredFaultTraceRows()"
                        :key="trace.id"
                      >
                        <td>{{ trace.time }}</td>
                        <td class="trace-id">{{ trace.traceId }}</td>
                        <td>
                          <span
                            v-for="podName in trace.podNames"
                            :key="`${trace.id}-pod-${podName}`"
                            class="multi-line-cell-item"
                          >
                            {{ podName }}
                          </span>
                        </td>
                        <td>
                          <span
                            v-for="clusterName in trace.clusterNames"
                            :key="`${trace.id}-cluster-${clusterName}`"
                            class="multi-line-cell-item"
                          >
                            {{ clusterName }}
                          </span>
                        </td>
                        <td>
                          <span
                            v-for="hostName in trace.hostNames"
                            :key="`${trace.id}-host-${hostName}`"
                            class="multi-line-cell-item"
                          >
                            {{ hostName }}
                          </span>
                        </td>
                        <td>
                          <span class="fault-code-pill">{{ trace.faultCode }}</span>
                        </td>
                        <td>{{ trace.faultType }}</td>
                        <td>{{ trace.faultDomain }}</td>
                        <td class="trace-actions-cell">
                          <div class="trace-actions">
                            <button
                              class="metric-action-btn detail-action-btn"
                              type="button"
                              @click="openFaultTraceDialog(trace)"
                            >
                              查看链路
                            </button>
                            <button
                              class="metric-action-btn"
                              type="button"
                              @click="openTraceFilterDialog(trace)"
                            >
                              ➕ 筛选
                            </button>
                          </div>
                        </td>
                      </tr>
                    </template>
                  </tbody>
                </table>
              </div>
              <div
                v-if="
                  activeFaultMonitorTab === 'trace' &&
                  faultTraceEventsTotal > faultTraceEventsPageSize
                "
                class="aggregate-pagination"
              >
                <button
                  class="ghost-btn"
                  type="button"
                  :disabled="faultTraceEventsPage <= 1 || isFaultTraceEventsLoading"
                  @click="goFaultTraceEventsPage(faultTraceEventsPage - 1)"
                >
                  上一页
                </button>
                <span class="pagination-pages" aria-label="故障异常 Trace 页码">
                  <button
                    v-for="pageNum in faultTraceEventsPageWindow"
                    :key="`fault-trace-events-page-${pageNum}`"
                    class="pagination-page-btn"
                    :class="{ active: pageNum === faultTraceEventsPage }"
                    type="button"
                    :disabled="pageNum === faultTraceEventsPage || isFaultTraceEventsLoading"
                    @click="goFaultTraceEventsPage(pageNum)"
                  >
                    {{ pageNum }}
                  </button>
                </span>
                <button
                  class="ghost-btn"
                  type="button"
                  :disabled="
                    faultTraceEventsPage >= faultTraceEventsPageCount ||
                    isFaultTraceEventsLoading
                  "
                  @click="goFaultTraceEventsPage(faultTraceEventsPage + 1)"
                >
                  下一页
                </button>
                <span class="pagination-jump">
                  <span>第 {{ faultTraceEventsPage }} / {{ faultTraceEventsPageCount }} 页</span>
                  <input
                    v-model="faultTraceEventsPageInput"
                    class="pagination-jump-input"
                    type="number"
                    min="1"
                    :max="faultTraceEventsPageCount"
                    aria-label="跳转故障异常 Trace 页码"
                    @keyup.enter="jumpFaultTraceEventsPage"
                  />
                  <button
                    class="pagination-jump-btn"
                    type="button"
                    :disabled="isFaultTraceEventsLoading"
                    @click="jumpFaultTraceEventsPage"
                  >
                    跳转
                  </button>
                </span>
              </div>
            </article>
          </div>
        </section>
      </div>

      <div v-else-if="isDetailLoading" class="empty-detail">正在加载详情...</div>

      <article v-else-if="selectedAsset" class="detail-content">
        <header class="detail-header">
          <div class="detail-title-block">
            <p class="eyebrow">资产库详情</p>
            <h1>{{ selectedAsset.name }}</h1>
            <p class="detail-description">{{ selectedAsset.description }}</p>
            <div class="detail-times">
              <span>创建时间：{{ selectedAsset.created_at || '-' }}</span>
              <span>更新时间：{{ selectedAsset.updated_at || '-' }}</span>
            </div>
          </div>
          <div class="detail-actions">
            <div class="detail-actions-bottom">
              <button
                class="edit-btn icon-btn detail-icon-btn"
                type="button"
                aria-label="编辑"
                title="编辑"
                @click="openEditDialog"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M6 3.75h8.25L18 7.5v11.25a1.5 1.5 0 0 1-1.5 1.5H6a1.5 1.5 0 0 1-1.5-1.5V5.25A1.5 1.5 0 0 1 6 3.75Z"
                  />
                  <path d="M14.25 3.75V7.5H18" />
                  <path d="m9 15 5.25-5.25 2.25 2.25-5.25 5.25-3 .75.75-3Z" />
                </svg>
              </button>
              <button
                class="delete-detail-btn icon-btn detail-icon-btn"
                type="button"
                aria-label="删除"
                title="删除"
                @click="deleteAsset(selectedAsset)"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4.5 7h15" />
                  <path d="M9.75 7V4.75h4.5V7" />
                  <path
                    d="M7 7l.75 12.25a1.5 1.5 0 0 0 1.5 1.25h5.5a1.5 1.5 0 0 0 1.5-1.25L17 7"
                  />
                  <path d="M10 11v5.5" />
                  <path d="M14 11v5.5" />
                </svg>
              </button>
            </div>
          </div>
        </header>

        <section class="log-upload-section">
          <div class="log-upload-area">
            <input
              v-model="logSourceInput"
              type="text"
              class="log-source-input"
              placeholder="添加日志：输入目录路径（如 /var/log/）或远程 URL（如 https://example.com/log.zip）"
              :disabled="isUploadingLog"
              @keydown.enter="submitLogSource"
            />
            <button
              class="log-add-btn"
              type="button"
              :disabled="isUploadingLog || !logSourceInput.trim()"
              @click="submitLogSource"
            >
              {{ isUploadingLog ? '提交中...' : '添加' }}
            </button>
            <button
              class="log-upload-btn"
              type="button"
              :disabled="isUploadingLog"
              @click="triggerFileUpload"
            >
              上传 ZIP 文件
            </button>
            <input
              ref="fileInputRef"
              type="file"
              accept=".zip"
              style="display: none"
              @change="handleFileChange"
            />
          </div>
          <div v-if="uploadLogError" class="upload-log-error">{{ uploadLogError }}</div>
        </section>

        <section class="log-files-section">
          <div v-if="isLogFilesLoading" class="state-text">正在加载日志文件...</div>
          <div v-else-if="logFiles.length === 0" class="state-text">暂无日志文件</div>
          <div v-else class="log-file-list">
            <div v-for="file in logFiles" :key="file.id" class="log-file-item">
              <div class="log-file-info">
                <div class="log-file-summary">
                  <span class="log-file-path">📁 {{ file.file_path || file.name }}</span>
                  <span class="log-file-meta">
                    <span class="log-file-time">创建时间：{{ file.created_at || '-' }}</span>
                    <span
                      class="status-badge"
                      :class="statusBadgeClass(getLogFileTaskStatus(file))"
                      >{{ statusLabel(getLogFileTaskStatus(file)) }}</span
                    >
                    <span
                      v-if="isSuccessfulLogFileTask(file) && isLogFileDetailLoaded(file)"
                      class="anomaly-badge"
                      :class="getLogFileAnomalyCountClass(file)"
                      >{{ getLogFileAnomalyCountText(file) }}</span
                    >
                    <span
                      v-if="isSuccessfulLogFileTask(file) && isLogFileDetailLoaded(file)"
                      class="anomaly-badge"
                      :class="getLogFileTraceFailureEventCountClass(file)"
                      >{{ getLogFileTraceFailureEventCountText(file) }}</span
                    >
                  </span>
                </div>
                <div
                  v-if="shouldShowLogFileProgress(file)"
                  class="log-file-progress"
                  :class="`progress-${getLogFileProgressClass(file)}`"
                >
                  <div class="log-file-progress-info">
                    <span class="log-file-progress-message">
                      解析进度：{{ getLogFileProgressMessage(file) }}
                    </span>
                    <span class="log-file-progress-percent">
                      {{ getLogFileProgressText(file) }}
                    </span>
                  </div>
                  <div
                    class="log-file-progress-track"
                    role="progressbar"
                    aria-valuemin="0"
                    aria-valuemax="100"
                    :aria-valuenow="Math.round(getLogFileProgress(file))"
                  >
                    <div
                      class="log-file-progress-bar"
                      :style="{ width: `${getLogFileProgress(file)}%` }"
                    ></div>
                  </div>
                </div>
              </div>
              <div class="log-file-actions">
                <button
                  class="log-file-refresh-btn"
                  type="button"
                  aria-label="更新"
                  title="更新"
                  :disabled="refreshingFileIds.has(file.id)"
                  @click="refreshLogFile(file.id)"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M19 8a7 7 0 0 0-12.25-3.25L5 6.5" />
                    <path d="M5 3v3.5h3.5" />
                    <path d="M5 16a7 7 0 0 0 12.25 3.25L19 17.5" />
                    <path d="M19 21v-3.5h-3.5" />
                  </svg>
                </button>
              </div>
            </div>
            <div
              v-if="logFilesTotal > logFilesPageSize"
              class="aggregate-pagination log-file-pagination"
            >
              <button
                class="ghost-btn"
                type="button"
                :disabled="logFilesPage <= 1 || isLogFilesLoading"
                @click="goLogFilesPage(logFilesPage - 1)"
              >
                上一页
              </button>
              <span class="pagination-pages" aria-label="日志路径解析任务页码">
                <button
                  v-for="pageNum in logFilesPageWindow"
                  :key="`log-file-page-${pageNum}`"
                  class="pagination-page-btn"
                  :class="{ active: pageNum === logFilesPage }"
                  type="button"
                  :disabled="pageNum === logFilesPage || isLogFilesLoading"
                  @click="goLogFilesPage(pageNum)"
                >
                  {{ pageNum }}
                </button>
              </span>
              <button
                class="ghost-btn"
                type="button"
                :disabled="logFilesPage >= logFilesPageCount || isLogFilesLoading"
                @click="goLogFilesPage(logFilesPage + 1)"
              >
                下一页
              </button>
              <span class="pagination-jump">
                <span>第 {{ logFilesPage }} / {{ logFilesPageCount }} 页</span>
                <input
                  v-model="logFilesPageInput"
                  class="pagination-jump-input"
                  type="number"
                  min="1"
                  :max="logFilesPageCount"
                  aria-label="跳转日志路径解析任务页码"
                  @keyup.enter="jumpLogFilesPage"
                />
                <button
                  class="pagination-jump-btn"
                  type="button"
                  :disabled="isLogFilesLoading"
                  @click="jumpLogFilesPage"
                >
                  跳转
                </button>
              </span>
            </div>
          </div>
        </section>
      </article>

      <div v-else class="empty-detail empty-detail-prompt">请添加资产库，上传路径进行日志解析</div>
    </main>

    <div v-if="timePointDialog.open" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content time-point-modal">
        <header class="modal-header">
          <h2>⏲️ 按时间点筛选</h2>
          <button class="close-modal" type="button" title="关闭" @click="closeTimePointDialog">
            x
          </button>
        </header>

        <div class="modal-body time-point-body">
          <div v-if="timePointDialog.error" class="dialog-error">{{ timePointDialog.error }}</div>

          <section class="time-point-section">
            <h3>
              🕒 基于时间点
              <span class="time-point-value">{{ timePointDialog.bucket?.label || '-' }}</span>
              设置筛选范围
            </h3>
            <div class="time-range-options">
              <button type="button" @click="applyPresetTimePointRange(5)">前后 5 分钟</button>
              <button type="button" @click="applyPresetTimePointRange(10)">前后 10 分钟</button>
              <button type="button" @click="applyPresetTimePointRange(15)">前后 15 分钟</button>
            </div>
          </section>

          <section class="time-point-section">
            <h3>✏️ 自定义范围 (分钟)</h3>
            <div class="custom-time-range">
              <label>
                <span>前</span>
                <input v-model="timePointDialog.customBefore" type="number" min="0" step="1" />
                <span>分钟</span>
              </label>
              <label>
                <span>后</span>
                <input v-model="timePointDialog.customAfter" type="number" min="0" step="1" />
                <span>分钟</span>
              </label>
              <button
                class="save-btn custom-time-confirm"
                type="button"
                @click="confirmCustomTimePointRange"
              >
                确定
              </button>
            </div>
          </section>
        </div>

        <footer class="modal-actions time-point-actions">
          <button class="ghost-btn full-width" type="button" @click="closeTimePointDialog">
            取消
          </button>
        </footer>
      </section>
    </div>

    <div v-if="dialog.open" class="modal" role="dialog" aria-modal="true">
      <form class="modal-content" @submit.prevent="saveDialog">
        <header class="modal-header">
          <h2>{{ dialogTitle }}</h2>
          <button class="close-modal" type="button" title="关闭" @click="closeDialog">x</button>
        </header>

        <div class="modal-body">
          <div v-if="dialog.error" class="dialog-error">{{ dialog.error }}</div>

          <label class="form-field">
            <span>资产库名称</span>
            <input v-model="dialog.name" type="text" maxlength="80" autocomplete="off" />
          </label>

          <label class="form-field">
            <span>描述</span>
            <textarea v-model="dialog.description" rows="5" maxlength="1000"></textarea>
          </label>
        </div>

        <footer class="modal-actions">
          <button class="ghost-btn" type="button" :disabled="isSaving" @click="closeDialog">
            取消
          </button>
          <button class="save-btn" type="submit" :disabled="isSaving">
            {{ isSaving ? '提交中...' : '提交' }}
          </button>
        </footer>
      </form>
    </div>

    <div v-if="queryDialog.open" class="modal" role="dialog" aria-modal="true">
      <form class="modal-content" @submit.prevent="submitQuery">
        <header class="modal-header">
          <h2>查询资产库</h2>
          <button class="close-modal" type="button" title="关闭" @click="closeQueryDialog">
            x
          </button>
        </header>

        <div class="modal-body">
          <div v-if="queryDialog.error" class="dialog-error">{{ queryDialog.error }}</div>

          <label class="form-field">
            <span>名称</span>
            <input v-model="queryDialog.name" type="text" maxlength="80" autocomplete="off" />
          </label>

          <label class="form-field">
            <span>描述</span>
            <input
              v-model="queryDialog.description"
              type="text"
              maxlength="200"
              autocomplete="off"
            />
          </label>

          <div class="form-grid">
            <label class="form-field">
              <span>创建开始时间</span>
              <input v-model="queryDialog.createdAtStart" type="datetime-local" />
            </label>

            <label class="form-field">
              <span>创建结束时间</span>
              <input v-model="queryDialog.createdAtEnd" type="datetime-local" />
            </label>
          </div>

          <div class="form-field">
            <span>时间排序</span>
            <div class="radio-row">
              <label>
                <input v-model="queryDialog.sortOrder" type="radio" value="desc" />
                降序
              </label>
              <label>
                <input v-model="queryDialog.sortOrder" type="radio" value="asc" />
                升序
              </label>
            </div>
          </div>
        </div>

        <footer class="modal-actions">
          <button class="ghost-btn" type="button" :disabled="isQuerying" @click="closeQueryDialog">
            取消
          </button>
          <button class="save-btn" type="submit" :disabled="isQuerying">
            {{ isQuerying ? '查询中...' : '提交' }}
          </button>
        </footer>
      </form>
    </div>

    <div v-if="traceFilterDialog.open" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content trace-filter-modal">
        <header class="modal-header">
          <h2>🔍 添加筛选条件</h2>
          <button class="close-modal" type="button" title="关闭" @click="closeTraceFilterDialog">
            x
          </button>
        </header>

        <div class="modal-body">
          <div class="trace-filter-summary">
            <span>
              <strong>集群:</strong>
              {{ traceFilterDialog.trace?.clusterName || 'null' }}
            </span>
            <span>
              <strong>主机 IP:</strong>
              {{ traceFilterDialog.trace?.host || 'null' }}
            </span>
            <span v-if="isFaultCodeFeatureEnabled">
              <strong>故障码:</strong> {{ traceFilterDialog.trace?.faultCode || '-' }}
            </span>
            <span><strong>Trace ID:</strong> {{ traceFilterDialog.trace?.traceId }}</span>
          </div>
          <div class="trace-filter-options">
            <label class="trace-filter-option">
              <input
                v-model="traceFilterDialog.addCluster"
                type="checkbox"
                :disabled="!isTraceFilterValueAvailable(traceFilterDialog.trace?.clusterName)"
              />
              <span>添加集群</span>
            </label>
            <label class="trace-filter-option">
              <input
                v-model="traceFilterDialog.addHost"
                type="checkbox"
                :disabled="!isTraceFilterValueAvailable(traceFilterDialog.trace?.host)"
              />
              <span>添加主机IP</span>
            </label>
            <label v-if="isFaultCodeFeatureEnabled" class="trace-filter-option">
              <input
                v-model="traceFilterDialog.addFaultCode"
                type="checkbox"
                :disabled="!isTraceFilterValueAvailable(traceFilterDialog.trace?.faultCode)"
              />
              <span>添加至故障码</span>
            </label>
            <label class="trace-filter-option">
              <input v-model="traceFilterDialog.addTraceBoard" type="checkbox" />
              <span>添加到Trace看板</span>
            </label>
          </div>
        </div>

        <footer class="modal-actions">
          <button class="ghost-btn" type="button" @click="closeTraceFilterDialog">取消</button>
          <button class="save-btn" type="button" @click="confirmTraceFilterDialog">确定</button>
        </footer>
      </section>
    </div>

    <div v-if="abnormalTraceFilterDialog.open" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content abnormal-trace-filter-modal">
        <header class="modal-header">
          <h2>按集群/主机过滤</h2>
          <button
            class="close-modal"
            type="button"
            title="关闭"
            @click="closeAbnormalTraceFilterDialog"
          >
            x
          </button>
        </header>

        <div class="modal-body abnormal-trace-filter-body">
          <div v-if="abnormalTraceFilterDialog.error" class="dialog-error">
            {{ abnormalTraceFilterDialog.error }}
          </div>

          <div v-if="abnormalTraceFilterDialog.isLoading" class="option-list-state">
            正在加载集群和主机...
          </div>

          <div v-else class="option-list-grid">
            <section class="option-list-section">
              <div class="option-list-title">集群</div>
              <div class="option-scroll-list">
                <label class="option-list-item">
                  <input
                    v-model="abnormalTraceFilterDialog.selectedClusterName"
                    type="radio"
                    value=""
                  />
                  <span>不选择集群</span>
                </label>
                <label
                  v-for="cluster in abnormalTraceFilterDialog.clusters"
                  :key="cluster"
                  class="option-list-item"
                >
                  <input
                    v-model="abnormalTraceFilterDialog.selectedClusterName"
                    type="radio"
                    :value="cluster"
                  />
                  <span>{{ cluster }}</span>
                </label>
              </div>
            </section>

            <section class="option-list-section">
              <div class="option-list-title">主机</div>
              <div class="option-scroll-list">
                <label class="option-list-item">
                  <input v-model="abnormalTraceFilterDialog.selectedHost" type="radio" value="" />
                  <span>不选择主机</span>
                </label>
                <label
                  v-for="host in abnormalTraceFilterDialog.hosts"
                  :key="host"
                  class="option-list-item"
                >
                  <input
                    v-model="abnormalTraceFilterDialog.selectedHost"
                    type="radio"
                    :value="host"
                  />
                  <span>{{ host }}</span>
                </label>
              </div>
            </section>
          </div>
        </div>

        <footer class="modal-actions">
          <button class="ghost-btn" type="button" @click="closeAbnormalTraceFilterDialog">
            取消
          </button>
          <button
            class="save-btn"
            type="button"
            :disabled="abnormalTraceFilterDialog.isLoading"
            @click="confirmAbnormalTraceFilterDialog"
          >
            确定
          </button>
        </footer>
      </section>
    </div>

    <div v-if="latencyHostFilterDialog.open" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content trace-filter-modal">
        <header class="modal-header">
          <h2>🔍 添加筛选条件</h2>
          <button
            class="close-modal"
            type="button"
            title="关闭"
            @click="closeLatencyHostFilterDialog"
          >
            x
          </button>
        </header>

        <div class="modal-body">
          <div class="trace-filter-summary">
            <span><strong>源 IP:</strong> {{ latencyHostFilterDialog.row?.sourceHost }}</span>
            <span><strong>目标 IP:</strong> {{ latencyHostFilterDialog.row?.targetHost }}</span>
          </div>
          <div class="trace-filter-options">
            <label class="trace-filter-option">
              <input v-model="latencyHostFilterDialog.addSourceHost" type="checkbox" />
              <span>添加源IP</span>
            </label>
            <label class="trace-filter-option">
              <input v-model="latencyHostFilterDialog.addTargetHost" type="checkbox" />
              <span>添加目标IP</span>
            </label>
          </div>
        </div>

        <footer class="modal-actions">
          <button class="ghost-btn" type="button" @click="closeLatencyHostFilterDialog">
            取消
          </button>
          <button class="save-btn" type="button" @click="confirmLatencyHostFilterDialog">
            确定
          </button>
        </footer>
      </section>
    </div>

    <div
      v-if="selectedAggregatedEvent"
      class="side-drawer-mask"
      role="dialog"
      aria-modal="true"
      @click.self="closeAggregatedEventDetail"
    >
      <aside class="side-drawer">
        <header class="side-drawer-header">
          <div class="side-drawer-title">
            <h2>聚合事件详情</h2>
            <span class="aggregate-detail-hosts">
              {{ selectedAggregatedEvent.sourceHost }} → {{ selectedAggregatedEvent.targetHost }}
            </span>
          </div>
          <button
            class="close-modal"
            type="button"
            title="关闭"
            @click="closeAggregatedEventDetail"
          >
            x
          </button>
        </header>
        <div class="side-drawer-body">
          <div class="aggregate-detail-metrics">
            <div class="aggregate-detail-metric">
              <span>结果数</span>
              <span class="metric-number metric-number-blue">
                {{ selectedAggregatedEvent.traceCount }}
              </span>
            </div>
            <div class="aggregate-detail-metric">
              <span>异常数</span>
              <span class="metric-number metric-number-red">
                {{ selectedAggregatedEvent.anomalyTraceCount }}
              </span>
            </div>
            <div class="aggregate-detail-metric">
              <span>平均延迟</span>
              <span
                class="metric-number"
                :class="
                  isLatencyMetricAbnormal(
                    'total_latency',
                    selectedAggregatedEvent.event.ave_total_latency,
                  )
                    ? 'metric-number-red'
                    : 'metric-number-green'
                "
              >
                {{ formatMetricValue(selectedAggregatedEvent.event.ave_total_latency) }} ms
              </span>
            </div>
            <div class="aggregate-detail-metric">
              <span>P99延迟</span>
              <span
                class="metric-number"
                :class="
                  isDetailP99LatencyAbnormal(selectedAggregatedEvent.event.p99_total_latency)
                    ? 'metric-number-alert'
                    : 'metric-number-green'
                "
              >
                {{ formatMetricValue(selectedAggregatedEvent.event.p99_total_latency) }} ms
              </span>
            </div>
          </div>

          <section class="aggregate-detail-chart">
            <div class="aggregate-detail-chart-title">时延趋势（P99）</div>
            <div class="latency-series-toggle">
              <span class="latency-series-toggle-label">曲线选择：</span>
              <button
                class="latency-series-toggle-btn latency-series-toggle-all"
                type="button"
                @click="selectAllLatencySeries"
              >
                全选
              </button>
              <button
                class="latency-series-toggle-btn latency-series-toggle-none"
                type="button"
                @click="deselectAllLatencySeries"
              >
                清空
              </button>
              <label
                v-for="series in latencySeriesConfig"
                :key="series.key"
                class="latency-series-checkbox"
              >
                <input
                  type="checkbox"
                  :checked="isLatencySeriesVisible(series.key)"
                  @change="toggleLatencySeriesVisibility(series.key)"
                />
                <span
                  class="latency-series-color-dot"
                  :style="{ backgroundColor: series.color }"
                ></span>
                {{ series.label }}
              </label>
            </div>
            <div class="latency-chart-panel detail-latency-chart-panel">
              <div v-if="isDetailLatencyChartLoading" class="chart-state detail-chart-state">
                正在加载时延趋势...
              </div>
              <div
                v-else-if="detailLatencyChartError"
                class="chart-state chart-error detail-chart-state"
              >
                {{ detailLatencyChartError }}
              </div>
              <div
                v-else-if="detailLatencyChartBuckets.length === 0"
                class="chart-state detail-chart-state"
              >
                暂无时延数据
              </div>
              <div
                v-else
                ref="detailLatencyChartRef"
                class="echarts-latency-chart detail-echarts-latency-chart"
                role="img"
                aria-label="聚合事件时延趋势"
              ></div>
            </div>
          </section>

          <section class="aggregate-parse-results">
            <div class="aggregate-parse-results-header">
              <h3>时延异常 / 阶段时延</h3>
              <span class="parse-result-count">{{ detailParseResultsBadgeCount }} 条</span>
            </div>
            <div class="parse-result-table-wrapper detail-abnormal-trace-wrapper">
              <div class="aggregate-table-frame abnormal-trace-frame detail-abnormal-trace-frame">
                <div class="aggregate-fixed-left">
                  <div class="abnormal-left-grid latency-anomaly-left-grid aggregate-table-header">
                    <div class="aggregate-cell">时间</div>
                    <div class="aggregate-cell">Trace ID</div>
                    <div class="aggregate-cell">Pod IP</div>
                    <div class="aggregate-cell">操作类型</div>
                    <div class="aggregate-cell">集群</div>
                    <div class="aggregate-cell">主机 IP</div>
                  </div>
                  <template
                    v-if="
                      !isDetailParseResultsLoading &&
                      !detailParseResultsError &&
                      detailParseResultRows.length > 0
                    "
                  >
                    <div
                      v-for="row in detailParseResultRows"
                      :key="`${row.id}-fixed`"
                      class="abnormal-left-grid latency-anomaly-left-grid aggregate-body-row"
                    >
                      <div class="aggregate-cell">{{ row.time }}</div>
                      <div class="aggregate-cell trace-id">{{ row.traceId }}</div>
                      <div class="aggregate-cell">{{ row.podIp }}</div>
                      <div class="aggregate-cell">{{ row.operation }}</div>
                      <div class="aggregate-cell">{{ row.clusterName }}</div>
                      <div class="aggregate-cell">{{ row.host }}</div>
                    </div>
                  </template>
                </div>

                <div class="aggregate-latency-scroll">
                  <div class="aggregate-latency-head aggregate-latency-sync">
                    <div class="abnormal-latency-grid aggregate-table-header">
                      <div class="aggregate-cell aggregate-sortable-cell" @click="detailParseResultSort.handleHeaderClick('total_latency')">
                        <span class="sort-header-content">
                          总时延 (ms)
                          <span class="sort-icons">
                            <span class="sort-icon-up" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('total_latency') === 'asc' }">▲</span>
                            <span class="sort-icon-down" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('total_latency') === 'desc' }">▼</span>
                          </span>
                        </span>
                      </div>
                      <div class="aggregate-cell aggregate-sortable-cell" @click="detailParseResultSort.handleHeaderClick('worker_query_meta_latency')">
                        <span class="sort-header-content">
                          查询元数据时延 (ms)
                          <span class="sort-icons">
                            <span class="sort-icon-up" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('worker_query_meta_latency') === 'asc' }">▲</span>
                            <span class="sort-icon-down" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('worker_query_meta_latency') === 'desc' }">▼</span>
                          </span>
                        </span>
                      </div>
                      <div class="aggregate-cell aggregate-sortable-cell" @click="detailParseResultSort.handleHeaderClick('urma_total_latency')">
                        <span class="sort-header-content">
                          URMA总时延 (ms)
                          <span class="sort-icons">
                            <span class="sort-icon-up" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('urma_total_latency') === 'asc' }">▲</span>
                            <span class="sort-icon-down" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('urma_total_latency') === 'desc' }">▼</span>
                          </span>
                        </span>
                      </div>
                      <div class="aggregate-cell aggregate-sortable-cell" @click="detailParseResultSort.handleHeaderClick('urma_link_latency')">
                        <span class="sort-header-content">
                          URMA建链时延 (ms)
                          <span class="sort-icons">
                            <span class="sort-icon-up" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('urma_link_latency') === 'asc' }">▲</span>
                            <span class="sort-icon-down" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('urma_link_latency') === 'desc' }">▼</span>
                          </span>
                        </span>
                      </div>
                      <div class="aggregate-cell aggregate-sortable-cell" @click="detailParseResultSort.handleHeaderClick('c2w_urma_latency')">
                        <span class="sort-header-content">
                          C2W URMA时延 (ms)
                          <span class="sort-icons">
                            <span class="sort-icon-up" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('c2w_urma_latency') === 'asc' }">▲</span>
                            <span class="sort-icon-down" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('c2w_urma_latency') === 'desc' }">▼</span>
                          </span>
                        </span>
                      </div>
                      <div class="aggregate-cell aggregate-sortable-cell" @click="detailParseResultSort.handleHeaderClick('w2w_urma_latency')">
                        <span class="sort-header-content">
                          W2W URMA时延 (ms)
                          <span class="sort-icons">
                            <span class="sort-icon-up" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('w2w_urma_latency') === 'asc' }">▲</span>
                            <span class="sort-icon-down" :class="{ 'sort-icon-active': detailParseResultSort.getSortOrder('w2w_urma_latency') === 'desc' }">▼</span>
                          </span>
                        </span>
                      </div>
                    </div>
                  </div>
                  <div
                    class="aggregate-latency-scrollbar aggregate-latency-sync"
                    @scroll="syncAggregateLatencyScroll"
                  >
                    <div class="aggregate-latency-scrollbar-spacer"></div>
                  </div>
                  <div
                    class="aggregate-latency-body aggregate-latency-sync"
                    @scroll="syncAggregateLatencyScroll"
                  >
                    <template
                      v-if="
                        !isDetailParseResultsLoading &&
                        !detailParseResultsError &&
                        detailParseResultRows.length > 0
                      "
                    >
                      <div
                        v-for="row in detailParseResultRows"
                        :key="`${row.id}-latency`"
                        class="abnormal-latency-grid aggregate-body-row"
                      >
                        <div class="aggregate-cell">
                          <span
                            class="metric-value"
                            :class="{
                              abnormal: isAnomalyListLatencyMetricAbnormal(
                                row,
                                'total_latency',
                                row.totalLatency,
                              ),
                            }"
                          >
                            {{ formatNullableMetricValue(row.totalLatency) }}
                          </span>
                        </div>
                        <div class="aggregate-cell">
                          <span
                            class="metric-value"
                            :class="{
                              abnormal: isAnomalyListLatencyMetricAbnormal(
                                row,
                                'query_meta_latency',
                                row.queryMetaLatency,
                              ),
                            }"
                          >
                            {{ formatNullableMetricValue(row.queryMetaLatency) }}
                          </span>
                        </div>
                        <div class="aggregate-cell">
                          <span
                            class="metric-value"
                            :class="{
                              abnormal: isAnomalyListLatencyMetricAbnormal(
                                row,
                                'urma_total_latency',
                                row.urmaTotalLatency,
                              ),
                            }"
                          >
                            {{ formatNullableMetricValue(row.urmaTotalLatency) }}
                          </span>
                        </div>
                        <div class="aggregate-cell">
                          <span
                            class="metric-value"
                            :class="{
                              abnormal: isAnomalyListLatencyMetricAbnormal(
                                row,
                                'urma_link_latency',
                                row.urmaLinkLatency,
                              ),
                            }"
                          >
                            {{ formatNullableMetricValue(row.urmaLinkLatency) }}
                          </span>
                        </div>
                        <div class="aggregate-cell">
                          <span
                            class="metric-value"
                            :class="{
                              abnormal: isAnomalyListLatencyMetricAbnormal(
                                row,
                                'c2w_urma_latency',
                                row.c2wUrmaLatency,
                              ),
                            }"
                          >
                            {{ formatNullableMetricValue(row.c2wUrmaLatency) }}
                          </span>
                        </div>
                        <div class="aggregate-cell">
                          <span
                            class="metric-value"
                            :class="{
                              abnormal: isAnomalyListLatencyMetricAbnormal(
                                row,
                                'w2w_urma_latency',
                                row.w2wUrmaLatency,
                              ),
                            }"
                          >
                            {{ formatNullableMetricValue(row.w2wUrmaLatency) }}
                          </span>
                        </div>
                      </div>
                    </template>
                  </div>
                </div>

                <div class="aggregate-fixed-actions">
                  <div class="aggregate-cell action-cell aggregate-table-header">Trace分析</div>
                  <template
                    v-if="
                      !isDetailParseResultsLoading &&
                      !detailParseResultsError &&
                      detailParseResultRows.length > 0
                    "
                  >
                    <div
                      v-for="row in detailParseResultRows"
                      :key="`${row.id}-action`"
                      class="aggregate-cell action-cell trace-analysis-actions aggregate-body-row"
                    >
                      <button
                        class="metric-action-btn detail-action-btn"
                        type="button"
                        @click="openParseResultChain(row)"
                      >
                        查看链路
                      </button>
                    </div>
                  </template>
                </div>
              </div>
              <div v-if="isDetailParseResultsLoading" class="aggregate-table-state">
                正在加载日志...
              </div>
              <div
                v-else-if="detailParseResultsError"
                class="aggregate-table-state metric-table-error"
              >
                {{ detailParseResultsError }}
              </div>
              <div v-else-if="detailParseResultRows.length === 0" class="aggregate-table-state">
                暂无时延异常记录
              </div>
            </div>
            <div class="parse-result-pagination">
              <button
                class="ghost-btn"
                type="button"
                :disabled="detailParseResultsPage <= 1 || isDetailParseResultsLoading"
                @click="goDetailParseResultsPage(detailParseResultsPage - 1)"
              >
                上一页
              </button>
              <span class="pagination-pages" aria-label="解析结果页码">
                <button
                  v-for="pageNum in detailParseResultsPageWindow"
                  :key="`detail-parse-results-page-${pageNum}`"
                  class="pagination-page-btn"
                  :class="{ active: pageNum === detailParseResultsPage }"
                  type="button"
                  :disabled="pageNum === detailParseResultsPage || isDetailParseResultsLoading"
                  @click="goDetailParseResultsPage(pageNum)"
                >
                  {{ pageNum }}
                </button>
              </span>
              <button
                class="ghost-btn"
                type="button"
                :disabled="
                  detailParseResultsPage >= detailParseResultsPageCount ||
                  isDetailParseResultsLoading
                "
                @click="goDetailParseResultsPage(detailParseResultsPage + 1)"
              >
                下一页
              </button>
              <span class="pagination-jump">
                <span>第 {{ detailParseResultsPage }} / {{ detailParseResultsPageCount }} 页</span>
                <input
                  v-model="detailParseResultsPageInput"
                  class="pagination-jump-input"
                  type="number"
                  min="1"
                  :max="detailParseResultsPageCount"
                  aria-label="跳转解析结果页码"
                  @keyup.enter="jumpDetailParseResultsPage"
                />
                <button
                  class="pagination-jump-btn"
                  type="button"
                  :disabled="isDetailParseResultsLoading"
                  @click="jumpDetailParseResultsPage"
                >
                  跳转
                </button>
              </span>
            </div>
          </section>
        </div>
      </aside>
    </div>

    <div
      v-if="selectedFaultAggregatedEventDetail"
      class="side-drawer-mask"
      role="dialog"
      aria-modal="true"
      @click.self="closeFaultAggregatedEventDetail"
    >
      <aside class="side-drawer">
        <header class="side-drawer-header">
          <div class="side-drawer-title">
            <h2>聚合事件详情</h2>
            <span class="aggregate-detail-hosts">
              Pod IP: {{ selectedFaultAggregatedEventDetail.podRow.podIp }}
            </span>
          </div>
          <button
            class="close-modal"
            type="button"
            title="关闭"
            @click="closeFaultAggregatedEventDetail"
          >
            x
          </button>
        </header>

        <div class="side-drawer-body">
          <div class="aggregate-detail-metrics fault-detail-metrics">
            <div
              v-for="item in selectedFaultDetailCodeCounts"
              :key="`fault-detail-code-${item.code}`"
              class="aggregate-detail-metric"
            >
              <span>{{ item.label }}</span>
              <span
                class="metric-number"
                :class="item.code === 'all' ? 'metric-number-red' : 'metric-number-blue'"
              >
                {{ item.count }}
              </span>
            </div>
          </div>

          <section class="aggregate-detail-chart">
            <div class="aggregate-detail-chart-title">故障码计数趋势</div>
            <div class="latency-chart-panel detail-latency-chart-panel">
              <div v-if="isFaultDetailChartLoading" class="chart-state detail-chart-state">
                正在加载故障码计数趋势...
              </div>
              <div
                v-else-if="faultDetailChartError"
                class="chart-state chart-error detail-chart-state"
              >
                {{ faultDetailChartError }}
              </div>
              <div
                v-else-if="
                  selectedFaultDetailChartCodes.length === 0 ||
                  faultDetailChartBuckets.length === 0
                "
                class="chart-state detail-chart-state"
              >
                暂无故障码计数趋势数据
              </div>
              <div
                v-else
                ref="faultDetailChartRef"
                class="echarts-latency-chart detail-echarts-latency-chart"
                role="img"
                aria-label="聚合事件故障码计数趋势"
              ></div>
            </div>
          </section>

          <section class="aggregate-parse-results">
            <div class="aggregate-parse-results-header">
              <h3>错误日志</h3>
              <span class="parse-result-count">{{ selectedFaultDetailErrorLogTotal }} 条</span>
            </div>
            <div class="parse-result-table-wrapper fault-detail-log-wrapper">
              <table class="metric-table fault-detail-log-table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>Trace ID</th>
                    <th>集群</th>
                    <th>主机 IP</th>
                    <th>故障码</th>
                    <th>故障模式</th>
                    <th>Trace分析</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="isFaultDetailTraceEventsLoading">
                    <td colspan="7" class="metric-table-state">正在加载错误日志...</td>
                  </tr>
                  <tr v-else-if="faultDetailTraceEventsError">
                    <td colspan="7" class="metric-table-state metric-table-error">
                      {{ faultDetailTraceEventsError }}
                    </td>
                  </tr>
                  <tr v-else-if="faultDetailTraceRows.length === 0">
                    <td colspan="7" class="metric-table-state">暂无错误日志</td>
                  </tr>
                  <template v-else>
                    <tr v-for="row in faultDetailTraceRows" :key="row.id">
                      <td>{{ row.time }}</td>
                      <td class="trace-id">{{ row.traceId }}</td>
                      <td>{{ row.clusterName }}</td>
                      <td>{{ row.host }}</td>
                      <td>{{ row.faultCode || '-' }}</td>
                      <td>{{ getFaultTraceFailureModeLabel(row) }}</td>
                      <td class="trace-actions-cell">
                        <div class="trace-actions">
                          <button
                            class="metric-action-btn detail-action-btn"
                            type="button"
                            @click="openFaultTraceDialog(row)"
                          >
                            查看链路
                          </button>
                        </div>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
            <div v-if="faultDetailTraceEventsTotal > 0" class="parse-result-pagination">
              <button
                class="ghost-btn"
                type="button"
                :disabled="
                  faultDetailTraceEventsPage <= 1 || isFaultDetailTraceEventsLoading
                "
                @click="goFaultDetailTraceEventsPage(faultDetailTraceEventsPage - 1)"
              >
                上一页
              </button>
              <span class="pagination-pages" aria-label="故障详情错误日志页码">
                <button
                  v-for="pageNum in faultDetailTraceEventsPageWindow"
                  :key="`fault-detail-trace-page-${pageNum}`"
                  class="pagination-page-btn"
                  :class="{ active: pageNum === faultDetailTraceEventsPage }"
                  type="button"
                  :disabled="
                    pageNum === faultDetailTraceEventsPage || isFaultDetailTraceEventsLoading
                  "
                  @click="goFaultDetailTraceEventsPage(pageNum)"
                >
                  {{ pageNum }}
                </button>
              </span>
              <button
                class="ghost-btn"
                type="button"
                :disabled="
                  faultDetailTraceEventsPage >= faultDetailTraceEventsPageCount ||
                  isFaultDetailTraceEventsLoading
                "
                @click="goFaultDetailTraceEventsPage(faultDetailTraceEventsPage + 1)"
              >
                下一页
              </button>
              <span class="pagination-jump">
                <span>
                  第 {{ faultDetailTraceEventsPage }} / {{ faultDetailTraceEventsPageCount }} 页
                </span>
                <input
                  v-model="faultDetailTraceEventsPageInput"
                  class="pagination-jump-input"
                  type="number"
                  min="1"
                  :max="faultDetailTraceEventsPageCount"
                  aria-label="跳转故障详情错误日志页码"
                  @keyup.enter="jumpFaultDetailTraceEventsPage"
                />
                <button
                  class="pagination-jump-btn"
                  type="button"
                  :disabled="isFaultDetailTraceEventsLoading"
                  @click="jumpFaultDetailTraceEventsPage"
                >
                  跳转
                </button>
              </span>
            </div>
          </section>
        </div>
      </aside>
    </div>

    <div v-if="selectedTrace" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content trace-modal-content">
        <header class="modal-header">
          <h2>📜 Trace：{{ selectedTrace.traceId }}</h2>
          <button class="close-modal" type="button" title="关闭" @click="closeTraceDialog">
            x
          </button>
        </header>

        <div class="modal-body trace-modal-body">
          <section>
            <h3 class="trace-section-title">📋 运行日志</h3>
            <div class="trace-log-list">
              <div v-if="isTraceLogsLoading" class="trace-empty">正在加载运行日志...</div>
              <div
                v-else-if="traceLogsError && getSelectedTraceLogs().length === 0"
                class="trace-empty metric-table-error"
              >
                {{ traceLogsError }}
              </div>
              <div v-else-if="getSelectedTraceLogs().length === 0" class="trace-empty">
                暂无匹配日志
              </div>
              <template v-else>
                <article
                  v-for="log in getSelectedTraceLogs()"
                  :key="`${log.filename}-${log.time}-${log.pidTid}-${log.rawText}`"
                  class="trace-raw-log-item"
                  :class="log.level === 'ERROR' ? 'log-error' : 'log-info'"
                >
                  <div class="trace-raw-log-meta">
                    <span :class="log.level === 'ERROR' ? 'log-level-error' : 'log-level-info'">
                      {{ log.level }}
                    </span>
                    <span>{{ log.time }}</span>
                    <span>{{ log.formatName }}</span>
                    <span class="trace-raw-log-file">{{ log.filename }}</span>
                    <span
                      v-if="log.level === 'ERROR' && log.faultType && log.faultDomain"
                      class="fault-tag"
                    >
                      🔴 {{ log.faultType }}/{{ log.faultDomain }}
                    </span>
                  </div>
                  <div class="trace-raw-log-table-wrapper">
                    <table class="trace-raw-log-table">
                      <tbody>
                        <tr>
                          <th>格式</th>
                          <td
                            v-for="(column, columnIndex) in log.rawColumns"
                            :key="`${column.label}-${columnIndex}`"
                          >
                            {{ column.label }}
                          </td>
                        </tr>
                        <tr>
                          <th>内容</th>
                          <td
                            v-for="(column, columnIndex) in log.rawColumns"
                            :key="`${column.label}-${columnIndex}`"
                            :title="column.value"
                          >
                            {{ column.value }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </article>
              </template>
            </div>
          </section>

          <section>
            <h3 class="trace-section-title">⏱️ 时延明细</h3>
            <div class="trace-delay-table-wrapper">
              <table class="trace-delay-table">
                <thead>
                  <tr>
                    <th>阶段</th>
                    <th>时延</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="column in traceDelayColumns" :key="column.key">
                    <td class="trace-stage-name">{{ getTraceDelayLabel(column) }}</td>
                    <td
                      :class="{ 'delay-timeout': isTraceDelayAbnormal(selectedTrace, column) }"
                    >
                      {{
                        formatTraceDelayColumnValue(
                          getTraceDelayValue(selectedTrace, column),
                          column,
                        )
                      }}
                    </td>
                    <td
                      class="trace-stage-status"
                      :class="{ 'delay-timeout': isTraceDelayAbnormal(selectedTrace, column) }"
                    >
                      {{ getTraceDelayStatusLabel(selectedTrace, column) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </section>
    </div>

    <div v-if="selectedFaultTrace" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content trace-modal-content fault-trace-modal-content">
        <header class="modal-header">
          <h2>📜 Trace：{{ selectedFaultTrace.traceId }}</h2>
          <button class="close-modal" type="button" title="关闭" @click="closeFaultTraceDialog">
            x
          </button>
        </header>

        <div class="modal-body trace-modal-body">
          <section>
            <h3 class="trace-section-title">📋 运行日志</h3>
            <div class="trace-log-list">
              <div v-if="isTraceLogsLoading" class="trace-empty">正在加载运行日志...</div>
              <div
                v-else-if="traceLogsError && getSelectedFaultTraceLogs().length === 0"
                class="trace-empty metric-table-error"
              >
                {{ traceLogsError }}
              </div>
              <div v-else-if="getSelectedFaultTraceLogs().length === 0" class="trace-empty">
                暂无匹配日志
              </div>
              <template v-else>
                <article
                  v-for="log in getSelectedFaultTraceLogs()"
                  :key="`${log.filename}-${log.time}-${log.pidTid}-${log.rawText}`"
                  class="trace-raw-log-item"
                  :class="[
                    log.level === 'ERROR' ? 'log-error' : 'log-info',
                    { 'log-failure-mode': log.failureModeIds.length > 0 },
                  ]"
                >
                  <div class="trace-raw-log-meta">
                    <span :class="log.level === 'ERROR' ? 'log-level-error' : 'log-level-info'">
                      {{ log.level }}
                    </span>
                    <span>{{ log.time }}</span>
                    <span>{{ log.formatName }}</span>
                    <span class="trace-raw-log-file">{{ log.filename }}</span>
                    <button
                      v-for="mode in getTraceLogFailureModeLabels(log)"
                      :key="mode.id"
                      type="button"
                      class="failure-mode-tag"
                      :class="{ active: selectedFaultTraceFailureModeId === mode.id }"
                      @click="selectFaultTraceFailureMode(mode.id)"
                    >
                      🔴 {{ mode.label }}
                    </button>
                  </div>
                  <div class="trace-raw-log-table-wrapper">
                    <table class="trace-raw-log-table">
                      <tbody>
                        <tr>
                          <th>格式</th>
                          <td
                            v-for="(column, columnIndex) in log.rawColumns"
                            :key="`${column.label}-${columnIndex}`"
                          >
                            {{ column.label }}
                          </td>
                        </tr>
                        <tr>
                          <th>内容</th>
                          <td
                            v-for="(column, columnIndex) in log.rawColumns"
                            :key="`${column.label}-${columnIndex}`"
                            :title="column.value"
                          >
                            {{ column.value }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </article>
              </template>
            </div>
          </section>

          <section>
            <h3 class="trace-section-title">🗃️ 故障模式详情</h3>
            <div v-if="selectedFaultTraceFailureModes.length === 0" class="trace-fault-detail-list">
              <div class="trace-fault-detail-item trace-fault-detail-wide">
                <span class="trace-fault-detail-value">暂无故障模式</span>
              </div>
            </div>
            <div v-else-if="!selectedFaultTraceFailureMode" class="failure-mode-chain-list">
              <div class="failure-mode-chain-item">
                <div class="failure-mode-chain-detail">
                  <span class="trace-fault-detail-value">点击运行日志中的故障模式标签查看详情</span>
                </div>
              </div>
            </div>
            <div v-else class="failure-mode-chain-list">
              <div class="failure-mode-chain-item">
                <div class="failure-mode-chain-header">
                  <span class="failure-mode-chain-id">{{ selectedFaultTraceFailureMode._id }}</span>
                  <span class="failure-mode-chain-name">
                    {{ selectedFaultTraceFailureMode.name || '-' }}
                  </span>
                  <span class="failure-mode-chain-domain">
                    故障域：{{ selectedFaultTraceFailureMode.failure_domain || '-' }}
                  </span>
                </div>
                <div class="failure-mode-chain-detail">
                  <div class="trace-fault-detail-list">
                    <div class="trace-fault-detail-item trace-fault-detail-wide">
                      <span class="trace-fault-detail-label">故障表现</span>
                      <span class="trace-fault-detail-value">
                        {{ selectedFaultTraceFailureMode.symptom || '-' }}
                      </span>
                    </div>
                    <div class="trace-fault-detail-item trace-fault-detail-wide">
                      <span class="trace-fault-detail-label">故障根因</span>
                      <span class="trace-fault-detail-value">
                        {{ selectedFaultTraceFailureMode.root_cause || '-' }}
                      </span>
                    </div>
                    <div class="trace-fault-detail-item trace-fault-detail-wide">
                      <span class="trace-fault-detail-label">解决方法</span>
                      <span class="trace-fault-detail-value">
                        {{ selectedFaultTraceFailureMode.solution || '-' }}
                      </span>
                    </div>
                    <div class="trace-fault-detail-item trace-fault-detail-wide">
                      <span class="trace-fault-detail-label">子故障</span>
                      <span
                        v-if="getFailureModeChildren(selectedFaultTraceFailureMode).length === 0"
                        class="trace-fault-detail-value"
                      >
                        -
                      </span>
                      <div v-else class="trace-sub-fault-block">
                        <div class="trace-sub-fault-list">
                          <button
                            v-for="childId in getFailureModeChildren(selectedFaultTraceFailureMode)"
                            :key="childId"
                            type="button"
                            class="trace-sub-fault"
                            :class="{ active: selectedChildFailureModeId === childId }"
                            @click="selectChildFailureMode(childId)"
                          >
                            {{ getFailureModeChildLabel(childId) }}
                          </button>
                        </div>
                        <div v-if="selectedChildFailureModeId" class="trace-sub-fault-detail">
                          <div v-if="selectedChildFailureMode" class="trace-fault-detail-list">
                            <div class="trace-fault-detail-item">
                              <span class="trace-fault-detail-label">故障名称</span>
                              <span class="trace-fault-detail-value">
                                {{ selectedChildFailureMode.name || '-' }}
                              </span>
                            </div>
                            <div class="trace-fault-detail-item">
                              <span class="trace-fault-detail-label">故障域</span>
                              <span class="trace-fault-detail-value">
                                {{ selectedChildFailureMode.failure_domain || '-' }}
                              </span>
                            </div>
                            <div class="trace-fault-detail-item trace-fault-detail-wide">
                              <span class="trace-fault-detail-label">故障表现</span>
                              <span class="trace-fault-detail-value">
                                {{ selectedChildFailureMode.symptom || '-' }}
                              </span>
                            </div>
                            <div class="trace-fault-detail-item trace-fault-detail-wide">
                              <span class="trace-fault-detail-label">故障根因</span>
                              <span class="trace-fault-detail-value">
                                {{ selectedChildFailureMode.root_cause || '-' }}
                              </span>
                            </div>
                            <div class="trace-fault-detail-item trace-fault-detail-wide">
                              <span class="trace-fault-detail-label">解决方法</span>
                              <span class="trace-fault-detail-value">
                                {{ selectedChildFailureMode.solution || '-' }}
                              </span>
                            </div>
                          </div>
                          <span
                            v-else-if="!hasFailureModeDetailResult(selectedChildFailureModeId)"
                            class="trace-fault-detail-value"
                          >
                            正在加载子故障详情...
                          </span>
                          <span v-else class="trace-fault-detail-value">暂无子故障详情</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </section>
    </div>

    <div v-if="resultsDialog.open" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content results-modal">
        <header class="modal-header">
          <h2>查询结果</h2>
          <button
            class="close-modal"
            type="button"
            title="关闭"
            @click="resultsDialog.open = false"
          >
            x
          </button>
        </header>

        <div class="modal-body results-body">
          <div v-if="resultsDialog.assets.length === 0" class="state-text">未查询到资产库</div>

          <div v-else class="result-list">
            <article v-for="asset in resultsDialog.assets" :key="asset.id" class="result-item">
              <div class="result-main">
                <h3>{{ asset.name }}</h3>
                <p>{{ asset.description }}</p>
                <div class="result-times">
                  <span>创建时间：{{ asset.created_at || '-' }}</span>
                  <span>更新时间：{{ asset.updated_at || '-' }}</span>
                </div>
              </div>

              <button class="view-btn" type="button" @click="viewQueryResult(asset.id)">
                查看
              </button>
            </article>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
