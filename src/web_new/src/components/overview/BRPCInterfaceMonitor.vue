<script setup lang="ts">
import { onMounted } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'

// P0.1：只注入 UBSocket 接口监控所需状态
const {
  brpcFileKey,
  brpcFileLabel,
  brpcIfaceNames,
  brpcInterfaces,
  brpcKpi,
  brpcLatencyRef,
  brpcLoading,
  brpcMonitorTab,
  brpcP99Ref,
  brpcProfilingFiles,
  brpcScopeTasks,
  brpcSelectedFileKey,
  brpcSingleIface,
  brpcSingleRef,
  brpcSuccessMetric,
  brpcSuccessMetricOptions,
  brpcSuccessOverviewRef,
  brpcSuccessRef,
  brpcSuccessSelectedIfaces,
  renderBrpcCharts,
  renderBrpcLatencyChart,
  renderBrpcSingleChart,
  renderBrpcSuccessOverviewChart,
} = useOverviewData()

onMounted(() => {
  renderBrpcCharts()
  renderBrpcSuccessOverviewChart()
  renderBrpcSingleChart()
  renderBrpcLatencyChart()
})

const selectAllIfaces = () => {
  brpcSuccessSelectedIfaces.value = [...brpcIfaceNames.value]
}
const clearIfaces = () => {
  brpcSuccessSelectedIfaces.value = []
}
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
    <template v-else>
      <!-- 文件存在但暂无数据时仍展示空图；仅当完全没有 profiling 数据时给出文字提示 -->
      <div v-if="brpcInterfaces.length === 0" class="empty" style="padding: 36px 0">
        <div class="icon">📭</div>
        <div>无接口日志文件，请检查是否存在profiling文件</div>
      </div>
      <template v-else>
        <!-- P2.1：profiling 文件选择（客户端过滤，不重拉） -->
        <div class="operate-bar">
          <div style="display: flex; align-items: center; gap: 8px">
            <span style="font-size: 13px; color: var(--text2)">选择 profiling 文件:</span>
            <select class="select" v-model="brpcSelectedFileKey">
              <option
                v-for="file in brpcProfilingFiles"
                :key="brpcFileKey(file)"
                :value="brpcFileKey(file)"
              >
                {{ brpcFileLabel(file) }}
              </option>
            </select>
          </div>
        </div>
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

        <!-- P2.1：成功率总览（指标切换 + 接口曲线勾选） -->
        <div class="section-card">
          <div class="section-card-title">
            接口成功率总览
            <span style="margin-left: auto; display: inline-flex; align-items: center; gap: 6px">
              <label for="brpc-success-metric" class="hint">指标</label>
              <select id="brpc-success-metric" class="select" v-model="brpcSuccessMetric">
                <option v-for="opt in brpcSuccessMetricOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </span>
          </div>
          <div
            class="cb-group"
            style="
              background: var(--bg);
              border-radius: var(--radius-md);
              padding: 8px 12px;
              margin-bottom: 8px;
            "
          >
            <span class="hint" style="margin-right: 4px">
              已选 {{ brpcSuccessSelectedIfaces.length }}/{{ brpcIfaceNames.length }}
            </span>
            <button class="btn btn-sm btn-text" @click="selectAllIfaces">全选</button>
            <button class="btn btn-sm btn-text" @click="clearIfaces">清空</button>
            <label v-for="iface in brpcIfaceNames" :key="iface">
              <input type="checkbox" v-model="brpcSuccessSelectedIfaces" :value="iface" />
              {{ iface }}
            </label>
          </div>
          <div ref="brpcSuccessOverviewRef" style="height: 280px"></div>
        </div>

        <!-- P2.1：单接口监控（成功率/失败率） -->
        <div class="section-card">
          <div class="section-card-title">
            单接口监控
            <span style="margin-left: auto; display: inline-flex; align-items: center; gap: 6px">
              <label for="brpc-single-iface" class="hint">接口</label>
              <select id="brpc-single-iface" class="select" v-model="brpcSingleIface">
                <option v-for="iface in brpcIfaceNames" :key="iface" :value="iface">
                  {{ iface }}
                </option>
              </select>
            </span>
          </div>
          <div ref="brpcSingleRef" style="height: 240px"></div>
        </div>

        <!-- P2.1：单接口时延（avg/P99/max） -->
        <div class="section-card">
          <div class="section-card-title">
            单接口时延（ms）
            <span class="hint">{{ brpcSingleIface || '-' }}</span>
          </div>
          <div ref="brpcLatencyRef" style="height: 240px"></div>
        </div>

        <div class="section-card">
          <div class="section-card-title">接口明细 <span class="hint">P99/均值单位为 ms</span></div>
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
        </div>
      </template>
    </template>
  </template>
</template>
