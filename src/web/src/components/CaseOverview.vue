<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiBase, request } from '../api/client'
import { searchDiagCases, type DiagCase } from '../api/diagCase'

type LegacyCase = {
  id: string
  case_category?: string
  root_cause_type: string
  description?: string
  attachment_path?: string
  created_at?: string
}

type OverviewRow = {
  source: 'diagnosis' | 'legacy'
  key: string
  id: string
  title: string
  classification: string
  status: string
  trust: string
  reportId: string | null
  faultId: string | null
  time: string
}

const props = defineProps<{ source: 'all' | 'legacy' }>()
const emit = defineEmits<{
  'open-case': [caseId: string]
  'open-report': [reportId: string, faultId: string]
}>()

const loading = ref(false)
const error = ref('')
const diagCases = ref<DiagCase[]>([])
const legacyCases = ref<LegacyCase[]>([])

const diagClassification = (item: DiagCase) => {
  if (!item.first_level_label && !item.second_level_label) {
    return item.label_taxonomy_version ? '未分类' : '未分类 / 来源待核对'
  }
  return [item.first_level_label, item.second_level_label].filter(Boolean).join(' / ')
}

const diagTrust = (item: DiagCase) => {
  if (item.status !== 'confirmed') return '未确认'
  return item.verification_json?.closed_loop ? '已验证' : '已确认未验证'
}

const legacyClassification = (item: LegacyCase) =>
  [item.case_category || '未分类', item.root_cause_type].filter(Boolean).join(' / ')

const rows = computed<OverviewRow[]>(() => {
  const diagRows = diagCases.value.map((item) => ({
    source: 'diagnosis' as const,
    key: `diagnosis:${item.id}`,
    id: item.id,
    title: item.title || item.case_no || item.id,
    classification: diagClassification(item),
    status: item.status,
    trust: diagTrust(item),
    reportId: item.report_id ?? null,
    faultId: item.source_fault_id ?? null,
    time: item.updated_at,
  }))
  const legacyRows = legacyCases.value.map((item) => ({
    source: 'legacy' as const,
    key: `legacy:${item.id}`,
    id: item.id,
    title: item.description || item.root_cause_type || item.id,
    classification: legacyClassification(item),
    status: '历史',
    trust: '旧案例未验证',
    reportId: null,
    faultId: null,
    time: item.created_at || '',
  }))
  const merged = props.source === 'legacy' ? legacyRows : [...diagRows, ...legacyRows]
  return merged.sort((a, b) => b.time.localeCompare(a.time))
})

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const legacyTask = request<LegacyCase[]>('/case_library/list')
    if (props.source === 'legacy') {
      legacyCases.value = (await legacyTask) ?? []
    } else {
      const [diag, legacy] = await Promise.all([searchDiagCases({
        include_status: ['draft', 'confirmed', 'archived'],
        page_num: 1,
        page_cnt: 200,
      }), legacyTask])
      diagCases.value = (diag.matches ?? []).map((item) => item.case)
      legacyCases.value = legacy ?? []
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案例加载失败'
    diagCases.value = []
    legacyCases.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())

const attachmentUrl = (caseId: string) =>
  `${apiBase}/case_library/attachment/${encodeURIComponent(caseId)}`

const openRow = (row: OverviewRow) => {
  if (row.source === 'diagnosis') emit('open-case', row.id)
}

const openReport = (row: OverviewRow) => {
  if (!row.reportId) return
  emit('open-report', row.reportId, row.faultId ?? '')
}
</script>

<template>
  <div class="diag-case-page">
    <div class="diag-toolbar">
      <span class="diag-hint">共 {{ rows.length }} 条</span>
      <button class="ghost-btn" type="button" :disabled="loading" @click="load">刷新</button>
    </div>

    <div v-if="loading" class="state-text">正在加载案例...</div>
    <div v-else-if="error" class="dialog-error">
      {{ error }}
      <button class="ghost-btn" type="button" @click="load">重试</button>
    </div>
    <div v-else-if="rows.length === 0" class="state-text">暂无案例</div>
    <table v-else class="task-table">
      <thead>
        <tr>
          <th>来源</th>
          <th>案例</th>
          <th>分类</th>
          <th>状态</th>
          <th>验证</th>
          <th>来源报告</th>
          <th>时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.key">
          <td>
            <span class="status-badge">{{ row.source === 'diagnosis' ? '诊断案例' : '文件案例' }}</span>
          </td>
          <td>
            <button
              v-if="row.source === 'diagnosis'"
              class="table-link-btn"
              type="button"
              @click="openRow(row)"
            >
              {{ row.title }}
            </button>
            <span v-else :title="row.title">{{ row.title }}</span>
            <a
              v-if="row.source === 'legacy' && legacyCases.find((item) => item.id === row.id)?.attachment_path"
              class="diag-hint"
              :href="attachmentUrl(row.id)"
              target="_blank"
              rel="noopener noreferrer"
            >
              📎 附件
            </a>
          </td>
          <td>{{ row.classification }}</td>
          <td>{{ row.status }}</td>
          <td>{{ row.trust }}</td>
          <td>
            <button
              v-if="row.reportId"
              class="table-link-btn"
              type="button"
              @click="openReport(row)"
            >
              {{ row.reportId }}
            </button>
            <span v-else class="diag-hint">—</span>
          </td>
          <td>{{ row.time || '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
