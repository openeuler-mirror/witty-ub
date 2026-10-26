<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import BaseModal from '../common/BaseModal.vue'
import KeywordTags from '../common/KeywordTags.vue'
import LineClampText from '../common/LineClampText.vue'
import PageNav from '../common/PageNav.vue'
import { useExperience } from '../../composables/useExperience'
import { formatTime } from '../../utils/format'
import { renderAgentMarkdown } from '../../utils/agentMarkdown'
import CaseLibrarySection from './CaseLibrarySection.vue'
import DiagCaseSection from './DiagCaseSection.vue'
import AllCasesSection from './AllCasesSection.vue'

// 知识库两个板块：经验与案例库；案例库按来源区分诊断案例与文件案例
const section = ref<'experience' | 'cases'>('experience')
const caseSource = ref<'all' | 'diagnosis' | 'legacy'>('all')

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

// 关键词差异化排序：当前页内出现次数少的（更稀有、更有区分度）排前面，
// 同频次保持原序；通用词（每张卡都有）自然沉底
const rankedPagedItems = computed(() => {
  const freq = new Map<string, number>()
  for (const item of pagedItems.value) {
    for (const kw of item.keywords ?? []) {
      freq.set(kw, (freq.get(kw) ?? 0) + 1)
    }
  }
  return pagedItems.value.map((item) => ({
    ...item,
    keywords: [...(item.keywords ?? [])].sort(
      (a, b) => (freq.get(a) ?? 0) - (freq.get(b) ?? 0),
    ),
  }))
})
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
        📚 案例库
      </button>
    </nav>

    <!-- ===== 案例库（诊断案例与文件案例统一入口） ===== -->
    <template v-if="section === 'cases'">
      <div class="case-source-bar">
        <button
          type="button"
          class="btn btn-sm"
          :class="caseSource === 'all' ? 'btn-primary' : 'btn-default'"
          @click="caseSource = 'all'"
        >
          全部来源
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :class="caseSource === 'diagnosis' ? 'btn-primary' : 'btn-default'"
          @click="caseSource = 'diagnosis'"
        >
          诊断案例
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :class="caseSource === 'legacy' ? 'btn-primary' : 'btn-default'"
          @click="caseSource = 'legacy'"
        >
          文件案例
        </button>
      </div>
      <AllCasesSection v-if="caseSource === 'all'" />
      <DiagCaseSection v-else-if="caseSource === 'diagnosis'" />
      <CaseLibrarySection v-else />
    </template>

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
        <div class="card knowledge-card" v-for="item in rankedPagedItems" :key="item.id">
          <div class="knowledge-card-head">
            <div class="knowledge-card-name" :title="item.name">{{ item.name }}</div>
            <span class="knowledge-type-badge">{{ expType === 'SKILL' ? 'Skill' : 'Wiki' }}</span>
          </div>
          <LineClampText class="knowledge-card-desc" :text="item.description || '—'" />
          <KeywordTags class="knowledge-card-keywords" :keywords="item.keywords ?? []" />
          <div class="knowledge-card-footer">
            <span class="knowledge-card-time">更新 {{ formatTime(item.updated_at) }}</span>
            <div class="knowledge-card-actions">
              <button class="knowledge-view-btn" @click="openDetail(item)">查看</button>
              <button class="knowledge-delete-btn" @click="removeItem(item)">删除</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <PageNav v-if="totalPages > 1" v-model:page="page" :pages="totalPages" />
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

.case-source-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.knowledge-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: none;
}

.knowledge-card:hover {
  transform: none;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.knowledge-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.knowledge-card-name {
  min-width: 0;
  flex: 1;
  font-weight: 600;
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-type-badge {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  background: var(--primary-bg);
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}

.knowledge-card-desc {
  font-size: 13px;
  line-height: 19px;
  height: 38px;
  color: var(--text2);
  overflow: hidden;
  word-break: break-word;
}

.knowledge-kw-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--primary-bg);
  color: var(--primary);
  white-space: nowrap;
}

.knowledge-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--bg);
}

.knowledge-card-time {
  font-size: 12px;
  color: var(--text3);
}

.knowledge-card-actions {
  display: flex;
  gap: 8px;
}

.knowledge-view-btn,
.knowledge-delete-btn {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 6px;
  cursor: pointer;
  background: none;
  transition: background 0.15s;
}

.knowledge-view-btn {
  color: var(--primary);
  border: 1px solid #bfdbfe;
}

.knowledge-view-btn:hover {
  background: var(--primary-bg);
}

.knowledge-delete-btn {
  color: var(--danger);
  border: 1px solid #fecaca;
}

.knowledge-delete-btn:hover {
  background: #fef2f2;
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
