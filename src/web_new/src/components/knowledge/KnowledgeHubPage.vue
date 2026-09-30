<script setup lang="ts">
import { onMounted } from 'vue'
import BaseModal from '../common/BaseModal.vue'
import { useExperience } from '../../composables/useExperience'
import { formatTime } from '../../utils/format'

const {
  expType,
  loading,
  error,
  searchKey,
  page,
  filteredItems,
  totalPages,
  pagedItems,
  loadList,
  switchType,
  // detail
  detailOpen,
  detailLoading,
  detailItem,
  openDetail,
  closeDetail,
  // add
  addOpen,
  saving,
  addForm,
  addError,
  openAdd,
  closeAdd,
  saveAdd,
  // delete
  removeItem,
} = useExperience()

onMounted(() => void loadList())
</script>

<template>
  <div class="knowledge-hub-page">
    <!-- 类型切换 -->
    <nav class="page-nav" aria-label="知识库导航">
      <button
        type="button"
        :class="['page-nav-item', { active: expType === 'SKILL' }]"
        @click="switchType('SKILL')"
      >
        🛠️ Skill管理
      </button>
      <button
        type="button"
        :class="['page-nav-item', { active: expType === 'WIKI' }]"
        @click="switchType('WIKI')"
      >
        📖 Wiki管理
      </button>
    </nav>

    <!-- 操作栏 -->
    <div class="operate-bar">
      <button class="btn btn-primary" @click="openAdd">+ 新建{{ expType === 'SKILL' ? 'Skill' : 'Wiki' }}</button>
      <div class="operate-right">
        <input class="input" style="width: 240px" v-model="searchKey" placeholder="搜索名称/描述/关键词..." />
      </div>
    </div>

    <!-- 加载/错误/空态 -->
    <div v-if="loading" class="empty">
      <div class="icon">⏳</div>
      <div>正在加载...</div>
    </div>
    <div v-else-if="error" class="error-banner">{{ error }}</div>
    <div v-else-if="filteredItems.length === 0" class="empty">
      <div class="icon">📭</div>
      <div>暂无{{ expType === 'SKILL' ? 'Skill' : 'Wiki' }}</div>
      <div class="hint">点击上方按钮新建</div>
    </div>

    <!-- 列表 -->
    <div v-else class="card-grid">
      <div class="card knowledge-card" v-for="item in pagedItems" :key="item.id">
        <div class="knowledge-card-head">
          <div class="knowledge-card-name" :title="item.name">{{ item.name }}</div>
          <span class="badge badge-normal">{{ expType === 'SKILL' ? 'Skill' : 'Wiki' }}</span>
        </div>
        <div class="knowledge-card-desc" :title="item.description">
          {{ item.description || '—' }}
        </div>
        <div class="knowledge-card-keywords" v-if="item.keywords?.length">
          <span v-for="kw in item.keywords.slice(0, 5)" :key="kw" class="knowledge-kw-tag">{{ kw }}</span>
          <span v-if="item.keywords.length > 5" class="knowledge-kw-more">+{{ item.keywords.length - 5 }}</span>
        </div>
        <div class="knowledge-card-stats">
          <span>更新 {{ formatTime(item.updated_at) }}</span>
        </div>
        <div class="knowledge-card-actions">
          <button class="btn btn-sm btn-text" @click="openDetail(item)">查看</button>
          <button class="btn btn-sm btn-text btn-text-danger" @click="removeItem(item)">删除</button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="totalPages > 1">
      <button
        v-for="p in totalPages"
        :key="p"
        :class="{ active: page === p }"
        @click="page = p"
      >
        {{ p }}
      </button>
    </div>

    <!-- 查看详情弹窗 -->
    <BaseModal :open="detailOpen" :title="detailItem?.name || '详情'" size="xl" @close="closeDetail">
      <div v-if="detailLoading" class="empty">
        <div class="icon">⏳</div>
        <div>正在加载...</div>
      </div>
      <div v-else-if="detailItem">
        <div class="knowledge-detail-meta">
          <div class="knowledge-detail-row">
            <span class="knowledge-detail-label">名称：</span>{{ detailItem.name }}
          </div>
          <div class="knowledge-detail-row">
            <span class="knowledge-detail-label">描述：</span>{{ detailItem.description || '—' }}
          </div>
          <div class="knowledge-detail-row" v-if="detailItem.keywords?.length">
            <span class="knowledge-detail-label">关键词：</span>
            <span v-for="kw in detailItem.keywords" :key="kw" class="knowledge-kw-tag">{{ kw }}</span>
          </div>
          <div class="knowledge-detail-row">
            <span class="knowledge-detail-label">来源：</span>{{ detailItem.source }}
          </div>
          <div class="knowledge-detail-row">
            <span class="knowledge-detail-label">创建时间：</span>{{ formatTime(detailItem.created_at) }}
          </div>
        </div>
        <div class="knowledge-detail-content">
          <pre>{{ detailItem.content || '（无正文内容）' }}</pre>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-default" @click="closeDetail">关闭</button>
      </template>
    </BaseModal>

    <!-- 新建弹窗 -->
    <BaseModal
      :open="addOpen"
      :title="`新建${expType === 'SKILL' ? 'Skill' : 'Wiki'}`"
      size="lg"
      @close="closeAdd"
    >
      <div class="form-group">
        <label class="form-label required">名称</label>
        <input class="input" v-model="addForm.name" placeholder="输入名称（作为文件名/目录名）" />
      </div>
      <div class="form-group">
        <label class="form-label required">描述</label>
        <textarea class="textarea" v-model="addForm.description" rows="2" placeholder="简要描述..."></textarea>
      </div>
      <div class="form-group">
        <label class="form-label">关键词</label>
        <input class="input" v-model="addForm.keywords" placeholder="逗号分隔，如: KVCache, 诊断, 日志" />
      </div>
      <div class="form-group">
        <label class="form-label">正文内容（Markdown）</label>
        <textarea class="textarea" v-model="addForm.content" rows="10" placeholder="输入 Markdown 正文..."></textarea>
      </div>
      <div v-if="addError" class="form-error">{{ addError }}</div>
      <template #footer>
        <button class="btn btn-default" @click="closeAdd">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="saveAdd">
          {{ saving ? '保存中...' : '创建' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.knowledge-hub-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.knowledge-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.knowledge-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.knowledge-card-name {
  font-weight: 600;
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-card-desc {
  font-size: 13px;
  color: var(--text2);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 38px;
}

.knowledge-card-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  min-height: 22px;
}

.knowledge-kw-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--primary-bg);
  color: var(--primary);
  white-space: nowrap;
}

.knowledge-kw-more {
  font-size: 11px;
  color: var(--text3);
  align-self: center;
}

.knowledge-card-stats {
  font-size: 12px;
  color: var(--text3);
}

.knowledge-card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}

.knowledge-detail-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}

.knowledge-detail-row {
  font-size: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.knowledge-detail-label {
  color: var(--text2);
  font-weight: 500;
  flex-shrink: 0;
}

.knowledge-detail-content {
  max-height: 50vh;
  overflow: auto;
}

.knowledge-detail-content pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
}
</style>
