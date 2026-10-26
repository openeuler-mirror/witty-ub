<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  confirmDiagCase,
  fetchDiagCase,
  updateDiagCaseVerification,
  type DiagCase,
  type DiagCaseDetail,
} from '../api/diagCase'

const props = defineProps<{ open: boolean; caseId: string }>()
const emit = defineEmits<{
  close: []
  changed: []
  'open-report': [reportId: string, faultId: string]
}>()

const loading = ref(false)
const error = ref('')
const detail = ref<DiagCaseDetail | null>(null)
const operator = ref(localStorage.getItem('witty-operator') ?? '')
const confirming = ref(false)
const savingVerification = ref(false)
const method = ref('')
const observedResult = ref('')
const closedLoop = ref(false)
const notes = ref('')

const caseData = computed<DiagCase | null>(() => detail.value?.case ?? null)
const source = computed(() => detail.value?.source_report ?? null)
const classificationText = computed(() => {
  const item = caseData.value
  if (!item) return '—'
  if (!item.first_level_label && !item.second_level_label) {
    return item.label_taxonomy_version ? '未分类' : '未分类 / 来源待核对'
  }
  return [item.first_level_label, item.second_level_label].filter(Boolean).join(' / ')
})
const sourceStatusText = computed(() => {
  const map: Record<string, string> = {
    valid: '源报告当前版本有效',
    stale: '源报告版本已变化',
    deleted: '源报告不可用',
    unavailable: '暂时无法校验源报告',
    independent: '无关联报告',
  }
  return map[source.value?.status ?? ''] ?? '无关联报告'
})
const verificationText = (item: DiagCase) => {
  if (item.status !== 'confirmed') return '未确认'
  return item.verification_json?.closed_loop ? '已验证' : '已确认未验证'
}

const saveOperator = () => {
  operator.value = operator.value.trim()
  if (operator.value) localStorage.setItem('witty-operator', operator.value)
  else localStorage.removeItem('witty-operator')
}

const load = async () => {
  if (!props.caseId) return
  loading.value = true
  error.value = ''
  try {
    detail.value = await fetchDiagCase(props.caseId)
    const verification = detail.value.case?.verification_json
    method.value = verification?.method ?? ''
    observedResult.value = verification?.observed_result ?? ''
    closedLoop.value = Boolean(verification?.closed_loop)
    notes.value = verification?.notes ?? ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案例加载失败'
    detail.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.open, props.caseId],
  () => {
    if (props.open) void load()
  },
  { immediate: true },
)

const confirmCase = async () => {
  saveOperator()
  if (!operator.value) {
    error.value = '请先填写操作人'
    return
  }
  confirming.value = true
  try {
    detail.value = await confirmDiagCase(props.caseId, operator.value)
    error.value = ''
    emit('changed')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案例确认失败'
  } finally {
    confirming.value = false
  }
}

const saveVerification = async () => {
  if (!caseData.value) return
  saveOperator()
  if (!operator.value) {
    error.value = '请先填写操作人'
    return
  }
  if (closedLoop.value && (!method.value.trim() || !observedResult.value.trim())) {
    error.value = '标记闭环时必须填写验证方法和实测结果'
    return
  }
  savingVerification.value = true
  try {
    detail.value = await updateDiagCaseVerification(
      caseData.value.id,
      {
        method: method.value.trim() || null,
        observed_result: observedResult.value.trim() || null,
        closed_loop: closedLoop.value,
        verified_by: operator.value,
        verified_at: new Date().toISOString(),
        notes: notes.value.trim() || null,
      },
      caseData.value.revision,
    )
    error.value = ''
    emit('changed')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '验证结果保存失败'
  } finally {
    savingVerification.value = false
  }
}

const openSource = () => {
  if (source.value?.status !== 'valid' || !source.value.report_id) return
  emit('open-report', source.value.report_id, source.value.source_fault_id ?? '')
}
</script>

<template>
  <div v-if="open" class="modal" @click.self="emit('close')">
    <section class="modal-content diag-detail-content">
      <header class="modal-header">
        <span>诊断案例详情</span>
        <button class="close-modal" type="button" aria-label="关闭" @click="emit('close')">✕</button>
      </header>
      <div class="modal-body">
        <div v-if="loading" class="state-text">正在加载案例...</div>
        <div v-else-if="error" class="dialog-error">
          {{ error }}
          <button class="ghost-btn" type="button" @click="load">重试</button>
        </div>
        <template v-else-if="caseData">
          <div class="diag-detail-header">
            <div>
              <div class="diag-detail-title">{{ caseData.title || '未命名案例' }}</div>
              <div class="diag-detail-meta">
                {{ caseData.case_no || caseData.id }} · {{ caseData.status }} ·
                {{ verificationText(caseData) }} · revision {{ caseData.revision }}
              </div>
            </div>
            <button
              v-if="caseData.status === 'draft'"
              class="primary-btn"
              type="button"
              :disabled="confirming"
              @click="confirmCase"
            >
              {{ confirming ? '确认中...' : '确认案例' }}
            </button>
          </div>

          <div class="diag-form-row">
            <label>操作人</label>
            <input class="diag-input" v-model="operator" @change="saveOperator" />
          </div>

          <section class="diag-section">
            <h4>分类与来源</h4>
            <div class="diag-grid">
              <div><span>两级分类</span>{{ classificationText }}</div>
              <div>
                <span>来源报告</span>
                <button
                  v-if="source?.status === 'valid' && source.report_id"
                  class="table-link-btn"
                  type="button"
                  @click="openSource"
                >
                  {{ source.report_title || source.report_id }}
                </button>
                <template v-else>{{ sourceStatusText }}</template>
              </div>
              <div><span>源故障</span>{{ source?.source_fault_title || source?.source_fault_id || '—' }}</div>
              <div><span>报告审核</span>{{ source?.review_status || '—' }}</div>
              <div><span>来源校验</span>{{ sourceStatusText }}</div>
              <div><span>分类校验</span>{{ source?.classification_status || 'unclassified' }}</div>
            </div>
          </section>

          <section class="diag-section">
            <h4>现象与根因</h4>
            <p class="diag-prewrap">{{ caseData.symptom_summary || '—' }}</p>
            <p class="diag-prewrap">{{ caseData.root_cause_summary || '—' }}</p>
            <p v-if="caseData.root_cause_detail" class="diag-prewrap">{{ caseData.root_cause_detail }}</p>
          </section>

          <section class="diag-section">
            <h4>证据锚点（{{ caseData.evidence_json?.length ?? 0 }}）</h4>
            <ul>
              <li v-for="(item, index) in caseData.evidence_json ?? []" :key="index">
                <code>{{ item.kind }}:{{ item.ref }}</code>
                <span v-if="item.note"> {{ item.note }}</span>
              </li>
            </ul>
          </section>

          <section class="diag-section">
            <h4>处置步骤（{{ caseData.remediation_json?.length ?? 0 }}）</h4>
            <ol>
              <li v-for="(item, index) in caseData.remediation_json ?? []" :key="index">
                {{ item.action }}
              </li>
            </ol>
          </section>

          <section v-if="caseData.status === 'confirmed'" class="diag-section">
            <h4>复测验证</h4>
            <div class="diag-form-grid">
              <label>验证方法<input class="diag-input" v-model="method" /></label>
              <label>备注<input class="diag-input" v-model="notes" /></label>
            </div>
            <label class="diag-block-label">实测结果</label>
            <textarea class="diag-textarea" rows="3" v-model="observedResult"></textarea>
            <label class="diag-check">
              <input type="checkbox" v-model="closedLoop" />
              复测已闭环
            </label>
            <div class="diag-actions">
              <button
                class="primary-btn"
                type="button"
                :disabled="savingVerification"
                @click="saveVerification"
              >
                {{ savingVerification ? '保存中...' : '保存验证结果' }}
              </button>
            </div>
            <div v-if="caseData.verification_history_json?.length" class="diag-history">
              <div v-for="(entry, index) in caseData.verification_history_json" :key="index">
                r{{ entry.revision_from }} → r{{ entry.revision_to }} ·
                {{ entry.verified_by || '—' }} · {{ entry.verified_at || '—' }} ·
                {{ entry.closed_loop ? '闭环' : '未闭环' }}
              </div>
            </div>
          </section>
        </template>
      </div>
    </section>
  </div>
</template>
