<script setup lang="ts">
import { onMounted } from 'vue'
import PageNav from '../common/PageNav.vue'
import { useOverviewData } from '../../composables/useOverviewData'

// P0.1：只注入 UBSocket 通断故障监控所需状态
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
  brpcEventWindowOptions,
  brpcEventWindowSize,
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
  brpcFaultVisibleSeriesIds,
  brpcFaultZoomed,
  brpcThreadSearchInput,
  brpcThreadSearchQuery,
  brpcThreadListLoading,
  brpcEventListLoading,
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
        📈 UBSocket 公共API故障时序分布
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
            <option v-for="option in brpcFaultScaleOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </span>
      </div>
      <p class="monitor-card-hint">
        横坐标会根据时间范围缩放，图中数据为缩放后的抽稀结果；拖动下方滑块可框选时间范围
      </p>
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
        <span class="fault-result-static">Pod IP</span>
        <label class="hint" for="brpc-event-window">时间间隔</label>
        <select
          id="brpc-event-window"
          class="select"
          v-model="brpcEventWindowSize"
          @change="changeBrpcEventWindowSize"
        >
          <option v-for="option in brpcEventWindowOptions" :key="option.value" :value="option.value">
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
          聚合口径：时间窗 × 接口命中数（同一窗口内所有 Pod 求和）；点「明细」展开该窗的 Pod 逐行结果
        </p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="col-nowrap">时间窗</th>
                <th class="col-num">故障总数</th>
                <th v-for="name in brpcEventInterfaceColumns" :key="name" class="col-num">
                  <span class="matrix-head" :title="name">{{ name }}</span>
                </th>
                <th class="col-nowrap">操作</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="window in brpcEventWindowPageRows" :key="window.key">
                <tr>
                  <td class="col-nowrap" style="font-family: monospace; font-size: 12px">
                    {{ window.start }} ~ {{ window.end }}
                  </td>
                  <td class="col-num"><b>{{ window.total }}</b></td>
                  <td v-for="name in brpcEventInterfaceColumns" :key="name" class="col-num">
                    <span :class="{ 'matrix-zero': !window.byInterface[name] }">
                      {{ window.byInterface[name] ?? '-' }}
                    </span>
                  </td>
                  <td class="col-nowrap">
                    <button
                      class="btn btn-sm btn-default"
                      type="button"
                      @click="toggleBrpcEventWindow(window.key)"
                    >
                      {{ brpcExpandedEventWindow === window.key ? '收起' : '明细' }}
                      （{{ window.pods.length }}）
                    </button>
                  </td>
                </tr>
                <tr v-if="brpcExpandedEventWindow === window.key">
                  <td :colspan="brpcEventInterfaceColumns.length + 3" class="matrix-detail-cell">
                    <table class="matrix-detail-table">
                      <thead>
                        <tr>
                          <th>Pod IP</th>
                          <th>Pod 名称</th>
                          <th>命中数</th>
                          <th>主要接口</th>
                          <th>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="pod in window.pods" :key="pod.event_id">
                          <td style="font-family: monospace">{{ pod.pod_ip }}</td>
                          <td>{{ pod.pod_name || '-' }}</td>
                          <td>{{ pod.hitTotal }}</td>
                          <td>
                            <div class="chip-row">
                              <span
                                v-for="hit in pod.interface_hits || []"
                                :key="hit.interface_id"
                                class="trace-chip"
                              >
                                {{ hit.interface_name }}:{{ hit.interface_hit_count }}
                              </span>
                              <span v-if="!(pod.interface_hits || []).length" class="hint">-</span>
                            </div>
                          </td>
                          <td>
                            <button class="btn btn-sm btn-primary" @click="openBrpcFaultDetail(pod)">
                              查看接口命中
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
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
      <!-- P2.4 异常 Thread 服务端搜索（线程 ID / Pod IP / Pod 名） -->
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
        <table>
          <thead>
            <tr>
              <th class="col-nowrap">线程ID</th>
              <th class="col-nowrap">Pod IP</th>
              <th class="col-nowrap">Pod 名称</th>
              <th class="col-num">命中数</th>
              <th>接口概要</th>
              <th class="col-nowrap">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="thread in brpcAbnormalThreads" :key="thread.thread_key">
              <td class="col-nowrap">
                <span class="thread-id-pill" :title="thread.thread_key">
                  {{ thread.thread_id }}
                </span>
              </td>
              <td class="col-nowrap" style="font-family: monospace">{{ thread.pod_ip }}</td>
              <td class="col-nowrap">{{ thread.pod_name || '-' }}</td>
              <td class="col-num">{{ thread.total_interface_hit_count }}</td>
              <td>
                <div class="chip-row">
                  <span
                    v-for="hit in thread.interface_hits || []"
                    :key="hit.interface_id"
                    class="trace-chip"
                  >
                    {{ hit.interface_name }}:{{ hit.interface_hit_count }}
                  </span>
                  <span v-if="!(thread.interface_hits || []).length" class="hint">-</span>
                </div>
              </td>
              <td class="col-nowrap">
                <button class="btn btn-sm btn-primary" @click="openBrpcFaultDetail(thread)">
                  详情
                </button>
              </td>
            </tr>
          </tbody>
        </table>
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
