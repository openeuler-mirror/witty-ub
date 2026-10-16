<script setup lang="ts">
import { onMounted, ref } from 'vue'
import BaseModal from '../common/BaseModal.vue'
import { useExperience } from '../../composables/useExperience'
import { formatTime } from '../../utils/format'
import { renderAgentMarkdown } from '../../utils/agentMarkdown'
import CaseLibrarySection from './CaseLibrarySection.vue'

// 知识库两个板块：经验（Skill/Wiki）与案例库（全局故障案例）
const section = ref<'experience' | 'cases'>('experience')

const openExperienceSection = (type: 'SKILL' | 'WIKI') => {
  section.value = 'experience'
  void switchType(type)
}

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
        :class="['page-nav-item', { active: section === 'experience' && expType === 'SKILL' }]"
        @click="openExperienceSection('SKILL')"
      >
        🛠️ Skill管理
      </button>
      <button
        type="button"
        :class="['page-nav-item', { active: section === 'experience' && expType === 'WIKI' }]"
        @click="openExperienceSection('WIKI')"
      >
        📖 Wiki管理
      </button>
      <button
        type="button"
        :class="['page-nav-item', { active: section === 'cases' }]"
        @click="section = 'cases'"
      >
        📋 案例管理
      </button>
    </nav>

    <!-- ===== 案例管理（全局案例库） ===== -->
    <CaseLibrarySection v-if="section === 'cases'" />

    <template v-else>
      <!-- 操作栏 -->
      <div class="operate-bar">
        <button class="btn btn-primary" @click="openAdd">
          + 新建{{ expType === 'SKILL' ? 'Skill' : 'Wiki' }}
        </button>
        <div class="operate-right">
          <input
            class="input"
            style="width: 240px"
            v-model="searchKey"
            placeholder="搜索名称/描述/关键词..."
          />
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
            <span v-for="kw in item.keywords.slice(0, 5)" :key="kw" class="knowledge-kw-tag">{{
              kw
            }}</span>
            <span v-if="item.keywords.length > 5" class="knowledge-kw-more"
              >+{{ item.keywords.length - 5 }}</span
            >
          </div>
          <div class="knowledge-card-stats">
            <span>更新 {{ formatTime(item.updated_at) }}</span>
          </div>
          <div class="knowledge-card-actions">
            <button class="btn btn-sm btn-text" @click="openDetail(item)">查看</button>
            <button class="btn btn-sm btn-text btn-text-danger" @click="removeItem(item)">
              删除
            </button>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="totalPages > 1">
        <button v-for="p in totalPages" :key="p" :class="{ active: page === p }" @click="page = p">
          {{ p }}
        </button>
      </div>
    </template>

    <!-- 查看详情弹窗 -->
    <BaseModal
      :open="detailOpen"
      :title="detailItem?.name || '详情'"
      size="doc"
      @close="closeDetail"
    >
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
            <span v-for="kw in detailItem.keywords" :key="kw" class="knowledge-kw-tag">{{
              kw
            }}</span>
          </div>
          <div class="knowledge-detail-row">
            <span class="knowledge-detail-label">来源：</span>{{ detailItem.source }}
          </div>
          <div class="knowledge-detail-row">
            <span class="knowledge-detail-label">创建时间：</span
            >{{ formatTime(detailItem.created_at) }}
          </div>
        </div>
        <div class="knowledge-detail-content">
          <div
            class="knowledge-markdown"
            v-html="renderAgentMarkdown(detailItem.content || '（无正文内容）')"
          ></div>
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
        <textarea
          class="textarea"
          v-model="addForm.description"
          rows="2"
          placeholder="简要描述..."
        ></textarea>
      </div>
      <div class="form-group">
        <label class="form-label">关键词</label>
        <input
          class="input"
          v-model="addForm.keywords"
          placeholder="逗号分隔，如: KVCache, 诊断, 日志"
        />
      </div>
      <div class="form-group">
        <label class="form-label">正文内容（Markdown）</label>
        <textarea
          class="textarea"
          v-model="addForm.content"
          rows="10"
          placeholder="输入 Markdown 正文..."
        ></textarea>
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
  font-size: 13.5px;
  line-height: 1.7;
}

.knowledge-markdown {
  overflow-wrap: anywhere;
  color: var(--text);
}

.knowledge-markdown :deep(h1),
.knowledge-markdown :deep(h2),
.knowledge-markdown :deep(h3),
.knowledge-markdown :deep(h4) {
  margin: 14px 0 6px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
}

.knowledge-markdown :deep(h1) {
  font-size: 16px;
}

.knowledge-markdown :deep(h2) {
  font-size: 15px;
}

.knowledge-markdown :deep(h1:first-child),
.knowledge-markdown :deep(h2:first-child),
.knowledge-markdown :deep(h3:first-child),
.knowledge-markdown :deep(h4:first-child) {
  margin-top: 0;
}

.knowledge-markdown :deep(p) {
  margin: 6px 0;
}

.knowledge-markdown :deep(ul),
.knowledge-markdown :deep(ol) {
  margin: 6px 0;
  padding-left: 1.4em;
}

.knowledge-markdown :deep(li) {
  margin: 2px 0;
}

.knowledge-markdown :deep(code) {
  padding: 1px 5px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
}

.knowledge-markdown :deep(pre) {
  margin: 8px 0;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg);
  overflow-x: auto;
}

.knowledge-markdown :deep(pre code) {
  padding: 0;
  border: 0;
  background: transparent;
}

.knowledge-markdown :deep(.agent-markdown-table-wrap) {
  margin: 8px 0;
  overflow-x: auto;
}

.knowledge-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.knowledge-markdown :deep(th),
.knowledge-markdown :deep(td) {
  border: 1px solid var(--border);
  padding: 5px 8px;
  text-align: left;
}

.knowledge-markdown :deep(th) {
  background: var(--bg);
  font-weight: 600;
}
</style>
