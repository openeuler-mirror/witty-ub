<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import BlockTable from '../common/BlockTable.vue'
import { useOverviewData } from '../../composables/useOverviewData'
import { useAssets } from '../../composables/useAssets'
import { useTasks } from '../../composables/useTasks'
import type { LogFileModel, LogKnowledge, LogType } from '../../types'
import {
  failureModeDisplayCode,
  formatTime,
  normalizeFaultCodes,
  normalizeTraceOperation,
} from '../../utils/format'
import LatencyOverview from './LatencyOverview.vue'
import LatencyTrend from './LatencyTrend.vue'
import DisconnectMonitor from './DisconnectMonitor.vue'
import DisconnectAggregateEvents from './DisconnectAggregateEvents.vue'
import BRPCInterfaceMonitor from './BRPCInterfaceMonitor.vue'
import BRPCFaultMonitor from './BRPCFaultMonitor.vue'
import PageNav from '../common/PageNav.vue'

const props = defineProps<{
  asset: LogKnowledge | null
  logFiles: LogFileModel[]
  logFilesAssetId?: string
  logFilesLoading?: boolean
  logFilesError?: string
}>()

const {
  bindOverviewWatchers,
  selectedAsset,
  assetTab,
  analysisModule,
  analysisTab,
  assetTypeFilter,
  brpcEventDetail,
  brpcEventDetailError,
  brpcEventDetailLoading,
  brpcEventDetailThreads,
  brpcEventDetailTimeline,
  brpcEventTimelineRef,
  brpcDetailHasParent,
  brpcFaultDetail,
  closeBrpcFaultDetail,
  brpcSelectedGraphNode,
  brpcSelectedGraphNodeId,
  brpcThreadDetail,
  brpcThreadDetailError,
  brpcThreadGraphLayout,
  brpcEventDetailThreadInterfaceColumns,
  brpcRowInterfaceCountOf,
  brpcThreadDetailLoading,
  brpcThreadLogs,
  brpcThreadLogsLoading,
  brpcThreadLogsError,
  brpcThreadTimelineRef,
  openBrpcFaultDetail,
  brpcLoading,
  brpcFaultLoading,
  brpcMonitorError,
  brpcMonitorTab,
  closeObjectDetail,
  currentOp,
  detailDrawerOpen,
  detailDrawerRow,
  failureModeOf,
  isBrpcTask,
  kpiData,
  latencyFilter,
  loadBrpcFaultData,
  objectDetail,
  objectDetailGoPage,
  objectDetailPages,
  openTraceDrawer,
  overviewError,
  overviewLoading,
  podRowTags,
  relatedFailureModeIdsOf,
  renderAnalysisModules,
  scopeTaskCount,
  scopeTasks,
  setCurrentOp,
  traceDrawerLogs,
  traceFailureModeIdsOf,
  traceStageRows,
} = useOverviewData({
  getAsset: () => props.asset,
  getLogFiles: () => props.logFiles,
  getLogFilesAssetId: () => props.logFilesAssetId ?? '',
  getLogFilesLoading: () => props.logFilesLoading ?? false,
})

bindOverviewWatchers()

// P22 数据域空态：该域没有可分析的任务时，用「去任务页面」入口替换整块空图表
const { assetTab: appAssetTab } = useAssets()
const { statusOf: taskStatusOf, statusLabel: taskStatusLabel, openCreateTask, newTask } = useTasks()

const domainLabel = computed<LogType>(() => (isBrpcTask.value ? 'UBSocket' : 'KVCache'))
const domainTasks = computed(() =>
  props.logFiles.filter((file) => file.log_type === domainLabel.value),
)
// 任务列表必须已属于当前资产库并加载完成，否则切库瞬间会把上一个库的空列表当成「没有任务」
const domainTasksLoaded = computed(
  () =>
    Boolean(props.asset) &&
    props.logFilesAssetId === props.asset?.id &&
    !props.logFilesLoading &&
    !props.logFilesError,
)
// 空态判定要「锁存」：重新进入同一个库时任务列表 id 已经匹配，首帧先判出空态；紧接着
// loadLogFiles 会把 loading 置位（domainTasksLoaded 变 false）。若继续直接依赖 domainTasksLoaded，
// 判定会被撤销、落回分析分支画 1~2 帧空图表（用户报障的闪烁）。
const settledAssetId = ref('')
const settledEmpty = ref(false)
watch(
  [domainTasksLoaded, scopeTaskCount],
  () => {
    if (!domainTasksLoaded.value) return
    settledAssetId.value = props.asset?.id ?? ''
    settledEmpty.value = scopeTaskCount.value === 0
  },
  { immediate: true },
)
const domainEmpty = computed(() => settledAssetId.value === props.asset?.id && settledEmpty.value)
// 任务列表还没到：先占位。否则会先按空 scope 画一屏空图表，再把整块换成空态（用户报障）
const domainPending = computed(
  () => Boolean(props.asset) && !props.logFilesError && settledAssetId.value !== props.asset?.id,
)
const domainEmptyTitle = computed(() =>
  domainTasks.value.length > 0
    ? `暂无可分析的 ${domainLabel.value} 任务`
    : `该资料库还没有 ${domainLabel.value} 任务`,
)
// 未完成任务的构成（如「待解析 2 · 解析中 1」），让用户知道卡在哪一步
const domainStatusSummary = computed(() => {
  const order = ['pending', 'running', 'retrying', 'failed', 'cancelled']
  const rank = (status: string) => {
    const index = order.indexOf(status)
    return index === -1 ? order.length : index
  }
  const counts = new Map<string, number>()
  domainTasks.value.forEach((file) => {
    const status = taskStatusOf(file)
    counts.set(status, (counts.get(status) ?? 0) + 1)
  })
  return [...counts.entries()]
    .sort((a, b) => rank(a[0]) - rank(b[0]))
    .map(([status, count]) => `${taskStatusLabel(status)} ${count}`)
    .join(' · ')
})
const domainEmptyHint = computed(() => {
  if (domainTasks.value.length > 0) {
    return `该资料库的 ${domainTasks.value.length} 个 ${domainLabel.value} 任务尚未完成（${domainStatusSummary.value}），任务完成后这里会显示分析结果。`
  }
  return isBrpcTask.value
    ? 'UBSocket 分析读取已完成任务的 profiling 文件与故障数据。在任务页面创建并完成一个 UBSocket 任务，这里就会显示接口监控与通断故障监控。'
    : 'KVCache 分析汇总该资料库下已完成任务的解析结果。在任务页面创建并完成一个 KVCache 任务，这里就会显示时延与通断分析。'
})

// 跳转共用同一份 App 级页签状态（useAssets 单例），本页与任务页才会真正切过去
const goTasksPage = () => {
  appAssetTab.value = 'tasks'
}

const createTaskForDomain = () => {
  openCreateTask()
  newTask.taskType = domainLabel.value
  goTasksPage()
}

const openBrpcFaultTab = () => {
  brpcMonitorTab.value = 'fault'
  void loadBrpcFaultData()
}

// P2.2：事件窗时序无任何数据点时展示空态（避免渲染空图）
const brpcEventDetailTimelineEmpty = computed(
  () =>
    !(brpcEventDetailTimeline.value ?? []).some((series: any) => (series?.points || []).length > 0),
)

// P2.3：线程运行日志按时间正序；故障模式标签优先取图节点名，再取 detail failure_modes
const sortedBrpcThreadLogs = computed(() =>
  [...brpcThreadLogs.value].sort((a, b) =>
    String(a.time ?? '').localeCompare(String(b.time ?? '')),
  ),
)
const brpcThreadTimelineEmpty = computed(
  () =>
    !(brpcThreadDetail.value?.interface_timeline ?? []).some(
      (series: any) => (series?.points || []).length > 0,
    ),
)
const brpcThreadFailureModeLabel = (id: string) =>
  brpcThreadDetail.value?.failure_graph?.nodes?.find(
    (node: any) => node.node_type === 'failure_mode' && node.node_id === id,
  )?.name ||
  brpcThreadDetail.value?.failure_modes?.find((mode: any) => mode.failure_mode_id === id)
    ?.failure_mode_name ||
  id

// 分析数据加载中：仅在页头提示，不再整块替换内容（避免切 GET/SET 时整页闪烁）
const analysisLoading = computed(
  () => overviewLoading.value || brpcLoading.value || brpcFaultLoading.value,
)
const selectBrpcGraphNode = (id: string) => {
  brpcSelectedGraphNodeId.value = brpcSelectedGraphNodeId.value === id ? '' : id
}

const onKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Escape') return
  closeObjectDetail()
  detailDrawerOpen.value = false
  closeBrpcFaultDetail()
}

// 抽屉故障码：access 口径数组 + 故障模式知识库显示码（含 FATAL 回退），去重
const drawerFaultCodes = (row: any) => {
  const codes = normalizeFaultCodes(row?.status_code)
  const modeCode = failureModeDisplayCode(primaryFailureMode.value)
  if (modeCode && !codes.includes(modeCode)) codes.push(modeCode)
  return codes
}

// P1.2：主模式优先取 trace 行 failure_mode，KVCache 行无该字段时回退命中集合第一个
const primaryFailureMode = computed(() => {
  const row = detailDrawerRow.value
  const primaryId =
    String(row?.failure_mode ?? '')
      .split(',')[0]
      ?.trim() || traceFailureModeIdsOf(row)[0]
  return primaryId ? failureModeOf(primaryId) : null
})

// P1.2：相关故障折叠列表（默认收起，切换 trace 时重置）
const relatedFaultsOpen = ref(false)
const relatedFaultIds = computed(() => relatedFailureModeIdsOf(detailDrawerRow.value))
watch(
  () => detailDrawerRow.value?.trace_id,
  () => {
    relatedFaultsOpen.value = false
  },
)
const relatedFaultCodes = (id: string) => {
  const code = failureModeDisplayCode(failureModeOf(id))
  return code ? [code] : []
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  renderAnalysisModules()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <!-- ====== 总览 ====== -->
  <template v-if="assetTab === 'overview'">
    <div v-if="overviewError" class="error-banner">{{ overviewError }}</div>

    <header class="analysis-shell-header">
      <div class="analysis-heading">
        <span class="analysis-eyebrow">当前资产</span>
        <h1>{{ selectedAsset?.name }}</h1>
        <p>选择数据域后，按日志与操作类型查看诊断结果。</p>
      </div>
      <div class="domain-switch">
        <span>数据域</span>
        <div class="context-tabs" role="tablist" aria-label="分析数据域">
          <button
            type="button"
            role="tab"
            :aria-selected="assetTypeFilter === 'kvcache'"
            :class="['context-tab', { active: assetTypeFilter === 'kvcache' }]"
            @click="assetTypeFilter = 'kvcache'"
          >
            KVCache
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="assetTypeFilter === 'brpc'"
            :class="['context-tab', { active: assetTypeFilter === 'brpc' }]"
            @click="assetTypeFilter = 'brpc'"
          >
            UBSocket
          </button>
        </div>
      </div>
    </header>

    <!-- 任务列表未到：先占位，避免「先画一屏空图表、再切空态」的闪烁 -->
    <section
      v-if="domainPending"
      class="domain-empty domain-empty-loading"
      aria-busy="true"
      aria-live="polite"
    >
      <div class="domain-empty-icon" aria-hidden="true">⏳</div>
      <h2>正在加载任务列表…</h2>
      <p>确认该资料库有没有 {{ domainLabel }} 任务后，这里会显示分析结果或跳转入口。</p>
    </section>

    <!-- 空态：该数据域没有可分析的任务，直接给出跳转入口，不渲染大块空图表 -->
    <section v-else-if="domainEmpty" class="domain-empty" aria-live="polite">
      <div class="domain-empty-icon" aria-hidden="true">📭</div>
      <h2>{{ domainEmptyTitle }}</h2>
      <p>{{ domainEmptyHint }}</p>
      <div class="domain-empty-actions">
        <button class="btn btn-primary" type="button" @click="goTasksPage">前往任务页面 →</button>
        <button
          v-if="domainTasks.length === 0"
          class="btn btn-default"
          type="button"
          @click="createTaskForDomain"
        >
          创建 {{ domainLabel }} 任务
        </button>
      </div>
    </section>

    <template v-else>
      <div class="analysis-scope-bar">
        <div class="analysis-scope-summary">
          <strong>{{ domainLabel }} 分析</strong>
          <span>
            共 {{ scopeTaskCount }} 个已完成 {{ domainLabel }} 任务 ·
            {{
              !isBrpcTask && analysisTab === 'latency' && latencyFilter.logId.value
                ? '单日志文件'
                : '跨任务汇总'
            }}
          </span>
          <span v-if="analysisLoading" class="analysis-loading-chip" role="status">
            <span class="analysis-loading-dot" aria-hidden="true"></span>正在加载分析数据…
          </span>
        </div>
        <div v-if="!isBrpcTask" class="scope-controls">
          <template v-if="!isBrpcTask">
            <template v-if="analysisTab === 'latency'">
              <label class="scope-field">
                <span>日志文件</span>
                <select
                  class="select"
                  v-model="latencyFilter.logId.value"
                  :disabled="scopeTasks.length === 0"
                >
                  <option :value="undefined">全部已完成 KVCache 任务</option>
                  <option v-for="file in scopeTasks" :key="file.id" :value="file.id">
                    {{ file.name || file.id }}
                  </option>
                </select>
              </label>
            </template>
            <div class="scope-field">
              <span>操作类型</span>
              <div class="op-toggle" role="group" aria-label="操作类型">
                <button
                  type="button"
                  :class="['op-btn', { active: currentOp === 'GET' }]"
                  @click="setCurrentOp('GET')"
                >
                  GET
                </button>
                <button
                  type="button"
                  :class="['op-btn', { active: currentOp === 'SET' }]"
                  @click="setCurrentOp('SET')"
                >
                  SET
                </button>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div v-if="!isBrpcTask" class="analysis-tabs" role="tablist" aria-label="分析类型">
        <button
          type="button"
          role="tab"
          :aria-selected="analysisTab === 'latency'"
          :class="['analysis-tab', { active: analysisTab === 'latency' }]"
          @click="analysisTab = 'latency'"
        >
          时延故障监控
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="analysisTab === 'disconnect'"
          :class="['analysis-tab', { active: analysisTab === 'disconnect' }]"
          @click="analysisTab = 'disconnect'"
        >
          通断故障监控
        </button>
      </div>

      <!-- 加载中不再整体替换内容：切 GET/SET 或切数据域时只提示，不清空已渲染的图与指标，
         避免整页闪烁 -->
      <div v-if="!isBrpcTask" class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-num">{{ kpiData.totalTraces.toLocaleString() }}</div>
          <div class="kpi-label">
            {{ analysisTab === 'disconnect' ? '通断/故障 Trace 数' : '总 Trace 数' }}
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-num" style="color: var(--danger)">
            {{ kpiData.anomalyTraces.toLocaleString() }}
          </div>
          <div class="kpi-label">
            {{ analysisTab === 'disconnect' ? '故障码数' : '异常 Trace 数' }}
          </div>
        </div>
        <div class="kpi-card">
          <div
            class="kpi-num"
            :style="{
              color:
                analysisTab === 'disconnect'
                  ? 'var(--danger)'
                  : Number(kpiData.anomalyRate) > 5
                    ? 'var(--danger)'
                    : Number(kpiData.anomalyRate) > 1
                      ? 'var(--warning)'
                      : 'var(--success)',
            }"
          >
            {{ analysisTab === 'disconnect' ? kpiData.linkCount : kpiData.anomalyRate + '%' }}
          </div>
          <div class="kpi-label">
            {{ analysisTab === 'disconnect' ? '受影响链路数' : '异常率' }}
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-num">{{ kpiData.endpointCount }}</div>
          <div class="kpi-label">
            {{ analysisTab === 'disconnect' ? '故障端点数' : '当前范围端点数' }}
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-num" style="font-size: 15px; color: var(--danger)">
            {{ kpiData.worstEndpoint }}
          </div>
          <div class="kpi-label">
            {{
              analysisTab === 'disconnect'
                ? '故障最多端点 · ' + kpiData.worstEndpointAnomaly + ' 次'
                : '当前范围最差端点 · 异常 ' + kpiData.worstEndpointAnomaly
            }}
          </div>
        </div>
      </div>

      <!-- ===== 时延故障监控 ===== -->
      <template v-if="!isBrpcTask && analysisTab === 'latency'">
        <div class="view-tabs" role="tablist" aria-label="时延分析视图">
          <button
            type="button"
            role="tab"
            :aria-selected="analysisModule.latency === 'overview'"
            :class="['view-tab', { active: analysisModule.latency === 'overview' }]"
            @click="analysisModule.latency = 'overview'"
          >
            Pod 分析
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="analysisModule.latency === 'trend'"
            :class="['view-tab', { active: analysisModule.latency === 'trend' }]"
            @click="analysisModule.latency = 'trend'"
          >
            指标趋势与异常分析
          </button>
        </div>

        <LatencyOverview v-if="analysisModule.latency === 'overview'" />
        <LatencyTrend v-if="analysisModule.latency === 'trend'" />
      </template>

      <!-- ===== 通断故障监控 ===== -->
      <template v-else-if="!isBrpcTask">
        <div class="view-tabs" role="tablist" aria-label="通断分析视图">
          <button
            type="button"
            role="tab"
            :aria-selected="analysisModule.disconnect === 'faults'"
            :class="['view-tab', { active: analysisModule.disconnect === 'faults' }]"
            @click="analysisModule.disconnect = 'faults'"
          >
            故障诊断
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="analysisModule.disconnect === 'events'"
            :class="['view-tab', { active: analysisModule.disconnect === 'events' }]"
            @click="analysisModule.disconnect = 'events'"
          >
            聚合事件
          </button>
        </div>
        <DisconnectMonitor v-if="analysisModule.disconnect === 'faults'" />
        <DisconnectAggregateEvents v-else />
      </template>

      <!-- ===== UBSocket 监控 ===== -->
      <template v-else>
        <div v-if="brpcMonitorError" class="error-banner">{{ brpcMonitorError }}</div>
        <div class="analysis-tabs" role="tablist" aria-label="UBSocket 分析类型">
          <button
            type="button"
            role="tab"
            :aria-selected="brpcMonitorTab === 'iface'"
            :class="['analysis-tab', { active: brpcMonitorTab === 'iface' }]"
            @click="brpcMonitorTab = 'iface'"
          >
            接口监控
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="brpcMonitorTab === 'fault'"
            :class="['analysis-tab', { active: brpcMonitorTab === 'fault' }]"
            @click="openBrpcFaultTab"
          >
            通断故障监控
          </button>
        </div>

        <BRPCInterfaceMonitor v-if="brpcMonitorTab === 'iface'" />
        <BRPCFaultMonitor v-if="brpcMonitorTab === 'fault'" />
      </template>
    </template>
  </template>

  <!-- ============ UBSocket 事件 / Thread 详情弹窗 ============ -->
  <div class="modal-overlay" v-if="brpcFaultDetail" @click.self="closeBrpcFaultDetail()">
    <div class="modal modal-xl">
      <div class="modal-header">
        <span class="modal-header-main">
          <button
            v-if="brpcDetailHasParent"
            class="modal-back"
            type="button"
            aria-label="返回上层详情"
            @click="closeBrpcFaultDetail()"
          >
            ‹ 返回
          </button>
          <span>{{ brpcFaultDetail.thread_key ? 'Thread 接口命中明细' : '聚合事件详情' }}</span>
          <span v-if="brpcDetailHasParent" class="modal-header-crumb">来自 聚合事件详情</span>
        </span>
        <button class="modal-close" @click="closeBrpcFaultDetail()">✕</button>
      </div>
      <div class="modal-body modal-scroll">
        <div style="font-size: 13px; color: var(--text2); margin-bottom: 12px">
          <template v-if="brpcFaultDetail.thread_key">
            线程: <b style="color: var(--text)">{{ brpcFaultDetail.thread_key }}</b> · Pod:
            <b style="color: var(--text)">{{ brpcFaultDetail.pod_ip }}</b>
          </template>
          <template v-else>
            窗口:
            <b style="color: var(--text)"
              >{{ brpcFaultDetail.window_start_time }} ~ {{ brpcFaultDetail.window_end_time }}</b
            >
            · Pod: <b style="color: var(--text)">{{ brpcFaultDetail.pod_ip }}</b>
          </template>
        </div>

        <!-- P2.2 聚合事件详情：组件计数 / 当前窗时序 / 关联线程 -->
        <template v-if="!brpcFaultDetail.thread_key">
          <div v-if="brpcEventDetailError" class="error-banner">{{ brpcEventDetailError }}</div>
          <div v-if="brpcEventDetailLoading" class="empty" style="padding: 20px 0">
            <div class="icon">⏳</div>
            <div>正在加载事件详情...</div>
          </div>
          <template v-else>
            <div style="font-weight: 600; font-size: 13px; margin: 4px 0 8px">
              组件计数（共 {{ brpcEventDetail?.hit_total ?? 0 }} 次命中）
            </div>
            <div
              v-if="!brpcEventDetail?.failure_modes?.length"
              class="empty"
              style="padding: 12px 0"
            >
              暂无组件计数
            </div>
            <div v-else class="table-wrap" style="margin-bottom: 16px">
              <table>
                <thead>
                  <tr>
                    <th>组件</th>
                    <th>故障模式</th>
                    <th>命中数</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="mode in brpcEventDetail.failure_modes"
                    :key="mode.failure_mode_id + ':' + mode.component"
                  >
                    <td>{{ mode.component || '-' }}</td>
                    <td style="font-size: 12px">{{ mode.failure_mode_name || '-' }}</td>
                    <td>{{ mode.hit_count }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div style="font-weight: 600; font-size: 13px; margin: 4px 0 8px">当前窗故障时序</div>
            <div v-if="brpcEventDetailTimelineEmpty" class="empty" style="padding: 12px 0">
              当前窗内无故障时序数据
            </div>
            <div
              v-if="!brpcEventDetailTimelineEmpty"
              ref="brpcEventTimelineRef"
              style="height: 280px; margin-bottom: 16px"
            ></div>

            <div style="font-weight: 600; font-size: 13px; margin: 4px 0 8px">
              关联异常 Thread（{{ brpcEventDetailThreads.length }}）
            </div>
            <div v-if="brpcEventDetailThreads.length === 0" class="empty" style="padding: 12px 0">
              当前窗内无异常 Thread
            </div>
            <div v-else class="table-wrap" style="margin-bottom: 16px">
              <BlockTable
                :rows="brpcEventDetailThreads"
                :row-key="(row: any) => row.thread_key"
                :left-cols="['110px', '130px', '150px', '96px']"
                :mid-width="brpcEventDetailThreadInterfaceColumns.length * 132 + 'px'"
              >
                <template #left-head>
                  <span class="col-nowrap">线程ID</span>
                  <span class="col-nowrap">Pod IP</span>
                  <span class="col-nowrap">Pod 名称</span>
                  <span class="col-num">命中数</span>
                </template>
                <template #left="{ row: thread }">
                  <span class="col-nowrap">
                    <span class="thread-id-pill" :title="thread.thread_key">{{
                      thread.thread_id
                    }}</span>
                  </span>
                  <span class="col-nowrap agg-mono">{{ thread.pod_ip }}</span>
                  <span class="col-nowrap">{{ thread.pod_name || '-' }}</span>
                  <span class="col-num">{{ thread.total_interface_hit_count }}</span>
                </template>
                <template #mid-head>
                  <div
                    v-for="column in brpcEventDetailThreadInterfaceColumns"
                    :key="column.id"
                    class="col-num matrix-head-cell"
                    :title="`${column.component} / ${column.interfaceName} / ${column.functionName}`"
                  >
                    <small class="matrix-head-component">{{ column.component }}</small>
                    <span class="matrix-head-name">{{ column.interfaceName }}</span>
                    <code class="matrix-head-function">{{ column.functionName }}</code>
                  </div>
                </template>
                <template #mid="{ row: thread }">
                  <div
                    v-for="column in brpcEventDetailThreadInterfaceColumns"
                    :key="column.id"
                    class="col-num"
                  >
                    <span :class="{ 'matrix-zero': !brpcRowInterfaceCountOf(thread, column.id) }">
                      {{ brpcRowInterfaceCountOf(thread, column.id) || '-' }}
                    </span>
                  </div>
                </template>
                <template #right-head>操作</template>
                <template #right="{ row: thread }">
                  <button class="btn btn-sm btn-primary" @click="openBrpcFaultDetail(thread, true)">
                    详情
                  </button>
                </template>
              </BlockTable>
            </div>
          </template>
        </template>

        <div style="font-weight: 600; font-size: 13px; margin: 4px 0 8px">接口命中</div>
        <div
          v-if="!brpcFaultDetail.interface_hits || brpcFaultDetail.interface_hits.length === 0"
          class="empty"
          style="padding: 24px 0"
        >
          暂无接口命中
        </div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>接口</th>
                <th>组件</th>
                <th>函数</th>
                <th>命中数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="hit in brpcFaultDetail.interface_hits" :key="hit.interface_id">
                <td style="font-family: monospace; font-size: 12px">{{ hit.interface_name }}</td>
                <td>{{ hit.component || '-' }}</td>
                <td style="font-family: monospace; font-size: 12px">
                  {{ hit.function_name || '-' }}
                </td>
                <td>{{ hit.interface_hit_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <template v-if="brpcFaultDetail.thread_key">
          <!-- P2.3：故障模式视图（failure_graph） -->
          <div style="font-weight: 600; font-size: 13px; margin: 16px 0 8px">
            故障模式视图
            <span class="graph-legend" aria-label="故障模式视图图例">
              <span><i class="graph-legend-interface"></i>接口节点</span>
              <span><i class="graph-legend-mode"></i>故障模式节点</span>
              <span><i class="graph-legend-edge"></i>组件内关系</span>
              <span><i class="graph-legend-edge cross"></i>跨组件关系</span>
              <span class="hint" style="font-weight: 400"
                >粗边框=直接命中；可拖拽/缩放，点击节点查看详情</span
              >
            </span>
          </div>
          <div v-if="brpcThreadDetailLoading" class="empty" style="padding: 16px 0">
            正在加载故障模式视图...
          </div>
          <div v-else-if="brpcThreadDetailError" class="error-banner">
            {{ brpcThreadDetailError }}
          </div>
          <div
            v-else-if="!brpcThreadDetail?.failure_graph?.nodes?.length"
            class="empty"
            style="padding: 16px 0"
          >
            当前 Thread 暂无命中的故障模式子图
          </div>
          <div v-else class="graph-viewport">
            <div
              class="graph-canvas"
              :style="{
                width: (brpcThreadGraphLayout?.width ?? 720) + 'px',
                height: (brpcThreadGraphLayout?.height ?? 320) + 'px',
              }"
            >
              <svg
                class="graph-edges"
                :width="brpcThreadGraphLayout?.width ?? 720"
                :height="brpcThreadGraphLayout?.height ?? 320"
              >
                <defs>
                  <marker
                    id="brpc-graph-arrow"
                    viewBox="0 0 10 10"
                    refX="9"
                    refY="5"
                    markerWidth="7"
                    markerHeight="7"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
                  </marker>
                  <marker
                    id="brpc-graph-arrow-cross"
                    viewBox="0 0 10 10"
                    refX="9"
                    refY="5"
                    markerWidth="7"
                    markerHeight="7"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                  </marker>
                </defs>
                <path
                  v-for="link in brpcThreadGraphLayout?.links ?? []"
                  :key="link.id"
                  :d="link.d"
                  :class="['graph-edge', { 'graph-edge-cross': link.cross }]"
                  :marker-end="
                    link.cross ? 'url(#brpc-graph-arrow-cross)' : 'url(#brpc-graph-arrow)'
                  "
                />
              </svg>
              <button
                v-for="node in brpcThreadGraphLayout?.nodes ?? []"
                :key="node.id"
                type="button"
                :class="[
                  'graph-node',
                  node.nodeType === 'interface' ? 'graph-node-interface' : 'graph-node-mode',
                  { active: brpcSelectedGraphNodeId === node.id, hit: node.directlyHit },
                ]"
                :style="{
                  left: node.x + 'px',
                  top: node.y + 'px',
                  width: node.width + 'px',
                  height: node.height + 'px',
                }"
                :title="
                  node.nodeType === 'interface'
                    ? `${node.name}${node.functionName ? ' / ' + node.functionName : ''}`
                    : `${node.name}（命中 ${node.hitCount} 次）`
                "
                @click="
                  brpcSelectedGraphNodeId = brpcSelectedGraphNodeId === node.id ? '' : node.id
                "
              >
                <span class="graph-node-id">
                  <span
                    v-for="(line, index) in node.idLines"
                    :key="`id-${index}`"
                    class="graph-node-line"
                    >{{ line }}</span
                  >
                </span>
                <span class="graph-node-name">
                  <span
                    v-for="(line, index) in node.nameLines"
                    :key="`name-${index}`"
                    class="graph-node-line"
                    >{{ line }}</span
                  >
                </span>
                <span
                  :class="[
                    'graph-node-tail',
                    node.nodeType === 'interface' ? 'graph-node-fn' : 'graph-node-count',
                  ]"
                >
                  <span
                    v-for="(line, index) in node.nodeType === 'interface'
                      ? node.tailLines
                      : [`命中 ${node.hitCount}`]"
                    :key="`tail-${index}`"
                    class="graph-node-line"
                    >{{ line }}</span
                  >
                </span>
              </button>
            </div>
          </div>

          <!-- P2.3：选中节点详情 -->
          <div
            v-if="brpcSelectedGraphNode"
            style="
              border: 1px solid #fecaca;
              background: #fef2f2;
              border-radius: 4px;
              padding: 10px 12px;
              margin-bottom: 12px;
            "
          >
            <div style="font-weight: 600; color: var(--danger); margin-bottom: 4px">
              {{ brpcSelectedGraphNode.name || brpcSelectedGraphNode.node_id }}
              <span
                v-if="brpcSelectedGraphNode.node_type === 'failure_mode'"
                class="fault-code-chip"
              >
                命中 {{ brpcSelectedGraphNode.hit_count ?? 0 }}
              </span>
              <span
                v-if="
                  brpcSelectedGraphNode.error_code != null &&
                  brpcSelectedGraphNode.error_code !== ''
                "
                class="fault-code-chip"
              >
                故障码 {{ brpcSelectedGraphNode.error_code }}
              </span>
            </div>
            <div style="font-size: 12px; color: var(--text2); line-height: 1.7">
              <template v-if="brpcSelectedGraphNode.node_type === 'failure_mode'">
                症状：{{ brpcSelectedGraphNode.phenomenon || '-' }}<br />
                根因：{{ brpcSelectedGraphNode.cause || '-' }}<br />
                解决：{{ brpcSelectedGraphNode.solution || '-' }}
              </template>
              <template v-else>
                组件：{{ brpcSelectedGraphNode.component || '-' }} · 函数：{{
                  brpcSelectedGraphNode.function_name || '-'
                }}
                · 文件：{{ brpcSelectedGraphNode.filename || '-' }}
              </template>
            </div>
          </div>

          <!-- P2.3：接口命中时序 -->
          <div style="font-weight: 600; font-size: 13px; margin: 12px 0 8px">接口命中时序</div>
          <div v-if="brpcThreadTimelineEmpty" class="empty" style="padding: 12px 0">
            暂无接口命中时序数据
          </div>
          <div
            v-if="!brpcThreadTimelineEmpty"
            ref="brpcThreadTimelineRef"
            style="height: 280px; margin-bottom: 8px"
          ></div>

          <!-- P2.3：完整运行日志列，故障行高亮 -->
          <div style="font-weight: 600; font-size: 13px; margin: 16px 0 8px">
            运行日志（{{ brpcThreadLogs.length }} 条）
          </div>
          <div v-if="brpcThreadLogsLoading" class="empty" style="padding: 16px 0">
            正在加载运行日志...
          </div>
          <div v-else-if="brpcThreadLogsError" class="error-banner">{{ brpcThreadLogsError }}</div>
          <div v-else-if="brpcThreadLogs.length === 0" class="empty" style="padding: 16px 0">
            暂无运行日志
          </div>
          <div v-else class="table-wrap" style="max-height: 360px; overflow-y: auto">
            <table style="min-width: 1080px">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>Pod IP</th>
                  <th>Pod 名称</th>
                  <th>组件</th>
                  <th>文件</th>
                  <th>函数</th>
                  <th>行号</th>
                  <th>日志正文</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(log, index) in sortedBrpcThreadLogs"
                  :key="log.hit_id || index"
                  :style="log.failure_mode_id ? 'background: #fef2f2' : ''"
                >
                  <td style="font-size: 11px; font-family: monospace; white-space: nowrap">
                    {{ (log.time || '').slice(0, 23) }}
                  </td>
                  <td style="font-size: 11px; font-family: monospace">{{ log.pod_ip || '-' }}</td>
                  <td style="font-size: 11px">{{ log.pod_name || '-' }}</td>
                  <td style="font-size: 11px">{{ log.component || '-' }}</td>
                  <td style="font-size: 11px; font-family: monospace">{{ log.filename || '-' }}</td>
                  <td style="font-size: 11px; font-family: monospace">
                    {{ log.function_name || '-' }}
                  </td>
                  <td style="font-size: 11px">{{ log.line_number ?? '-' }}</td>
                  <td style="white-space: normal; font-size: 12px">
                    {{ log.message || '-' }}
                    <button
                      v-if="log.failure_mode_id"
                      type="button"
                      class="fault-code-chip"
                      style="cursor: pointer; margin-left: 4px"
                      :title="'定位故障模式节点：' + log.failure_mode_id"
                      @click="selectBrpcGraphNode(log.failure_mode_id)"
                    >
                      {{ brpcThreadFailureModeLabel(log.failure_mode_id) }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>
  </div>

  <!-- ============ 对象详情弹窗（窗 × 端点/链路，服务端分页） ============ -->
  <div class="modal-overlay" v-if="objectDetail.open" @click.self="closeObjectDetail">
    <div class="modal modal-xl">
      <div class="modal-header">
        {{ objectDetail.title }} · {{ objectDetail.windowLabel }}
        <button class="modal-close" @click="closeObjectDetail">✕</button>
      </div>
      <div class="modal-body" style="overflow-y: auto; flex: 1; min-height: 0">
        <div style="margin-bottom: 12px; display: flex; gap: 8px; flex-wrap: wrap">
          <span class="stat-pill"
            >异常 Trace <b>{{ objectDetail.total }}</b></span
          >
          <span class="stat-pill">{{
            objectDetail.domain === 'latency' ? '时延异常口径' : '通断故障口径'
          }}</span>
        </div>
        <div v-if="objectDetail.error" class="error-banner">{{ objectDetail.error }}</div>
        <div v-else-if="objectDetail.loading" class="empty" style="padding: 28px 0">
          <div class="icon">⏳</div>
          <div>正在加载 Trace...</div>
        </div>
        <div v-else-if="objectDetail.rows.length === 0" class="empty" style="padding: 28px 0">
          <div class="icon">📭</div>
          <div>当前时段 × 对象没有异常 Trace</div>
        </div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>Trace ID</th>
                <th>源 IP</th>
                <th>目标 IP</th>
                <th>类型</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in objectDetail.rows" :key="row.trace_id || row.id">
                <td style="font-size: 12px; font-family: monospace">
                  {{ (row.timestamp || '').slice(0, 19) }}
                </td>
                <td>
                  <span class="trace-chip">{{ row.trace_id }}</span>
                </td>
                <td style="font-family: monospace">{{ row.src_ip || '-' }}</td>
                <td style="font-family: monospace">{{ row.dst_ip || '-' }}</td>
                <td>
                  <div class="task-actions">
                    <span
                      v-for="tag in podRowTags(row)"
                      :key="tag.type"
                      :class="['badge', tag.type === 'fault' ? 'badge-failed' : 'badge-warning']"
                      >{{ tag.label }}</span
                    >
                  </div>
                </td>
                <td>
                  <button class="btn btn-sm btn-primary" @click="openTraceDrawer(row)">
                    查看 Trace 详情
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div
          style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 12px;
          "
          v-if="objectDetailPages > 1"
        >
          <span style="font-size: 13px; color: var(--text2)"
            >共 {{ objectDetail.total }} 条 · 第 {{ objectDetail.page }} /
            {{ objectDetailPages }} 页</span
          >
          <PageNav
            :page="objectDetail.page"
            :pages="objectDetailPages"
            @update:page="objectDetailGoPage($event)"
          />
        </div>
      </div>
    </div>
  </div>

  <!-- ============ Trace 链路抽屉 ============ -->
  <div
    class="detail-drawer-mask"
    :class="{ show: detailDrawerOpen }"
    @click="detailDrawerOpen = false"
  ></div>
  <div
    class="detail-drawer"
    :class="{ open: detailDrawerOpen }"
    :aria-hidden="!detailDrawerOpen"
    :inert="!detailDrawerOpen"
  >
    <div class="modal-header">
      <span class="modal-header-main">
        {{ detailDrawerRow ? 'Trace：' + detailDrawerRow.trace_id : '日志详情' }}
      </span>
      <button class="modal-close" @click="detailDrawerOpen = false">✕</button>
    </div>
    <div class="modal-scroll" style="padding: 20px 24px">
      <div v-if="detailDrawerRow">
        <div style="font-size: 13px; color: var(--text2); margin-bottom: 12px; line-height: 1.9">
          时间:
          <b style="color: var(--text)">{{ (detailDrawerRow.timestamp || '').slice(0, 19) }}</b
          ><br />
          操作:
          <span
            :class="
              String(detailDrawerRow.operation || '')
                .toUpperCase()
                .includes('SET')
                ? 'badge action-badge-set'
                : 'badge action-badge-get'
            "
          >
            {{ normalizeTraceOperation(detailDrawerRow.operation) }}
          </span>
          &nbsp;·&nbsp; 总时延:
          <b style="color: var(--danger)"
            >{{
              (
                Number(detailDrawerRow.total_latency) ||
                Number(detailDrawerRow.total_latency_us) / 1000 ||
                0
              ).toFixed(3)
            }}
            ms</b
          >
          <span
            v-if="
              detailDrawerRow.is_anomalous ||
              normalizeFaultCodes(detailDrawerRow.status_code).length > 0
            "
            class="badge badge-anomaly"
            style="margin-left: 8px"
            >异常</span
          >
        </div>

        <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px">
          运行日志（{{ traceDrawerLogs.length }} 条）
        </div>
        <div class="table-wrap" style="margin-bottom: 16px">
          <table class="log-table" style="min-width: 1100px">
            <thead>
              <tr>
                <th>Time</th>
                <th>level</th>
                <th>filename</th>
                <th>pod_name</th>
                <th>pid:tid</th>
                <th>cluster_name</th>
                <th>message</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(log, index) in traceDrawerLogs" :key="index">
                <td style="font-size: 11px; font-family: monospace">
                  {{ (log.timestamp || '').slice(0, 23) }}
                </td>
                <td>{{ log.level }}</td>
                <td style="font-size: 11px; font-family: monospace">{{ log.filename || '-' }}</td>
                <td style="font-family: monospace">{{ log.pod_name || '-' }}</td>
                <td>{{ log.pid && log.tid ? log.pid + ':' + log.tid : '-' }}</td>
                <td>{{ log.cluster_name || '-' }}</td>
                <td style="white-space: normal; font-size: 12px">{{ log.message || '-' }}</td>
              </tr>
              <tr v-if="traceDrawerLogs.length === 0">
                <td colspan="7" style="text-align: center; color: var(--text3)">
                  该 Trace 暂无运行日志
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px">故障模式详情</div>
        <div
          v-if="primaryFailureMode"
          style="
            border: 1px solid #fecaca;
            background: #fef2f2;
            border-radius: 4px;
            padding: 10px 12px;
            margin-bottom: 16px;
          "
        >
          <div style="font-weight: 600; color: var(--danger); margin-bottom: 4px">
            {{ primaryFailureMode.name }}
            <span
              v-for="code in drawerFaultCodes(detailDrawerRow)"
              :key="code"
              class="fault-code-chip"
              >故障码 {{ code }}</span
            >
          </div>
          <div style="font-size: 12px; color: var(--text2); line-height: 1.7">
            症状：{{ primaryFailureMode.symptom }}<br />
            根因：{{ primaryFailureMode.root_cause }}<br />
            解决：{{ primaryFailureMode.solution }}
          </div>
        </div>
        <div
          v-else
          style="
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 10px 12px;
            margin-bottom: 16px;
            color: var(--text3);
            font-size: 13px;
          "
        >
          暂无故障模式
        </div>

        <div
          style="
            font-weight: 600;
            font-size: 13px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
          "
        >
          相关故障（{{ relatedFaultIds.length }}）
          <button
            v-if="relatedFaultIds.length > 0"
            class="btn btn-text btn-sm"
            @click="relatedFaultsOpen = !relatedFaultsOpen"
          >
            {{ relatedFaultsOpen ? '收起' : '展开' }}
          </button>
        </div>
        <div
          v-if="relatedFaultIds.length === 0"
          style="color: var(--text3); font-size: 13px; margin-bottom: 16px"
        >
          暂无相关故障
        </div>
        <template v-else-if="relatedFaultsOpen">
          <div
            v-for="id in relatedFaultIds"
            :key="id"
            style="
              border: 1px solid var(--border);
              border-radius: 4px;
              padding: 10px 12px;
              margin-bottom: 8px;
              font-size: 12px;
            "
          >
            <div style="font-weight: 600; margin-bottom: 4px">
              {{ failureModeOf(id)?.name || id }}
              <span v-for="code in relatedFaultCodes(id)" :key="code" class="fault-code-chip"
                >故障码 {{ code }}</span
              >
            </div>
            <div style="color: var(--text2); line-height: 1.7">
              症状：{{ failureModeOf(id)?.symptom || '-' }}<br />
              根因：{{ failureModeOf(id)?.root_cause || '-' }}<br />
              解决：{{ failureModeOf(id)?.solution || '-' }}
            </div>
          </div>
        </template>

        <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px">时延明细</div>
        <div class="table-wrap" style="margin-bottom: 8px">
          <table>
            <thead>
              <tr>
                <th>阶段</th>
                <th>时延</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="stage in traceStageRows(detailDrawerRow)" :key="stage.name">
                <td>{{ stage.name }}</td>
                <td>
                  {{ stage.value == null ? '未解析' : Number(stage.value).toFixed(3) + ' ms' }}
                </td>
                <td>
                  <span
                    :class="
                      stage.status === '异常'
                        ? 'badge badge-anomaly'
                        : stage.status === '正常'
                          ? 'badge badge-normal'
                          : 'badge badge-pending'
                    "
                  >
                    {{ stage.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@media (max-width: 768px) {
  .detail-drawer {
    width: 100vw;
    height: 100vh;
    border-radius: 0;
  }
}
</style>
