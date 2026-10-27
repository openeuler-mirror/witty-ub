<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import {
  fetchReportDetail, previewReportCase, reportHtmlUrl, verifyReportFault,
  type ReportCasePreview, type ReportDetail, type ReportFaultSummary,
} from '../api/diagCase'
import { canVerifyFault, documentClassificationText, documentProgress, formatReportTime, isFaultVerified, verificationInput, verifySelectedFaults, type VerificationOutcome } from '../utils/caseWorkflow'

const props = defineProps<{ open: boolean; reportId: string; faultId?: string; refreshToken?: number }>()
const emit = defineEmits<{ close: []; changed: []; 'open-case': [caseId: string] }>()
const loading = ref(false)
const error = ref('')
const detail = ref<ReportDetail | null>(null)
const operator = ref(localStorage.getItem('witty-operator') ?? '')
const observedResult = ref('')
const saving = ref(false)
const selected = ref<string[]>([])
const outcomes = ref<Record<string, VerificationOutcome>>({})
const previews = ref<Record<string, ReportCasePreview>>({})
const previewErrors = ref<Record<string, string>>({})
const panel = ref<HTMLElement | null>(null)
let previousFocus: HTMLElement | null = null
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
const saveOperator = () => {
  operator.value = operator.value.trim()
  localStorage.setItem('witty-operator', operator.value)
}
const load = async () => {
  if (!props.reportId) return
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  try {
    const result = await fetchReportDetail(props.reportId)
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
watch(() => [props.open, props.reportId], async () => {
  if (!props.open) {
    loadVersion += 1
    previousFocus?.focus()
    return
  }
  previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
  operator.value = localStorage.getItem('witty-operator') ?? ''
  selected.value = []
  outcomes.value = {}
  previews.value = {}
  previewErrors.value = {}
  observedResult.value = ''
  detail.value = null
  await nextTick()
  panel.value?.focus()
  await load()
  if (props.faultId && faults.value.some((fault) => fault.fault_id === props.faultId && selectable(fault))) {
    selected.value = [props.faultId]
  }
}, { immediate: true })
watch(() => props.refreshToken, () => { if (props.open && !saving.value) void load() })

const toggleAll = () => {
  selected.value = allSelected.value ? [] : selectableFaults.value.map((fault) => fault.fault_id!)
}
const showPreview = async (fault: ReportFaultSummary, event: Event) => {
  if (!(event.target as HTMLDetailsElement).open || !fault.fault_id || previews.value[fault.fault_id]) return
  const id = fault.fault_id
  const currentReport = props.reportId
  try {
    const result = await previewReportCase(currentReport, id)
    if (currentReport === props.reportId) previews.value[id] = result
  } catch (err) {
    if (currentReport === props.reportId) previewErrors.value[id] = err instanceof Error ? err.message : '结论加载失败'
  }
}
const submit = async () => {
  error.value = ''
  try {
    const body = verificationInput(operator.value, observedResult.value, report.value?.current_sidecar_hash)
    const ids = selected.value.filter((id) => selectableFaults.value.some((fault) => fault.fault_id === id))
    if (!ids.length) throw new Error('请选择需要验证的结论')
    saveOperator()
    saving.value = true
    await verifySelectedFaults(ids, (id) => verifyReportFault(props.reportId, id, body), (outcome) => {
      outcomes.value = { ...outcomes.value, [outcome.faultId]: outcome }
      if (outcome.caseId) selected.value = selected.value.filter((id) => id !== outcome.faultId)
    })
    await load()
    emit('changed')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '验证失败'
  } finally {
    saving.value = false
  }
}
const close = () => { if (!saving.value) emit('close') }
const openCase = (id: string) => { close(); emit('open-case', id) }
const openHtml = () => {
  if (report.value) window.open(reportHtmlUrl(report.value.report_id), '_blank', 'noopener')
}
const trapFocus = (event: KeyboardEvent) => {
  if (event.key !== 'Tab') return
  const items = Array.from(panel.value?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), textarea:not([disabled]), summary, a[href]') ?? [])
    .filter((item) => item.offsetParent !== null)
  const first = items[0]
  const last = items[items.length - 1]
  if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.value)) {
    event.preventDefault(); last?.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault(); first?.focus()
  }
}
</script>

<template>
  <div v-if="open" class="modal" @click.self="close">
    <section ref="panel" class="modal-content diag-workbench-content verification-workbench" role="dialog" aria-modal="true" aria-labelledby="verification-workbench-title" tabindex="-1" @keydown.esc.stop="close" @keydown="trapFocus">
      <header class="modal-header">
        <span id="verification-workbench-title">验证定界结论</span>
        <button class="close-modal" type="button" aria-label="关闭" :disabled="saving" @click="close">✕</button>
      </header>
      <div class="modal-body">
        <div v-if="loading && !report" class="state-text">正在加载定界文档…</div>
        <div v-if="error" class="dialog-error" role="alert">{{ error }} <button v-if="!report" class="ghost-btn" @click="load">重试</button></div>
        <template v-if="report">
          <header class="workbench-summary">
            <div><h2>{{ report.title || '未命名定界文档' }}</h2><p>{{ report.kb_name || report.source_name || (report.imported ? '外部导入' : '诊断任务') }} · {{ formatReportTime(report.generated_at) }} · 已验证 {{ documentProgress(report) }}</p></div>
            <button class="ghost-btn" type="button" @click="openHtml">阅读定界文档</button>
          </header>
          <section v-if="report.case_refs?.length" class="workbench-note" aria-label="关联案例">
            <h3>关联案例</h3>
            <ul><li v-for="item in report.case_refs" :key="`${item.case_id}:${item.revision}`"><button class="table-link-btn" type="button" :disabled="saving" @click="openCase(item.case_id)">{{ item.case_no || item.case_id }}</button> · {{ item.source_fault_id || '未绑定结论' }} · {{ !item.is_current_version ? '历史版本' : item.status === 'confirmed' && item.closed_loop ? '有效案例' : item.status === 'draft' ? '关联草稿' : '历史记录' }}</li></ul>
          </section>
          <label v-if="selectableFaults.length" class="select-all"><input type="checkbox" :checked="allSelected" :disabled="saving" @change="toggleAll" />全选待验证结论</label>
          <p v-if="!faults.length" class="state-text">文档暂无可验证结论，请阅读原文核对材料。</p>
          <article v-for="(fault, index) in faults" :key="fault.fault_id || `fault:${index}`" class="fault-card" :class="{ highlighted: fault.fault_id === faultId }">
            <div class="fault-heading">
              <label><input v-if="selectable(fault)" v-model="selected" type="checkbox" :value="fault.fault_id" :disabled="saving" /><strong>{{ fault.title || `结论 ${index + 1}` }}</strong></label>
              <span class="status-badge">{{ isVerified(fault) || outcomes[fault.fault_id || '']?.caseId ? '已验证' : fault.synthetic || fault.excluded || !fault.fault_id ? '仅供参考' : '待验证' }}</span>
            </div>
            <p class="classification">{{ classification(fault) }}</p>
            <details v-if="fault.fault_id && !fault.synthetic" @toggle="showPreview(fault, $event)">
              <summary>查看结论与处置</summary>
              <p v-if="previewErrors[fault.fault_id]" class="dialog-error">{{ previewErrors[fault.fault_id] }}</p>
              <template v-else-if="previews[fault.fault_id]">
                <p>{{ previews[fault.fault_id]?.draft.symptom_summary || '暂无现象摘要' }}</p>
                <p>{{ previews[fault.fault_id]?.draft.root_cause_summary || '暂无根因摘要' }}</p>
                <ol><li v-for="(step, stepIndex) in (previews[fault.fault_id]?.draft.remediation_json as Array<Record<string, unknown>> ?? [])" :key="stepIndex">{{ step.action }}</li></ol>
              </template>
              <p v-else>正在加载…</p>
            </details>
            <p v-if="outcomes[fault.fault_id || '']?.error" class="dialog-error" role="alert">验证未完成：{{ outcomes[fault.fault_id || '']?.error }}</p>
            <p v-if="outcomes[fault.fault_id || '']?.caseId" class="verification-success" role="status">已形成有效案例 <button class="table-link-btn" :disabled="saving" @click="openCase(outcomes[fault.fault_id || '']!.caseId!)">查看案例</button></p>
          </article>
          <form v-if="selectableFaults.length" class="verification-form" @submit.prevent="submit">
            <label>操作人<input v-model="operator" class="diag-input" autocomplete="name" :disabled="saving" @change="saveOperator" /></label>
            <label>定界结论检验结果<textarea v-model="observedResult" rows="4" :disabled="saving" placeholder="记录原始日志、证据与定界结论的核对结果；所选结论均适用时可批量提交。" /></label>
            <p v-if="!report.current_sidecar_hash" class="dialog-error">文档版本暂不可校验，请重新加载后验证。</p>
            <div class="submit-row"><span>已选择 {{ selected.length }} 条结论</span><button class="primary-btn" type="submit" :disabled="saving || !selected.length || !report.current_sidecar_hash">{{ saving ? '正在逐条检验…' : '检验通过并形成有效案例' }}</button></div>
          </form>
          <p v-else-if="faults.length" class="workbench-note">当前可验证结论已处理，可继续阅读文档或查看关联案例。</p>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.verification-workbench { width: min(940px, 94vw); }
.workbench-summary { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; margin-bottom: 20px; }
.workbench-summary h2 { margin: 0 0 8px; font-size: 20px; }
.workbench-summary p, .classification, .workbench-note { color: #64748b; line-height: 1.7; }
.workbench-summary p { margin: 0; }
.select-all, .fault-heading label { display: flex; gap: 10px; align-items: center; }
.select-all { margin: 20px 0 14px; }
.fault-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 14px; }
.fault-card.highlighted { border-color: #93b4ee; }
.fault-heading { display: flex; justify-content: space-between; gap: 18px; }
.classification { margin: 8px 0; font-size: 12px; }
summary { cursor: pointer; color: #475569; }
.verification-form { display: grid; gap: 18px; border-top: 1px solid #e2e8f0; margin-top: 24px; padding-top: 24px; }
.verification-form label { display: grid; gap: 8px; font-weight: 500; }
.verification-form input { max-width: 320px; }
.verification-form textarea { width: 100%; padding: 12px; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 6px; font: inherit; resize: vertical; }
.submit-row { display: flex; justify-content: space-between; gap: 20px; align-items: center; }
.verification-success { color: #15803d; }
</style>
