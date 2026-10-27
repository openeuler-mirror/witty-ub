<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BaseModal from '../common/BaseModal.vue'
import { fetchDiagCase, verifyDiagCase, type DiagCaseDetail } from '../../api/diagCaseLibrary'
import { useDiagCaseDetail } from '../../composables/useDiagCaseDetail'
import { useReportWorkbench } from '../../composables/useReportWorkbench'
import { useOperator } from '../../composables/useOperator'
import { belongsToScope, canOpenSource, caseOrigin, sourceReportLabel } from '../../utils/caseWorkflow'

const { open, caseId, closeCase, bumpCaseVersion } = useDiagCaseDetail()
const { openReport } = useReportWorkbench()
const { operator, setOperator } = useOperator()
const loading = ref(false)
const error = ref('')
const detail = ref<DiagCaseDetail | null>(null)
const observedResult = ref('')
const saving = ref(false)
const verificationError = ref('')
const savedMessage = ref('')
const caseData = computed(() => detail.value?.case ?? null)
const source = computed(() => detail.value?.source_report ?? null)
const verified = computed(() => caseData.value && belongsToScope(caseData.value, 'library'))
const canVerify = computed(() => Boolean(caseData.value && !caseData.value.report_id && !verified.value && caseData.value.status !== 'archived'))
const classification = computed(() => [caseData.value?.first_level_label, caseData.value?.second_level_label].filter(Boolean).join(' / ') || '未分类')
let loadVersion = 0
const load = async () => {
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  try {
    const result = await fetchDiagCase(caseId.value)
    if (version === loadVersion) {
      detail.value = result
      observedResult.value = result.case?.verification_json?.observed_result ?? ''
    }
  } catch (err) {
    if (version === loadVersion) error.value = err instanceof Error ? err.message : '案例加载失败'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}
watch(() => [open.value, caseId.value], () => {
  if (!open.value) { loadVersion += 1; return }
  observedResult.value = ''
  verificationError.value = ''
  savedMessage.value = ''
  detail.value = null
  void load()
}, { immediate: true })
const openSource = () => {
  if (saving.value || !canOpenSource(source.value) || !source.value?.report_id) return
  const reportId = source.value.report_id
  const faultId = source.value.source_fault_id ?? ''
  closeCase()
  openReport(reportId, faultId)
}
const close = () => { if (!saving.value) closeCase() }
const submitVerification = async () => {
  if (!canVerify.value || !caseData.value || saving.value) return
  verificationError.value = ''
  if (!operator.value.trim() || !observedResult.value.trim()) {
    verificationError.value = !operator.value.trim() ? '请填写操作人' : '请填写定界结论检验结果'
    return
  }
  saving.value = true
  try {
    const result = await verifyDiagCase(caseData.value.id, {
      expected_revision: caseData.value.revision,
      verified_by: operator.value.trim(),
      observed_result: observedResult.value.trim(),
      method: '定界文档人工检验',
    })
    if (!result.case) throw new Error('未返回已验证案例，请刷新后重试')
    setOperator(operator.value.trim())
    detail.value = result
    savedMessage.value = '检验通过，已形成有效案例'
    bumpCaseVersion()
  } catch (err) {
    verificationError.value = err instanceof Error ? err.message : '验证失败，请核对后重试'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <BaseModal :open="open" size="doc" title="案例详情" :close-on-esc="!saving" :close-on-overlay="!saving" @close="close">
    <div v-if="loading" class="empty">正在加载案例…</div>
    <div v-else-if="error" class="error-banner" role="alert">{{ error }} <button class="btn btn-default" @click="load">重试</button></div>
    <article v-else-if="caseData" class="case-reading">
      <p v-if="savedMessage" class="verification-success" role="status">{{ savedMessage }}</p>
      <header class="case-heading">
        <div><h2>{{ caseData.title || '未命名案例' }}</h2><p>{{ classification }} · {{ caseOrigin(caseData) }}</p></div>
        <span class="badge" :class="{ 'badge-success': verified }">{{ caseData.status === 'archived' ? '已归档' : verified ? '已验证' : '历史草稿' }}</span>
      </header>
      <section><h3>故障现象</h3><p>{{ caseData.symptom_summary || '暂无摘要' }}</p></section>
      <section><h3>根因结论</h3><p>{{ caseData.root_cause_summary || '暂无结论' }}</p><p v-if="caseData.root_cause_detail">{{ caseData.root_cause_detail }}</p></section>
      <section><h3>证据</h3><ul v-if="caseData.evidence_json?.length"><li v-for="(item, index) in caseData.evidence_json" :key="index"><span>{{ item.note || item.description || item.kind }}</span><code v-if="item.ref">{{ item.ref }}</code></li></ul><p v-else>暂无证据材料</p></section>
      <section><h3>处置步骤</h3><ol v-if="caseData.remediation_json?.length"><li v-for="(item, index) in caseData.remediation_json" :key="index">{{ item.action || item.description }}</li></ol><p v-else>暂无处置步骤</p></section>
      <section v-if="verified"><h3>定界结论检验结果</h3><p>{{ caseData.verification_json?.observed_result || '导入时已声明定界结论经过人工检验' }}</p><p class="case-meta">{{ caseData.verification_json?.verified_by || caseData.confirmed_by || '—' }} · {{ caseData.verification_json?.verified_at || caseData.confirmed_at || '—' }}</p></section>
      <section><h3>来源定界文档</h3><button v-if="canOpenSource(source)" class="btn btn-text" type="button" :disabled="saving" @click="openSource">{{ source?.report_title || '查看来源定界文档' }}</button><p v-else>{{ sourceReportLabel(source?.status) }}</p><p v-if="caseData.report_id && !verified">请在来源定界文档中检验结论，关联草稿不单独入库。</p></section>
      <form v-if="canVerify" class="case-verification-form" @submit.prevent="submitVerification">
        <h3>历史记录检验</h3>
        <label>操作人<input :value="operator" class="input" autocomplete="name" :disabled="saving" @input="setOperator(($event.target as HTMLInputElement).value)" /></label>
        <label>定界结论检验结果<textarea v-model="observedResult" class="input" rows="4" :disabled="saving" placeholder="记录原始日志、证据与定界结论的核对结果。" /></label>
        <p v-if="verificationError" class="error-banner" role="alert">{{ verificationError }}</p>
        <button class="btn btn-primary" type="submit" :disabled="saving">{{ saving ? '正在验证…' : '验证通过并入库' }}</button>
      </form>
    </article>
    <p v-else class="empty">案例不存在或已不可用</p>
  </BaseModal>
</template>

<style scoped>
.case-reading { display: grid; gap: 24px; }
.case-heading { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
.case-heading h2 { margin: 0 0 8px; font-size: 22px; }
.case-heading p, .case-meta { color: var(--text2); font-size: 13px; }
.case-reading h3 { font-size: 15px; margin: 0 0 12px; }
.case-reading p, .case-reading li { line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
.case-reading p { margin: 6px 0; }
.case-reading code { display: block; white-space: pre-wrap; color: var(--text2); font-size: 12px; }
.case-reading ul, .case-reading ol { padding-left: 22px; margin: 0; }
.case-verification-form { display: grid; gap: 16px; border-top: 1px solid var(--border); padding-top: 24px; }
.case-verification-form label { display: grid; gap: 8px; }
.case-verification-form input { max-width: 320px; }
.case-verification-form textarea { width: 100%; min-height: 110px; height: auto; font: inherit; resize: vertical; }
.case-verification-form button { justify-self: start; }
.verification-success { color: #15803d; }
</style>
