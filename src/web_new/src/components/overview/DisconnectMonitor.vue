<script setup lang="ts">
import { onMounted } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'
import { normalizeFaultCodes, normalizeTraceOperation } from '../../utils/format'
import PageNav from '../common/PageNav.vue'

const {
  clearFaultRange,
  currentOp,
  enterFaultDetail,
  failureModeOf,
  faultChartData,
  faultChartRef,
  faultPodAgg,
  faultPodRef,
  faultPieRefs,
  faultTimeRange,
  faultTopoRef,
  faultTracePage,
  faultTracePages,
  faultTraceLoadedCount,
  faultTraceTotal,
  faultTracesTruncated,
  filteredFaultTraces,
  openTraceDrawer,
  pagedFaultTraces,
  renderFaultChart,
  renderFaultPieCharts,
  renderFaultPodChart,
  renderFaultTopology,
  traceTags,
} = useOverviewData()

onMounted(() => {
  renderFaultTopology()
  renderFaultPieCharts()
  renderFaultChart()
  renderFaultPodChart()
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
        >hover 节点/边查看详情；也可通过下方端点表用键盘查看故障 Trace</span
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
      异常 Trace 列表
      <span class="hint">{{
        faultTimeRange
          ? '当前范围：' + faultTimeRange.start + ' ~ ' + faultTimeRange.end
          : '未过滤，展示全部'
      }}</span>
    </h2>
    <div v-if="filteredFaultTraces.length === 0" class="empty" style="padding: 30px 0">
      <div class="icon">📭</div>
      <div>
        {{
          currentOp === 'GET'
            ? 'GET 无故障 Trace'
            : faultTimeRange
              ? '框选范围内无故障 Trace'
              : '暂无故障 Trace'
        }}
      </div>
    </div>
    <span v-if="filteredFaultTraces.length" class="mobile-table-hint"
      >窄屏下隐藏次要列；表格仍可左右滑动，操作列固定在右侧</span
    >
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
        >{{ faultTracesTruncated ? '当前范围已加载' : '共' }}
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
</style>
