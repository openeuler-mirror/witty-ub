<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { fetchSimilarFaultTypes, type SimilarityMatch, type SimilarityResult } from '../../api/analysis'
import { apiBase } from '../../api/http'

const props = defineProps<{
  logFileId: string
  logFileName: string
}>()

const loading = ref(false)
const error = ref('')
const result = ref<SimilarityResult | null>(null)

const topMatches = computed(() => result.value?.top_matches ?? [])
const librarySize = computed(() => result.value?.library_size ?? 0)
const uniqueTypesCount = computed(() => result.value?.unique_types_count ?? 0)

const loadData = async () => {
  if (!props.logFileId) {
    result.value = null
    return
  }
  loading.value = true
  error.value = ''
  try {
    result.value = await fetchSimilarFaultTypes(props.logFileId, 3)
  } catch (e: any) {
    error.value = e?.message || '相似案例分析请求失败'
    result.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => props.logFileId,
  (id) => {
    if (id) {
      void loadData()
    } else {
      result.value = null
    }
  },
  { immediate: true },
)

const formatSimilarity = (sim: number) => (sim * 100).toFixed(1) + '%'

const faultCategoryClass = (cat: string) => {
  if (cat === 'latency') return 'cat-latency'
  if (cat === 'connectivity') return 'cat-connectivity'
  if (cat === 'mixed') return 'cat-mixed'
  return 'cat-unknown'
}

const faultCategoryLabel = (cat: string) => {
  const map: Record<string, string> = {
    latency: '时延故障',
    connectivity: '通断故障',
    mixed: '混合故障',
    unknown: '未知',
  }
  return map[cat] || cat
}

const getAttachmentUrl = (caseId: string) => {
  return `${apiBase}/case_library/attachment/${encodeURIComponent(caseId)}`
}

const getLogFileUrl = (logFileId: string) => {
  return `${apiBase}/case_library/log_file/${encodeURIComponent(logFileId)}`
}

const getAttachmentDisplayName = (attachmentPath: string) => {
  if (!attachmentPath) return ''
  const parts = attachmentPath.split('_')
  return parts.length > 1 ? parts.slice(1).join('_') : attachmentPath
}
</script>

<template>
  <div v-if="!logFileId" class="similarity-section">
    <div class="similarity-empty">
      <span class="icon">🔍</span>
      <span>选择一个已完成的 KVCache 任务以查看相似案例分析</span>
    </div>
  </div>

  <div v-else class="similarity-section">
    <div class="section-header">
      <div class="section-title">
        <span class="icon">🔗</span>
        相似案例分析
      </div>
      <div class="section-subtitle">
        当前任务：{{ logFileName || logFileId }} · 案例库共 {{ librarySize }} 条，{{ uniqueTypesCount }} 种故障类型
      </div>
    </div>

    <div v-if="loading" class="similarity-loading">
      <div class="spinner"></div>
      <div>正在分析相似案例...</div>
    </div>

    <div v-else-if="error" class="similarity-error">
      <div class="error-icon">⚠️</div>
      <div>{{ error }}</div>
    </div>

    <div v-else-if="!topMatches.length" class="similarity-empty">
      <span class="icon">📭</span>
      <span>案例库为空，请先上传案例数据</span>
    </div>

    <div v-else class="similarity-results">
      <div
        v-for="match in topMatches"
        :key="match.rank"
        class="match-card"
        :class="'rank-' + match.rank"
      >
        <div class="match-header">
          <div class="rank-badge" :class="'rank-' + match.rank">
            TOP {{ match.rank }}
          </div>
          <div class="match-info">
            <div class="match-type">
              <span class="fault-type">{{ match.root_cause_type }}</span>
              <span
                class="fault-cat"
                :class="faultCategoryClass(match.fault_category)"
              >
                {{ faultCategoryLabel(match.fault_category) }}
              </span>
            </div>
            <div class="match-meta">
              <span v-if="match.log_file_name" class="log-name">
                来源：{{ match.log_file_name }}
              </span>
            </div>
            <div v-if="match.description" class="match-desc">
              {{ match.description }}
            </div>
            <div v-if="match.attachment_path || match.log_file_id" class="match-links">
              <a
                v-if="match.attachment_path"
                :href="getAttachmentUrl(match.case_id)"
                class="file-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                📎 下载附件：{{ getAttachmentDisplayName(match.attachment_path) }}
              </a>
              <a
                v-if="match.log_file_id"
                :href="getLogFileUrl(match.log_file_id)"
                class="file-link"
                target="_blank"
                rel="noopener noreferrer"
              >
                📁 原始日志文件
              </a>
            </div>
          </div>
          <div class="similarity-score">
            <div class="score-value">{{ formatSimilarity(match.similarity) }}</div>
            <div class="score-label">综合相似度</div>
          </div>
        </div>

        <div class="match-reason">
          <div class="reason-title">📝 分析原因</div>
          <div class="reason-text">{{ match.reason }}</div>
        </div>

        <div class="match-breakdown">
          <div class="breakdown-title">📊 维度明细</div>
          <div class="breakdown-table">
            <div class="breakdown-row breakdown-header-row">
              <span class="col-name">维度</span>
              <span class="col-score">得分</span>
              <span class="col-weight">权重</span>
              <span class="col-weighted">加权分</span>
              <span class="col-bar">可视化</span>
            </div>
            <div
              v-for="dim in match.breakdown.filter((d) => d.weight > 0).slice(0, 8)"
              :key="dim.name"
              class="breakdown-row"
            >
              <span class="col-name">{{ dim.label }}</span>
              <span class="col-score">{{ dim.score.toFixed(2) }}</span>
              <span class="col-weight">{{ dim.weight.toFixed(1) }}</span>
              <span class="col-weighted">{{ dim.weighted_score.toFixed(3) }}</span>
              <span class="col-bar">
                <div
                  class="score-bar"
                  :style="{ width: Math.max(dim.score * 100, dim.weighted_score * 100 / 3).toFixed(0) + '%' }"
                  :class="{ high: dim.score >= 0.7, medium: dim.score >= 0.4 && dim.score < 0.7 }"
                ></div>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.similarity-section {
  margin-top: 24px;
  padding: 20px;
  background: var(--bg-secondary, #f8f9fa);
  border-radius: 8px;
  border: 1px solid var(--border-color, #e0e0e0);
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #333);
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-subtitle {
  font-size: 12px;
  color: var(--text-secondary, #888);
}

.similarity-loading,
.similarity-error,
.similarity-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--text-secondary, #888);
  gap: 12px;
  font-size: 13px;
}

.similarity-error {
  color: #e74c3c;
}

.error-icon {
  font-size: 28px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e0e0e0;
  border-top-color: #007bff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.similarity-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.match-card {
  background: var(--bg-primary, #fff);
  border-radius: 8px;
  border: 2px solid var(--border-color, #e0e0e0);
  padding: 16px;
  transition: box-shadow 0.2s;
}

.match-card.rank-1 {
  border-color: #f39c12;
  background: linear-gradient(135deg, #fff9e6 0%, #fff 40%);
}

.match-card.rank-2 {
  border-color: #95a5a6;
  background: linear-gradient(135deg, #f8f9fa 0%, #fff 40%);
}

.match-card.rank-3 {
  border-color: #cd7f32;
  background: linear-gradient(135deg, #fdf2e9 0%, #fff 40%);
}

.match-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}

.rank-badge {
  flex-shrink: 0;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
}

.rank-badge.rank-1 {
  background: #f39c12;
}

.rank-badge.rank-2 {
  background: #95a5a6;
}

.rank-badge.rank-3 {
  background: #cd7f32;
}

.match-info {
  flex: 1;
  min-width: 0;
}

.match-type {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.fault-type {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #333);
  word-break: break-all;
}

.fault-cat {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.fault-cat.cat-latency {
  background: #e3f2fd;
  color: #1565c0;
}

.fault-cat.cat-connectivity {
  background: #fce4ec;
  color: #c62828;
}

.fault-cat.cat-mixed {
  background: #fff3e0;
  color: #e65100;
}

.fault-cat.cat-unknown {
  background: #f5f5f5;
  color: #757575;
}

.match-meta {
  font-size: 12px;
  color: var(--text-secondary, #888);
}

.match-desc {
  font-size: 12px;
  color: var(--text-secondary, #666);
  margin-top: 4px;
  line-height: 1.5;
  max-height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.match-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.file-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #1976d2;
  text-decoration: none;
  padding: 3px 10px;
  border: 1px solid #1976d2;
  border-radius: 12px;
  transition: all 0.15s ease;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-link:hover {
  background: #1976d2;
  color: #fff;
}

.similarity-score {
  flex-shrink: 0;
  text-align: center;
}

.score-value {
  font-size: 24px;
  font-weight: 700;
  color: #27ae60;
}

.match-card.rank-1 .score-value {
  color: #f39c12;
}

.match-card.rank-2 .score-value {
  color: #7f8c8d;
}

.match-card.rank-3 .score-value {
  color: #cd7f32;
}

.score-label {
  font-size: 11px;
  color: var(--text-secondary, #888);
}

.match-reason {
  background: var(--bg-secondary, #f8f9fa);
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 12px;
}

.reason-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #333);
  margin-bottom: 4px;
}

.reason-text {
  font-size: 12px;
  color: var(--text-secondary, #666);
  line-height: 1.6;
}

.match-breakdown {
  border-top: 1px solid var(--border-color, #e0e0e0);
  padding-top: 12px;
}

.breakdown-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #333);
  margin-bottom: 8px;
}

.breakdown-table {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.breakdown-row {
  display: grid;
  grid-template-columns: 120px 50px 50px 70px 1fr;
  gap: 8px;
  padding: 5px 8px;
  font-size: 11px;
  align-items: center;
}

.breakdown-header-row {
  font-weight: 600;
  color: var(--text-secondary, #888);
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  margin-bottom: 4px;
}

.col-name {
  color: var(--text-primary, #333);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-score,
.col-weight,
.col-weighted {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.col-bar {
  display: flex;
  align-items: center;
}

.score-bar {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  min-width: 4px;
  transition: width 0.3s;
}

.score-bar.high {
  background: #27ae60;
}

.score-bar.medium {
  background: #f39c12;
}

.score-bar:not(.high):not(.medium) {
  background: #e74c3c;
}

@media (max-width: 768px) {
  .breakdown-row {
    grid-template-columns: 80px 40px 40px 60px 1fr;
    gap: 4px;
  }

  .match-header {
    flex-wrap: wrap;
  }
}
</style>
