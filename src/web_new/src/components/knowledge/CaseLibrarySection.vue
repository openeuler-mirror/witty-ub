<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useCaseLibrary } from '../../composables/useCaseLibrary'
import { caseAttachmentUrl, type CaseRecord } from '../../api/caseLibrary'

const {
  cases,
  categories,
  loading,
  error,
  scope,
  filterText,
  expanded,
  load,
  filteredCategories,
  scopedCases,
  scopeTitle,
  selectAll,
  selectCategory,
  selectType,
  toggleExpand,
  editingCaseId,
  editCaseCategory,
  editCaseType,
  startEditCase,
  cancelEditCase,
  saveEditCase,
  removeCase,
  editingCategory,
  editingType,
  creatingCategory,
  newCategoryName,
  startEditCategory,
  cancelEditCategory,
  saveEditCategory,
  removeCategory,
  submitCreateCategory,
  startEditType,
  cancelEditType,
  saveEditType,
  removeType,
} = useCaseLibrary()

const uncategorized = computed(() =>
  categories.value.find((cat) => cat.is_uncategorized || cat.id === '__uncategorized__'),
)

// 编辑案例时可选项：小类跟随所选大类
const editCaseAvailableTypes = computed(() => {
  const cat = categories.value.find((item) => item.name === editCaseCategory.value)
  return cat?.types ?? []
})

const isActive = (key: string) => {
  const current = scope.value
  if (current.kind === 'all') return key === '__all__'
  if (current.kind === 'category') return key === `__cat__:${current.id}`
  return key === `__type__:${current.name}`
}

const cancelCreateCategory = () => {
  creatingCategory.value = false
  newCategoryName.value = ''
}

const featureLines = (item: CaseRecord) => {
  const lines: string[] = []
  const latency = item.features?.latency
  if (latency) {
    lines.push(
      `时延特征：超时分段 ${latency.timeout_segments?.join(', ') || '无'}；P99/P50 ${
        latency.p99_p50_ratio?.toFixed(1) ?? '-'
      }；Pod集中度 ${latency.pod_concentration || '-'}`,
    )
  }
  const conn = item.features?.connectivity
  if (conn) {
    lines.push(
      `通断特征：故障模式 ${Object.keys(conn.failure_mode_dist ?? {}).join(', ') || '无'}；Pod范围 ${
        conn.spatial_pod?.scope || '-'
      }；节点范围 ${conn.spatial_host?.scope || '-'}`,
    )
  }
  const summary = item.features?.summary
  if (summary) {
    lines.push(
      `统计：异常事件 ${summary.anomalous_event_count ?? 0}，故障事件 ${
        summary.failure_event_count ?? 0
      }，总记录 ${summary.total_parse_result_count ?? 0}`,
    )
  }
  return lines
}

onMounted(() => void load())
</script>
<template>
  <div v-if="loading" class="empty">
    <div class="icon">⏳</div>
    <div>正在加载案例库...</div>
  </div>
  <div v-else-if="error" class="error-banner" role="alert">
    案例加载失败：{{ error }}
    <button class="btn btn-sm btn-default" type="button" @click="load">重试</button>
  </div>
  <div v-else-if="cases.length === 0 && categories.length === 0" class="empty">
    <div class="icon">📭</div>
    <div>暂无案例</div>
    <div class="hint">诊断流程产出的案例会汇总在此，按故障大类/类型管理</div>
  </div>
  <div v-else class="case-layout">
    <aside class="case-sidebar">
      <div class="case-sidebar-search">
        <input class="input" v-model="filterText" placeholder="搜索故障大类/类型..." />
      </div>
      <div class="case-sidebar-list">
        <button
          type="button"
          :class="['case-type-item', { active: isActive('__all__') }]"
          @click="selectAll"
        >
          <span class="case-type-name">全部案例</span>
          <span class="case-type-count">{{ cases.length }}</span>
        </button>
        <div v-for="cat in filteredCategories" :key="cat.id" class="case-cat-group">
          <div class="case-cat-header">
            <button
              type="button"
              class="case-cat-toggle"
              :aria-expanded="expanded.has(cat.id)"
              @click.stop="toggleExpand(cat.id)"
            >
              {{ expanded.has(cat.id) ? '▼' : '▶' }}
            </button>
            <button
              type="button"
              :class="['case-cat-name', { active: isActive(`__cat__:${cat.id}`) }]"
              :title="cat.name"
              @click="selectCategory(cat.id)"
            >
              {{ cat.name }}
            </button>
            <span class="case-type-count">{{ cat.case_count }}</span>
            <template v-if="!uncategorized || cat.id !== uncategorized.id">
              <button
                class="case-cat-manage-btn"
                type="button"
                title="编辑分类"
                @click.stop="startEditCategory(cat)"
              >
                ✎
              </button>
              <button
                class="case-cat-manage-btn case-cat-delete-btn"
                type="button"
                title="删除分类（可递归删除子类型与案例）"
                @click.stop="removeCategory(cat)"
              >
                🗑
              </button>
            </template>
          </div>
          <div v-if="cat.description && editingCategory.id !== cat.id" class="case-cat-desc">
            {{ cat.description }}
          </div>
          <div v-if="editingCategory.id === cat.id" class="case-edit-form" @click.stop>
            <input class="input" v-model="editingCategory.name" placeholder="分类名称" />
            <input class="input" v-model="editingCategory.description" placeholder="描述（选填）" />
            <div class="case-edit-actions">
              <button class="btn btn-sm btn-primary" type="button" @click="saveEditCategory">
                保存
              </button>
              <button class="btn btn-sm btn-default" type="button" @click="cancelEditCategory">
                取消
              </button>
            </div>
          </div>
          <div v-if="expanded.has(cat.id)" class="case-cat-types">
            <div
              v-for="t in cat.types"
              :key="t.name"
              :class="[
                'case-type-item',
                'case-type-child',
                { active: isActive(`__type__:${t.name}`) },
              ]"
            >
              <button
                type="button"
                class="case-type-name"
                :title="t.name"
                @click="selectType(t.name)"
              >
                {{ t.name }}
              </button>
              <span class="case-type-count">{{ t.case_count }}</span>
              <template v-if="!uncategorized || cat.id !== uncategorized.id">
                <button
                  class="case-cat-manage-btn"
                  type="button"
                  title="编辑类型"
                  @click.stop="startEditType(t)"
                >
                  ✎
                </button>
                <button
                  class="case-cat-manage-btn case-cat-delete-btn"
                  type="button"
                  title="删除类型"
                  @click.stop="removeType(t)"
                >
                  🗑
                </button>
              </template>
            </div>
            <div
              v-if="editingType.id && cat.types.some((t) => t.id === editingType.id)"
              class="case-edit-form"
              @click.stop
            >
              <input class="input" v-model="editingType.name" placeholder="类型名称" />
              <input class="input" v-model="editingType.description" placeholder="描述（选填）" />
              <div class="case-edit-actions">
                <button class="btn btn-sm btn-primary" type="button" @click="saveEditType">
                  保存
                </button>
                <button class="btn btn-sm btn-default" type="button" @click="cancelEditType">
                  取消
                </button>
              </div>
            </div>
          </div>
        </div>
        <div v-if="filteredCategories.length === 0" class="case-type-empty">无匹配结果</div>
        <div class="case-sidebar-footer">
          <button
            v-if="!creatingCategory"
            class="btn btn-sm btn-default"
            type="button"
            @click="creatingCategory = true"
          >
            + 新建分类
          </button>
          <div v-else class="case-edit-form">
            <input
              class="input"
              v-model="newCategoryName"
              placeholder="分类名称"
              @keyup.enter="submitCreateCategory"
            />
            <div class="case-edit-actions">
              <button class="btn btn-sm btn-primary" type="button" @click="submitCreateCategory">
                创建
              </button>
              <button class="btn btn-sm btn-default" type="button" @click="cancelCreateCategory">
                取消
              </button>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <main class="case-main">
      <div class="case-main-header">
        <h2>{{ scopeTitle }}</h2>
        <span class="case-main-count">共 {{ scopedCases.length }} 条</span>
      </div>
      <div class="case-main-list">
        <div
          v-for="c in scopedCases"
          :key="c.id"
          class="card case-card"
          :class="{ 'case-card-editing': editingCaseId === c.id }"
        >
          <div class="case-card-header">
            <template v-if="editingCaseId === c.id">
              <input
                class="input"
                v-model="editCaseCategory"
                list="edit-cat-list"
                placeholder="大类（选择或输入）"
                @change="editCaseType = ''"
              />
              <datalist id="edit-cat-list">
                <option v-for="cat in categories" :key="cat.id" :value="cat.name"></option>
              </datalist>
              <input
                class="input"
                v-model="editCaseType"
                list="edit-type-list"
                placeholder="小类（选择或输入）"
              />
              <datalist id="edit-type-list">
                <option v-for="t in editCaseAvailableTypes" :key="t.id" :value="t.name"></option>
              </datalist>
              <button class="btn btn-sm btn-primary" type="button" @click="saveEditCase(c)">
                保存
              </button>
              <button class="btn btn-sm btn-default" type="button" @click="cancelEditCase">
                取消
              </button>
            </template>
            <template v-else>
              <span class="badge badge-pending">{{ c.root_cause_type }}</span>
              <span class="badge badge-success">{{ c.case_category || '未分类' }}</span>
              <span v-if="c.fault_category" class="badge badge-normal">{{ c.fault_category }}</span>
              <span class="case-card-time">{{ c.created_at || '—' }}</span>
              <a
                v-if="c.attachment_path"
                :href="caseAttachmentUrl(c.id)"
                class="btn btn-sm btn-text"
                target="_blank"
                rel="noopener noreferrer"
                title="下载附件"
              >
                📎 附件
              </a>
              <button
                class="btn btn-sm btn-text"
                type="button"
                title="修改分类"
                @click="startEditCase(c)"
              >
                ✎ 编辑
              </button>
              <button
                class="btn btn-sm btn-text btn-text-danger"
                type="button"
                @click="removeCase(c)"
              >
                删除
              </button>
            </template>
          </div>
          <div class="case-card-body">
            <div v-if="c.description" class="case-card-row">
              <span class="case-card-label">说明：</span>
              <span>{{ c.description }}</span>
            </div>
            <div v-for="line in featureLines(c)" :key="line" class="case-card-row">
              <span>{{ line }}</span>
            </div>
            <div class="case-card-row">
              <span class="case-card-label">关联任务：</span>
              <span>{{ c.task_names?.join(', ') || '无' }}</span>
            </div>
          </div>
        </div>
        <div v-if="scopedCases.length === 0" class="empty">
          <div class="icon">📭</div>
          <div>暂无匹配案例</div>
        </div>
      </div>
    </main>
  </div>
</template>
