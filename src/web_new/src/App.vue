<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
import { formatTime } from './utils/format'
import { useToast } from './composables/useToast'
import { useAssets } from './composables/useAssets'
import { useTasks } from './composables/useTasks'
import { useOverviewData } from './composables/useOverviewData'
import AssetModal from './components/AssetModal.vue'
import CreateTaskModal from './components/CreateTaskModal.vue'
import BrpcDiagnosisModal from './components/BrpcDiagnosisModal.vue'
import ParseConfigDrawer from './components/common/ParseConfigDrawer.vue'
import AgentChatPanel from './components/agent/AgentChatPanel.vue'

const OverviewPanel = defineAsyncComponent(() => import('./components/overview/OverviewPanel.vue'))

const { toasts, toast } = useToast()
const {
  view,
  assetTab,
  assets,
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
  assetLoading,
  assetError,
  loadAssets,
  enterAsset,
  goAssetList,
  assetModalOpen,
  assetModalMode,
  savingAsset,
  assetForm,
  assetFormError,
  openAssetModal,
  closeAssetModal,
  saveAsset,
  deleteAsset,
} = useAssets()

const {
  logFiles,
  logFilesTotal,
  logFilesLoading,
  logFilesError,
  logFilesAssetId,
  statusOf,
  progressOf,
  progressMessageOf,
  statusLabel,
  statusBadgeClass,
  isRunningStatus,
  isPending,
  isRunning,
  isFailed,
  brpcDiagStatusOf,
  canRunBrpcDiagnosis,
  brpcModalOpen,
  brpcTargetFile,
  brpcStartTime,
  brpcSaving,
  brpcError,
  openBrpcDiagnosis,
  runBrpcDiagnosis,
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
  showCreateTask,
  savingTask,
  taskError,
  newTask,
  openCreateTask,
  closeCreateTask,
  onTaskFilesChange,
  canSubmitTask,
  createTask,
} = useTasks()

// P1.1 资产级日志解析配置抽屉
const { assetTypeFilter } = useOverviewData()
const parseConfigOpen = ref(false)
const openParseConfig = () => {
  assetTypeFilter.value = 'kvcache'
  parseConfigOpen.value = true
}

// P2.5 任务行「更新」：纯前端重拉日志列表刷新该文件状态/结果，不是重新解析
const refreshingFileIds = ref(new Set<string>())
const refreshOneLogFile = async (file: { id?: string }) => {
  const id = file.id ?? ''
  if (!id || refreshingFileIds.value.has(id)) return
  refreshingFileIds.value = new Set(refreshingFileIds.value).add(id)
  try {
    await refreshLogFiles(true)
  } finally {
    const next = new Set(refreshingFileIds.value)
    next.delete(id)
    refreshingFileIds.value = next
  }
}

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
})

onBeforeUnmount(() => {
  stopPolling()
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
    <!-- ============ 资产列表 ============ -->
    <template v-if="view === 'assets'">
      <div v-if="!isInitialDataUnavailable" class="operate-bar">
        <button class="btn btn-primary" @click="openAssetModal()">+ 创建资产</button>
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
        <div
          class="card asset-card"
          v-for="asset in pagedAssets"
          :key="asset.id"
          style="padding: 20px"
        >
          <div class="asset-card-name">{{ asset.name }}</div>
          <div class="asset-card-desc">{{ asset.description }}</div>
          <div class="asset-card-meta">
            异常: {{ asset.anomaly_cnt ?? '-' }} &nbsp; 创建: {{ formatTime(asset.created_at) }}
          </div>
          <div class="asset-card-actions">
            <div style="display: flex; gap: 2px; flex-wrap: wrap">
              <button class="btn btn-sm btn-text" @click="openAssetModal(asset)">编辑</button>
              <button
                class="btn btn-sm btn-text"
                style="color: var(--danger)"
                @click="deleteAsset(asset)"
              >
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
        />
      </section>

      <!-- ====== 任务管理 ====== -->
      <section v-else id="asset-tasks-panel" aria-labelledby="asset-tasks-tab">
        <div class="operate-bar task-toolbar">
          <div class="toolbar-primary">
            <button class="btn btn-primary" @click="openCreateTask">+ 创建任务</button>
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

        <div v-if="logFilesLoading" class="empty">
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
                <th>时延异常</th>
                <th>通断异常</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="file in pagedTasks" :key="file.id">
                <td class="task-name-cell">
                  <div class="task-name">{{ file.name }}</div>
                  <div class="task-path">{{ file.file_path || '—' }}</div>
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
                      <span>{{ Math.round(progressOf(file)) }}%</span>
                    </div>
                    <div
                      v-if="progressMessageOf(file)"
                      :class="['task-progress-message', { failed: isFailed(file) }]"
                      :title="progressMessageOf(file)"
                    >
                      {{ progressMessageOf(file) }}
                    </div>
                  </div>
                </td>
                <td>
                  <span :class="['badge', statusBadgeClass(statusOf(file))]">
                    {{ statusLabel(statusOf(file)) }}
                  </span>
                </td>
                <td>{{ formatTime(file.created_at) }}</td>
                <td>{{ file.anomaly_cnt ?? '-' }}</td>
                <td>{{ file.trace_failure_event_cnt ?? '-' }}</td>
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
                    <button
                      class="btn btn-sm btn-text"
                      :disabled="refreshingFileIds.has(file.id)"
                      title="重新拉取该文件的状态/结果，不是重新解析"
                      @click="refreshOneLogFile(file)"
                    >
                      {{ refreshingFileIds.has(file.id) ? '更新中…' : '⟳ 更新' }}
                    </button>
                    <button class="btn btn-sm btn-danger" @click="deleteLogFile(file)">
                      ✕ 删除
                    </button>
                  </div>
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
          "
        >
          <span style="font-size: 13px; color: var(--text2)">
            共 {{ filteredTasks.length }} 个任务，每页 {{ taskPageSize }} 个
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
  <!-- P1.3 AI 故障诊断助手：仅分析页（总览）显示 FAB -->
  <AgentChatPanel v-if="view === 'home' && assetTab === 'overview'" :asset="selectedAsset" />

  <div class="toast">
    <div v-for="item in toasts" :key="item.id" :class="['toast-item', `toast-${item.type}`]">
      {{ item.text }}
    </div>
  </div>
</template>
