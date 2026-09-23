<script setup lang="ts">
import { onMounted } from 'vue'
import BlockTable from '../common/BlockTable.vue'
import PageNav from '../common/PageNav.vue'
import { useOverviewData } from '../../composables/useOverviewData'

// 只注入 UBSocket 通断故障监控所需状态
const {
  brpcAbnormalThreadPage,
  brpcAbnormalThreadTotal,
  brpcAbnormalThreads,
  brpcAggregatedEventPage,
  brpcAggregatedEventTotal,
  brpcAggregatedEventsTruncated,
  brpcEventInterfaceColumns,
  brpcEventWindowPageRows,
  brpcEventWindowPages,
  brpcEventWindows,
  brpcEventAggregation,
  brpcEventAggregationOptions,
  brpcEventWindowOptions,
  brpcEventWindowSize,
  brpcRowInterfaceCountOf,
  brpcThreadInterfaceColumns,
  brpcExpandedEventWindow,
  brpcFaultBatch,
  brpcFaultError,
  brpcFaultLoading,
  brpcFaultLogOptions,
  brpcFaultScale,
  brpcFaultScaleOptions,
  brpcFaultSelectedLogId,
  brpcFaultSeriesOptions,
  brpcFaultTab,
  brpcFaultThreadPages,
  brpcFaultTimelineRef,
  brpcFaultTimelineError,
  brpcFaultTimelineLoading,
  brpcFaultVisibleSeriesIds,
  brpcFaultZoomed,
  brpcThreadSearchInput,
  brpcThreadSearchQuery,
  brpcThreadListLoading,
  brpcEventListLoading,
  changeBrpcEventAggregation,
  changeBrpcFaultLog,
  changeBrpcEventWindowSize,
  clearBrpcFaultSeries,
  clearBrpcThreadSearch,
  goBrpcFaultEventsPage,
  goBrpcFaultThreadsPage,
  openBrpcFaultDetail,
  renderBrpcFaultTimeline,
  resetBrpcFaultZoom,
  selectAllBrpcFaultSeries,
  submitBrpcThreadSearch,
  toggleBrpcEventWindow,
  toggleBrpcFaultSeries,
} = useOverviewData()

onMounted(() => {
  renderBrpcFaultTimeline()
})
</script>

<template>
  <div v-if="brpcFaultError" class="error-banner">{{ brpcFaultError }}</div>
  <div class="operate-bar" v-if="brpcFaultLogOptions.length > 0">
    <div style="display: flex; align-items: center; gap: 8px">
      <span style="font-size: 13px; color: var(--text2)">UBSocket 日志:</span>
      <select class="select" v-model="brpcFaultSelectedLogId" @change="changeBrpcFaultLog">
        <option v-for="option in brpcFaultLogOptions" :key="option.id" :value="option.id">
          {{ option.name }}
        </option>
      </select>
      <span v-if="brpcFaultLoading" class="hint">加载中…</span>
    </div>
  </div>
  <!-- 首屏才用整块加载态；切换日志/翻页时页面保持可见，仅就地提示 -->
  <div v-if="brpcFaultLoading && !brpcFaultBatch" class="empty" style="padding: 28px 0">
    <div class="icon">⏳</div>
    <div>正在加载 UBSocket 故障监控数据...</div>
  </div>
  <div v-else-if="brpcFaultLogOptions.length === 0" class="empty" style="padding: 36px 0">
    <div class="icon">📭</div>
    <div>暂无已运行 UBSocket 诊断的日志</div>
    <div class="hint">在任务管理中创建 UBSocket 任务并运行诊断后，可在此查看通断故障监控</div>
  </div>
  <template v-else>
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-num">{{ brpcFaultBatch?.hit_count ?? 0 }}</div>
        <div class="kpi-label">诊断命中数</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num">{{ brpcAggregatedEventTotal }}</div>
        <div class="kpi-label">聚合事件数</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num">{{ brpcAbnormalThreadTotal }}</div>
        <div class="kpi-label">异常 Thread 数</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-num" style="font-size: 15px">
          {{ brpcFaultBatch ? (brpcFaultBatch.start_time || '').slice(0, 16) : '—' }}
        </div>
        <div class="kpi-label">批次开始</div>
      </div>
    </div>

    <div class="section-card">
      <div class="section-card-title">
        UBSocket 公共API故障时序分布
        <span style="margin-left: auto; display: inline-flex; align-items: center; gap: 8px">
          <button
            v-if="brpcFaultZoomed"
            class="btn btn-sm btn-text"
            type="button"
            @click="resetBrpcFaultZoom"
          >
            重置缩放
          </button>
          <label class="hint" for="brpc-fault-scale">时间聚合尺度</label>
          <select id="brpc-fault-scale" class="select" v-model.number="brpcFaultScale">
            <option
              v-for="option in brpcFaultScaleOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
          <span v-if="brpcFaultTimelineLoading" class="hint">加载中…</span>
        </span>
      </div>
      <p class="monitor-card-hint">
        横坐标会根据时间范围缩放；聚合尺度按后端预聚合桶查询，拖动下方滑块可框选时间范围
      </p>
      <div v-if="brpcFaultTimelineError" class="error-banner">{{ brpcFaultTimelineError }}</div>
      <div v-if="brpcFaultSeriesOptions.length > 0" class="series-toggle">
        <span class="series-toggle-label">曲线选择：</span>
        <span class="series-toggle-count">
          已选 {{ brpcFaultVisibleSeriesIds.length }}/{{ brpcFaultSeriesOptions.length }}
        </span>
        <button class="btn btn-sm btn-text" type="button" @click="selectAllBrpcFaultSeries">
          全选
        </button>
        <button class="btn btn-sm btn-text" type="button" @click="clearBrpcFaultSeries">
          清空
        </button>
        <label
          v-for="series in brpcFaultSeriesOptions"
          :key="series.id"
          class="series-toggle-option"
        >
          <input
            type="checkbox"
            :checked="brpcFaultVisibleSeriesIds.includes(series.id)"
            @change="toggleBrpcFaultSeries(series.id)"
          />
          <span class="series-dot" :style="{ backgroundColor: series.color }"></span>
          {{ series.label }}
        </label>
      </div>
      <div ref="brpcFaultTimelineRef" style="height: 320px"></div>
    </div>

    <div class="fault-result-bar">
      <div class="view-tabs" role="tablist" aria-label="UBSocket 故障结果视图">
        <button
          type="button"
          role="tab"
          :aria-selected="brpcFaultTab === 'event'"
          :class="['view-tab', { active: brpcFaultTab === 'event' }]"
          @click="brpcFaultTab = 'event'"
        >
          聚合事件
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="brpcFaultTab === 'thread'"
          :class="['view-tab', { active: brpcFaultTab === 'thread' }]"
          @click="brpcFaultTab = 'thread'"
        >
          异常 Thread
        </button>
      </div>
      <!-- 聚合指标固定为 Pod IP（异常 Thread 视图即线程聚合），时间间隔走服务端 window_size -->
      <div v-if="brpcFaultTab === 'event'" class="fault-result-controls">
        <span class="hint">聚合指标</span>
        <select
          id="brpc-event-aggregation"
          class="select"
          aria-label="聚合指标"
          v-model="brpcEventAggregation"
          @change="changeBrpcEventAggregation"
        >
          <option
            v-for="option in brpcEventAggregationOptions"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </option>
        </select>
        <label class="hint" for="brpc-event-window">时间间隔</label>
        <select
          id="brpc-event-window"
          class="select"
          v-model="brpcEventWindowSize"
          @change="changeBrpcEventWindowSize"
        >
          <option
            v-for="option in brpcEventWindowOptions"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </option>
        </select>
      </div>
    </div>

    <template v-if="brpcFaultTab === 'event'">
      <div v-if="brpcEventWindows.length === 0" class="empty" style="padding: 28px 0">
        <div class="icon">📭</div>
        <div>暂无聚合事件</div>
      </div>
      <template v-else>
        <p class="monitor-card-hint">
          聚合口径：时间窗 × 接口命中数（同一窗口内所有 Pod 求和）；点「明细」展开该窗的 Pod
          逐行结果
        </p>
        <div class="agg-table">
          <!-- 左固定：时间窗 + 故障总数；展开后为 Pod/线程 明细 -->
          <div class="agg-block agg-left">
            <div class="agg-row agg-head agg-left-main">
              <span class="col-nowrap">时间窗</span>
              <span class="col-num">故障总数</span>
            </div>
            <template v-for="window in brpcEventWindowPageRows" :key="`l-${window.key}`">
              <div class="agg-row agg-left-main">
                <span class="col-nowrap agg-mono">{{ window.start }} ~ {{ window.end }}</span>
                <span class="col-num"
                  ><b>{{ window.total }}</b></span
                >
              </div>
              <template v-if="brpcExpandedEventWindow === window.key">
                <div class="agg-row agg-subhead agg-left-sub">
                  <span>Pod IP</span><span>Pod 名称</span><span class="col-num">命中数</span>
                </div>
                <div
                  v-for="pod in window.pods"
                  :key="`lp-${pod.event_id}`"
                  class="agg-row agg-subrow agg-left-sub"
                >
                  <span class="col-nowrap agg-mono">{{ pod.pod_ip }}</span>
                  <span class="col-nowrap">{{ pod.pod_name || '-' }}</span>
                  <span class="col-num">{{ pod.hitTotal }}</span>
                </div>
              </template>
            </template>
          </div>

          <!-- 中间：接口列矩阵，超出宽度时本块横向滚动 -->
          <div class="agg-block agg-mid">
            <div
              class="agg-mid-inner"
              :style="{ width: brpcEventInterfaceColumns.length * 132 + 'px' }"
            >
              <div class="agg-row agg-head agg-mid-grid">
                <div
                  v-for="column in brpcEventInterfaceColumns"
                  :key="column.id"
                  class="col-num matrix-head-cell"
                  :title="`${column.component} / ${column.interfaceName} / ${column.functionName}`"
                >
                  <small class="matrix-head-component">{{ column.component }}</small>
                  <span class="matrix-head-name">{{ column.interfaceName }}</span>
                  <code class="matrix-head-function">{{ column.functionName }}</code>
                </div>
              </div>
              <template v-for="window in brpcEventWindowPageRows" :key="`m-${window.key}`">
                <div class="agg-row agg-mid-grid">
                  <div v-for="column in brpcEventInterfaceColumns" :key="column.id" class="col-num">
                    <span :class="{ 'matrix-zero': !window.byInterface[column.id] }">
                      {{ window.byInterface[column.id] ?? '-' }}
                    </span>
                  </div>
                </div>
                <template v-if="brpcExpandedEventWindow === window.key">
                  <div class="agg-row agg-subhead agg-mid-grid">
                    <div
                      v-for="column in brpcEventInterfaceColumns"
                      :key="column.id"
                      class="agg-mono"
                    >
                      {{ column.functionName }}
                    </div>
                  </div>
                  <div
                    v-for="pod in window.pods"
                    :key="`mp-${pod.event_id}`"
                    class="agg-row agg-subrow agg-mid-grid"
                  >
                    <div
                      v-for="column in brpcEventInterfaceColumns"
                      :key="column.id"
                      class="col-num"
                    >
                      <span :class="{ 'matrix-zero': !brpcRowInterfaceCountOf(pod, column.id) }">
                        {{ brpcRowInterfaceCountOf(pod, column.id) || '-' }}
                      </span>
                    </div>
                  </div>
                </template>
              </template>
            </div>
          </div>

          <!-- 右固定：操作 -->
          <div class="agg-block agg-right">
            <div class="agg-row agg-head agg-right-main">操作</div>
            <template v-for="window in brpcEventWindowPageRows" :key="`r-${window.key}`">
              <div class="agg-row agg-right-main">
                <button
                  class="btn btn-sm btn-default"
                  type="button"
                  @click="toggleBrpcEventWindow(window.key)"
                >
                  {{ brpcExpandedEventWindow === window.key ? '收起' : '明细' }}
                </button>
              </div>
              <template v-if="brpcExpandedEventWindow === window.key">
                <div class="agg-row agg-subhead agg-right-sub">操作</div>
                <div
                  v-for="pod in window.pods"
                  :key="`rp-${pod.event_id}`"
                  class="agg-row agg-subrow agg-right-sub"
                >
                  <button class="btn btn-sm btn-primary" @click="openBrpcFaultDetail(pod)">
                    查看接口命中
                  </button>
                </div>
              </template>
            </template>
          </div>
        </div>
        <div v-if="brpcAggregatedEventsTruncated" class="error-banner" style="margin-top: 10px">
          聚合事件共 {{ brpcAggregatedEventTotal }} 条，已加载前 500 条用于聚合，结果可能不完整
        </div>
        <div class="table-foot">
          <span class="hint">
            共 {{ brpcEventWindows.length }} 个时间窗 / {{ brpcAggregatedEventTotal }} 条 Pod 记录
            <template v-if="brpcEventListLoading"> · 刷新中…</template>
          </span>
          <PageNav
            v-if="brpcEventWindowPages > 1"
            :page="brpcAggregatedEventPage"
            :pages="brpcEventWindowPages"
            @update:page="goBrpcFaultEventsPage"
          />
        </div>
      </template>
    </template>

    <template v-else>
      <!-- 异常 Thread 服务端搜索（线程 ID / Pod IP / Pod 名） -->
      <div class="filter-bar" style="margin-bottom: 10px">
        <form
          style="display: flex; gap: 6px; align-items: center"
          @submit.prevent="submitBrpcThreadSearch"
        >
          <input
            class="input"
            style="width: 280px"
            v-model="brpcThreadSearchInput"
            placeholder="搜索线程 ID、Pod IP、Pod 名称"
            aria-label="搜索异常 Thread"
          />
          <button class="btn btn-sm btn-primary" type="submit" :disabled="brpcFaultLoading">
            搜索
          </button>
          <button
            v-if="brpcThreadSearchInput || brpcThreadSearchQuery"
            class="btn btn-sm btn-default"
            type="button"
            @click="clearBrpcThreadSearch"
          >
            清除
          </button>
        </form>
        <span v-if="brpcThreadSearchQuery" class="hint" style="margin-left: auto">
          搜索：{{ brpcThreadSearchQuery }}
        </span>
      </div>
      <div v-if="brpcAbnormalThreads.length === 0" class="empty" style="padding: 28px 0">
        <div class="icon">📭</div>
        <div>{{ brpcThreadSearchQuery ? '未搜索到匹配的异常 Thread' : '暂无异常 Thread' }}</div>
      </div>
      <div v-else class="table-wrap">
        <BlockTable
          :rows="brpcAbnormalThreads"
          :row-key="(row: any) => row.thread_key"
          :left-cols="['110px', '130px', '150px', '96px']"
          :mid-width="brpcThreadInterfaceColumns.length * 132 + 'px'"
        >
          <template #left-head>
            <span class="col-nowrap">线程ID</span>
            <span class="col-nowrap">Pod IP</span>
            <span class="col-nowrap">Pod 名称</span>
            <span class="col-num">命中数</span>
          </template>
          <template #left="{ row: thread }">
            <span class="col-nowrap">
              <span class="thread-id-pill" :title="thread.thread_key">{{ thread.thread_id }}</span>
            </span>
            <span class="col-nowrap agg-mono">{{ thread.pod_ip }}</span>
            <span class="col-nowrap">{{ thread.pod_name || '-' }}</span>
            <span class="col-num">{{ thread.total_interface_hit_count }}</span>
          </template>
          <template #mid-head>
            <div
              v-for="column in brpcThreadInterfaceColumns"
              :key="column.id"
              class="col-num matrix-head-cell"
              :title="`${column.component} / ${column.interfaceName} / ${column.functionName}`"
            >
              <small class="matrix-head-component">{{ column.component }}</small>
              <span class="matrix-head-name">{{ column.interfaceName }}</span>
              <code class="matrix-head-function">{{ column.functionName }}</code>
            </div>
          </template>
          <template #mid="{ row: thread }">
            <div v-for="column in brpcThreadInterfaceColumns" :key="column.id" class="col-num">
              <span :class="{ 'matrix-zero': !brpcRowInterfaceCountOf(thread, column.id) }">
                {{ brpcRowInterfaceCountOf(thread, column.id) || '-' }}
              </span>
            </div>
          </template>
          <template #right-head>操作</template>
          <template #right="{ row: thread }">
            <button class="btn btn-sm btn-primary" @click="openBrpcFaultDetail(thread)">
              详情
            </button>
          </template>
        </BlockTable>
      </div>
      <div class="table-foot">
        <span class="hint">
          共 {{ brpcAbnormalThreadTotal }} 条
          <template v-if="brpcThreadListLoading"> · 刷新中…</template>
        </span>
        <PageNav
          v-if="brpcFaultThreadPages > 1"
          :page="brpcAbnormalThreadPage"
          :pages="brpcFaultThreadPages"
          :disabled="brpcThreadListLoading"
          @update:page="goBrpcFaultThreadsPage"
        />
      </div>
    </template>
  </template>
</template>
