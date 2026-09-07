<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted } from 'vue'
import { formatTime } from './utils/format'
import { useToast } from './composables/useToast'
import { useAssets } from './composables/useAssets'
import { useTasks } from './composables/useTasks'
import AssetModal from './components/AssetModal.vue'
import CreateTaskModal from './components/CreateTaskModal.vue'
import BrpcDiagnosisModal from './components/BrpcDiagnosisModal.vue'

const OverviewPanel = defineAsyncComponent(() => import('./components/overview/OverviewPanel.vue'))

const { toasts, toast } = useToast()
const {
  view,
  assetTab,
  assets,
  assetsLoading,
  assetsError,
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
  statusOf,
  progressOf,
  statusLabel,
  statusBadgeClass,
  isRunningStatus,
  isPending,
  isRunning,
  isFailed,
  isSuccess,
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

const createTaskFromOverview = () => {
  assetTab.value = 'tasks'
  nextTick(() => openCreateTask())
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
      <div class="breadcrumb">
        <span :class="{ current: view === 'assets' }" @click="goAssetList">资产列表</span>
        <template v-if="selectedAsset">
          <span class="sep">›</span>
          <span @click="enterAsset(selectedAsset)">{{ selectedAsset.name }}</span>
          <template v-if="view === 'home'">
            <span class="sep">›</span>
            <span class="current">{{ assetTab === 'tasks' ? '任务管理' : '总览' }}</span>
          </template>
        </template>
      </div>
    </div>
  </div>

  <div class="main">
    <!-- ============ 资产列表 ============ -->
    <template v-if="view === 'assets'">
      <div class="operate-bar">
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

      <div v-if="assetsLoading" class="empty">
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

      <div class="sub-nav">
        <div :class="['tab', { active: assetTab === 'overview' }]" @click="assetTab = 'overview'">
          总览
        </div>
        <div :class="['tab', { active: assetTab === 'tasks' }]" @click="assetTab = 'tasks'">
          任务管理 <span class="count">{{ filteredTasks.length }}</span>
        </div>
        <div class="tab disabled" title="当前后端暂不支持成员管理，入口已置灰">
          人员管理 <span class="count">—</span>
        </div>
      </div>

      <!-- ====== 总览 ====== -->
      <template v-if="assetTab === 'overview'">
        <OverviewPanel
          :asset="selectedAsset"
          :log-files="logFiles"
          @edit-asset="openAssetModal($event)"
          @create-task="createTaskFromOverview"
        />
      </template>

      <!-- ====== 任务管理 ====== -->
      <template v-else>
        <div class="operate-bar">
          <button class="btn btn-primary" @click="openCreateTask">+ 创建任务</button>
          <div class="operate-right">
            <select class="select" v-model="taskTypeFilter">
              <option value="">全部类型</option>
              <option value="kv-cache">KVCache</option>
              <option value="brpc">UBSocket</option>
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
        <div v-else class="table-wrap">
          <table>
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
                    :class="['badge', file.log_type === 'brpc' ? 'badge-pending' : 'badge-success']"
                  >
                    {{ file.log_type === 'brpc' ? 'UBSocket' : 'KVCache' }}
                  </span>
                </td>
                <td>
                  <div class="progress-cell">
                    <div class="progress-bar">
                      <div class="fill" :style="{ width: progressOf(file) + '%' }"></div>
                    </div>
                    <span>{{ Math.round(progressOf(file)) }}%</span>
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
                      v-if="isSuccess(file)"
                      class="btn btn-sm btn-primary"
                      disabled
                      title="当前后端暂不支持进入分析"
                    >
                      进入分析 →
                    </button>
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
                      style="color: var(--danger)"
                      @click="deleteLogFile(file)"
                    >
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
      </template>
    </template>
  </div>

  <AssetModal />
  <CreateTaskModal />
  <BrpcDiagnosisModal />

  <div class="toast">
    <div v-for="item in toasts" :key="item.id" :class="['toast-item', `toast-${item.type}`]">
      {{ item.text }}
    </div>
  </div>
</template>
