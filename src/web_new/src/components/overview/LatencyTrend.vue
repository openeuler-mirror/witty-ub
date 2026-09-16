<script setup lang="ts">
import { onMounted } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'
import { normalizeTraceOperation } from '../../utils/format'
import PageNav from '../common/PageNav.vue'

// 只注入趋势/最慢/Trace 列表所需状态
const {
  currentOp,
  latencyFilter,
  latencyThresholds,
  openTraceDrawer,
  pagedTraceRows,
  renderSlowChart,
  renderTrendChart,
  resetTrend,
  selectAllTrend,
  slowRef,
  slowRows,
  slowTotal,
  traceCluster,
  traceClusters,
  traceBreakdownTitle,
  tracePage,
  tracePages,
  traceRows,
  traceSearch,
  traceSegments,
  traceTags,
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
  clearTrend,
  toggleTrendSeries,
} = useOverviewData()

onMounted(() => {
  renderTrendChart()
  renderSlowChart()
})

const podIpsOf = (row: any) =>
  row.pod_ips && row.pod_ips.length ? row.pod_ips : [row.src_ip, row.dst_ip].filter(Boolean)

const visiblePodIps = (row: any) => podIpsOf(row).slice(0, 2)

const podIpCount = (row: any) => podIpsOf(row).length
</script>

<template>
  <div style="font-size: 13px; color: var(--text2); margin-bottom: 12px">
    指标趋势、最慢请求时序分解、异常 Trace 列表同页展示
  </div>
  <div class="section-card">
    <h2 class="section-card-title">
      关键时延指标趋势
      <span class="hint"
        >{{ currentOp }} · {{ trendChartData.length }} 个采样点 · {{ trendAnomalyHint }}</span
      >
    </h2>
    <div class="filter-bar display-tools" style="margin-bottom: 10px">
      <strong class="filter-bar-title">趋势设置</strong>
      <label for="trend-scale">时间聚合尺度</label>
      <select id="trend-scale" class="select" v-model.number="trendScale">
        <option v-for="option in trendScaleOptions" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
      <label for="trend-percentile">百分位</label>
      <select id="trend-percentile" class="select" v-model="trendPercentile">
        <option v-for="option in trendPercentileOptions" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
      <button v-if="trendRange" class="btn btn-sm btn-text" @click="resetTrend">
        恢复趋势全时段
      </button>
      <div style="margin-left: auto; display: flex; gap: 4px">
        <button class="btn btn-sm btn-text" @click="selectAllTrend">全选</button>
        <button class="btn btn-sm btn-text" @click="clearTrend">清空</button>
      </div>
    </div>
    <p class="chart-scale-hint">
      横坐标会根据时间范围进行缩放，图中显示的数据为横坐标缩放后的抽稀结果<template
        v-if="!latencyFilter.logId.value && trendLogLabel"
        >；分位曲线取自首个已完成任务「{{ trendLogLabel }}」</template
      >
    </p>
    <div
      class="cb-group"
      style="background: var(--bg); border-radius: var(--radius-md); padding: 8px 12px"
    >
      <label v-for="metric in trendMetrics" :key="metric.key">
        <input
          type="checkbox"
          :checked="trendVisible.has(metric.key)"
          @change="toggleTrendSeries(metric.key)"
        />
        {{ metric.label }}
      </label>
    </div>
    <div ref="trendRef" style="height: 400px"></div>
    <div style="font-size: 12px; color: var(--text3); margin-top: 6px">
      点击数据点：以该时间为中心按当前尺度缩小范围（可继续下钻）；“重置时间范围”恢复全量。
    </div>
  </div>

  <div class="section-card">
    <h2 class="section-card-title">
      最慢请求时序分解（Top 1000）
      <span class="hint"
        >{{ currentOp }} · 图表展示 {{ slowRows.length }} 条 / 符合条件
        {{ slowTotal.toLocaleString() }} 条</span
      >
    </h2>
    <div style="font-size: 12px; color: var(--text3); margin-bottom: 8px">
      按总时延选出最慢请求，再按发生时间排列；柱体为 18 个可解析阶段（栈式）+
      其他，红线为真实总时延。
    </div>
    <div ref="slowRef" style="height: 360px"></div>
  </div>

  <div class="section-card">
    <h2 class="section-card-title">
      异常 Trace 列表
      <span class="hint">点击“查看 Trace 详情”查看原始日志与失败模式</span>
    </h2>
    <div class="filter-bar" style="margin-bottom: 10px">
      <input
        class="input"
        style="width: 240px"
        v-model="traceSearch"
        placeholder="搜索 Trace ID / Pod IP"
      />
      <select class="select" v-model="traceCluster">
        <option value="">全部集群</option>
        <option v-for="cluster in traceClusters" :key="cluster" :value="cluster">
          {{ cluster }}
        </option>
      </select>
      <span class="hint" style="margin-left: auto">共 {{ traceRows.length }} 条</span>
    </div>
    <div
      class="table-wrap trace-table-wrap"
      role="region"
      tabindex="0"
      aria-label="异常 Trace 列表，可左右滚动"
    >
      <table class="trace-compact-table">
        <colgroup>
          <col style="width: 72px" />
          <col style="width: 132px" />
          <col style="width: 132px" />
          <col style="width: 150px" />
          <col style="width: 60px" />
          <col style="width: 96px" />
          <col style="width: 96px" />
          <col style="width: 72px" />
          <col style="width: 250px" />
          <col style="width: 140px" />
        </colgroup>
        <thead>
          <tr>
            <th>故障类型</th>
            <th>时间</th>
            <th>Trace ID</th>
            <th>Pod IP</th>
            <th>操作类型</th>
            <th>集群</th>
            <th>主机</th>
            <th>总时延(ms)</th>
            <th>各阶段时延分解（P99）</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in pagedTraceRows" :key="row.trace_id">
            <td>
              <div class="task-actions">
                <span
                  v-for="tag in traceTags(row.trace_id, 'latency')"
                  :key="tag.type"
                  :class="['badge', tag.type === 'fault' ? 'badge-failed' : 'badge-warning']"
                  >{{ tag.label }}</span
                >
              </div>
            </td>
            <td style="font-size: 12px; font-family: monospace">
              {{ (row.timestamp || '').slice(0, 19) }}
            </td>
            <td>
              <span class="trace-chip" :title="row.trace_id">{{ row.trace_id.slice(0, 10) }}…</span>
            </td>
            <td>
              <div class="trace-pod-cell" :title="podIpsOf(row).join('\n')">
                <span v-for="ip in visiblePodIps(row)" :key="ip" class="trace-chip">{{ ip }}</span>
                <span v-if="podIpCount(row) > visiblePodIps(row).length" class="trace-chip more">
                  +{{ podIpCount(row) - visiblePodIps(row).length }}
                </span>
              </div>
            </td>
            <td>{{ normalizeTraceOperation(row.operation) }}</td>
            <td>{{ row.cluster_name || '-' }}</td>
            <td>{{ row.host || '-' }}</td>
            <td
              :style="{
                color:
                  Number(row.total_latency_us) / 1000 > latencyThresholds.p99
                    ? 'var(--danger)'
                    : '',
              }"
              :title="`红色 = 总时延 > ${latencyThresholds.p99}ms（P99 阈值，可用解析配置调整）`"
            >
              {{ (Number(row.total_latency_us) / 1000).toFixed(2) }}
            </td>
            <td>
              <div class="latency-breakdown" :title="traceBreakdownTitle(row)">
                <div class="latency-breakdown-bar">
                  <span
                    v-for="segment in traceSegments(row)"
                    :key="segment.key"
                    class="latency-breakdown-segment"
                    :style="{ width: segment.width + '%', background: segment.color }"
                  ></span>
                  <span
                    v-if="traceSegments(row).length === 0"
                    class="latency-breakdown-empty"
                    style="width: 100%; background: var(--bg)"
                  ></span>
                </div>
                <div class="latency-breakdown-values" style="flex-wrap: wrap">
                  <span
                    v-for="segment in traceSegments(row).slice(0, 3)"
                    :key="segment.key"
                    class="latency-breakdown-value"
                  >
                    <i :style="{ background: segment.color }"></i>{{ segment.shortLabel }}
                    {{ (segment.value / 1000).toFixed(2) }}
                  </span>
                </div>
              </div>
            </td>
            <td>
              <div class="task-actions">
                <button class="btn btn-sm btn-primary" @click="openTraceDrawer(row)">
                  查看 Trace 详情
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px"
    >
      <span style="font-size: 13px; color: var(--text2)">共 {{ traceRows.length }} 条</span>
      <PageNav
        v-if="tracePages > 1"
        :page="tracePage"
        :pages="tracePages"
        @update:page="tracePage = $event"
      />
    </div>
  </div>
</template>

<style scoped>
.trace-compact-table th {
  height: 32px;
  padding: 0 8px;
  font-size: 12px;
}

.trace-compact-table {
  width: 100%;
  min-width: 1240px;
  table-layout: fixed;
}

.trace-compact-table th:last-child,
.trace-compact-table td:last-child {
  position: sticky;
  right: 0;
  z-index: 1;
  background: var(--surface);
  box-shadow: -8px 0 12px -12px rgba(31, 42, 58, 0.45);
}

.trace-compact-table th:last-child {
  z-index: 2;
  background: var(--bg);
}

.trace-compact-table tr:hover td:last-child {
  background: var(--primary-bg);
}

@media (max-width: 800px) {
  .trace-compact-table {
    min-width: 680px;
  }

  .trace-compact-table :is(col, th, td):nth-child(1),
  .trace-compact-table :is(col, th, td):nth-child(6),
  .trace-compact-table :is(col, th, td):nth-child(7),
  .trace-compact-table :is(col, th, td):nth-child(9) {
    display: none;
  }
}

.trace-compact-table td {
  height: 34px;
  padding: 0 8px;
  font-size: 12px;
  line-height: 1.3;
}

.trace-compact-table .trace-chip {
  display: inline-block;
  padding: 0 5px;
  font-size: 10px;
  line-height: 16px;
  margin: 1px 3px 1px 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.trace-compact-table .trace-pod-cell {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.trace-compact-table .trace-pod-cell .trace-chip {
  max-width: 68px;
}

.trace-compact-table .trace-pod-cell .more {
  background: var(--bg);
  color: var(--text2);
}

.trace-compact-table .latency-breakdown {
  min-width: 0;
  padding: 3px 0;
}

.trace-compact-table .latency-breakdown-bar {
  height: 8px;
  margin-bottom: 3px;
}

.trace-compact-table .latency-breakdown-values {
  font-size: 10px;
  gap: 6px;
  line-height: 1.5;
}

.trace-compact-table .latency-breakdown-value {
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
