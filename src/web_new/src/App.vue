<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useToast } from './composables/useToast'
import { useAssets } from './composables/useAssets'
import { useTasks } from './composables/useTasks'
import { useServiceHealth } from './composables/useServiceHealth'
import { useNavigation } from './composables/useNavigation'
import type { AppView } from './composables/useAssets'
import AssetsPage from './views/assets/AssetsPage.vue'
import AssetWorkspace from './views/assets/AssetWorkspace.vue'
import KnowledgeHubPage from './components/knowledge/KnowledgeHubPage.vue'
import BrpcDiagnosisModal from './components/BrpcDiagnosisModal.vue'
import ReportWorkbenchModal from './components/report/ReportWorkbenchModal.vue'
import DiagCaseDetailModal from './components/knowledge/DiagCaseDetailModal.vue'

const { toasts } = useToast()
const { view, selectedAsset, assetTab, goAssetList } = useAssets()
const { logFiles, statusOf, brpcDiagStatusOf, refreshLogFiles } = useTasks()

// 磁盘降级（只读）状态：轮询 /health_check，受限时禁用全部写操作入口
const {
  writeRestricted,
  writeRestrictedMessage,
  startServiceHealthPolling,
  stopServiceHealthPolling,
} = useServiceHealth()

// 顶层导航：hash 双向同步（前进/后退/刷新均可用）
useNavigation()

const NAV_ITEMS: Array<{ key: AppView; label: string }> = [
  { key: 'assets', label: '资产库' },
  { key: 'knowledge', label: '知识库' },
]

// 顶层页签点击：资产库一律回列表（详情在工作区内，通过卡片进入）
const onNavClick = (key: AppView) => {
  if (key === 'assets') {
    goAssetList()
    return
  }
  view.value = key
}

// 顶栏资产库页签后内联的位置路径：资产库 › 资产名 › 当前子页
const assetTabLabel = computed(
  () => ({ overview: '分析', tasks: '任务', reports: '定界文档' })[assetTab.value],
)

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
      <button type="button" class="logo logo-btn" @click="goAssetList">witty-ub</button>
      <nav class="top-nav" aria-label="主导航">
        <template v-for="item in NAV_ITEMS" :key="item.key">
          <div v-if="item.key === 'assets'" class="top-nav-asset">
            <button
              type="button"
              :class="['top-nav-item', { active: view === item.key || view === 'home' }]"
              :aria-current="view === item.key || view === 'home' ? 'page' : undefined"
              @click="onNavClick(item.key)"
            >
              {{ item.label }}
            </button>
            <span
              v-if="view === 'home' && selectedAsset"
              class="top-nav-crumb"
              aria-label="位置"
            >
              <span class="top-crumb-sep" aria-hidden="true">›</span>
              <span class="top-crumb-asset" :title="selectedAsset.name">{{
                selectedAsset.name
              }}</span>
              <span class="top-crumb-sep" aria-hidden="true">›</span>
              <span class="top-crumb-current">{{ assetTabLabel }}</span>
            </span>
          </div>
          <button
            v-else
            type="button"
            :class="['top-nav-item', { active: view === item.key }]"
            :aria-current="view === item.key ? 'page' : undefined"
            @click="onNavClick(item.key)"
          >
            {{ item.label }}
          </button>
        </template>
      </nav>
    </div>
  </div>

  <main class="main">
    <!-- 磁盘降级：后端只开放查询/删除，写操作入口同步禁用 -->
    <div v-if="writeRestricted" class="error-banner" role="status">
      {{ writeRestrictedMessage }}；资产查询、详情查看和删除操作仍可使用。
    </div>

    <AssetsPage v-if="view === 'assets'" />
    <AssetWorkspace v-else-if="view === 'home'" />
    <KnowledgeHubPage v-else />
  </main>

  <BrpcDiagnosisModal />
  <ReportWorkbenchModal />
  <DiagCaseDetailModal />

  <div class="toast">
    <div v-for="item in toasts" :key="item.id" :class="['toast-item', `toast-${item.type}`]">
      {{ item.text }}
    </div>
  </div>
</template>
