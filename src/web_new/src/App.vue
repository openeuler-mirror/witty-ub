<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { formatTime } from './utils/format'
import {
  formatParseTimingCores,
  formatParseTimingRows,
  formatParseTimingSeconds,
  formatParseTimingShare,
  parseTimingHeadlineLabel,
  parseTimingHeadlineSeconds,
} from './utils/parseTiming'
import type { LogFileModel } from './types'
import { useToast } from './composables/useToast'
import { useAssets } from './composables/useAssets'
import { useTasks } from './composables/useTasks'
import { useOverviewData } from './composables/useOverviewData'
import { useServiceHealth } from './composables/useServiceHealth'
import { taskFailureReason, taskFailureReasonLabel } from './utils/taskProgress'
import AssetModal from './components/AssetModal.vue'
import CreateTaskModal from './components/CreateTaskModal.vue'
import BrpcDiagnosisModal from './components/BrpcDiagnosisModal.vue'
import ParseConfigDrawer from './components/common/ParseConfigDrawer.vue'
import AgentChatPanel from './components/agent/AgentChatPanel.vue'

const OverviewPanel = defineAsyncComponent(() => import('./components/overview/OverviewPanel.vue'))

const { toasts } = useToast()
const {
  view,
  assetTab,
  assetsLoading,
  assetsError,
  isInitialDataUnavailable,
  searchMode,
  searchKey,
  assetPage,
  filteredAssets,
  assetPages,
  pagedAssets,
  selectedAsset,
  assetError,
  assetLatestTasks,
  loadAssetLatestTasks,
  loadAssets,
  enterAsset,
  goAssetList,
  openAssetModal,
  deleteAsset,
} = useAssets()

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
  skippedAlertsOf,
  hasTaskDetailOf,
  statusLabel,
  statusBadgeClass,
  isRunningStatus,
  isPending,
  isRunning,
  isFailed,
  brpcDiagStatusOf,
  canRunBrpcDiagnosis,
  openBrpcDiagnosis,
  refreshLogFiles,
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

// 磁盘降级（只读）状态：轮询 /health_check，受限时禁用全部写操作入口
const {
  writeRestricted,
  writeRestrictedMessage,
  startServiceHealthPolling,
  stopServiceHealthPolling,
} = useServiceHealth()

// 资产级日志解析配置抽屉
const { assetTypeFilter } = useOverviewData()
const parseConfigOpen = ref(false)
const openParseConfig = () => {
  assetTypeFilter.value = 'kvcache'
  parseConfigOpen.value = true
}

// 资产卡片摘要：只为当前页的卡片拉取「最近一条任务」，不阻塞列表渲染
watch(pagedAssets, (list) => void loadAssetLatestTasks(list), { immediate: true })

// 卡片状态徽标：undefined = 未加载（不渲染），null = 该资产还没有任务
const assetTaskBadge = (assetId: string) => {
  const latest = assetLatestTasks.value[assetId]
  if (latest === undefined) return null
  if (latest === null) {
    return { label: '暂无任务', cls: 'badge-cancelled', title: '该资产库下还没有任务' }
  }
  const label = statusLabel(latest.status)
  return {
    label,
    cls: statusBadgeClass(latest.status),
    title: `最近任务：${label} · ${formatTime(latest.createdAt)}`,
  }
}

// 任务行提示：失败/重试中给原因，其余给进度消息；单行省略，完整内容走 title
const taskRowHint = (file: LogFileModel) => {
  const reason = taskFailureReason(file)
  return reason ? `${taskFailureReasonLabel(file)}：${reason}` : progressMessageOf(file)
}
const taskRowHintIsFailure = (file: LogFileModel) => Boolean(taskFailureReason(file))

let pollTimer: number | null = null

const hasActiveTasks = computed(() =>
  logFiles.value.some((file) => {
    const status = statusOf(file)
    return (
      ['running', 'pending', 'cancelled', 'retrying'].includes(status) ||
      brpcDiagStatusOf(file) === 'running'
    )
  }),
)

const startPolling = () => {
  stopPolling()
  pollTimer = window.setInterval(() => {
    if (view.value === 'home' && selectedAsset.value && hasActiveTasks.value) {
      void refreshLogFiles(true)
    }
  }, 5000)
}

const stopPolling = () => {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  void loadAssets()
  startPolling()
  startServiceHealthPolling()
})

onBeforeUnmount(() => {
  stopPolling()
  stopServiceHealthPolling()
})
</script>
<template>
  <div class="topbar">
    <div class="topbar-left">
      <div class="logo">witty-ub</div>
      <nav class="breadcrumb" aria-label="面包屑导航">
        <button
          type="button"
          class="breadcrumb-link"
          :class="{ current: view === 'assets' }"
          :aria-current="view === 'assets' ? 'page' : undefined"
          @click="goAssetList"
        >
          资产列表
        </button>
        <template v-if="selectedAsset">
          <span class="sep">›</span>
          <button type="button" class="breadcrumb-link" @click="enterAsset(selectedAsset)">
            {{ selectedAsset.name }}
          </button>
          <template v-if="view === 'home'">
            <span class="sep">›</span>
            <span class="current" aria-current="page">{{
              assetTab === 'tasks' ? '任务' : '分析'
            }}</span>
          </template>
        </template>
      </nav>
    </div>
  </div>

  <main class="main">
    <!-- 磁盘降级：后端只开放查询/删除，写操作入口同步禁用 -->
    <div v-if="writeRestricted" class="error-banner" role="status">
      {{ writeRestrictedMessage }}；资产查询、详情查看和删除操作仍可使用。
    </div>

    <!-- ============ 资产列表 ============ -->
    <template v-if="view === 'assets'">
      <div v-if="!isInitialDataUnavailable" class="operate-bar">
        <button
          class="btn btn-primary"
          :disabled="writeRestricted"
          :title="writeRestricted ? writeRestrictedMessage : ''"
          @click="openAssetModal()"
        >
          + 创建资产
        </button>
        <div class="operate-right">
          <select class="select" v-model="searchMode">
            <option value="all">全部</option>
            <option value="name">名称</option>
            <option value="desc">简介</option>
          </select>
          <input class="input" style="width: 240px" v-model="searchKey" placeholder="搜索资产..." />
        </div>
      </div>

      <section v-if="isInitialDataUnavailable" class="service-unavailable" role="alert">
        <div class="service-unavailable-icon" aria-hidden="true">!</div>
        <h1>数据服务暂时不可用</h1>
        <p>当前无法加载资产库和任务状态，请稍后重试或联系管理员。</p>
        <p class="service-unavailable-hint">
          服务恢复后可继续使用，任务状态以重新连接后的结果为准。
        </p>
        <button class="btn btn-primary" type="button" :disabled="assetsLoading" @click="loadAssets">
          {{ assetsLoading ? '正在重试...' : '重新加载' }}
        </button>
      </section>
      <div v-else-if="assetsLoading" class="empty">
        <div class="icon">⏳</div>
        <div>正在加载资产库...</div>
      </div>
      <div v-else-if="assetsError" class="error-banner">{{ assetsError }}</div>
      <div v-else-if="filteredAssets.length === 0" class="empty">
        <div class="icon">📭</div>
        <div>暂无资产</div>
        <div class="hint">点击上方按钮创建第一个资产库</div>
      </div>
      <div v-else class="card-grid">
        <div class="card asset-card" v-for="asset in pagedAssets" :key="asset.id">
          <div class="asset-card-head">
            <div class="asset-card-name" :title="asset.name">{{ asset.name }}</div>
            <span
              v-if="assetTaskBadge(asset.id)"
              class="badge"
              :class="assetTaskBadge(asset.id)?.cls"
              :title="assetTaskBadge(asset.id)?.title"
            >
              {{ assetTaskBadge(asset.id)?.label }}
            </span>
          </div>
          <div class="asset-card-desc" :title="asset.description">
            {{ asset.description || '—' }}
          </div>
          <div class="asset-card-stats">
            <span
              ><b>{{ asset.task_cnt ?? 0 }}</b> 个任务</span
            >
            <span>更新 {{ formatTime(asset.updated_at) }}</span>
          </div>
          <div class="asset-card-actions">
            <div class="asset-card-tools">
              <button
                class="btn btn-sm btn-text"
                :disabled="writeRestricted"
                :title="writeRestricted ? writeRestrictedMessage : ''"
                @click="openAssetModal(asset)"
              >
                编辑
              </button>
              <button class="btn btn-sm btn-text btn-text-danger" @click="deleteAsset(asset)">
                删除
              </button>
            </div>
            <button class="btn btn-sm btn-primary asset-enter-btn" @click="enterAsset(asset)">
              进入资产库 →
            </button>
          </div>
        </div>
      </div>

      <div class="pagination" v-if="assetPages > 1">
        <button
          v-for="page in assetPages"
          :key="page"
          :class="{ active: assetPage === page }"
          @click="assetPage = page"
        >
          {{ page }}
        </button>
      </div>
    </template>

    <!-- ============ 资产库主页 ============ -->
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
      </nav>

      <!-- ====== 总览 ====== -->
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
      <section v-else id="asset-tasks-panel" aria-labelledby="asset-tasks-tab">
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
                      <div
                        v-if="skippedAlertsOf(file).length"
                        class="task-skip-chip"
                        :title="skippedAlertsOf(file).join('\n')"
                      >
                        ⚠ {{ skippedAlertsOf(file)[0] }}
                      </div>
                    </div>
                  </td>
                  <td>
                    <span :class="['badge', statusBadgeClass(statusOf(file))]">
                      {{ statusLabel(statusOf(file)) }}
                    </span>
                  </td>
                  <td>{{ formatTime(file.created_at) }}</td>
                  <td class="num">{{ file.anomaly_cnt ?? '-' }}</td>
                  <td class="num">{{ file.trace_failure_event_cnt ?? '-' }}</td>
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
                        <button class="btn btn-sm btn-text" @click="runLogFile(file)">
                          ↻ 重试
                        </button>
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
                    <div v-if="skippedAlertsOf(file).length" class="task-detail-skip" role="alert">
                      <span class="task-detail-skip-title">已跳过读不出来的日志文件</span>
                      <span
                        v-for="alert in skippedAlertsOf(file)"
                        :key="alert"
                        class="task-detail-skip-line"
                      >
                        {{ alert }}
                      </span>
                    </div>

                    <div v-if="parseTimingOf(file)" class="task-detail-timing">
                      <div class="task-detail-timing-head">
                        <span class="task-detail-timing-title">解析用时</span>
                        <span class="task-detail-timing-total">
                          {{
                            formatParseTimingSeconds(
                              parseTimingHeadlineSeconds(parseTimingOf(file)),
                            )
                          }}
                        </span>
                        <span class="task-detail-timing-meta">
                          {{ parseTimingHeadlineLabel() }}
                        </span>
                        <span v-if="parseTimingOf(file)?.rows" class="task-detail-timing-meta">
                          {{ formatParseTimingRows(parseTimingOf(file)?.rows ?? null) }}
                        </span>
                      </div>

                      <table class="task-timing-table">
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
          style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 12px;
          "
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
    </template>
  </main>

  <AssetModal />
  <CreateTaskModal />
  <BrpcDiagnosisModal />
  <ParseConfigDrawer
    :asset="selectedAsset"
    :asset-type="assetTypeFilter"
    v-model:open="parseConfigOpen"
  />
  <!-- AI 故障诊断助手：仅分析页（总览）显示 FAB -->
  <AgentChatPanel v-if="view === 'home' && assetTab === 'overview'" :asset="selectedAsset" />

  <div class="toast">
    <div v-for="item in toasts" :key="item.id" :class="['toast-item', `toast-${item.type}`]">
      {{ item.text }}
    </div>
  </div>
</template>
