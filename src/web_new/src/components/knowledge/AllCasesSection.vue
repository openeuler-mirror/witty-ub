<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageNav from '../common/PageNav.vue'
import { fetchCases, type CaseRecord } from '../../api/caseLibrary'
import { searchDiagCases, type DiagCase, type DiagCaseMatch } from '../../api/diagCaseLibrary'
import { useDiagCaseDetail } from '../../composables/useDiagCaseDetail'
import { useReportWorkbench } from '../../composables/useReportWorkbench'

type CaseSource = 'diagnosis' | 'legacy'

type OverviewRow = {
  source: CaseSource
  key: string
  id: string
  title: string
  classification: string
  status: string
  trust: string
  reportId: string | null
  faultId: string | null
  reportStatus: string
  time: string
}

const PAGE_SIZE = 50
const DIAG_PAGE_SIZE = 200

const { openCase, caseVersion } = useDiagCaseDetail()
const { openReport } = useReportWorkbench()

const loading = ref(false)
const error = ref('')
const page = ref(1)
const diagMatches = ref<DiagCaseMatch[]>([])
const legacyCases = ref<CaseRecord[]>([])

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

const legacyClassification = (item: CaseRecord) =>
  [item.case_category || '未分类', item.root_cause_type].filter(Boolean).join(' / ')

const rows = computed<OverviewRow[]>(() => {
  const diagRows = diagMatches.value.map((match) => ({
    source: 'diagnosis' as CaseSource,
    key: `diagnosis:${match.case.id}`,
    id: match.case.id,
    title: match.case.title || match.case.case_no || match.case.id,
    classification: diagClassification(match.case),
    status: match.case.status,
    trust: diagTrust(match.case),
    reportId: match.case.report_id,
    faultId: match.case.source_fault_id,
    reportStatus: match.source_report?.status ?? 'unavailable',
    time: match.case.updated_at,
  }))
  const legacyRows = legacyCases.value.map((item) => ({
    source: 'legacy' as CaseSource,
    key: `legacy:${item.id}`,
    id: item.id,
    title: item.description || item.root_cause_type || item.id,
    classification: legacyClassification(item),
    status: '历史',
    trust: '旧案例未验证',
    reportId: null,
    faultId: null,
    reportStatus: 'independent',
    time: item.created_at || '',
  }))
  const merged = [...diagRows, ...legacyRows]
  return merged.sort((a, b) => b.time.localeCompare(a.time))
})

const totalPages = computed(() => Math.max(1, Math.ceil(rows.value.length / PAGE_SIZE)))
const pagedRows = computed(() =>
  rows.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE),
)

const reportStatusText = (status: string) => {
  const labels: Record<string, string> = {
    deleted: '来源已删除',
    stale: '来源已变化',
    unavailable: '来源不可用',
  }
  return labels[status] ?? '无关联报告'
}

const loadDiagMatches = async () => {
  let pageNum = 1
  let total = 0
  const collected: DiagCaseMatch[] = []
  do {
    const result = await searchDiagCases({
      pageNum,
      pageCnt: DIAG_PAGE_SIZE,
    })
    const batch = result.matches ?? []
    collected.push(...batch)
    total = result.total ?? 0
    if (batch.length === 0) break
    pageNum += 1
  } while (collected.length < total)
  return collected
}

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const [diag, legacy] = await Promise.all([loadDiagMatches(), fetchCases()])
    diagMatches.value = diag
    legacyCases.value = legacy ?? []
    if (page.value > totalPages.value) page.value = totalPages.value
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案例加载失败'
    diagMatches.value = []
    legacyCases.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())

// 诊断案例确认或验证后，聚合列表要及时反映状态变化。
watch(caseVersion, () => void load())
watch(rows, () => {
  if (page.value > totalPages.value) page.value = totalPages.value
})

const sourceLabel = (value: CaseSource) => (value === 'diagnosis' ? '诊断案例' : '文件案例')

const openRow = (row: OverviewRow) => {
  if (row.source === 'diagnosis') {
    openCase(row.id)
  }
}
</script>

<template>
  <div class="case-overview">
    <div class="operate-bar">
      <div class="filter-bar">
        <button class="btn btn-default btn-sm" type="button" :disabled="loading" @click="load">
          刷新
        </button>
        <span class="hint">共 {{ rows.length }} 条</span>
      </div>
    </div>

    <div v-if="loading" class="empty">
      <div class="icon">⏳</div>
      <div>正在加载案例...</div>
    </div>
    <div v-else-if="error" class="error-banner" role="alert">
      {{ error }}
      <button class="btn btn-sm btn-default" type="button" @click="load">重试</button>
    </div>
    <div v-else-if="rows.length === 0" class="empty">
      <div class="icon">📭</div>
      <div>暂无案例</div>
    </div>
    <div v-else class="table-wrap">
      <table class="task-table">
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
          <tr v-for="row in pagedRows" :key="row.key">
            <td>
              <span class="badge" :class="{ 'badge-pending': row.source === 'legacy' }">
                {{ sourceLabel(row.source) }}
              </span>
            </td>
            <td>
              <button
                v-if="row.source === 'diagnosis'"
                class="btn-text btn"
                type="button"
                @click="openRow(row)"
              >
                {{ row.title }}
              </button>
              <span v-else>{{ row.title }}</span>
            </td>
            <td>{{ row.classification }}</td>
            <td>{{ row.status }}</td>
            <td>{{ row.trust }}</td>
            <td>
              <button
                v-if="row.reportId && row.reportStatus === 'valid'"
                class="btn-text btn"
                type="button"
                @click="openReport(row.reportId, row.faultId ?? '')"
              >
                {{ row.reportId }}
              </button>
              <span v-else-if="row.reportId" class="hint">
                {{ reportStatusText(row.reportStatus) }}
              </span>
              <span v-else class="hint">—</span>
            </td>
            <td>{{ row.time || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <PageNav v-if="rows.length > PAGE_SIZE" v-model:page="page" :pages="totalPages" />
  </div>
</template>

<style scoped>
.case-overview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
