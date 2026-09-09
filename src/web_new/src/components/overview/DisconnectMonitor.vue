<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'
import { normalizeFaultCodes, normalizeTraceOperation } from '../../utils/format'
import PageNav from '../common/PageNav.vue'

const {
  activeFaultTraces,
  clearFaultRange,
  clearFaultTraceQuery,
  currentOp,
  disconnectFilter,
  enterFaultDetail,
  enterFaultLinkDetail,
  failureModeOf,
  faultActivePairs,
  faultChartData,
  faultChartRef,
  faultChartSampled,
  faultChartScale,
  faultChartScaleOptions,
  faultCodeSummaries,
  faultPodStats,
  faultScopedTraces,
  faultTimeRange,
  faultTopoRef,
  faultTraceIdInput,
  faultTraceLoadedCount,
  faultTracePage,
  faultTracePages,
  faultTraceQuery,
  faultTraceQueryError,
  faultTraceQueryLoading,
  faultTraceTotal,
  faultTracesTruncated,
  filteredFaultTraces,
  openTraceDrawer,
  pagedFaultTraces,
  queryFaultTraceById,
  renderFaultChart,
  renderFaultTopology,
  selectedFaultCode,
  traceTags,
} = useOverviewData()

const selectedSummary = computed(() =>
  faultCodeSummaries.value.find((summary) => summary.code === selectedFaultCode.value),
)
const selectedModeIds = computed(() => selectedSummary.value?.modeIds ?? [])
const topFaultPairs = computed(() => faultActivePairs.value.slice(0, 8))
const topFaultEndpoints = computed(() => faultPodStats.value.slice(0, 8))
const scopeLabel = computed(() =>
  selectedFaultCode.value ? `故障码 ${selectedFaultCode.value}` : '全部故障码',
)

const selectFaultCode = (code: string) => {
  if (selectedFaultCode.value === code) return
  selectedFaultCode.value = code
  disconnectFilter.clearFocus()
  clearFaultTraceQuery()
  faultTracePage.value = 1
}

watch(faultCodeSummaries, (summaries) => {
  if (
    selectedFaultCode.value &&
    !summaries.some((summary) => summary.code === selectedFaultCode.value)
  ) {
    selectFaultCode('')
  }
})

onMounted(() => {
  renderFaultChart()
  renderFaultTopology()
})

const faultPodIps = (row: any) =>
  row.pod_names?.length
    ? row.pod_names
    : row.pod_ips?.length
      ? row.pod_ips
      : [row.src_ip, row.dst_ip].filter(Boolean)
const visibleFaultPodIps = (row: any) => faultPodIps(row).slice(0, 2)
const faultPodIpCount = (row: any) => faultPodIps(row).length
const shortTraceId = (id: string) => (id?.length > 12 ? `${id.slice(0, 12)}…` : id || '-')
const faultCodesOf = (row: any) => normalizeFaultCodes(row.status_code)
const failureModeIdsOf = (row: any) =>
  String(row.failure_mode || '')
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean)
const failureModeNamesOf = (row: any) => {
  const names = failureModeIdsOf(row).map((id) => failureModeOf(id)?.name || id)
  return names.length ? names.join(' / ') : '-'
}
const failureDomainsOf = (row: any) => {
  const domains = [
    ...new Set(
      failureModeIdsOf(row)
        .map((id) => failureModeOf(id)?.failure_domain)
        .filter(Boolean),
    ),
  ]
  return domains.length ? domains.join(' / ') : '-'
}
</script>

<template>
  <section class="fault-journey" aria-label="通断故障诊断路径">
    <div>
      <span class="fault-eyebrow">故障诊断</span>
      <h2>从故障码出发，定位影响范围并核对现场证据</h2>
      <p>故障码是入口，具体故障、时间、链路、端点、Trace 与运行日志共同构成诊断结论。</p>
    </div>
    <ol>
      <li class="active"><b>1</b><span>识别故障码</span></li>
      <li><b>2</b><span>理解故障</span></li>
      <li><b>3</b><span>定位影响</span></li>
      <li><b>4</b><span>核验证据</span></li>
    </ol>
  </section>

  <div class="analysis-range-bar">
    <div>
      <strong>当前诊断范围</strong>
      <span
        >{{ currentOp }} ·
        {{ faultTimeRange ? `${faultTimeRange.start} ~ ${faultTimeRange.end}` : '全部时段' }} ·
        {{ scopeLabel }}</span
      >
    </div>
    <button v-if="faultTimeRange" class="btn btn-sm btn-default" @click="clearFaultRange">
      恢复全部时段
    </button>
  </div>

  <div v-if="faultTracesTruncated" class="fault-warning" role="alert">
    当前仅加载 {{ faultTraceLoadedCount }} / {{ faultTraceTotal }} 条故障
    Trace；故障码、拓扑、端点和实例统计均基于已加载数据，不能视为全量结论。精确计数请使用“聚合事件”。
  </div>

  <section class="fault-code-workbench">
    <aside class="fault-code-catalog" aria-label="故障码目录">
      <header>
        <div>
          <strong>故障码目录</strong><span>{{ faultCodeSummaries.length }} 类</span>
        </div>
        <small>按关联 Trace 数降序</small>
      </header>
      <button
        type="button"
        :class="['fault-code-item', { active: !selectedFaultCode }]"
        @click="selectFaultCode('')"
      >
        <span class="fault-code-token all">ALL</span>
        <span class="fault-code-main"><b>全部故障</b><small>查看当前范围整体情况</small></span>
        <strong>{{ activeFaultTraces.length }}</strong>
      </button>
      <button
        v-for="summary in faultCodeSummaries"
        :key="summary.code"
        type="button"
        :class="['fault-code-item', { active: selectedFaultCode === summary.code }]"
        @click="selectFaultCode(summary.code)"
      >
        <span class="fault-code-token">{{ summary.code }}</span>
        <span class="fault-code-main">
          <b>{{ failureModeOf(summary.modeIds[0])?.name || `故障码 ${summary.code}` }}</b>
          <small>{{ summary.endpointCount }} 端点 · {{ summary.pairCount }} 链路</small>
        </span>
        <strong>{{ summary.traceCount }}</strong>
      </button>
      <div v-if="faultCodeSummaries.length === 0" class="fault-code-empty">当前范围没有故障码</div>
    </aside>

    <div class="fault-code-detail">
      <header class="fault-detail-header">
        <div>
          <span class="fault-eyebrow">{{ selectedFaultCode ? '当前故障码' : '全部故障概览' }}</span>
          <h2>
            {{ selectedFaultCode ? `故障码 ${selectedFaultCode}` : '选择一个故障码查看具体语义' }}
          </h2>
          <p v-if="selectedSummary">
            关联 {{ selectedSummary.traceCount }} 条 Trace，影响
            {{ selectedSummary.endpointCount }} 个端点、{{ selectedSummary.pairCount }} 条有向链路。
          </p>
          <p v-else>左侧按影响规模列出当前时段内的故障码。选择后，下方全部内容只分析该故障码。</p>
        </div>
        <div v-if="selectedSummary" class="fault-time-span">
          <span
            >首次出现<strong>{{ selectedSummary.firstSeen || '-' }}</strong></span
          >
          <span
            >最后出现<strong>{{ selectedSummary.lastSeen || '-' }}</strong></span
          >
        </div>
      </header>

      <div v-if="selectedFaultCode" class="failure-knowledge-grid">
        <article v-for="id in selectedModeIds" :key="id" class="failure-knowledge-card">
          <div class="failure-knowledge-title">
            <span>{{ failureModeOf(id)?.failure_domain || '故障模式' }}</span>
            <strong>{{ failureModeOf(id)?.name || id }}</strong>
          </div>
          <dl>
            <div>
              <dt>现象</dt>
              <dd>{{ failureModeOf(id)?.symptom || '暂无故障现象说明' }}</dd>
            </div>
            <div>
              <dt>根因</dt>
              <dd>{{ failureModeOf(id)?.root_cause || '暂无根因说明' }}</dd>
            </div>
            <div>
              <dt>建议</dt>
              <dd>{{ failureModeOf(id)?.solution || '请结合 Trace 与运行日志进一步确认' }}</dd>
            </div>
          </dl>
        </article>
        <div v-if="selectedModeIds.length === 0" class="failure-knowledge-empty">
          当前故障码没有关联到可展示的故障模式知识，请从下方实例进入 Trace 日志确认。
        </div>
      </div>
    </div>
  </section>

  <section class="section-card">
    <header class="fault-section-header">
      <div>
        <span class="fault-step">时间定位</span>
        <h2 class="section-card-title">{{ scopeLabel }} · 发生趋势</h2>
        <p>拖拽框选时间范围后，影响链路、端点与故障实例同步收窄。</p>
      </div>
      <div class="fault-chart-controls">
        <span
          v-if="faultChartSampled"
          class="sample-warning"
          title="后端已抽稀，按尺度聚合后的桶计数不再精确"
          >数据已抽稀，桶计数为近似</span
        >
        <label for="fault-chart-scale">时间尺度</label>
        <select id="fault-chart-scale" class="select" v-model.number="faultChartScale">
          <option v-for="opt in faultChartScaleOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>
    </header>
    <div v-if="Object.keys(faultChartData).length === 0" class="empty fault-empty">
      <div class="icon">📭</div>
      <div>当前操作无故障码时序数据</div>
    </div>
    <div v-else ref="faultChartRef" class="fault-trend-chart"></div>
  </section>

  <section class="section-card">
    <header class="fault-section-header">
      <div>
        <span class="fault-step">影响定位</span>
        <h2 class="section-card-title">{{ scopeLabel }} · 影响链路与端点</h2>
        <p>
          拓扑呈现通信方向；右侧按故障 Trace 数列出热点链路和端点。点击即可查看当前范围内的故障
          Trace。
        </p>
      </div>
    </header>
    <div class="fault-impact-workbench">
      <div class="fault-topology-panel">
        <div class="fault-topology-meta">
          <span>{{ faultActivePairs.length }} 条链路</span>
          <span>{{ faultPodStats.length }} 个端点</span>
          <span>线宽 / 节点大小 = 故障 Trace 数</span>
        </div>
        <div ref="faultTopoRef" class="fault-topology"></div>
      </div>
      <aside class="fault-impact-ranking">
        <section>
          <h3>
            热点链路 <small>Top {{ topFaultPairs.length }}</small>
          </h3>
          <button
            v-for="pair in topFaultPairs"
            :key="pair.src + '→' + pair.dst"
            class="impact-row"
            @click="enterFaultLinkDetail(pair.src, pair.dst)"
          >
            <span class="impact-route"
              ><b>{{ pair.src }}</b
              ><i>→</i><b>{{ pair.dst }}</b
              ><small>{{ pair.codes.map((code) => `故障码 ${code}`).join(' / ') }}</small></span
            >
            <strong>{{ pair.faults }}</strong>
          </button>
          <div v-if="topFaultPairs.length === 0" class="impact-empty">暂无故障链路</div>
        </section>
        <section>
          <h3>
            热点端点 <small>Top {{ topFaultEndpoints.length }}</small>
          </h3>
          <button
            v-for="endpoint in topFaultEndpoints"
            :key="endpoint.ip"
            class="impact-row endpoint"
            @click="enterFaultDetail(endpoint.ip)"
          >
            <span
              ><b>{{ endpoint.ip }}</b
              ><small>出 {{ endpoint.src }} · 入 {{ endpoint.dst }}</small></span
            >
            <strong>{{ endpoint.faults }}</strong>
          </button>
          <div v-if="topFaultEndpoints.length === 0" class="impact-empty">暂无受影响端点</div>
        </section>
      </aside>
    </div>
  </section>

  <section class="section-card">
    <header class="fault-section-header trace-header">
      <div>
        <span class="fault-step">现场证据</span>
        <h2 class="section-card-title">{{ scopeLabel }} · 故障实例</h2>
        <p>
          {{
            faultTraceQuery
              ? `Trace ID ${faultTraceQuery.id} 的查询结果`
              : faultTimeRange
                ? `${faultTimeRange.start} ~ ${faultTimeRange.end}`
                : '全部时段'
          }}
        </p>
      </div>
      <form class="trace-search" @submit.prevent="queryFaultTraceById">
        <input
          class="input"
          v-model="faultTraceIdInput"
          placeholder="输入 Trace ID 精确查询"
          aria-label="按 Trace ID 查询通断异常 Trace"
          :disabled="faultTraceQueryLoading"
        />
        <button
          class="btn btn-sm btn-primary"
          type="submit"
          :disabled="faultTraceQueryLoading || !faultTraceIdInput.trim()"
        >
          {{ faultTraceQueryLoading ? '查询中…' : '查询' }}
        </button>
        <button
          v-if="faultTraceQuery"
          class="btn btn-sm btn-default"
          type="button"
          @click="clearFaultTraceQuery"
        >
          恢复列表
        </button>
      </form>
    </header>
    <div v-if="faultTraceQueryError" class="error-banner">{{ faultTraceQueryError }}</div>
    <div v-if="filteredFaultTraces.length === 0" class="empty fault-empty">
      <div class="icon">📭</div>
      <div>{{ faultTraceQuery ? '未查询到匹配的故障实例' : '当前诊断范围内没有故障实例' }}</div>
    </div>
    <div
      v-else
      class="table-wrap"
      role="region"
      tabindex="0"
      aria-label="通断故障实例列表，可左右滚动"
    >
      <table class="fault-instance-table">
        <thead>
          <tr>
            <th>发生时间</th>
            <th>故障码</th>
            <th>具体故障 / 故障域</th>
            <th>影响链路</th>
            <th>Pod 上下文</th>
            <th>Trace ID</th>
            <th>证据</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in pagedFaultTraces" :key="row.trace_id">
            <td class="mono">{{ (row.timestamp || '').slice(0, 19) }}</td>
            <td>
              <span v-for="code in faultCodesOf(row)" :key="code" class="fault-code-chip">{{
                code
              }}</span
              ><span v-if="faultCodesOf(row).length === 0">-</span>
            </td>
            <td>
              <strong class="fault-name">{{ failureModeNamesOf(row) }}</strong
              ><small class="fault-domain">{{ failureDomainsOf(row) }}</small>
            </td>
            <td class="route-cell">
              <span>{{ row.src_ip || '-' }}</span
              ><i>→</i><span>{{ row.dst_ip || '-' }}</span>
            </td>
            <td>
              <div class="trace-pods" :title="faultPodIps(row).join('\n')">
                <span v-for="ip in visibleFaultPodIps(row)" :key="ip" class="trace-chip">{{
                  ip
                }}</span
                ><span
                  v-if="faultPodIpCount(row) > visibleFaultPodIps(row).length"
                  class="trace-chip"
                  >+{{ faultPodIpCount(row) - visibleFaultPodIps(row).length }}</span
                >
              </div>
            </td>
            <td>
              <span class="trace-chip" :title="row.trace_id">{{ shortTraceId(row.trace_id) }}</span>
            </td>
            <td>
              <div class="evidence-actions">
                <span
                  v-for="tag in traceTags(row.trace_id, 'fault')"
                  :key="tag.type"
                  :class="['badge', tag.type === 'fault' ? 'badge-failed' : 'badge-warning']"
                  >{{ tag.label }}</span
                ><button class="btn btn-sm btn-primary" @click="openTraceDrawer(row)">
                  Trace / 日志
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer class="fault-table-footer">
      <span
        >{{ faultTraceQuery ? '查询结果' : faultTracesTruncated ? '当前范围已加载' : '共' }}
        {{ filteredFaultTraces.length }} 条</span
      >
      <PageNav
        v-if="faultTracePages > 1"
        :page="faultTracePage"
        :pages="faultTracePages"
        @update:page="faultTracePage = $event"
      />
    </footer>
  </section>
</template>

<style scoped>
.fault-compact-table th {
  height: 32px;
  padding: 0 8px;
  font-size: 12px;
  text-align: left;
  white-space: nowrap;
}

.fault-compact-table {
  width: 100%;
}

/* 窄屏不隐藏列：内容与宽屏一致，靠容器横向滑动看全。
   解除 nowrap 让较长单元格在容器宽度内换行收缩，避免固定列宽
   让内容伸出操作列 sticky 阈值、在其背后横向滚动 */
@media (max-width: 800px) {
  .fault-compact-table th,
  .fault-compact-table td {
    white-space: normal;
  }
}

.fault-compact-table th:last-child,
.fault-compact-table td:last-child {
  position: sticky;
  right: 0;
  z-index: 1;
  background: var(--surface);
  box-shadow: -8px 0 12px -12px rgba(31, 42, 58, 0.45);
}

.fault-compact-table th:last-child {
  z-index: 2;
  background: var(--bg);
}

.fault-compact-table tr:hover td:last-child {
  background: var(--primary-bg);
}

.fault-compact-table td {
  height: 34px;
  padding: 0 8px;
  font-size: 12px;
  line-height: 1.3;
  overflow: hidden;
}

.fault-compact-table .trace-chip {
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

.fault-compact-table .trace-pod-cell {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.fault-compact-table .trace-pod-cell .trace-chip {
  max-width: 74px;
}

.fault-compact-table .trace-pod-cell .more {
  background: var(--bg);
  color: var(--text2);
}

.fault-compact-table .cell-ellipsis {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.fault-compact-table .fault-code-chip {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  padding: 1px 6px;
  margin: 0;
}

/* P1.7 聚合事件表 */
.fault-agg-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.fault-agg-table th,
.fault-agg-table td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.fault-agg-table th {
  background: var(--bg);
  font-size: 12px;
  color: var(--text2);
  font-weight: 600;
}

.fault-agg-table th.sortable,
.fault-agg-pair-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.fault-agg-table th.sortable:hover,
.fault-agg-pair-table th.sortable:hover {
  color: var(--primary);
}

.fault-agg-table th.num,
.fault-agg-table td.num,
.fault-agg-pair-table th.num,
.fault-agg-pair-table td.num {
  text-align: right;
}

.sort-mark {
  margin-left: 2px;
  color: var(--primary);
}

.fault-agg-table tbody tr:not(.pair-subrow) {
  cursor: pointer;
}

.fault-agg-table tbody tr:not(.pair-subrow):hover {
  background: var(--primary-bg);
}

.fault-agg-table tr.row-expanded {
  background: var(--primary-bg);
}

.expand-mark {
  color: var(--text3);
  font-size: 12px;
}

.pair-subrow > td {
  background: var(--bg);
  padding: 10px 16px 12px 40px;
}

.fault-agg-pair-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.fault-agg-pair-table th,
.fault-agg-pair-table td {
  padding: 6px 10px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.fault-agg-pair-table th {
  background: var(--primary-bg);
  color: var(--text2);
  font-weight: 600;
}

.fault-agg-pair-table tbody tr:last-child td {
  border-bottom: none;
}
</style>
