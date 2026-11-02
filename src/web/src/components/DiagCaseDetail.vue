<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { fetchDiagCase, verifyDiagCase, type DiagCaseDetail } from '../api/diagCase'
import { belongsToScope, canOpenSource, caseOrigin, sourceReportLabel } from '../utils/caseWorkflow'

const props = defineProps<{ open: boolean; caseId: string; returnToReport?: boolean }>()
const emit = defineEmits<{ close: []; changed: []; 'open-report': [reportId: string, faultId: string] }>()
const loading = ref(false)
const error = ref('')
const detail = ref<DiagCaseDetail | null>(null)
const panel = ref<HTMLElement | null>(null)
const operator = ref(localStorage.getItem('witty-operator') ?? '')
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
let previousFocus: HTMLElement | null = null
const load = async () => {
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  try {
    const result = await fetchDiagCase(props.caseId)
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
watch(() => [props.open, props.caseId], async () => {
  if (!props.open) { loadVersion += 1; previousFocus?.focus(); return }
  previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
  operator.value = localStorage.getItem('witty-operator') ?? ''
  observedResult.value = ''
  verificationError.value = ''
  savedMessage.value = ''
  detail.value = null
  await nextTick()
  panel.value?.focus()
  await load()
}, { immediate: true })
const openSource = () => {
  if (saving.value || !canOpenSource(source.value) || !source.value?.report_id) return
  emit('open-report', source.value.report_id, source.value.source_fault_id ?? '')
}
const close = () => { if (!saving.value) emit('close') }
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
    localStorage.setItem('witty-operator', operator.value.trim())
    detail.value = result
    savedMessage.value = '检验通过，已形成有效案例'
    emit('changed')
  } catch (err) {
    verificationError.value = err instanceof Error ? err.message : '验证失败，请核对后重试'
  } finally {
    saving.value = false
  }
}
const trapFocus = (event: KeyboardEvent) => {
  if (event.key !== 'Tab') return
  const items = Array.from(panel.value?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), textarea:not([disabled]), a[href]') ?? [])
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
    <section ref="panel" class="modal-content diag-detail-content" role="dialog" aria-modal="true" aria-labelledby="case-detail-title" :aria-busy="saving" tabindex="-1" @keydown.esc.stop="close" @keydown="trapFocus">
      <header class="modal-header"><span id="case-detail-title">案例详情</span><button class="close-modal" type="button" aria-label="关闭" :disabled="saving" @click="close">✕</button></header>
      <div class="modal-body">
        <div v-if="loading" class="state-text">正在加载案例…</div>
        <div v-else-if="error" class="dialog-error" role="alert">{{ error }} <button class="ghost-btn" @click="load">重试</button></div>
        <article v-else-if="caseData" class="case-reading">
          <p v-if="savedMessage" class="verification-success" role="status">{{ savedMessage }}</p>
          <header class="case-heading">
            <div><h2>{{ caseData.title || '未命名案例' }}</h2><p>案例 ID：{{ caseData.case_no || caseData.id }}</p><p>{{ classification }} · {{ caseOrigin(caseData) }}</p></div>
            <span class="status-badge" :class="caseData.status === 'archived' ? 'status-cancelled' : verified ? 'status-successful' : 'status-pending'">{{ caseData.status === 'archived' ? '已归档' : verified ? '已验证' : '历史草稿' }}</span>
          </header>
          <section><h3>故障现象</h3><p>{{ caseData.symptom_summary || '暂无摘要' }}</p></section>
          <section><h3>根因结论</h3><p>{{ caseData.root_cause_summary || '暂无结论' }}</p><p v-if="caseData.root_cause_detail">{{ caseData.root_cause_detail }}</p></section>
          <section><h3>证据</h3><ul v-if="caseData.evidence_json?.length"><li v-for="(item, index) in caseData.evidence_json" :key="index"><span>{{ item.note || item.description || item.kind }}</span><code v-if="item.ref">{{ item.ref }}</code></li></ul><p v-else>暂无证据材料</p></section>
          <section><h3>处置步骤</h3><ol v-if="caseData.remediation_json?.length"><li v-for="(item, index) in caseData.remediation_json" :key="index">{{ item.action || item.description }}</li></ol><p v-else>暂无处置步骤</p></section>
          <section v-if="verified"><h3>定界结论检验结果</h3><p>{{ caseData.verification_json?.observed_result || '导入时已声明定界结论经过人工检验' }}</p><p class="case-meta">{{ caseData.verification_json?.verified_by || caseData.confirmed_by || '—' }} · {{ caseData.verification_json?.verified_at || caseData.confirmed_at || '—' }}</p></section>
          <section><h3>来源定界文档</h3><button v-if="returnToReport" class="source-btn" type="button" :disabled="saving" @click="close">返回定界文档</button><button v-else-if="canOpenSource(source)" class="source-btn" type="button" :disabled="saving" @click="openSource">{{ source?.report_title || '查看来源定界文档' }} →</button><p v-else>{{ sourceReportLabel(source?.status) }}</p><p v-if="caseData.report_id && !verified">请在来源定界文档中检验结论，关联草稿不单独入库。</p></section>
          <form v-if="canVerify" class="case-verification-form" @submit.prevent="submitVerification">
            <h3>历史记录检验</h3>
            <label>操作人<input v-model="operator" class="diag-input" autocomplete="name" :disabled="saving" /></label>
            <label>定界结论检验结果<textarea v-model="observedResult" rows="4" :disabled="saving" placeholder="记录原始日志、证据与定界结论的核对结果。" /></label>
            <p v-if="verificationError" class="dialog-error" role="alert">{{ verificationError }}</p>
            <button class="primary-btn" type="submit" :disabled="saving">{{ saving ? '正在验证…' : '验证通过并入库' }}</button>
          </form>
        </article>
        <p v-else class="state-text">案例不存在或已不可用</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.case-reading { display: grid; gap: 24px; }
.case-heading { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
.case-heading h2 { margin: 0 0 8px; font-size: 22px; }
.case-heading p, .case-meta { color: #64748b; font-size: 13px; }
.case-reading h3 { font-size: 15px; margin: 0 0 12px; }
.case-reading p, .case-reading li { line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
.case-reading p { margin: 6px 0; }
.case-reading code { display: block; white-space: pre-wrap; color: #64748b; font-size: 12px; }
.case-reading ul, .case-reading ol { padding-left: 22px; margin: 0; }
.case-verification-form { display: grid; gap: 16px; border-top: 1px solid #e2e8f0; padding-top: 24px; }
.case-verification-form label { display: grid; gap: 8px; }
.case-verification-form input { max-width: 320px; }
.case-verification-form textarea { width: 100%; padding: 12px; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 6px; font: inherit; resize: vertical; }
.case-verification-form button { justify-self: start; }
.source-btn { border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; color: #1d4ed8; padding: 8px 12px; font: inherit; text-align: left; cursor: pointer; }
.source-btn:hover:not(:disabled) { border-color: #93c5fd; background: #eff6ff; }
.source-btn:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
.source-btn:disabled { opacity: .55; cursor: not-allowed; }
.verification-success { color: #15803d; }
</style>
