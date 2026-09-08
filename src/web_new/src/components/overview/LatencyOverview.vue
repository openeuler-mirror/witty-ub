<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'
import PageNav from '../common/PageNav.vue'

// P0.1：只注入时延/拓扑/Pod 所需状态
const {
  analysisModule,
  analysisWindowLoading,
  anomalyRef,
  clearAnalysisTime,
  currentOp,
  enterLinkDetail,
  enterPodDetail,
  filteredPodStats,
  focusPairs,
  ipRowRefs,
  latencyFilter,
  overview,
  overviewScale,
  overviewScaleOptions,
  pagedPodIpsCb,
  pagedPodStats,
  podIpCbPage,
  podIpCbPages,
  podPage,
  podPageSize,
  podPages,
  podStageFlow,
  podStageFullLegend,
  renderAnomalyChart,
  renderTopology,
  resetOverviewFilter,
  resetTopologyFilter,
  selectedTopologyLink,
  selectedTopologyNode,
  selectTopologyLink,
  selectTopologyNode,
  showLinkEndsOnly,
  showPodIpCb,
  timeRangeLabel,
  timelineTruncated,
  topoHiddenCount,
  topoNodeLimit,
  topoRef,
  topoShowAll,
  topoTotalCount,
  topologySummary,
  uniquePodIps,
  visibleTopologyLinks,
} = useOverviewData()

const topologyRankPage = ref(1)
const topologyRankPageSize = 5

// 模板桥接：AnalysisFilter 内嵌 ref 在模板中不自动解包
const timeMode = computed(() => latencyFilter.time.value.mode)
const nodeWhitelist = computed<string[]>({
  get: () => latencyFilter.nodeWhitelist.value,
  set: (value) => latencyFilter.showOnlyNodes(value),
})
const topologyRankPages = computed(() =>
  Math.max(1, Math.ceil(visibleTopologyLinks.value.length / topologyRankPageSize)),
)
const pagedTopologyLinks = computed(() =>
  visibleTopologyLinks.value.slice(
    (topologyRankPage.value - 1) * topologyRankPageSize,
    topologyRankPage.value * topologyRankPageSize,
  ),
)

watch(visibleTopologyLinks, () => {
  topologyRankPage.value = Math.min(topologyRankPage.value, topologyRankPages.value)
})

let topologyResizeObserver: ResizeObserver | null = null
let topologyResizeFrame = 0

onMounted(() => {
  renderAnomalyChart()
  renderTopology()
  if (topoRef.value) {
    topologyResizeObserver = new ResizeObserver(() => {
      cancelAnimationFrame(topologyResizeFrame)
      topologyResizeFrame = requestAnimationFrame(renderTopology)
    })
    topologyResizeObserver.observe(topoRef.value)
  }
})

onBeforeUnmount(() => {
  topologyResizeObserver?.disconnect()
  cancelAnimationFrame(topologyResizeFrame)
})
</script>

<template>
  <template v-if="analysisModule.latency === 'overview'">
    <div class="filter-bar display-tools">
      <strong class="filter-bar-title">显示设置</strong>
      <label for="overview-top-k">TopK</label>
      <select id="overview-top-k" class="select" v-model.number="overview.topK">
        <option>5</option>
        <option>10</option>
        <option>20</option>
        <option>50</option>
      </select>
      <label for="overview-sort">排序</label>
      <select id="overview-sort" class="select" v-model="overview.sortBy">
        <option value="">默认</option>
        <option value="total_desc">结果数↓</option>
        <option value="total_asc">结果数↑</option>
        <option value="anomaly_desc">异常数↓</option>
        <option value="anomaly_asc">异常数↑</option>
      </select>
      <label for="overview-stat">统计</label>
      <select id="overview-stat" class="select" v-model="overview.statType">
        <option>ave</option>
        <option>p95</option>
        <option>p99</option>
        <option>min</option>
        <option>max</option>
      </select>
      <label for="overview-scale">时间聚合尺度</label>
      <select id="overview-scale" class="select" v-model.number="overviewScale">
        <option v-for="opt in overviewScaleOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
      <div style="margin-left: auto; display: flex; gap: 6px; flex-wrap: wrap; align-items: center">
        <span v-if="analysisWindowLoading" style="font-size: 12px; color: var(--text3)"
          >按窗加载中…</span
        >
        <button class="btn btn-sm btn-default" @click="resetOverviewFilter">重置显示设置</button>
      </div>
    </div>

    <!-- 时段异常强度：时间控制器（P0.3） -->
    <p class="chart-scale-hint">
      缩放时间范围（滚轮/滑块）或点击柱体选中该时段，下方拓扑与端点列表随所选时段联动；点击「全时段」恢复全域
    </p>
    <div class="chart-box" style="margin-bottom: 12px">
      <div class="chart-title">
        各时段异常请求数与总时延走势（{{ currentOp }}）
        <button
          type="button"
          class="select-bucket"
          :class="{ active: timeMode !== 'all' }"
          title="点击恢复全部时段"
          @click="clearAnalysisTime"
        >
          {{ timeRangeLabel }}
        </button>
        <span
          v-if="timelineTruncated"
          class="hint"
          style="color: var(--warning)"
          title="时间窗总数超出单次加载上限，当前仅加载部分异常桶，不得据此下结论全局最高值"
          >⏳ 数据已截断，仅部分时段入图</span
        >
        <span class="hint" style="margin-left: auto">缩放时间范围 / 点击柱体选中该时段</span>
      </div>
      <div ref="anomalyRef" style="height: 190px"></div>
    </div>

    <!-- 时延异常 IP 通信关系 -->
    <div class="chart-box topology-card" style="margin-bottom: 16px">
      <header class="chart-title topology-header">
        <span>IP 通信拓扑（{{ currentOp }} · {{ timeRangeLabel }}）</span>
        <div class="topology-actions">
          <button
            v-for="ip in nodeWhitelist"
            :key="ip"
            class="topo-chip"
            :title="'点击移除显示过滤：' + ip"
            @click="nodeWhitelist = nodeWhitelist.filter((item) => item !== ip)"
          >
            {{ ip }} ×
          </button>
          <button class="btn btn-sm btn-text" @click="showPodIpCb = !showPodIpCb">
            {{ showPodIpCb ? '▼' : '▶' }} 拓扑显示范围 {{ nodeWhitelist.length }} /
            {{ uniquePodIps.length }}
          </button>
          <button
            v-if="nodeWhitelist.length"
            class="btn btn-sm btn-text"
            @click="resetTopologyFilter"
          >
            清除显示范围
          </button>
        </div>
      </header>
      <div class="topology-meta">
        <div class="topology-summary" role="group" aria-label="当前通信关系摘要">
          <span
            >端点 <b>{{ topologySummary.nodeCount }}</b></span
          >
          <span
            >异常链路 <b>{{ topologySummary.linkCount }}</b></span
          >
          <span
            >异常桶内请求 <b>{{ topologySummary.totalCount.toLocaleString() }}</b></span
          >
          <span class="danger"
            >异常 Trace <b>{{ topologySummary.anomalyCount.toLocaleString() }}</b></span
          >
        </div>
        <span class="topology-identity-note">
          仅展示含时延异常 Trace 的 <code>src_ip → dst_ip</code>；端点 IP 不代表已识别的 Pod 身份
        </span>
      </div>
      <div class="topology-toolbar">
        <div class="topo-legend">
          <span class="lg"><i class="legend-node"></i>IP 端点</span>
          <span class="lg"
            ><i class="legend-line thin"></i><i class="legend-line thick"></i>线宽 =
            异常桶内请求量</span
          >
          <span class="lg"><i class="legend-line warning"></i>一般异常</span>
          <span class="lg"><i class="legend-line critical"></i>高异常率</span>
          <span
            class="lg"
            style="cursor: help"
            title="点击节点或连线即选中该对象（点空白取消）；下方 inspector 显示当前时段 × 当前对象；勾选「只显示节点」仅改变图上可见节点"
            >ⓘ 说明</span
          >
        </div>
      </div>
      <!-- 只显示节点面板（本地可视化白名单，不影响服务端查询） -->
      <div v-if="showPodIpCb" class="cb-group topology-filter-panel">
        <label v-for="ip in pagedPodIpsCb" :key="ip">
          <input type="checkbox" v-model="nodeWhitelist" :value="ip" /> {{ ip }}
        </label>
        <div
          style="
            width: 100%;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
          "
        >
          <div style="display: flex; gap: 4px">
            <button class="btn btn-sm btn-text" @click="nodeWhitelist = uniquePodIps.slice()">
              全选
            </button>
            <button class="btn btn-sm btn-text" @click="nodeWhitelist = []">清空勾选</button>
          </div>
          <div class="pagination" style="margin-top: 0" v-if="podIpCbPages > 1">
            <button
              aria-label="上一页拓扑端点"
              :disabled="podIpCbPage === 1"
              @click="podIpCbPage--"
            >
              ‹
            </button>
            <button
              v-for="page in podIpCbPages"
              :key="page"
              :class="{ active: podIpCbPage === page }"
              @click="podIpCbPage = page"
            >
              {{ page }}
            </button>
            <button
              aria-label="下一页拓扑端点"
              :disabled="podIpCbPage === podIpCbPages"
              @click="podIpCbPage++"
            >
              ›
            </button>
          </div>
        </div>
      </div>
      <div
        v-if="topoHiddenCount > 0 || (topoShowAll && topoTotalCount > topoNodeLimit)"
        class="topology-limit-note"
      >
        <template v-if="!topoShowAll && topoHiddenCount > 0">
          节点较多，已显示通信量 Top {{ topoNodeLimit }}（共 {{ topoTotalCount }} 个）·
          <button class="text-link-button" @click="topoShowAll = true">显示全部</button>
        </template>
        <template v-else>
          已显示全部 {{ topoTotalCount }} 个节点 ·
          <button class="text-link-button" @click="topoShowAll = false">
            仅看 Top {{ topoNodeLimit }}
          </button>
        </template>
      </div>
      <div class="topology-workbench">
        <div class="topology-canvas-wrap">
          <div ref="topoRef" class="topology-canvas"></div>
          <span class="topology-canvas-hint">端点环绕排列 · 箭头表示通信方向</span>
        </div>
        <aside class="topology-inspector" aria-label="异常链路排名与详情">
          <section class="topology-ranking-section">
            <div class="topology-panel-title">
              异常链路排名
              <small>共 {{ visibleTopologyLinks.length }} 条</small>
            </div>
            <div v-if="visibleTopologyLinks.length" class="topology-ranking">
              <button
                v-for="(link, index) in pagedTopologyLinks"
                :key="link.key"
                class="topology-rank-item"
                :class="{ active: selectedTopologyLink?.key === link.key }"
                @click="selectTopologyLink(link)"
              >
                <span class="rank">{{
                  (topologyRankPage - 1) * topologyRankPageSize + index + 1
                }}</span>
                <span class="route">
                  <b>{{ link.source }}</b>
                  <span>→ {{ link.target }}</span>
                  <i class="rate-track"
                    ><i :style="{ width: Math.max(4, link.anomalyRate * 100) + '%' }"></i
                  ></i>
                </span>
                <span class="rank-metric">
                  <b>{{ link.anomalyCount }} 异常</b>
                  <small>{{ (link.anomalyRate * 100).toFixed(1) }}%</small>
                </span>
              </button>
            </div>
            <div v-else class="topology-empty">当前筛选范围内没有异常通信关系</div>
            <div v-if="topologyRankPages > 1" class="topology-rank-pagination">
              <button
                aria-label="上一页异常链路"
                :disabled="topologyRankPage === 1"
                @click="topologyRankPage--"
              >
                ‹
              </button>
              <span>{{ topologyRankPage }} / {{ topologyRankPages }}</span>
              <button
                aria-label="下一页异常链路"
                :disabled="topologyRankPage === topologyRankPages"
                @click="topologyRankPage++"
              >
                ›
              </button>
            </div>
          </section>

          <section class="topology-detail">
            <template v-if="selectedTopologyLink">
              <div class="topology-panel-title">
                已选链路
                <button
                  class="topology-clear-selection"
                  @click="selectTopologyLink(selectedTopologyLink)"
                >
                  取消选择
                </button>
              </div>
              <div class="topology-route-title">
                {{ selectedTopologyLink.source }}
                <span>→</span>
                {{ selectedTopologyLink.target }}
              </div>
              <div class="topology-detail-grid">
                <span
                  >异常桶内请求<b>{{ selectedTopologyLink.totalCount.toLocaleString() }}</b></span
                >
                <span
                  >异常数<b>{{ selectedTopologyLink.anomalyCount.toLocaleString() }}</b></span
                >
                <span
                  >异常率<b>{{ (selectedTopologyLink.anomalyRate * 100).toFixed(1) }}%</b></span
                >
                <span
                  >URMA 总时延<b>{{
                    selectedTopologyLink.urmaTotal == null
                      ? '-'
                      : Number(selectedTopologyLink.urmaTotal).toFixed(1) + ' ms'
                  }}</b></span
                >
              </div>
              <div class="topology-detail-actions">
                <button
                  class="btn btn-sm btn-primary"
                  @click="enterLinkDetail(selectedTopologyLink.source, selectedTopologyLink.target)"
                >
                  查看链路 Trace
                </button>
                <button
                  class="btn btn-sm btn-default"
                  @click="showLinkEndsOnly(selectedTopologyLink)"
                >
                  仅显示链路两端
                </button>
                <button
                  class="btn btn-sm btn-text"
                  @click="enterPodDetail(selectedTopologyLink.source)"
                >
                  查看源端详情
                </button>
                <button
                  class="btn btn-sm btn-text"
                  @click="enterPodDetail(selectedTopologyLink.target)"
                >
                  查看目标端详情
                </button>
              </div>
            </template>
            <template v-else-if="selectedTopologyNode">
              <div class="topology-panel-title">
                已选端点
                <button
                  class="topology-clear-selection"
                  @click="selectTopologyNode(selectedTopologyNode.ip)"
                >
                  取消选择
                </button>
              </div>
              <div class="topology-route-title">{{ selectedTopologyNode.ip }}</div>
              <div class="topology-detail-grid">
                <span
                  >出方向<b>{{ selectedTopologyNode.srcCount.toLocaleString() }}</b></span
                >
                <span
                  >入方向<b>{{ selectedTopologyNode.dstCount.toLocaleString() }}</b></span
                >
                <span
                  >异常桶内请求<b>{{ selectedTopologyNode.total.toLocaleString() }}</b></span
                >
                <span
                  >异常数<b>{{ selectedTopologyNode.anomaly.toLocaleString() }}</b></span
                >
              </div>
              <div v-if="focusPairs.length" class="focus-pairs">
                <div class="topology-panel-title">该时段通信对</div>
                <button
                  v-for="pair in focusPairs"
                  :key="pair.src + '→' + pair.dst"
                  class="topology-rank-item"
                  @click="enterLinkDetail(pair.src, pair.dst)"
                >
                  <span class="route">
                    <b>{{ pair.src }}</b>
                    <span>→ {{ pair.dst }}</span>
                  </span>
                  <span class="rank-metric">
                    <b>{{ pair.anomaly }} 异常</b>
                    <small>{{ pair.total }} 请求</small>
                  </span>
                </button>
              </div>
              <button
                class="btn btn-sm btn-primary"
                @click="enterPodDetail(selectedTopologyNode.ip)"
              >
                查看端点 Trace
              </button>
            </template>
            <div v-else class="topology-detail-placeholder">
              点击图中节点、连线或上方排名，查看「当前时段 × 当前对象」指标；点空白取消选中。
            </div>
          </section>
        </aside>
      </div>
    </div>

    <!-- 端点时延故障列表（索引视图 + 时间窗联动） -->
    <div style="margin: 16px 0 4px; font-weight: 600; font-size: 14px">
      端点时延故障列表（{{ currentOp }} · {{ timeRangeLabel }}）
    </div>
    <div style="font-size: 12px; color: var(--text3); margin-bottom: 8px">
      行 = 单个端点
      IP（当前时段内作为源/目标汇总，默认按异常数排序）；「请求数」为异常桶内请求量，不代表故障严重度；各阶段时延
      =
      <b>所选时间段内按请求数加权的阶段平均耗时(均值)</b>；阶段指标后端仅提供均值（无每阶段
      P99/min/max）。悬停彩色条查看数值
    </div>
    <div
      v-if="nodeWhitelist.length"
      style="font-size: 12px; color: var(--text2); margin-bottom: 8px"
    >
      拓扑图仅显示 {{ nodeWhitelist.length }} 个勾选节点（不影响下方列表与查询） ·
      可在上方“拓扑显示范围”中调整
    </div>
    <div class="legend-strip">
      <span v-for="lg in podStageFullLegend" :key="lg.label" class="legend-strip-item">
        <i :style="{ background: lg.color }"></i>{{ lg.label }}
      </span>
    </div>
    <span class="mobile-table-hint">窄屏下可左右滑动表格，操作列固定在右侧</span>
    <div
      class="table-wrap endpoint-table-wrap"
      role="region"
      tabindex="0"
      aria-label="端点时延故障列表，可左右滚动"
    >
      <table class="endpoint-table">
        <colgroup>
          <col style="width: 130px" />
          <col style="width: 70px" />
          <col style="width: 70px" />
          <col style="width: 70px" />
          <col style="width: 60px" />
          <col style="width: 460px" />
          <col style="width: 76px" />
        </colgroup>
        <thead>
          <tr>
            <th>端点 IP</th>
            <th>出方向</th>
            <th>入方向</th>
            <th>请求数</th>
            <th>异常数</th>
            <th>各阶段时延（ms）</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="stat in pagedPodStats"
            :key="stat.ip"
            :class="{ 'focus-row': selectedTopologyNode?.ip === stat.ip }"
            :ref="
              (el) => {
                if (el) ipRowRefs[stat.ip] = el as HTMLElement
              }
            "
          >
            <td>
              <button
                type="button"
                class="text-link-button"
                title="点击选中该端点"
                @click="selectTopologyNode(stat.ip)"
              >
                {{ stat.ip }}
              </button>
            </td>
            <td>{{ stat.srcCount.toLocaleString() }}</td>
            <td>{{ stat.dstCount.toLocaleString() }}</td>
            <td>{{ stat.total.toLocaleString() }}</td>
            <td :style="{ color: stat.anomaly > 10 ? 'var(--danger)' : '' }">{{ stat.anomaly }}</td>
            <td class="stage-td">
              <div
                v-if="podStageFlow(stat).stages.some((s: any) => s.valueMs != null)"
                class="stage-zone"
              >
                <div class="stage-flow">
                  <div
                    v-for="s in podStageFlow(stat).stages"
                    :key="s.key"
                    class="stage-col"
                    :style="{ flex: '0 0 ' + s.pct + '%' }"
                  >
                    <div
                      class="stage-col-bar"
                      :style="{ background: s.color }"
                      :title="
                        s.label +
                        ' ' +
                        (s.valueMs != null ? s.valueMs + 'ms' : '-') +
                        (' (' + s.pct.toFixed(0) + '%)')
                      "
                    ></div>
                    <div class="stage-col-sub">
                      <div
                        v-for="c in s.children"
                        :key="c.label"
                        class="stage-sub"
                        :title="c.label + ' ' + (c.valueMs != null ? c.valueMs + 'ms' : '-')"
                      >
                        <span class="stage-sub-track"
                          ><i :style="{ width: c.rel + '%', background: c.color }"></i
                        ></span>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="stage-values">
                  <span
                    v-for="s in podStageFlow(stat).stages"
                    :key="'v' + s.key"
                    class="sv-item"
                    :title="s.label + ' ' + (s.valueMs != null ? s.valueMs + 'ms' : '-')"
                  >
                    <i :style="{ background: s.color }"></i>{{ s.label }}
                    {{ s.valueMs != null ? s.valueMs + 'ms' : '-' }}
                    <template v-if="s.children.some((c: any) => c.valueMs != null)">
                      <span class="sv-subs">
                        (<span
                          v-for="c in s.children.filter((x: any) => x.valueMs != null)"
                          :key="'s' + c.label"
                          class="sv-sub"
                          :title="c.label + ' ' + c.valueMs + 'ms'"
                          >{{ c.label }} {{ c.valueMs }}ms</span
                        >)
                      </span>
                    </template>
                  </span>
                </div>
              </div>
              <div v-else style="font-size: 12px; color: var(--text3)">-</div>
            </td>
            <td>
              <button class="btn btn-sm btn-primary" @click="enterPodDetail(stat.ip)">
                查看端点 Trace
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;
        font-size: 13px;
        color: var(--text2);
      "
    >
      <span>共 {{ filteredPodStats.length }} 个端点，每页 {{ podPageSize }} 个</span>
      <PageNav
        v-if="podPages > 1"
        :page="podPage"
        :pages="podPages"
        @update:page="podPage = $event"
      />
    </div>
  </template>
</template>

<style scoped>
.focus-row {
  background: rgba(79, 142, 247, 0.08);
}
.focus-pairs {
  margin: 10px 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
}
.focus-pairs .topology-rank-item {
  width: 100%;
  text-align: left;
}
.select-bucket {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text2);
  cursor: pointer;
  background: var(--bg);
  transition: all 0.15s;
}
.select-bucket::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text3);
}
.select-bucket.active {
  border-color: #ef4444;
  color: #ef4444;
}
.select-bucket.active::before {
  background: #ef4444;
}
.stage-flow {
  display: flex;
  align-items: flex-start;
  min-width: 0;
}
.stage-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.stage-col-bar {
  height: 14px;
  min-width: 2px;
  transition: filter 0.12s;
  cursor: default;
}
.stage-col:hover .stage-col-bar {
  filter: brightness(0.85);
}
.stage-col-sub {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-height: 0;
}
.stage-sub {
  display: flex;
  flex-direction: column;
  gap: 1px;
  cursor: default;
}
.stage-sub-track {
  display: block;
  height: 6px;
  border-radius: 2px;
  background: var(--bg);
  overflow: hidden;
}
.stage-sub-track i {
  display: block;
  height: 100%;
}
.stage-zone {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.stage-td {
  vertical-align: middle;
  padding: 6px 12px;
}
.stage-values {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 12px;
  align-items: baseline;
  font-size: 10px;
}
.sv-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
  color: var(--text);
  font-family: monospace;
}
.sv-item > i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: 0 0 auto;
  display: inline-block;
}
.sv-subs {
  display: inline-flex;
  gap: 6px;
  color: var(--text2);
}
.sv-sub {
  white-space: nowrap;
}
.legend-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  padding: 8px 12px;
  margin-bottom: 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}
.legend-strip-item {
  font-size: 11px;
  color: var(--text2);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.legend-strip-item i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
}
.topology-card {
  overflow: hidden;
}
.topology-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.topology-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
}
.topology-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
}
.topology-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  color: var(--text2);
  font-size: 11px;
}
.topology-summary b {
  color: var(--text);
  font-size: 12px;
}
.topology-summary .danger,
.topology-summary .danger b {
  color: var(--danger);
}
.topology-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 42px;
  padding: 7px 16px;
  border-bottom: 1px solid var(--border);
  background: #fff;
}
.topology-identity-note {
  color: var(--text3);
  font-size: 10px;
  text-align: right;
}
.topology-identity-note code {
  color: var(--text2);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.topo-legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.topo-legend .lg {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text2);
  font-size: 10px;
}
.legend-node {
  width: 10px;
  height: 10px;
  border: 1px solid #1d4ed8;
  border-radius: 50%;
  background: #4f8ef7;
}
.legend-line {
  width: 18px;
  height: 2px;
  border-radius: 2px;
}
.legend-line.thin {
  width: 10px;
  height: 2px;
  background: #64748b;
}
.legend-line.thick {
  width: 10px;
  height: 4px;
  margin-left: -5px;
  background: #475569;
}
.legend-line.warning {
  background: #ea580c;
}
.legend-line.critical {
  background: #dc2626;
}
.topology-filter-panel {
  margin: 10px 20px;
  padding: 10px;
  border: 1px solid #e1e8f1;
  border-radius: 10px;
  background: #f8fafc;
}
.topology-limit-note {
  padding: 6px 20px;
  border-bottom: 1px solid #e5eaf1;
  color: var(--text2);
  background: #fbfcfe;
  font-size: 11px;
}
.topology-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 350px;
  height: 560px;
  background: #fff;
}
.topology-canvas-wrap {
  position: relative;
  min-width: 0;
  height: 532px;
  margin: 14px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg);
}
.topology-canvas {
  height: 100%;
}
.topology-canvas-hint {
  position: absolute;
  right: 10px;
  bottom: 8px;
  color: var(--text3);
  font-size: 10px;
  pointer-events: none;
}
.topology-inspector {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 560px;
  padding: 14px 14px 14px 0;
  overflow: hidden;
  background: #fff;
}
.topology-ranking-section {
  flex: 0 0 348px;
  min-height: 0;
}
.topology-panel-title {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
  color: #273449;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.topology-panel-title small {
  color: var(--text3);
  font-weight: 400;
}
.topology-ranking {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.topology-rank-item {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  width: 100%;
  min-height: 51px;
  padding: 7px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: #fff;
  color: var(--text);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s;
}
.topology-rank-item:hover,
.topology-rank-item.active {
  border-color: #4f79d8;
  background: #f1f5ff;
  box-shadow: none;
}
.topology-rank-item.active {
  box-shadow: inset 3px 0 #6d28d9;
}
.topology-rank-item .rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  color: #718096;
  background: #f0f3f7;
  font-weight: 700;
  text-align: center;
}
.topology-rank-item .route,
.topology-rank-item .rank-metric {
  display: flex;
  flex-direction: column;
  min-width: 0;
  font-size: 11px;
}
.topology-rank-item .route b,
.topology-rank-item .route span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.topology-rank-item .route b {
  color: #26364e;
}
.topology-rank-item .route span {
  margin-top: 2px;
  color: #758297;
}
.rate-track {
  width: 100%;
  height: 3px;
  margin-top: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf0f4;
}
.rate-track > i {
  display: block;
  max-width: 100%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ea580c, #dc2626);
}
.topology-rank-item .rank-metric {
  align-items: flex-end;
  color: #d74455;
}
.topology-rank-item .rank-metric small {
  color: var(--text2);
}
.topology-detail {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: #fff;
}
.topology-rank-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  height: 28px;
  margin-top: 6px;
  color: var(--text2);
  font-size: 11px;
}
.topology-rank-pagination button,
.topology-clear-selection {
  border: 1px solid var(--border);
  border-radius: 4px;
  background: #fff;
  color: var(--text2);
  cursor: pointer;
}
.topology-rank-pagination button {
  width: 26px;
  height: 24px;
}
.topology-rank-pagination button:disabled {
  opacity: 0.4;
  cursor: default;
}
.topology-clear-selection {
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 400;
}
.topology-clear-selection:hover {
  color: var(--primary);
  border-color: var(--primary);
}
.topology-route-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  font-weight: 600;
}
.topology-route-title span {
  color: var(--primary);
}
.topology-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 10px;
}
.topology-detail-grid span {
  display: flex;
  flex-direction: column;
  padding: 7px;
  border: 1px solid #edf0f4;
  border-radius: 8px;
  background: #f8fafc;
  color: var(--text2);
  font-size: 11px;
}
.topology-detail-grid b {
  margin-top: 2px;
  color: var(--text);
  font-size: 13px;
}
.topology-detail-actions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.topology-detail-placeholder,
.topology-empty {
  padding: 14px 8px;
  color: var(--text3);
  font-size: 12px;
  line-height: 1.6;
}
@media (max-width: 1000px) {
  .topology-header,
  .topology-toolbar {
    align-items: stretch;
    flex-direction: column;
  }
  .topology-meta {
    align-items: flex-start;
    flex-direction: column;
  }
  .topology-identity-note {
    text-align: left;
  }
  .topology-workbench {
    grid-template-columns: 1fr;
    height: auto;
  }
  .topology-canvas-wrap {
    height: 430px;
  }
  .topology-inspector {
    height: auto;
    padding: 0 14px 14px;
    overflow: visible;
  }
  .topology-ranking-section {
    flex: none;
  }
  .topology-ranking {
    max-height: 280px;
    overflow-y: auto;
  }
}
</style>
