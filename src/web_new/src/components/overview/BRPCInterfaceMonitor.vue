<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'

// 只注入 UBSocket 接口监控所需状态
const {
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
  brpcMonitorTab,
  brpcOverviewSelectedIfaces,
  brpcProfilingFiles,
  brpcScopeTasks,
  brpcSelectedFileKey,
  brpcSingleIface,
  brpcSingleLatencyColor,
  brpcSingleLatencyMetrics,
  brpcSingleLatencySelectedMetrics,
  brpcSingleLatencyUnit,
  brpcSingleMetricColor,
  brpcSingleMetrics,
  brpcSingleRef,
  brpcSingleSelectedMetrics,
  brpcSuccessMetric,
  brpcSuccessMetricOptions,
  brpcSuccessOverviewRef,
  renderBrpcLatencyChart,
  renderBrpcLatencyMonitorChart,
  renderBrpcSingleChart,
  renderBrpcSuccessOverviewChart,
} = useOverviewData()

// 单接口分析卡片：接口明细表点接口名时滚动到这里
const singleIfaceCardRef = ref<HTMLElement | null>(null)

const renderAllBrpcCharts = () => {
  renderBrpcSuccessOverviewChart()
  renderBrpcSingleChart()
  renderBrpcLatencyMonitorChart()
  renderBrpcLatencyChart()
}

onMounted(renderAllBrpcCharts)

// 全接口总览：成功率与时延两张图共用一套接口勾选
const toggleOverviewIface = (iface: string) => {
  const selected = brpcOverviewSelectedIfaces.value
  brpcOverviewSelectedIfaces.value = selected.includes(iface)
    ? selected.filter((item) => item !== iface)
    : [...selected, iface]
}
const selectAllOverviewIfaces = () => {
  brpcOverviewSelectedIfaces.value = [...brpcIfaceNames.value]
}
const clearOverviewIfaces = () => {
  brpcOverviewSelectedIfaces.value = []
}

const toggleBrpcSingleMetric = (metric: string) => {
  const selected = brpcSingleSelectedMetrics.value
  brpcSingleSelectedMetrics.value = selected.includes(metric)
    ? selected.filter((item) => item !== metric)
    : [...selected, metric]
}
const selectAllSingleMetrics = () => {
  brpcSingleSelectedMetrics.value = brpcSingleMetrics.map((metric) => metric.value)
}
const clearSingleMetrics = () => {
  brpcSingleSelectedMetrics.value = []
}

const toggleSingleLatencyMetric = (metric: string) => {
  const selected = brpcSingleLatencySelectedMetrics.value
  brpcSingleLatencySelectedMetrics.value = selected.includes(metric)
    ? selected.filter((item) => item !== metric)
    : [...selected, metric]
}
const selectAllSingleLatencyMetrics = () => {
  brpcSingleLatencySelectedMetrics.value = brpcSingleLatencyMetrics.map((metric) => metric.value)
}
const clearSingleLatencyMetrics = () => {
  brpcSingleLatencySelectedMetrics.value = []
}

// 接口明细 → 单接口分析：选中该接口并滚动到卡片，联动的两张图立即切换
const openSingleIface = (iface: string) => {
  brpcSingleIface.value = iface
  singleIfaceCardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const singleSuccessMetricLabel = computed(
  () =>
    brpcSingleMetrics
      .filter((metric) => brpcSingleSelectedMetrics.value.includes(metric.value))
      .map((metric) => metric.label)
      .join(' / ') || '未选择指标',
)
</script>

<template>
  <template v-if="brpcMonitorTab === 'iface'">
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-num">{{ brpcKpi.ifaceCount }}</div>
        <div class="kpi-label">接口数</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num">{{ brpcKpi.totalReq.toLocaleString() }}</div>
        <div class="kpi-label">总请求数</div>
      </div>
      <div class="kpi-card">
        <div
          class="kpi-num"
          :style="{
            color:
              brpcKpi.avgSuccess == null
                ? 'var(--text3)'
                : brpcKpi.avgSuccess < 99
                  ? 'var(--warning)'
                  : 'var(--success)',
          }"
        >
          {{ brpcKpi.avgSuccess == null ? '—' : brpcKpi.avgSuccess + '%' }}
        </div>
        <div class="kpi-label">平均成功率</div>
      </div>
      <div class="kpi-card">
        <div
          class="kpi-num"
          :style="{ color: brpcKpi.p99Max == null ? 'var(--text3)' : 'var(--danger)' }"
        >
          {{ brpcKpi.p99Max == null ? '—' : brpcKpi.p99Max.toFixed(2) }}
        </div>
        <div class="kpi-label">最高 P99 (ms)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num">{{ brpcKpi.failIface }}</div>
        <div class="kpi-label">偏高接口数</div>
      </div>
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
    <div v-else-if="brpcProfilingFiles.length === 0" class="empty" style="padding: 36px 0">
      <div class="icon">📭</div>
      <div>无接口日志文件，请检查是否存在profiling文件</div>
    </div>
    <template v-else>
      <!-- 文件选择条：文件存在但无数据时明确说明，避免“看起来像没过滤” -->
      <div class="monitor-toolbar">
        <span class="monitor-toolbar-label">选择 profiling 文件：</span>
        <select class="select" v-model="brpcSelectedFileKey">
          <option
            v-for="file in brpcProfilingFiles"
            :key="brpcFileKey(file)"
            :value="brpcFileKey(file)"
          >
            {{ brpcFileLabel(file) }}
          </option>
        </select>
        <span class="monitor-toolbar-hint">
          {{ brpcIfaceNames.length }} 个接口 · 数据来自选中的 profiling 文件
        </span>
      </div>

      <div v-if="!brpcHasRows" class="brpc-chart-empty" role="status">
        当前筛选时间范围内无数据
      </div>
      <template v-else>
        <div class="monitor-grid">
          <!-- 卡片 1：全接口总览（成功率 + 时延共用一套接口勾选，左右并排对照） -->
          <article class="monitor-card monitor-card-wide">
            <div class="monitor-card-title">
              <span>全接口总览</span>
              <span class="monitor-card-actions hint"
                >按接口叠加对比 · 两张图共用下方勾选的接口</span
              >
            </div>
            <div class="series-toggle">
              <span class="series-toggle-label">曲线选择：</span>
              <span class="series-toggle-count">
                已选 {{ brpcOverviewSelectedIfaces.length }}/{{ brpcIfaceNames.length }}
              </span>
              <button class="btn btn-sm btn-text" type="button" @click="selectAllOverviewIfaces">
                全选
              </button>
              <button class="btn btn-sm btn-text" type="button" @click="clearOverviewIfaces">
                清空
              </button>
              <label v-for="iface in brpcIfaceNames" :key="iface" class="series-toggle-option">
                <input
                  type="checkbox"
                  :checked="brpcOverviewSelectedIfaces.includes(iface)"
                  @change="toggleOverviewIface(iface)"
                />
                <span class="series-dot" :style="{ backgroundColor: brpcIfaceColor(iface) }"></span>
                {{ iface }}
              </label>
            </div>
            <div class="monitor-pane-grid">
              <section class="monitor-pane">
                <header class="monitor-pane-head">
                  <span class="monitor-pane-title">成功率 / 请求量</span>
                  <span class="monitor-pane-actions">
                    <label class="hint" for="brpc-success-metric">指标</label>
                    <select id="brpc-success-metric" class="select" v-model="brpcSuccessMetric">
                      <option
                        v-for="opt in brpcSuccessMetricOptions"
                        :key="opt.value"
                        :value="opt.value"
                      >
                        {{ opt.label }}
                      </option>
                    </select>
                  </span>
                </header>
                <div ref="brpcSuccessOverviewRef" style="height: 300px"></div>
              </section>
              <section class="monitor-pane">
                <header class="monitor-pane-head">
                  <span class="monitor-pane-title">时延 (µs)</span>
                  <span class="monitor-pane-actions">
                    <label class="hint" for="brpc-latency-metric">指标</label>
                    <select id="brpc-latency-metric" class="select" v-model="brpcLatencyMetric">
                      <option v-for="m in brpcLatencyMetrics" :key="m.value" :value="m.value">
                        {{ m.label }}
                      </option>
                    </select>
                  </span>
                </header>
                <div ref="brpcLatencyMonitorRef" style="height: 300px"></div>
              </section>
            </div>
          </article>

          <!-- 卡片 2：单接口分析（同一个接口选择驱动成功率与时延两张图） -->
          <article
            ref="singleIfaceCardRef"
            class="monitor-card monitor-card-wide monitor-card-anchor"
          >
            <div class="monitor-card-title">
              <span>单接口分析</span>
              <span class="monitor-pane-actions">
                <label class="hint" for="brpc-single-iface">接口</label>
                <select
                  id="brpc-single-iface"
                  class="select select-iface"
                  v-model="brpcSingleIface"
                >
                  <option v-for="iface in brpcIfaceNames" :key="iface" :value="iface">
                    {{ iface }}
                  </option>
                </select>
              </span>
            </div>
            <div class="monitor-card-hint">
              下方两张图联动同一接口{{
                brpcSingleIface ? `（当前：${brpcSingleIface}）` : ''
              }}，切换接口即同时刷新成功率与时延
            </div>
            <div class="monitor-pane-grid">
              <section class="monitor-pane">
                <header class="monitor-pane-head">
                  <span class="monitor-pane-title">成功率 / 请求量</span>
                  <span class="monitor-pane-actions">
                    <span class="series-toggle-count">
                      已选 {{ brpcSingleSelectedMetrics.length }}/{{ brpcSingleMetrics.length }}
                    </span>
                    <button
                      class="btn btn-sm btn-text"
                      type="button"
                      @click="selectAllSingleMetrics"
                    >
                      全选
                    </button>
                    <button class="btn btn-sm btn-text" type="button" @click="clearSingleMetrics">
                      清空
                    </button>
                  </span>
                </header>
                <div class="series-toggle series-toggle-compact">
                  <label
                    v-for="metric in brpcSingleMetrics"
                    :key="metric.value"
                    class="series-toggle-option"
                  >
                    <input
                      type="checkbox"
                      :checked="brpcSingleSelectedMetrics.includes(metric.value)"
                      @change="toggleBrpcSingleMetric(metric.value)"
                    />
                    <span
                      class="series-dot"
                      :style="{ backgroundColor: brpcSingleMetricColor(metric.value) }"
                    ></span>
                    {{ metric.label }}
                  </label>
                  <span class="series-toggle-count series-toggle-current">
                    当前：{{ singleSuccessMetricLabel }}
                  </span>
                </div>
                <div ref="brpcSingleRef" style="height: 300px"></div>
              </section>
              <section class="monitor-pane">
                <header class="monitor-pane-head">
                  <span class="monitor-pane-title">时延</span>
                  <span class="monitor-pane-actions">
                    <span class="series-toggle-count">
                      已选 {{ brpcSingleLatencySelectedMetrics.length }}/{{
                        brpcSingleLatencyMetrics.length
                      }}
                    </span>
                    <button
                      class="btn btn-sm btn-text"
                      type="button"
                      @click="selectAllSingleLatencyMetrics"
                    >
                      全选
                    </button>
                    <button
                      class="btn btn-sm btn-text"
                      type="button"
                      @click="clearSingleLatencyMetrics"
                    >
                      清空
                    </button>
                    <span class="view-tabs unit-tabs" role="group" aria-label="时延单位">
                      <button
                        class="view-tab"
                        :class="{ active: brpcSingleLatencyUnit === 'ms' }"
                        type="button"
                        @click="brpcSingleLatencyUnit = 'ms'"
                      >
                        ms
                      </button>
                      <button
                        class="view-tab"
                        :class="{ active: brpcSingleLatencyUnit === 'µs' }"
                        type="button"
                        @click="brpcSingleLatencyUnit = 'µs'"
                      >
                        µs
                      </button>
                    </span>
                  </span>
                </header>
                <div class="series-toggle series-toggle-compact">
                  <label
                    v-for="metric in brpcSingleLatencyMetrics"
                    :key="metric.value"
                    class="series-toggle-option"
                  >
                    <input
                      type="checkbox"
                      :checked="brpcSingleLatencySelectedMetrics.includes(metric.value)"
                      @change="toggleSingleLatencyMetric(metric.value)"
                    />
                    <span
                      class="series-dot"
                      :style="{ backgroundColor: brpcSingleLatencyColor(metric.value) }"
                    ></span>
                    {{ metric.label }}
                  </label>
                </div>
                <div ref="brpcLatencyRef" style="height: 300px"></div>
              </section>
            </div>
          </article>
        </div>

        <!-- 接口明细表（保留） -->
        <article class="monitor-card" style="margin-top: 16px">
          <div class="monitor-card-title">
            <span>接口明细</span>
            <span class="monitor-card-actions hint">
              按请求数排序 · avg/P99/max 单位 ms · P99 &gt; 2ms 记为偏高 ·
              点击接口名可下钻到单接口分析
            </span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>接口</th>
                  <th>请求数</th>
                  <th>成功数</th>
                  <th>失败数</th>
                  <th>成功率</th>
                  <th>失败率</th>
                  <th>avg(ms)</th>
                  <th>P99(ms)</th>
                  <th>max(ms)</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in brpcInterfaces" :key="item.name">
                  <td>
                    <button
                      class="iface-link"
                      type="button"
                      title="在单接口分析中查看该接口"
                      @click="openSingleIface(item.name)"
                    >
                      {{ item.name }}
                    </button>
                  </td>
                  <td>{{ item.requestCount.toLocaleString() }}</td>
                  <td>{{ item.successCount.toLocaleString() }}</td>
                  <td>{{ item.failureCount.toLocaleString() }}</td>
                  <td>{{ item.successRate }}%</td>
                  <td>{{ item.failureRate }}%</td>
                  <td>{{ (item.avg_ns / 1e6).toFixed(2) }}</td>
                  <td :style="{ color: item.p99_ns / 1e6 > 2 ? 'var(--danger)' : '' }">
                    {{ (item.p99_ns / 1e6).toFixed(2) }}
                  </td>
                  <td>{{ (item.max_ns / 1e6).toFixed(2) }}</td>
                  <td>
                    <span
                      :class="item.status === '正常' ? 'badge badge-normal' : 'badge badge-warning'"
                      >{{ item.status }}</span
                    >
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </template>
    </template>
  </template>
</template>
