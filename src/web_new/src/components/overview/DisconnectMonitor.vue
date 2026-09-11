<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'
import { normalizeFaultCodes, normalizeTraceOperation } from '../../utils/format'
import BlockTable from '../common/BlockTable.vue'
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
  faultCodeColor,
  faultCodeColorOrder,
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
const faultCodeColorsLimit = 5
const legendCodes = computed(() => faultCodeColorOrder.value.slice(0, faultCodeColorsLimit))
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
  <div class="analysis-range-bar">
    <div>
      <strong>当前范围</strong>
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
        <span class="fault-code-main"><b>全部故障</b></span>
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
          <h2>
            {{ selectedFaultCode ? `故障码 ${selectedFaultCode}` : '全部故障概览' }}
          </h2>
          <p v-if="selectedSummary">
            关联 {{ selectedSummary.traceCount }} 条 Trace，影响
            {{ selectedSummary.endpointCount }} 个端点、{{ selectedSummary.pairCount }} 条有向链路。
          </p>
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
        <h2 class="section-card-title">{{ scopeLabel }} · 发生趋势</h2>
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
        <h2 class="section-card-title">{{ scopeLabel }} · 影响链路与端点</h2>
      </div>
    </header>
    <div class="fault-impact-workbench">
      <div class="fault-topology-panel">
        <div class="fault-topology-meta">
          <span>{{ faultActivePairs.length }} 条链路</span>
          <span>{{ faultPodStats.length }} 个端点</span>
          <span>线宽 / 节点大小 = 故障 Trace 数</span>
          <span
            v-for="code in legendCodes"
            :key="code"
            class="topo-code-legend"
            :title="`故障码 ${code}`"
          >
            <i :style="{ background: faultCodeColor(code) }"></i>{{ code }}
          </span>
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
      <BlockTable
        :rows="pagedFaultTraces"
        :row-key="(row: any) => row.trace_id"
        :left-cols="['150px', '110px', '120px', '340px']"
        :right-cols="['190px']"
        :mid-cols="['200px', '260px', '220px']"
        mid-width="680px"
      >
        <template #left-head>
          <span>发生时间</span><span>故障类型</span><span>故障码</span><span>具体故障 / 故障域</span>
        </template>
        <template #left="{ row }">
          <span class="agg-mono col-nowrap">{{ (row.timestamp || '').slice(0, 19) }}</span>
          <span class="chip-row-nowrap">
            <span v-for="code in faultCodesOf(row)" :key="code" class="fault-code-chip">{{
              code
            }}</span>
            <span v-if="faultCodesOf(row).length === 0">-</span>
          </span>
          <span class="fault-type-cell">
            <span
              v-for="tag in traceTags(row.trace_id, 'fault')"
              :key="tag.type"
              :class="['badge', tag.type === 'fault' ? 'badge-failed' : 'badge-warning']"
              >{{ tag.label }}</span
            >
            <span v-if="traceTags(row.trace_id, 'fault').length === 0" class="hint">-</span>
          </span>
          <span>
            <span class="fault-name">{{ failureModeNamesOf(row) }}</span>
            <span class="fault-domain">{{ failureDomainsOf(row) }}</span>
          </span>
        </template>
        <template #mid-head>
          <span>影响链路</span><span>Pod 上下文</span><span>Trace ID</span>
        </template>
        <template #mid="{ row }">
          <span class="route-cell col-nowrap">
            <span>{{ row.src_ip || '-' }}</span><i>→</i><span>{{ row.dst_ip || '-' }}</span>
          </span>
          <span class="trace-pods col-nowrap" :title="faultPodIps(row).join('\n')">
            <span v-for="ip in visibleFaultPodIps(row)" :key="ip" class="trace-chip">{{ ip }}</span>
            <span v-if="faultPodIpCount(row) > visibleFaultPodIps(row).length" class="trace-chip"
              >+{{ faultPodIpCount(row) - visibleFaultPodIps(row).length }}</span
            >
          </span>
          <span class="col-nowrap">
            <span class="trace-chip" :title="row.trace_id">{{ shortTraceId(row.trace_id) }}</span>
          </span>
        </template>
        <template #right-head>证据</template>
        <template #right="{ row }">
          <span class="evidence-actions">
            <button class="btn btn-sm btn-primary" @click="openTraceDrawer(row)">Trace / 日志</button>
          </span>
        </template>
      </BlockTable>
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
.fault-detail-header h2 {
  margin: 5px 0 6px;
  font-size: 18px;
}
.fault-detail-header p,
.fault-section-header p {
  margin: 0;
  color: var(--text2);
  font-size: 12px;
  line-height: 1.6;
}
.fault-warning {
  padding: 10px 14px;
  margin-bottom: 14px;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  background: #fffbeb;
  color: #92400e;
  font-size: 12px;
  line-height: 1.6;
}
.fault-code-workbench {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  min-height: 310px;
  margin-bottom: 16px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.fault-code-catalog {
  padding: 14px;
  border-right: 1px solid var(--border);
  background: #f8fafc;
}
.fault-code-catalog header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
.fault-code-catalog header div {
  display: flex;
  gap: 8px;
  align-items: baseline;
}
.fault-code-catalog header span,
.fault-code-catalog header small {
  color: var(--text3);
  font-size: 10px;
}
.fault-code-item {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  width: 100%;
  padding: 9px;
  margin-bottom: 6px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: transparent;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}
.fault-code-item:hover,
.fault-code-item.active {
  border-color: #bfd0f5;
  background: #fff;
  box-shadow: 0 2px 8px rgba(31, 64, 117, 0.07);
}
.fault-code-item.active {
  box-shadow: inset 3px 0 var(--primary);
}
.fault-code-token {
  display: inline-flex;
  justify-content: center;
  padding: 4px 5px;
  border-radius: 6px;
  background: #fee2e2;
  color: #b91c1c;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  font-weight: 700;
}
.fault-code-token.all {
  background: #e8eefc;
  color: #34569b;
}
.fault-code-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.fault-code-main b,
.fault-code-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fault-code-main b {
  font-size: 12px;
}
.fault-code-main small {
  margin-top: 2px;
  color: var(--text3);
  font-size: 10px;
}
.fault-code-item > strong {
  color: var(--danger);
  font-size: 14px;
}
.fault-code-empty,
.failure-knowledge-empty,
.impact-empty {
  padding: 18px 8px;
  color: var(--text3);
  font-size: 12px;
  text-align: center;
}
.fault-code-detail {
  padding: 18px 20px;
  min-width: 0;
}
.fault-detail-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}
.fault-time-span {
  display: grid;
  grid-template-columns: auto auto;
  gap: 5px 12px;
  align-content: start;
  min-width: 260px;
  color: var(--text3);
  font-size: 10px;
}
.fault-time-span strong {
  color: var(--text2);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 500;
}
.failure-knowledge-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.failure-knowledge-card {
  padding: 12px;
  border: 1px solid #fecaca;
  border-radius: 9px;
  background: #fffafa;
}
.failure-knowledge-title {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 8px;
}
.failure-knowledge-title span {
  color: #b91c1c;
  font-size: 10px;
}
.failure-knowledge-title strong {
  font-size: 13px;
}
.failure-knowledge-card dl,
.failure-knowledge-card dd {
  margin: 0;
}
.failure-knowledge-card dl > div {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 8px;
  margin-top: 5px;
  font-size: 11px;
  line-height: 1.55;
}
.failure-knowledge-card dt {
  color: var(--text3);
}
.failure-knowledge-card dd {
  color: var(--text2);
}
.fault-section-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 10px;
}
.fault-section-header .section-card-title {
  margin: 3px 0;
}
.fault-chart-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text2);
  font-size: 11px;
}
.sample-warning {
  color: var(--warning);
}
.fault-trend-chart {
  height: 300px;
}
.fault-impact-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  min-height: 470px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 9px;
}
.fault-topology-panel {
  min-width: 0;
  border-right: 1px solid var(--border);
}
.fault-topology-meta {
  display: flex;
  gap: 16px;
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
  color: var(--text2);
  font-size: 10px;
}
.topo-code-legend {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  color: var(--text2);
}
.topo-code-legend i {
  width: 9px;
  height: 9px;
  border-radius: 2px;
}
.fault-topology {
  height: 430px;
}
.fault-impact-ranking {
  display: grid;
  grid-template-rows: 1fr 1fr;
  gap: 12px;
  padding: 12px;
  overflow: auto;
  background: #fbfcfe;
}
.fault-impact-ranking h3 {
  display: flex;
  justify-content: space-between;
  margin: 0 0 7px;
  font-size: 12px;
}
.fault-impact-ranking h3 small {
  color: var(--text3);
  font-weight: 400;
}
.impact-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  width: 100%;
  padding: 7px 8px;
  margin-bottom: 5px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: #fff;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}
.impact-row:hover {
  border-color: var(--primary);
  background: var(--primary-bg);
}
.impact-row > strong {
  color: var(--danger);
}
.impact-route,
.impact-row.endpoint > span {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 5px;
  min-width: 0;
  font-size: 10px;
}
.impact-row.endpoint > span {
  grid-template-columns: 1fr;
}
.impact-route b,
.impact-row.endpoint b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.impact-route i {
  color: var(--primary);
  font-style: normal;
}
.impact-route small,
.impact-row.endpoint small {
  grid-column: 1 / -1;
  color: var(--text3);
}
.trace-header {
  align-items: center;
}
.trace-search {
  display: flex;
  gap: 6px;
  align-items: center;
}
.trace-search .input {
  width: 270px;
}
.fault-instance-table {
  min-width: 1080px;
}
.fault-instance-table th,
.fault-instance-table td {
  padding: 8px 10px;
  font-size: 11px;
  vertical-align: middle;
}
.mono {
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.fault-name,
.fault-domain {
  display: block;
  max-width: 210px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fault-name {
  font-size: 11px;
}
.fault-domain {
  margin-top: 3px;
  color: var(--text3);
}
.route-cell {
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.route-cell i {
  margin: 0 5px;
  color: var(--primary);
  font-style: normal;
}
.trace-pods,
.evidence-actions {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: wrap;
}
.fault-instance-table th:last-child,
.fault-instance-table td:last-child {
  position: sticky;
  right: 0;
  z-index: 1;
  background: var(--surface);
  box-shadow: -8px 0 12px -12px rgba(31, 42, 58, 0.45);
}
.fault-instance-table th:last-child {
  z-index: 2;
  background: var(--bg);
}
.fault-table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  color: var(--text2);
  font-size: 12px;
}
.fault-empty {
  padding: 32px 0;
}
@media (max-width: 1000px) {
  .fault-code-workbench {
    grid-template-columns: 1fr;
  }
  .fault-code-catalog {
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
  .fault-impact-workbench {
    grid-template-columns: 1fr;
  }
  .fault-topology-panel {
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
}
@media (max-width: 700px) {
  .fault-journey ol {
    display: none;
  }
  .fault-detail-header,
  .fault-section-header,
  .trace-header {
    flex-direction: column;
  }
  .failure-knowledge-grid {
    grid-template-columns: 1fr;
  }
  .fault-time-span {
    min-width: 0;
  }
  .trace-search {
    width: 100%;
    flex-wrap: wrap;
  }
  .trace-search .input {
    width: 100%;
  }
}
</style>
