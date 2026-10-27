<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BaseModal from '../common/BaseModal.vue'
import {
  diagnosticReportHtmlUrl, fetchDiagnosticReport, previewReportCase, verifyReportFault,
  type DiagnosticReportDetailResult, type ReportCasePreview, type ReportFaultSummary,
} from '../../api/diagnosticReport'
import { useDiagCaseDetail } from '../../composables/useDiagCaseDetail'
import { useOperator } from '../../composables/useOperator'
import { useReportWorkbench } from '../../composables/useReportWorkbench'
import { canVerifyFault, caseRefsForFault, documentClassificationText, documentProgress, formatReportTime, isFaultVerified, unmatchedCaseRefs, verificationInput, verifySelectedFaults, type VerificationOutcome } from '../../utils/caseWorkflow'

const { open, reportId, sourceFaultId, resume, closeReport, suspendReport } = useReportWorkbench()
const { openCase, caseVersion, bumpCaseVersion } = useDiagCaseDetail()
const { operator, setOperator } = useOperator()
const loading = ref(false)
const error = ref('')
const detail = ref<DiagnosticReportDetailResult | null>(null)
const observedResult = ref('')
const saving = ref(false)
const selected = ref<string[]>([])
const outcomes = ref<Record<string, VerificationOutcome>>({})
const previews = ref<Record<string, ReportCasePreview>>({})
const previewErrors = ref<Record<string, string>>({})
let loadVersion = 0
const report = computed(() => detail.value?.report ?? null)
const faults = computed(() => report.value?.fault_summaries ?? [])
const isVerified = (fault: ReportFaultSummary) => isFaultVerified(fault, report.value?.case_refs)
const selectable = (fault: ReportFaultSummary) => canVerifyFault(fault, report.value?.case_refs)
const selectableFaults = computed(() => faults.value.filter(selectable))
const allSelected = computed(() => selectableFaults.value.length > 0 &&
  selectableFaults.value.every((fault) => selected.value.includes(fault.fault_id!)))
const classification = (fault: ReportFaultSummary) => documentClassificationText({
  classifications: [{
    first_level_label: fault.classification?.first_level_label ?? null,
    second_level_label: fault.classification?.second_level_label ?? null,
    status: fault.classification?.status ?? 'unavailable',
  }],
})
const load = async () => {
  if (!reportId.value) return
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  try {
    const result = await fetchDiagnosticReport(reportId.value)
    if (version === loadVersion) {
      if (report.value?.current_sidecar_hash && report.value.current_sidecar_hash !== result.report.current_sidecar_hash) {
        previews.value = {}
        previewErrors.value = {}
        selected.value = []
        observedResult.value = ''
        error.value = '定界文档已更新，请重新核对结论并填写检验结果。'
      }
      detail.value = result
    }
  } catch (err) {
    if (version === loadVersion) {
      error.value = err instanceof Error ? err.message : '定界文档加载失败'
      detail.value = null
    }
  } finally {
    if (version === loadVersion) loading.value = false
  }
}
watch(() => [open.value, reportId.value], async () => {
  if (!open.value) { loadVersion += 1; return }
  if (resume.value && report.value?.report_id === reportId.value) {
    await load()
    return
  }
  selected.value = []
  outcomes.value = {}
  previews.value = {}
  previewErrors.value = {}
  observedResult.value = ''
  detail.value = null
  await load()
  if (sourceFaultId.value && faults.value.some((fault) => fault.fault_id === sourceFaultId.value && selectable(fault))) {
    selected.value = [sourceFaultId.value]
  }
}, { immediate: true })
watch(caseVersion, () => { if (open.value && !saving.value) void load() })
const toggleAll = () => {
  selected.value = allSelected.value ? [] : selectableFaults.value.map((fault) => fault.fault_id!)
}
const showPreview = async (fault: ReportFaultSummary, event: Event) => {
  if (!(event.target as HTMLDetailsElement).open || !fault.fault_id || previews.value[fault.fault_id]) return
  const id = fault.fault_id
  const currentReport = reportId.value
  try {
    const result = await previewReportCase(currentReport, id)
    if (currentReport === reportId.value) previews.value[id] = result
  } catch (err) {
    if (currentReport === reportId.value) previewErrors.value[id] = err instanceof Error ? err.message : '结论加载失败'
  }
}
const submit = async () => {
  error.value = ''
  try {
    const body = verificationInput(operator.value, observedResult.value, report.value?.current_sidecar_hash)
    const ids = selected.value.filter((id) => selectableFaults.value.some((fault) => fault.fault_id === id))
    if (!ids.length) throw new Error('请选择需要验证的结论')
    setOperator(operator.value.trim())
    saving.value = true
    await verifySelectedFaults(ids, (id) => verifyReportFault(reportId.value, id, body), (outcome) => {
      outcomes.value = { ...outcomes.value, [outcome.faultId]: outcome }
      if (outcome.caseId) selected.value = selected.value.filter((id) => id !== outcome.faultId)
    })
    await load()
    bumpCaseVersion()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '验证失败'
  } finally {
    saving.value = false
  }
}
const close = () => { if (!saving.value) closeReport() }
const showCase = (id: string) => {
  if (saving.value) return
  suspendReport()
  openCase(id, true)
}
const openHtml = () => {
  if (report.value) window.open(diagnosticReportHtmlUrl(report.value.report_id), '_blank', 'noopener')
}
</script>

<template>
  <BaseModal :open="open" size="doc" title="定界文档详情" keep-mounted :close-on-esc="!saving" :close-on-overlay="!saving" @close="close">
    <div v-if="loading && !report" class="empty">正在加载定界文档…</div>
    <div v-if="error" class="error-banner" role="alert">{{ error }} <button v-if="!report" class="btn btn-default" @click="load">重试</button></div>
    <div v-if="report" class="verification-workbench">
      <header class="workbench-summary">
        <div><h2>{{ report.title || '未命名定界文档' }}</h2><p>{{ report.kb_name || report.source_name || (report.imported ? '外部导入' : '诊断任务') }} · {{ formatReportTime(report.generated_at) }} · 已验证 {{ documentProgress(report) }}</p></div>
        <button class="btn btn-default" type="button" @click="openHtml">阅读定界文档</button>
      </header>
      <label v-if="selectableFaults.length" class="select-all"><input type="checkbox" :checked="allSelected" :disabled="saving" @change="toggleAll" />全选待验证结论</label>
      <p v-if="!faults.length" class="empty">文档暂无可验证结论，请阅读原文核对材料。</p>
      <article v-for="(fault, index) in faults" :key="fault.fault_id || `fault:${index}`" class="fault-card" :class="{ highlighted: fault.fault_id === sourceFaultId }">
        <div class="fault-heading">
          <label><input v-if="selectable(fault)" v-model="selected" type="checkbox" :value="fault.fault_id" :disabled="saving" /><strong>{{ fault.title || `结论 ${index + 1}` }}</strong></label>
          <span class="badge" :class="{ 'badge-success': isVerified(fault) }">{{ isVerified(fault) || outcomes[fault.fault_id || '']?.caseId ? '已验证' : fault.synthetic || fault.excluded || !fault.fault_id ? '仅供参考' : '待验证' }}</span>
        </div>
        <p class="classification">{{ classification(fault) }}</p>
        <div v-if="caseRefsForFault(report.case_refs ?? [], fault.fault_id).length" class="linked-cases">
          <span>关联案例</span>
          <button v-for="item in caseRefsForFault(report.case_refs ?? [], fault.fault_id)" :key="`${item.case_id}:${item.revision}`" class="case-link" type="button" :disabled="saving" @click="showCase(item.case_id)">
            {{ item.case_no || item.case_id }} <small>{{ !item.is_current_version ? '历史版本' : item.status === 'confirmed' && item.closed_loop ? '已验证' : item.status === 'draft' ? '草稿' : '历史记录' }}</small>
          </button>
        </div>
        <details v-if="fault.fault_id && !fault.synthetic && !isVerified(fault)" @toggle="showPreview(fault, $event)">
          <summary>查看结论与处置</summary>
          <p v-if="previewErrors[fault.fault_id]" class="error-banner">{{ previewErrors[fault.fault_id] }}</p>
          <template v-else-if="previews[fault.fault_id]">
            <p>{{ previews[fault.fault_id]?.draft.symptom_summary || '暂无现象摘要' }}</p>
            <p>{{ previews[fault.fault_id]?.draft.root_cause_summary || '暂无根因摘要' }}</p>
            <ol><li v-for="(step, stepIndex) in (previews[fault.fault_id]?.draft.remediation_json as Array<Record<string, unknown>> ?? [])" :key="stepIndex">{{ step.action }}</li></ol>
          </template>
          <p v-else>正在加载…</p>
        </details>
        <p v-if="outcomes[fault.fault_id || '']?.error" class="error-banner" role="alert">验证未完成：{{ outcomes[fault.fault_id || '']?.error }}</p>
        <p v-if="outcomes[fault.fault_id || '']?.caseId && !caseRefsForFault(report.case_refs ?? [], fault.fault_id).some((item) => item.case_id === outcomes[fault.fault_id || '']?.caseId)" class="verification-success" role="status">已形成有效案例 <button class="case-link" type="button" :disabled="saving" @click="showCase(outcomes[fault.fault_id || '']!.caseId!)">查看案例</button></p>
      </article>
      <section v-if="unmatchedCaseRefs(report.case_refs ?? [], faults).length" class="linked-cases">
        <span>未绑定结论的关联案例</span>
        <button v-for="item in unmatchedCaseRefs(report.case_refs ?? [], faults)" :key="`${item.case_id}:${item.revision}`" class="case-link" type="button" :disabled="saving" @click="showCase(item.case_id)">{{ item.case_no || item.case_id }}</button>
      </section>
      <form v-if="selectableFaults.length" class="verification-form" @submit.prevent="submit">
        <label>操作人<input :value="operator" class="input" autocomplete="name" :disabled="saving" @input="setOperator(($event.target as HTMLInputElement).value)" /></label>
        <label>定界结论检验结果<textarea v-model="observedResult" class="input" rows="4" :disabled="saving" placeholder="记录原始日志、证据与定界结论的核对结果；所选结论均适用时可批量提交。" /></label>
        <p v-if="!report.current_sidecar_hash" class="error-banner">文档版本暂不可校验，请重新加载后验证。</p>
        <div class="submit-row"><span>已选择 {{ selected.length }} 条结论</span><button class="btn btn-primary" type="submit" :disabled="saving || !selected.length || !report.current_sidecar_hash">{{ saving ? '正在逐条检验…' : '检验通过并形成有效案例' }}</button></div>
      </form>
      <p v-else-if="faults.length" class="workbench-note">当前可验证结论已处理，可继续阅读文档或查看关联案例。</p>
    </div>
  </BaseModal>
</template>

<style scoped>
.workbench-summary { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; margin-bottom: 20px; }
.workbench-summary h2 { margin: 0 0 8px; font-size: 20px; }
.workbench-summary p, .classification, .workbench-note { color: var(--text2); line-height: 1.7; }
.workbench-summary p { margin: 0; }
.select-all, .fault-heading label { display: flex; gap: 10px; align-items: center; }
.select-all { margin: 20px 0 14px; }
.fault-card { border: 1px solid var(--border); border-radius: 8px; padding: 18px; margin-bottom: 14px; }
.fault-card.highlighted { border-color: #93b4ee; }
.fault-heading { display: flex; justify-content: space-between; gap: 18px; }
.classification { margin: 8px 0; font-size: 12px; }
.linked-cases { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; color: var(--text2); font-size: 13px; }
.case-link { border: 1px solid #bfdbfe; border-radius: 6px; background: #eff6ff; color: #1d4ed8; padding: 6px 10px; font: inherit; cursor: pointer; }
.case-link:hover:not(:disabled) { background: #dbeafe; }
.case-link:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
.case-link:disabled { opacity: .55; cursor: not-allowed; }
.case-link small { color: var(--text2); margin-left: 4px; }
summary { cursor: pointer; color: var(--text2); }
.verification-form { display: grid; gap: 18px; border-top: 1px solid var(--border); margin-top: 24px; padding-top: 24px; }
.verification-form label { display: grid; gap: 8px; font-weight: 500; }
.verification-form input { max-width: 320px; }
.verification-form textarea { width: 100%; min-height: 110px; height: auto; box-sizing: border-box; font: inherit; resize: vertical; }
.submit-row { display: flex; justify-content: space-between; gap: 20px; align-items: center; }
.verification-success { color: #15803d; }
</style>
