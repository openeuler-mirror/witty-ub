<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PageNav from '../common/PageNav.vue'
import BaseModal from '../common/BaseModal.vue'
import { caseAttachmentUrl, fetchCases, type CaseRecord } from '../../api/caseLibrary'
import { searchDiagCases, type DiagCaseMatch } from '../../api/diagCaseLibrary'
import {
  fetchDiagnosticReports, fetchImportOptions, fetchReportLabelTaxonomy, importCases, importReportPath,
  type DiagnosticReportItem, type ReportLabelTaxonomy,
} from '../../api/diagnosticReport'
import { useDiagCaseDetail } from '../../composables/useDiagCaseDetail'
import { useReportWorkbench } from '../../composables/useReportWorkbench'
import { useOperator } from '../../composables/useOperator'
import {
  belongsToScope, caseOrigin, collectPages, documentProgress, filterDocuments, legacyCaseOrigin,
  formatReportTime, submitReportImport, validDocumentClassifications,
  loadKnowledgeWorkspace, matchesClassification, matchesKeywords, materialKey, populatedLabels, selectPrimary,
  sourceReportLabel, UNCLASSIFIED, type DocumentFilter, type KnowledgeView, type ImportBatch, type ImportMode, type ImportOptions,
} from '../../utils/caseWorkflow'

const PAGE_SIZE = 50
const props = defineProps<{ view: KnowledgeView; initialDocumentFilter?: DocumentFilter }>()
const emit = defineEmits<{ 'show-pending': [] }>()
const { openCase, caseVersion, bumpCaseVersion } = useDiagCaseDetail()
const { openReport } = useReportWorkbench()
const { operator, setOperator } = useOperator()
const loading = ref(false)
const error = ref('')
const matches = ref<DiagCaseMatch[]>([])
const reports = ref<DiagnosticReportItem[]>([])
const legacyCases = ref<CaseRecord[]>([])
const taxonomy = ref<ReportLabelTaxonomy | null>(null)
const selection = ref(selectPrimary(''))
const query = ref('')
const reportCases = ref<DiagCaseMatch[]>([])
const reportPage = ref(1)
const documentFilter = ref<DocumentFilter>(props.initialDocumentFilter ?? 'all')
const legacyPage = ref(1)
const importing = ref(false)
const importOpen = ref(false)
const importDialogOpen = computed(() => importOpen.value && props.view === 'documents')
const importError = ref('')
const file = ref<File | null>(null)
const importMode = ref<ImportMode>('upload')
const serverPath = ref('')
const importOptions = ref<ImportOptions | null>(null)
const optionsError = ref('')
const sourceName = ref('')
const declaredVerified = ref(true)
const batch = ref<ImportBatch | null>(null)
let loadVersion = 0

const scopedMatches = computed(() => matches.value.filter((item) => belongsToScope(item.case, 'library')))
const documentBase = computed(() => filterDocuments(reports.value, documentFilter.value))
const classificationItems = computed(() => props.view === 'documents'
  ? reports.value.flatMap(validDocumentClassifications)
  : scopedMatches.value.map((item) => item.case))
const firstOptions = computed(() => populatedLabels(
  taxonomy.value?.first_level_labels ?? [],
  classificationItems.value.map((item) => item.first_level_label),
))
const secondOptions = computed(() => populatedLabels(
  taxonomy.value?.pairs.find((pair) => pair.first_level_label === selection.value.first)?.second_level_labels ?? [],
  classificationItems.value.filter((item) => item.first_level_label === selection.value.first)
    .map((item) => item.second_level_label),
))
const count = (first: string, second = '') =>
  props.view === 'documents'
    ? filterDocuments(documentBase.value, 'all', first, second).length
    : scopedMatches.value.filter((item) => matchesClassification(item.case, first, second)).length
const filtered = computed(() => scopedMatches.value.filter((item) =>
  matchesClassification(item.case, selection.value.first, selection.value.second) &&
  matchesKeywords(query.value, [item.case.id, item.case.case_no, item.case.title, item.case.symptom_summary, item.case.root_cause_summary])))
const pages = computed(() => Math.max(1, Math.ceil(filtered.value.length / PAGE_SIZE)))
const pagedCases = computed(() => filtered.value.slice((selection.value.page - 1) * PAGE_SIZE, selection.value.page * PAGE_SIZE))
const casesByReport = computed(() => {
  const index = new Map<string, string[]>()
  for (const { case: item } of reportCases.value) {
    if (!item.report_id) continue
    const values = index.get(item.report_id) ?? []
    values.push(item.id, item.case_no ?? '', item.title ?? '', item.symptom_summary, item.root_cause_summary)
    index.set(item.report_id, values)
  }
  return index
})
const filteredReports = computed(() => filterDocuments(reports.value, documentFilter.value, selection.value.first, selection.value.second)
  .filter((report) => matchesKeywords(query.value, [
    report.report_id, report.title, report.kb_name, report.source_name,
    ...(casesByReport.value.get(report.report_id) ?? []),
  ])))
const reportPages = computed(() => Math.max(1, Math.ceil(filteredReports.value.length / PAGE_SIZE)))
const pagedReports = computed(() => filteredReports.value.slice((reportPage.value - 1) * PAGE_SIZE, reportPage.value * PAGE_SIZE))
const filteredLegacy = computed(() => legacyCases.value.filter((item) =>
  matchesKeywords(query.value, [item.id, item.root_cause_type, item.description, item.log_file_name])))
const legacyPages = computed(() => Math.max(1, Math.ceil(filteredLegacy.value.length / PAGE_SIZE)))
const pagedLegacy = computed(() => filteredLegacy.value.slice((legacyPage.value - 1) * PAGE_SIZE, legacyPage.value * PAGE_SIZE))
const outcomeLabels: Record<string, string> = {
  imported: '已导入', duplicate: '重复，已保留原记录', failed: '导入失败',
  confirmed: '已验证', draft: '待验证', skipped: '已跳过', existing: '已存在',
}
const outcomeLabel = (status: string) => outcomeLabels[status] ?? status

const loadCases = (scope: 'library' | 'all' = 'library') => collectPages(async (pageNum, pageCnt) => {
  const result = await searchDiagCases({
    scope, includeStatus: scope === 'all' ? ['draft', 'confirmed', 'archived'] : ['confirmed'],
    pageNum, pageCnt,
  })
  return { total: result.total, items: result.matches ?? [] }
})
const load = async () => {
  const version = ++loadVersion
  const view = props.view
  loading.value = true
  error.value = ''
  try {
    const [result, linkedCases] = await Promise.all([loadKnowledgeWorkspace(view, {
      cases: () => loadCases(),
      documents: (pageNum, pageCnt) => fetchDiagnosticReports({ pageNum, pageCnt }),
      legacy: fetchCases,
    }), view === 'documents' ? loadCases('all') : Promise.resolve([])])
    if (version !== loadVersion) return
    matches.value = result.cases
    reports.value = result.documents
    reportCases.value = linkedCases
    if (selection.value.first && selection.value.first !== UNCLASSIFIED && !firstOptions.value.includes(selection.value.first)) {
      selection.value = selectPrimary('')
    } else if (selection.value.second && !secondOptions.value.includes(selection.value.second)) {
      selection.value = { ...selection.value, second: '', page: 1 }
    }
    legacyCases.value = result.legacy ?? []
    selection.value.page = Math.min(selection.value.page, pages.value)
    reportPage.value = Math.min(reportPage.value, reportPages.value)
    legacyPage.value = Math.min(legacyPage.value, legacyPages.value)
  } catch (err) {
    if (version === loadVersion) error.value = err instanceof Error ? err.message : '案例加载失败'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}
const selectFirst = (first: string) => { selection.value = selectPrimary(first); reportPage.value = 1 }
const selectSecond = (second: string) => { selection.value = { ...selection.value, second, page: 1 }; reportPage.value = 1 }
const loadImportOptions = async () => {
  optionsError.value = ''
  try { importOptions.value = await fetchImportOptions() }
  catch { importOptions.value = null; optionsError.value = '无法读取服务器路径导入配置，文件上传仍可使用' }
}
const closeImport = () => { if (!importing.value) importOpen.value = false }
const toggleImport = () => {
  if (importing.value || props.view !== 'documents') return
  if (importOpen.value) { closeImport(); return }
  importOpen.value = true
  void loadImportOptions()
}
const submitImport = async () => {
  if (importing.value) return
  importError.value = ''
  batch.value = null
  try {
    setOperator(operator.value.trim())
    importing.value = true
    batch.value = await submitReportImport({
      mode: importMode.value, file: file.value, path: serverPath.value,
      operator: operator.value, sourceName: sourceName.value, verified: declaredVerified.value,
    }, importOptions.value, { upload: importCases, path: importReportPath })
    bumpCaseVersion()
  } catch (err) {
    importError.value = err instanceof Error ? err.message : '导入失败'
  } finally {
    importing.value = false
  }
}
onMounted(async () => {
  void fetchReportLabelTaxonomy().then((value) => { taxonomy.value = value }).catch(() => {})
  await load()
})
watch(() => props.view, (view) => {
  if (view !== 'documents') closeImport()
  selection.value = selectPrimary('')
  reportPage.value = 1
  legacyPage.value = 1
  query.value = ''
  void load()
})
const resetSearchPages = () => { reportPage.value = 1; legacyPage.value = 1; selection.value = { ...selection.value, page: 1 } }
watch(query, resetSearchPages)
watch(documentFilter, () => { reportPage.value = 1; selection.value = { ...selection.value, second: '', page: 1 } })
watch(() => props.initialDocumentFilter, (value) => { documentFilter.value = value ?? 'all' })
watch(caseVersion, () => void load())
</script>

<template>
  <div class="case-workspace">
    <header class="workspace-header">
      <div>
        <h2>{{ view === 'library' ? '已知案例' : '定界文档' }}</h2>
        <p>{{ view === 'library' ? '查看已检验的定界结论，以及从真实任务日志自动生成的有效案例。' : '跨资产阅读定界文档，人工检验定界结论的正确性，形成有效案例。' }}</p>
      </div>
      <div class="workspace-actions">
        <form class="workspace-search" role="search" @submit.prevent="resetSearchPages">
          <input v-model="query" class="input" type="search" :aria-label="view === 'documents' ? '搜索定界文档' : '搜索已知案例'" :placeholder="view === 'documents' ? '搜索文档标题、案例 ID 或来源' : '搜索案例 ID、标题或关键内容'" />
          <button class="btn btn-primary" type="submit">搜索</button>
        </form>
        <button class="btn btn-default" type="button" :disabled="loading || importing" @click="load">刷新</button>
        <button v-if="view === 'documents'" class="btn btn-primary" type="button" aria-haspopup="dialog" :aria-expanded="importDialogOpen" :disabled="importing" @click="toggleImport">导入定界报告</button>
      </div>
    </header>

    <BaseModal :open="importDialogOpen" label="导入定界报告" size="form" :close-on-esc="!importing" :close-on-overlay="!importing" @close="closeImport">
      <template #header>
        <div class="modal-header">
          <span>导入定界报告</span>
          <button class="modal-close" type="button" aria-label="关闭" :disabled="importing" @click="closeImport">✕</button>
        </div>
      </template>
      <section class="import-panel">
      <p class="hint">导入报告 JSON 或 ZIP，生成定界文档与案例，不关联当前资产或任务。未检验的结论可在「待验证」中核对。</p>
      <nav class="classification-tabs" aria-label="导入方式">
        <button type="button" :disabled="importing" :class="{ active: importMode === 'upload' }" :aria-pressed="importMode === 'upload'" @click="importMode = 'upload'; importError = ''">文件上传</button>
        <button type="button" :disabled="importing" :class="{ active: importMode === 'path' }" :aria-pressed="importMode === 'path'" @click="importMode = 'path'; importError = ''">服务器路径</button>
      </nav>
      <form class="import-form" @submit.prevent="submitImport">
        <template v-if="importMode === 'upload'">
          <label>报告文件<input type="file" accept=".json,.zip" :disabled="importing" @change="file = ($event.target as HTMLInputElement).files?.[0] ?? null" /></label>
          <p v-if="file" class="hint">已选择：{{ file.name }}</p>
        </template>
            <template v-else>
          <p class="hint">仅支持服务器文件系统的绝对路径，不是浏览器所在电脑的本地路径。Docker 部署请填写容器内挂载路径，仅允许读取已配置的只读导入目录。</p>
          <p v-if="optionsError" class="error-banner" role="alert">{{ optionsError }} <button type="button" class="btn btn-default" @click="loadImportOptions">重试</button></p>
          <p v-else-if="!importOptions" class="hint">正在读取导入配置…</p>
          <p v-else-if="!importOptions.path_import_enabled" class="error-banner" role="alert">服务器路径导入未启用，请使用文件上传或联系管理员配置允许的只读导入目录。</p>
          <p v-if="importOptions?.allowed_roots.length" class="hint">允许的只读导入目录：{{ importOptions.allowed_roots.join('、') }}</p>
          <label>服务器绝对路径<input v-model="serverPath" class="input" type="text" autocomplete="off" placeholder="输入服务器上 JSON 或 ZIP 文件的绝对路径" :disabled="importing || !importOptions?.path_import_enabled" /></label>
        </template>
        <label>报告来源<input v-model="sourceName" class="input" placeholder="如合作伙伴或现场团队" :disabled="importing" /></label>
        <label>操作人<input :value="operator" class="input" autocomplete="name" :disabled="importing" @input="setOperator(($event.target as HTMLInputElement).value)" /></label>
        <label class="verification-declaration"><input v-model="declaredVerified" type="checkbox" :disabled="importing" />外部已验证声明：这些定界结论已由人工检验正确，按有效案例导入</label>
        <p v-if="importError" class="error-banner" role="alert">{{ importError }}</p>
        <button class="btn btn-primary" type="submit" :disabled="importing || (importMode === 'path' && !importOptions?.path_import_enabled)">{{ importing ? '正在导入…' : '开始导入' }}</button>
      </form>
      <div v-if="batch" class="import-result" role="status">
        <h4>导入结果 · {{ batch.file_count }} 个文件</h4>
        <p>成功 {{ batch.summary.imported }} · 重复 {{ batch.summary.duplicate }} · 失败 {{ batch.summary.failed }}</p>
        <p>已验证案例 {{ batch.summary.cases.confirmed }} · 待验证 {{ batch.summary.cases.draft }} · 已存在 {{ batch.summary.cases.existing }} · 跳过 {{ batch.summary.cases.skipped }}</p>
        <details class="import-items" :open="batch.status !== 'completed'">
          <summary>查看逐项结果（{{ batch.items.length }} 个文件）</summary>
        <details v-for="(item, index) in batch.items" :key="`${index}:${item.original_name}`" :open="Boolean(item.error) || item.status === 'failed' || item.cases?.some((entry) => Boolean(entry.missing_fields?.length))">
          <summary>{{ item.original_name }} · {{ outcomeLabel(item.status) }}</summary>
          <p v-if="item.error" class="error-banner">{{ item.error }}</p>
          <ul><li v-for="(entry, entryIndex) in item.cases ?? []" :key="entryIndex">结论 {{ entryIndex + 1 }}：{{ outcomeLabel(entry.status) }}<template v-if="entry.reason"> · {{ entry.reason }}</template><template v-if="entry.missing_fields?.length"> · 缺少 {{ entry.missing_fields.join('、') }}</template></li></ul>
        </details>
        </details>
        <button v-if="batch.declared_verified === false || batch.summary.cases.draft || batch.summary.cases.skipped" class="btn btn-text" type="button" :disabled="importing" @click="closeImport(); emit('show-pending')">查看待验证定界文档</button>
      </div>
      </section>
      <template #footer>
        <button class="btn btn-default" type="button" :disabled="importing" @click="closeImport">关闭</button>
      </template>
    </BaseModal>

    <div v-if="loading" class="empty">正在加载…</div>
    <div v-else-if="error" class="error-banner" role="alert">{{ error }} <button class="btn btn-default" type="button" @click="load">重试</button></div>
    <template v-else>
      <section v-if="view === 'documents'" class="workspace-section">
        <nav class="classification-tabs" aria-label="定界文档筛选">
          <button type="button" :class="{ active: documentFilter === 'all' }" :aria-pressed="documentFilter === 'all'" @click="documentFilter = 'all'">全部文档 <span>{{ reports.length }}</span></button>
          <button type="button" :class="{ active: documentFilter === 'pending' }" :aria-pressed="documentFilter === 'pending'" @click="documentFilter = 'pending'">待验证 <span>{{ filterDocuments(reports, 'pending').length }}</span></button>
        </nav>
        <nav class="classification-tabs" aria-label="文档一级分类">
          <button v-for="option in [{ value: '', label: '全部' }, { value: UNCLASSIFIED, label: '未分类' }, ...firstOptions.map((label) => ({ value: label, label }))]" :key="option.value" type="button" :class="{ active: selection.first === option.value }" :aria-pressed="selection.first === option.value" @click="selectFirst(option.value)">{{ option.label }} <span>{{ count(option.value) }}</span></button>
        </nav>
        <nav v-if="selection.first && selection.first !== UNCLASSIFIED && secondOptions.length" class="classification-tabs secondary" aria-label="文档二级分类">
          <button type="button" :class="{ active: !selection.second }" :aria-pressed="!selection.second" @click="selectSecond('')">全部 <span>{{ count(selection.first) }}</span></button>
          <button v-for="label in secondOptions" :key="label" type="button" :class="{ active: selection.second === label }" :aria-pressed="selection.second === label" @click="selectSecond(label)">{{ label }} <span>{{ count(selection.first, label) }}</span></button>
        </nav>
        <p class="hint">共 {{ filteredReports.length }} 份定界文档</p>
        <div v-if="!pagedReports.length" class="empty">{{ query ? '没有匹配的定界文档' : documentFilter === 'pending' ? '暂无待验证定界文档' : '暂无定界文档' }}</div>
        <div v-else class="table-wrap"><table class="task-table">
          <thead><tr><th>定界文档</th><th>来源</th><th>生成时间</th><th>结论数</th><th>已验证</th><th>操作</th></tr></thead>
          <tbody><tr v-for="report in pagedReports" :key="`report:${report.report_id}`">
            <td>{{ report.title || '未命名定界文档' }}</td>
            <td>{{ report.kb_name || report.source_name || (report.imported ? '外部导入' : '诊断任务') }}</td>
            <td>{{ formatReportTime(report.generated_at) }}</td>
            <td>{{ report.fault_count ?? '—' }}</td>
            <td>{{ documentProgress(report) }}</td>
            <td><button class="btn btn-text" type="button" :disabled="report.report_available === false" @click="openReport(report.report_id)">{{ report.report_available === false ? '文档不可用' : '查看文档' }}</button></td>
          </tr></tbody>
        </table></div>
        <PageNav v-if="reportPages > 1" v-model:page="reportPage" :pages="reportPages" />
      </section>

      <section v-if="view === 'library'" class="workspace-section">
        <nav class="classification-tabs" aria-label="一级分类">
          <button v-for="option in [{ value: '', label: '全部' }, { value: UNCLASSIFIED, label: '未分类' }, ...firstOptions.map((label) => ({ value: label, label }))]" :key="option.value" type="button" :class="{ active: selection.first === option.value }" :aria-pressed="selection.first === option.value" @click="selectFirst(option.value)">{{ option.label }} <span>{{ count(option.value) }}</span></button>
        </nav>
        <nav v-if="selection.first && selection.first !== UNCLASSIFIED && secondOptions.length" class="classification-tabs secondary" aria-label="二级分类">
          <button type="button" :class="{ active: !selection.second }" :aria-pressed="!selection.second" @click="selectSecond('')">全部 <span>{{ count(selection.first) }}</span></button>
          <button v-for="label in secondOptions" :key="label" type="button" :class="{ active: selection.second === label }" :aria-pressed="selection.second === label" @click="selectSecond(label)">{{ label }} <span>{{ count(selection.first, label) }}</span></button>
        </nav>
        <p class="hint">共 {{ filtered.length }} 条</p>
        <div v-if="!pagedCases.length" class="empty">{{ query ? '没有匹配的文档案例' : '暂无文档案例。检验定界文档或导入已验证案例后，将在这里沉淀。' }}</div>
        <div v-else class="table-wrap"><table class="task-table case-table">
          <colgroup><col /><col class="case-meta-column" /><col class="case-meta-column" /></colgroup>
          <thead><tr><th>案例</th><th>来源</th><th>更新时间</th></tr></thead>
          <tbody><tr v-for="match in pagedCases" :key="materialKey('diagnosis', match.case.id)">
            <td><button class="btn btn-text case-title" type="button" @click="openCase(match.case.id)">{{ match.case.title || '未命名案例' }}</button><p class="case-summary" :title="match.case.symptom_summary">{{ match.case.case_no || match.case.id }} · {{ match.case.symptom_summary }}</p></td>
            <td class="case-source"><span class="case-origin">{{ caseOrigin(match.case) }}</span><button v-if="match.case.report_id && match.source_report?.status === 'valid'" class="btn btn-text case-source-link" type="button" @click="openReport(match.case.report_id, match.case.source_fault_id ?? '')">查看来源定界文档</button><span v-else-if="match.case.report_id" class="hint case-source-status">{{ sourceReportLabel(match.source_report?.status) }}</span></td>
            <td>{{ match.case.updated_at || '—' }}</td>
          </tr></tbody>
        </table></div>
        <PageNav v-if="pages > 1" v-model:page="selection.page" :pages="pages" />
      </section>

      <section v-if="view === 'library'" class="workspace-section historical-material">
        <h3>任务与文件案例 · {{ filteredLegacy.length }} 条</h3>
        <div v-if="pagedLegacy.length" class="table-wrap"><table class="task-table">
          <thead><tr><th>案例</th><th>来源</th><th>附件</th></tr></thead>
          <tbody><tr v-for="item in pagedLegacy" :key="materialKey('legacy', item.id)">
            <td><details><summary>{{ item.root_cause_type || '任务案例' }}</summary><p>{{ item.description || '暂无描述' }}</p><p v-if="item.log_file_name || item.log_file_id">日志：{{ item.log_file_name || item.log_file_id }}</p><p v-if="item.task_names?.length || item.task_ids?.length">任务：{{ (item.task_names?.length ? item.task_names : item.task_ids)?.join('、') }}</p><pre v-if="item.features">{{ JSON.stringify(item.features, null, 2) }}</pre></details></td>
            <td>{{ legacyCaseOrigin(item) }}</td>
            <td><a v-if="item.attachment_path" :href="caseAttachmentUrl(item.id)" target="_blank" rel="noopener noreferrer">查看附件</a><span v-else>—</span></td>
          </tr></tbody>
        </table></div>
        <PageNav v-if="legacyPages > 1" v-model:page="legacyPage" :pages="legacyPages" />
        <p v-if="!pagedLegacy.length" class="empty">{{ query ? '没有匹配的任务与文件案例' : '暂无任务与文件案例' }}</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.case-workspace { display: grid; gap: 24px; }
.historical-material pre { white-space: pre-wrap; overflow-wrap: anywhere; max-width: 40rem; }
.workspace-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; }
.workspace-header h2 { margin: 0 0 8px; font-size: 20px; }
.workspace-header p, .case-summary { margin: 0; color: var(--text2); line-height: 1.6; }
.workspace-actions { display: flex; flex-shrink: 0; align-items: center; justify-content: flex-end; gap: 12px; }
.workspace-actions > button { flex: 0 0 auto; white-space: nowrap; }
.workspace-section { min-width: 0; }
.workspace-search { display: flex; flex: 0 0 340px; min-width: 0; }
.workspace-search input { min-width: 0; border-radius: var(--radius-sm) 0 0 var(--radius-sm); border-right: 0; }
.workspace-search button { height: 36px; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; flex: 0 0 auto; }
.workspace-search:focus-within { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-sm); }
.workspace-section h3 { margin: 0 0 12px; font-size: 16px; }
.classification-tabs { display: flex; flex-wrap: nowrap; overflow-x: auto; max-width: 100%; gap: 8px; padding: 4px 2px 12px; border-bottom: 1px solid var(--border); scrollbar-width: thin; overscroll-behavior-x: contain; }
.classification-tabs button { flex: 0 0 auto; white-space: nowrap; border: 0; background: transparent; padding: 9px 14px; border-radius: 6px; color: var(--text2); cursor: pointer; font: inherit; }
.classification-tabs button.active { background: #eaf2ff; color: #1d4ed8; font-weight: 600; }
.classification-tabs span { margin-left: 6px; font-size: 12px; opacity: .75; }
.classification-tabs.secondary { margin-top: 12px; }
.case-title { display: block; max-width: 100%; padding: 0; overflow: hidden; text-align: left; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.case-summary { max-width: 100%; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.case-table { min-width: 680px; table-layout: fixed; }
.case-table .case-meta-column { width: 180px; }
.case-table td { height: auto; padding: 14px 12px; vertical-align: top; }
.case-origin { display: block; margin-bottom: 4px; line-height: 1.5; }
.case-source { white-space: normal; }
.case-source-link { display: block; padding: 0; line-height: 1.5; text-align: left; }
.case-source-status { display: block; line-height: 1.5; }
.import-panel { padding: 24px; border: 1px solid var(--border); border-radius: 10px; background: var(--bg); }
.import-panel h3 { margin-top: 0; }
.import-form { display: grid; gap: 16px; max-width: 680px; }
.import-form label { display: grid; gap: 8px; }
.import-form .verification-declaration { display: flex; align-items: flex-start; gap: 8px; }
.import-form button { justify-self: start; }
.import-result { margin-top: 24px; line-height: 1.8; }
.import-result details { border-top: 1px solid var(--border); padding: 10px 0; }
.historical-material { border-top: 1px solid var(--border); padding-top: 20px; }
.workspace-section > .hint { margin: 12px 0; }
summary { cursor: pointer; }
@media (max-width: 1050px) {
  .workspace-header { flex-wrap: wrap; }
  .workspace-actions { width: 100%; flex-wrap: wrap; }
  .workspace-search { flex: 1 1 200px; }
}
</style>
