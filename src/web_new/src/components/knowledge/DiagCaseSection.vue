<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageNav from '../common/PageNav.vue'
import {
  searchDiagCases,
  type DiagCase,
  type DiagCaseMatch,
} from '../../api/diagCaseLibrary'
import { fetchReportLabelTaxonomy, type ReportLabelTaxonomy } from '../../api/diagnosticReport'
import { useDiagCaseDetail } from '../../composables/useDiagCaseDetail'
import { useReportWorkbench } from '../../composables/useReportWorkbench'

const PAGE_SIZE = 50

const { open, openCase } = useDiagCaseDetail()
const { openReport } = useReportWorkbench()

const loading = ref(false)
const error = ref('')
const matches = ref<DiagCaseMatch[]>([])
const total = ref(0)
const page = ref(1)
const taxonomy = ref<ReportLabelTaxonomy | null>(null)
const firstLabel = ref('')
const secondLabel = ref('')
const unclassifiedOnly = ref(false)

const secondOptions = computed(() => {
  const pair = taxonomy.value?.pairs.find(
    (item) => item.first_level_label === firstLabel.value,
  )
  return pair?.second_level_labels ?? []
})

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

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const result = await searchDiagCases({
      pageNum: page.value,
      pageCnt: PAGE_SIZE,
      firstLevelLabel: firstLabel.value || null,
      secondLevelLabel: secondLabel.value || null,
      unclassifiedOnly: unclassifiedOnly.value,
    })
    matches.value = result.matches ?? []
    total.value = result.total ?? 0
    if (page.value > totalPages.value) page.value = totalPages.value
  } catch (err) {
    error.value = err instanceof Error ? err.message : '诊断案例加载失败'
    matches.value = []
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

const reportStatusText = (status?: string | null) => {
  const labels: Record<string, string> = {
    deleted: '来源已删除',
    stale: '来源已变化',
    unavailable: '来源不可用',
  }
  return labels[status ?? ''] ?? '无关联报告'
}

const loadTaxonomy = async () => {
  try {
    taxonomy.value = await fetchReportLabelTaxonomy()
  } catch {
    taxonomy.value = null
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

onMounted(() => {
  void loadTaxonomy()
  void load()
})

watch(open, (value, previous) => {
  if (previous && !value) void load()
})

watch(page, () => void load())
</script>

<template>
  <div class="diag-case-section">
    <div class="operate-bar">
      <div class="filter-bar">
        <select class="select" v-model="firstLabel" @change="changeFirst">
          <option value="">全部一级分类</option>
          <option
            v-for="label in taxonomy?.first_level_labels ?? []"
            :key="label"
            :value="label"
          >
            {{ label }}
          </option>
        </select>
        <select
          class="select"
          v-model="secondLabel"
          :disabled="!firstLabel || unclassifiedOnly"
          @change="applyFilter"
        >
          <option value="">全部二级分类</option>
          <option v-for="label in secondOptions" :key="label" :value="label">
            {{ label }}
          </option>
        </select>
        <label class="form-check">
          <input
            type="checkbox"
            v-model="unclassifiedOnly"
            @change="changeUnclassified"
          />
          仅未分类
        </label>
        <button class="btn btn-default btn-sm" type="button" :disabled="loading" @click="load">
          刷新
        </button>
        <span class="hint">共 {{ total }} 条</span>
      </div>
    </div>

    <div v-if="loading" class="empty">
      <div class="icon">⏳</div>
      <div>正在加载诊断案例...</div>
    </div>
    <div v-else-if="error" class="error-banner" role="alert">
      {{ error }}
      <button class="btn btn-sm btn-default" type="button" @click="load">重试</button>
    </div>
    <div v-else-if="matches.length === 0" class="empty">
      <div class="icon">📭</div>
      <div>暂无诊断案例</div>
      <div class="hint">在报告工作台确认报告并生成案例后会出现在这里</div>
    </div>
    <div v-else class="table-wrap">
      <table class="task-table">
        <thead>
          <tr>
            <th>案例</th>
            <th>分类</th>
            <th>状态</th>
            <th>验证</th>
            <th>来源报告</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in matches" :key="item.case.id">
            <td>
              <button class="btn-text btn" type="button" @click="openCase(item.case.id)">
                {{ item.case.case_no || item.case.id }}
              </button>
              <div class="hint">{{ item.case.title || '未命名案例' }}</div>
            </td>
            <td>{{ classificationText(item.case) }}</td>
            <td><span class="badge">{{ item.case.status }}</span></td>
            <td>
              <span
                class="badge"
                :class="{ 'badge-success': item.case.verification_json?.closed_loop }"
              >
                {{ verificationText(item.case) }}
              </span>
            </td>
            <td>
              <button
                v-if="item.case.report_id && item.source_report?.status === 'valid'"
                class="btn-text btn"
                type="button"
                @click="openReport(item.case.report_id, item.case.source_fault_id ?? '')"
              >
                {{ item.case.report_id }}
              </button>
              <span v-else-if="item.case.report_id" class="hint">
                {{ reportStatusText(item.source_report?.status) }}
              </span>
              <span v-else class="hint">无关联报告</span>
            </td>
            <td>{{ item.case.updated_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <PageNav v-if="total > PAGE_SIZE" v-model:page="page" :pages="totalPages" />
  </div>
</template>
