<script setup lang="ts">
import { watch } from 'vue'
import LineClampText from '../../components/common/LineClampText.vue'
import { formatTime } from '../../utils/format'
import { assetLogFileCountText } from '../../utils/inspectionCounts'
import { useAssets } from '../../composables/useAssets'
import { useTasks } from '../../composables/useTasks'
import { useServiceHealth } from '../../composables/useServiceHealth'
import AssetModal from '../../components/AssetModal.vue'

const {
  assetsLoading,
  assetsError,
  isInitialDataUnavailable,
  searchMode,
  searchKey,
  assetPage,
  filteredAssets,
  assetPages,
  pagedAssets,
  assetLatestTasks,
  assetLogFileCounts,
  loadAssetCardSummaries,
  loadAssets,
  assetError,
  enterAsset,
  openAssetModal,
  deleteAsset,
} = useAssets()

const { statusLabel, statusBadgeClass } = useTasks()

const { writeRestricted, writeRestrictedMessage } = useServiceHealth()

// 资产卡片摘要：只为当前页的卡片拉取「最近一条任务」，不阻塞列表渲染
watch(pagedAssets, (list) => void loadAssetCardSummaries(list), { immediate: true })

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
</script>
<template>
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
    <p class="service-unavailable-hint">服务恢复后可继续使用，任务状态以重新连接后的结果为准。</p>
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
      <LineClampText class="asset-card-desc" :text="asset.description || '—'" />
      <div class="asset-card-stats">
        <!-- 计数取 /log_file/list 的 total：资产列表里的 task_cnt 只在 KVCache 任务收尾时
             刷新，UBSocket 资产的该列会恒为 0 -->
        <span
          ><b>{{ assetLogFileCountText(assetLogFileCounts[asset.id]) }}</b> 个日志文件</span
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

  <div v-if="assetError" class="error-banner">{{ assetError }}</div>

  <AssetModal />
</template>
