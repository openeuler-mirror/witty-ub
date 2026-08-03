<script setup lang="ts">
import * as echarts from 'echarts'
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  onUpdated,
  reactive,
  ref,
  watch,
} from 'vue'
import type { ECharts, EChartsOption } from 'echarts'
import { useTableSort, type SortField } from './composables/useTableSort'
import diagnosisConfig from '../../../config/diagnosis_config.toml'

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

type AgentChatMessage = {
  id: string
  role: 'user' | 'assistant'
  reasoning: string
  parts?: AgentChatPart[]
  reasoningCollapsed: boolean
  content: string
  status: 'thinking' | 'done' | 'error'
  messageId?: string
}

type AgentChatPart = {
  id: string
  type: 'reasoning' | 'text'
  text: string
  collapsed?: boolean
}

type OpenCodeEvent = {
  type: string
  properties?: {
    sessionID?: string
    messageID?: string
    info?: {
      id?: string
      sessionID?: string
      role?: string
    }
    part?: {
      id?: string
      sessionID?: string
      messageID?: string
      type?: string
      text?: string
    }
    status?: {
      type?: string
    }
    error?: unknown
    message?: string
    data?: unknown
  }
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
  overall_progress?: number
  existed_status: boolean
  created_at: string
}

type LogFilenamePatternKey = keyof typeof diagnosisConfig.log_filename_pattern
type LogAnalyzerThresholdKey =
  | 'total_p99_threshold_ms'
  | 'c2w_p99_threshold_ms'
  | 'w2w_p99_threshold_ms'
  | 'urma_link_p99_threshold_ms'
  | 'query_meta_p99_threshold_ms'

type DiagnosisConfigForm = {
  logFilenamePattern: Record<LogFilenamePatternKey, string[]>
  logAnalyzerParams: Record<LogAnalyzerThresholdKey, number>
}

type DiagnosisConfigApiModel = {
  log_filename_pattern: Record<LogFilenamePatternKey, string[]>
  log_analyzer_params: Record<LogAnalyzerThresholdKey, number>
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
  pod_ips?: string[] | null
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

type StatusCodeKnowledge = {
  status_code: string
  symptom: string
  root_cause: string
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

type TimeWindowAggregatedIpPair = {
  src_ip: string
  dst_ip: string
  log_parse_result_cnt: number
  anomaly_log_parse_result_cnt: number
  anomaly_cnt: number
  ave_total_latency: number | null
  min_total_latency: number | null
  max_total_latency: number | null
  p99_total_latency: number | null
  p95_total_latency: number | null
  ave_query_meta_latency: number | null
  min_query_meta_latency: number | null
  max_query_meta_latency: number | null
  p99_query_meta_latency: number | null
  p95_query_meta_latency: number | null
  ave_urma_total_latency: number | null
  min_urma_total_latency: number | null
  max_urma_total_latency: number | null
  p99_urma_total_latency: number | null
  p95_urma_total_latency: number | null
  ave_urma_link_latency: number | null
  min_urma_link_latency: number | null
  max_urma_link_latency: number | null
  p99_urma_link_latency: number | null
  p95_urma_link_latency: number | null
  ave_c2w_urma_latency: number | null
  min_c2w_urma_latency: number | null
  max_c2w_urma_latency: number | null
  p99_c2w_urma_latency: number | null
  p95_c2w_urma_latency: number | null
  ave_w2w_urma_latency: number | null
  min_w2w_urma_latency: number | null
  max_w2w_urma_latency: number | null
  p99_w2w_urma_latency: number | null
  p95_w2w_urma_latency: number | null
  ave_create_latency: number | null
  min_create_latency: number | null
  max_create_latency: number | null
  p99_create_latency: number | null
  p95_create_latency: number | null
  ave_publish_latency: number | null
  min_publish_latency: number | null
  max_publish_latency: number | null
  p99_publish_latency: number | null
  p95_publish_latency: number | null
  ave_worker_total_latency: number | null
  min_worker_total_latency: number | null
  max_worker_total_latency: number | null
  p99_worker_total_latency: number | null
  p95_worker_total_latency: number | null
}

type TimeWindowAggregatedEvent = {
  start_time: string
  end_time: string
  total_cnt: number
  anomaly_cnt: number
  ave_total_latency: number | null
  min_total_latency: number | null
  max_total_latency: number | null
  p99_total_latency: number | null
  p95_total_latency: number | null
  ave_query_meta_latency: number | null
  p99_query_meta_latency: number | null
  p95_query_meta_latency: number | null
  ave_urma_total_latency: number | null
  p99_urma_total_latency: number | null
  p95_urma_total_latency: number | null
  ave_urma_link_latency: number | null
  p99_urma_link_latency: number | null
  p95_urma_link_latency: number | null
  ave_c2w_urma_latency: number | null
  p99_c2w_urma_latency: number | null
  p95_c2w_urma_latency: number | null
  ave_w2w_urma_latency: number | null
  p99_w2w_urma_latency: number | null
  p95_w2w_urma_latency: number | null
  ave_create_latency: number | null
  p99_create_latency: number | null
  p95_create_latency: number | null
  ave_publish_latency: number | null
  p99_publish_latency: number | null
  p95_publish_latency: number | null
  ave_worker_total_latency: number | null
  p99_worker_total_latency: number | null
  p95_worker_total_latency: number | null
  ip_pairs: TimeWindowAggregatedIpPair[]
}

type LatencyDetailRow = {
  id: string
  sourcePodIp: string
  targetPodIp: string
  traceCount: number
  anomalyTraceCount: number
  event: AggregatedEventModel
  startTime?: string
  endTime?: string
  operation?: string
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
  operation?: string
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
  sourcePodIp: string
  targetPodIp: string
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
  srcIp: string
  dstIp: string
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

type SrcDstAggregatedFailureEventModel = {
  src_ip: string
  dst_ip: string
  status_code_cnt: Record<string, number>
}

type ListPodAggregatedFailureEventMsg = {
  total: number
  events: PodAggregatedFailureEventModel[]
}

type ListSrcDstAggregatedFailureEventMsg = {
  total: number
  events: SrcDstAggregatedFailureEventModel[]
}

type FaultAggregateInterval = 'hour' | 'minute' | 'second'

type TraceRawLogColumn = {
  label: string
  value: string
}

type TraceLogRow = {
  time: string
  level: string
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
  host_name?: string | null
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
  host_names?: Array<string | null>
  cluster_names?: string[]
  timestamp?: string
  status_code?: string
  failure_mode?: string
  operation?: string
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
  createLatency: number | null
  publishLatency: number | null
  workerTotalLatency: number | null
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
  createLatency: number | null
  publishLatency: number | null
  workerTotalLatency: number | null
  raw: LogParseResultModel
}

type LatencyChartRange = {
  centerTime: number
  startTime: number
  endTime: number
  label: string
}

type LatencyPercentileValue = 'p99' | 'p9999' | 'pmax' | 'ave'

type ApiResponse<T> = {
  code?: number
  message?: string
  result?: T
  data?: T
}

type UploadLogFilesResult = {
  log_file_ids?: string[]
}

type OpenCodeHealthResult = {
  healthy?: boolean
  version?: string
}

type OpenCodeModel = {
  id: string
  providerID: string
  name: string
}

type OpenCodeProvider = {
  id: string
  name: string
  models: Record<string, OpenCodeModel>
}

type OpenCodeProviderResult = {
  all: OpenCodeProvider[]
  connected: string[]
  default: Record<string, string>
}

type AgentView = 'login' | 'models' | 'providers' | 'new-models' | 'chat'

type GetLogFileResult = {
  log_file?: LogFileModel | null
}

type LogParseOptions = {
  clusters?: string[]
  hosts?: string[]
}

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const defaultAgentApiBase = (import.meta.env.VITE_OPENCODE_API_BASE_URL ?? '/agent-api').replace(
  /\/$/,
  '',
)
const agentName = 'witty-ub-diagnostician'
const agentUserAbortMessage = '用户终止响应'
const isAgentChatOpen = ref(false)
const agentView = ref<AgentView>('login')
const agentUsername = ref('')
const agentPassword = ref('')
const agentServerAddress = ref('')
const agentApiBase = ref(defaultAgentApiBase)
const agentAuthHeader = ref('')
const agentProviders = ref<OpenCodeProviderResult | null>(null)
const selectedAgentProvider = ref<OpenCodeProvider | null>(null)
const selectedAgentModel = ref<OpenCodeModel | null>(null)
const providerSearch = ref('')
const modelSearch = ref('')
const providerApiKey = ref('')
const expandedProviderId = ref('')
const isAgentAuthorizing = ref(false)
const isAgentSending = ref(false)
const isAgentAborting = ref(false)
const agentChatInput = ref('')
const agentSessionId = ref('')
const agentConnectionError = ref('')
const agentConnectionState = ref<'connected' | 'connecting' | 'disconnected'>('connecting')
const isAgentLoggingIn = ref(false)
const agentChatMessages = ref<AgentChatMessage[]>([])
const agentChatMessagesRef = ref<HTMLElement | null>(null)
const isAgentConnectionUnavailable = computed(() => agentConnectionState.value !== 'connected')
const connectedAgentModels = computed(() => {
  const data = agentProviders.value
  if (!data) return []
  const connected = new Set(data.connected)
  const query = modelSearch.value.trim().toLocaleLowerCase()
  return data.all.flatMap((provider) =>
    connected.has(provider.id)
      ? Object.values(provider.models)
          .filter(
            (model) =>
              !query ||
              provider.name.toLocaleLowerCase().includes(query) ||
              model.name.toLocaleLowerCase().includes(query),
          )
          .map((model) => ({ provider, model }))
      : [],
  )
})
const availableAgentProviders = computed(() => {
  const data = agentProviders.value
  if (!data) return []
  const ids = new Set(Object.keys(data.default))
  const query = providerSearch.value.trim().toLocaleLowerCase()
  return data.all.filter(
    (provider) =>
      ids.has(provider.id) && (!query || provider.name.toLocaleLowerCase().includes(query)),
  )
})
const newProviderModels = computed(() =>
  selectedAgentProvider.value ? Object.values(selectedAgentProvider.value.models) : [],
)
const assistantMessageIds = new Set<string>()
let agentEventController: AbortController | null = null
let isAgentEventStreamConnected = false
let agentLocalMessageSequence = 0
let agentHealthCheckSequence = 0
let agentRequestSequence = 0
let agentEventStreamSequence = 0
let shouldIgnoreNextAgentAbortError = false

const nextAgentLocalMessageId = () => {
  agentLocalMessageSequence += 1
  return `agent-message-${agentLocalMessageSequence}`
}

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')

const renderInlineMarkdown = (value: string) => {
  let html = escapeHtml(value)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  return html
}

const splitMarkdownTableRow = (line: string) => {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '')
  return trimmed.split('|').map((cell) => cell.trim())
}

const isMarkdownTableSeparator = (line: string) => {
  const cells = splitMarkdownTableRow(line)
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell))
}

const getMarkdownLine = (lines: string[], index: number) => lines[index] ?? ''

const isMarkdownTableStart = (lines: string[], index: number) =>
  index + 1 < lines.length &&
  getMarkdownLine(lines, index).includes('|') &&
  isMarkdownTableSeparator(getMarkdownLine(lines, index + 1))

const renderAgentMarkdown = (markdown: string) => {
  const lines = markdown.replace(/\r\n?/g, '\n').split('\n')
  const blocks: string[] = []
  let index = 0

  while (index < lines.length) {
    const line = getMarkdownLine(lines, index)
    const trimmed = line.trim()

    if (!trimmed) {
      index += 1
      continue
    }

    if (trimmed.startsWith('```')) {
      const codeLines: string[] = []
      index += 1
      while (index < lines.length && !getMarkdownLine(lines, index).trim().startsWith('```')) {
        codeLines.push(getMarkdownLine(lines, index))
        index += 1
      }
      if (index < lines.length) index += 1
      blocks.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
      continue
    }

    if (isMarkdownTableStart(lines, index)) {
      const headers = splitMarkdownTableRow(getMarkdownLine(lines, index))
      index += 2
      const rows: string[][] = []
      while (
        index < lines.length &&
        getMarkdownLine(lines, index).includes('|') &&
        getMarkdownLine(lines, index).trim()
      ) {
        rows.push(splitMarkdownTableRow(getMarkdownLine(lines, index)))
        index += 1
      }
      const headHtml = headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join('')
      const bodyHtml = rows
        .map((row) => {
          const cells = headers.map((_, cellIndex) => row[cellIndex] ?? '')
          return `<tr>${cells.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join('')}</tr>`
        })
        .join('')
      blocks.push(
        `<div class="agent-markdown-table-wrap"><table><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`,
      )
      continue
    }

    if (/^#{1,4}\s+/.test(trimmed)) {
      const level = Math.min(trimmed.match(/^#+/)?.[0].length ?? 2, 4)
      const text = trimmed.replace(/^#{1,4}\s+/, '')
      blocks.push(`<h${level}>${renderInlineMarkdown(text)}</h${level}>`)
      index += 1
      continue
    }

    if (/^[-*]\s+/.test(trimmed)) {
      const items: string[] = []
      while (index < lines.length && /^[-*]\s+/.test(getMarkdownLine(lines, index).trim())) {
        items.push(
          `<li>${renderInlineMarkdown(
            getMarkdownLine(lines, index)
              .trim()
              .replace(/^[-*]\s+/, ''),
          )}</li>`,
        )
        index += 1
      }
      blocks.push(`<ul>${items.join('')}</ul>`)
      continue
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = []
      while (index < lines.length && /^\d+\.\s+/.test(getMarkdownLine(lines, index).trim())) {
        items.push(
          `<li>${renderInlineMarkdown(
            getMarkdownLine(lines, index)
              .trim()
              .replace(/^\d+\.\s+/, ''),
          )}</li>`,
        )
        index += 1
      }
      blocks.push(`<ol>${items.join('')}</ol>`)
      continue
    }

    const paragraphLines = [trimmed]
    index += 1
    while (
      index < lines.length &&
      getMarkdownLine(lines, index).trim() &&
      !getMarkdownLine(lines, index).trim().startsWith('```') &&
      !isMarkdownTableStart(lines, index) &&
      !/^#{1,4}\s+/.test(getMarkdownLine(lines, index).trim()) &&
      !/^[-*]\s+/.test(getMarkdownLine(lines, index).trim()) &&
      !/^\d+\.\s+/.test(getMarkdownLine(lines, index).trim())
    ) {
      paragraphLines.push(getMarkdownLine(lines, index).trim())
      index += 1
    }
    blocks.push(`<p>${paragraphLines.map(renderInlineMarkdown).join('<br>')}</p>`)
  }

  return blocks.join('')
}

const scrollAgentChatToBottom = async () => {
  await nextTick()
  const container = agentChatMessagesRef.value
  if (container) {
    container.scrollTop = container.scrollHeight
  }
}

const getPendingAssistantMessage = () =>
  [...agentChatMessages.value]
    .reverse()
    .find((message) => message.role === 'assistant' && message.status === 'thinking')

const getAgentMessagePart = (
  message: AgentChatMessage,
  type: AgentChatPart['type'],
  partId: string,
) => {
  const id = `${type}:${partId}`
  message.parts ||= []
  let messagePart = message.parts.find((part) => part.id === id)
  if (!messagePart) {
    messagePart = { id, type, text: '', collapsed: false }
    message.parts.push(messagePart)
  }
  return messagePart
}

const syncAgentMessageText = (message: AgentChatMessage) => {
  const parts = message.parts ?? []
  message.reasoning = parts
    .filter((part) => part.type === 'reasoning' && part.text)
    .map((part) => part.text)
    .join('\n\n')
  message.content = parts
    .filter((part) => part.type === 'text' && part.text)
    .map((part) => part.text)
    .join('\n\n')
}

const getAgentDisplayParts = (message: AgentChatMessage): AgentChatPart[] => {
  if (message.role !== 'assistant') return []
  const parts = (message.parts ?? []).filter((part) => part.text || part.type === 'reasoning')
  if (parts.length > 0) return parts
  if (message.content) return [{ id: `${message.id}:content`, type: 'text', text: message.content }]
  if (message.status === 'thinking') {
    return [{ id: `${message.id}:reasoning-placeholder`, type: 'reasoning', text: '' }]
  }
  return []
}

const extractOpenCodeError = (payload: unknown, fallback: string): string => {
  if (typeof payload === 'string' && payload.trim()) return payload.trim()
  if (!payload || typeof payload !== 'object') return fallback
  const value = payload as {
    message?: string
    error?: unknown
    data?: unknown
    cause?: unknown
  }
  return (
    extractOpenCodeError(value.error, '') ||
    extractOpenCodeError(value.data, '') ||
    extractOpenCodeError(value.cause, '') ||
    value.message ||
    fallback
  )
}

const requestAgentApi = async <T,>(path: string, init: RequestInit = {}) => {
  const response = await fetch(`${agentApiBase.value}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(agentAuthHeader.value ? { Authorization: agentAuthHeader.value } : {}),
      ...init.headers,
    },
  })
  const payload = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(extractOpenCodeError(payload, `Agent 服务请求失败：${response.status}`))
  }
  return payload as T
}

const normalizeAgentServerAddress = (address: string) => {
  const value = address.trim().replace(/\/+$/, '')
  if (!value) return defaultAgentApiBase
  return /^https?:\/\//i.test(value) ? value : `http://${value}`
}

const getAgentRequestModelId = (provider: OpenCodeProvider, model: OpenCodeModel) => {
  const providerPrefix = `${provider.id}/`
  return model.id.startsWith(providerPrefix) ? model.id.slice(providerPrefix.length) : model.id
}

const connectAgent = async (serverAddress: string, authHeader = '') => {
  if (isAgentLoggingIn.value) return
  isAgentLoggingIn.value = true
  agentConnectionError.value = ''
  agentConnectionState.value = 'connecting'
  agentApiBase.value = normalizeAgentServerAddress(serverAddress)
  agentAuthHeader.value = authHeader
  try {
    const health = await requestAgentApi<OpenCodeHealthResult>('/global/health')
    if (!health?.healthy) throw new Error('OpenCode Server 健康检查未通过。')
    agentProviders.value = await requestAgentApi<OpenCodeProviderResult>('/provider')
    agentConnectionState.value = 'connected'
    agentView.value = 'models'
  } catch (error) {
    agentConnectionState.value = 'disconnected'
    agentConnectionError.value = error instanceof Error ? error.message : '登录失败。'
  } finally {
    isAgentLoggingIn.value = false
  }
}

const loginLocalAgent = () => connectAgent('http://127.0.0.1:4096')

const loginAgent = async () => {
  if (!agentUsername.value.trim() || !agentPassword.value) {
    agentConnectionError.value = '请完整填写用户名和密码。'
    return
  }
  if (!agentServerAddress.value.trim()) {
    agentConnectionError.value = '请输入远程服务器的 IP:端口号。'
    return
  }
  const authHeader = `Basic ${btoa(
    unescape(encodeURIComponent(`${agentUsername.value}:${agentPassword.value}`)),
  )}`
  await connectAgent(agentServerAddress.value, authHeader)
}

const chooseAgentModel = async (provider: OpenCodeProvider, model: OpenCodeModel) => {
  selectedAgentProvider.value = provider
  selectedAgentModel.value = { ...model, id: getAgentRequestModelId(provider, model) }
  agentView.value = 'chat'
  agentSessionId.value = ''
  await scrollAgentChatToBottom()
  ensureAgentSession().catch((error: unknown) => {
    agentConnectionState.value = 'disconnected'
    agentConnectionError.value = error instanceof Error ? error.message : '无法创建 Agent 会话。'
  })
}

const authorizeAgentProvider = async (provider: OpenCodeProvider) => {
  if (!providerApiKey.value.trim() || isAgentAuthorizing.value) return
  isAgentAuthorizing.value = true
  agentConnectionError.value = ''
  try {
    await requestAgentApi<boolean>(`/auth/${encodeURIComponent(provider.id)}`, {
      method: 'PUT',
      body: JSON.stringify({ type: 'api', key: providerApiKey.value.trim() }),
    })
    agentProviders.value = await requestAgentApi<OpenCodeProviderResult>('/provider')
    selectedAgentProvider.value =
      agentProviders.value.all.find((item) => item.id === provider.id) || provider
    providerApiKey.value = ''
    agentView.value = 'new-models'
  } catch (error) {
    agentConnectionError.value = error instanceof Error ? error.message : 'API key 认证失败。'
  } finally {
    isAgentAuthorizing.value = false
  }
}

const checkAgentHealth = async () => {
  const checkSequence = ++agentHealthCheckSequence
  agentConnectionState.value = 'connecting'

  try {
    const health = await requestAgentApi<OpenCodeHealthResult>('/global/health')
    if (checkSequence !== agentHealthCheckSequence) return

    if (health?.healthy) {
      agentConnectionState.value = 'connected'
      agentConnectionError.value = ''
    } else {
      agentConnectionState.value = 'disconnected'
      agentConnectionError.value = 'OpenCode Server 健康检查未通过。'
    }
  } catch (error) {
    if (checkSequence !== agentHealthCheckSequence) return
    agentConnectionState.value = 'disconnected'
    agentConnectionError.value =
      error instanceof Error
        ? `无法连接到 OpenCode Server：${error.message}`
        : '无法连接到 OpenCode Server。'
  }
}

const markAgentResponseFailed = (message: string) => {
  const pending = getPendingAssistantMessage()
  if (pending) {
    pending.status = 'error'
    pending.content = pending.content || message
  }
  isAgentSending.value = false
  isAgentAborting.value = false
  agentConnectionError.value = message
  void scrollAgentChatToBottom()
}

const markAgentResponseAborted = () => {
  const pending = getPendingAssistantMessage()
  if (pending) {
    pending.status = 'done'
    pending.reasoningCollapsed = true
    pending.parts = [{ id: `${pending.id}:aborted`, type: 'text', text: agentUserAbortMessage }]
    syncAgentMessageText(pending)
  }
  isAgentSending.value = false
  agentConnectionError.value = ''
  void scrollAgentChatToBottom()
}

const handleOpenCodeEvent = (event: MessageEvent<string>) => {
  let payload: OpenCodeEvent
  try {
    payload = JSON.parse(event.data) as OpenCodeEvent
  } catch {
    return
  }

  const properties = payload.properties
  const eventSessionId =
    properties?.sessionID || properties?.info?.sessionID || properties?.part?.sessionID
  if (!eventSessionId || eventSessionId !== agentSessionId.value) return

  if (payload.type === 'message.updated' && properties?.info?.role === 'assistant') {
    const messageId = properties.info.id
    const pending = getPendingAssistantMessage()
    if (messageId) {
      assistantMessageIds.add(messageId)
      if (pending && !pending.messageId) pending.messageId = messageId
    }
    return
  }

  if (payload.type === 'message.part.updated' && properties?.part) {
    const part = properties.part
    if (!part.messageID || !assistantMessageIds.has(part.messageID)) return
    const target =
      agentChatMessages.value.find((message) => message.messageId === part.messageID) ||
      getPendingAssistantMessage()
    if (!target) return
    target.messageId = part.messageID
    if (part.type === 'reasoning') {
      const reasoningPartId = part.id || 'reasoning'
      getAgentMessagePart(target, 'reasoning', reasoningPartId).text = part.text || ''
      syncAgentMessageText(target)
    } else if (part.type === 'text') {
      const textPartId = part.id || 'text'
      getAgentMessagePart(target, 'text', textPartId).text = part.text || ''
      syncAgentMessageText(target)
    }
    void scrollAgentChatToBottom()
    return
  }

  if (
    payload.type === 'session.idle' ||
    (payload.type === 'session.status' && properties?.status?.type === 'idle')
  ) {
    const pending = getPendingAssistantMessage()
    if (pending) {
      pending.status = 'done'
      if (!pending.content) pending.content = 'Agent 已完成处理，但没有返回文本结果。'
      pending.reasoningCollapsed = true
    }
    isAgentSending.value = false
    void scrollAgentChatToBottom()
    return
  }

  if (payload.type === 'session.error') {
    if (shouldIgnoreNextAgentAbortError) {
      shouldIgnoreNextAgentAbortError = false
      isAgentSending.value = false
      isAgentAborting.value = false
      agentConnectionError.value = ''
      return
    }
    markAgentResponseFailed(
      extractOpenCodeError(properties?.error ?? properties, 'Agent 处理消息时发生错误。'),
    )
  }
}

const closeAgentEventStream = () => {
  agentEventController?.abort()
  agentEventController = null
  isAgentEventStreamConnected = false
  agentEventStreamSequence += 1
}

const dispatchAgentEventStreamChunk = (chunk: string) => {
  const data = chunk
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
  if (!data) return
  handleOpenCodeEvent(new MessageEvent('message', { data }))
}

const readAgentEventStream = async (
  response: Response,
  controller: AbortController,
  streamSequence: number,
) => {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('Agent 服务没有返回事件流。')

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split(/\r?\n\r?\n/)
      buffer = chunks.pop() ?? ''
      chunks.forEach(dispatchAgentEventStreamChunk)
    }
    buffer += decoder.decode()
    if (buffer.trim()) dispatchAgentEventStreamChunk(buffer)

    if (streamSequence === agentEventStreamSequence && !controller.signal.aborted) {
      isAgentEventStreamConnected = false
      agentConnectionError.value = 'Agent 事件流连接已断开。'
      agentConnectionState.value = 'disconnected'
    }
  } catch (error) {
    if (streamSequence !== agentEventStreamSequence || controller.signal.aborted) return
    isAgentEventStreamConnected = false
    agentConnectionError.value =
      error instanceof Error
        ? `Agent 事件流连接已断开：${error.message}`
        : 'Agent 事件流连接已断开。'
    agentConnectionState.value = 'disconnected'
  }
}

const connectAgentEvents = async () => {
  closeAgentEventStream()
  agentConnectionState.value = 'connecting'
  const eventUrl = new URL(`${agentApiBase.value}/event`, window.location.href)
  const controller = new AbortController()
  const streamSequence = agentEventStreamSequence
  agentEventController = controller
  let timedOut = false
  const timeoutId = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, 10000)

  try {
    const response = await fetch(eventUrl.toString(), {
      headers: {
        Accept: 'text/event-stream',
        ...(agentAuthHeader.value ? { Authorization: agentAuthHeader.value } : {}),
      },
      signal: controller.signal,
    })
    window.clearTimeout(timeoutId)
    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(extractOpenCodeError(payload, `Agent 事件流连接失败：${response.status}`))
    }
    if (!response.body) throw new Error('Agent 服务没有返回事件流。')
    agentConnectionError.value = ''
    agentConnectionState.value = 'connected'
    isAgentEventStreamConnected = true
    agentHealthCheckSequence += 1
    void readAgentEventStream(response, controller, streamSequence)
  } catch (error) {
    window.clearTimeout(timeoutId)
    isAgentEventStreamConnected = false
    agentConnectionState.value = 'disconnected'
    if (timedOut) throw new Error('连接 Agent 事件流超时。')
    throw error
  }
}

const ensureAgentSession = async () => {
  if (!agentSessionId.value) {
    const session = await requestAgentApi<{ id: string }>('/session', {
      method: 'POST',
      body: JSON.stringify({ title: 'KVC 时延与通断故障诊断' }),
    })
    if (!session?.id) throw new Error('Agent 服务没有返回会话 ID。')
    agentSessionId.value = session.id
  }
  if (!isAgentEventStreamConnected) {
    await connectAgentEvents()
  }
}

const toggleAgentChat = () => {
  isAgentChatOpen.value = !isAgentChatOpen.value
  if (isAgentChatOpen.value) {
    void scrollAgentChatToBottom()
  }
}

const sendAgentMessage = async () => {
  if (isAgentSending.value) {
    await abortAgentSession()
    return
  }

  const question = agentChatInput.value.trim()
  if (!question || isAgentAborting.value) return
  if (!selectedAgentProvider.value || !selectedAgentModel.value) {
    agentConnectionError.value = '请先选择一个模型。'
    return
  }

  shouldIgnoreNextAgentAbortError = false
  agentChatInput.value = ''
  agentConnectionError.value = ''
  agentChatMessages.value.push({
    id: nextAgentLocalMessageId(),
    role: 'user',
    reasoning: '',
    reasoningCollapsed: false,
    content: question,
    status: 'done',
  })
  const assistantMessage: AgentChatMessage = {
    id: nextAgentLocalMessageId(),
    role: 'assistant',
    reasoning: '',
    parts: [],
    reasoningCollapsed: false,
    content: '',
    status: 'thinking',
  }
  agentChatMessages.value.push(assistantMessage)
  isAgentSending.value = true
  const requestSequence = ++agentRequestSequence
  await scrollAgentChatToBottom()

  try {
    await ensureAgentSession()
    if (requestSequence !== agentRequestSequence) return
    const contextPrefix = selectedAssetId.value
      ? `当前页面选中的知识库 ID 是 ${selectedAssetId.value}。`
      : ''
    await requestAgentApi<void>(
      `/session/${encodeURIComponent(agentSessionId.value)}/prompt_async`,
      {
        method: 'POST',
        body: JSON.stringify({
          agent: agentName,
          model: {
            providerID: selectedAgentProvider.value.id,
            modelID: getAgentRequestModelId(selectedAgentProvider.value, selectedAgentModel.value),
          },
          parts: [
            { type: 'text', text: `${contextPrefix}${contextPrefix ? '\n\n' : ''}${question}` },
          ],
        }),
      },
    )
  } catch (error) {
    agentConnectionState.value = 'disconnected'
    markAgentResponseFailed(error instanceof Error ? error.message : '消息发送失败。')
  }
}

const abortAgentSession = async () => {
  if (!isAgentSending.value || isAgentAborting.value) return
  isAgentAborting.value = true
  shouldIgnoreNextAgentAbortError = true
  agentRequestSequence += 1
  agentConnectionError.value = ''

  try {
    if (agentSessionId.value) {
      await requestAgentApi<boolean>(`/session/${encodeURIComponent(agentSessionId.value)}/abort`, {
        method: 'POST',
      })
    }
    markAgentResponseAborted()
  } catch (error) {
    shouldIgnoreNextAgentAbortError = false
    agentConnectionState.value = 'disconnected'
    agentConnectionError.value = error instanceof Error ? error.message : '停止会话失败。'
  } finally {
    isAgentAborting.value = false
    void scrollAgentChatToBottom()
  }
}
const assetPageSize = 5
const logFilesPageSize = 10
const aggregateEventPageSize = 10
const abnormalTracesPageSize = 10
const faultAggregatedEventPageSize = 10
const faultAggregatedEventPodPageSize = 5
const faultTraceEventsPageSize = 10
const detailParseResultsPageSize = 10
const faultDetailTraceEventsPageSize = 10
const logFilesPollIntervalMs = 3_000
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
const isParseConfigDrawerOpen = ref(false)
const isDiagnosisConfigLoading = ref(false)
const isDiagnosisConfigSaving = ref(false)
const diagnosisConfigError = ref('')
const diagnosisConfigResetSnapshot = ref('')
const diagnosisConfigImportAssets = ref<LogKnowledge[]>([])
const diagnosisConfigImportAssetId = ref('')
const isDiagnosisConfigImportListLoading = ref(false)
const isDiagnosisConfigImporting = ref(false)
const diagnosisConfigImportMessage = ref('')
const diagnosisConfigsByAsset = ref<Record<string, DiagnosisConfigForm>>({})
const patternInputs = reactive<Record<LogFilenamePatternKey, string>>({
  ds_client_access_log_file: '',
  ds_client_info_log_file: '',
  ds_worker_access_log_file: '',
  ds_worker_info_log_file: '',
  resource_log_file: '',
})
const patternTypeOptions: Array<{
  key: LogFilenamePatternKey
  label: string
  description: string
}> = [
  {
    key: 'ds_client_access_log_file',
    label: 'SDK 客户端接口日志',
    description: '客户端请求与调用链日志',
  },
  {
    key: 'ds_client_info_log_file',
    label: 'SDK 客户端运行日志',
    description: '客户端运行与状态日志',
  },
  {
    key: 'ds_worker_access_log_file',
    label: 'Worker 接口日志',
    description: 'Worker 请求接口日志',
  },
  {
    key: 'ds_worker_info_log_file',
    label: 'Worker 运行日志',
    description: 'Worker 运行与状态日志',
  },
  { key: 'resource_log_file', label: '资源日志', description: '资源监控与资源状态日志' },
]
const analyzerThresholdOptions: Array<{
  key: LogAnalyzerThresholdKey
  label: string
  description: string
}> = [
  { key: 'total_p99_threshold_ms', label: '总时延 P99 阈值', description: '端到端总耗时' },
  { key: 'c2w_p99_threshold_ms', label: 'C2W 时延 P99 阈值', description: 'Client 到 Worker' },
  { key: 'w2w_p99_threshold_ms', label: 'W2W 时延 P99 阈值', description: 'Worker 间调用' },
  {
    key: 'urma_link_p99_threshold_ms',
    label: 'URMA 建链 P99 阈值',
    description: 'URMA 链路建立耗时',
  },
  {
    key: 'query_meta_p99_threshold_ms',
    label: 'QueryMeta 时延阈值',
    description: '查询元数据时延阈值',
  },
]
const logFiles = ref<LogFileModel[]>([])
const isLogFilesLoading = ref(false)
const isLogFilesPolling = ref(false)
const logFilesPage = ref(1)
const logFilesTotal = ref(0)
const refreshingFileIds = ref<Set<string>>(new Set())
const taskDetailsById = ref<Record<string, TaskModel>>({})
const loadingTaskDetailIds = ref<Set<string>>(new Set())
const logFileAnomalyCntById = ref<Record<string, number>>({})
const logFileTraceFailureEventCntById = ref<Record<string, number>>({})
const loadedAnomalyLogFileIds = ref<Set<string>>(new Set())
const loadingAnomalyLogFileIds = ref<Set<string>>(new Set())
const latencyMetricsByPercentile = reactive<Record<LatencyPercentileValue, LatencyMetricItem[]>>({
  p99: [],
  p9999: [],
  pmax: [],
  ave: [],
})
const isLatencyChartLoading = ref(false)
const latencyChartError = ref('')
const aggregatedEvents = ref<AggregatedEventModel[]>([])
const isLatencyDetailLoading = ref(false)
const latencyDetailError = ref('')
const aggregateEventPage = ref(1)
const aggregateEventTotal = ref(0)
const selectedLatencyPercentile = ref<LatencyPercentileValue>('p99')
const selectedLatencyStat = ref<'total' | 'p99' | 'p95' | 'ave' | 'min' | 'max'>('p99')
const selectedOperation = ref<'get' | 'set'>('get')

const createDefaultDiagnosisConfig = (): DiagnosisConfigForm => ({
  logFilenamePattern: {
    ds_client_access_log_file: [...diagnosisConfig.log_filename_pattern.ds_client_access_log_file],
    ds_client_info_log_file: [...diagnosisConfig.log_filename_pattern.ds_client_info_log_file],
    ds_worker_access_log_file: [...diagnosisConfig.log_filename_pattern.ds_worker_access_log_file],
    ds_worker_info_log_file: [...diagnosisConfig.log_filename_pattern.ds_worker_info_log_file],
    resource_log_file: [...diagnosisConfig.log_filename_pattern.resource_log_file],
  },
  logAnalyzerParams: {
    total_p99_threshold_ms: diagnosisConfig.log_analyzer_params.total_p99_threshold_ms,
    c2w_p99_threshold_ms: diagnosisConfig.log_analyzer_params.c2w_p99_threshold_ms,
    w2w_p99_threshold_ms: diagnosisConfig.log_analyzer_params.w2w_p99_threshold_ms,
    urma_link_p99_threshold_ms: diagnosisConfig.log_analyzer_params.urma_link_p99_threshold_ms,
    query_meta_p99_threshold_ms: diagnosisConfig.log_analyzer_params.query_meta_p99_threshold_ms,
  },
})

const cloneDiagnosisConfig = (config: DiagnosisConfigForm): DiagnosisConfigForm =>
  JSON.parse(JSON.stringify(config)) as DiagnosisConfigForm

const fromDiagnosisConfigApi = (config: DiagnosisConfigApiModel): DiagnosisConfigForm => ({
  logFilenamePattern: {
    ds_client_access_log_file: [...config.log_filename_pattern.ds_client_access_log_file],
    ds_client_info_log_file: [...config.log_filename_pattern.ds_client_info_log_file],
    ds_worker_access_log_file: [...config.log_filename_pattern.ds_worker_access_log_file],
    ds_worker_info_log_file: [...config.log_filename_pattern.ds_worker_info_log_file],
    resource_log_file: [...config.log_filename_pattern.resource_log_file],
  },
  logAnalyzerParams: {
    total_p99_threshold_ms: config.log_analyzer_params.total_p99_threshold_ms,
    c2w_p99_threshold_ms: config.log_analyzer_params.c2w_p99_threshold_ms,
    w2w_p99_threshold_ms: config.log_analyzer_params.w2w_p99_threshold_ms,
    urma_link_p99_threshold_ms: config.log_analyzer_params.urma_link_p99_threshold_ms,
    query_meta_p99_threshold_ms: config.log_analyzer_params.query_meta_p99_threshold_ms,
  },
})

const toDiagnosisConfigApi = (config: DiagnosisConfigForm): DiagnosisConfigApiModel => ({
  log_filename_pattern: cloneDiagnosisConfig(config).logFilenamePattern,
  log_analyzer_params: {
    total_p99_threshold_ms: config.logAnalyzerParams.total_p99_threshold_ms,
    c2w_p99_threshold_ms: config.logAnalyzerParams.c2w_p99_threshold_ms,
    w2w_p99_threshold_ms: config.logAnalyzerParams.w2w_p99_threshold_ms,
    urma_link_p99_threshold_ms: config.logAnalyzerParams.urma_link_p99_threshold_ms,
    query_meta_p99_threshold_ms: config.logAnalyzerParams.query_meta_p99_threshold_ms,
  },
})

const diagnosisConfigDraft = reactive<DiagnosisConfigForm>(createDefaultDiagnosisConfig())

const activeDiagnosisConfig = computed<DiagnosisConfigForm>(() => {
  if (!selectedAssetId.value) return createDefaultDiagnosisConfig()
  return diagnosisConfigsByAsset.value[selectedAssetId.value] ?? createDefaultDiagnosisConfig()
})

const parseConfigSummary =
  '各资产库配置相互独立，仅对后续添加的日志解析任务生效，未进行配置时使用默认配置'

const loadDiagnosisConfigImportAssets = async () => {
  isDiagnosisConfigImportListLoading.value = true
  try {
    const pageSize = 100
    let pageNum = 1
    let total = 0
    const allAssets: LogKnowledge[] = []
    do {
      const result = await request<{ total: number; kbs: LogKnowledge[] }>('/log_kb/list', {
        method: 'POST',
        body: JSON.stringify({
          page_cnt: pageSize,
          page_num: pageNum,
          created_sorted_desc: true,
        }),
      })
      total = result.total ?? 0
      const pageAssets = result.kbs ?? []
      allAssets.push(...pageAssets)
      pageNum += 1
      if (pageAssets.length === 0) break
    } while (allAssets.length < total)

    diagnosisConfigImportAssets.value = allAssets.filter(
      (asset) => asset.existed_status !== false && asset.id !== selectedAssetId.value,
    )
  } catch (error) {
    diagnosisConfigError.value = error instanceof Error ? error.message : '读取可导入资产库列表失败'
  } finally {
    isDiagnosisConfigImportListLoading.value = false
  }
}

const openParseConfigDrawer = async () => {
  Object.assign(diagnosisConfigDraft, cloneDiagnosisConfig(activeDiagnosisConfig.value))
  Object.keys(patternInputs).forEach((key) => {
    patternInputs[key as LogFilenamePatternKey] = ''
  })
  diagnosisConfigError.value = ''
  diagnosisConfigResetSnapshot.value = ''
  diagnosisConfigImportAssetId.value = ''
  diagnosisConfigImportMessage.value = ''
  isParseConfigDrawerOpen.value = true
  void loadDiagnosisConfigImportAssets()
  isDiagnosisConfigLoading.value = true
  try {
    if (!selectedAssetId.value) return
    const configPath = `/diagnosis_config/${encodeURIComponent(selectedAssetId.value)}`
    const result = await request<DiagnosisConfigApiModel>(configPath)
    const config = fromDiagnosisConfigApi(result)
    Object.assign(diagnosisConfigDraft, config)
    if (selectedAssetId.value) {
      diagnosisConfigsByAsset.value = {
        ...diagnosisConfigsByAsset.value,
        [selectedAssetId.value]: cloneDiagnosisConfig(config),
      }
    }
  } catch (error) {
    diagnosisConfigError.value = error instanceof Error ? error.message : '读取日志解析配置失败'
  } finally {
    isDiagnosisConfigLoading.value = false
  }
}

const importDiagnosisConfigFromAsset = async () => {
  if (!diagnosisConfigImportAssetId.value || isDiagnosisConfigImporting.value) return
  isDiagnosisConfigImporting.value = true
  diagnosisConfigError.value = ''
  diagnosisConfigImportMessage.value = ''
  try {
    const sourceAsset = diagnosisConfigImportAssets.value.find(
      ({ id }) => id === diagnosisConfigImportAssetId.value,
    )
    const result = await request<DiagnosisConfigApiModel>(
      `/diagnosis_config/${encodeURIComponent(diagnosisConfigImportAssetId.value)}`,
    )
    Object.assign(diagnosisConfigDraft, fromDiagnosisConfigApi(result))
    diagnosisConfigResetSnapshot.value = ''
    diagnosisConfigImportMessage.value = `已导入“${sourceAsset?.name || '所选资产库'}”的配置，保存后生效`
  } catch (error) {
    diagnosisConfigError.value = error instanceof Error ? error.message : '导入其他资产库配置失败'
  } finally {
    isDiagnosisConfigImporting.value = false
  }
}

const closeParseConfigDrawer = () => {
  isParseConfigDrawerOpen.value = false
}

const resetParseConfigDraft = () => {
  Object.assign(diagnosisConfigDraft, createDefaultDiagnosisConfig())
  diagnosisConfigResetSnapshot.value = JSON.stringify(diagnosisConfigDraft)
}

const saveParseConfig = async () => {
  if (!selectedAssetId.value || isDiagnosisConfigSaving.value) return
  diagnosisConfigError.value = ''
  const emptyPatternType = patternTypeOptions.find(
    ({ key }) => diagnosisConfigDraft.logFilenamePattern[key].length === 0,
  )
  if (emptyPatternType) {
    diagnosisConfigError.value = `${emptyPatternType.label}至少需要一个 Pattern`
    return
  }
  isDiagnosisConfigSaving.value = true
  try {
    const configPath = `/diagnosis_config/${encodeURIComponent(selectedAssetId.value)}`
    const shouldResetFromTrustedDefault =
      diagnosisConfigResetSnapshot.value !== '' &&
      diagnosisConfigResetSnapshot.value === JSON.stringify(diagnosisConfigDraft)
    const result = shouldResetFromTrustedDefault
      ? await request<DiagnosisConfigApiModel>(`${configPath}/reset`, {
          method: 'POST',
        })
      : await request<DiagnosisConfigApiModel>(configPath, {
          method: 'PUT',
          body: JSON.stringify(toDiagnosisConfigApi(diagnosisConfigDraft)),
        })
    const savedConfig = fromDiagnosisConfigApi(result)
    diagnosisConfigsByAsset.value = {
      ...diagnosisConfigsByAsset.value,
      [selectedAssetId.value]: cloneDiagnosisConfig(savedConfig),
    }
    Object.assign(diagnosisConfigDraft, savedConfig)
    closeParseConfigDrawer()
  } catch (error) {
    diagnosisConfigError.value = error instanceof Error ? error.message : '保存日志解析配置失败'
  } finally {
    isDiagnosisConfigSaving.value = false
  }
}

const addFilenamePattern = (key: LogFilenamePatternKey) => {
  const pattern = patternInputs[key].trim()
  if (!pattern || diagnosisConfigDraft.logFilenamePattern[key].includes(pattern)) return
  diagnosisConfigDraft.logFilenamePattern[key].push(pattern)
  patternInputs[key] = ''
}

const removeFilenamePattern = (key: LogFilenamePatternKey, index: number) => {
  diagnosisConfigDraft.logFilenamePattern[key].splice(index, 1)
}

// 聚合事件列表排序状态
const aggregateEventSort = useTableSort([{ field: 'total_latency', order: 'desc' }], () => {
  // 排序变化时重新加载数据（重置到第一页）
  aggregateEventPage.value = 1
  void loadLatencyDetail(1)
})

// 异常Trace列表排序状态
const abnormalTraceSort = useTableSort([{ field: 'total_latency', order: 'desc' }], () => {
  // 排序变化时重新加载数据（重置到第一页）
  abnormalTracesPageMap[selectedLatencyScale.value] = 1
  void loadAbnormalTraces(1)
})

// 时间窗口聚合事件列表
const selectedLatencyTimeWindowInterval = ref<'hour' | 'minute' | 'second'>('minute')
const timeWindowAggregatedEvents = ref<TimeWindowAggregatedEvent[]>([])
const isTimeWindowLoading = ref(false)
const timeWindowError = ref('')
const timeWindowPage = ref(1)
const timeWindowChartRange = ref<{ startTime: number; endTime: number } | null>(null)
const timeWindowTotal = ref(0)
const timeWindowPageInput = ref('')
const expandedTimeWindowIds = ref<Set<number>>(new Set())
const hoveredTimeWindowRowIndex = ref<number | null>(null)
const hoveredTimeWindowIpPairKey = ref('')
const timeWindowSortFields = ref<SortField[]>([])
const timeWindowStartTimeSortOrder = ref<SortField['order']>('asc')
const isTimeWindowStartTimeSortActive = computed(() => timeWindowSortFields.value.length === 0)
const timeWindowIpPairSortFields = ref<SortField[]>([{ field: 'total_cnt', order: 'desc' }])

const IP_PAIR_PAGE_SIZE = 10
const timeWindowIpPairPageMap = ref<Record<number, number>>({})

type ColumnWidthMap = {
  latencyLeft: number[]
  faultLeft: number[]
  latencyData: number[]
  faultData: number[]
  faultTraceLeft: number[]
  faultTraceActions: number[]
}

const traceListColumnWidths = reactive<ColumnWidthMap>({
  latencyLeft: [110, 185, 300, 130, 80, 110, 110],
  faultLeft: [110, 185, 300, 130, 110, 110, 80, 110],
  latencyData: [110, 180, 165, 170, 175, 175],
  faultData: [110, 180, 165, 170, 175, 175],
  faultTraceLeft: [110, 185, 315],
  faultTraceActions: [150],
})

const faultTraceScrollColumns = reactive({
  widths: [150, 100, 110, 80, 80, 200, 100],
  labels: ['Pod IP', '集群', '主机', '故障码', '操作类型', '故障名称', '故障域'],
})

const handleFaultTraceScrollColumnResizeStart = (e: MouseEvent, columnIndex: number) => {
  e.preventDefault()
  columnResizeState.isResizing = true
  columnResizeState.resizingColumn = 'faultTraceScroll'
  columnResizeState.startX = e.clientX
  columnResizeState.startWidth = faultTraceScrollColumns.widths[columnIndex] || 100
  columnResizeState.columnIndex = columnIndex

  document.addEventListener('mousemove', handleFaultTraceScrollColumnResize)
  document.addEventListener('mouseup', handleFaultTraceScrollColumnResizeEnd)
}

const handleFaultTraceScrollColumnResize = (e: MouseEvent) => {
  if (!columnResizeState.isResizing || columnResizeState.resizingColumn !== 'faultTraceScroll')
    return

  const diff = e.clientX - columnResizeState.startX
  const newWidth = Math.max(60, columnResizeState.startWidth + diff)
  if (columnResizeState.columnIndex >= 0) {
    faultTraceScrollColumns.widths[columnResizeState.columnIndex] = newWidth
  }
}

const handleFaultTraceScrollColumnResizeEnd = () => {
  columnResizeState.isResizing = false
  columnResizeState.resizingColumn = null
  document.removeEventListener('mousemove', handleFaultTraceScrollColumnResize)
  document.removeEventListener('mouseup', handleFaultTraceScrollColumnResizeEnd)
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', handleColumnResize)
  document.removeEventListener('mouseup', handleColumnResizeEnd)
  document.removeEventListener('mousemove', handleFaultTraceScrollColumnResize)
  document.removeEventListener('mouseup', handleFaultTraceScrollColumnResizeEnd)
})

const getFaultTraceScrollGridColumnWidths = () =>
  faultTraceScrollColumns.widths.map((w) => `${w}px`).join(' ')

const faultTraceScrollGridStyle = computed(() => {
  const columnCount = faultTraceScrollColumns.widths.length
  const width = faultTraceScrollColumns.widths.reduce((sum, w) => sum + w, 0)
  return {
    gridTemplateColumns: faultTraceScrollColumns.widths.map((w) => `${w}px`).join(' '),
    width: `${width}px`,
    minWidth: `${width}px`,
  }
})

const faultDetailTraceScrollGridStyle = computed(() => {
  const widths = faultTraceScrollColumns.widths.slice(1)
  const width = widths.reduce((sum, w) => sum + w, 0)
  return {
    gridTemplateColumns: widths.map((w) => `${w}px`).join(' '),
    width: `${width}px`,
    minWidth: `${width}px`,
  }
})

const columnResizeState = reactive({
  isResizing: false,
  resizingColumn: null as string | null,
  startX: 0,
  startWidth: 0,
  columnIndex: -1,
})

const handleColumnResizeStart = (
  e: MouseEvent,
  listType:
    | 'latencyLeft'
    | 'faultLeft'
    | 'latencyData'
    | 'faultData'
    | 'faultTraceLeft'
    | 'faultTraceActions',
  columnIndex: number,
) => {
  e.preventDefault()
  columnResizeState.isResizing = true
  columnResizeState.resizingColumn = listType
  columnResizeState.startX = e.clientX
  columnResizeState.startWidth = traceListColumnWidths[listType][columnIndex] || 100
  columnResizeState.columnIndex = columnIndex

  document.addEventListener('mousemove', handleColumnResize)
  document.addEventListener('mouseup', handleColumnResizeEnd)
}

const handleColumnResize = (e: MouseEvent) => {
  if (!columnResizeState.isResizing || !columnResizeState.resizingColumn) return

  const diff = e.clientX - columnResizeState.startX
  const newWidth = Math.max(60, columnResizeState.startWidth + diff)
  const columnArray =
    traceListColumnWidths[columnResizeState.resizingColumn as keyof ColumnWidthMap]
  if (columnArray && columnResizeState.columnIndex >= 0) {
    columnArray[columnResizeState.columnIndex] = newWidth
  }
}

const handleColumnResizeEnd = () => {
  columnResizeState.isResizing = false
  columnResizeState.resizingColumn = null
  document.removeEventListener('mousemove', handleColumnResize)
  document.removeEventListener('mouseup', handleColumnResizeEnd)
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', handleColumnResize)
  document.removeEventListener('mouseup', handleColumnResizeEnd)
})

const getLatencyLeftGridColumnWidths = () =>
  traceListColumnWidths.latencyLeft.map((w) => `${w}px`).join(' ')

const getFaultLeftGridColumnWidths = () =>
  traceListColumnWidths.faultLeft.map((w) => `${w}px`).join(' ')

const getLatencyDataGridColumnWidths = () => {
  const cols = getLatencyDataColumns.value
  return cols.map((_, i) => `${traceListColumnWidths.latencyData[i] || 160}px`).join(' ')
}

const getLatencyDataTotalWidth = () => {
  const cols = getLatencyDataColumns.value
  return cols.reduce((sum, _, i) => sum + (traceListColumnWidths.latencyData[i] || 160), 0)
}

const getTimeWindowGridColumnWidths = () => {
  const cols = getLatencyDataColumns.value.slice(1)
  return cols.map((_, i) => `${traceListColumnWidths.latencyData[i + 1] || 160}px`).join(' ')
}

const getTimeWindowTotalWidth = () => {
  const cols = getLatencyDataColumns.value.slice(1)
  return cols.reduce((sum, _, i) => sum + (traceListColumnWidths.latencyData[i + 1] || 160), 0)
}

const getFaultDataGridColumnWidths = () =>
  traceListColumnWidths.faultData.map((w) => `${w}px`).join(' ')

const getFaultTraceLeftGridColumnWidths = () =>
  traceListColumnWidths.faultTraceLeft.map((w) => `${w}px`).join(' ')

const getFaultTraceActionsGridColumnWidths = () =>
  traceListColumnWidths.faultTraceActions.map((w) => `${w}px`).join(' ')

const getTimeWindowIpPairPage = (twIdx: number) => timeWindowIpPairPageMap.value[twIdx] ?? 1

const setTimeWindowIpPairPage = (twIdx: number, page: number) => {
  timeWindowIpPairPageMap.value = {
    ...timeWindowIpPairPageMap.value,
    [twIdx]: Math.max(1, page),
  }
}

const getTimeWindowIpPairTotalPages = (twEvent: TimeWindowAggregatedEvent) =>
  Math.max(1, Math.ceil(twEvent.ip_pairs.length / IP_PAIR_PAGE_SIZE))

const getTimeWindowIpPairPageWindow = (twIdx: number, twEvent: TimeWindowAggregatedEvent) =>
  getPageWindow(getTimeWindowIpPairPage(twIdx), getTimeWindowIpPairTotalPages(twEvent))

const getNextTimeWindowSortFields = (fields: SortField[], field: string): SortField[] => {
  const nextFields = fields.map((sortField) => ({ ...sortField }))
  const existingIndex = nextFields.findIndex((sortField) => sortField.field === field)
  const existingField = existingIndex === -1 ? null : nextFields[existingIndex]

  if (existingIndex === -1) {
    nextFields.push({ field, order: 'asc' })
  } else if (existingField?.order === 'asc') {
    nextFields[existingIndex] = { field, order: 'desc' }
  } else {
    nextFields.splice(existingIndex, 1)
  }

  return nextFields
}

const getTimeWindowSortOrder = (field: string) =>
  field === 'start_time' && isTimeWindowStartTimeSortActive.value
    ? timeWindowStartTimeSortOrder.value
    : (timeWindowSortFields.value.find((sortField) => sortField.field === field)?.order ?? null)

const getTimeWindowIpPairSortOrder = (field: string) =>
  timeWindowIpPairSortFields.value.find((sortField) => sortField.field === field)?.order ?? null

const getTimeWindowSortPriority = (field: string) => {
  const index = timeWindowSortFields.value.findIndex((sortField) => sortField.field === field)
  return index === -1 ? null : index + 1
}

const getTimeWindowIpPairSortPriority = (field: string) => {
  const index = timeWindowIpPairSortFields.value.findIndex((sortField) => sortField.field === field)
  return index === -1 ? null : index + 1
}

const compareSortValues = (
  aVal: number | string,
  bVal: number | string,
  order: SortField['order'],
) => {
  const result =
    typeof aVal === 'number' && typeof bVal === 'number'
      ? aVal - bVal
      : String(aVal).localeCompare(String(bVal))
  return order === 'asc' ? result : -result
}

const getPaginatedIpPairs = (twEvent: TimeWindowAggregatedEvent, twIdx: number) => {
  const sorted = getSortedIpPairs(twEvent)
  const page = getTimeWindowIpPairPage(twIdx)
  const start = (page - 1) * IP_PAIR_PAGE_SIZE
  return sorted.slice(start, start + IP_PAIR_PAGE_SIZE)
}

const timeWindowPageCount = computed(() => Math.max(1, Math.ceil(timeWindowTotal.value / 10)))

const sortedTimeWindowAggregatedEvents = computed(() => {
  const events = [...timeWindowAggregatedEvents.value]
  const sortFields = timeWindowSortFields.value
  const getValue = (event: TimeWindowAggregatedEvent, key: string): number | string => {
    if (key === 'start_time') return event.start_time
    if (key === 'total_cnt') return event.total_cnt
    if (key === 'anomaly_cnt') return event.anomaly_cnt
    const metricKey = `ave_${key}` as keyof TimeWindowAggregatedEvent
    const val = event[metricKey]
    return typeof val === 'number' ? val : 0
  }
  events.sort((a, b) => {
    for (const sortField of sortFields) {
      const result = compareSortValues(
        getValue(a, sortField.field),
        getValue(b, sortField.field),
        sortField.order,
      )
      if (result !== 0) return result
    }
    return 0
  })
  return events
})

const timeWindowPageWindow = computed(() =>
  getPageWindow(timeWindowPage.value, timeWindowPageCount.value),
)

// 聚合事件详情表格排序状态
const detailParseResultSort = useTableSort([{ field: 'total_latency', order: 'desc' }], () => {
  // 排序变化时重新加载数据（重置到第一页）
  if (selectedAggregatedEvent.value) {
    detailParseResultsPage.value = 1
    void loadDetailParseResults(selectedAggregatedEvent.value, 1)
  }
})

// 故障聚合事件列表排序状态
const faultAggregatedEventSort = useTableSort([], () => {
  faultAggregatedEventPage.value = 1
  void loadFaultAggregatedEvents(1)
})
const faultAggregatedEventSortDesc = ref(false)
const isFaultAggregatedEventStartTimeSortActive = computed(
  () => faultAggregatedEventSort.getSortFields.value.length === 0,
)
const faultAggregatedEventPodSort = useTableSort([{ field: 'all', order: 'desc' }])

const selectedAggregatedEvent = ref<LatencyDetailRow | null>(null)
const activeAggregateTab = ref<'event' | 'trace'>('event')
const activeFaultMonitorTab = ref<'event' | 'trace'>('event')
const selectedFaultAggregateInterval = ref<FaultAggregateInterval>('minute')
const selectedFaultOperation = ref<'get' | 'set'>('get')
const abnormalTraceRowsMap = reactive<Record<number, AbnormalTraceRow[]>>({
  0: [],
  10: [],
  60: [],
  600: [],
  3600: [],
})
const abnormalTracesTotalMap = reactive<Record<number, number>>({
  0: 0,
  10: 0,
  60: 0,
  600: 0,
  3600: 0,
})
const abnormalTracesPageMap = reactive<Record<number, number>>({
  0: 1,
  10: 1,
  60: 1,
  600: 1,
  3600: 1,
})
const isAbnormalTracesLoadingMap = reactive<Record<number, boolean>>({
  0: false,
  10: false,
  60: false,
  600: false,
  3600: false,
})
const abnormalTracesErrorMap = reactive<Record<number, string>>({
  0: '',
  10: '',
  60: '',
  600: '',
  3600: '',
})

const abnormalTraceRows = computed(() => abnormalTraceRowsMap[selectedLatencyScale.value] ?? [])
const isAbnormalTracesLoading = computed(
  () => isAbnormalTracesLoadingMap[selectedLatencyScale.value] ?? false,
)
const abnormalTracesError = computed(() => abnormalTracesErrorMap[selectedLatencyScale.value] ?? '')
const abnormalTracesPage = computed(() => abnormalTracesPageMap[selectedLatencyScale.value] ?? 1)
const abnormalTracesTotal = computed(() => abnormalTracesTotalMap[selectedLatencyScale.value] ?? 0)
const faultAggregatedEventPage = ref(1)
const faultAggregatedEventTotal = ref(0)
const isFaultAggregatedEventsLoading = ref(false)
const faultAggregatedEventsError = ref('')
const expandedFaultAggregatedEventId = ref('')
const hoveredFaultAggregatedEventId = ref('')
const hoveredFaultAggregatedPodRowKey = ref('')
const hoveredFaultTraceRowKey = ref('')
const faultTraceRowsMap = reactive<Record<number, FaultTraceTableRow[]>>({
  0: [],
  10: [],
  60: [],
  600: [],
  3600: [],
})
const faultTraceEventsTotalMap = reactive<Record<number, number>>({
  0: 0,
  10: 0,
  60: 0,
  600: 0,
  3600: 0,
})
const faultTraceEventsPageMap = reactive<Record<number, number>>({
  0: 1,
  10: 1,
  60: 1,
  600: 1,
  3600: 1,
})
const isFaultTraceEventsLoadingMap = reactive<Record<number, boolean>>({
  0: false,
  10: false,
  60: false,
  600: false,
  3600: false,
})
const faultTraceEventsErrorMap = reactive<Record<number, string>>({
  0: '',
  10: '',
  60: '',
  600: '',
  3600: '',
})

const faultTraceIdsWithLatency = ref<Set<string>>(new Set())
const latencyTraceIdsWithFault = ref<Set<string>>(new Set())

const checkFaultTracesForLatency = async (traceIds: string[]) => {
  if (!selectedAssetId.value || traceIds.length === 0) {
    faultTraceIdsWithLatency.value = new Set()
    return
  }

  try {
    const body: Record<string, unknown> = {
      kb_id: selectedAssetId.value,
      is_anomalous: true,
      page_cnt: 1000,
      page_num: 1,
      trace_ids: traceIds,
    }

    const result = await request<{ total: number; log_parse_results: LogParseResultModel[] }>(
      '/log_parse_result/list',
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
    )

    const latencyTraceIds = new Set<string>()
    ;(result.log_parse_results ?? []).forEach((r) => {
      if (r.trace_id) latencyTraceIds.add(r.trace_id)
    })
    faultTraceIdsWithLatency.value = latencyTraceIds
  } catch {
    faultTraceIdsWithLatency.value = new Set()
  }
}

const checkLatencyTracesForFault = async (traceIds: string[]) => {
  if (!selectedAssetId.value || traceIds.length === 0) {
    latencyTraceIdsWithFault.value = new Set()
    return
  }

  try {
    const body: Record<string, unknown> = {
      kb_id: selectedAssetId.value,
      is_anomalous: true,
      page_cnt: 1000,
      page_num: 1,
      trace_ids: traceIds,
    }

    const result = await request<{
      total: number
      trace_failure_event_results: TraceFailureEventResultModel[]
    }>('/log_failure_event_result/list_trace_events', {
      method: 'POST',
      body: JSON.stringify(body),
    })

    const faultTraceIds = new Set<string>()
    ;(result.trace_failure_event_results ?? []).forEach((r) => {
      if (r.trace_id) faultTraceIds.add(r.trace_id)
    })
    latencyTraceIdsWithFault.value = faultTraceIds
  } catch {
    latencyTraceIdsWithFault.value = new Set()
  }
}

const getTraceTags = (traceId: string, source: 'fault' | 'latency') => {
  const tags: { type: 'fault' | 'latency'; label: string }[] = []

  if (source === 'fault') {
    tags.push({ type: 'fault', label: '通断' })
    if (faultTraceIdsWithLatency.value.has(traceId)) {
      tags.push({ type: 'latency', label: '时延' })
    }
  } else {
    tags.push({ type: 'latency', label: '时延' })
    if (latencyTraceIdsWithFault.value.has(traceId)) {
      tags.push({ type: 'fault', label: '通断' })
    }
  }

  return tags
}

const faultDetailTraceRows = ref<FaultTraceTableRow[]>([])
const isDetailLatencyChartLoading = ref(false)
const detailLatencyChartError = ref('')
const detailLatencyMetrics = ref<LatencyMetricItem[]>([])
const detailParseResults = ref<LogParseResultModel[]>([])
const isDetailParseResultsLoading = ref(false)
const detailParseResultsError = ref('')
const detailParseResultsPage = ref(1)
const detailParseResultsTotal = ref(0)
const isFaultDetailTraceEventsLoading = ref(false)
const faultDetailTraceEventsError = ref('')
const faultDetailTraceEventsPage = ref(1)
const faultDetailTraceEventsTotal = ref(0)
const assetPageInput = ref('')
const logFilesPageInput = ref('')
const abnormalTracesPageInput = ref('')
const abnormalTraceIdInput = ref('')
const abnormalTraceIdQuery = ref('')
const faultAggregatedEventPageInput = ref('')
const faultTraceEventsPageInput = ref('')
const faultTraceIdInput = ref('')
const faultTraceIdQuery = ref('')
const detailParseResultsPageInput = ref('')
const detailParseResultTraceIdInput = ref('')
const detailParseResultTraceIdQuery = ref('')
const faultDetailTraceEventsPageInput = ref('')
const faultDetailTraceIdInput = ref('')
const faultDetailTraceIdQuery = ref('')
const latencyChartRef = ref<HTMLDivElement | null>(null)
const detailLatencyChartRef = ref<HTMLDivElement | null>(null)
const faultChartRef = ref<HTMLDivElement | null>(null)
const faultDetailChartRef = ref<HTMLDivElement | null>(null)
const logFilesPollingTimer = ref<ReturnType<typeof window.setInterval> | null>(null)
const isFaultChartLoading = ref(false)
const faultChartError = ref('')
const faultChartMetrics = ref<Record<string, ErrCodeMetricItem[]>>({})
const knownFaultCodes = ref<string[]>([])
const isFaultDetailChartLoading = ref(false)
const faultDetailChartError = ref('')
const faultDetailChartMetrics = ref<Record<string, ErrCodeMetricItem[]>>({})
const faultAggregatedEventCodes = ref<string[]>([])
const statusCodePopoverRef = ref<HTMLDivElement | null>(null)
const statusCodePopover = reactive({
  open: false,
  code: '',
  symptom: '',
  rootCause: '',
  loading: false,
  error: '',
  left: 0,
  top: 0,
})
const failureModePopoverRef = ref<HTMLDivElement | null>(null)
const failureModePopover = reactive({
  open: false,
  failureMode: null as FailureModeKnowledgeModel | null,
  loading: false,
  error: '',
  left: 0,
  top: 0,
})
const faultAggregatedEventRows = ref<FaultAggregatedEventRow[]>([])
const faultAggregatedEventPodRowsByEventId = ref<Record<string, FaultAggregatedEventPodRow[]>>({})
const faultAggregatedEventPodTotalsByEventId = ref<Record<string, number>>({})
const faultAggregatedEventPodPagesByEventId = ref<Record<string, number>>({})
const faultAggregatedEventPodPageInputsByEventId = ref<Record<string, string>>({})
const loadingFaultAggregatedEventPodIds = ref<Set<string>>(new Set())
const faultAggregatedEventPodErrors = ref<Record<string, string>>({})
const failureModeDetailsById = ref<Record<string, FailureModeKnowledgeModel | null>>({})
const selectedTrace = ref<TraceDetailRow | null>(null)
const selectedFaultTrace = ref<TraceDetailRow | null>(null)
const selectedFaultAggregatedEventDetail = ref<FaultAggregatedEventDetail | null>(null)
const selectedFaultTraceFailureModeId = ref('')
const selectedTraceFailureModeId = ref('')
const selectedChildFailureModeId = ref('')
const traceFailureLogsByTrace = ref<Record<string, TraceLogRow[]>>({})
const traceFailureEventsByTrace = ref<Record<string, LogFailureEventResultModel[]>>({})
const isTraceLogsLoading = ref(false)
const traceLogsError = ref('')
const latencyScaleOptions = [
  { value: 10, label: '10秒' },
  { value: 60, label: '1分钟' },
  { value: 600, label: '10分钟' },
  { value: 3600, label: '1小时' },
] as const

const selectedLatencyScale = ref<number>(60)

const latencyChartCenterTime = ref<number | null>(null)

// 每个时间尺度点击图表时，选中范围半宽 = halfSpanMultiplier * scaleSeconds（秒）
// 10s: 60 * 10s = 10min 半宽 → 120 个点
// 1min: 60 * 60s = 60min 半宽 → 120 个点
// 10min: 72 * 600s = 12h 半宽 → 144 个点（24h 总范围）
// 1hr: 12 * 3600s = 12h 半宽 → 24 个点（24h 总范围）
const latencyChartHalfSpanMultiplier: Record<number, number> = {
  10: 60,
  60: 60,
  600: 72,
  3600: 12,
}

const latencyChartRange = computed<LatencyChartRange | null>(() => {
  const centerTime = latencyChartCenterTime.value
  if (centerTime === null) return null
  const scaleSeconds = selectedLatencyScale.value || 10
  const halfSpan = (latencyChartHalfSpanMultiplier[scaleSeconds] ?? 60) * scaleSeconds * secondMs
  return {
    centerTime,
    startTime: centerTime - halfSpan,
    endTime: centerTime + halfSpan,
    label: formatFullTimeLabel(new Date(centerTime)),
  }
})

// 故障监控时间尺度
const selectedFaultScale = ref<number>(60)
const faultChartCenterTime = ref<number | null>(null)
const faultChartHalfSpanMultiplier: Record<number, number> = {
  10: 60,
  60: 60,
  600: 72,
  3600: 12,
}
const faultChartRange = computed<LatencyChartRange | null>(() => {
  const centerTime = faultChartCenterTime.value
  if (centerTime === null) return null
  const scaleSeconds = selectedFaultScale.value || 10
  const halfSpan = (faultChartHalfSpanMultiplier[scaleSeconds] ?? 60) * scaleSeconds * secondMs
  return {
    centerTime,
    startTime: centerTime - halfSpan,
    endTime: centerTime + halfSpan,
    label: formatFullTimeLabel(new Date(centerTime)),
  }
})

const faultTraceRows = computed(() => faultTraceRowsMap[selectedFaultScale.value] ?? [])
const faultTraceEventsTotal = computed(
  () => faultTraceEventsTotalMap[selectedFaultScale.value] ?? 0,
)
const faultTraceEventsPage = computed(() => faultTraceEventsPageMap[selectedFaultScale.value] ?? 1)
const isFaultTraceEventsLoading = computed(
  () => isFaultTraceEventsLoadingMap[selectedFaultScale.value] ?? false,
)
const faultTraceEventsError = computed(
  () => faultTraceEventsErrorMap[selectedFaultScale.value] ?? '',
)

const abnormalTraceTableRef = ref<HTMLDivElement | null>(null)
const detailAbnormalTraceTableRef = ref<HTMLDivElement | null>(null)
const faultTraceTableRef = ref<HTMLDivElement | null>(null)
const latencyTraceTableRef = ref<HTMLDivElement | null>(null)
const hoveredLatencyTraceRowKey = ref('')

const syncSplitTableRowHeights = (table: HTMLDivElement | null, scrollRowSelector: string) => {
  if (!table) return

  const scrollRows = table.querySelectorAll<HTMLElement>(scrollRowSelector)
  const fixedRows = table.querySelectorAll<HTMLElement>('.aggregate-fixed-left .aggregate-body-row')
  const actionRows = table.querySelectorAll<HTMLElement>(
    '.aggregate-fixed-actions .aggregate-body-row',
  )

  scrollRows.forEach((scrollRow, index) => {
    const rows = [scrollRow, fixedRows[index], actionRows[index]].filter(
      (row): row is HTMLElement => Boolean(row),
    )

    // Clear the previous synchronized value first so content changes can also shrink a row.
    rows.forEach((row) => row.style.removeProperty('height'))
    const height = Math.max(...rows.map((row) => row.getBoundingClientRect().height))
    rows.forEach((row) => (row.style.height = `${height}px`))
  })
}

const syncLatencyTraceRowHeights = () => {
  nextTick(() => {
    syncSplitTableRowHeights(
      latencyTraceTableRef.value,
      '.abnormal-latency-grid.aggregate-body-row',
    )
  })
}

const syncDetailLatencyTraceRowHeights = () => {
  nextTick(() => {
    syncSplitTableRowHeights(
      detailAbnormalTraceTableRef.value,
      '.abnormal-latency-grid.aggregate-body-row',
    )
  })
}

const syncAbnormalTraceRowHeights = () => {
  nextTick(() => {
    requestAnimationFrame(() => {
      setTimeout(() => {
        if (!abnormalTraceTableRef.value) return

        const scrollBody = abnormalTraceTableRef.value.querySelector('.aggregate-latency-body')
        const fixedLeft = abnormalTraceTableRef.value.querySelector('.aggregate-fixed-left')
        const fixedActions = abnormalTraceTableRef.value.querySelector('.aggregate-fixed-actions')

        if (!scrollBody || !fixedLeft || !fixedActions) return

        const scrollRows = scrollBody.querySelectorAll('.abnormal-latency-grid.aggregate-body-row')
        const fixedRows = fixedLeft.querySelectorAll('.abnormal-left-grid.aggregate-body-row')
        const actionRows = fixedActions.querySelectorAll('.aggregate-cell.aggregate-body-row')

        const count = Math.max(scrollRows.length, fixedRows.length, actionRows.length)
        for (let index = 0; index < count; index++) {
          const scrollRow = scrollRows[index] as HTMLElement | undefined
          const fixedRow = fixedRows[index] as HTMLElement | undefined
          const actionRow = actionRows[index] as HTMLElement | undefined

          const heights: number[] = []
          if (scrollRow) heights.push(scrollRow.getBoundingClientRect().height)
          if (fixedRow) heights.push(fixedRow.getBoundingClientRect().height)
          if (actionRow) heights.push(actionRow.getBoundingClientRect().height)

          if (heights.length > 0) {
            const maxHeight = Math.max(...heights, 59)
            if (scrollRow) scrollRow.style.height = `${maxHeight}px`
            if (fixedRow) fixedRow.style.height = `${maxHeight}px`
            if (actionRow) actionRow.style.height = `${maxHeight}px`
          }
        }
      }, 50)
    })
  })
}

const syncFaultTraceRowHeights = () => {
  nextTick(() => {
    syncSplitTableRowHeights(
      faultTraceTableRef.value,
      '.fault-trace-scroll-grid.aggregate-body-row',
    )
  })
}

watch(
  [faultTraceRows, activeFaultMonitorTab],
  () => {
    if (activeFaultMonitorTab.value === 'trace') {
      syncFaultTraceRowHeights()
    }
  },
  { immediate: true },
)

watch(
  abnormalTraceRows,
  () => {
    syncAbnormalTraceRowHeights()
  },
  { immediate: true },
)

const syncDetailAbnormalTraceRowHeights = () => {
  nextTick(() => {
    requestAnimationFrame(() => {
      setTimeout(() => {
        if (!detailAbnormalTraceTableRef.value) return

        const scrollBody =
          detailAbnormalTraceTableRef.value.querySelector('.aggregate-latency-body')
        const fixedLeft = detailAbnormalTraceTableRef.value.querySelector('.aggregate-fixed-left')
        const fixedActions = detailAbnormalTraceTableRef.value.querySelector(
          '.aggregate-fixed-actions',
        )

        if (!scrollBody || !fixedLeft || !fixedActions) return

        const scrollRows = scrollBody.querySelectorAll('.abnormal-latency-grid.aggregate-body-row')
        const fixedRows = fixedLeft.querySelectorAll('.abnormal-left-grid.aggregate-body-row')
        const actionRows = fixedActions.querySelectorAll('.aggregate-cell.aggregate-body-row')

        const count = Math.max(scrollRows.length, fixedRows.length, actionRows.length)
        for (let index = 0; index < count; index++) {
          const scrollRow = scrollRows[index] as HTMLElement | undefined
          const fixedRow = fixedRows[index] as HTMLElement | undefined
          const actionRow = actionRows[index] as HTMLElement | undefined

          const heights: number[] = []
          if (scrollRow) heights.push(scrollRow.getBoundingClientRect().height)
          if (fixedRow) heights.push(fixedRow.getBoundingClientRect().height)
          if (actionRow) heights.push(actionRow.getBoundingClientRect().height)

          if (heights.length > 0) {
            const maxHeight = Math.max(...heights, 59)
            if (scrollRow) scrollRow.style.height = `${maxHeight}px`
            if (fixedRow) fixedRow.style.height = `${maxHeight}px`
            if (actionRow) actionRow.style.height = `${maxHeight}px`
          }
        }
      }, 50)
    })
  })
}

onUpdated(() => {
  if (activeAggregateTab.value === 'trace') {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!latencyTraceTableRef.value) return
        const scrollBody = latencyTraceTableRef.value.querySelector('.aggregate-latency-body')
        const fixedLeft = latencyTraceTableRef.value.querySelector('.aggregate-fixed-left')
        if (!scrollBody || !fixedLeft) return
        const scrollRows = scrollBody.querySelectorAll('.abnormal-latency-grid.aggregate-body-row')
        const fixedRows = fixedLeft.querySelectorAll('.abnormal-left-grid.aggregate-body-row')
        if (scrollRows.length === 0 || fixedRows.length === 0) return
        scrollRows.forEach((scrollRow, index) => {
          const scrollHeight = scrollRow.getBoundingClientRect().height
          const fixedRow = fixedRows[index] as HTMLElement | undefined
          if (!fixedRow) return
          const fixedHeight = fixedRow.getBoundingClientRect().height
          const maxHeight = Math.max(scrollHeight, fixedHeight)
          if (scrollHeight < maxHeight) {
            ;(scrollRow as HTMLElement).style.height = `${maxHeight}px`
          }
          if (fixedHeight < maxHeight) {
            fixedRow.style.height = `${maxHeight}px`
          }
        })
      })
    })
  }
})

type GlobalFilterState = {
  startTime: string
  endTime: string
  clusters: string[]
  hosts: string[]
  podIps: string[]
  sourcePodIps: string[]
  targetPodIps: string[]
  traceBoards: string[]
}

type AssetState = {
  filters: GlobalFilterState
  appliedFilters: GlobalFilterState
  latencyChartCenterTime: number | null
  faultChartCenterTime: number | null
  selectedLatencyScale: number
  selectedFaultScale: number
  logSourceInput: string
  uploadLogError: string
}

const createEmptyAssetState = (): AssetState => ({
  filters: createEmptyFilters(),
  appliedFilters: createEmptyFilters(),
  latencyChartCenterTime: null,
  faultChartCenterTime: null,
  selectedLatencyScale: 60,
  selectedFaultScale: 60,
  logSourceInput: '',
  uploadLogError: '',
})

const assetStates = ref<Record<string, AssetState>>({})



const createEmptyFilters = (): GlobalFilterState => ({
  startTime: '',
  endTime: '',
  clusters: [],
  hosts: [],
  podIps: [],
  sourcePodIps: [],
  targetPodIps: [],
  traceBoards: [],
})

const filterDraftInput = reactive({
  cluster: '',
  host: '',
  podIp: '',
  sourcePodIp: '',
  targetPodIp: '',
})
const globalFilters = reactive<GlobalFilterState>(createEmptyFilters())
const appliedFilters = ref<GlobalFilterState>(createEmptyFilters())
const filterApplyMessage = ref('')
const traceFilterDialog = reactive({
  open: false,
  trace: null as TraceFilterTarget | null,
  addCluster: false,
  addHost: false,
  addPodIp: false,
  addSourcePodIp: false,
  addTargetPodIp: false,
  addTraceBoard: false,
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

const latencyPodIpFilterDialog = reactive({
  open: false,
  row: null as LatencyDetailRow | FaultDetailRow | null,
  addSourcePodIp: false,
  addTargetPodIp: false,
  addSourcePodIpToPodFilter: false,
  addTargetPodIpToPodFilter: false,
})

const faultAggregatedPodIpFilterDialog = reactive({
  open: false,
  podRow: null as FaultAggregatedEventPodRow | null,
  addPodIp: false,
  addSourcePodIp: false,
  addTargetPodIp: false,
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
  const visiblePages = new Set([1, pageCount])
  const start = Math.max(1, currentPage - 2)
  const end = Math.min(pageCount, currentPage + 2)
  for (let page = start; page <= end; page += 1) visiblePages.add(page)

  const pages = [...visiblePages].sort((first, second) => first - second)
  const pageWindow: number[] = []
  pages.forEach((page, index) => {
    const previousPage = pages[index - 1]
    if (previousPage !== undefined && page - previousPage > 1) {
      pageWindow.push(previousPage === 1 ? -1 : -2)
    }
    pageWindow.push(page)
  })
  return pageWindow
}
const assetPageWindow = computed(() => getPageWindow(assetPage.value, assetPageCount.value))
const logFilesPageWindow = computed(() =>
  getPageWindow(logFilesPage.value, logFilesPageCount.value),
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
const isLatencyEventListFilterMode = computed(
  () => isAbnormalMonitorPage.value && activeAggregateTab.value === 'event',
)
const shouldShowTraceListFilters = computed(
  () => activePage.value === 'asset' || isAbnormalMonitorPage.value,
)
const shouldShowFaultCodeFilter = computed(
  () => isFaultCodeFeatureEnabled && isAbnormalMonitorPage.value,
)
const getLatencySeriesConfig = [
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

const setLatencySeriesConfig = [
  {
    key: 'total_latency',
    label: '总时延',
    color: '#5470c6',
  },
  {
    key: 'create_latency',
    label: 'CREATE阶段时延',
    color: '#91cc75',
  },
  {
    key: 'publish_latency',
    label: 'PUBLISH阶段时延',
    color: '#fac858',
  },
  {
    key: 'worker_total_latency',
    label: 'Worker端总时延',
    color: '#ee6666',
  },
] as const

const latencySeriesConfig = computed(() =>
  selectedOperation.value === 'get' ? getLatencySeriesConfig : setLatencySeriesConfig,
)

type LatencyMetricKey = (typeof getLatencySeriesConfig)[number]['key']

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
  visibleLatencyKeys.value = new Set(latencySeriesConfig.value.map((s) => s.key))
}

const deselectAllLatencySeries = () => {
  visibleLatencyKeys.value = new Set<LatencyMetricKey>([latencySeriesConfig.value[0].key])
}

const latencyPercentileOptions = [
  { value: 'p99', label: 'P99', abnormalThreshold: 2 },
  { value: 'p9999', label: 'P9999', abnormalThreshold: 5 },
  { value: 'pmax', label: 'Pmax', abnormalThreshold: 5 },
  { value: 'ave', label: '均值', abnormalThreshold: 5 },
] as const

const latencySampleModeMap: Record<LatencyPercentileValue, string> = {
  p99: 'p99',
  p9999: 'p9999',
  pmax: 'max',
  ave: 'avg',
}

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

const aggregatedLatencyColumns = [
  { key: 'total_latency', label: '总时延 (ms)', threshold: 150 },
  { key: 'query_meta_latency', label: '查询元数据时延 (ms)', threshold: 150 },
  { key: 'urma_total_latency', label: 'URMA总时延 (ms)', threshold: 150 },
  { key: 'urma_link_latency', label: 'URMA建链时延 (ms)', threshold: 150 },
  { key: 'c2w_urma_latency', label: 'C2W URMA时延 (ms)', threshold: 100 },
  { key: 'w2w_urma_latency', label: 'W2W URMA时延 (ms)', threshold: 100 },
  { key: 'create_latency', label: 'CREATE阶段时延 (ms)', threshold: 100 },
  { key: 'publish_latency', label: 'PUBLISH阶段时延 (ms)', threshold: 100 },
  { key: 'worker_total_latency', label: 'Worker端总时延 (ms)', threshold: 100 },
] as const

const timeWindowLatencyColumns = computed(() =>
  getLatencyDataColumns.value.slice(1),
)

const getLatencyDataColumns = computed(() => {
  const isSet = selectedOperation.value === 'set'
  return aggregatedLatencyColumns.filter((col) => {
    if (col.key === 'total_latency') return true
    if (isSet) {
      return ['create_latency', 'publish_latency', 'worker_total_latency'].includes(col.key)
    }
    return ['query_meta_latency', 'urma_total_latency', 'urma_link_latency', 'c2w_urma_latency', 'w2w_urma_latency'].includes(col.key)
  })
})

const LATENCY_KEY_TO_ROW_FIELD: Record<string, string> = {
  total_latency: 'totalLatency',
  query_meta_latency: 'queryMetaLatency',
  urma_total_latency: 'urmaTotalLatency',
  urma_link_latency: 'urmaLinkLatency',
  c2w_urma_latency: 'c2wUrmaLatency',
  w2w_urma_latency: 'w2wUrmaLatency',
  create_latency: 'createLatency',
  publish_latency: 'publishLatency',
  worker_total_latency: 'workerTotalLatency',
}

const getLatencyRowValue = (row: Record<string, unknown>, key: string): number | null => {
  const field = LATENCY_KEY_TO_ROW_FIELD[key]
  return field ? (row[field] as number | null) ?? null : null
}

const DETAIL_SORT_KEY_MAP: Record<string, string> = {
  query_meta_latency: 'worker_query_meta_latency',
}

const getDetailSortKey = (colKey: string): string => DETAIL_SORT_KEY_MAP[colKey] || colKey

type AggregatedLatencyKey = (typeof aggregatedLatencyColumns)[number]['key']

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

const maxBucketMetricValue = (values: number[]) => {
  if (values.length === 0) return null
  return Math.max(...values)
}

const createEmptyLatencyMetricBuckets = (): Record<LatencyMetricKey, number[]> =>
  latencySeriesConfig.value.reduce(
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

const padDatePart = (value: number) => String(value).padStart(2, '0')

const formatFullTimeLabel = (date: Date) =>
  [
    `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`,
    `${padDatePart(date.getHours())}:${padDatePart(date.getMinutes())}:${padDatePart(date.getSeconds())}`,
  ].join(' ')

const formatMetricValue = (value?: number | null) =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(3) : '-'

const formatNullableMetricValue = (value?: number | null) =>
  value === null ? 'null' : formatMetricValue(value)

const formatTraceDelayColumnValue = (value: number | null | undefined, column: TraceDelayColumn) =>
  typeof value === 'number' && Number.isFinite(value)
    ? `${formatMetricValue(value)} ${column.unit}`
    : '未解析'

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
  create_latency: 1,
  publish_latency: 1,
  worker_total_latency: 1,
} satisfies Record<AggregatedLatencyKey, number>

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

  if ('metric' in column && column.metric) {
    if (column.metric === 'total_latency' && trace && 'faultCode' in trace && trace.faultCode) {
      return true
    }
    return isLatencyMetricAbnormal(column.metric, value)
  }
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

const secondMs = 1000
const minuteMs = 60 * secondMs
const latencyBucketCandidatesMs = [
  10 * secondMs,
  30 * secondMs,
  minuteMs,
  5 * minuteMs,
  10 * minuteMs,
  30 * minuteMs,
  60 * minuteMs,
]

const getAdaptiveLatencyBucketMs = (times: number[]) => {
  if (times.length <= 1) return 10 * secondMs

  const minTime = Math.min(...times)
  const maxTime = Math.max(...times)
  const timeSpan = Math.max(maxTime - minTime, 10 * secondMs)

  return (
    latencyBucketCandidatesMs.find((candidate) => Math.ceil(timeSpan / candidate) <= 120) ??
    latencyBucketCandidatesMs[latencyBucketCandidatesMs.length - 1]!
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
  const bucketMs =
    selectedLatencyScale.value !== 0 && chartRange
      ? selectedLatencyScale.value * secondMs
      : getAdaptiveLatencyBucketMs(allTimes)
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

    latencySeriesConfig.value.forEach((series) => {
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

    const values = latencySeriesConfig.value.reduce(
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

const detailLatencyChartBuckets = computed<LatencyChartBucket[]>(() =>
  detailLatencyMetrics.value
    .map((metric) => {
      const date = parseMetricDate(metric)
      if (!date) return null

      const values = latencySeriesConfig.value.reduce(
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
  const visibleSeries = latencySeriesConfig.value.filter((s) => isLatencySeriesVisible(s.key))

  return {
    color: visibleSeries.map((series) => series.color),
    tooltip: {
      trigger: 'axis',
      appendToBody: true,
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
    series: latencySeriesConfig.value
      .filter((s) => isLatencySeriesVisible(s.key))
      .map((series, index) => ({
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
  if (!isAbnormalMonitorPage.value || isLatencyChartLoading.value || latencyChartError.value) return
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
      if (bucket) {
        latencyChartCenterTime.value = bucket.time
        selectedFaultScale.value = selectedLatencyScale.value
        faultChartCenterTime.value = bucket.time
        // Sync time range to filter panel
        const scaleSeconds = selectedLatencyScale.value || 10
        const halfSpan = (latencyChartHalfSpanMultiplier[scaleSeconds] ?? 60) * scaleSeconds * secondMs
        globalFilters.startTime = timestampToDatetimeLocal(bucket.time - halfSpan)
        globalFilters.endTime = timestampToDatetimeLocal(bucket.time + halfSpan)
        void loadAllLatencyData(latencyChartRange.value)
      }
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
      if (bucket) {
        faultChartCenterTime.value = bucket.time
        selectedLatencyScale.value = selectedFaultScale.value
        latencyChartCenterTime.value = bucket.time
        // Sync time range to filter panel
        const scaleSeconds = selectedFaultScale.value || 10
        const halfSpan = (faultChartHalfSpanMultiplier[scaleSeconds] ?? 60) * scaleSeconds * secondMs
        globalFilters.startTime = timestampToDatetimeLocal(bucket.time - halfSpan)
        globalFilters.endTime = timestampToDatetimeLocal(bucket.time + halfSpan)
        void loadAllFaultData()
      }
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
  syncLatencyTraceRowHeights()
  syncDetailLatencyTraceRowHeights()
  syncFaultTraceRowHeights()
}

const loadAllLatencyData = async (chartRange?: { startTime: number; endTime: number } | null) => {
  await loadLatencyChart()

  await Promise.all([loadLatencyDetail(1), loadAbnormalTraces(1)])

  await Promise.all([loadFaultTraceEvents(1), loadFaultAggregatedEvents(1), loadFaultChart()])

  await loadTimeWindowAggregatedEvents(1, chartRange)
}

const loadAllFaultData = async () => {
  await loadFaultChart()

  await Promise.all([loadFaultTraceEvents(1), loadFaultAggregatedEvents(1)])

  await Promise.all([loadLatencyChart(), loadAbnormalTraces(1), loadLatencyDetail(1)])

  await loadTimeWindowAggregatedEvents(1, null)
}

const resetLatencyChartRange = () => {
  latencyChartCenterTime.value = null
  faultChartCenterTime.value = null
  globalFilters.startTime = ''
  globalFilters.endTime = ''
  void loadAllLatencyData(null)
}

const resetFaultChartRange = () => {
  faultChartCenterTime.value = null
  latencyChartCenterTime.value = null
  globalFilters.startTime = ''
  globalFilters.endTime = ''
  void loadAllFaultData()
}

const faultCodes = computed(() => {
  const currentCodes = Object.keys(faultChartMetrics.value).sort((a, b) => a.localeCompare(b))
  return currentCodes.length > 0 ? currentCodes : knownFaultCodes.value
})
const hasFaultChartMetricData = computed(() =>
  Object.values(faultChartMetrics.value).some((metrics) => metrics.length > 0),
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
const closeStatusCodePopover = () => {
  statusCodePopover.open = false
}
const closeFailureModePopover = () => {
  failureModePopover.open = false
  failureModePopover.failureMode = null
}
const openFailureModeDetailPopover = (
  failureMode: FailureModeKnowledgeModel,
  event: MouseEvent,
) => {
  const popoverWidth = 460
  const popoverHeight = 480
  const margin = 12
  failureModePopover.open = true
  failureModePopover.failureMode = failureMode
  failureModePopover.loading = false
  failureModePopover.error = ''
  failureModePopover.left = Math.min(
    event.clientX + margin,
    Math.max(margin, window.innerWidth - popoverWidth - margin),
  )
  const showBelow = event.clientY < window.innerHeight / 2
  if (showBelow) {
    failureModePopover.top = Math.max(
      margin,
      Math.min(event.clientY + margin, window.innerHeight - popoverHeight - margin),
    )
  } else {
    failureModePopover.top = Math.max(margin, event.clientY - popoverHeight - margin)
  }
}
const openStatusCodePopover = async (code: string, event: MouseEvent) => {
  if (code === 'all') return
  const popoverWidth = 460
  const popoverHeight = 320
  const margin = 12
  statusCodePopover.open = true
  statusCodePopover.code = code
  statusCodePopover.symptom = ''
  statusCodePopover.rootCause = ''
  statusCodePopover.error = ''
  statusCodePopover.loading = true
  statusCodePopover.left = Math.min(
    event.clientX + margin,
    Math.max(margin, window.innerWidth - popoverWidth - margin),
  )
  const showBelow = event.clientY < window.innerHeight / 2
  if (showBelow) {
    statusCodePopover.top = Math.max(
      margin,
      Math.min(event.clientY + margin, window.innerHeight - popoverHeight - margin),
    )
  } else {
    statusCodePopover.top = Math.max(margin, event.clientY - popoverHeight - margin)
  }

  try {
    const result = await request<{ status_code_info: StatusCodeKnowledge }>(
      `/failure_mode/status_code/${encodeURIComponent(code)}`,
    )
    if (!statusCodePopover.open || statusCodePopover.code !== code) return
    statusCodePopover.symptom = result.status_code_info.symptom
    statusCodePopover.rootCause = result.status_code_info.root_cause
  } catch (error) {
    if (!statusCodePopover.open || statusCodePopover.code !== code) return
    statusCodePopover.error = error instanceof Error ? error.message : '加载故障码信息失败'
  } finally {
    if (statusCodePopover.code === code) statusCodePopover.loading = false
  }
}
const handleStatusCodePopoverOutsideClick = (event: MouseEvent) => {
  if (
    statusCodePopover.open &&
    !statusCodePopoverRef.value?.contains(event.target as Node) &&
    !(event.target as Element).closest?.('.fault-code-knowledge-link') &&
    !(event.target as Element).closest?.('.fault-code-clickable')
  ) {
    closeStatusCodePopover()
  }
  if (
    failureModePopover.open &&
    !failureModePopoverRef.value?.contains(event.target as Node) &&
    !(event.target as Element).closest?.('.failure-mode-link-btn')
  ) {
    closeFailureModePopover()
  }
}
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
const getFaultAggregatedEventSortPriority = (field: string) => {
  const index = faultAggregatedEventSort.getSortFields.value.findIndex(
    (sortField) => sortField.field === field,
  )
  return index === -1 ? null : index + 1
}
const getFaultAggregatedEventPodSortPriority = (field: string) => {
  const index = faultAggregatedEventPodSort.getSortFields.value.findIndex(
    (sortField) => sortField.field === field,
  )
  return index === -1 ? null : index + 1
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
  const chartRange = faultChartRange.value
  const allMetricPoints: { code: string; time: number; value: number }[] = []

  Object.entries(faultChartMetrics.value).forEach(([code, metrics]) => {
    metrics.forEach((metric) => {
      const parsed = parseMetricDate(metric)
      if (!parsed) return
      const time = parsed.getTime()
      const value = metric.err_cnt ?? metric.count ?? metric.value
      if (typeof value === 'number' && Number.isFinite(value)) {
        allMetricPoints.push({ code, time, value })
      }
    })
  })

  if (allMetricPoints.length === 0) {
    const codes = faultCodes.value
    if (codes.length === 0) return []

    let minTime: number
    let maxTime: number
    if (chartRange) {
      minTime = chartRange.startTime
      maxTime = chartRange.endTime
    } else {
      const filters = appliedFilters.value
      const startMs = filters.startTime ? new Date(filters.startTime).getTime() : NaN
      const endMs = filters.endTime ? new Date(filters.endTime).getTime() : NaN
      if (isNaN(startMs) || isNaN(endMs)) return []
      minTime = startMs
      maxTime = endMs
    }

    const bucketMs =
      selectedFaultScale.value !== 0
        ? selectedFaultScale.value * secondMs
        : Math.max(60000, Math.floor((maxTime - minTime) / 100))

    const firstBucketStart = Math.floor(minTime / bucketMs) * bucketMs
    const lastBucketStart = Math.floor(maxTime / bucketMs) * bucketMs

    const zeroCounts: Record<string, number> = {}
    codes.forEach((code) => {
      zeroCounts[code] = 0
    })

    const zeroBuckets: FaultChartBucket[] = []
    for (let time = firstBucketStart; time <= lastBucketStart; time += bucketMs) {
      zeroBuckets.push({
        time,
        label: formatFullTimeLabel(new Date(time)),
        counts: { ...zeroCounts },
      })
    }

    return zeroBuckets
  }

  const allTimes = allMetricPoints.map((p) => p.time)
  const bucketMs =
    selectedFaultScale.value !== 0 && chartRange
      ? selectedFaultScale.value * secondMs
      : getAdaptiveLatencyBucketMs(allTimes)
  const minTime = chartRange?.startTime ?? Math.min(...allTimes)
  const maxTime = chartRange?.endTime ?? Math.max(...allTimes)
  const firstBucketStart = Math.floor(minTime / bucketMs) * bucketMs
  const lastBucketStart = Math.floor(maxTime / bucketMs) * bucketMs

  const buckets = new Map<number, Record<string, number>>()

  allMetricPoints.forEach(({ code, time, value }) => {
    if (chartRange && (time < chartRange.startTime || time > chartRange.endTime)) return
    const bucketStart = Math.floor(time / bucketMs) * bucketMs
    const bucket = buckets.get(bucketStart) ?? {}
    bucket[code] = (bucket[code] ?? 0) + value
    buckets.set(bucketStart, bucket)
  })

  const chartBuckets: FaultChartBucket[] = []
  for (let time = firstBucketStart; time <= lastBucketStart; time += bucketMs) {
    chartBuckets.push({
      time,
      label: formatFullTimeLabel(new Date(time)),
      counts: buckets.get(time) ?? {},
    })
  }

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
      sourcePodIp: stripHostPort(event.src_ip),
      targetPodIp: stripHostPort(event.dst_ip),
      traceCount: event.log_parse_result_cnt ?? 0,
      anomalyTraceCount: event.anomaly_log_parse_result_cnt ?? 0,
      event,
      operation: event.operation || undefined,
    })
  })

  return rows
})

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

const getDisplayHost = (record: Record<string, unknown>) => {
  const host = getRecordString(record, ['host'], '-').trim()
  return host.toLowerCase() === 'unknown' ? '-' : host
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
  create_latency: ['create_latency'],
  publish_latency: ['publish_latency'],
  worker_total_latency: ['worker_total_latency'],
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

const normalizeTraceOperation = (operation: string) => {
  const normalized = operation.trim().toUpperCase()
  if (normalized.includes('GET')) return 'GET'
  if (normalized.includes('SET')) return 'SET'
  return '-'
}

const normalizeTimeText = (value: string) => {
  let normalized = value.replace('T', ' ').replace(/Z$/, '')
  const match = normalized.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(\.\d+)?$/)
  if (match) {
    const base = match[1]
    const decimals = match[2] || '.000'
    const trimmedDecimals = decimals.length > 4 ? decimals.substring(0, 4) : decimals.padEnd(4, '0')
    return base + trimmedDecimals
  }
  return normalized
}

const getTraceRowHeight = (podIpHtml: string) => {
  const lineCount = Math.max(1, podIpHtml.split(/<br\s*\/?\s*>/i).length)
  return `${Math.max(59, 24 + lineCount * 20)}px`
}

const detailParseResultRows = computed<ParseResultTableRow[]>(() =>
  detailParseResults.value.map((result) => {
    const record = result as Record<string, unknown>
    return {
      id: getRecordString(record, ['id', 'trace_id', 'traceId']),
      logStatus: getLogDisplayStatus(record),
      statusReason: getLogDisplayReason(record),
      time: normalizeTimeText(getRecordString(record, ['timestamp', 'created_at', 'time'], '')),
      traceId: getRecordString(record, ['trace_id', 'traceId', 'span_id', 'id']),
      podIp: (() => {
        const podIps = record['pod_ips']
        if (Array.isArray(podIps)) {
          return podIps.join('<br>')
        }
        return getRecordString(record, ['pod_ips', 'pod_ip', 'pod_id', 'pod_name', 'podId', 'pod'])
      })(),
      operation: normalizeTraceOperation(
        getRecordString(record, ['operation', 'op_type', 'operation_type', 'method']),
      ),
      clusterName: getRecordString(record, ['cluster_name'], 'null'),
      host: getDisplayHost(record),
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
      createLatency: getRecordNullableNumber(record, ['create_latency']),
      publishLatency: getRecordNullableNumber(record, ['publish_latency']),
      workerTotalLatency: getRecordNullableNumber(record, ['worker_total_latency']),
      raw: result,
    }
  }),
)

watch(
  detailParseResultRows,
  () => {
    syncDetailAbnormalTraceRowHeights()
  },
  { immediate: true },
)

const detailParseResultsPageCount = computed(() =>
  Math.max(1, Math.ceil(detailParseResultsTotal.value / detailParseResultsPageSize)),
)
const detailParseResultsPageWindow = computed(() =>
  getPageWindow(detailParseResultsPage.value, detailParseResultsPageCount.value),
)

const detailParseResultsBadgeCount = computed(() => detailParseResultsTotal.value)

const faultDetailTraceEventsPageCount = computed(() =>
  Math.max(1, Math.ceil(faultDetailTraceEventsTotal.value / faultDetailTraceEventsPageSize)),
)
const faultDetailTraceEventsPageWindow = computed(() =>
  getPageWindow(faultDetailTraceEventsPage.value, faultDetailTraceEventsPageCount.value),
)
const selectedFaultDetailErrorLogTotal = computed(() => faultDetailTraceEventsTotal.value)

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
    const accessFields = [
      ...fields.slice(0, accessLogHeaders.length - 1),
      fields.slice(accessLogHeaders.length - 1).join(' | '),
    ]
    const message = accessLogHeaders
      .slice(7)
      .map((header, index) => `${header}: ${accessFields[index + 7] || '-'}`)
      .join(' | ')

    return {
      formatName: '接口日志',
      columns: normalizeTraceLogColumns(runLogHeaders, [...accessFields.slice(0, 7), message]),
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
    ? result.failure_mode.filter(
        (item): item is string => typeof item === 'string' && Boolean(item),
      )
    : []

  return {
    time: normalizeTimeText(getRecordString(record, ['timestamp', 'created_at', 'time'], '')),
    level,
    filename: logFile,
    podIp: (() => {
      const podIps = record['pod_ips']
      if (Array.isArray(podIps)) {
        return podIps.join('<br>')
      }
      return getRecordString(record, ['pod_ips', 'pod_ip', 'pod_name', 'pod_id', 'podId', 'pod'])
    })(),
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

const getVisibleTraceLogColumns = (log?: TraceLogRow) =>
  log?.rawColumns.filter((column) => column.label.toLowerCase() !== 'trace_id') ?? []

const isTraceLogMessageColumn = (column: TraceRawLogColumn) =>
  column.label.toLowerCase() === 'message'

const getTraceLogRowClass = (log: TraceLogRow) => ({
  'log-error': ['E', 'ERROR'].includes(log.level),
  'log-warning': ['W', 'WARN', 'WARNING'].includes(log.level),
  'log-info': !['E', 'ERROR', 'W', 'WARN', 'WARNING'].includes(log.level),
  'log-failure-mode': log.failureModeIds.length > 0,
})

const getTraceLogLevelClass = (log: TraceLogRow) =>
  ['E', 'ERROR'].includes(log.level)
    ? 'log-level-error'
    : ['W', 'WARN', 'WARNING'].includes(log.level)
      ? 'log-level-warning'
      : 'log-level-info'

const getTraceLogs = (trace?: TraceDetailRow | null) => {
  if (!trace) return []
  const traceId = trace.traceId
  return Object.prototype.hasOwnProperty.call(traceFailureLogsByTrace.value, traceId)
    ? (traceFailureLogsByTrace.value[traceId] ?? [])
    : []
}

const getSelectedTraceLogs = () => getTraceLogs(selectedTrace.value)

const getTraceFailureEvents = (trace?: TraceDetailRow | null) => {
  if (!trace) return []
  const traceId = trace.traceId
  return traceFailureEventsByTrace.value[traceId] ?? []
}

const getSelectedFaultTraceLogs = () => getTraceLogs(selectedFaultTrace.value)

const selectedTraceFailureModeIds = computed<string[]>(() => {
  const events = getTraceFailureEvents(selectedTrace.value)
  const ids = new Set<string>()
  events.forEach((event) => {
    getFailureModeIds(event as Record<string, unknown>).forEach((id) => ids.add(id))
  })
  return [...ids]
})

const selectedTraceFailureModes = computed<(FailureModeKnowledgeModel & { _id: string })[]>(
  () =>
    selectedTraceFailureModeIds.value
      .map((id) => {
        const detail = failureModeDetailsById.value[id]
        return { ...detail, _id: id }
      })
      .filter((item) => item.id || item.name || item._id) as (FailureModeKnowledgeModel & {
      _id: string
    })[],
)

const selectedTraceFailureMode = computed<(FailureModeKnowledgeModel & { _id: string }) | null>(
  () => {
    const selectedId = selectedTraceFailureModeId.value
    if (!selectedId) return null
    return (
      selectedTraceFailureModes.value.find((failureMode) => failureMode._id === selectedId) ?? null
    )
  },
)

const selectTraceFailureMode = (failureModeId: string) => {
  selectedTraceFailureModeId.value = failureModeId
  selectedChildFailureModeId.value = ''
  void loadFailureModeChildrenDetails(failureModeId)
}

const selectedFaultTraceFailureModeIds = computed<string[]>(() => {
  const events = getTraceFailureEvents(selectedFaultTrace.value)
  const ids = new Set<string>()
  events.forEach((event) => {
    getFailureModeIds(event as Record<string, unknown>).forEach((id) => ids.add(id))
  })
  return [...ids]
})

const selectedFaultTraceFailureModes = computed<(FailureModeKnowledgeModel & { _id: string })[]>(
  () =>
    selectedFaultTraceFailureModeIds.value
      .map((id) => {
        const detail = failureModeDetailsById.value[id]
        return { ...detail, _id: id }
      })
      .filter((item) => item.id || item.name || item._id) as (FailureModeKnowledgeModel & {
      _id: string
    })[],
)

const selectedFaultTraceFailureMode = computed<
  (FailureModeKnowledgeModel & { _id: string }) | null
>(() => {
  const selectedId = selectedFaultTraceFailureModeId.value
  if (!selectedId) return null
  return (
    selectedFaultTraceFailureModes.value.find((failureMode) => failureMode._id === selectedId) ??
    null
  )
})

const selectedChildFailureMode = computed<(FailureModeKnowledgeModel & { _id: string }) | null>(
  () => {
    const selectedId = selectedChildFailureModeId.value
    if (!selectedId) return null
    const detail = failureModeDetailsById.value[selectedId]
    if (!detail) return null
    return { ...detail, _id: selectedId }
  },
)

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
  selectedChildFailureModeId.value = selectedChildFailureModeId.value === childId ? '' : childId
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

const matchesLatencyRowPodIpFilters = (row: LatencyDetailRow) => {
  const { sourcePodIps, targetPodIps } = appliedFilters.value
  if (sourcePodIps.length > 0 && !sourcePodIps.includes(row.sourcePodIp)) return false
  if (targetPodIps.length > 0 && !targetPodIps.includes(row.targetPodIp)) return false
  return true
}

const getFilteredLatencyRows = () =>
  isLatencyEventListFilterMode.value
    ? latencyDetailRows.value
    : latencyDetailRows.value.filter(matchesLatencyRowPodIpFilters)

const matchesAbnormalTraceFilters = (row: AbnormalTraceRow) => {
  const filters = appliedFilters.value
  if (filters.clusters.length > 0 && !filters.clusters.includes(row.clusterName)) return false
  if (filters.hosts.length > 0 && !filters.hosts.includes(row.host)) return false
  if (filters.podIps.length > 0 && !filters.podIps.includes(row.podIp)) return false
  return true
}

const getFilteredAbnormalTraceRows = () => {
  return abnormalTraceRows.value.filter(matchesAbnormalTraceFilters)
}

watch(
  () => [
    activeAggregateTab.value,
    ...getFilteredAbnormalTraceRows().map((row) => `${row.id}:${row.podIp}`),
    ...traceListColumnWidths.latencyLeft,
    ...traceListColumnWidths.latencyData,
  ],
  () => {
    if (activeAggregateTab.value === 'trace') syncLatencyTraceRowHeights()
  },
  { immediate: true },
)

watch(
  () => [
    selectedAggregatedEvent.value?.id ?? '',
    ...detailParseResultRows.value.map((row) => `${row.id}:${row.podIp}`),
    ...traceListColumnWidths.latencyLeft,
    ...traceListColumnWidths.latencyData,
  ],
  () => {
    if (selectedAggregatedEvent.value) syncDetailLatencyTraceRowHeights()
  },
  { immediate: true },
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
    operation: getRecordString(record, ['operation'], ''),
  }
}

const getFilteredFaultTraceRows = () => {
  return faultTraceRows.value
}

const getFaultTraceFailureModeLabel = (row: FaultTraceTableRow) =>
  row.failureMode?.name || row.failureModeId || row.faultType || '-'

const openTraceDialog = (trace: TraceDetailRow) => {
  selectedTrace.value = trace
}

const closeTraceDialog = () => {
  selectedTrace.value = null
  selectedTraceFailureModeId.value = ''
  selectedChildFailureModeId.value = ''
}

const loadTraceLatencyData = async (traceId: string): Promise<LogParseResultModel | null> => {
  if (!selectedAssetId.value) return null
  try {
    const result = await request<{ total: number; log_parse_results: LogParseResultModel[] }>(
      '/log_parse_result/list',
      {
        method: 'POST',
        body: JSON.stringify({
          kb_id: selectedAssetId.value,
          trace_id: traceId,
          page_cnt: 1,
          page_num: 1,
        }),
      },
    )
    const results = result.log_parse_results ?? []
    return results[0] ?? null
  } catch {
    return null
  }
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
  const latencyData = await loadTraceLatencyData(trace.traceId)
  if (latencyData && selectedFaultTrace.value) {
    const record = latencyData as Record<string, unknown>
    selectedFaultTrace.value = {
      ...selectedFaultTrace.value,
      sdkMs: latencyData.total_latency ?? null,
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
      urmaLinkLatency: latencyData.urma_link_latency ?? null,
      c2wUrmaLatency: latencyData.c2w_urma_latency ?? null,
      w2wUrmaLatency: latencyData.w2w_urma_latency ?? null,
      sdkProcess: latencyData.sdk_process ?? null,
      sdkRpc: latencyData.sdk_rpc ?? null,
      localWorkerCost: latencyData.local_worker_cost ?? null,
      localWorkerLock: latencyData.local_worker_lock ?? null,
      remoteWorkerCost: latencyData.remote_worker_cost ?? null,
      remoteWorkerRpc: latencyData.remote_worker_rpc ?? null,
      masterProcess: latencyData.master_process ?? null,
      masterRpcTotal: latencyData.master_rpc_total ?? null,
    }
  }
}

const closeFaultTraceDialog = () => {
  selectedFaultTrace.value = null
  selectedFaultTraceFailureModeId.value = ''
  selectedChildFailureModeId.value = ''
}

const openParseResultChain = async (row: ParseResultTableRow) => {
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
  await loadTraceFailureLogs(row.traceId, true)
  const events = traceFailureEventsByTrace.value[row.traceId] ?? []
  const failureModeIds = new Set<string>()
  events.forEach((event) => {
    getFailureModeIds(event as Record<string, unknown>).forEach((id) => failureModeIds.add(id))
  })
  await Promise.all([...failureModeIds].map((id) => loadFailureModeDetail(id)))
}

type FilterTagCategory = 'cluster' | 'host' | 'podIp' | 'sourcePodIp' | 'targetPodIp'

type GlobalFilterListKey = 'clusters' | 'hosts' | 'podIps' | 'sourcePodIps' | 'targetPodIps'

const filterTagCollections: Record<FilterTagCategory, GlobalFilterListKey> = {
  cluster: 'clusters',
  host: 'hosts',
  podIp: 'podIps',
  sourcePodIp: 'sourcePodIps',
  targetPodIp: 'targetPodIps',
}

const replaceFilterItem = (category: FilterTagCategory, value: string) => {
  const normalized = value.trim()
  if (!normalized) return

  const key = filterTagCollections[category]
  globalFilters[key] = [normalized]
  filterApplyMessage.value = ''
}

const setSingleFilterItem = (category: 'cluster' | 'host', value: string) => {
  const normalized = value.trim()
  if (!normalized) return

  const key = filterTagCollections[category]
  globalFilters[key] = [normalized]
  filterApplyMessage.value = ''
}

const setSingleIpFilterItem = (category: 'sourcePodIp' | 'targetPodIp', value: string) => {
  const normalized = value.trim()
  if (!normalized) return

  const key = filterTagCollections[category]
  globalFilters[key] = [normalized]
  filterApplyMessage.value = ''
}

const addFilterValue = (category: FilterTagCategory) => {
  const value = filterDraftInput[category].trim()
  if (!value) return

  if (category === 'cluster' || category === 'host' || category === 'podIp') {
    replaceFilterItem(category, value)
  } else if (category === 'sourcePodIp' || category === 'targetPodIp') {
    setSingleIpFilterItem(category, value)
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
  globalFilters.podIps = []
  globalFilters.sourcePodIps = []
  globalFilters.targetPodIps = []
  filterDraftInput.cluster = ''
  filterDraftInput.host = ''
  filterDraftInput.podIp = ''
  filterDraftInput.sourcePodIp = ''
  filterDraftInput.targetPodIp = ''
  filterApplyMessage.value = ''
}

const addSourcePodIpFilter = (podIp: string) => {
  setSingleIpFilterItem('sourcePodIp', podIp)
}

const addTargetPodIpFilter = (podIp: string) => {
  setSingleIpFilterItem('targetPodIp', podIp)
}

const openLatencyPodIpFilterDialog = (row: LatencyDetailRow | FaultDetailRow) => {
  latencyPodIpFilterDialog.row = row
  latencyPodIpFilterDialog.addSourcePodIp = false
  latencyPodIpFilterDialog.addTargetPodIp = false
  latencyPodIpFilterDialog.addSourcePodIpToPodFilter = false
  latencyPodIpFilterDialog.addTargetPodIpToPodFilter = false
  latencyPodIpFilterDialog.open = true
}

const openFaultAggregatedPodIpFilterDialog = (podRow: FaultAggregatedEventPodRow) => {
  faultAggregatedPodIpFilterDialog.podRow = podRow
  faultAggregatedPodIpFilterDialog.addPodIp = false
  faultAggregatedPodIpFilterDialog.addSourcePodIp = false
  faultAggregatedPodIpFilterDialog.addTargetPodIp = false
  faultAggregatedPodIpFilterDialog.open = true
}

const openAggregatedEventDetail = (row: LatencyDetailRow) => {
  selectedAggregatedEvent.value = row
  detailParseResultsPage.value = 1
  detailParseResultsPageInput.value = ''
  detailParseResultTraceIdInput.value = ''
  detailParseResultTraceIdQuery.value = ''
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
  detailParseResultsPageInput.value = ''
  detailParseResultTraceIdInput.value = ''
  detailParseResultTraceIdQuery.value = ''
  detailLatencyChartInstance?.dispose()
  detailLatencyChartInstance = null
}

const getFaultAggregatedEventPodNames = (podRow: FaultAggregatedEventPodRow) =>
  [podRow.srcIp, podRow.dstIp]
    .map((podIp) => podIp.trim())
    .filter((podIp, index, podIps) => podIp && podIp !== '-' && podIps.indexOf(podIp) === index)

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
    const requestBody: Record<string, unknown> = {
      kb_id: selectedAssetId.value,
      src_ip: detail.podRow.srcIp,
      dst_ip: detail.podRow.dstIp,
      is_anomalous: true,
      start_time: detail.eventRow.startTime,
      end_time: detail.eventRow.endTime,
      operation: selectedFaultOperation.value.toUpperCase(),
      page_cnt: faultDetailTraceEventsPageSize,
      page_num: pageNum,
    }
    if (faultDetailTraceIdQuery.value) {
      requestBody.trace_ids = [faultDetailTraceIdQuery.value]
    }

    const result = await request<{
      total: number
      trace_failure_event_results: TraceFailureEventResultModel[]
    }>('/log_failure_event_result/list_trace_events', {
      method: 'POST',
      body: JSON.stringify(requestBody),
    })

    if (
      `${selectedFaultAggregatedEventDetail.value?.eventRow.id}-${selectedFaultAggregatedEventDetail.value?.podRow.id}` !==
      detailKey
    ) {
      return
    }

    const events = result.trace_failure_event_results ?? []
    const total = result.total ?? 0
    const pageCount = Math.max(1, Math.ceil(total / faultDetailTraceEventsPageSize))

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

      const traceIds = events.map((e) => e.trace_id).filter((id): id is string => !!id)
      await checkFaultTracesForLatency(traceIds)
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
        src_ip: detail.podRow.srcIp,
        dst_ip: detail.podRow.dstIp,
        start_time: detail.eventRow.startTime,
        end_time: detail.eventRow.endTime,
        operation: selectedFaultOperation.value.toUpperCase(),
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
  faultDetailTraceIdInput.value = ''
  faultDetailTraceIdQuery.value = ''
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
  faultDetailTraceIdInput.value = ''
  faultDetailTraceIdQuery.value = ''
  faultDetailTraceEventsError.value = ''
  isFaultDetailTraceEventsLoading.value = false
  faultDetailChartMetrics.value = {}
  faultDetailChartError.value = ''
  isFaultDetailChartLoading.value = false
  faultDetailChartInstance?.dispose()
  faultDetailChartInstance = null
}

const viewAbnormalTraceLink = async (row: AbnormalTraceRow) => {
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
  await loadTraceFailureLogs(row.traceId, true)
  const events = traceFailureEventsByTrace.value[row.traceId] ?? []
  const failureModeIds = new Set<string>()
  events.forEach((event) => {
    getFailureModeIds(event as Record<string, unknown>).forEach((id) => failureModeIds.add(id))
  })
  await Promise.all([...failureModeIds].map((id) => loadFailureModeDetail(id)))
}

const closeLatencyPodIpFilterDialog = () => {
  latencyPodIpFilterDialog.open = false
  latencyPodIpFilterDialog.row = null
}

const confirmLatencyPodIpFilterDialog = () => {
  const row = latencyPodIpFilterDialog.row
  if (!row) return

  if (latencyPodIpFilterDialog.addSourcePodIp) {
    addSourcePodIpFilter(row.sourcePodIp)
  }
  if (latencyPodIpFilterDialog.addTargetPodIp) {
    addTargetPodIpFilter(row.targetPodIp)
  }
  if (latencyPodIpFilterDialog.addSourcePodIpToPodFilter) {
    replaceFilterItem('podIp', row.sourcePodIp)
  }
  if (latencyPodIpFilterDialog.addTargetPodIpToPodFilter) {
    replaceFilterItem('podIp', row.targetPodIp)
  }

  closeLatencyPodIpFilterDialog()
}

const closeFaultAggregatedPodIpFilterDialog = () => {
  faultAggregatedPodIpFilterDialog.open = false
  faultAggregatedPodIpFilterDialog.podRow = null
}

const confirmFaultAggregatedPodIpFilterDialog = () => {
  const podRow = faultAggregatedPodIpFilterDialog.podRow
  if (!podRow) return

  if (faultAggregatedPodIpFilterDialog.addPodIp) {
    getFaultAggregatedEventPodNames(podRow).forEach((podIp) => replaceFilterItem('podIp', podIp))
  }
  if (
    faultAggregatedPodIpFilterDialog.addSourcePodIp &&
    isTraceFilterValueAvailable(podRow.srcIp)
  ) {
    addSourcePodIpFilter(podRow.srcIp)
  }
  if (
    faultAggregatedPodIpFilterDialog.addTargetPodIp &&
    isTraceFilterValueAvailable(podRow.dstIp)
  ) {
    addTargetPodIpFilter(podRow.dstIp)
  }

  closeFaultAggregatedPodIpFilterDialog()
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
  traceFilterDialog.addPodIp = false
  traceFilterDialog.addSourcePodIp = false
  traceFilterDialog.addTargetPodIp = false
  traceFilterDialog.addTraceBoard = false
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
  if (traceFilterDialog.addPodIp && isTraceFilterValueAvailable(trace.podIp)) {
    replaceFilterItem('podIp', trace.podIp)
  }
  if (traceFilterDialog.addSourcePodIp && isTraceFilterValueAvailable(trace.podIp)) {
    addSourcePodIpFilter(trace.podIp)
  }
  if (traceFilterDialog.addTargetPodIp && isTraceFilterValueAvailable(trace.podIp)) {
    addTargetPodIpFilter(trace.podIp)
  }
  if (traceFilterDialog.addTraceBoard) {
    addTraceBoardValue(trace.traceId)
  }

  closeTraceFilterDialog()
}

const snapshotCurrentFilters = (): GlobalFilterState => ({
  startTime: globalFilters.startTime,
  endTime: globalFilters.endTime,
  clusters: globalFilters.clusters.map(normalizeFilterText).filter(Boolean).slice(-1),
  hosts: globalFilters.hosts.map(normalizeFilterText).filter(Boolean).slice(-1),
  podIps: globalFilters.podIps.map(normalizeFilterText).filter(Boolean).slice(-1),
  sourcePodIps: globalFilters.sourcePodIps.map(normalizeFilterText).filter(Boolean).slice(-1),
  targetPodIps: globalFilters.targetPodIps.map(normalizeFilterText).filter(Boolean).slice(-1),
  traceBoards: [],
})

const getActiveFilterCount = (filters: GlobalFilterState) => {
  const traceFilterCount =
    (filters.startTime || filters.endTime ? 1 : 0) +
    filters.clusters.length +
    filters.hosts.length +
    filters.podIps.length
  return traceFilterCount + filters.sourcePodIps.length + filters.targetPodIps.length
}

const clearFilterApplyMessage = () => {
  filterApplyMessage.value = ''
}

const applyGlobalFilters = () => {
  const nextFilters = snapshotCurrentFilters()
  appliedFilters.value = nextFilters

  const activeCount = getActiveFilterCount(nextFilters)

  filterApplyMessage.value = activeCount > 0 ? `已确认 ${activeCount} 个筛选条件` : '已清空筛选条件'
  latencyChartCenterTime.value = null
  faultChartCenterTime.value = null
  void loadLatencyChart()
  void loadTimeWindowAggregatedEvents(timeWindowPage.value, null)
  void loadAbnormalTraces(abnormalTracesPage.value)
  void loadFaultChart()
  void loadFaultAggregatedEvents(faultAggregatedEventPage.value)
  void loadFaultTraceEvents(faultTraceEventsPage.value)
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
        ...new Set(events.flatMap((event) => getFailureModeIds(event as Record<string, unknown>))),
      ]

      await Promise.all(failureModeIds.map((failureModeId) => loadFailureModeDetail(failureModeId)))
    }

    traceFailureEventsByTrace.value = {
      ...traceFailureEventsByTrace.value,
      [traceId]: events,
    }
    traceFailureLogsByTrace.value = {
      ...traceFailureLogsByTrace.value,
      [traceId]: events.map(toTraceLogRow),
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
  const scale = selectedFaultScale.value
  if (!selectedAssetId.value) {
    faultTraceRowsMap[scale] = []
    faultTraceEventsTotalMap[scale] = 0
    faultTraceEventsPageMap[scale] = 1
    return
  }

  isFaultTraceEventsLoadingMap[scale] = true
  faultTraceEventsErrorMap[scale] = ''

  try {
    const filters = appliedFilters.value
    const chartRange = faultChartRange.value
    const requestBody: Record<string, unknown> = {
      kb_id: selectedAssetId.value,
      is_anomalous: true,
      operation: selectedFaultOperation.value.toUpperCase(),
      page_cnt: faultTraceEventsPageSize,
      page_num: pageNum,
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
    if (filters.podIps.length > 0) {
      requestBody.pod_names = filters.podIps
    }
    if (filters.sourcePodIps.length > 0) {
      requestBody.src_ip = getLogParseFilterValue(filters.sourcePodIps)
    }
    if (filters.targetPodIps.length > 0) {
      requestBody.dst_ip = getLogParseFilterValue(filters.targetPodIps)
    }
    if (chartRange) {
      requestBody.start_time = formatTimestamp(chartRange.startTime)
      requestBody.end_time = formatTimestamp(chartRange.endTime)
    }
    if (faultTraceIdQuery.value) {
      requestBody.trace_ids = [faultTraceIdQuery.value]
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
      isFaultTraceEventsLoadingMap[scale] = false
      await loadFaultTraceEvents(pageCount)
      return
    }

    const failureModeIds = [
      ...new Set(events.flatMap((event) => getFailureModeIds(event as Record<string, unknown>))),
    ]

    await Promise.all(failureModeIds.map((failureModeId) => loadFailureModeDetail(failureModeId)))

    faultTraceRowsMap[scale] = events.map(toFaultTraceTableRow)
    faultTraceEventsTotalMap[scale] = total
    faultTraceEventsPageMap[scale] = pageNum

    const traceIds = events.map((e) => e.trace_id).filter((id): id is string => !!id)
    await checkFaultTracesForLatency(traceIds)
  } catch (error) {
    faultTraceRowsMap[scale] = []
    faultTraceEventsTotalMap[scale] = 0
    faultTraceEventsPageMap[scale] = 1
    faultTraceEventsErrorMap[scale] =
      error instanceof Error ? error.message : '加载错误日志列表失败'
    faultTraceIdsWithLatency.value = new Set()
  } finally {
    isFaultTraceEventsLoadingMap[scale] = false
    syncFaultTraceRowHeights()
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
    const chartRange = faultChartRange.value
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
    if (filters.podIps.length > 0) {
      requestBody.pod_names = filters.podIps
    }
    if (filters.sourcePodIps.length > 0) {
      requestBody.src_ip = getLogParseFilterValue(filters.sourcePodIps)
    }
    if (filters.targetPodIps.length > 0) {
      requestBody.dst_ip = getLogParseFilterValue(filters.targetPodIps)
    }
    if (chartRange) {
      requestBody.start_time = formatTimestamp(chartRange.startTime)
      requestBody.end_time = formatTimestamp(chartRange.endTime)
    }
    requestBody.operation = selectedFaultOperation.value.toUpperCase()

    const result = await request<{
      total: number
      metrics: Record<string, ErrCodeMetricItem[]>
    }>('/log_failure_event_result/metrics/err_code', {
      method: 'POST',
      body: JSON.stringify(requestBody),
    })

    faultChartMetrics.value = result.metrics ?? {}
    const codes = Object.keys(result.metrics ?? {})
    if (codes.length > 0) {
      knownFaultCodes.value = codes.sort((a, b) => a.localeCompare(b))
    }
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



const timestampToDatetimeLocal = (ts: number) => {
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const formatTimestamp = (ts: number) => {
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const normalizeTraceIdQuery = (value: string) => value.trim()

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

const loadLatencyChart = async () => {
  const percentile = selectedLatencyPercentile.value

  if (!selectedAssetId.value) {
    latencyMetricsByPercentile[percentile] = []
    latencyChartError.value = ''
    isLatencyChartLoading.value = false
    return
  }

  const assetId = selectedAssetId.value
  isLatencyChartLoading.value = true
  latencyChartError.value = ''

  const range = latencyChartRange.value

  try {
    const filters = appliedFilters.value
    const body: Record<string, unknown> = {
      kb_id: assetId,
      max_points: 1000,
      sample_mode: latencySampleModeMap[percentile],
      sort_by: 'timestamp',
      sort_order: 'asc',
      operation: selectedOperation.value.toUpperCase(),
    }

    if (filters.startTime) {
      body.start_time = formatDateTime(filters.startTime)
    }
    if (filters.endTime) {
      body.end_time = formatDateTime(filters.endTime)
    }
    if (filters.clusters.length > 0) {
      body.cluster_name = getLogParseFilterValue(filters.clusters)
    }
    if (filters.podIps.length > 0) {
      body.pod_ip = getLogParseFilterValue(filters.podIps)
    }
    if (filters.hosts.length > 0) {
      body.host = getLogParseFilterValue(filters.hosts)
    }
    if (filters.sourcePodIps.length > 0) {
      body.src_ip = getLogParseFilterValue(filters.sourcePodIps)
    }
    if (filters.targetPodIps.length > 0) {
      body.dst_ip = getLogParseFilterValue(filters.targetPodIps)
    }
    if (range) {
      body.start_time = formatTimestamp(range.startTime)
      body.end_time = formatTimestamp(range.endTime)
    }
    const result = await request<{ total: number; metrics: LatencyMetricItem[] }>(
      '/log_parse_result/metrics/latency',
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
    )

    latencyMetricsByPercentile[percentile] = result.metrics ?? []
  } catch (error) {
    latencyMetricsByPercentile[percentile] = []
    latencyChartError.value = error instanceof Error ? error.message : '加载延迟趋势失败'
  } finally {
    isLatencyChartLoading.value = false
  }
}

watch(selectedOperation, () => {
  visibleLatencyKeys.value = new Set<LatencyMetricKey>(['total_latency'])
  loadLatencyChart()
  loadLatencyDetail()
  loadTimeWindowAggregatedEvents()
  loadAbnormalTraces(1)
  if (selectedAggregatedEvent.value) {
    selectedAggregatedEvent.value.operation = selectedOperation.value.toUpperCase()
    detailParseResultsPage.value = 1
    void loadDetailParseResults(selectedAggregatedEvent.value, 1)
  }
})

watch(selectedFaultOperation, () => {
  loadFaultChart()
  loadFaultAggregatedEvents(1)
  loadFaultTraceEvents(1)
})

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
    const requestBody: Record<string, unknown> = {
      kb_id: assetId,
      src_ip: row.sourcePodIp === '-' ? undefined : row.sourcePodIp,
      dst_ip: row.targetPodIp === '-' ? undefined : row.targetPodIp,
      max_points: 30,
      sort_by: 'timestamp',
      sort_order: 'asc',
    }
    if (row.startTime) {
      requestBody.start_time = row.startTime
    }
    if (row.endTime) {
      requestBody.end_time = row.endTime
    }
    const result = await request<{ total: number; metrics: LatencyMetricItem[] }>(
      '/log_parse_result/metrics/latency',
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
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
    const requestBody: Record<string, unknown> = {
      kb_id: assetId,
      aggregated_event_id: row.startTime || row.endTime ? undefined : row.id,
      src_ip: row.sourcePodIp === '-' ? undefined : row.sourcePodIp,
      dst_ip: row.targetPodIp === '-' ? undefined : row.targetPodIp,
      start_time: row.startTime || undefined,
      end_time: row.endTime || undefined,
      page_cnt: detailParseResultsPageSize,
      page_num: pageNum,
      sort_fields: sortFields.length > 0 ? sortFields : undefined,
      is_anomalous: true,
      operation: row.operation || undefined,
    }
    if (detailParseResultTraceIdQuery.value) {
      requestBody.trace_id = detailParseResultTraceIdQuery.value
    }

    const result = await request<{ total: number; log_parse_results: LogParseResultModel[] }>(
      '/log_parse_result/list',
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
        signal: detailParseResultSort.getAbortSignal(),
      },
    )

    if (selectedAggregatedEvent.value?.id === row.id) {
      detailParseResults.value = result.log_parse_results ?? []
      detailParseResultsTotal.value = result.total ?? detailParseResults.value.length
      detailParseResultsPage.value = pageNum

      const traceIds = (result.log_parse_results ?? [])
        .map((r) => r.trace_id)
        .filter((id): id is string => !!id)
      await checkLatencyTracesForFault(traceIds)
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
      latencyTraceIdsWithFault.value = new Set()
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

const submitDetailParseResultTraceIdQuery = () => {
  const row = selectedAggregatedEvent.value
  if (!row) return
  const nextTraceId = normalizeTraceIdQuery(detailParseResultTraceIdInput.value)
  detailParseResultTraceIdInput.value = nextTraceId
  if (nextTraceId === detailParseResultTraceIdQuery.value && detailParseResultsPage.value === 1) {
    return
  }
  detailParseResultTraceIdQuery.value = nextTraceId
  detailParseResultsPageInput.value = ''
  void loadDetailParseResults(row, 1)
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
  if (nextPage === faultDetailTraceEventsPage.value || isFaultDetailTraceEventsLoading.value) return
  void loadFaultAggregatedEventDetailTraceEvents(detail, nextPage)
}

const submitFaultDetailTraceIdQuery = () => {
  const detail = selectedFaultAggregatedEventDetail.value
  if (!detail) return
  const nextTraceId = normalizeTraceIdQuery(faultDetailTraceIdInput.value)
  faultDetailTraceIdInput.value = nextTraceId
  if (nextTraceId === faultDetailTraceIdQuery.value && faultDetailTraceEventsPage.value === 1) {
    return
  }
  faultDetailTraceIdQuery.value = nextTraceId
  faultDetailTraceEventsPageInput.value = ''
  void loadFaultAggregatedEventDetailTraceEvents(detail, 1)
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

    const chartRange = latencyChartRange.value
    const result = await request<unknown>('/aggregated_event/list', {
      method: 'POST',
      body: JSON.stringify({
        kb_id: assetId,
        page_num: pageNum,
        page_cnt: aggregateEventPageSize,
        stat_type: statType,
        sort_fields: sortFields.length > 0 ? sortFields : undefined,
        cluster_name: getLogParseFilterValue(filters.clusters),
        host: getLogParseFilterValue(filters.hosts),
        pod_ip: getLogParseFilterValue(filters.podIps),
        src_ip: getLogParseFilterValue(filters.sourcePodIps),
        dst_ip: getLogParseFilterValue(filters.targetPodIps),
        start_time: chartRange ? formatTimestamp(chartRange.startTime) : undefined,
        end_time: chartRange ? formatTimestamp(chartRange.endTime) : undefined,
        operation: selectedOperation.value.toUpperCase(),
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
    const nextPageCount = Math.max(1, Math.ceil(nextTotal / aggregateEventPageSize))

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

// 时间窗口聚合事件列表
const loadTimeWindowAggregatedEvents = async (
  pageNum = timeWindowPage.value,
  chartRange?: { startTime: number; endTime: number } | null,
) => {
  if (!selectedAssetId.value) {
    timeWindowAggregatedEvents.value = []
    timeWindowTotal.value = 0
    timeWindowPage.value = 1
    timeWindowError.value = ''
    isTimeWindowLoading.value = false
    return
  }

  // 如果传入了 chartRange 参数，更新 ref；否则使用已保存的值
  if (chartRange !== undefined) {
    timeWindowChartRange.value = chartRange ?? null
  }
  const currentChartRange = timeWindowChartRange.value

  const assetId = selectedAssetId.value
  isTimeWindowLoading.value = true
  timeWindowError.value = ''
  expandedTimeWindowIds.value = new Set()

  try {
    const filters = appliedFilters.value
    const sortFields = timeWindowSortFields.value
    const primarySortField = sortFields[0] ?? {
      field: 'start_time',
      order: timeWindowStartTimeSortOrder.value,
    }
    const requestBody: Record<string, unknown> = {
      kb_id: assetId,
      page_num: pageNum,
      page_cnt: 10,
      interval: selectedLatencyTimeWindowInterval.value,
      stat_type: 'p99',
      sort_fields: sortFields.length > 0 ? sortFields : undefined,
      sort_by: primarySortField.field,
      sort_order: primarySortField.order,
      cluster_name: getLogParseFilterValue(filters.clusters),
      host: getLogParseFilterValue(filters.hosts),
      pod_ip: getLogParseFilterValue(filters.podIps),
      src_ip: getLogParseFilterValue(filters.sourcePodIps),
      dst_ip: getLogParseFilterValue(filters.targetPodIps),
      operation: selectedOperation.value.toUpperCase(),
    }
    if (currentChartRange) {
      requestBody.start_time = formatTimestamp(currentChartRange.startTime)
      requestBody.end_time = formatTimestamp(currentChartRange.endTime)
    } else {
      if (filters.startTime) {
        requestBody.start_time = formatDateTime(filters.startTime)
      }
      if (filters.endTime) {
        requestBody.end_time = formatDateTime(filters.endTime)
      }
    }
    const result = await request<unknown>('/aggregated_event/list_time_window', {
      method: 'POST',
      body: JSON.stringify(requestBody),
    })
    const events = extractListItems<TimeWindowAggregatedEvent>(result, [
      'events',
      'items',
      'list',
      'time_window_events',
    ])
    const total =
      result && typeof result === 'object'
        ? ((result as Record<string, unknown>).total as number | undefined)
        : undefined
    const nextTotal = total ?? events.length
    const nextPageCount = Math.max(1, Math.ceil(nextTotal / 10))

    if (pageNum > nextPageCount) {
      isTimeWindowLoading.value = false
      await loadTimeWindowAggregatedEvents(nextPageCount)
      return
    }

    timeWindowAggregatedEvents.value = events
    timeWindowTotal.value = nextTotal
    timeWindowPage.value = pageNum
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return
    }
    timeWindowAggregatedEvents.value = []
    timeWindowTotal.value = 0
    timeWindowPage.value = 1
    timeWindowError.value = error instanceof Error ? error.message : '加载时间窗口聚合事件失败'
  } finally {
    isTimeWindowLoading.value = false
  }
}

const changeLatencyTimeWindowInterval = () => {
  timeWindowPage.value = 1
  void loadTimeWindowAggregatedEvents(1)
}

const toggleTimeWindowRow = (idx: number) => {
  const newSet = new Set(expandedTimeWindowIds.value)
  if (newSet.has(idx)) {
    newSet.delete(idx)
  } else {
    newSet.add(idx)
    setTimeWindowIpPairPage(idx, 1)
  }
  expandedTimeWindowIds.value = newSet
}

const isTimeWindowExpanded = (idx: number) => expandedTimeWindowIds.value.has(idx)

const goTimeWindowPage = (pageNum: number) => {
  const nextPage = Math.min(Math.max(1, pageNum), timeWindowPageCount.value)
  if (nextPage === timeWindowPage.value || isTimeWindowLoading.value) return
  void loadTimeWindowAggregatedEvents(nextPage)
}

const jumpTimeWindowPage = () => {
  const nextPage = normalizePageInput(timeWindowPageInput.value, timeWindowPageCount.value)
  if (nextPage === null) return
  timeWindowPageInput.value = ''
  goTimeWindowPage(nextPage)
}

const handleTimeWindowSort = (sortBy: string) => {
  timeWindowSortFields.value = getNextTimeWindowSortFields(timeWindowSortFields.value, sortBy)
  timeWindowPage.value = 1
  void loadTimeWindowAggregatedEvents(1)
}

const setTimeWindowStartTimeSort = (order: SortField['order']) => {
  timeWindowSortFields.value = []
  timeWindowStartTimeSortOrder.value = order
  timeWindowPage.value = 1
  timeWindowPageInput.value = ''
  void loadTimeWindowAggregatedEvents(1)
}

const handleTimeWindowStartTimeSort = () => {
  setTimeWindowStartTimeSort(
    isTimeWindowStartTimeSortActive.value && timeWindowStartTimeSortOrder.value === 'asc'
      ? 'desc'
      : 'asc',
  )
}

const handleIpPairSort = (sortBy: string) => {
  timeWindowIpPairSortFields.value = getNextTimeWindowSortFields(
    timeWindowIpPairSortFields.value,
    sortBy,
  )
  timeWindowIpPairPageMap.value = {}
}

const getSortedIpPairs = (event: TimeWindowAggregatedEvent): TimeWindowAggregatedIpPair[] => {
  const pairs = [...event.ip_pairs]
  const sortFields = timeWindowIpPairSortFields.value
  const getValue = (pair: TimeWindowAggregatedIpPair, key: string): number => {
    if (key === 'total_cnt') return pair.log_parse_result_cnt
    if (key === 'anomaly_cnt') return pair.anomaly_log_parse_result_cnt
    const metricKey = `ave_${key}` as keyof TimeWindowAggregatedIpPair
    const val = pair[metricKey]
    return typeof val === 'number' ? val : 0
  }
  pairs.sort((a, b) => {
    for (const sortField of sortFields) {
      const result = compareSortValues(
        getValue(a, sortField.field),
        getValue(b, sortField.field),
        sortField.order,
      )
      if (result !== 0) return result
    }
    return 0
  })
  return pairs
}

const getTimeWindowAggregatedLatencyValue = (
  ipPair: TimeWindowAggregatedIpPair,
  metric: string,
) => {
  const key = `ave_${metric}` as keyof TimeWindowAggregatedIpPair
  const val = ipPair[key]
  return typeof val === 'number' ? val : null
}

const openTimeWindowIpPairDetail = (
  ipPair: TimeWindowAggregatedIpPair,
  twEvent: TimeWindowAggregatedEvent,
) => {
  // 构造一个聚合事件模型来复用详情弹窗
  const event: AggregatedEventModel = {
    id: `${ipPair.src_ip}-${ipPair.dst_ip}`,
    src_ip: ipPair.src_ip,
    dst_ip: ipPair.dst_ip,
    log_parse_result_cnt: ipPair.log_parse_result_cnt,
    anomaly_log_parse_result_cnt: ipPair.anomaly_log_parse_result_cnt,
    ave_total_latency: ipPair.ave_total_latency,
    min_total_latency: ipPair.min_total_latency,
    max_total_latency: ipPair.max_total_latency,
    p99_total_latency: ipPair.p99_total_latency,
    p95_total_latency: ipPair.p95_total_latency,
    ave_query_meta_latency: ipPair.ave_query_meta_latency,
    min_query_meta_latency: ipPair.min_query_meta_latency,
    max_query_meta_latency: ipPair.max_query_meta_latency,
    p99_query_meta_latency: ipPair.p99_query_meta_latency,
    p95_query_meta_latency: ipPair.p95_query_meta_latency,
    ave_urma_total_latency: ipPair.ave_urma_total_latency,
    min_urma_total_latency: ipPair.min_urma_total_latency,
    max_urma_total_latency: ipPair.max_urma_total_latency,
    p99_urma_total_latency: ipPair.p99_urma_total_latency,
    p95_urma_total_latency: ipPair.p95_urma_total_latency,
    ave_urma_link_latency: ipPair.ave_urma_link_latency,
    min_urma_link_latency: ipPair.min_urma_link_latency,
    max_urma_link_latency: ipPair.max_urma_link_latency,
    p99_urma_link_latency: ipPair.p99_urma_link_latency,
    p95_urma_link_latency: ipPair.p95_urma_link_latency,
    ave_c2w_urma_latency: ipPair.ave_c2w_urma_latency,
    min_c2w_urma_latency: ipPair.min_c2w_urma_latency,
    max_c2w_urma_latency: ipPair.max_c2w_urma_latency,
    p99_c2w_urma_latency: ipPair.p99_c2w_urma_latency,
    p95_c2w_urma_latency: ipPair.p95_c2w_urma_latency,
    ave_w2w_urma_latency: ipPair.ave_w2w_urma_latency,
    min_w2w_urma_latency: ipPair.min_w2w_urma_latency,
    max_w2w_urma_latency: ipPair.max_w2w_urma_latency,
    p99_w2w_urma_latency: ipPair.p99_w2w_urma_latency,
    p95_w2w_urma_latency: ipPair.p95_w2w_urma_latency,
  }
  const row: LatencyDetailRow = {
    id: `${ipPair.src_ip}-${ipPair.dst_ip}`,
    sourcePodIp: ipPair.src_ip,
    targetPodIp: ipPair.dst_ip,
    traceCount: ipPair.log_parse_result_cnt,
    anomalyTraceCount: ipPair.anomaly_log_parse_result_cnt,
    startTime: twEvent.start_time,
    endTime: twEvent.end_time,
    event,
  }
  openAggregatedEventDetail(row)
}

const openTimeWindowIpPairFilter = (ipPair: TimeWindowAggregatedIpPair) => {
  const row: LatencyDetailRow = {
    id: `${ipPair.src_ip}-${ipPair.dst_ip}`,
    sourcePodIp: ipPair.src_ip,
    targetPodIp: ipPair.dst_ip,
    traceCount: ipPair.log_parse_result_cnt,
    anomalyTraceCount: ipPair.anomaly_log_parse_result_cnt,
    event: {} as AggregatedEventModel,
  }
  openLatencyPodIpFilterDialog(row)
}

const getTimeWindowSummaryValue = (twEvent: TimeWindowAggregatedEvent, metric: string) => {
  const key = `ave_${metric}` as keyof TimeWindowAggregatedEvent
  const val = twEvent[key]
  return typeof val === 'number' ? val : null
}

const toAbnormalTraceRow = (result: LogParseResultModel): AbnormalTraceRow => {
  const record = result as Record<string, unknown>
  return {
    id: result.id,
    logStatus: getLogDisplayStatus(record),
    statusReason: getLogDisplayReason(record),
    time: result.timestamp ?? result.created_at ?? '-',
    traceId: result.trace_id ?? '-',
    podIp: Array.isArray(result.pod_ips) ? result.pod_ips.join('<br>') : (result.pod_ips ?? '-'),
    operation: normalizeTraceOperation(
      getRecordString(record, ['operation', 'op_type', 'operation_type', 'method']),
    ),
    clusterName: getRecordString(record, ['cluster_name'], 'null'),
    host: getDisplayHost(record),
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
    createLatency: getRecordNullableNumber(record, ['create_latency']),
    publishLatency: getRecordNullableNumber(record, ['publish_latency']),
    workerTotalLatency: getRecordNullableNumber(record, ['worker_total_latency']),
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
  const scale = selectedLatencyScale.value
  if (!selectedAssetId.value) {
    abnormalTraceRowsMap[scale] = []
    abnormalTracesTotalMap[scale] = 0
    abnormalTracesPageMap[scale] = 1
    abnormalTracesErrorMap[scale] = ''
    isAbnormalTracesLoadingMap[scale] = false
    return
  }

  const assetId = selectedAssetId.value
  isAbnormalTracesLoadingMap[scale] = true
  abnormalTracesErrorMap[scale] = ''

  try {
    const filters = appliedFilters.value

    // 构建排序参数
    const sortFields = abnormalTraceSort.getSortFields.value
    const chartRange = latencyChartRange.value

    const body: Record<string, unknown> = {
      kb_id: assetId,
      page_cnt: abnormalTracesPageSize,
      page_num: pageNum,
      sort_fields: sortFields.length > 0 ? sortFields : undefined,
      is_anomalous: true,
      operation: selectedOperation.value.toUpperCase(),
      start_time: chartRange
        ? formatTimestamp(chartRange.startTime)
        : formatDateTime(filters.startTime),
      end_time: chartRange ? formatTimestamp(chartRange.endTime) : formatDateTime(filters.endTime),
      cluster_name: getLogParseFilterValue(filters.clusters),
      host: getLogParseFilterValue(filters.hosts),
      pod_ip: getLogParseFilterValue(filters.podIps),
      src_ip: getLogParseFilterValue(filters.sourcePodIps),
      dst_ip: getLogParseFilterValue(filters.targetPodIps),
    }
    if (abnormalTraceIdQuery.value) {
      body.trace_id = abnormalTraceIdQuery.value
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
      isAbnormalTracesLoadingMap[scale] = false
      abnormalTraceSort.releaseSortLock()
      await loadAbnormalTraces(pageCount)
      return
    }

    abnormalTraceRowsMap[scale] = (result.log_parse_results ?? []).map(toAbnormalTraceRow)
    abnormalTracesTotalMap[scale] = total
    abnormalTracesPageMap[scale] = pageNum

    const traceIds = (result.log_parse_results ?? [])
      .map((r) => r.trace_id)
      .filter((id): id is string => !!id)
    await checkLatencyTracesForFault(traceIds)
  } catch (error) {
    // 忽略取消请求的错误
    if (error instanceof DOMException && error.name === 'AbortError') {
      return
    }
    abnormalTraceRowsMap[scale] = []
    abnormalTracesTotalMap[scale] = 0
    abnormalTracesPageMap[scale] = 1
    abnormalTracesErrorMap[scale] = error instanceof Error ? error.message : '加载时延异常列表失败'
    latencyTraceIdsWithFault.value = new Set()
  } finally {
    isAbnormalTracesLoadingMap[scale] = false
    abnormalTraceSort.releaseSortLock()
    syncAbnormalTraceRowHeights()
  }
}

const goAbnormalTracesPage = (pageNum: number) => {
  const scale = selectedLatencyScale.value
  const nextPage = Math.min(Math.max(1, pageNum), abnormalTracesPageCount.value)
  if (nextPage === abnormalTracesPageMap[scale] || isAbnormalTracesLoadingMap[scale]) return
  void loadAbnormalTraces(nextPage)
}

const submitAbnormalTraceIdQuery = () => {
  const nextTraceId = normalizeTraceIdQuery(abnormalTraceIdInput.value)
  abnormalTraceIdInput.value = nextTraceId
  if (nextTraceId === abnormalTraceIdQuery.value && abnormalTracesPage.value === 1) return
  abnormalTraceIdQuery.value = nextTraceId
  abnormalTracesPageInput.value = ''
  void loadAbnormalTraces(1)
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
  events: SrcDstAggregatedFailureEventModel[],
): FaultAggregatedEventPodRow[] =>
  events.map((event, index) => ({
    id: `${eventId}-srcdst-api-${event.src_ip}-${event.dst_ip}-${index}`,
    srcIp: event.src_ip || '-',
    dstIp: event.dst_ip || '-',
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
    const filters = appliedFilters.value
    const sortFields = faultAggregatedEventPodSort.getSortFields.value
    const result = await request<ListSrcDstAggregatedFailureEventMsg>(
      '/log_failure_event_result/list_src_dst_aggregated_failure_events',
      {
        method: 'POST',
        body: JSON.stringify({
          kb_id: selectedAssetId.value,
          start_time: row.startTime,
          end_time: row.endTime,
          cluster_name: getLogParseFilterValue(filters.clusters),
          host: getLogParseFilterValue(filters.hosts),
          pod_ip: getLogParseFilterValue(filters.podIps),
          src_ip: getLogParseFilterValue(filters.sourcePodIps),
          dst_ip: getLogParseFilterValue(filters.targetPodIps),
          operation: selectedFaultOperation.value.toUpperCase(),
          sort_fields: sortFields.length > 0 ? sortFields : undefined,
          sort_by: 'all',
          sort_desc: true,
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
  if (nextPage === getFaultAggregatedEventPodPage(row) || isFaultAggregatedEventPodLoading(row))
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
  applyFaultAggregatedEventResult(
    {
      total: 0,
      err_codes: [],
      events: [],
    },
    pageNum,
  )

  try {
    const filters = appliedFilters.value
    const sortFields = faultAggregatedEventSort.getSortFields.value
    const chartRange = faultChartRange.value
    const requestBody: Record<string, unknown> = {
      kb_id: selectedAssetId.value,
      interval: selectedFaultAggregateInterval.value,
      cluster_name: getLogParseFilterValue(filters.clusters),
      host: getLogParseFilterValue(filters.hosts),
      pod_ip: getLogParseFilterValue(filters.podIps),
      src_ip: getLogParseFilterValue(filters.sourcePodIps),
      dst_ip: getLogParseFilterValue(filters.targetPodIps),
      operation: selectedFaultOperation.value.toUpperCase(),
      sort_fields: sortFields.length > 0 ? sortFields : undefined,
      sort_by: 'timestamp',
      sort_desc: faultAggregatedEventSortDesc.value,
      page_cnt: faultAggregatedEventPageSize,
      page_num: pageNum,
    }

    if (chartRange) {
      requestBody.start_time = formatTimestamp(chartRange.startTime)
      requestBody.end_time = formatTimestamp(chartRange.endTime)
    } else {
      if (filters.startTime) {
        requestBody.start_time = formatDateTime(filters.startTime)
      }
      if (filters.endTime) {
        requestBody.end_time = formatDateTime(filters.endTime)
      }
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
    faultAggregatedEventsError.value = error instanceof Error ? error.message : '加载聚合事件失败'
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

const setFaultAggregatedEventStartTimeSort = (sortDesc: boolean) => {
  faultAggregatedEventSort.setSortFields([])
  faultAggregatedEventSortDesc.value = sortDesc
  faultAggregatedEventPage.value = 1
  faultAggregatedEventPageInput.value = ''
  void loadFaultAggregatedEvents(1)
}

const handleFaultAggregatedEventStartTimeSort = () => {
  setFaultAggregatedEventStartTimeSort(
    isFaultAggregatedEventStartTimeSortActive.value ? !faultAggregatedEventSortDesc.value : false,
  )
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

const submitFaultTraceIdQuery = () => {
  const nextTraceId = normalizeTraceIdQuery(faultTraceIdInput.value)
  faultTraceIdInput.value = nextTraceId
  if (nextTraceId === faultTraceIdQuery.value && faultTraceEventsPage.value === 1) return
  faultTraceIdQuery.value = nextTraceId
  faultTraceEventsPageInput.value = ''
  void loadFaultTraceEvents(1)
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

const handleAssetClick = (assetId: string) => {
  void loadAssetDetail(assetId)
}

const loadAssetDetail = async (assetId: string) => {
  // Save current asset state before switching
  if (selectedAssetId.value) {
    assetStates.value[selectedAssetId.value] = {
      filters: { ...globalFilters },
      appliedFilters: { ...appliedFilters.value },
      latencyChartCenterTime: latencyChartCenterTime.value,
      faultChartCenterTime: faultChartCenterTime.value,
      selectedLatencyScale: selectedLatencyScale.value,
      selectedFaultScale: selectedFaultScale.value,
      logSourceInput: logSourceInput.value,
      uploadLogError: uploadLogError.value,
    }
  }
  
  // Switch to new asset
  activePage.value = 'asset'
  selectedAssetId.value = assetId
  
  // Restore or initialize asset state
  const savedState = assetStates.value[assetId] || createEmptyAssetState()
  Object.assign(globalFilters, savedState.filters)
  appliedFilters.value = savedState.appliedFilters
  latencyChartCenterTime.value = savedState.latencyChartCenterTime
  faultChartCenterTime.value = savedState.faultChartCenterTime
  selectedLatencyScale.value = savedState.selectedLatencyScale
  selectedFaultScale.value = savedState.selectedFaultScale
  logSourceInput.value = savedState.logSourceInput
  uploadLogError.value = savedState.uploadLogError
  
  selectedAsset.value = null
  selectedTrace.value = null
  selectedFaultTrace.value = null
  Object.keys(faultTraceRowsMap).forEach((k) => {
    const key = Number(k)
    faultTraceRowsMap[key] = []
    faultTraceEventsTotalMap[key] = 0
    faultTraceEventsPageMap[key] = 1
    faultTraceEventsErrorMap[key] = ''
  })
  faultTraceEventsPageInput.value = ''
  traceFailureLogsByTrace.value = {}
  traceFailureEventsByTrace.value = {}
  traceLogsError.value = ''
  logFilesPage.value = 1
  logFilesPageInput.value = ''
  faultTraceIdsWithLatency.value = new Set()
  latencyTraceIdsWithFault.value = new Set()
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

const terminalTaskStatuses = new Set([
  'cancelled',
  'successful',
  'failed',
  'successful_pending_remove',
  'failed_pending_remove',
])

const isTerminalTaskStatus = (status?: string) =>
  Boolean(status && terminalTaskStatuses.has(status))

const getDetailedLogFileTask = (file: LogFileModel) =>
  file.task?.id ? (taskDetailsById.value[file.task.id] ?? file.task) : file.task

const getLogFileTaskStatus = (file: LogFileModel) =>
  getDetailedLogFileTask(file)?.status ?? file.parse_status ?? ''

const clampProgress = (value: number) => Math.min(100, Math.max(0, value))

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
  '解析失败：未在路径中识别到日志信息',
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
    [...reports].sort((first, second) => getTaskReportTime(second) - getTaskReportTime(first))[0] ??
    null
  )
}

const nonProgressReportPrefixes = ['[perf]', '[parse_log]', '[TASK]']
const isProgressReport = (report: TaskReportModel) => {
  const message = report.message?.trim() ?? ''
  return !nonProgressReportPrefixes.some((prefix) => message.startsWith(prefix))
}

const getLatestProgressReport = (file: LogFileModel) => {
  const reports = getLogFileTaskReports(file).filter(isProgressReport)
  if (reports.length === 0) return null
  return (
    [...reports].sort((first, second) => getTaskReportTime(second) - getTaskReportTime(first))[0] ??
    null
  )
}

const getLogFileProgress = (file: LogFileModel) => {
  const overallProgress = Number(file.overall_progress)
  if (Number.isFinite(overallProgress)) {
    return clampProgress(overallProgress)
  }
  const latestReport = getLatestProgressReport(file)
  if (latestReport) {
    const progress = Number(latestReport.progress)
    if (Number.isFinite(progress)) {
      return clampProgress(progress)
    }
  }
  return 0
}

const getLogFileProgressText = (file: LogFileModel) => `${Math.round(getLogFileProgress(file))}%`

const getLogFileProgressMessage = (file: LogFileModel) => {
  const latestProgress = getLatestProgressReport(file)
  const progressMessage = latestProgress?.message?.trim()
  if (progressMessage) return progressMessage
  const latestMilestone = getLatestLogFileTaskReport(file)
  const milestoneMessage = latestMilestone?.message?.trim()
  if (milestoneMessage) return milestoneMessage
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

const normalizeLogFile = (file: LogFileModel): LogFileModel => {
  const logFileId = file.log_file_id || file.id
  return {
    ...file,
    log_file_id: logFileId,
    anomaly_cnt: logFileAnomalyCntById.value[logFileId] ?? file.anomaly_cnt,
    trace_failure_event_cnt:
      logFileTraceFailureEventCntById.value[logFileId] ?? file.trace_failure_event_cnt,
  }
}

const isSuccessfulLogFileTask = (file: LogFileModel) =>
  ['successful', 'successful_pending_remove'].includes(getLogFileTaskStatus(file))

const isLogFileDetailLoaded = (file: LogFileModel) =>
  loadedAnomalyLogFileIds.value.has(getLogFileId(file))

const getLogFileAnomalyCountText = (file: LogFileModel) => `时延异常数：${file.anomaly_cnt}`

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
  const completedTasks: Record<string, TaskModel> = {}
  files.forEach((file) => {
    if (!file.task?.id) return
    if (isTerminalTaskStatus(file.task.status)) {
      completedTasks[file.task.id] = file.task
      return
    }
    taskIds.add(file.task.id)
  })
  if (Object.keys(completedTasks).length > 0) {
    taskDetailsById.value = {
      ...taskDetailsById.value,
      ...completedTasks,
    }
  }
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

const deletingFileIds = reactive(new Set<string>())

const deleteLogFile = async (logFileId: string) => {
  if (!confirm('确定要删除这个日志文件吗？删除后将无法恢复。')) {
    return
  }

  deletingFileIds.add(logFileId)
  try {
    await request<{ log_file_ids: string[] }>(`/log_file/${logFileId}`, {
      method: 'DELETE',
    })

    // 直接从列表中移除被删除的文件，避免重新加载整个列表
    const index = logFiles.value.findIndex((f) => f.id === logFileId)
    if (index !== -1) {
      logFiles.value.splice(index, 1)
      logFilesTotal.value = Math.max(0, logFilesTotal.value - 1)
    }
  } catch (error) {
    console.error('删除日志文件失败:', error)
    alert('删除失败，请稍后重试')
  } finally {
    deletingFileIds.delete(logFileId)
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
    await request<UploadLogFilesResult>(`/log_file/${selectedAssetId.value}`, {
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
    })
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
  if (!isTimeWindowLoading.value) {
    requests.push(loadTimeWindowAggregatedEvents())
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

    const data = (await response
      .json()
      .catch(() => null)) as ApiResponse<UploadLogFilesResult> | null

    if (!response.ok || !data) {
      throw new Error(data?.message || `请求失败：${response.status}`)
    }

    if (typeof data.code === 'number' && data.code !== 200) {
      throw new Error(data.message || '接口返回异常')
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
  const panel = source?.closest<HTMLElement>('.aggregate-latency-scroll')
  if (!source || !panel) return

  if (panel.closest('.time-window-aggregate-frame')) {
    panel.style.setProperty('--time-window-latency-offset', `${-source.scrollLeft}px`)
  }
  if (panel.closest('.fault-aggregate-event-frame')) {
    panel.style.setProperty('--fault-aggregate-code-offset', `${-source.scrollLeft}px`)
  }

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

watch(selectedLatencyScale, () => {
  if (latencyChartCenterTime.value !== null) {
    void loadLatencyChart()
    void loadAbnormalTraces(1)
    void loadLatencyDetail(1)
    void loadTimeWindowAggregatedEvents(1, latencyChartRange.value)
  } else if ((abnormalTraceRowsMap[selectedLatencyScale.value] ?? []).length === 0) {
    void loadAbnormalTraces(1)
  }
})

watch(selectedLatencyPercentile, () => {
  void loadLatencyChart()
})

watch(selectedFaultScale, (newVal) => {
  if (selectedLatencyScale.value !== newVal) {
    selectedLatencyScale.value = newVal
  }
  if (faultChartCenterTime.value !== null) {
    void loadFaultChart()
    void loadFaultTraceEvents(1)
    void loadFaultAggregatedEvents(1)
  } else if ((faultTraceRowsMap[selectedFaultScale.value] ?? []).length === 0) {
    void loadFaultTraceEvents(1)
  }
})

onMounted(() => {
  void loadAssets()
  window.addEventListener('resize', resizeLatencyCharts)
  document.addEventListener('click', handleStatusCodePopoverOutsideClick)
})

onUpdated(() => {
  syncAbnormalTraceRowHeights()
  syncDetailAbnormalTraceRowHeights()
})

onBeforeUnmount(() => {
  stopLogFilesPolling()
  closeAgentEventStream()
  window.removeEventListener('resize', resizeLatencyCharts)
  document.removeEventListener('click', handleStatusCodePopoverOutsideClick)
  latencyChartInstance?.dispose()
  detailLatencyChartInstance?.dispose()
  faultChartInstance?.dispose()
  faultDetailChartInstance?.dispose()
})
</script>

<template>
  <div class="app-layout">
    <div
      v-if="statusCodePopover.open"
      ref="statusCodePopoverRef"
      class="status-code-popover"
      :style="{ left: `${statusCodePopover.left}px`, top: `${statusCodePopover.top}px` }"
      role="dialog"
      :aria-label="`故障码${statusCodePopover.code}详情`"
    >
      <div class="status-code-popover-header">
        <span class="status-code-capsule">{{ statusCodePopover.code }}</span>
        <button
          class="status-code-popover-close"
          type="button"
          aria-label="关闭"
          @click="closeStatusCodePopover"
        >
          ×
        </button>
      </div>
      <div v-if="statusCodePopover.loading" class="status-code-popover-state">正在加载...</div>
      <div v-else-if="statusCodePopover.error" class="status-code-popover-state error">
        {{ statusCodePopover.error }}
      </div>
      <div v-else class="status-code-popover-content">
        <div class="status-code-detail status-code-detail-symptom">
          <span class="status-code-detail-label">故障现象</span>
          <p>{{ statusCodePopover.symptom || '-' }}</p>
        </div>
        <div class="status-code-detail status-code-detail-cause">
          <span class="status-code-detail-label">故障原因</span>
          <p>{{ statusCodePopover.rootCause || '-' }}</p>
        </div>
      </div>
    </div>
    <div
      v-if="failureModePopover.open"
      ref="failureModePopoverRef"
      class="failure-mode-popover"
      :style="{ left: `${failureModePopover.left}px`, top: `${failureModePopover.top}px` }"
      role="dialog"
      :aria-label="`故障模式详情`"
    >
      <div class="failure-mode-popover-header">
        <span class="failure-mode-popover-title">
          {{ failureModePopover.failureMode?.name || '-' }}
        </span>
        <button
          class="failure-mode-popover-close"
          type="button"
          aria-label="关闭"
          @click="closeFailureModePopover"
        >
          ×
        </button>
      </div>
      <div v-if="failureModePopover.loading" class="failure-mode-popover-state">正在加载...</div>
      <div v-else-if="failureModePopover.error" class="failure-mode-popover-state error">
        {{ failureModePopover.error }}
      </div>
      <div v-else-if="failureModePopover.failureMode" class="failure-mode-popover-content">
        <div class="failure-mode-detail-item">
          <span class="failure-mode-detail-label">故障域</span>
          <p>{{ failureModePopover.failureMode.failure_domain || '-' }}</p>
        </div>
        <div class="failure-mode-detail-item failure-mode-detail-wide">
          <span class="failure-mode-detail-label">故障表现</span>
          <p>{{ failureModePopover.failureMode.symptom || '-' }}</p>
        </div>
        <div class="failure-mode-detail-item failure-mode-detail-wide">
          <span class="failure-mode-detail-label">故障根因</span>
          <p>{{ failureModePopover.failureMode.root_cause || '-' }}</p>
        </div>
        <div class="failure-mode-detail-item failure-mode-detail-wide">
          <span class="failure-mode-detail-label">解决方法</span>
          <p>{{ failureModePopover.failureMode.solution || '-' }}</p>
        </div>
      </div>
    </div>
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
            @click="handleAssetClick(asset.id)"
            @keydown.enter="handleAssetClick(asset.id)"
            @keydown.space.prevent="handleAssetClick(asset.id)"
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
              :class="{ active: pageNum === assetPage, ellipsis: pageNum < 0 }"
              type="button"
              :disabled="pageNum < 0 || pageNum === assetPage || isListLoading"
              @click="pageNum > 0 && goAssetPage(pageNum)"
            >
              {{ pageNum < 0 ? '…' : pageNum }}
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
            📊 时延故障监控
          </button>
          <button
            class="monitor-nav-item"
            :class="{ disabled: !selectedAssetId }"
            type="button"
            :disabled="!selectedAssetId"
            @click="openMonitorPage('fault')"
          >
            ⚠️ 通断故障监控
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
          <div class="filter-section">
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

          <div class="filter-section">
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

          <div class="filter-section">
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
                placeholder="输入主机名或主机 IP"
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

          <div class="filter-section">
            <div class="filter-section-title">
              <span>📦 按Pod IP</span>
              <button
                class="reset-category-btn"
                type="button"
                @click="resetFilterCategory('podIp')"
              >
                重置
              </button>
            </div>
            <div class="filter-entry-row">
              <input
                v-model="filterDraftInput.podIp"
                type="text"
                placeholder="输入 Pod IP"
                @keydown.enter.prevent="addFilterValue('podIp')"
              />
              <button type="button" @click="addFilterValue('podIp')">添加</button>
            </div>
            <div class="selected-tags">
              <span v-for="podIp in globalFilters.podIps" :key="podIp" class="filter-tag">
                {{ podIp }}
                <button type="button" class="remove-tag" @click="removeFilterValue('podIp', podIp)">
                  ×
                </button>
              </span>
              <span v-if="globalFilters.podIps.length === 0" class="empty-hint">
                未选择Pod IP
              </span>
            </div>
          </div>

          <div class="filter-section">
            <div class="filter-section-title">
              <span>📤 按源IP</span>
              <button
                class="reset-category-btn"
                type="button"
                @click="resetFilterCategory('sourcePodIp')"
              >
                重置
              </button>
            </div>
            <div class="filter-entry-row">
              <input
                v-model="filterDraftInput.sourcePodIp"
                type="text"
                placeholder="输入源 IP"
                @keydown.enter.prevent="addFilterValue('sourcePodIp')"
              />
              <button type="button" @click="addFilterValue('sourcePodIp')">添加</button>
            </div>
            <div class="selected-tags">
              <span
                v-for="sourcePodIp in globalFilters.sourcePodIps"
                :key="sourcePodIp"
                class="filter-tag"
              >
                {{ sourcePodIp }}
                <button
                  type="button"
                  class="remove-tag"
                  @click="removeFilterValue('sourcePodIp', sourcePodIp)"
                >
                  ×
                </button>
              </span>
              <span v-if="globalFilters.sourcePodIps.length === 0" class="empty-hint"
                >未选择源IP</span
              >
            </div>
          </div>

          <div class="filter-section">
            <div class="filter-section-title">
              <span>📥 按目标IP</span>
              <button
                class="reset-category-btn"
                type="button"
                @click="resetFilterCategory('targetPodIp')"
              >
                重置
              </button>
            </div>
            <div class="filter-entry-row">
              <input
                v-model="filterDraftInput.targetPodIp"
                type="text"
                placeholder="输入目标 IP"
                @keydown.enter.prevent="addFilterValue('targetPodIp')"
              />
              <button type="button" @click="addFilterValue('targetPodIp')">添加</button>
            </div>
            <div class="selected-tags">
              <span
                v-for="targetPodIp in globalFilters.targetPodIps"
                :key="targetPodIp"
                class="filter-tag"
              >
                {{ targetPodIp }}
                <button
                  type="button"
                  class="remove-tag"
                  @click="removeFilterValue('targetPodIp', targetPodIp)"
                >
                  ×
                </button>
              </span>
              <span v-if="globalFilters.targetPodIps.length === 0" class="empty-hint"
                >未选择目标IP</span
              >
            </div>
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
              <h1>时延故障监控</h1>
              <div class="operation-toggle">
                <button
                  type="button"
                  class="operation-toggle-btn"
                  :class="{ active: selectedOperation === 'get' }"
                  @click="selectedOperation = 'get'"
                >
                  GET
                </button>
                <button
                  type="button"
                  class="operation-toggle-btn"
                  :class="{ active: selectedOperation === 'set' }"
                  @click="selectedOperation = 'set'"
                >
                  SET
                </button>
              </div>
            </div>
            <p class="monitor-sub">支持 11 项时延指标曲线，可交互选择展示</p>
          </header>

          <div class="monitor-grid">
            <article class="monitor-card chart-slot">
              <div class="monitor-card-title">
                <span>📈 关键时延指标趋势</span>
                <span class="danger-chip">{{ latencyAnomalyHint }}</span>
                <div class="chart-title-actions">
                  <button
                    v-if="latencyChartRange"
                    class="chart-reset-btn"
                    type="button"
                    @click="resetLatencyChartRange"
                  >
                    重置
                  </button>
                  <span class="scale-label">时间尺度：</span>
                  <label class="latency-percentile-select">
                    <select v-model="selectedLatencyScale" aria-label="时间尺度">
                      <option
                        v-for="option in latencyScaleOptions"
                        :key="option.value"
                        :value="option.value"
                      >
                        {{ option.label }}
                      </option>
                    </select>
                  </label>
                  <span class="scale-label">百分位指标：</span>
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
                    异常Trace列表
                  </button>
                </div>
                <label v-if="activeAggregateTab === 'event'" class="latency-stat-select">
                  <span>时间间隔</span>
                  <select
                    v-model="selectedLatencyTimeWindowInterval"
                    @change="changeLatencyTimeWindowInterval"
                  >
                    <option value="hour">时</option>
                    <option value="minute">分</option>
                    <option value="second">秒</option>
                  </select>
                </label>
                <div v-else class="abnormal-trace-filter-actions">
                  <form class="trace-id-search" @submit.prevent="submitAbnormalTraceIdQuery">
                    <label class="trace-id-search-field">
                      <span>Trace ID</span>
                      <input
                        v-model="abnormalTraceIdInput"
                        type="text"
                        placeholder="输入 Trace ID"
                        autocomplete="off"
                        :disabled="isAbnormalTracesLoading"
                      />
                    </label>
                    <button
                      class="save-btn compact-action-btn trace-id-search-submit"
                      type="submit"
                      :disabled="isAbnormalTracesLoading"
                    >
                      查询
                    </button>
                  </form>
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
                <template
                  v-if="
                    !isTimeWindowLoading &&
                    !timeWindowError &&
                    timeWindowAggregatedEvents.length > 0
                  "
                >
                  <div class="aggregate-table-frame time-window-aggregate-frame">
                    <div class="aggregate-fixed-left">
                      <div class="aggregate-left-grid aggregate-table-header">
                        <div class="aggregate-cell fault-expand-cell"></div>
                        <div
                          class="aggregate-cell aggregate-sortable-cell"
                          @click="handleTimeWindowStartTimeSort"
                        >
                          <span class="sort-header-content">
                            开始时间
                            <span class="sort-icons">
                              <span
                                class="sort-icon-up"
                                @click.stop="setTimeWindowStartTimeSort('asc')"
                                :class="{
                                  'sort-icon-active':
                                    getTimeWindowSortOrder('start_time') === 'asc',
                                }"
                                >▲</span
                              >
                              <span
                                class="sort-icon-down"
                                @click.stop="setTimeWindowStartTimeSort('desc')"
                                :class="{
                                  'sort-icon-active':
                                    getTimeWindowSortOrder('start_time') === 'desc',
                                }"
                                >▼</span
                              >
                            </span>
                          </span>
                        </div>
                        <div class="aggregate-cell">结束时间</div>
                        <div
                          class="aggregate-cell count-cell aggregate-sortable-cell"
                          @click="handleTimeWindowSort('total_cnt')"
                        >
                          <span class="sort-header-content">
                            结果数
                            <span class="sort-icons">
                              <span
                                class="sort-icon-up"
                                :class="{
                                  'sort-icon-active': getTimeWindowSortOrder('total_cnt') === 'asc',
                                }"
                                >▲</span
                              >
                              <span
                                class="sort-icon-down"
                                :class="{
                                  'sort-icon-active':
                                    getTimeWindowSortOrder('total_cnt') === 'desc',
                                }"
                                >▼</span
                              >
                              <span
                                v-if="getTimeWindowSortPriority('total_cnt')"
                                class="sort-priority-badge"
                              >
                                {{ getTimeWindowSortPriority('total_cnt') }}
                              </span>
                            </span>
                          </span>
                        </div>
                        <div
                          class="aggregate-cell count-cell aggregate-sortable-cell"
                          @click="handleTimeWindowSort('anomaly_cnt')"
                        >
                          <span class="sort-header-content">
                            异常数
                            <span class="sort-icons">
                              <span
                                class="sort-icon-up"
                                :class="{
                                  'sort-icon-active':
                                    getTimeWindowSortOrder('anomaly_cnt') === 'asc',
                                }"
                                >▲</span
                              >
                              <span
                                class="sort-icon-down"
                                :class="{
                                  'sort-icon-active':
                                    getTimeWindowSortOrder('anomaly_cnt') === 'desc',
                                }"
                                >▼</span
                              >
                              <span
                                v-if="getTimeWindowSortPriority('anomaly_cnt')"
                                class="sort-priority-badge"
                              >
                                {{ getTimeWindowSortPriority('anomaly_cnt') }}
                              </span>
                            </span>
                          </span>
                        </div>
                        <div
                          class="aggregate-cell aggregate-sortable-cell"
                          @click="handleTimeWindowSort('total_latency')"
                        >
                          <span class="sort-header-content">
                            总时延
                            <span class="sort-icons">
                              <span
                                class="sort-icon-up"
                                :class="{
                                  'sort-icon-active':
                                    getTimeWindowSortOrder('total_latency') === 'asc',
                                }"
                                >▲</span
                              >
                              <span
                                class="sort-icon-down"
                                :class="{
                                  'sort-icon-active':
                                    getTimeWindowSortOrder('total_latency') === 'desc',
                                }"
                                >▼</span
                              >
                              <span
                                v-if="getTimeWindowSortPriority('total_latency')"
                                class="sort-priority-badge"
                              >
                                {{ getTimeWindowSortPriority('total_latency') }}
                              </span>
                            </span>
                          </span>
                        </div>
                      </div>
                      <template
                        v-if="
                          !isTimeWindowLoading &&
                          !timeWindowError &&
                          timeWindowAggregatedEvents.length > 0
                        "
                      >
                        <template
                          v-for="(twEvent, twIdx) in sortedTimeWindowAggregatedEvents"
                          :key="`tw-${twIdx}`"
                        >
                          <div
                            class="aggregate-left-grid aggregate-body-row expandable-aggregate-row"
                            :class="{
                              expanded: isTimeWindowExpanded(twIdx),
                              'shared-row-hover': hoveredTimeWindowRowIndex === twIdx,
                            }"
                            @click="toggleTimeWindowRow(twIdx)"
                            @mouseenter="hoveredTimeWindowRowIndex = twIdx"
                            @mouseleave="hoveredTimeWindowRowIndex = null"
                          >
                            <div class="aggregate-cell fault-expand-cell">
                              <span class="fault-expand-indicator">
                                {{ isTimeWindowExpanded(twIdx) ? '🔽' : '▶️' }}
                              </span>
                            </div>
                            <div class="aggregate-cell">{{ twEvent.start_time }}</div>
                            <div class="aggregate-cell">{{ twEvent.end_time }}</div>
                            <div class="aggregate-cell count-cell">{{ twEvent.total_cnt }}</div>
                            <div class="aggregate-cell count-cell anomaly-count">
                              {{ twEvent.anomaly_cnt }}
                            </div>
                            <div class="aggregate-cell">
                              <span class="metric-value">
                                {{ formatMetricValue(twEvent.ave_total_latency) }}
                              </span>
                            </div>
                          </div>
                          <template v-if="isTimeWindowExpanded(twIdx)">
                            <div
                              class="aggregate-left-grid aggregate-body-row fault-aggregate-sub-header"
                            >
                              <div class="aggregate-cell fault-expand-cell"></div>
                              <div class="aggregate-cell">源IP</div>
                              <div class="aggregate-cell">目标IP</div>
                              <div
                                class="aggregate-cell count-cell aggregate-sortable-cell"
                                @click.stop="handleIpPairSort('total_cnt')"
                              >
                                <span class="sort-header-content">
                                  结果数
                                  <span class="sort-icons">
                                    <span
                                      class="sort-icon-up"
                                      :class="{
                                        'sort-icon-active':
                                          getTimeWindowIpPairSortOrder('total_cnt') === 'asc',
                                      }"
                                      >▲</span
                                    >
                                    <span
                                      class="sort-icon-down"
                                      :class="{
                                        'sort-icon-active':
                                          getTimeWindowIpPairSortOrder('total_cnt') === 'desc',
                                      }"
                                      >▼</span
                                    >
                                    <span
                                      v-if="getTimeWindowIpPairSortPriority('total_cnt')"
                                      class="sort-priority-badge"
                                    >
                                      {{ getTimeWindowIpPairSortPriority('total_cnt') }}
                                    </span>
                                  </span>
                                </span>
                              </div>
                              <div
                                class="aggregate-cell count-cell aggregate-sortable-cell"
                                @click.stop="handleIpPairSort('anomaly_cnt')"
                              >
                                <span class="sort-header-content">
                                  异常数
                                  <span class="sort-icons">
                                    <span
                                      class="sort-icon-up"
                                      :class="{
                                        'sort-icon-active':
                                          getTimeWindowIpPairSortOrder('anomaly_cnt') === 'asc',
                                      }"
                                      >▲</span
                                    >
                                    <span
                                      class="sort-icon-down"
                                      :class="{
                                        'sort-icon-active':
                                          getTimeWindowIpPairSortOrder('anomaly_cnt') === 'desc',
                                      }"
                                      >▼</span
                                    >
                                    <span
                                      v-if="getTimeWindowIpPairSortPriority('anomaly_cnt')"
                                      class="sort-priority-badge"
                                    >
                                      {{ getTimeWindowIpPairSortPriority('anomaly_cnt') }}
                                    </span>
                                  </span>
                                </span>
                              </div>
                              <div
                                class="aggregate-cell aggregate-sortable-cell"
                                @click.stop="handleIpPairSort('total_latency')"
                              >
                                <span class="sort-header-content">
                                  总时延
                                  <span class="sort-icons">
                                    <span
                                      class="sort-icon-up"
                                      :class="{
                                        'sort-icon-active':
                                          getTimeWindowIpPairSortOrder('total_latency') === 'asc',
                                      }"
                                      >▲</span
                                    >
                                    <span
                                      class="sort-icon-down"
                                      :class="{
                                        'sort-icon-active':
                                          getTimeWindowIpPairSortOrder('total_latency') === 'desc',
                                      }"
                                      >▼</span
                                    >
                                    <span
                                      v-if="getTimeWindowIpPairSortPriority('total_latency')"
                                      class="sort-priority-badge"
                                    >
                                      {{ getTimeWindowIpPairSortPriority('total_latency') }}
                                    </span>
                                  </span>
                                </span>
                              </div>
                            </div>
                            <div
                              v-for="ipPair in getPaginatedIpPairs(twEvent, twIdx)"
                              :key="`${twIdx}-${ipPair.src_ip}-${ipPair.dst_ip}`"
                              class="aggregate-left-grid aggregate-body-row fault-aggregate-sub-row"
                              :class="{
                                'shared-row-hover':
                                  hoveredTimeWindowIpPairKey ===
                                  `${twIdx}:${ipPair.src_ip}:${ipPair.dst_ip}`,
                              }"
                              @mouseenter="
                                hoveredTimeWindowIpPairKey = `${twIdx}:${ipPair.src_ip}:${ipPair.dst_ip}`
                              "
                              @mouseleave="hoveredTimeWindowIpPairKey = ''"
                            >
                              <div class="aggregate-cell fault-expand-cell"></div>
                              <div class="aggregate-cell">{{ ipPair.src_ip || '-' }}</div>
                              <div class="aggregate-cell">{{ ipPair.dst_ip || '-' }}</div>
                              <div class="aggregate-cell count-cell">
                                {{ ipPair.log_parse_result_cnt }}
                              </div>
                              <div class="aggregate-cell count-cell anomaly-count">
                                {{ ipPair.anomaly_log_parse_result_cnt }}
                              </div>
                              <div class="aggregate-cell">
                                <span class="metric-value">
                                  {{ formatMetricValue(ipPair.ave_total_latency) }}
                                </span>
                              </div>
                            </div>
                            <div
                              v-if="getTimeWindowIpPairTotalPages(twEvent) > 1"
                              class="aggregate-left-grid aggregate-body-row fault-aggregate-sub-row ip-pair-pagination-row"
                            >
                              <div class="aggregate-cell ip-pair-pagination" colspan="6">
                                <button
                                  class="page-btn"
                                  :disabled="getTimeWindowIpPairPage(twIdx) <= 1"
                                  @click="
                                    setTimeWindowIpPairPage(
                                      twIdx,
                                      getTimeWindowIpPairPage(twIdx) - 1,
                                    )
                                  "
                                >
                                  &lt;
                                </button>
                                <span class="pagination-pages" aria-label="IP对页码">
                                  <button
                                    v-for="pageNum in getTimeWindowIpPairPageWindow(twIdx, twEvent)"
                                    :key="`${twIdx}-ip-pair-page-${pageNum}`"
                                    class="pagination-page-btn"
                                    :class="{
                                      active: pageNum === getTimeWindowIpPairPage(twIdx),
                                      ellipsis: pageNum < 0,
                                    }"
                                    type="button"
                                    :disabled="
                                      pageNum < 0 || pageNum === getTimeWindowIpPairPage(twIdx)
                                    "
                                    @click="pageNum > 0 && setTimeWindowIpPairPage(twIdx, pageNum)"
                                  >
                                    {{ pageNum < 0 ? '…' : pageNum }}
                                  </button>
                                </span>
                                <button
                                  class="page-btn"
                                  :disabled="
                                    getTimeWindowIpPairPage(twIdx) >=
                                    getTimeWindowIpPairTotalPages(twEvent)
                                  "
                                  @click="
                                    setTimeWindowIpPairPage(
                                      twIdx,
                                      getTimeWindowIpPairPage(twIdx) + 1,
                                    )
                                  "
                                >
                                  &gt;
                                </button>
                              </div>
                            </div>
                          </template>
                        </template>
                      </template>
                    </div>

                    <div
                      class="aggregate-latency-scroll time-window-latency-scroll scroll-section-outline"
                      :class="{
                        'scroll-section-outline-full':
                          !isTimeWindowLoading &&
                          !timeWindowError &&
                          sortedTimeWindowAggregatedEvents.length > 0,
                      }"
                    >
                      <div class="aggregate-latency-head aggregate-latency-sync">
                        <div class="aggregate-latency-grid aggregate-table-header"
                          :style="{ gridTemplateColumns: getTimeWindowGridColumnWidths(), minWidth: getTimeWindowTotalWidth() + 'px' }">
                          <div
                            v-for="column in timeWindowLatencyColumns"
                            :key="column.key"
                            class="aggregate-cell aggregate-sortable-cell"
                            @click="handleTimeWindowSort(column.key)"
                          >
                            <span class="sort-header-content">
                              {{ column.label }}
                              <span class="sort-icons">
                                <span
                                  class="sort-icon-up"
                                  :class="{
                                    'sort-icon-active':
                                      getTimeWindowSortOrder(column.key) === 'asc',
                                  }"
                                  >▲</span
                                >
                                <span
                                  class="sort-icon-down"
                                  :class="{
                                    'sort-icon-active':
                                      getTimeWindowSortOrder(column.key) === 'desc',
                                  }"
                                  >▼</span
                                >
                                <span
                                  v-if="getTimeWindowSortPriority(column.key)"
                                  class="sort-priority-badge"
                                >
                                  {{ getTimeWindowSortPriority(column.key) }}
                                </span>
                              </span>
                            </span>
                          </div>
                        </div>
                      </div>
                      <div
                        class="aggregate-latency-scrollbar aggregate-latency-sync"
                        @scroll="syncAggregateLatencyScroll"
                      >
                        <div
                          class="aggregate-latency-scrollbar-spacer"
                          :style="{ minWidth: getTimeWindowTotalWidth() + 'px' }"
                        ></div>
                      </div>
                      <div
                        class="aggregate-latency-body aggregate-latency-sync"
                        @scroll="syncAggregateLatencyScroll"
                      >
                        <template
                          v-if="
                            !isTimeWindowLoading &&
                            !timeWindowError &&
                            timeWindowAggregatedEvents.length > 0
                          "
                        >
                          <template
                            v-for="(twEvent, twIdx) in sortedTimeWindowAggregatedEvents"
                            :key="`tw-body-${twIdx}`"
                          >
                            <div
                              class="aggregate-latency-grid aggregate-body-row expandable-aggregate-row"
                              :class="{
                                expanded: isTimeWindowExpanded(twIdx),
                                'shared-row-hover': hoveredTimeWindowRowIndex === twIdx,
                              }"
                              @click="toggleTimeWindowRow(twIdx)"
                              @mouseenter="hoveredTimeWindowRowIndex = twIdx"
                              @mouseleave="hoveredTimeWindowRowIndex = null"
                              :style="{ gridTemplateColumns: getTimeWindowGridColumnWidths(), minWidth: getTimeWindowTotalWidth() + 'px' }"
                            >
                              <div
                                v-for="column in timeWindowLatencyColumns"
                                :key="column.key"
                                class="aggregate-cell"
                              >
                                <span class="metric-value">
                                  {{
                                    formatMetricValue(
                                      getTimeWindowSummaryValue(twEvent, column.key),
                                    )
                                  }}
                                </span>
                              </div>
                            </div>
                            <template v-if="isTimeWindowExpanded(twIdx)">
                              <div
                                class="aggregate-latency-grid aggregate-body-row fault-aggregate-sub-header"
                                :style="{ gridTemplateColumns: getTimeWindowGridColumnWidths(), minWidth: getTimeWindowTotalWidth() + 'px' }"
                              >
                                <div
                                  v-for="column in timeWindowLatencyColumns"
                                  :key="column.key"
                                  class="aggregate-cell aggregate-sortable-cell"
                                  @click.stop="handleIpPairSort(column.key)"
                                >
                                  <span class="sort-header-content">
                                    {{ column.label }}
                                    <span class="sort-icons">
                                      <span
                                        class="sort-icon-up"
                                        :class="{
                                          'sort-icon-active':
                                            getTimeWindowIpPairSortOrder(column.key) === 'asc',
                                        }"
                                        >▲</span
                                      >
                                      <span
                                        class="sort-icon-down"
                                        :class="{
                                          'sort-icon-active':
                                            getTimeWindowIpPairSortOrder(column.key) === 'desc',
                                        }"
                                        >▼</span
                                      >
                                      <span
                                        v-if="getTimeWindowIpPairSortPriority(column.key)"
                                        class="sort-priority-badge"
                                      >
                                        {{ getTimeWindowIpPairSortPriority(column.key) }}
                                      </span>
                                    </span>
                                  </span>
                                </div>
                              </div>
                              <div
                                v-for="ipPair in getPaginatedIpPairs(twEvent, twIdx)"
                                :key="`${twIdx}-body-${ipPair.src_ip}-${ipPair.dst_ip}`"
                                class="aggregate-latency-grid aggregate-body-row fault-aggregate-sub-row"
                                :class="{
                                  'shared-row-hover':
                                    hoveredTimeWindowIpPairKey ===
                                    `${twIdx}:${ipPair.src_ip}:${ipPair.dst_ip}`,
                                }"
                                @mouseenter="
                                  hoveredTimeWindowIpPairKey = `${twIdx}:${ipPair.src_ip}:${ipPair.dst_ip}`
                                "
                                @mouseleave="hoveredTimeWindowIpPairKey = ''"
                                :style="{ gridTemplateColumns: getTimeWindowGridColumnWidths(), minWidth: getTimeWindowTotalWidth() + 'px' }"
                              >
                                <div
                                  v-for="column in timeWindowLatencyColumns"
                                  :key="column.key"
                                  class="aggregate-cell"
                                >
                                  <span
                                    class="metric-value"
                                    :class="{
                                      abnormal: isLatencyMetricAbnormal(
                                        column.key,
                                        getTimeWindowAggregatedLatencyValue(ipPair, column.key),
                                      ),
                                    }"
                                  >
                                    {{
                                      formatMetricValue(
                                        getTimeWindowAggregatedLatencyValue(ipPair, column.key),
                                      )
                                    }}
                                  </span>
                                </div>
                              </div>
                              <div
                                v-if="getTimeWindowIpPairTotalPages(twEvent) > 1"
                                class="aggregate-latency-grid aggregate-body-row fault-aggregate-sub-row ip-pair-pagination-row"
                                :style="{ gridTemplateColumns: getTimeWindowGridColumnWidths(), minWidth: getTimeWindowTotalWidth() + 'px' }"
                              >
                                <div
                                  v-for="column in timeWindowLatencyColumns"
                                  :key="column.key"
                                  class="aggregate-cell"
                                ></div>
                              </div>
                            </template>
                          </template>
                        </template>
                      </div>
                    </div>

                    <div class="aggregate-fixed-actions">
                      <div class="aggregate-cell action-cell aggregate-table-header">
                        聚合事件分析
                      </div>
                      <template
                        v-if="
                          !isTimeWindowLoading &&
                          !timeWindowError &&
                          timeWindowAggregatedEvents.length > 0
                        "
                      >
                        <template
                          v-for="(twEvent, twIdx) in sortedTimeWindowAggregatedEvents"
                          :key="`tw-action-${twIdx}`"
                        >
                          <div
                            class="aggregate-cell action-cell trace-actions aggregate-body-row expandable-aggregate-row"
                            :class="{
                              expanded: isTimeWindowExpanded(twIdx),
                              'shared-row-hover': hoveredTimeWindowRowIndex === twIdx,
                            }"
                            @click="toggleTimeWindowRow(twIdx)"
                            @mouseenter="hoveredTimeWindowRowIndex = twIdx"
                            @mouseleave="hoveredTimeWindowRowIndex = null"
                          >
                            <span class="metric-action-hint">展开查看IP对</span>
                          </div>
                          <template v-if="isTimeWindowExpanded(twIdx)">
                            <div
                              class="aggregate-cell action-cell trace-actions aggregate-body-row fault-aggregate-sub-header"
                            >
                              <span class="metric-action-hint">操作</span>
                            </div>
                            <div
                              v-for="ipPair in getPaginatedIpPairs(twEvent, twIdx)"
                              :key="`${twIdx}-action-${ipPair.src_ip}-${ipPair.dst_ip}`"
                              class="aggregate-cell action-cell trace-actions aggregate-body-row fault-aggregate-sub-row"
                              :class="{
                                'shared-row-hover':
                                  hoveredTimeWindowIpPairKey ===
                                  `${twIdx}:${ipPair.src_ip}:${ipPair.dst_ip}`,
                              }"
                              @mouseenter="
                                hoveredTimeWindowIpPairKey = `${twIdx}:${ipPair.src_ip}:${ipPair.dst_ip}`
                              "
                              @mouseleave="hoveredTimeWindowIpPairKey = ''"
                            >
                              <button
                                class="metric-action-btn detail-action-btn"
                                type="button"
                                @click.stop="openTimeWindowIpPairDetail(ipPair, twEvent)"
                              >
                                📄详情
                              </button>
                              <button
                                class="metric-action-btn"
                                type="button"
                                @click.stop="openTimeWindowIpPairFilter(ipPair)"
                              >
                                ➕筛选
                              </button>
                            </div>
                            <div
                              v-if="getTimeWindowIpPairTotalPages(twEvent) > 1"
                              class="aggregate-cell action-cell trace-actions aggregate-body-row fault-aggregate-sub-row ip-pair-pagination-row"
                            >
                              <span class="metric-action-hint"></span>
                            </div>
                          </template>
                        </template>
                      </template>
                    </div>
                  </div>
                  <div v-if="timeWindowTotal > 0" class="aggregate-pagination">
                    <button
                      class="ghost-btn"
                      type="button"
                      :disabled="timeWindowPage <= 1 || isTimeWindowLoading"
                      @click="goTimeWindowPage(timeWindowPage - 1)"
                    >
                      上一页
                    </button>
                    <span class="pagination-pages" aria-label="时间窗口聚合事件页码">
                      <button
                        v-for="pageNum in timeWindowPageWindow"
                        :key="`tw-page-${pageNum}`"
                        class="pagination-page-btn"
                        :class="{ active: pageNum === timeWindowPage, ellipsis: pageNum < 0 }"
                        type="button"
                        :disabled="pageNum < 0 || pageNum === timeWindowPage || isTimeWindowLoading"
                        @click="pageNum > 0 && goTimeWindowPage(pageNum)"
                      >
                        {{ pageNum < 0 ? '…' : pageNum }}
                      </button>
                    </span>
                    <button
                      class="ghost-btn"
                      type="button"
                      :disabled="timeWindowPage >= timeWindowPageCount || isTimeWindowLoading"
                      @click="goTimeWindowPage(timeWindowPage + 1)"
                    >
                      下一页
                    </button>
                    <span class="pagination-jump">
                      <span>第 {{ timeWindowPage }} / {{ timeWindowPageCount }} 页</span>
                      <input
                        v-model="timeWindowPageInput"
                        class="pagination-jump-input"
                        type="number"
                        min="1"
                        :max="timeWindowPageCount"
                        aria-label="跳转时间窗口聚合事件页码"
                        @keyup.enter="jumpTimeWindowPage"
                      />
                      <button
                        class="pagination-jump-btn"
                        type="button"
                        :disabled="isTimeWindowLoading"
                        @click="jumpTimeWindowPage"
                      >
                        跳转
                      </button>
                    </span>
                  </div>
                </template>

                <div v-if="isTimeWindowLoading" class="aggregate-table-state">
                  正在加载时间窗口聚合...
                </div>
                <div v-else-if="timeWindowError" class="aggregate-table-state metric-table-error">
                  {{ timeWindowError }}
                </div>
                <div
                  v-else-if="timeWindowAggregatedEvents.length === 0"
                  class="aggregate-table-state"
                >
                  暂无时间窗口聚合数据
                </div>
              </div>

              <div
                v-else-if="activeAggregateTab === 'trace'"
                class="aggregate-table"
                :class="{
                  'aggregate-table-state-mode':
                    isAbnormalTracesLoading ||
                    !!abnormalTracesError ||
                    abnormalTraceRows.length === 0 ||
                    getFilteredAbnormalTraceRows().length === 0,
                }"
              >
                <div ref="latencyTraceTableRef" class="aggregate-table-frame abnormal-trace-frame">
                  <div class="aggregate-fixed-left">
                    <div
                      class="abnormal-left-grid latency-anomaly-left-grid aggregate-table-header"
                      :style="{ gridTemplateColumns: getLatencyLeftGridColumnWidths() }"
                    >
                      <div class="aggregate-cell column-resizable">
                        故障类型
                        <div
                          class="column-resize-handle"
                          @mousedown="(e) => handleColumnResizeStart(e, 'latencyLeft', 0)"
                        ></div>
                      </div>
                      <div class="aggregate-cell column-resizable">
                        时间
                        <div
                          class="column-resize-handle"
                          @mousedown="(e) => handleColumnResizeStart(e, 'latencyLeft', 1)"
                        ></div>
                      </div>
                      <div class="aggregate-cell column-resizable">
                        Trace ID
                        <div
                          class="column-resize-handle"
                          @mousedown="(e) => handleColumnResizeStart(e, 'latencyLeft', 2)"
                        ></div>
                      </div>
                      <div class="aggregate-cell column-resizable">
                        Pod IP
                        <div
                          class="column-resize-handle"
                          @mousedown="(e) => handleColumnResizeStart(e, 'latencyLeft', 3)"
                        ></div>
                      </div>
                      <div class="aggregate-cell column-resizable">
                        操作类型
                        <div
                          class="column-resize-handle"
                          @mousedown="(e) => handleColumnResizeStart(e, 'latencyLeft', 4)"
                        ></div>
                      </div>
                      <div class="aggregate-cell column-resizable">
                        集群
                        <div
                          class="column-resize-handle"
                          @mousedown="(e) => handleColumnResizeStart(e, 'latencyLeft', 5)"
                        ></div>
                      </div>
                      <div class="aggregate-cell">主机</div>
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
                        :class="{
                          'shared-row-hover':
                            hoveredLatencyTraceRowKey === `${row.id}:${row.traceId}`,
                        }"
                        :style="{
                          gridTemplateColumns: getLatencyLeftGridColumnWidths(),
                          height: getTraceRowHeight(row.podIp),
                        }"
                        @mouseenter="hoveredLatencyTraceRowKey = `${row.id}:${row.traceId}`"
                        @mouseleave="hoveredLatencyTraceRowKey = ''"
                      >
                        <div class="aggregate-cell">
                          <span
                            v-for="tag in getTraceTags(row.traceId, 'latency')"
                            :key="tag.type"
                            class="trace-type-tag"
                            :class="`trace-type-tag-${tag.type}`"
                          >
                            {{ tag.label }}
                          </span>
                        </div>
                        <div class="aggregate-cell">{{ row.time }}</div>
                        <div class="aggregate-cell trace-id">{{ row.traceId }}</div>
                        <div class="aggregate-cell multi-line-pod-cell" v-html="row.podIp"></div>
                        <div class="aggregate-cell">{{ row.operation }}</div>
                        <div class="aggregate-cell">{{ row.clusterName }}</div>
                        <div class="aggregate-cell">{{ row.host }}</div>
                      </div>
                    </template>
                  </div>

                  <div
                    class="aggregate-latency-scroll scroll-section-outline"
                    :class="{
                      'scroll-section-outline-full':
                        !isAbnormalTracesLoading &&
                        !abnormalTracesError &&
                        getFilteredAbnormalTraceRows().length > 0,
                    }"
                  >
                    <div class="aggregate-latency-head aggregate-latency-sync">
                      <div
                        class="abnormal-latency-grid aggregate-table-header"
                        :style="{ gridTemplateColumns: getLatencyDataGridColumnWidths(), minWidth: getLatencyDataTotalWidth() + 'px' }"
                      >
                        <div
                          class="aggregate-cell aggregate-sortable-cell column-resizable"
                          @click="abnormalTraceSort.handleHeaderClick('total_latency')"
                        >
                          <span class="sort-header-content">
                            总时延
                            <span class="sort-icons">
                              <span
                                class="sort-icon-up"
                                :class="{
                                  'sort-icon-active':
                                    abnormalTraceSort.getSortOrder('total_latency') === 'asc',
                                }"
                                >▲</span
                              >
                              <span
                                class="sort-icon-down"
                                :class="{
                                  'sort-icon-active':
                                    abnormalTraceSort.getSortOrder('total_latency') === 'desc',
                                }"
                                >▼</span
                              >
                            </span>
                          </span>
                          <div
                            class="column-resize-handle"
                            @mousedown.stop="(e) => handleColumnResizeStart(e, 'latencyData', 0)"
                          ></div>
                        </div>
                        <div
                          v-for="(col, index) in getLatencyDataColumns.slice(1)"
                          :key="col.key"
                          class="aggregate-cell aggregate-sortable-cell column-resizable"
                          @click="abnormalTraceSort.handleHeaderClick(col.key)"
                        >
                          <span class="sort-header-content">
                            {{ col.label.replace(' (ms)', '') }}
                            <span class="sort-icons">
                              <span
                                class="sort-icon-up"
                                :class="{
                                  'sort-icon-active':
                                    abnormalTraceSort.getSortOrder(col.key) === 'asc',
                                }"
                                >▲</span
                              >
                              <span
                                class="sort-icon-down"
                                :class="{
                                  'sort-icon-active':
                                    abnormalTraceSort.getSortOrder(col.key) === 'desc',
                                }"
                                >▼</span
                              >
                            </span>
                          </span>
                          <div
                            class="column-resize-handle"
                            @mousedown.stop="(e) => handleColumnResizeStart(e, 'latencyData', index + 1)"
                          ></div>
                        </div>
                      </div>
                    </div>
                    <div
                      class="aggregate-latency-scrollbar aggregate-latency-sync"
                      @scroll="syncAggregateLatencyScroll"
                    >
                      <div
                        class="aggregate-latency-scrollbar-spacer"
                        :style="{ minWidth: getLatencyDataTotalWidth() + 'px' }"
                      ></div>
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
                          :class="{
                            'shared-row-hover':
                              hoveredLatencyTraceRowKey === `${row.id}:${row.traceId}`,
                          }"
                          :style="{
                            gridTemplateColumns: getLatencyDataGridColumnWidths(),
                            height: getTraceRowHeight(row.podIp),
                          }"
                          @mouseenter="hoveredLatencyTraceRowKey = `${row.id}:${row.traceId}`"
                          @mouseleave="hoveredLatencyTraceRowKey = ''"
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
                          <div
                          v-for="col in getLatencyDataColumns.slice(1)"
                          :key="col.key"
                          class="aggregate-cell"
                        >
                          <span
                            class="metric-value"
                            :class="{
                              abnormal: isAnomalyListLatencyMetricAbnormal(
                                row,
                                col.key,
                                getLatencyRowValue(row as any, col.key),
                              ),
                            }"
                          >
                            {{ formatNullableMetricValue(getLatencyRowValue(row as any, col.key)) }}
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
                        :class="{
                          'shared-row-hover':
                            hoveredLatencyTraceRowKey === `${row.id}:${row.traceId}`,
                        }"
                        :style="{ height: getTraceRowHeight(row.podIp) }"
                        @mouseenter="hoveredLatencyTraceRowKey = `${row.id}:${row.traceId}`"
                        @mouseleave="hoveredLatencyTraceRowKey = ''"
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
                <div v-if="abnormalTracesTotal > 0" class="aggregate-pagination">
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
                      :class="{ active: pageNum === abnormalTracesPage, ellipsis: pageNum < 0 }"
                      type="button"
                      :disabled="
                        pageNum < 0 || pageNum === abnormalTracesPage || isAbnormalTracesLoading
                      "
                      @click="pageNum > 0 && goAbnormalTracesPage(pageNum)"
                    >
                      {{ pageNum < 0 ? '…' : pageNum }}
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
              <h1>通断故障监控</h1>
              <div class="operation-toggle">
                <button
                  type="button"
                  class="operation-toggle-btn"
                  :class="{ active: selectedFaultOperation === 'get' }"
                  @click="selectedFaultOperation = 'get'"
                >
                  GET
                </button>
                <button
                  type="button"
                  class="operation-toggle-btn"
                  :class="{ active: selectedFaultOperation === 'set' }"
                  @click="selectedFaultOperation = 'set'"
                >
                  SET
                </button>
              </div>
            </div>
            <p class="monitor-sub">故障码 / 故障名称 / 故障域</p>
          </header>

          <div class="monitor-grid">
            <article class="monitor-card chart-slot">
              <div class="monitor-card-title">
                <span>📈 故障码计数时序分布</span>
                <div class="chart-title-actions">
                  <button
                    v-if="faultChartRange"
                    class="chart-reset-btn"
                    type="button"
                    @click="resetFaultChartRange"
                  >
                    重置
                  </button>
                  <span class="scale-label">时间尺度：</span>
                  <label class="latency-percentile-select">
                    <select v-model="selectedFaultScale" aria-label="故障时间尺度">
                      <option
                        v-for="option in latencyScaleOptions"
                        :key="option.value"
                        :value="option.value"
                      >
                        {{ option.label }}
                      </option>
                    </select>
                  </label>
                </div>
              </div>
              <div class="latency-chart-panel">
                <div v-if="isFaultChartLoading" class="chart-state">
                  正在加载故障码计数时序分布...
                </div>
                <div v-else-if="faultChartError" class="chart-state chart-error">
                  {{ faultChartError }}
                </div>
                <div v-else-if="!hasFaultChartMetricData" class="chart-state">
                  暂无故障码计数时序数据
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
                    异常Trace列表
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
                <div v-else class="abnormal-trace-filter-actions">
                  <form class="trace-id-search" @submit.prevent="submitFaultTraceIdQuery">
                    <label class="trace-id-search-field">
                      <span>Trace ID</span>
                      <input
                        v-model="faultTraceIdInput"
                        type="text"
                        placeholder="输入 Trace ID"
                        autocomplete="off"
                        :disabled="isFaultTraceEventsLoading"
                      />
                    </label>
                    <button
                      class="save-btn compact-action-btn trace-id-search-submit"
                      type="submit"
                      :disabled="isFaultTraceEventsLoading"
                    >
                      查询
                    </button>
                  </form>
                </div>
              </div>

              <div
                v-if="activeFaultMonitorTab === 'event'"
                class="aggregate-table"
                :class="{
                  'aggregate-table-state-mode':
                    isFaultAggregatedEventsLoading ||
                    !!faultAggregatedEventsError ||
                    faultAggregatedEventRows.length === 0,
                }"
              >
                <template
                  v-if="
                    !isFaultAggregatedEventsLoading &&
                    !faultAggregatedEventsError &&
                    faultAggregatedEventRows.length > 0
                  "
                >
                  <div class="aggregate-table-frame fault-aggregate-event-frame">
                    <div class="aggregate-fixed-left">
                      <div class="fault-aggregate-time-grid aggregate-table-header">
                        <div class="aggregate-cell fault-expand-cell"></div>
                        <div
                          class="aggregate-cell aggregate-sortable-cell"
                          @click="handleFaultAggregatedEventStartTimeSort"
                        >
                          <span class="sort-header-content">
                            开始时间
                            <span class="sort-icons">
                              <span
                                class="sort-icon-up"
                                @click.stop="setFaultAggregatedEventStartTimeSort(false)"
                                :class="{
                                  'sort-icon-active':
                                    isFaultAggregatedEventStartTimeSortActive &&
                                    !faultAggregatedEventSortDesc,
                                }"
                              >
                                ▲
                              </span>
                              <span
                                class="sort-icon-down"
                                @click.stop="setFaultAggregatedEventStartTimeSort(true)"
                                :class="{
                                  'sort-icon-active':
                                    isFaultAggregatedEventStartTimeSortActive &&
                                    faultAggregatedEventSortDesc,
                                }"
                              >
                                ▼
                              </span>
                            </span>
                          </span>
                        </div>
                        <div class="aggregate-cell">结束时间</div>
                      </div>
                      <template
                        v-if="
                          !isFaultAggregatedEventsLoading &&
                          !faultAggregatedEventsError &&
                          paginatedFaultAggregatedEventRows.length > 0
                        "
                      >
                        <template
                          v-for="row in paginatedFaultAggregatedEventRows"
                          :key="`${row.id}-time`"
                        >
                          <div
                            class="fault-aggregate-time-grid aggregate-body-row fault-aggregate-main-row"
                            :class="{
                              expanded: isFaultAggregatedEventExpanded(row),
                              'shared-row-hover': hoveredFaultAggregatedEventId === row.id,
                            }"
                            @click="toggleFaultAggregatedEventRow(row)"
                            @mouseenter="hoveredFaultAggregatedEventId = row.id"
                            @mouseleave="hoveredFaultAggregatedEventId = ''"
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
                              <div class="aggregate-cell fault-aggregate-sub-pod-head">
                                <div class="fault-aggregate-ip-columns">
                                  <div class="fault-aggregate-ip-column">源IP</div>
                                  <div class="fault-aggregate-ip-column">目标IP</div>
                                </div>
                              </div>
                              <template
                                v-if="
                                  isFaultAggregatedEventPodLoading(row) &&
                                  getFaultAggregatedEventPodRows(row).length === 0
                                "
                              >
                                <div class="aggregate-cell fault-expand-cell"></div>
                                <div class="aggregate-cell fault-aggregate-sub-pod-cell">
                                  <div class="fault-aggregate-ip-columns">
                                    <div class="fault-aggregate-ip-column">加载中...</div>
                                    <div class="fault-aggregate-ip-column">加载中...</div>
                                  </div>
                                </div>
                              </template>
                              <template
                                v-else-if="getFaultAggregatedEventPodRows(row).length === 0"
                              >
                                <div class="aggregate-cell fault-expand-cell"></div>
                                <div class="aggregate-cell fault-aggregate-sub-pod-cell">
                                  <div class="fault-aggregate-ip-columns">
                                    <div class="fault-aggregate-ip-column">
                                      {{ getFaultAggregatedEventPodError(row) || '暂无数据' }}
                                    </div>
                                    <div class="fault-aggregate-ip-column">
                                      {{ getFaultAggregatedEventPodError(row) || '暂无数据' }}
                                    </div>
                                  </div>
                                </div>
                              </template>
                              <template
                                v-for="podRow in getFaultAggregatedEventPodRows(row)"
                                :key="`${podRow.id}-srcdst-ip`"
                              >
                                <div
                                  class="aggregate-cell fault-expand-cell"
                                  :class="{
                                    'shared-row-hover':
                                      hoveredFaultAggregatedPodRowKey === `${row.id}:${podRow.id}`,
                                  }"
                                  @mouseenter="
                                    hoveredFaultAggregatedPodRowKey = `${row.id}:${podRow.id}`
                                  "
                                  @mouseleave="hoveredFaultAggregatedPodRowKey = ''"
                                ></div>
                                <div
                                  class="aggregate-cell fault-aggregate-sub-pod-cell"
                                  :class="{
                                    'shared-row-hover':
                                      hoveredFaultAggregatedPodRowKey === `${row.id}:${podRow.id}`,
                                  }"
                                  @mouseenter="
                                    hoveredFaultAggregatedPodRowKey = `${row.id}:${podRow.id}`
                                  "
                                  @mouseleave="hoveredFaultAggregatedPodRowKey = ''"
                                >
                                  <div class="fault-aggregate-ip-columns">
                                    <div class="fault-aggregate-ip-column">{{ podRow.srcIp }}</div>
                                    <div class="fault-aggregate-ip-column">{{ podRow.dstIp }}</div>
                                  </div>
                                </div>
                              </template>
                              <div
                                v-if="getFaultAggregatedEventPodTotal(row) > 0"
                                class="fault-aggregate-sub-pagination fault-aggregate-sub-pagination-side ip-pair-pagination"
                              >
                                <button
                                  class="page-btn"
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
                                  &lt;
                                </button>
                                <span class="pagination-pages" aria-label="故障聚合事件Pod副表页码">
                                  <button
                                    v-for="pageNum in getFaultAggregatedEventPodPageWindow(row)"
                                    :key="`${row.id}-fixed-pod-page-${pageNum}`"
                                    class="pagination-page-btn"
                                    :class="{
                                      active: pageNum === getFaultAggregatedEventPodPage(row),
                                      ellipsis: pageNum < 0,
                                    }"
                                    type="button"
                                    :disabled="
                                      pageNum < 0 ||
                                      pageNum === getFaultAggregatedEventPodPage(row) ||
                                      isFaultAggregatedEventPodLoading(row)
                                    "
                                    @click.stop="
                                      pageNum > 0 && goFaultAggregatedEventPodPage(row, pageNum)
                                    "
                                  >
                                    {{ pageNum < 0 ? '…' : pageNum }}
                                  </button>
                                </span>
                                <button
                                  class="page-btn"
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
                                  &gt;
                                </button>
                              </div>
                            </div>
                          </div>
                        </template>
                      </template>
                    </div>

                    <div
                      class="aggregate-latency-scroll fault-code-scroll scroll-section-outline"
                      :class="{
                        'scroll-section-outline-full':
                          !isFaultAggregatedEventsLoading &&
                          !faultAggregatedEventsError &&
                          paginatedFaultAggregatedEventRows.length > 0,
                      }"
                    >
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
                              :class="{ 'fault-total-code-header': code === 'all' }"
                              @click.stop="faultAggregatedEventSort.handleHeaderClick(code)"
                            >
                              <span class="sort-header-content">
                                <button
                                  v-if="code !== 'all'"
                                  class="fault-code-knowledge-link"
                                  type="button"
                                  @click.stop="openStatusCodePopover(code, $event)"
                                >
                                  {{ getFaultAggregatedEventCodeLabel(code) }}
                                </button>
                                <strong v-else class="fault-total-code-label">
                                  {{ getFaultAggregatedEventCodeLabel(code) }}
                                </strong>
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
                                  <span
                                    v-if="getFaultAggregatedEventSortPriority(code)"
                                    class="sort-priority-badge"
                                  >
                                    {{ getFaultAggregatedEventSortPriority(code) }}
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
                        <template
                          v-if="
                            !isFaultAggregatedEventsLoading &&
                            !faultAggregatedEventsError &&
                            paginatedFaultAggregatedEventRows.length > 0
                          "
                        >
                          <template
                            v-for="row in paginatedFaultAggregatedEventRows"
                            :key="`${row.id}-fault-codes`"
                          >
                            <div
                              class="fault-code-grid aggregate-body-row fault-aggregate-main-row"
                              :class="{
                                expanded: isFaultAggregatedEventExpanded(row),
                                'shared-row-hover': hoveredFaultAggregatedEventId === row.id,
                              }"
                              :style="faultAggregatedEventCodeGridStyle"
                              @click="toggleFaultAggregatedEventRow(row)"
                              @mouseenter="hoveredFaultAggregatedEventId = row.id"
                              @mouseleave="hoveredFaultAggregatedEventId = ''"
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
                                  @click.stop="
                                    handleFaultAggregatedEventPodSortHeaderClick(row, code)
                                  "
                                >
                                  <span class="sort-header-content">
                                    <button
                                      v-if="code !== 'all'"
                                      class="fault-code-knowledge-link"
                                      type="button"
                                      @click.stop="openStatusCodePopover(code, $event)"
                                    >
                                      {{ getFaultAggregatedEventCodeLabel(code) }}
                                    </button>
                                    <span v-else>{{ getFaultAggregatedEventCodeLabel(code) }}</span>
                                    <span class="sort-icons">
                                      <span
                                        class="sort-icon-up"
                                        :class="{
                                          'sort-icon-active':
                                            faultAggregatedEventPodSort.getSortOrder(code) ===
                                            'asc',
                                        }"
                                      >
                                        ▲
                                      </span>
                                      <span
                                        class="sort-icon-down"
                                        :class="{
                                          'sort-icon-active':
                                            faultAggregatedEventPodSort.getSortOrder(code) ===
                                            'desc',
                                        }"
                                      >
                                        ▼
                                      </span>
                                      <span
                                        v-if="getFaultAggregatedEventPodSortPriority(code)"
                                        class="sort-priority-badge"
                                      >
                                        {{ getFaultAggregatedEventPodSortPriority(code) }}
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
                                  :style="{
                                    gridColumn: `span ${Math.max(1, faultAggregatedEventCodes.length)}`,
                                  }"
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
                                  :style="{
                                    gridColumn: `span ${Math.max(1, faultAggregatedEventCodes.length)}`,
                                  }"
                                >
                                  {{ getFaultAggregatedEventPodError(row) || '暂无Pod聚合数据' }}
                                </div>
                              </div>
                              <div
                                v-for="podRow in getFaultAggregatedEventPodRows(row)"
                                :key="`${podRow.id}-fault-codes`"
                                class="fault-code-grid aggregate-body-row fault-aggregate-sub-code-grid"
                                :class="{
                                  'shared-row-hover':
                                    hoveredFaultAggregatedPodRowKey === `${row.id}:${podRow.id}`,
                                }"
                                :style="faultAggregatedEventCodeGridStyle"
                                @mouseenter="
                                  hoveredFaultAggregatedPodRowKey = `${row.id}:${podRow.id}`
                                "
                                @mouseleave="hoveredFaultAggregatedPodRowKey = ''"
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
                                v-if="getFaultAggregatedEventPodTotal(row) > 0"
                                class="fault-aggregate-sub-pagination ip-pair-pagination"
                              ></div>
                            </div>
                          </template>
                        </template>
                      </div>
                    </div>

                    <div class="aggregate-fixed-actions">
                      <div class="aggregate-cell action-cell aggregate-table-header">
                        聚合事件分析
                      </div>
                      <template
                        v-if="
                          !isFaultAggregatedEventsLoading &&
                          !faultAggregatedEventsError &&
                          paginatedFaultAggregatedEventRows.length > 0
                        "
                      >
                        <template
                          v-for="row in paginatedFaultAggregatedEventRows"
                          :key="`${row.id}-action`"
                        >
                          <div
                            class="aggregate-cell action-cell trace-actions aggregate-body-row fault-aggregate-main-row"
                            :class="{
                              expanded: isFaultAggregatedEventExpanded(row),
                              'shared-row-hover': hoveredFaultAggregatedEventId === row.id,
                            }"
                            @click="toggleFaultAggregatedEventRow(row)"
                            @mouseenter="hoveredFaultAggregatedEventId = row.id"
                            @mouseleave="hoveredFaultAggregatedEventId = ''"
                          >
                            <span class="metric-action-hint">展开查看Pod IP</span>
                          </div>
                          <div
                            v-if="isFaultAggregatedEventExpanded(row)"
                            class="aggregate-cell action-cell aggregate-body-row fault-aggregate-sub-row fault-aggregate-sub-action"
                          >
                            <div class="fault-aggregate-sub-action-head">
                              <span class="metric-action-hint">操作</span>
                            </div>
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
                              :class="{
                                'shared-row-hover':
                                  hoveredFaultAggregatedPodRowKey === `${row.id}:${podRow.id}`,
                              }"
                              @mouseenter="
                                hoveredFaultAggregatedPodRowKey = `${row.id}:${podRow.id}`
                              "
                              @mouseleave="hoveredFaultAggregatedPodRowKey = ''"
                            >
                              <button
                                class="metric-action-btn detail-action-btn"
                                type="button"
                                @click.stop="openFaultAggregatedEventDetail(row, podRow)"
                              >
                                📄详情
                              </button>
                              <button
                                class="metric-action-btn filter-action-btn"
                                type="button"
                                @click.stop="openFaultAggregatedPodIpFilterDialog(podRow)"
                              >
                                ➕筛选
                              </button>
                            </div>
                            <div
                              v-if="getFaultAggregatedEventPodTotal(row) > 0"
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
                        :class="{
                          active: pageNum === faultAggregatedEventPage,
                          ellipsis: pageNum < 0,
                        }"
                        type="button"
                        :disabled="
                          pageNum < 0 ||
                          pageNum === faultAggregatedEventPage ||
                          isFaultAggregatedEventsLoading
                        "
                        @click="pageNum > 0 && goFaultAggregatedEventPage(pageNum)"
                      >
                        {{ pageNum < 0 ? '…' : pageNum }}
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
                </template>

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
              </div>

              <div
                v-else
                class="aggregate-table"
                :class="{
                  'aggregate-table-state-mode':
                    isFaultTraceEventsLoading ||
                    !!faultTraceEventsError ||
                    faultTraceRows.length === 0 ||
                    getFilteredFaultTraceRows().length === 0,
                }"
              >
                <div
                  ref="faultTraceTableRef"
                  class="aggregate-table-frame abnormal-trace-frame fault-trace-list"
                >
                  <div class="aggregate-fixed-left">
                    <div
                      class="abnormal-left-grid fault-trace-left-grid aggregate-table-header"
                      :style="{ gridTemplateColumns: getFaultTraceLeftGridColumnWidths() }"
                    >
                      <div class="aggregate-cell column-resizable">
                        故障类型
                        <div
                          class="column-resize-handle"
                          @mousedown="(e) => handleColumnResizeStart(e, 'faultTraceLeft', 0)"
                        ></div>
                      </div>
                      <div class="aggregate-cell column-resizable">
                        时间
                        <div
                          class="column-resize-handle"
                          @mousedown="(e) => handleColumnResizeStart(e, 'faultTraceLeft', 1)"
                        ></div>
                      </div>
                      <div class="aggregate-cell">Trace ID</div>
                    </div>
                    <template
                      v-if="
                        !isFaultTraceEventsLoading &&
                        !faultTraceEventsError &&
                        getFilteredFaultTraceRows().length > 0
                      "
                    >
                      <div
                        v-for="trace in getFilteredFaultTraceRows()"
                        :key="`${trace.id}-fixed`"
                        class="abnormal-left-grid fault-trace-left-grid aggregate-body-row"
                        :class="{
                          'shared-row-hover':
                            hoveredFaultTraceRowKey === `${trace.id}:${trace.traceId}`,
                        }"
                        :style="{ gridTemplateColumns: getFaultTraceLeftGridColumnWidths() }"
                        @mouseenter="hoveredFaultTraceRowKey = `${trace.id}:${trace.traceId}`"
                        @mouseleave="hoveredFaultTraceRowKey = ''"
                      >
                        <div class="aggregate-cell">
                          <span
                            v-for="tag in getTraceTags(trace.traceId, 'fault')"
                            :key="tag.type"
                            class="trace-type-tag"
                            :class="`trace-type-tag-${tag.type}`"
                          >
                            {{ tag.label }}
                          </span>
                        </div>
                        <div class="aggregate-cell">{{ trace.time }}</div>
                        <div class="aggregate-cell trace-id">{{ trace.traceId }}</div>
                      </div>
                    </template>
                  </div>

                  <div
                    class="aggregate-latency-scroll fault-trace-scroll scroll-section-outline"
                    :class="{
                      'scroll-section-outline-full':
                        !isFaultTraceEventsLoading &&
                        !faultTraceEventsError &&
                        getFilteredFaultTraceRows().length > 0,
                    }"
                  >
                    <div class="aggregate-latency-head aggregate-latency-sync">
                      <div
                        class="fault-trace-scroll-grid aggregate-table-header"
                        :style="faultTraceScrollGridStyle"
                      >
                        <div class="aggregate-cell column-resizable">
                          Pod IP
                          <div
                            class="column-resize-handle"
                            @mousedown="(e) => handleFaultTraceScrollColumnResizeStart(e, 0)"
                          ></div>
                        </div>
                        <div class="aggregate-cell column-resizable">
                          集群
                          <div
                            class="column-resize-handle"
                            @mousedown="(e) => handleFaultTraceScrollColumnResizeStart(e, 1)"
                          ></div>
                        </div>
                        <div class="aggregate-cell column-resizable">
                          主机IP
                          <div
                            class="column-resize-handle"
                            @mousedown="(e) => handleFaultTraceScrollColumnResizeStart(e, 2)"
                          ></div>
                        </div>
                        <div class="aggregate-cell column-resizable">
                          故障码
                          <div
                            class="column-resize-handle"
                            @mousedown="(e) => handleFaultTraceScrollColumnResizeStart(e, 3)"
                          ></div>
                        </div>
                        <div class="aggregate-cell column-resizable">
                          操作类型
                          <div
                            class="column-resize-handle"
                            @mousedown="(e) => handleFaultTraceScrollColumnResizeStart(e, 4)"
                          ></div>
                        </div>
                        <div class="aggregate-cell column-resizable">
                          故障名称
                          <div
                            class="column-resize-handle"
                            @mousedown="(e) => handleFaultTraceScrollColumnResizeStart(e, 5)"
                          ></div>
                        </div>
                        <div class="aggregate-cell column-resizable">
                          故障域
                          <div
                            class="column-resize-handle"
                            @mousedown="(e) => handleFaultTraceScrollColumnResizeStart(e, 6)"
                          ></div>
                        </div>
                      </div>
                    </div>
                    <div
                      class="aggregate-latency-scrollbar aggregate-latency-sync"
                      @scroll="syncAggregateLatencyScroll"
                    >
                      <div
                        class="aggregate-latency-scrollbar-spacer fault-trace-scrollbar-spacer"
                        :style="{ width: faultTraceScrollGridStyle.minWidth }"
                      ></div>
                    </div>
                    <div
                      class="aggregate-latency-body aggregate-latency-sync"
                      @scroll="syncAggregateLatencyScroll"
                    >
                      <template
                        v-if="
                          !isFaultTraceEventsLoading &&
                          !faultTraceEventsError &&
                          getFilteredFaultTraceRows().length > 0
                        "
                      >
                        <div
                          v-for="trace in getFilteredFaultTraceRows()"
                          :key="`${trace.id}-scroll`"
                          class="fault-trace-scroll-grid aggregate-body-row"
                          :class="{
                            'shared-row-hover':
                              hoveredFaultTraceRowKey === `${trace.id}:${trace.traceId}`,
                          }"
                          :style="faultTraceScrollGridStyle"
                          @mouseenter="hoveredFaultTraceRowKey = `${trace.id}:${trace.traceId}`"
                          @mouseleave="hoveredFaultTraceRowKey = ''"
                        >
                          <div class="aggregate-cell fault-trace-pod-cell">
                            <span
                              v-for="podName in trace.podNames"
                              :key="`${trace.id}-pod-${podName}`"
                              class="fault-trace-pod-item"
                            >
                              {{ podName }}
                            </span>
                          </div>
                          <div class="aggregate-cell fault-trace-cluster-cell">
                            <span
                              v-for="clusterName in trace.clusterNames"
                              :key="`${trace.id}-cluster-${clusterName}`"
                              class="fault-trace-cluster-item"
                            >
                              {{ clusterName }}
                            </span>
                          </div>
                          <div class="aggregate-cell fault-trace-host-cell">
                            <span
                              v-for="hostName in trace.hostNames"
                              :key="`${trace.id}-host-${hostName}`"
                              class="fault-trace-host-item"
                            >
                              {{ hostName }}
                            </span>
                          </div>
                          <div class="aggregate-cell">
                            <span
                              v-if="trace.faultCode"
                              class="fault-code-pill fault-code-clickable"
                              @click="openStatusCodePopover(trace.faultCode, $event)"
                            >
                              {{ trace.faultCode }}
                            </span>
                            <span v-else class="fault-code-pill">-</span>
                          </div>
                          <div class="aggregate-cell">{{ trace.operation || '-' }}</div>
                          <div class="aggregate-cell">
                            <button
                              v-if="trace.failureMode"
                              class="failure-mode-link-btn"
                              type="button"
                              @click="openFailureModeDetailPopover(trace.failureMode, $event)"
                            >
                              {{ trace.faultType }}
                            </button>
                            <span v-else>{{ trace.faultType }}</span>
                          </div>
                          <div class="aggregate-cell">{{ trace.faultDomain }}</div>
                        </div>
                      </template>
                    </div>
                  </div>

                  <div class="aggregate-fixed-actions">
                    <div class="aggregate-cell action-cell aggregate-table-header">Trace分析</div>
                    <template
                      v-if="
                        !isFaultTraceEventsLoading &&
                        !faultTraceEventsError &&
                        getFilteredFaultTraceRows().length > 0
                      "
                    >
                      <div
                        v-for="trace in getFilteredFaultTraceRows()"
                        :key="`${trace.id}-action`"
                        class="aggregate-cell action-cell trace-analysis-actions aggregate-body-row"
                        :class="{
                          'shared-row-hover':
                            hoveredFaultTraceRowKey === `${trace.id}:${trace.traceId}`,
                        }"
                        @mouseenter="hoveredFaultTraceRowKey = `${trace.id}:${trace.traceId}`"
                        @mouseleave="hoveredFaultTraceRowKey = ''"
                      >
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
                          ➕筛选
                        </button>
                      </div>
                    </template>
                  </div>
                </div>
                <div v-if="isFaultTraceEventsLoading" class="aggregate-table-state">
                  正在加载错误日志...
                </div>
                <div
                  v-else-if="faultTraceEventsError"
                  class="aggregate-table-state metric-table-error"
                >
                  {{ faultTraceEventsError }}
                </div>
                <div v-else-if="faultTraceRows.length === 0" class="aggregate-table-state">
                  暂无错误日志数据
                </div>
                <div
                  v-else-if="getFilteredFaultTraceRows().length === 0"
                  class="aggregate-table-state"
                >
                  无匹配错误日志
                </div>
              </div>
              <div
                v-if="activeFaultMonitorTab === 'trace' && faultTraceEventsTotal > 0"
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
                    :class="{ active: pageNum === faultTraceEventsPage, ellipsis: pageNum < 0 }"
                    type="button"
                    :disabled="
                      pageNum < 0 || pageNum === faultTraceEventsPage || isFaultTraceEventsLoading
                    "
                    @click="pageNum > 0 && goFaultTraceEventsPage(pageNum)"
                  >
                    {{ pageNum < 0 ? '…' : pageNum }}
                  </button>
                </span>
                <button
                  class="ghost-btn"
                  type="button"
                  :disabled="
                    faultTraceEventsPage >= faultTraceEventsPageCount || isFaultTraceEventsLoading
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
                  <path d="M7 7l.75 12.25a1.5 1.5 0 0 0 1.5 1.25h5.5a1.5 1.5 0 0 0 1.5-1.25L17 7" />
                  <path d="M10 11v5.5" />
                  <path d="M14 11v5.5" />
                </svg>
              </button>
            </div>
          </div>
        </header>

        <section class="log-upload-section">
          <div class="parse-config-bar">
            <div class="parse-config-main">
              <span class="parse-config-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M10 14v6" />
                </svg>
              </span>
              <div class="parse-config-copy">
                <div class="parse-config-title-row">
                  <strong>日志解析配置</strong>
                  <span class="parse-config-scope">本资产库</span>
                </div>
                <span class="parse-config-summary">{{ parseConfigSummary }}</span>
              </div>
            </div>
            <div class="parse-config-action">
              <button type="button" class="parse-config-edit-btn" @click="openParseConfigDrawer">
                修改配置
              </button>
            </div>
          </div>
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
                <button
                  class="log-file-delete-btn"
                  type="button"
                  aria-label="删除"
                  title="删除"
                  :disabled="deletingFileIds.has(file.id)"
                  @click="deleteLogFile(file.id)"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M6 7v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7M4 7h16M10 11v6M14 11v6M15 7V4a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v3" />
                  </svg>
                </button>
              </div>
            </div>
            <div v-if="logFilesTotal > 0" class="aggregate-pagination log-file-pagination">
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
                  :class="{ active: pageNum === logFilesPage, ellipsis: pageNum < 0 }"
                  type="button"
                  :disabled="pageNum < 0 || pageNum === logFilesPage || isLogFilesLoading"
                  @click="pageNum > 0 && goLogFilesPage(pageNum)"
                >
                  {{ pageNum < 0 ? '…' : pageNum }}
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
      <section class="modal-content filter-modal">
        <header class="modal-header">
          <h2>🔍 添加筛选条件</h2>
          <button class="close-modal" type="button" title="关闭" @click="closeTraceFilterDialog">
            x
          </button>
        </header>

        <div class="modal-body">
          <div class="filter-bar-list">
            <div class="filter-bar">
              <div class="filter-bar-info">
                <span class="filter-bar-label">Trace ID</span>
                <span class="filter-bar-value">{{ traceFilterDialog.trace?.traceId }}</span>
              </div>
              <div class="filter-bar-options">
                <label class="trace-filter-option">
                  <input v-model="traceFilterDialog.addTraceBoard" type="checkbox" />
                  <span>添加到Trace看板</span>
                </label>
              </div>
            </div>

            <div class="filter-bar">
              <div class="filter-bar-info">
                <span class="filter-bar-label">Pod IP</span>
                <span class="filter-bar-value">{{ traceFilterDialog.trace?.podIp || 'null' }}</span>
              </div>
              <div class="filter-bar-options">
                <label class="trace-filter-option">
                  <input
                    v-model="traceFilterDialog.addPodIp"
                    type="checkbox"
                    :disabled="!isTraceFilterValueAvailable(traceFilterDialog.trace?.podIp)"
                  />
                  <span>添加到Pod IP</span>
                </label>
                <label class="trace-filter-option">
                  <input
                    v-model="traceFilterDialog.addSourcePodIp"
                    type="checkbox"
                    :disabled="!isTraceFilterValueAvailable(traceFilterDialog.trace?.podIp)"
                  />
                  <span>添加到源 IP</span>
                </label>
                <label class="trace-filter-option">
                  <input
                    v-model="traceFilterDialog.addTargetPodIp"
                    type="checkbox"
                    :disabled="!isTraceFilterValueAvailable(traceFilterDialog.trace?.podIp)"
                  />
                  <span>添加到目标 IP</span>
                </label>
              </div>
            </div>

            <div class="filter-bar">
              <div class="filter-bar-info">
                <span class="filter-bar-label">集群</span>
                <span class="filter-bar-value">
                  {{ traceFilterDialog.trace?.clusterName || 'null' }}
                </span>
              </div>
              <div class="filter-bar-options">
                <label class="trace-filter-option">
                  <input
                    v-model="traceFilterDialog.addCluster"
                    type="checkbox"
                    :disabled="!isTraceFilterValueAvailable(traceFilterDialog.trace?.clusterName)"
                  />
                  <span>添加到集群</span>
                </label>
              </div>
            </div>

            <div class="filter-bar">
              <div class="filter-bar-info">
                <span class="filter-bar-label">主机</span>
                <span class="filter-bar-value">{{ traceFilterDialog.trace?.host || 'null' }}</span>
              </div>
              <div class="filter-bar-options">
                <label class="trace-filter-option">
                  <input
                    v-model="traceFilterDialog.addHost"
                    type="checkbox"
                    :disabled="!isTraceFilterValueAvailable(traceFilterDialog.trace?.host)"
                  />
                  <span>添加到主机</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <footer class="modal-actions">
          <button class="ghost-btn" type="button" @click="closeTraceFilterDialog">取消</button>
          <button class="save-btn" type="button" @click="confirmTraceFilterDialog">确定</button>
        </footer>
      </section>
    </div>

    <div v-if="abnormalTraceFilterDialog.open" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content filter-modal abnormal-trace-filter-modal">
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

    <div v-if="latencyPodIpFilterDialog.open" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content filter-modal">
        <header class="modal-header">
          <h2>🔍 添加筛选条件</h2>
          <button
            class="close-modal"
            type="button"
            title="关闭"
            @click="closeLatencyPodIpFilterDialog"
          >
            x
          </button>
        </header>

        <div class="modal-body">
          <div class="filter-bar-list">
            <div class="filter-bar">
              <div class="filter-bar-info">
                <span class="filter-bar-label">源 IP</span>
                <span class="filter-bar-value">
                  {{ latencyPodIpFilterDialog.row?.sourcePodIp }}
                </span>
              </div>
              <div class="filter-bar-options">
                <label class="trace-filter-option">
                  <input v-model="latencyPodIpFilterDialog.addSourcePodIp" type="checkbox" />
                  <span>添加到源IP</span>
                </label>
                <label class="trace-filter-option">
                  <input
                    v-model="latencyPodIpFilterDialog.addSourcePodIpToPodFilter"
                    type="checkbox"
                  />
                  <span>添加到Pod IP</span>
                </label>
              </div>
            </div>
            <div class="filter-bar">
              <div class="filter-bar-info">
                <span class="filter-bar-label">目标 IP</span>
                <span class="filter-bar-value">
                  {{ latencyPodIpFilterDialog.row?.targetPodIp }}
                </span>
              </div>
              <div class="filter-bar-options">
                <label class="trace-filter-option">
                  <input v-model="latencyPodIpFilterDialog.addTargetPodIp" type="checkbox" />
                  <span>添加到目标IP</span>
                </label>
                <label class="trace-filter-option">
                  <input
                    v-model="latencyPodIpFilterDialog.addTargetPodIpToPodFilter"
                    type="checkbox"
                  />
                  <span>添加到Pod IP</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <footer class="modal-actions">
          <button class="ghost-btn" type="button" @click="closeLatencyPodIpFilterDialog">
            取消
          </button>
          <button class="save-btn" type="button" @click="confirmLatencyPodIpFilterDialog">
            确定
          </button>
        </footer>
      </section>
    </div>

    <div v-if="faultAggregatedPodIpFilterDialog.open" class="modal" role="dialog" aria-modal="true">
      <section class="modal-content filter-modal">
        <header class="modal-header">
          <h2>🔍 添加筛选条件</h2>
          <button
            class="close-modal"
            type="button"
            title="关闭"
            @click="closeFaultAggregatedPodIpFilterDialog"
          >
            x
          </button>
        </header>

        <div class="modal-body">
          <div class="filter-bar-list">
            <div class="filter-bar">
              <div class="filter-bar-info">
                <span class="filter-bar-label">源 / 目标 IP</span>
                <span class="filter-bar-value">
                  {{ faultAggregatedPodIpFilterDialog.podRow?.srcIp }} →
                  {{ faultAggregatedPodIpFilterDialog.podRow?.dstIp }}
                </span>
              </div>
              <div class="filter-bar-options">
                <label class="trace-filter-option">
                  <input v-model="faultAggregatedPodIpFilterDialog.addPodIp" type="checkbox" />
                  <span>添加源/目标到Pod IP</span>
                </label>
                <label class="trace-filter-option">
                  <input
                    v-model="faultAggregatedPodIpFilterDialog.addSourcePodIp"
                    type="checkbox"
                  />
                  <span>添加到源IP</span>
                </label>
                <label class="trace-filter-option">
                  <input
                    v-model="faultAggregatedPodIpFilterDialog.addTargetPodIp"
                    type="checkbox"
                  />
                  <span>添加到目标IP</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <footer class="modal-actions">
          <button class="ghost-btn" type="button" @click="closeFaultAggregatedPodIpFilterDialog">
            取消
          </button>
          <button class="save-btn" type="button" @click="confirmFaultAggregatedPodIpFilterDialog">
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
      <aside class="side-drawer aggregate-event-detail-drawer">
        <header class="side-drawer-header">
          <div class="side-drawer-title">
            <h2>聚合事件详情</h2>
            <span class="aggregate-detail-hosts">
              {{ selectedAggregatedEvent.sourcePodIp }} → {{ selectedAggregatedEvent.targetPodIp }}
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
              <div class="aggregate-parse-results-title">
                <h3>异常 Trace</h3>
                <span class="parse-result-count">{{ detailParseResultsBadgeCount }} 条</span>
              </div>
              <form class="trace-id-search" @submit.prevent="submitDetailParseResultTraceIdQuery">
                <label class="trace-id-search-field">
                  <span>Trace ID</span>
                  <input
                    v-model="detailParseResultTraceIdInput"
                    type="text"
                    placeholder="输入 Trace ID"
                    autocomplete="off"
                    :disabled="isDetailParseResultsLoading"
                  />
                </label>
                <button
                  class="save-btn compact-action-btn trace-id-search-submit"
                  type="submit"
                  :disabled="isDetailParseResultsLoading"
                >
                  查询
                </button>
              </form>
            </div>
            <div
              class="parse-result-table-wrapper detail-abnormal-trace-wrapper"
              :class="{
                'aggregate-table-state-mode':
                  isDetailParseResultsLoading ||
                  !!detailParseResultsError ||
                  detailParseResultRows.length === 0,
              }"
            >
              <div
                ref="detailAbnormalTraceTableRef"
                class="aggregate-table-frame abnormal-trace-frame detail-abnormal-trace-frame"
              >
                <div class="aggregate-fixed-left">
                  <div
                    class="abnormal-left-grid latency-anomaly-left-grid aggregate-table-header"
                    :style="{ gridTemplateColumns: getLatencyLeftGridColumnWidths() }"
                  >
                    <div class="aggregate-cell">标签</div>
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
                      :style="{
                        gridTemplateColumns: getLatencyLeftGridColumnWidths(),
                        height: getTraceRowHeight(row.podIp),
                      }"
                    >
                      <div class="aggregate-cell">
                        <span
                          v-for="tag in getTraceTags(row.traceId, 'latency')"
                          :key="tag.type"
                          class="trace-type-tag"
                          :class="`trace-type-tag-${tag.type}`"
                        >
                          {{ tag.label }}
                        </span>
                      </div>
                      <div class="aggregate-cell">{{ row.time }}</div>
                      <div class="aggregate-cell trace-id">{{ row.traceId }}</div>
                      <div class="aggregate-cell multi-line-pod-cell" v-html="row.podIp"></div>
                      <div class="aggregate-cell">{{ row.operation }}</div>
                      <div class="aggregate-cell">{{ row.clusterName }}</div>
                      <div class="aggregate-cell">{{ row.host }}</div>
                    </div>
                  </template>
                </div>

                <div
                  class="aggregate-latency-scroll scroll-section-outline"
                  :class="{
                    'scroll-section-outline-full':
                      !isDetailParseResultsLoading &&
                      !detailParseResultsError &&
                      detailParseResultRows.length > 0,
                  }"
                >
                  <div class="aggregate-latency-head aggregate-latency-sync">
                    <div
                      class="abnormal-latency-grid aggregate-table-header"
                      :style="{ gridTemplateColumns: getLatencyDataGridColumnWidths(), minWidth: getLatencyDataTotalWidth() + 'px' }"
                    >
                      <div
                        class="aggregate-cell aggregate-sortable-cell"
                        @click="detailParseResultSort.handleHeaderClick('total_latency')"
                      >
                        <span class="sort-header-content">
                          总时延 (ms)
                          <span class="sort-icons">
                            <span
                              class="sort-icon-up"
                              :class="{
                                'sort-icon-active':
                                  detailParseResultSort.getSortOrder('total_latency') === 'asc',
                              }"
                              >▲</span
                            >
                            <span
                              class="sort-icon-down"
                              :class="{
                                'sort-icon-active':
                                  detailParseResultSort.getSortOrder('total_latency') === 'desc',
                              }"
                              >▼</span
                            >
                          </span>
                        </span>
                      </div>
                      <div
                        v-for="col in getLatencyDataColumns.slice(1)"
                        :key="col.key"
                        class="aggregate-cell aggregate-sortable-cell"
                        @click="detailParseResultSort.handleHeaderClick(getDetailSortKey(col.key))"
                      >
                        <span class="sort-header-content">
                          {{ col.label }}
                          <span class="sort-icons">
                            <span
                              class="sort-icon-up"
                              :class="{
                                'sort-icon-active':
                                  detailParseResultSort.getSortOrder(
                                    getDetailSortKey(col.key),
                                  ) === 'asc',
                              }"
                              >▲</span
                            >
                            <span
                              class="sort-icon-down"
                              :class="{
                                'sort-icon-active':
                                  detailParseResultSort.getSortOrder(
                                    getDetailSortKey(col.key),
                                  ) === 'desc',
                              }"
                              >▼</span
                            >
                          </span>
                        </span>
                      </div>
                    </div>
                  </div>
                  <div
                    class="aggregate-latency-scrollbar aggregate-latency-sync"
                    @scroll="syncAggregateLatencyScroll"
                  >
                    <div
                      class="aggregate-latency-scrollbar-spacer"
                      :style="{ minWidth: getLatencyDataTotalWidth() + 'px' }"
                    ></div>
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
                        :style="{ height: getTraceRowHeight(row.podIp) }"
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
                        <div
                          v-for="col in getLatencyDataColumns.slice(1)"
                          :key="col.key"
                          class="aggregate-cell"
                        >
                          <span
                            class="metric-value"
                            :class="{
                              abnormal: isAnomalyListLatencyMetricAbnormal(
                                row,
                                col.key,
                                getLatencyRowValue(row as any, col.key),
                              ),
                            }"
                          >
                            {{ formatNullableMetricValue(getLatencyRowValue(row as any, col.key)) }}
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
                      :style="{ height: getTraceRowHeight(row.podIp) }"
                    >
                      <button
                        class="metric-action-btn detail-action-btn"
                        type="button"
                        @click="openParseResultChain(row)"
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
            <div v-if="detailParseResultsTotal > 0" class="parse-result-pagination">
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
                  :class="{ active: pageNum === detailParseResultsPage, ellipsis: pageNum < 0 }"
                  type="button"
                  :disabled="
                    pageNum < 0 || pageNum === detailParseResultsPage || isDetailParseResultsLoading
                  "
                  @click="pageNum > 0 && goDetailParseResultsPage(pageNum)"
                >
                  {{ pageNum < 0 ? '…' : pageNum }}
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
      <aside class="side-drawer aggregate-event-detail-drawer">
        <header class="side-drawer-header">
          <div class="side-drawer-title">
            <h2>聚合事件详情</h2>
            <span class="aggregate-detail-hosts">
              {{ selectedFaultAggregatedEventDetail.podRow.srcIp }} →
              {{ selectedFaultAggregatedEventDetail.podRow.dstIp }}
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
                  selectedFaultDetailChartCodes.length === 0 || faultDetailChartBuckets.length === 0
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
              <div class="aggregate-parse-results-title">
                <h3>异常 Trace</h3>
                <span class="parse-result-count">{{ selectedFaultDetailErrorLogTotal }} 条</span>
              </div>
              <form class="trace-id-search" @submit.prevent="submitFaultDetailTraceIdQuery">
                <label class="trace-id-search-field">
                  <span>Trace ID</span>
                  <input
                    v-model="faultDetailTraceIdInput"
                    type="text"
                    placeholder="输入 Trace ID"
                    autocomplete="off"
                    :disabled="isFaultDetailTraceEventsLoading"
                  />
                </label>
                <button
                  class="save-btn compact-action-btn trace-id-search-submit"
                  type="submit"
                  :disabled="isFaultDetailTraceEventsLoading"
                >
                  查询
                </button>
              </form>
            </div>
            <div
              class="parse-result-table-wrapper fault-detail-log-wrapper aggregate-table"
              :class="{
                'aggregate-table-state-mode':
                  isFaultDetailTraceEventsLoading ||
                  !!faultDetailTraceEventsError ||
                  faultDetailTraceRows.length === 0,
              }"
            >
              <div class="aggregate-table-frame abnormal-trace-frame fault-trace-list">
                <div class="aggregate-fixed-left">
                  <div
                    class="abnormal-left-grid fault-trace-left-grid aggregate-table-header"
                    :style="{ gridTemplateColumns: getFaultTraceLeftGridColumnWidths() }"
                  >
                    <div class="aggregate-cell">故障类型</div>
                    <div class="aggregate-cell">时间</div>
                    <div class="aggregate-cell">Trace ID</div>
                  </div>
                  <template
                    v-if="
                      !isFaultDetailTraceEventsLoading &&
                      !faultDetailTraceEventsError &&
                      faultDetailTraceRows.length > 0
                    "
                  >
                    <div
                      v-for="trace in faultDetailTraceRows"
                      :key="`${trace.id}-fixed`"
                      class="abnormal-left-grid fault-trace-left-grid aggregate-body-row"
                      :style="{ gridTemplateColumns: getFaultTraceLeftGridColumnWidths() }"
                    >
                      <div class="aggregate-cell">
                        <span
                          v-for="tag in getTraceTags(trace.traceId, 'fault')"
                          :key="tag.type"
                          class="trace-type-tag"
                          :class="`trace-type-tag-${tag.type}`"
                        >
                          {{ tag.label }}
                        </span>
                      </div>
                      <div class="aggregate-cell">{{ trace.time }}</div>
                      <div class="aggregate-cell trace-id">{{ trace.traceId }}</div>
                    </div>
                  </template>
                </div>

                <div
                  class="aggregate-latency-scroll fault-trace-scroll scroll-section-outline"
                  :class="{
                    'scroll-section-outline-full':
                      !isFaultDetailTraceEventsLoading &&
                      !faultDetailTraceEventsError &&
                      faultDetailTraceRows.length > 0,
                  }"
                >
                  <div class="aggregate-latency-head aggregate-latency-sync">
                    <div
                      class="fault-trace-scroll-grid aggregate-table-header"
                      :style="faultDetailTraceScrollGridStyle"
                    >
                      <div class="aggregate-cell">集群</div>
                      <div class="aggregate-cell">主机IP</div>
                      <div class="aggregate-cell">故障码</div>
                      <div class="aggregate-cell">操作类型</div>
                      <div class="aggregate-cell">故障名称</div>
                      <div class="aggregate-cell">故障域</div>
                    </div>
                  </div>
                  <div
                    class="aggregate-latency-scrollbar aggregate-latency-sync"
                    @scroll="syncAggregateLatencyScroll"
                  >
                    <div
                      class="aggregate-latency-scrollbar-spacer fault-trace-scrollbar-spacer"
                      :style="{ width: faultDetailTraceScrollGridStyle.minWidth }"
                    ></div>
                  </div>
                  <div
                    class="aggregate-latency-body aggregate-latency-sync"
                    @scroll="syncAggregateLatencyScroll"
                  >
                    <template
                      v-if="
                        !isFaultDetailTraceEventsLoading &&
                        !faultDetailTraceEventsError &&
                        faultDetailTraceRows.length > 0
                      "
                    >
                      <div
                        v-for="trace in faultDetailTraceRows"
                        :key="`${trace.id}-scroll`"
                        class="fault-trace-scroll-grid aggregate-body-row"
                        :style="faultDetailTraceScrollGridStyle"
                      >
                        <div class="aggregate-cell fault-trace-cluster-cell">
                          <span
                            v-for="clusterName in trace.clusterNames"
                            :key="`${trace.id}-cluster-${clusterName}`"
                            class="fault-trace-cluster-item"
                          >
                            {{ clusterName }}
                          </span>
                        </div>
                        <div class="aggregate-cell fault-trace-host-cell">
                          <span
                            v-for="hostName in trace.hostNames"
                            :key="`${trace.id}-host-${hostName}`"
                            class="fault-trace-host-item"
                          >
                            {{ hostName }}
                          </span>
                        </div>
                        <div class="aggregate-cell">
                          <span
                            v-if="trace.faultCode"
                            class="fault-code-pill fault-code-clickable"
                            @click="openStatusCodePopover(trace.faultCode, $event)"
                          >
                            {{ trace.faultCode }}
                          </span>
                          <span v-else class="fault-code-pill">-</span>
                        </div>
                        <div class="aggregate-cell">{{ trace.operation || '-' }}</div>
                        <div class="aggregate-cell">
                          <button
                            v-if="trace.failureMode"
                            class="failure-mode-link-btn"
                            type="button"
                            @click="openFailureModeDetailPopover(trace.failureMode, $event)"
                          >
                            {{ trace.faultType }}
                          </button>
                          <span v-else>{{ trace.faultType }}</span>
                        </div>
                        <div class="aggregate-cell">{{ trace.faultDomain }}</div>
                      </div>
                    </template>
                  </div>
                </div>

                <div class="aggregate-fixed-actions">
                  <div class="aggregate-cell action-cell aggregate-table-header">Trace分析</div>
                  <template
                    v-if="
                      !isFaultDetailTraceEventsLoading &&
                      !faultDetailTraceEventsError &&
                      faultDetailTraceRows.length > 0
                    "
                  >
                    <div
                      v-for="trace in faultDetailTraceRows"
                      :key="`${trace.id}-action`"
                      class="aggregate-cell action-cell trace-analysis-actions aggregate-body-row"
                    >
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
                        ➕筛选
                      </button>
                    </div>
                  </template>
                </div>
              </div>
              <div v-if="isFaultDetailTraceEventsLoading" class="aggregate-table-state">
                正在加载错误日志...
              </div>
              <div
                v-else-if="faultDetailTraceEventsError"
                class="aggregate-table-state metric-table-error"
              >
                {{ faultDetailTraceEventsError }}
              </div>
              <div v-else-if="faultDetailTraceRows.length === 0" class="aggregate-table-state">
                暂无错误日志
              </div>
            </div>
            <div v-if="faultDetailTraceEventsTotal > 0" class="parse-result-pagination">
              <button
                class="ghost-btn"
                type="button"
                :disabled="faultDetailTraceEventsPage <= 1 || isFaultDetailTraceEventsLoading"
                @click="goFaultDetailTraceEventsPage(faultDetailTraceEventsPage - 1)"
              >
                上一页
              </button>
              <span class="pagination-pages" aria-label="故障详情错误日志页码">
                <button
                  v-for="pageNum in faultDetailTraceEventsPageWindow"
                  :key="`fault-detail-trace-page-${pageNum}`"
                  class="pagination-page-btn"
                  :class="{
                    active: pageNum === faultDetailTraceEventsPage,
                    ellipsis: pageNum < 0,
                  }"
                  type="button"
                  :disabled="
                    pageNum < 0 ||
                    pageNum === faultDetailTraceEventsPage ||
                    isFaultDetailTraceEventsLoading
                  "
                  @click="pageNum > 0 && goFaultDetailTraceEventsPage(pageNum)"
                >
                  {{ pageNum < 0 ? '…' : pageNum }}
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
              <div v-else class="trace-raw-log-table-wrapper">
                <table class="trace-raw-log-table">
                  <thead>
                    <tr>
                      <th
                        v-for="(column, columnIndex) in getVisibleTraceLogColumns(
                          getSelectedTraceLogs()[0],
                        )"
                        :key="`${column.label}-${columnIndex}`"
                        :class="{ 'trace-log-level-cell': column.label.toLowerCase() === 'level' }"
                      >
                        {{ column.label }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="log in getSelectedTraceLogs()"
                      :key="`${log.filename}-${log.time}-${log.pidTid}-${log.rawText}`"
                      :class="getTraceLogRowClass(log)"
                    >
                      <td
                        v-for="(column, columnIndex) in getVisibleTraceLogColumns(log)"
                        :key="`${column.label}-${columnIndex}`"
                        :title="column.value"
                        :class="[
                          { 'trace-log-level-cell': column.label.toLowerCase() === 'level' },
                          column.label.toLowerCase() === 'level' ? getTraceLogLevelClass(log) : '',
                        ]"
                      >
                        {{ column.value }}
                        <template v-if="isTraceLogMessageColumn(column)">
                          <button
                            v-for="mode in getTraceLogFailureModeLabels(log)"
                            :key="mode.id"
                            type="button"
                            class="failure-mode-tag trace-message-failure-mode"
                            :class="{ active: selectedTraceFailureModeId === mode.id }"
                            @click="selectTraceFailureMode(mode.id)"
                          >
                            🔴 {{ mode.label }}
                          </button>
                        </template>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          <section>
            <h3 class="trace-section-title">🗃️ 故障模式详情</h3>
            <div v-if="selectedTraceFailureModes.length === 0" class="trace-fault-detail-list">
              <div class="trace-fault-detail-item trace-fault-detail-wide">
                <span class="trace-fault-detail-value">暂无故障模式</span>
              </div>
            </div>
            <div v-else-if="!selectedTraceFailureMode" class="failure-mode-chain-list">
              <div class="failure-mode-chain-item">
                <div class="failure-mode-chain-detail">
                  <span class="trace-fault-detail-value">点击运行日志中的故障模式标签查看详情</span>
                </div>
              </div>
            </div>
            <div v-else class="failure-mode-chain-list">
              <div class="failure-mode-chain-item">
                <div class="failure-mode-chain-header">
                  <span class="failure-mode-chain-id">{{ selectedTraceFailureMode._id }}</span>
                  <span class="failure-mode-chain-name">
                    {{ selectedTraceFailureMode.name || '-' }}
                  </span>
                  <span class="failure-mode-chain-domain">
                    故障域：{{ selectedTraceFailureMode.failure_domain || '-' }}
                  </span>
                </div>
                <div class="failure-mode-chain-detail">
                  <div class="trace-fault-detail-list">
                    <div class="trace-fault-detail-item trace-fault-detail-wide">
                      <span class="trace-fault-detail-label">故障表现</span>
                      <span class="trace-fault-detail-value">
                        {{ selectedTraceFailureMode.symptom || '-' }}
                      </span>
                    </div>
                    <div class="trace-fault-detail-item trace-fault-detail-wide">
                      <span class="trace-fault-detail-label">故障根因</span>
                      <span class="trace-fault-detail-value">
                        {{ selectedTraceFailureMode.root_cause || '-' }}
                      </span>
                    </div>
                    <div class="trace-fault-detail-item trace-fault-detail-wide">
                      <span class="trace-fault-detail-label">解决方法</span>
                      <span class="trace-fault-detail-value">
                        {{ selectedTraceFailureMode.solution || '-' }}
                      </span>
                    </div>
                    <div class="trace-fault-detail-item trace-fault-detail-wide">
                      <span class="trace-fault-detail-label">子故障</span>
                      <span
                        v-if="getFailureModeChildren(selectedTraceFailureMode).length === 0"
                        class="trace-fault-detail-value"
                      >
                        -
                      </span>
                      <div v-else class="trace-sub-fault-block">
                        <div class="trace-sub-fault-list">
                          <button
                            v-for="childId in getFailureModeChildren(selectedTraceFailureMode)"
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
                    <td :class="{ 'delay-timeout': isTraceDelayAbnormal(selectedTrace, column) }">
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
              <div v-else class="trace-raw-log-table-wrapper">
                <table class="trace-raw-log-table">
                  <thead>
                    <tr>
                      <th
                        v-for="(column, columnIndex) in getVisibleTraceLogColumns(
                          getSelectedFaultTraceLogs()[0],
                        )"
                        :key="`${column.label}-${columnIndex}`"
                        :class="{ 'trace-log-level-cell': column.label.toLowerCase() === 'level' }"
                      >
                        {{ column.label }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="log in getSelectedFaultTraceLogs()"
                      :key="`${log.filename}-${log.time}-${log.pidTid}-${log.rawText}`"
                      :class="getTraceLogRowClass(log)"
                    >
                      <td
                        v-for="(column, columnIndex) in getVisibleTraceLogColumns(log)"
                        :key="`${column.label}-${columnIndex}`"
                        :title="column.value"
                        :class="[
                          { 'trace-log-level-cell': column.label.toLowerCase() === 'level' },
                          column.label.toLowerCase() === 'level' ? getTraceLogLevelClass(log) : '',
                        ]"
                      >
                        {{ column.value }}
                        <template v-if="isTraceLogMessageColumn(column)">
                          <button
                            v-for="mode in getTraceLogFailureModeLabels(log)"
                            :key="mode.id"
                            type="button"
                            class="failure-mode-tag trace-message-failure-mode"
                            :class="{ active: selectedFaultTraceFailureModeId === mode.id }"
                            @click="selectFaultTraceFailureMode(mode.id)"
                          >
                            🔴 {{ mode.label }}
                          </button>
                        </template>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
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
                      :class="{ 'delay-timeout': isTraceDelayAbnormal(selectedFaultTrace, column) }"
                    >
                      {{
                        formatTraceDelayColumnValue(
                          getTraceDelayValue(selectedFaultTrace, column),
                          column,
                        )
                      }}
                    </td>
                    <td
                      class="trace-stage-status"
                      :class="{ 'delay-timeout': isTraceDelayAbnormal(selectedFaultTrace, column) }"
                    >
                      {{ getTraceDelayStatusLabel(selectedFaultTrace, column) }}
                    </td>
                  </tr>
                </tbody>
              </table>
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

    <div
      v-if="isParseConfigDrawerOpen"
      class="side-drawer-mask parse-config-drawer-mask"
      role="dialog"
      aria-modal="true"
      aria-labelledby="parse-config-drawer-title"
      @click.self="closeParseConfigDrawer"
    >
      <aside class="side-drawer parse-config-drawer">
        <header class="side-drawer-header">
          <div class="side-drawer-title parse-config-drawer-title">
            <h2 id="parse-config-drawer-title">日志解析配置</h2>
            <span>{{ selectedAsset?.name || '当前资产库' }}</span>
          </div>
          <button
            class="close-modal"
            type="button"
            title="关闭"
            aria-label="关闭配置"
            @click="closeParseConfigDrawer"
          >
            ×
          </button>
        </header>

        <div class="side-drawer-body parse-config-drawer-body">
          <div v-if="diagnosisConfigError" class="diagnosis-config-error" role="alert">
            {{ diagnosisConfigError }}
          </div>
          <div v-if="isDiagnosisConfigLoading" class="diagnosis-config-loading">
            正在读取当前配置...
          </div>

          <section v-show="!isDiagnosisConfigLoading" class="config-import-section">
            <div class="config-import-copy">
              <strong>导入其他资产库配置</strong>
              <span>导入后仅填充当前表单，点击“保存配置”后才会应用到当前资产库。</span>
            </div>
            <div class="config-import-controls">
              <select
                v-model="diagnosisConfigImportAssetId"
                :disabled="
                  isDiagnosisConfigImportListLoading ||
                  isDiagnosisConfigImporting ||
                  diagnosisConfigImportAssets.length === 0
                "
                aria-label="选择要导入配置的资产库"
              >
                <option value="">
                  {{
                    isDiagnosisConfigImportListLoading
                      ? '正在加载资产库...'
                      : diagnosisConfigImportAssets.length
                        ? '选择资产库'
                        : '暂无其他资产库'
                  }}
                </option>
                <option
                  v-for="asset in diagnosisConfigImportAssets"
                  :key="asset.id"
                  :value="asset.id"
                >
                  {{ asset.name }}
                </option>
              </select>
              <button
                type="button"
                :disabled="!diagnosisConfigImportAssetId || isDiagnosisConfigImporting"
                @click="importDiagnosisConfigFromAsset"
              >
                {{ isDiagnosisConfigImporting ? '导入中...' : '导入配置' }}
              </button>
            </div>
            <span v-if="diagnosisConfigImportMessage" class="config-import-message">
              {{ diagnosisConfigImportMessage }}
            </span>
          </section>

          <section
            v-show="!isDiagnosisConfigLoading"
            class="parse-config-section pattern-config-section"
          >
            <div class="parse-config-section-heading">
              <div>
                <h3>日志文件名 Pattern</h3>
                <p>
                  使用
                  <strong>glob 模式</strong>识别不同类型的日志文件。可添加自定义规则，点击标签上的 ×
                  可删除。
                </p>
              </div>
            </div>

            <div class="pattern-type-list">
              <article
                v-for="option in patternTypeOptions"
                :key="option.key"
                class="pattern-type-item"
              >
                <div class="pattern-type-heading">
                  <div>
                    <strong>{{ option.label }}</strong>
                    <span>{{ option.description }}</span>
                  </div>
                  <span class="pattern-count">
                    {{ diagnosisConfigDraft.logFilenamePattern[option.key].length }} 个
                  </span>
                </div>
                <div
                  v-if="diagnosisConfigDraft.logFilenamePattern[option.key].length"
                  class="pattern-chip-list"
                >
                  <span
                    v-for="(pattern, patternIndex) in diagnosisConfigDraft.logFilenamePattern[
                      option.key
                    ]"
                    :key="`${option.key}-${pattern}-${patternIndex}`"
                    class="pattern-chip"
                  >
                    <code>{{ pattern }}</code>
                    <button
                      type="button"
                      :aria-label="`删除 ${pattern}`"
                      @click="removeFilenamePattern(option.key, patternIndex)"
                    >
                      ×
                    </button>
                  </span>
                </div>
                <div v-else class="pattern-empty">暂无 Pattern，请至少添加一项</div>
                <div class="pattern-add-row">
                  <input
                    v-model="patternInputs[option.key]"
                    type="text"
                    placeholder="输入 Pattern"
                    @keydown.enter.prevent="addFilenamePattern(option.key)"
                  />
                  <button
                    type="button"
                    :disabled="!patternInputs[option.key].trim()"
                    @click="addFilenamePattern(option.key)"
                  >
                    添加
                  </button>
                </div>
              </article>
            </div>
          </section>

          <section
            v-show="!isDiagnosisConfigLoading"
            class="parse-config-section analyzer-config-section"
          >
            <div class="parse-config-section-heading">
              <div>
                <h3>日志分析参数</h3>
                <p>调整异常检测使用的时延阈值，单条日志超过阈值即标记为异常。</p>
              </div>
            </div>

            <h4 class="analyzer-group-title">时延阈值</h4>
            <div class="analyzer-threshold-grid">
              <label
                v-for="option in analyzerThresholdOptions"
                :key="option.key"
                class="analyzer-threshold-field"
              >
                <span class="analyzer-field-name">{{ option.label }}</span>
                <span class="analyzer-field-description">{{ option.description }}</span>
                <span class="parse-config-input-suffix">
                  <input
                    v-model.number="diagnosisConfigDraft.logAnalyzerParams[option.key]"
                    type="number"
                    min="0"
                    step="0.1"
                  />
                  <em>ms</em>
                </span>
              </label>
            </div>
          </section>
        </div>

        <footer class="parse-config-drawer-footer">
          <button
            class="parse-config-reset-btn"
            type="button"
            :disabled="isDiagnosisConfigLoading || isDiagnosisConfigSaving"
            @click="resetParseConfigDraft"
          >
            恢复默认
          </button>
          <div>
            <button
              class="ghost-btn"
              type="button"
              :disabled="isDiagnosisConfigSaving"
              @click="closeParseConfigDrawer"
            >
              取消
            </button>
            <button
              class="save-btn"
              type="button"
              :disabled="isDiagnosisConfigLoading || isDiagnosisConfigSaving"
              @click="saveParseConfig"
            >
              {{ isDiagnosisConfigSaving ? '保存中...' : '保存配置' }}
            </button>
          </div>
        </footer>
      </aside>
    </div>

    <aside
      v-if="isAbnormalMonitorPage && isAgentChatOpen"
      class="agent-chat-panel"
      role="dialog"
      aria-label="AI 故障诊断助手"
    >
      <header class="agent-chat-header">
        <button
          v-if="agentView !== 'login' && agentView !== 'models'"
          class="agent-auth-back"
          type="button"
          aria-label="返回上一级"
          @click="
            agentView = agentView === 'chat' || agentView === 'providers' ? 'models' : 'providers'
          "
        >
          ‹
        </button>
        <div class="agent-chat-heading">
          <span
            class="agent-chat-status"
            :class="{ disconnected: isAgentConnectionUnavailable }"
            aria-hidden="true"
          ></span>
          <div>
            <strong>AI 故障诊断助手</strong>
            <span v-if="agentView === 'chat' && selectedAgentModel">
              {{ selectedAgentProvider?.name }} · {{ selectedAgentModel.name }}
            </span>
            <span v-else>时延与通断故障分析</span>
          </div>
        </div>
      </header>

      <main v-if="agentView === 'login'" class="agent-auth-page">
        <div class="agent-auth-intro">
          <span class="agent-chat-welcome-icon" aria-hidden="true">✦</span>
          <h3>连接 OpenCode</h3>
          <p>选择本地服务器，或使用登录信息连接远程服务器。</p>
        </div>
        <div class="agent-auth-connectors">
          <button
            class="agent-auth-local"
            type="button"
            :disabled="isAgentLoggingIn"
            @click="loginLocalAgent"
          >
            <strong>连接到本机 OpenCode 服务器</strong>
            <span>127.0.0.1:4096 · 无需用户名和密码</span>
          </button>
          <form class="agent-auth-form agent-auth-remote" @submit.prevent="loginAgent">
            <div class="agent-auth-remote-title">
              <strong>远程连接</strong>
              <span>使用远程服务器的登录信息</span>
            </div>
            <label>
              <span>用户名</span>
              <input
                v-model.trim="agentUsername"
                autocomplete="username"
                placeholder="请输入用户名"
              />
            </label>
            <label>
              <span>密码</span>
              <input
                v-model="agentPassword"
                type="password"
                autocomplete="current-password"
                placeholder="请输入密码"
              />
            </label>
            <label>
              <span>URL</span>
              <input v-model.trim="agentServerAddress" placeholder="远程服务器的 IP:端口号" />
            </label>
            <button class="agent-auth-primary" type="submit" :disabled="isAgentLoggingIn">
              连接远程服务器
            </button>
          </form>
        </div>
      </main>

      <main v-else-if="agentView === 'models'" class="agent-auth-page agent-selection-page">
        <div class="agent-selection-title">
          <div>
            <h3>选择大模型</h3>
            <p>选择一个已连接的模型开始诊断。</p>
          </div>
          <button class="agent-add-provider" type="button" @click="agentView = 'providers'">
            ＋ 新增
          </button>
        </div>
        <input v-model.trim="modelSearch" class="agent-search" placeholder="搜索提供商或模型" />
        <div class="agent-option-list">
          <button
            v-for="item in connectedAgentModels"
            :key="`${item.provider.id}:${item.model.id}`"
            class="agent-model-option"
            type="button"
            @click="chooseAgentModel(item.provider, item.model)"
          >
            <span>{{ item.model.name }}</span>
            <small>{{ item.provider.name }}</small>
          </button>
          <p v-if="connectedAgentModels.length === 0" class="agent-empty-options">
            没有找到已连接的模型
          </p>
        </div>
      </main>

      <main v-else-if="agentView === 'providers'" class="agent-auth-page agent-selection-page">
        <div class="agent-selection-title">
          <div>
            <h3>添加提供商</h3>
            <p>选择提供商并输入 API key。</p>
          </div>
        </div>
        <input v-model.trim="providerSearch" class="agent-search" placeholder="搜索提供商" />
        <div class="agent-option-list">
          <section
            v-for="provider in availableAgentProviders"
            :key="provider.id"
            class="agent-provider-option"
          >
            <button
              type="button"
              @click="
                expandedProviderId = expandedProviderId === provider.id ? '' : provider.id;
                providerApiKey = ''
              "
            >
              <span>{{ provider.name }}</span
              ><span>›</span>
            </button>
            <form
              v-if="expandedProviderId === provider.id"
              class="agent-api-key-form"
              @submit.prevent="authorizeAgentProvider(provider)"
            >
              <input
                v-model="providerApiKey"
                type="password"
                autocomplete="off"
                :placeholder="`${provider.name} API key`"
              />
              <button type="submit" :disabled="!providerApiKey.trim() || isAgentAuthorizing">
                {{ isAgentAuthorizing ? '认证中' : '确认' }}
              </button>
            </form>
          </section>
        </div>
      </main>

      <main v-else-if="agentView === 'new-models'" class="agent-auth-page agent-selection-page">
        <div class="agent-selection-title">
          <div>
            <h3>{{ selectedAgentProvider?.name }}</h3>
            <p>API key 已连接，请选择模型。</p>
          </div>
        </div>
        <div class="agent-option-list">
          <button
            v-for="model in newProviderModels"
            :key="model.id"
            class="agent-model-option"
            type="button"
            @click="selectedAgentProvider && chooseAgentModel(selectedAgentProvider, model)"
          >
            <span>{{ model.name }}</span>
            <small>{{ selectedAgentProvider?.name }}</small>
          </button>
        </div>
      </main>

      <div
        v-if="agentView === 'chat'"
        ref="agentChatMessagesRef"
        class="agent-chat-messages"
        aria-live="polite"
      >
        <div v-if="agentChatMessages.length === 0" class="agent-chat-welcome">
          <span class="agent-chat-welcome-icon" aria-hidden="true">✦</span>
          <strong>你好，我是故障诊断助手</strong>
          <p>可以问我当前资产库的时延异常、通断故障或故障码根因。</p>
        </div>

        <article
          v-for="message in agentChatMessages"
          :key="message.id"
          class="agent-chat-message"
          :class="message.role"
        >
          <div v-if="message.role === 'assistant'" class="agent-chat-avatar" aria-hidden="true">
            AI
          </div>
          <div class="agent-chat-bubble">
            <template v-if="message.role === 'assistant'">
              <section
                v-for="part in getAgentDisplayParts(message)"
                :key="part.id"
                :class="part.type === 'reasoning' ? 'agent-reasoning' : 'agent-final-answer'"
              >
                <template v-if="part.type === 'reasoning'">
                  <button
                    type="button"
                    class="agent-response-label agent-reasoning-toggle"
                    :aria-expanded="!part.collapsed"
                    @click="part.collapsed = !part.collapsed"
                  >
                    <span>思考过程</span>
                    <span
                      v-if="message.status === 'thinking'"
                      class="agent-thinking-dots"
                      aria-label="思考中"
                    >
                      <i></i><i></i><i></i>
                    </span>
                    <span class="agent-reasoning-chevron" aria-hidden="true">⌄</span>
                  </button>
                  <div v-show="!part.collapsed">
                    <p v-if="part.text">{{ part.text }}</p>
                    <p v-else class="agent-reasoning-placeholder">正在分析问题并查询诊断数据</p>
                  </div>
                </template>
                <div v-else class="agent-markdown" v-html="renderAgentMarkdown(part.text)"></div>
              </section>
            </template>
            <p v-else-if="message.role === 'user'">{{ message.content }}</p>
          </div>
        </article>
      </div>

      <div v-if="agentConnectionError" class="agent-chat-error" role="alert">
        {{ agentConnectionError }}
      </div>

      <form
        v-if="agentView === 'chat'"
        class="agent-chat-composer"
        @submit.prevent="sendAgentMessage"
      >
        <textarea
          v-model="agentChatInput"
          rows="1"
          aria-label="输入诊断问题"
          placeholder="输入你想诊断的问题…"
          :disabled="isAgentSending || isAgentAborting"
          @keydown.enter.exact.prevent="sendAgentMessage"
        ></textarea>
        <button
          type="submit"
          :class="{ stop: isAgentSending }"
          :aria-label="isAgentSending ? '停止本次会话' : '发送消息'"
          :title="isAgentSending ? '停止本次会话' : '发送消息'"
          :disabled="isAgentSending ? isAgentAborting : !agentChatInput.trim() || isAgentAborting"
        >
          <svg v-if="isAgentSending" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="7" y="7" width="10" height="10" rx="2" />
          </svg>
          <svg v-else viewBox="0 0 24 24" aria-hidden="true">
            <path d="m4 4 17 8-17 8 3-8-3-8Zm3.8 7h7.4L7 7.1 7.8 11Zm-.8 5.9 8.2-3.9H7.8L7 16.9Z" />
          </svg>
        </button>
      </form>
    </aside>

    <button
      v-if="isAbnormalMonitorPage"
      class="agent-fab"
      :class="{ active: isAgentChatOpen }"
      type="button"
      :aria-expanded="isAgentChatOpen"
      aria-label="打开或关闭 AI 故障诊断助手"
      title="AI 故障诊断助手"
      @click="toggleAgentChat"
    >
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <path d="M32 8v7" />
        <circle cx="32" cy="6" r="3" />
        <rect x="12" y="16" width="40" height="34" rx="12" />
        <circle cx="24" cy="31" r="3.5" />
        <circle cx="40" cy="31" r="3.5" />
        <path d="M23 41c5 4 13 4 18 0M12 29H7v11h5M52 29h5v11h-5M24 50v6M40 50v6" />
      </svg>
      <span
        v-if="!isAgentChatOpen"
        class="agent-fab-pulse"
        :class="{ disconnected: isAgentConnectionUnavailable }"
        aria-hidden="true"
      ></span>
    </button>
  </div>
</template>
