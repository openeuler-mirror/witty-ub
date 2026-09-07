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
  renderBrpcCharts()
})
</script>

<template>
          <template v-if="brpcMonitorTab === 'iface'">
            <div class="kpi-row">
              <div class="kpi-card"><div class="kpi-num">{{ brpcKpi.ifaceCount }}</div><div class="kpi-label">接口数</div></div>
              <div class="kpi-card"><div class="kpi-num">{{ brpcKpi.totalReq.toLocaleString() }}</div><div class="kpi-label">总请求数</div></div>
              <div class="kpi-card">
                <div class="kpi-num" :style="{ color: brpcKpi.avgSuccess == null ? 'var(--text3)' : (brpcKpi.avgSuccess < 99 ? 'var(--warning)' : 'var(--success)') }">
                  {{ brpcKpi.avgSuccess == null ? '—' : brpcKpi.avgSuccess + '%' }}
                </div>
                <div class="kpi-label">平均成功率</div>
              </div>
              <div class="kpi-card">
                <div class="kpi-num" :style="{ color: brpcKpi.p99Max == null ? 'var(--text3)' : 'var(--danger)' }">
                  {{ brpcKpi.p99Max == null ? '—' : brpcKpi.p99Max.toFixed(2) }}
                </div>
                <div class="kpi-label">最高 P99 (ms)</div>
              </div>
              <div class="kpi-card"><div class="kpi-num">{{ brpcKpi.failIface }}</div><div class="kpi-label">偏高接口数</div></div>
            </div>
            <div v-if="brpcLoading" class="empty" style="padding: 28px 0">
              <div class="icon">⏳</div>
              <div>正在加载 UBSocket 监控数据...</div>
            </div>
            <div v-else-if="brpcScopeTasks.length === 0" class="empty" style="padding: 36px 0">
              <div class="icon">📭</div>
              <div>暂无已完成的 UBSocket 任务</div>
              <div class="hint">在任务管理中创建 UBSocket 类型任务，解析完成后即可查看接口监控</div>
            </div>
            <template v-else>
              <!-- 文件存在但暂无数据时仍展示空图；仅当完全没有 profiling 数据时给出文字提示 -->
              <div v-if="brpcInterfaces.length === 0" class="empty" style="padding: 36px 0">
                <div class="icon">📭</div>
                <div>无接口日志文件，请检查是否存在profiling文件</div>
              </div>
              <template v-else>
              <div class="section-card">
                <div class="section-card-title">
                  接口成功率趋势
                  <span class="hint">UBSocket 任务（/brpc_profiling）</span>
                </div>
                <div ref="brpcSuccessRef" style="height: 240px"></div>
              </div>
              <div class="section-card">
                <div class="section-card-title">接口 P99 时延趋势</div>
                <div ref="brpcP99Ref" style="height: 240px"></div>
              </div>
              <div class="section-card">
                <div class="section-card-title">接口明细 <span class="hint">P99/均值单位为 ms</span></div>
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr><th>接口</th><th>请求数</th><th>成功数</th><th>失败数</th><th>成功率</th><th>失败率</th><th>avg(ms)</th><th>P99(ms)</th><th>max(ms)</th><th>状态</th></tr>
                    </thead>
                    <tbody>
                      <tr v-for="item in brpcInterfaces" :key="item.name">
                        <td style="font-family: monospace; font-size: 12px">{{ item.name }}</td>
                        <td>{{ item.requestCount.toLocaleString() }}</td>
                        <td>{{ item.successCount.toLocaleString() }}</td>
                        <td>{{ item.failureCount.toLocaleString() }}</td>
                        <td>{{ item.successRate }}%</td>
                        <td>{{ item.failureRate }}%</td>
                        <td>{{ (item.avg_ns / 1e6).toFixed(2) }}</td>
                        <td :style="{ color: item.p99_ns / 1e6 > 2 ? 'var(--danger)' : '' }">{{ (item.p99_ns / 1e6).toFixed(2) }}</td>
                        <td>{{ (item.max_ns / 1e6).toFixed(2) }}</td>
                        <td><span :class="item.status === '正常' ? 'badge badge-normal' : 'badge badge-warning'">{{ item.status }}</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              </template>
            </template>
          </template>
</template>
