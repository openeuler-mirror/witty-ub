<script setup lang="ts">
import { onMounted } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'
import { formatTime, normalizeTraceOperation } from '../../utils/format'

const {
  toast,
  selectedAsset,
  view,
  assetTab,
  pieRefs,
  ipRowRefs,
  activePairs,
  addTraceBoard,
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
  getAdaptiveBucketMs,
  getChart,
  goBrpcFaultEventsPage,
  goBrpcFaultThreadsPage,
  hasRealData,
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
  pagedPodDetailRows,
  pagedPodIpsCb,
  pagedPodStats,
  pagedTraceRows,
  podDetailIp,
  podDetailOpen,
  podDetailPage,
  podDetailPageSize,
  podDetailPages,
  podDetailRows,
  podDetailSearch,
  podDetailSummary,
  podIpCbPage,
  podIpCbPageSize,
  podIpCbPages,
  podIpStats,
  podPage,
  podPageSize,
  podPages,
  realOp,
  removeTraceBoard,
  renderAnalysisModules,
  renderBrpcCharts,
  renderBrpcFaultTimeline,
  renderFaultChart,
  renderFaultPodChart,
  renderPieCharts,
  renderSlowChart,
  renderTopology,
  renderTrendChart,
  resetOverviewFilter,
  resetTrend,
  resolveBrpcFaultBatch,
  scopeData,
  scopeTaskCount,
  scopeTasks,
  selectAllTrend,
  selectedMetrics,
  selectedPodIps,
  setChartOption,
  setCurrentOp,
  showMetricCb,
  showPodIpCb,
  slowChartRows,
  slowRef,
  slowRows,
  slowTotal,
  toAggregatedPairs,
  toggleTrendSeries,
  topSlowSegmentConfig,
  topoRef,
  traceBoard,
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
} = useOverviewData()

onMounted(() => {
  renderBrpcFaultTimeline()
})
</script>

<template>
  <div v-if="brpcFaultError" class="error-banner">{{ brpcFaultError }}</div>
  <div class="operate-bar" v-if="brpcFaultLogOptions.length > 0">
    <div style="display: flex; align-items: center; gap: 8px">
      <span style="font-size: 13px; color: var(--text2)">UBSocket 日志:</span>
      <select class="select" v-model="brpcFaultSelectedLogId" @change="changeBrpcFaultLog">
        <option v-for="option in brpcFaultLogOptions" :key="option.id" :value="option.id">
          {{ option.name }}
        </option>
      </select>
    </div>
  </div>
  <div v-if="brpcFaultLoading" class="empty" style="padding: 28px 0">
    <div class="icon">⏳</div>
    <div>正在加载 UBSocket 故障监控数据...</div>
  </div>
  <div v-else-if="brpcFaultLogOptions.length === 0" class="empty" style="padding: 36px 0">
    <div class="icon">📭</div>
    <div>暂无已运行 UBSocket 诊断的日志</div>
    <div class="hint">在任务管理中创建 UBSocket 任务并运行诊断后，可在此查看通断故障监控</div>
  </div>
  <template v-else>
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-num">{{ brpcFaultBatch?.hit_count ?? 0 }}</div>
        <div class="kpi-label">诊断命中数</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num">{{ brpcAggregatedEventTotal }}</div>
        <div class="kpi-label">聚合事件数</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num">{{ brpcAbnormalThreadTotal }}</div>
        <div class="kpi-label">异常 Thread 数</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num" style="font-size: 15px">
          {{ brpcFaultBatch ? (brpcFaultBatch.start_time || '').slice(0, 16) : '—' }}
        </div>
        <div class="kpi-label">批次开始</div>
      </div>
    </div>

    <div class="section-card">
      <div class="section-card-title">UBSocket 接口故障数时序分布</div>
      <div ref="brpcFaultTimelineRef" style="height: 300px"></div>
    </div>

    <div class="tabs module-tabs">
      <div :class="['tab', { active: brpcFaultTab === 'event' }]" @click="brpcFaultTab = 'event'">
        聚合事件
      </div>
      <div :class="['tab', { active: brpcFaultTab === 'thread' }]" @click="brpcFaultTab = 'thread'">
        异常 Thread
      </div>
    </div>

    <template v-if="brpcFaultTab === 'event'">
      <div v-if="brpcAggregatedEvents.length === 0" class="empty" style="padding: 28px 0">
        <div class="icon">📭</div>
        <div>暂无聚合事件</div>
      </div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>窗口开始</th>
              <th>窗口结束</th>
              <th>Pod IP</th>
              <th>Pod 名称</th>
              <th>线程ID</th>
              <th>接口命中数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in brpcAggregatedEvents" :key="event.event_id">
              <td style="font-family: monospace; font-size: 12px">{{ event.window_start_time }}</td>
              <td style="font-family: monospace; font-size: 12px">{{ event.window_end_time }}</td>
              <td style="font-family: monospace">{{ event.pod_ip }}</td>
              <td>{{ event.pod_name || '-' }}</td>
              <td>{{ event.thread_id ?? '-' }}</td>
              <td>{{ brpcEventHitTotal(event) }}</td>
              <td>
                <button class="btn btn-sm btn-primary" @click="openBrpcFaultDetail(event)">
                  查看接口
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div
        style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px"
        v-if="brpcFaultEventPages > 1"
      >
        <span style="font-size: 13px; color: var(--text2)"
          >共 {{ brpcAggregatedEventTotal }} 条</span
        >
        <div class="pagination" style="margin-top: 0">
          <button
            :disabled="brpcAggregatedEventPage === 1"
            @click="goBrpcFaultEventsPage(brpcAggregatedEventPage - 1)"
          >
            ‹
          </button>
          <button
            v-for="page in brpcFaultEventPages"
            :key="page"
            :class="{ active: brpcAggregatedEventPage === page }"
            @click="goBrpcFaultEventsPage(page)"
          >
            {{ page }}
          </button>
          <button
            :disabled="brpcAggregatedEventPage === brpcFaultEventPages"
            @click="goBrpcFaultEventsPage(brpcAggregatedEventPage + 1)"
          >
            ›
          </button>
        </div>
      </div>
    </template>

    <template v-else>
      <div v-if="brpcAbnormalThreads.length === 0" class="empty" style="padding: 28px 0">
        <div class="icon">📭</div>
        <div>暂无异常 Thread</div>
      </div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>线程Key</th>
              <th>Pod IP</th>
              <th>Pod 名称</th>
              <th>线程ID</th>
              <th>命中数</th>
              <th>接口概要</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="thread in brpcAbnormalThreads" :key="thread.thread_key">
              <td style="font-family: monospace; font-size: 12px">{{ thread.thread_key }}</td>
              <td style="font-family: monospace">{{ thread.pod_ip }}</td>
              <td>{{ thread.pod_name || '-' }}</td>
              <td>{{ thread.thread_id }}</td>
              <td>{{ thread.total_interface_hit_count }}</td>
              <td>
                <span
                  v-for="hit in (thread.interface_hits || []).slice(0, 3)"
                  :key="hit.interface_id"
                  class="trace-chip"
                >
                  {{ hit.interface_name }}:{{ hit.interface_hit_count }}
                </span>
              </td>
              <td>
                <button class="btn btn-sm btn-primary" @click="openBrpcFaultDetail(thread)">
                  查看接口
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div
        style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px"
        v-if="brpcFaultThreadPages > 1"
      >
        <span style="font-size: 13px; color: var(--text2)"
          >共 {{ brpcAbnormalThreadTotal }} 条</span
        >
        <div class="pagination" style="margin-top: 0">
          <button
            :disabled="brpcAbnormalThreadPage === 1"
            @click="goBrpcFaultThreadsPage(brpcAbnormalThreadPage - 1)"
          >
            ‹
          </button>
          <button
            v-for="page in brpcFaultThreadPages"
            :key="page"
            :class="{ active: brpcAbnormalThreadPage === page }"
            @click="goBrpcFaultThreadsPage(page)"
          >
            {{ page }}
          </button>
          <button
            :disabled="brpcAbnormalThreadPage === brpcFaultThreadPages"
            @click="goBrpcFaultThreadsPage(brpcAbnormalThreadPage + 1)"
          >
            ›
          </button>
        </div>
      </div>
    </template>
  </template>
</template>
