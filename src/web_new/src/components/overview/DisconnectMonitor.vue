<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'
import { normalizeFaultCodes, normalizeTraceOperation } from '../../utils/format'
import PageNav from '../common/PageNav.vue'

const {
  clearFaultRange,
  clearFaultTraceQuery,
  currentOp,
  enterFaultAggPairDetail,
  enterFaultDetail,
  failureModeOf,
  faultAggErrCodes,
  faultAggError,
  faultAggExpandedBucket,
  faultAggExpandedKey,
  faultAggInterval,
  faultAggIntervalOptions,
  faultAggLoading,
  faultAggPage,
  faultAggPages,
  faultAggPairs,
  faultAggPairsErrCodes,
  faultAggPairsLoading,
  faultAggPairsPage,
  faultAggPairsPages,
  faultAggPairsSortBy,
  faultAggPairsSortDesc,
  faultAggPairsSortField,
  faultAggPairsTotal,
  faultAggRows,
  faultAggSortBy,
  faultAggSortDesc,
  faultAggSortField,
  faultAggTotal,
  faultChartData,
  faultChartRef,
  faultChartSampled,
  faultChartScale,
  faultChartScaleOptions,
  faultPodAgg,
  faultPodRef,
  faultPieRefs,
  faultTimeRange,
  faultTopoRef,
  faultTraceIdInput,
  faultTracePage,
  faultTracePages,
  faultTraceLoadedCount,
  faultTraceQuery,
  faultTraceQueryError,
  faultTraceQueryLoading,
  faultTraceTotal,
  faultTracesTruncated,
  filteredFaultTraces,
  loadFaultAggEvents,
  loadFaultAggPairs,
  openTraceDrawer,
  pagedFaultTraces,
  queryFaultTraceById,
  renderFaultChart,
  renderFaultPieCharts,
  renderFaultPodChart,
  renderFaultTopology,
  toggleFaultAggBucket,
  traceTags,
} = useOverviewData()

onMounted(() => {
  renderFaultTopology()
  renderFaultPieCharts()
  renderFaultChart()
  renderFaultPodChart()
  void loadFaultAggEvents()
})

// 聚合尺度变化：重置排序/展开并按新尺度重查
watch(faultAggInterval, () => {
  faultAggSortField.value = 'timestamp'
  faultAggSortDesc.value = false
  faultAggExpandedKey.value = ''
  void loadFaultAggEvents(1)
})

const bucketKey = (row: { start_time: string; end_time: string }) =>
  `${row.start_time}|${row.end_time}`
const aggCount = (row: { status_code_cnt: Record<string, number> }, code: string) =>
  row.status_code_cnt?.[code] ?? 0

const faultPodIps = (row: any) =>
  row.pod_names?.length
    ? row.pod_names
    : row.pod_ips?.length
      ? row.pod_ips
      : [row.src_ip, row.dst_ip].filter(Boolean)
const visibleFaultPodIps = (row: any) => faultPodIps(row).slice(0, 2)
const faultPodIpCount = (row: any) => faultPodIps(row).length
const shortTraceId = (id: string) => (id?.length > 12 ? `${id.slice(0, 12)}…` : id || '-')
const joinList = (items: any[]) => (items || []).filter(Boolean).join(' / ') || '-'
const faultCodesOf = (row: any) => normalizeFaultCodes(row.status_code)
const faultModeName = (row: any) => failureModeOf(row.failure_mode)?.name || row.failure_mode || '-'
const faultModeDomain = (row: any) => failureModeOf(row.failure_mode)?.failure_domain || '-'
const faultModeTitle = (row: any) =>
  [
    faultCodesOf(row).length
      ? faultCodesOf(row)
          .map((code) => `故障码 ${code}`)
          .join('\n')
      : '故障码 -',
    faultModeName(row) !== '-' ? faultModeName(row) : '',
    faultModeDomain(row) !== '-' ? `故障域：${faultModeDomain(row)}` : '',
  ]
    .filter(Boolean)
    .join('\n')
</script>

<template>
  <div class="analysis-range-bar">
    <div>
      <strong>当前时间范围</strong>
      <span>{{
        faultTimeRange ? faultTimeRange.start + ' ~ ' + faultTimeRange.end : '全部时段'
      }}</span>
    </div>
    <button v-if="faultTimeRange" class="btn btn-sm btn-default" @click="clearFaultRange">
      恢复全部时段
    </button>
  </div>

  <div
    v-if="faultTracesTruncated"
    class="section-card"
    style="margin-bottom: 16px; border-color: #f59e0b; color: #92400e"
  >
    当前仅加载 {{ faultTraceLoadedCount }} / {{ faultTraceTotal }} 条故障
    Trace；本页拓扑、KPI、饼图、端点表与列表均基于已加载数据，不能视为全量结论。
  </div>

  <div class="chart-box" style="height: 440px; margin-bottom: 16px">
    <div class="chart-title">
      通断故障通信拓扑图（有向）
      <span class="hint" style="margin-left: auto"
        >点击节点/边查看该端点/链路当前范围的故障 Trace；hover 查看计数详情</span
      >
    </div>
    <div style="padding: 8px 12px; border-bottom: 1px solid var(--border)">
      <div class="topo-legend">
        <span class="lg"><span class="line-get"></span> 故障链路（实线）</span>
        <span class="lg"
          ><span class="dot-node" style="background: #ef4444"></span> 节点颜色=故障烈度</span
        >
        <span class="lg"
          ><span class="dot-node" style="background: #f59e0b"></span> 节点大小=故障次数</span
        >
      </div>
    </div>
    <div ref="faultTopoRef" style="height: 360px"></div>
  </div>

  <div class="pie-grid" style="margin-bottom: 16px">
    <div class="chart-box">
      <div class="chart-title">Pod 故障次数分布</div>
      <div
        class="chart-body"
        :ref="
          (el) => {
            if (el) faultPieRefs['faults'] = el as HTMLElement
          }
        "
      ></div>
    </div>
    <div class="chart-box">
      <div class="chart-title">故障码分布</div>
      <div
        class="chart-body"
        :ref="
          (el) => {
            if (el) faultPieRefs['codes'] = el as HTMLElement
          }
        "
      ></div>
    </div>
  </div>

  <div class="section-card">
    <h2 class="section-card-title">
      通断故障端点分析
      <span class="hint">基于当前时间范围内故障 Trace 的源/目标 IP 聚合</span>
    </h2>
    <div ref="faultPodRef" style="height: 240px"></div>
    <div class="table-wrap" style="margin-top: 12px">
      <table>
        <thead>
          <tr>
            <th>端点 IP</th>
            <th>故障次数</th>
            <th>故障码</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="fault in faultPodAgg" :key="fault.ip">
            <td style="font-family: monospace">{{ fault.ip }}</td>
            <td>{{ fault.faults }}</td>
            <td>
              <span class="fault-code-chip" v-for="code in fault.codes" :key="code"
                >故障码 {{ code }}</span
              >
            </td>
            <td>
              <button class="btn btn-sm btn-text" @click="enterFaultDetail(fault.ip)">
                查看故障 Trace
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="section-card">
    <h2 class="section-card-title">
      📈 故障码计数时序分布
      <span class="hint">拖拽选择时间范围，本页拓扑、KPI、饼图、端点表与 Trace 列表随之过滤</span>
      <span style="margin-left: auto; display: inline-flex; align-items: center; gap: 8px">
        <span
          v-if="faultChartSampled"
          class="hint"
          style="color: var(--warning)"
          title="单故障码秒级数据点达到加载上限，后端已抽稀；按尺度聚合后的桶计数不再精确"
          >⏳ 数据已抽稀，桶计数为近似</span
        >
        <label for="fault-chart-scale" class="hint">时间聚合尺度</label>
        <select id="fault-chart-scale" class="select" v-model.number="faultChartScale">
          <option v-for="opt in faultChartScaleOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </span>
    </h2>
    <div v-if="Object.keys(faultChartData).length === 0" class="empty" style="padding: 30px 0">
      <div class="icon">📭</div>
      <div>{{ currentOp === 'GET' ? '当前动作无故障码数据' : '暂无故障码数据' }}</div>
      <div class="hint">切换 SET 查看故障码时序</div>
    </div>
    <div v-else ref="faultChartRef" style="height: 300px"></div>
  </div>

  <div class="section-card">
    <h2 class="section-card-title">
      聚合事件表
      <span class="hint"
        >服务端按所选尺度分桶的时间 × IP
        对聚合下钻（对齐旧版）；不随日志文件选择收窄，时间右边界为闭区间，与主视图半开区间口径不同</span
      >
      <span style="margin-left: auto; display: inline-flex; align-items: center; gap: 8px">
        <label for="fault-agg-interval" class="hint">聚合尺度</label>
        <select id="fault-agg-interval" class="select" v-model="faultAggInterval">
          <option v-for="opt in faultAggIntervalOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </span>
    </h2>
    <div v-if="faultAggError" class="error-banner" style="margin-bottom: 10px">
      {{ faultAggError }}
    </div>
    <div v-if="faultAggLoading && faultAggRows.length === 0" class="empty" style="padding: 30px 0">
      <div class="icon">⏳</div>
      <div>聚合事件加载中…</div>
    </div>
    <div v-else-if="faultAggRows.length === 0" class="empty" style="padding: 30px 0">
      <div class="icon">📭</div>
      <div>{{ faultTimeRange ? '当前时间范围内无聚合故障事件' : '暂无聚合故障事件' }}</div>
    </div>
    <template v-else>
      <div class="table-wrap" role="region" tabindex="0" aria-label="通断聚合事件表，可左右滚动">
        <table class="fault-agg-table">
          <thead>
            <tr>
              <th style="width: 40px"></th>
              <th class="sortable" @click="faultAggSortBy('timestamp')">
                开始时间
                <span v-if="faultAggSortField === 'timestamp'" class="sort-mark">{{
                  faultAggSortDesc ? '↓' : '↑'
                }}</span>
              </th>
              <th>结束时间</th>
              <th
                v-for="code in faultAggErrCodes"
                :key="code"
                class="sortable num"
                @click="faultAggSortBy(code)"
              >
                {{ code === 'all' ? '全部' : `故障码 ${code}` }}
                <span v-if="faultAggSortField === code" class="sort-mark">{{
                  faultAggSortDesc ? '↓' : '↑'
                }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in faultAggRows" :key="bucketKey(row)">
              <tr
                :class="{ 'row-expanded': bucketKey(row) === faultAggExpandedKey }"
                @click="toggleFaultAggBucket(row)"
              >
                <td class="expand-mark">
                  {{ bucketKey(row) === faultAggExpandedKey ? '▾' : '▸' }}
                </td>
                <td style="font-family: monospace; font-size: 12px">{{ row.start_time }}</td>
                <td style="font-family: monospace; font-size: 12px">{{ row.end_time }}</td>
                <td v-for="code in faultAggErrCodes" :key="code" class="num">
                  {{ aggCount(row, code) || '-' }}
                </td>
              </tr>
              <tr v-if="bucketKey(row) === faultAggExpandedKey" class="pair-subrow">
                <td :colspan="3 + faultAggErrCodes.length">
                  <div v-if="faultAggPairsLoading" class="hint" style="padding: 8px 0">
                    IP 对加载中…
                  </div>
                  <div v-else-if="faultAggPairs.length === 0" class="hint" style="padding: 8px 0">
                    该时间桶内无源/目标 IP 对
                  </div>
                  <template v-else>
                    <table class="fault-agg-pair-table">
                      <thead>
                        <tr>
                          <th>源 IP</th>
                          <th>目标 IP</th>
                          <th
                            v-for="code in faultAggPairsErrCodes"
                            :key="code"
                            class="sortable num"
                            @click.stop="faultAggPairsSortBy(code)"
                          >
                            {{ code === 'all' ? '全部' : `故障码 ${code}` }}
                            <span v-if="faultAggPairsSortField === code" class="sort-mark">{{
                              faultAggPairsSortDesc ? '↓' : '↑'
                            }}</span>
                          </th>
                          <th>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="pair in faultAggPairs" :key="pair.src_ip + '→' + pair.dst_ip">
                          <td style="font-family: monospace">{{ pair.src_ip }}</td>
                          <td style="font-family: monospace">{{ pair.dst_ip }}</td>
                          <td v-for="code in faultAggPairsErrCodes" :key="code" class="num">
                            {{ aggCount(pair, code) || '-' }}
                          </td>
                          <td>
                            <button
                              class="btn btn-sm btn-text"
                              @click.stop="
                                enterFaultAggPairDetail(
                                  pair.src_ip,
                                  pair.dst_ip,
                                  faultAggExpandedBucket!,
                                )
                              "
                            >
                              查看故障 Trace
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    <div
                      style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-top: 8px;
                      "
                    >
                      <span style="font-size: 12px; color: var(--text2)"
                        >共 {{ faultAggPairsTotal }} 对</span
                      >
                      <PageNav
                        v-if="faultAggPairsPages > 1"
                        :page="faultAggPairsPage"
                        :pages="faultAggPairsPages"
                        @update:page="loadFaultAggPairs"
                      />
                    </div>
                  </template>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div
        style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px"
      >
        <span style="font-size: 13px; color: var(--text2)"
          >共 {{ faultAggTotal }} 桶{{ faultAggLoading ? ' · 刷新中…' : '' }}</span
        >
        <PageNav
          v-if="faultAggPages > 1"
          :page="faultAggPage"
          :pages="faultAggPages"
          @update:page="loadFaultAggEvents"
        />
      </div>
    </template>
  </div>

  <div class="section-card">
    <h2 class="section-card-title">
      异常 Trace 列表
      <span class="hint">{{
        faultTraceQuery
          ? 'Trace ID 查询结果'
          : faultTimeRange
            ? '当前范围：' + faultTimeRange.start + ' ~ ' + faultTimeRange.end
            : '未过滤，展示全部'
      }}</span>
    </h2>
    <div class="filter-bar" style="margin-bottom: 10px">
      <form
        style="display: flex; gap: 6px; align-items: center"
        @submit.prevent="queryFaultTraceById"
      >
        <input
          class="input"
          style="width: 300px"
          v-model="faultTraceIdInput"
          placeholder="输入 Trace ID 查询"
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
          恢复时间范围列表
        </button>
      </form>
      <span class="hint" style="margin-left: auto">服务端查询，不受已加载条数上限影响</span>
    </div>
    <div v-if="faultTraceQueryError" class="error-banner" style="margin-bottom: 10px">
      {{ faultTraceQueryError }}
    </div>
    <div v-if="faultTraceQuery" class="analysis-range-bar" style="margin-bottom: 10px">
      <div>
        <strong>Trace ID 查询结果</strong>
        <span>{{ faultTraceQuery.id }} · 共 {{ faultTraceQuery.total }} 条</span>
      </div>
    </div>
    <div v-if="filteredFaultTraces.length === 0" class="empty" style="padding: 30px 0">
      <div class="icon">📭</div>
      <div>
        {{
          faultTraceQuery
            ? '未查询到该 Trace ID 的异常 Trace'
            : currentOp === 'GET'
              ? 'GET 无故障 Trace'
              : faultTimeRange
                ? '框选范围内无故障 Trace'
                : '暂无故障 Trace'
        }}
      </div>
    </div>
    <div
      v-if="filteredFaultTraces.length"
      class="table-wrap fault-table-wrap"
      role="region"
      tabindex="0"
      aria-label="通断异常 Trace 列表，可左右滚动"
    >
      <table class="fault-compact-table">
        <colgroup>
          <col style="width: 86px" />
          <col style="width: 132px" />
          <col style="width: 128px" />
          <col style="width: 168px" />
          <col style="width: 96px" />
          <col style="width: 100px" />
          <col style="width: 64px" />
          <col style="width: 176px" />
          <col style="width: 110px" />
          <col style="width: 140px" />
        </colgroup>
        <thead>
          <tr>
            <th>故障类型</th>
            <th>时间</th>
            <th>Trace ID</th>
            <th>Pod IP</th>
            <th>集群</th>
            <th>主机IP</th>
            <th>操作类型</th>
            <th>故障码 / 故障名称</th>
            <th>故障域</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in pagedFaultTraces" :key="row.trace_id">
            <td>
              <div class="task-actions">
                <span
                  v-for="tag in traceTags(row.trace_id, 'fault')"
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
              <span class="trace-chip" :title="row.trace_id">{{ shortTraceId(row.trace_id) }}</span>
            </td>
            <td>
              <div class="trace-pod-cell" :title="faultPodIps(row).join('\n')">
                <span v-for="ip in visibleFaultPodIps(row)" :key="ip" class="trace-chip">{{
                  ip
                }}</span>
                <span
                  v-if="faultPodIpCount(row) > visibleFaultPodIps(row).length"
                  class="trace-chip more"
                >
                  +{{ faultPodIpCount(row) - visibleFaultPodIps(row).length }}
                </span>
              </div>
            </td>
            <td>
              <span class="cell-ellipsis" :title="joinList(row.cluster_names)">{{
                joinList(row.cluster_names)
              }}</span>
            </td>
            <td>
              <span class="cell-ellipsis" :title="joinList(row.host_names)">{{
                joinList(row.host_names)
              }}</span>
            </td>
            <td>{{ normalizeTraceOperation(row.operation) }}</td>
            <td>
              <span class="fault-code-chip" :title="faultModeTitle(row)">
                {{ faultCodesOf(row).length ? '故障码 ' + faultCodesOf(row).join(' / ') : '-' }}
              </span>
            </td>
            <td>
              <span class="cell-ellipsis" :title="faultModeDomain(row)">{{
                faultModeDomain(row)
              }}</span>
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
      <span style="font-size: 13px; color: var(--text2)"
        >{{ faultTraceQuery ? '查询结果' : faultTracesTruncated ? '当前范围已加载' : '共' }}
        {{ filteredFaultTraces.length }} 条</span
      >
      <PageNav
        v-if="faultTracePages > 1"
        :page="faultTracePage"
        :pages="faultTracePages"
        @update:page="faultTracePage = $event"
      />
    </div>
  </div>
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
  min-width: 1180px;
  table-layout: fixed;
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

@media (max-width: 800px) {
  .fault-compact-table {
    min-width: 760px;
  }

  .fault-compact-table :is(col, th, td):nth-child(1),
  .fault-compact-table :is(col, th, td):nth-child(5),
  .fault-compact-table :is(col, th, td):nth-child(6),
  .fault-compact-table :is(col, th, td):nth-child(9) {
    display: none;
  }
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
