<script setup lang="ts">
import { defineAsyncComponent, ref } from 'vue'
import { formatTime } from '../../utils/format'
import { countText } from '../../utils/inspectionCounts'
import {
  buildTimelineTicks,
  formatParseTimingCores,
  formatParseTimingRows,
  formatParseTimingSeconds,
  formatParseTimingShare,
  formatTaskLaneSegmentTitle,
  parseTimingHeadlineLabel,
  parseTimingHeadlineSeconds,
  taskLaneSegmentStyle,
  taskLaneTickStyle,
} from '../../utils/parseTiming'
import type { LogFileModel } from '../../types'
import { useAssets } from '../../composables/useAssets'
import { useTasks } from '../../composables/useTasks'
import { useServiceHealth } from '../../composables/useServiceHealth'
import { useOverviewData } from '../../composables/useOverviewData'
import { taskFailureReason, taskFailureReasonLabel } from '../../utils/taskProgress'
import CreateTaskModal from '../../components/CreateTaskModal.vue'
import BrpcDiagnosisModal from '../../components/BrpcDiagnosisModal.vue'
import ParseConfigDrawer from '../../components/common/ParseConfigDrawer.vue'
import AssetReportsPanel from './AssetReportsPanel.vue'

const OverviewPanel = defineAsyncComponent(
  () => import('../../components/overview/OverviewPanel.vue'),
)
const AgentChatPanel = defineAsyncComponent(
  () => import('../../components/agent/AgentChatPanel.vue'),
)

const { selectedAsset, assetTab, assetError } = useAssets()

const {
  logFiles,
  logFilesLoading,
  logFilesError,
  logFilesAssetId,
  statusOf,
  progressOf,
  progressMessageOf,
  isTaskDetailOpen,
  toggleTaskDetail,
  parseTimingOf,
  taskTimelineOf,
  taskLanesOf,
  taskAxisTotalSOf,
  timelineLegendOf,
  hasTaskDetailOf,
  statusLabel,
  statusBadgeClass,
  isPending,
  isRunning,
  isFailed,
  isRunningStatus,
  brpcDiagStatusOf,
  canRunBrpcDiagnosis,
  openBrpcDiagnosis,
  runLogFile,
  stopLogFile,
  deleteLogFile,
  taskTypeFilter,
  taskFilterStatus,
  taskSearch,
  taskPage,
  taskPageSize,
  filteredTasks,
  taskPages,
  pagedTasks,
  openCreateTask,
} = useTasks()

const { writeRestricted, writeRestrictedMessage } = useServiceHealth()

// 资产级日志解析配置抽屉
const { assetTypeFilter } = useOverviewData()
const parseConfigOpen = ref(false)
const openParseConfig = () => {
  assetTypeFilter.value = 'kvcache'
  parseConfigOpen.value = true
}

// 任务行提示：失败/重试中给原因，其余给进度消息；单行省略，完整内容走 title
const taskRowHint = (file: LogFileModel) => {
  const reason = taskFailureReason(file)
  return reason ? `${taskFailureReasonLabel(file)}：${reason}` : progressMessageOf(file)
}
const taskRowHintIsFailure = (file: LogFileModel) => Boolean(taskFailureReason(file))
</script>
<template>
  <div v-if="!selectedAsset" class="empty">
    <div class="icon">📭</div>
    <div>尚未选择资产库</div>
    <div class="hint">请返回资产库列表选择</div>
  </div>
  <template v-else>
    <div v-if="assetError" class="error-banner">{{ assetError }}</div>

    <nav class="page-nav" aria-label="资产工作区">
      <button
        id="asset-analysis-tab"
        type="button"
        :class="['page-nav-item', { active: assetTab === 'overview' }]"
        :aria-current="assetTab === 'overview' ? 'page' : undefined"
        :aria-controls="assetTab === 'overview' ? 'asset-analysis-panel' : undefined"
        @click="assetTab = 'overview'"
      >
        分析
      </button>
      <button
        id="asset-tasks-tab"
        type="button"
        :class="['page-nav-item', { active: assetTab === 'tasks' }]"
        :aria-current="assetTab === 'tasks' ? 'page' : undefined"
        :aria-controls="assetTab === 'tasks' ? 'asset-tasks-panel' : undefined"
        @click="assetTab = 'tasks'"
      >
        任务 <span class="count">{{ filteredTasks.length }}</span>
      </button>
      <button
        id="asset-reports-tab"
        type="button"
        :class="['page-nav-item', { active: assetTab === 'reports' }]"
        :aria-current="assetTab === 'reports' ? 'page' : undefined"
        :aria-controls="assetTab === 'reports' ? 'asset-reports-panel' : undefined"
        @click="assetTab = 'reports'"
      >
        定界文档
      </button>
    </nav>

    <!-- ====== 分析（监控） ====== -->
    <section
      v-if="assetTab === 'overview'"
      id="asset-analysis-panel"
      aria-labelledby="asset-analysis-tab"
    >
      <OverviewPanel
        :asset="selectedAsset"
        :log-files="logFiles"
        :log-files-asset-id="logFilesAssetId"
        :log-files-loading="logFilesLoading"
        :log-files-error="logFilesError"
      />
    </section>

    <!-- ====== 任务管理 ====== -->
    <section
      v-else-if="assetTab === 'tasks'"
      id="asset-tasks-panel"
      aria-labelledby="asset-tasks-tab"
    >
      <div class="operate-bar task-toolbar">
        <div class="toolbar-primary">
          <button
            class="btn btn-primary"
            :disabled="writeRestricted"
            :title="writeRestricted ? writeRestrictedMessage : ''"
            @click="openCreateTask"
          >
            + 创建任务
          </button>
          <button
            v-if="taskTypeFilter !== 'UBSocket'"
            class="btn btn-default"
            @click="openParseConfig"
          >
            KVCache 解析配置
          </button>
        </div>
        <div class="operate-right toolbar-filters" aria-label="任务筛选">
          <select class="select" v-model="taskTypeFilter">
            <option value="">全部类型</option>
            <option value="KVCache">KVCache</option>
            <option value="UBSocket">UBSocket</option>
          </select>
          <select class="select" v-model="taskFilterStatus">
            <option value="">全部状态</option>
            <option value="pending">待解析</option>
            <option value="running">解析中</option>
            <option value="retrying">正在重试</option>
            <option value="successful">已完成</option>
            <option value="failed">失败</option>
            <option value="cancelled">已取消</option>
          </select>
          <input
            class="input"
            style="width: 240px"
            v-model="taskSearch"
            placeholder="搜索任务名称 / 路径"
          />
        </div>
      </div>

      <!-- 已有数据时不清空列表：只在首次加载展示占位，后续刷新就地提示 -->
      <div v-if="logFilesLoading && logFiles.length === 0" class="empty">
        <div class="icon">⏳</div>
        <div>正在加载任务...</div>
      </div>
      <div v-else-if="logFilesError" class="error-banner">{{ logFilesError }}</div>
      <div v-else-if="filteredTasks.length === 0" class="empty">
        <div class="icon">📭</div>
        <div>暂无任务</div>
        <div class="hint">点击上方按钮创建第一个解析任务</div>
      </div>
      <div v-else class="table-wrap task-table-wrap">
        <table class="task-table">
          <thead>
            <tr>
              <th>名称 / 路径</th>
              <th>类型</th>
              <th>进度</th>
              <th>状态</th>
              <th>创建时间</th>
              <th class="num">时延异常</th>
              <th class="num">通断异常</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="file in pagedTasks" :key="file.id">
              <tr>
                <td class="task-name-cell">
                  <div class="task-name-row">
                    <button
                      v-if="hasTaskDetailOf(file)"
                      type="button"
                      class="task-expand-btn"
                      :aria-expanded="isTaskDetailOpen(file)"
                      :title="isTaskDetailOpen(file) ? '收起解析明细' : '展开解析明细'"
                      @click="toggleTaskDetail(file)"
                    >
                      {{ isTaskDetailOpen(file) ? '▾' : '▸' }}
                    </button>
                    <span v-else class="task-expand-placeholder" aria-hidden="true"></span>
                    <div class="task-name-block">
                      <div class="task-name" :title="file.name">{{ file.name }}</div>
                      <div class="task-path" :title="file.file_path">
                        {{ file.file_path || '—' }}
                      </div>
                    </div>
                  </div>
                </td>
                <td>
                  <span
                    :class="[
                      'badge',
                      file.log_type === 'UBSocket' ? 'badge-pending' : 'badge-success',
                    ]"
                  >
                    {{ file.log_type }}
                  </span>
                </td>
                <td>
                  <div class="task-progress-stack">
                    <div class="progress-cell">
                      <div class="progress-bar">
                        <div class="fill" :style="{ width: progressOf(file) + '%' }"></div>
                      </div>
                      <span class="progress-value">{{ Math.round(progressOf(file)) }}%</span>
                    </div>
                    <div
                      v-if="taskRowHint(file)"
                      :class="[
                        'task-row-hint',
                        { 'task-row-hint-failed': taskRowHintIsFailure(file) },
                      ]"
                      :title="taskRowHint(file)"
                    >
                      {{ taskRowHint(file) }}
                    </div>
                  </div>
                </td>
                <td>
                  <span :class="['badge', statusBadgeClass(statusOf(file))]">
                    {{ statusLabel(statusOf(file)) }}
                  </span>
                </td>
                <td>{{ formatTime(file.created_at) }}</td>
                <td class="num">{{ countText(file.anomaly_cnt, statusOf(file)) }}</td>
                <td class="num">{{ countText(file.trace_failure_event_cnt, statusOf(file)) }}</td>
                <td>
                  <div class="task-actions">
                    <template v-if="isPending(file)">
                      <button class="btn btn-sm btn-primary" @click="runLogFile(file)">
                        ▶ 开始
                      </button>
                    </template>
                    <template v-else-if="isRunning(file)">
                      <button class="btn btn-sm btn-default" @click="stopLogFile(file)">
                        ■ 停止
                      </button>
                    </template>
                    <template v-else-if="isFailed(file)">
                      <button class="btn btn-sm btn-text" @click="runLogFile(file)">↻ 重试</button>
                    </template>
                    <button
                      v-if="canRunBrpcDiagnosis(file)"
                      class="btn btn-sm btn-default"
                      @click="openBrpcDiagnosis(file)"
                    >
                      ▶ 运行诊断
                    </button>
                    <span
                      v-else-if="isRunningStatus(brpcDiagStatusOf(file))"
                      class="badge badge-running"
                      >诊断中</span
                    >
                    <button class="btn btn-sm btn-danger" @click="deleteLogFile(file)">
                      ✕ 删除
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="isTaskDetailOpen(file)" class="task-detail-row">
                <td colspan="8">
                  <div
                    v-if="parseTimingOf(file) || taskLanesOf(file).length"
                    class="task-detail-timing"
                  >
                    <div class="task-detail-timing-head">
                      <span class="task-detail-timing-title">解析用时</span>
                      <span class="task-detail-timing-total">
                        {{
                          formatParseTimingSeconds(
                            parseTimingHeadlineSeconds(parseTimingOf(file), taskTimelineOf(file)),
                          )
                        }}
                      </span>
                      <span class="task-detail-timing-meta">
                        {{ parseTimingHeadlineLabel(taskTimelineOf(file)) }}
                      </span>
                      <span v-if="parseTimingOf(file)?.rows" class="task-detail-timing-meta">
                        {{ formatParseTimingRows(parseTimingOf(file)?.rows ?? null) }}
                      </span>
                    </div>

                    <!-- 三条泳道：解析 / 故障定界 / 上下文落库，共用一条时间轴 -->
                    <div v-if="taskLanesOf(file).length" class="task-timing-lanes">
                      <div class="task-timing-lane task-timing-lane--ticks">
                        <span class="task-timing-lane-label"></span>
                        <span class="task-timing-track">
                          <span
                            v-for="(tick, index) in buildTimelineTicks(taskAxisTotalSOf(file))"
                            :key="`tick-${index}`"
                            class="task-timing-tick"
                            :style="taskLaneTickStyle(tick, taskAxisTotalSOf(file))"
                          >
                            {{ tick }}s
                          </span>
                        </span>
                      </div>
                      <div
                        v-for="lane in taskLanesOf(file)"
                        :key="lane.taskType"
                        class="task-timing-lane"
                      >
                        <span class="task-timing-lane-label" :title="lane.taskType">
                          {{ lane.label }}
                        </span>
                        <span class="task-timing-track">
                          <span
                            v-for="(segment, segmentIndex) in lane.segments"
                            :key="`${segment.stage}-${segmentIndex}`"
                            :class="[
                              'task-timing-seg',
                              `is-stage-${segment.stage}`,
                              {
                                'is-waiting': segment.waiting,
                                'is-unknown': !segment.positionKnown,
                                'is-head': segment.head,
                              },
                            ]"
                            :style="taskLaneSegmentStyle(segment, taskAxisTotalSOf(file))"
                            :title="formatTaskLaneSegmentTitle(segment, taskAxisTotalSOf(file))"
                          ></span>
                        </span>
                        <span class="task-timing-lane-total">
                          {{ formatParseTimingSeconds(lane.totalS) }}
                        </span>
                        <span v-if="lane.note" class="task-timing-lane-note">{{ lane.note }}</span>
                        <span v-if="lane.running" class="task-timing-lane-running">进行中</span>
                      </div>
                    </div>

                    <div v-if="taskLanesOf(file).length" class="task-timing-legend">
                      <span
                        v-for="item in timelineLegendOf(file)"
                        :key="`legend-${item.stage}`"
                        class="task-timing-legend-item"
                      >
                        <span :class="['task-timing-legend-dot', `is-stage-${item.stage}`]"></span>
                        {{ item.label }}
                      </span>
                    </div>

                    <table v-if="parseTimingOf(file)" class="task-timing-table">
                      <thead>
                        <tr>
                          <th>阶段</th>
                          <th>用时</th>
                          <th>占比</th>
                          <th>核数</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="stage in parseTimingOf(file)?.stages ?? []" :key="stage.stage">
                          <td class="task-timing-stage">
                            {{ stage.label }}
                            <span v-if="stage.detail" class="task-timing-detail">
                              {{ stage.detail }}
                            </span>
                          </td>
                          <td>{{ formatParseTimingSeconds(stage.wall_s) }}</td>
                          <td>
                            {{
                              formatParseTimingShare(
                                stage.wall_s,
                                parseTimingOf(file)?.total_s ?? 0,
                              )
                            }}
                          </td>
                          <td>{{ formatParseTimingCores(stage.cores) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div
        style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px"
      >
        <span style="font-size: 13px; color: var(--text2)">
          共 {{ filteredTasks.length }} 个任务，每页 {{ taskPageSize }} 个
          <template v-if="logFilesLoading"> · 刷新中…</template>
        </span>
        <div class="pagination" style="margin-top: 0" v-if="taskPages > 1">
          <button :disabled="taskPage === 1" @click="taskPage = Math.max(1, taskPage - 1)">
            ‹
          </button>
          <button
            v-for="page in taskPages"
            :key="page"
            :class="{ active: taskPage === page }"
            @click="taskPage = page"
          >
            {{ page }}
          </button>
          <button
            :disabled="taskPage === taskPages"
            @click="taskPage = Math.min(taskPages, taskPage + 1)"
          >
            ›
          </button>
        </div>
      </div>
    </section>

    <!-- ====== 诊断报告（本资产库） ====== -->
    <section v-else id="asset-reports-panel" aria-labelledby="asset-reports-tab">
      <AssetReportsPanel />
    </section>

    <CreateTaskModal />
    <BrpcDiagnosisModal />
    <ParseConfigDrawer
      :asset="selectedAsset"
      :asset-type="assetTypeFilter"
      v-model:open="parseConfigOpen"
    />
    <!-- AI 故障诊断助手：工作区常驻右下角，切换子页签不卸载，进行中的会话不受影响 -->
    <AgentChatPanel :asset="selectedAsset" />
  </template>
</template>
