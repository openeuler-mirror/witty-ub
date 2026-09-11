<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'

// P0.1/U1：只注入 UBSocket 接口监控所需状态
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
  brpcLatencySelectedIfaces,
  brpcLoading,
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
  brpcSuccessSelectedIfaces,
  renderBrpcLatencyChart,
  renderBrpcLatencyMonitorChart,
  renderBrpcSingleChart,
  renderBrpcSuccessOverviewChart,
} = useOverviewData()

const renderAllBrpcCharts = () => {
  renderBrpcSuccessOverviewChart()
  renderBrpcSingleChart()
  renderBrpcLatencyMonitorChart()
  renderBrpcLatencyChart()
}

onMounted(renderAllBrpcCharts)

const selectAllIfaces = () => {
  brpcSuccessSelectedIfaces.value = [...brpcIfaceNames.value]
}
const clearIfaces = () => {
  brpcSuccessSelectedIfaces.value = []
}
const selectAllLatencyIfaces = () => {
  brpcLatencySelectedIfaces.value = [...brpcIfaceNames.value]
}
const clearLatencyIfaces = () => {
  brpcLatencySelectedIfaces.value = []
}
const toggleBrpcSingleMetric = (metric: string) => {
  const selected = brpcSingleSelectedMetrics.value
  brpcSingleSelectedMetrics.value = selected.includes(metric)
    ? selected.filter((item) => item !== metric)
    : [...selected, metric]
}
const selectedSingleMetricLabel = computed(
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
          <!-- 卡片 1：接口成功率总览（指标切换 + 接口曲线勾选，颜色与勾选点一致） -->
          <article class="monitor-card monitor-card-wide">
            <div class="monitor-card-title">
              <span>接口成功率总览</span>
              <span class="monitor-card-actions">
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
            </div>
            <div class="series-toggle">
              <span class="series-toggle-label">曲线选择：</span>
              <span class="series-toggle-count">
                已选 {{ brpcSuccessSelectedIfaces.length }}/{{ brpcIfaceNames.length }}
              </span>
              <button class="btn btn-sm btn-text" type="button" @click="selectAllIfaces">
                全选
              </button>
              <button class="btn btn-sm btn-text" type="button" @click="clearIfaces">清空</button>
              <label
                v-for="iface in brpcIfaceNames"
                :key="iface"
                class="series-toggle-option"
              >
                <input
                  type="checkbox"
                  :checked="brpcSuccessSelectedIfaces.includes(iface)"
                  @change="
                    brpcSuccessSelectedIfaces = brpcSuccessSelectedIfaces.includes(iface)
                      ? brpcSuccessSelectedIfaces.filter((item) => item !== iface)
                      : [...brpcSuccessSelectedIfaces, iface]
                  "
                />
                <span class="series-dot" :style="{ backgroundColor: brpcIfaceColor(iface) }"></span>
                {{ iface }}
              </label>
            </div>
            <div ref="brpcSuccessOverviewRef" style="height: 280px"></div>
          </article>

          <!-- 卡片 2：单接口成功率监控（接口 + 指标多选，数量/比率双轴，通栏避免轴标签挤压） -->
          <article class="monitor-card monitor-card-wide">
            <div class="monitor-card-title">
              <span>单接口成功率监控</span>
              <span class="monitor-card-actions">
                <label class="hint" for="brpc-single-iface">接口</label>
                <select id="brpc-single-iface" class="select" v-model="brpcSingleIface">
                  <option v-for="iface in brpcIfaceNames" :key="iface" :value="iface">
                    {{ iface }}
                  </option>
                </select>
              </span>
            </div>
            <div class="series-toggle">
              <span class="series-toggle-label">指标选择：</span>
              <span class="series-toggle-count">
                已选 {{ brpcSingleSelectedMetrics.length }}/{{ brpcSingleMetrics.length }}
              </span>
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
            </div>
            <div class="monitor-card-hint">当前：{{ selectedSingleMetricLabel }}</div>
            <div ref="brpcSingleRef" style="height: 320px"></div>
          </article>

          <!-- 卡片 4：单接口时延（ms，所选接口 avg/P99/max） -->
          <article class="monitor-card monitor-card-wide">
            <div class="monitor-card-title">
              <span>单接口时延（ms）</span>
              <span class="monitor-card-actions hint">{{ brpcSingleIface || '-' }}</span>
            </div>
            <div class="monitor-card-hint">跟随「单接口成功率监控」所选接口</div>
            <div ref="brpcLatencyRef" style="height: 320px"></div>
          </article>

          <!-- 卡片 3：时延监控（µs，指标下拉 + 接口曲线勾选） -->
          <article class="monitor-card monitor-card-wide">
            <div class="monitor-card-title">
              <span>时延监控 (µs)</span>
              <span class="monitor-card-actions">
                <label class="hint" for="brpc-latency-metric">指标</label>
                <select id="brpc-latency-metric" class="select" v-model="brpcLatencyMetric">
                  <option v-for="m in brpcLatencyMetrics" :key="m.value" :value="m.value">
                    {{ m.label }}
                  </option>
                </select>
              </span>
            </div>
            <div class="series-toggle">
              <span class="series-toggle-label">曲线选择：</span>
              <span class="series-toggle-count">
                已选 {{ brpcLatencySelectedIfaces.length }}/{{ brpcIfaceNames.length }}
              </span>
              <button class="btn btn-sm btn-text" type="button" @click="selectAllLatencyIfaces">
                全选
              </button>
              <button class="btn btn-sm btn-text" type="button" @click="clearLatencyIfaces">
                清空
              </button>
              <label v-for="iface in brpcIfaceNames" :key="iface" class="series-toggle-option">
                <input
                  type="checkbox"
                  :checked="brpcLatencySelectedIfaces.includes(iface)"
                  @change="
                    brpcLatencySelectedIfaces = brpcLatencySelectedIfaces.includes(iface)
                      ? brpcLatencySelectedIfaces.filter((item) => item !== iface)
                      : [...brpcLatencySelectedIfaces, iface]
                  "
                />
                <span class="series-dot" :style="{ backgroundColor: brpcIfaceColor(iface) }"></span>
                {{ iface }}
              </label>
            </div>
            <div ref="brpcLatencyMonitorRef" style="height: 280px"></div>
          </article>

        </div>

        <!-- 接口明细表（P2.1 保留） -->
        <article class="monitor-card" style="margin-top: 16px">
          <div class="monitor-card-title">
            <span>接口明细</span>
            <span class="monitor-card-actions hint">
              按请求数排序 · avg/P99/max 单位 ms · P99 &gt; 2ms 记为偏高
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
                  <td style="font-family: monospace; font-size: 12px">{{ item.name }}</td>
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
