<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  fetchLabelTaxonomy,
  searchDiagCases,
  type DiagCase,
  type LabelTaxonomy,
} from '../api/diagCase'

const PAGE_SIZE = 50

const props = defineProps<{ refreshToken?: number }>()
const emit = defineEmits<{
  'open-case': [caseId: string]
  'open-report': [reportId: string, faultId: string]
}>()

const loading = ref(false)
const error = ref('')
const cases = ref<Array<{ case: DiagCase; source_report?: { status: string } | null }>>([])
const total = ref(0)
const page = ref(1)
const taxonomy = ref<LabelTaxonomy | null>(null)
const firstLabel = ref('')
const secondLabel = ref('')
const unclassifiedOnly = ref(false)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const secondOptions = computed(
  () =>
    taxonomy.value?.pairs.find((item) => item.first_level_label === firstLabel.value)
      ?.second_level_labels ?? [],
)
const classificationText = (item: DiagCase) => {
  if (!item.first_level_label && !item.second_level_label) {
    return item.label_taxonomy_version ? '未分类' : '未分类 / 来源待核对'
  }
  return [item.first_level_label, item.second_level_label].filter(Boolean).join(' / ')
}
const verificationText = (item: DiagCase) => {
  if (item.status !== 'confirmed') return '未确认'
  return item.verification_json?.closed_loop ? '已验证' : '已确认未验证'
}
const reportStatusText = (status?: string | null) => {
  const labels: Record<string, string> = {
    deleted: '来源已删除',
    stale: '来源已变化',
    unavailable: '来源不可用',
  }
  return labels[status ?? ''] ?? '无关联报告'
}

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const result = await searchDiagCases({
      include_status: ['draft', 'confirmed', 'archived'],
      page_num: page.value,
      page_cnt: PAGE_SIZE,
      first_level_label: firstLabel.value || undefined,
      second_level_label: secondLabel.value || undefined,
      unclassified_only: unclassifiedOnly.value || undefined,
    })
    cases.value = result.matches
    total.value = result.total
    if (page.value > totalPages.value) page.value = totalPages.value
  } catch (err) {
    error.value = err instanceof Error ? err.message : '诊断案例加载失败'
    cases.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const applyFilter = () => {
  if (page.value === 1) {
    void load()
  } else {
    page.value = 1
  }
}

const changeFirst = () => {
  secondLabel.value = ''
  applyFilter()
}
const changeUnclassified = () => {
  if (unclassifiedOnly.value) {
    firstLabel.value = ''
    secondLabel.value = ''
  }
  applyFilter()
}

onMounted(async () => {
  try {
    taxonomy.value = await fetchLabelTaxonomy()
  } catch {
    taxonomy.value = null
  }
  await load()
})

watch(page, () => void load())
watch(
  () => props.refreshToken,
  () => void load(),
)
</script>

<template>
  <div class="diag-case-page">
    <div class="diag-toolbar">
      <select class="diag-select" v-model="firstLabel" @change="changeFirst">
        <option value="">全部一级分类</option>
        <option v-for="label in taxonomy?.first_level_labels ?? []" :key="label" :value="label">
          {{ label }}
        </option>
      </select>
      <select
        class="diag-select"
        v-model="secondLabel"
        :disabled="!firstLabel || unclassifiedOnly"
        @change="applyFilter"
      >
        <option value="">全部二级分类</option>
        <option v-for="label in secondOptions" :key="label" :value="label">{{ label }}</option>
      </select>
      <label class="diag-check">
        <input type="checkbox" v-model="unclassifiedOnly" @change="changeUnclassified" />
        仅未分类
      </label>
      <button class="ghost-btn" type="button" :disabled="loading" @click="load">刷新</button>
      <span class="diag-hint">共 {{ total }} 条</span>
    </div>

    <div v-if="loading" class="state-text">正在加载诊断案例...</div>
    <div v-else-if="error" class="dialog-error">
      {{ error }}
      <button class="ghost-btn" type="button" @click="load">重试</button>
    </div>
    <div v-else-if="cases.length === 0" class="state-text">暂无诊断案例</div>
    <template v-else>
      <div class="log-file-list">
        <div v-for="item in cases" :key="item.case.id" class="log-file-item">
          <div class="log-file-info">
            <div class="log-file-summary">
              <button
                class="table-link-btn"
                type="button"
                @click="emit('open-case', item.case.id)"
              >
                {{ item.case.case_no || item.case.id }}
              </button>
              <span class="diag-case-title">{{ item.case.title || '未命名案例' }}</span>
              <span class="status-badge">{{ item.case.status }}</span>
              <span class="status-badge">{{ verificationText(item.case) }}</span>
              <span class="status-badge">{{ classificationText(item.case) }}</span>
              <span class="log-file-time">
                来源：
                <button
                  v-if="item.case.report_id && item.source_report?.status === 'valid'"
                  class="table-link-btn"
                  type="button"
                  @click="emit('open-report', item.case.report_id, item.case.source_fault_id || '')"
                >
                  {{ item.case.report_id }}
                </button>
                <template v-else-if="item.case.report_id">
                  {{ reportStatusText(item.source_report?.status) }}
                </template>
                <template v-else>无关联报告</template>
              </span>
              <span class="log-file-time">{{ item.case.updated_at }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="diag-pagination" v-if="totalPages > 1">
        <button class="ghost-btn" type="button" :disabled="page <= 1" @click="page -= 1">
          上一页
        </button>
        <span class="pagination-pages">
          <button
            v-for="p in totalPages"
            :key="p"
            class="pagination-page-btn"
            :class="{ active: page === p }"
            type="button"
            @click="page = p"
          >
            {{ p }}
          </button>
        </span>
        <button class="ghost-btn" type="button" :disabled="page >= totalPages" @click="page += 1">
          下一页
        </button>
        <span class="diag-hint">第 {{ page }} / {{ totalPages }} 页</span>
      </div>
    </template>
  </div>
</template>
