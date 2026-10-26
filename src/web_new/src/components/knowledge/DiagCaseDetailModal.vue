<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BaseModal from '../common/BaseModal.vue'
import VerificationForm from '../report/VerificationForm.vue'
import {
  confirmDiagCase,
  fetchDiagCase,
  type DiagCase,
  type DiagCaseDetail,
} from '../../api/diagCaseLibrary'
import { useDiagCaseDetail } from '../../composables/useDiagCaseDetail'
import { useOperator } from '../../composables/useOperator'
import { useReportWorkbench } from '../../composables/useReportWorkbench'
import { useToast } from '../../composables/useToast'

const { open, caseId, closeCase, bumpCaseVersion } = useDiagCaseDetail()
const { openReport } = useReportWorkbench()
const { operator, setOperator, requireOperator } = useOperator()
const { toast } = useToast()

const loading = ref(false)
const error = ref('')
const detail = ref<DiagCaseDetail | null>(null)
const confirming = ref(false)

const caseData = computed<DiagCase | null>(() => detail.value?.case ?? null)
const source = computed(() => detail.value?.source_report ?? null)
const classificationText = computed(() => {
  const item = caseData.value
  if (!item?.first_level_label && !item?.second_level_label) {
    return item?.label_taxonomy_version ? '未分类' : '未分类 / 来源待核对'
  }
  return [item.first_level_label, item.second_level_label].filter(Boolean).join(' / ')
})
const sourceStatusText = computed(() => {
  const value = source.value?.status
  return (
    {
      valid: '源报告当前版本有效',
      stale: '源报告版本已变化',
      deleted: '源报告不可用',
      unavailable: '暂时无法校验源报告',
      independent: '无关联报告',
    }[value ?? ''] ?? '无关联报告'
  )
})
const verificationText = (item: DiagCase) => {
  if (item.status !== 'confirmed') return '未确认'
  return item.verification_json?.closed_loop ? '已验证' : '已确认未验证'
}
const canOpenSource = computed(
  () => source.value?.status === 'valid' && source.value.report_id,
)

const load = async () => {
  if (!caseId.value) return
  loading.value = true
  error.value = ''
  try {
    detail.value = await fetchDiagCase(caseId.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案例加载失败'
    detail.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => [open.value, caseId.value],
  () => {
    if (open.value) void load()
  },
  { immediate: true },
)

const confirmCase = async () => {
  const reviewer = requireOperator()
  if (!reviewer) {
    error.value = '请先填写操作人'
    return
  }
  confirming.value = true
  error.value = ''
  try {
    detail.value = await confirmDiagCase(caseId.value, reviewer)
    bumpCaseVersion()
    toast('案例已确认', 'success')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案例确认失败'
  } finally {
    confirming.value = false
  }
}

const onVerificationSaved = async () => {
  await load()
  bumpCaseVersion()
}

const openSourceReport = () => {
  if (!canOpenSource.value || !source.value?.report_id) return
  const reportId = source.value.report_id
  const faultId = source.value.source_fault_id ?? ''
  // 案例详情先关闭，报告工作台才能获得焦点与顶层交互。
  closeCase()
  openReport(reportId, faultId)
}
</script>

<template>
  <BaseModal :open="open" size="doc" title="诊断案例详情" @close="closeCase">
    <div v-if="loading" class="empty">
      <div class="icon">⏳</div>
      <div>正在加载案例...</div>
    </div>
    <div v-else-if="error" class="error-banner" role="alert">
      {{ error }}
      <button class="btn btn-sm btn-default" type="button" @click="load">重试</button>
    </div>
    <div v-else-if="caseData" class="case-detail">
      <header class="case-detail-header">
        <div>
          <div class="case-detail-title">{{ caseData.title || '未命名案例' }}</div>
          <div class="case-detail-meta">
            {{ caseData.case_no || caseData.id }} · {{ caseData.status }} ·
            {{ verificationText(caseData) }} · revision {{ caseData.revision }}
          </div>
        </div>
        <button
          v-if="caseData.status === 'draft'"
          class="btn btn-primary btn-sm"
          type="button"
          :disabled="confirming"
          @click="confirmCase"
        >
          {{ confirming ? '确认中...' : '确认案例' }}
        </button>
      </header>

      <div class="form-row">
        <div class="form-group" style="flex: 1">
          <label class="form-label">操作人</label>
          <input
            class="input"
            :value="operator"
            placeholder="确认/验证操作人"
            @input="setOperator(($event.target as HTMLInputElement).value)"
          />
        </div>
      </div>

      <section class="case-detail-section">
        <h4>分类与来源</h4>
        <div class="case-detail-grid">
          <div><span>两级分类</span>{{ classificationText }}</div>
          <div>
            <span>来源报告</span>
            <button
              v-if="canOpenSource"
              class="btn-text btn"
              type="button"
              @click="openSourceReport"
            >
              {{ source?.report_title || source?.report_id }}
            </button>
            <template v-else>{{ sourceStatusText }}</template>
          </div>
          <div><span>源故障</span>{{ source?.source_fault_title || source?.source_fault_id || '—' }}</div>
          <div><span>报告审核</span>{{ source?.review_status || '—' }}</div>
          <div><span>来源校验</span>{{ sourceStatusText }}</div>
          <div><span>分类校验</span>{{ source?.classification_status || 'unclassified' }}</div>
        </div>
      </section>

      <section class="case-detail-section">
        <h4>现象与根因</h4>
        <p class="prewrap">{{ caseData.symptom_summary || '—' }}</p>
        <p class="prewrap">{{ caseData.root_cause_summary || '—' }}</p>
        <p v-if="caseData.root_cause_detail" class="prewrap">{{ caseData.root_cause_detail }}</p>
      </section>

      <section class="case-detail-section">
        <h4>证据锚点（{{ caseData.evidence_json.length }}）</h4>
        <ul class="detail-list">
          <li v-for="(item, index) in caseData.evidence_json" :key="index">
            <code>{{ item.kind }}:{{ item.ref }}</code>
            <span v-if="item.note">{{ item.note }}</span>
          </li>
        </ul>
      </section>

      <section class="case-detail-section">
        <h4>处置步骤（{{ caseData.remediation_json.length }}）</h4>
        <ol class="detail-list">
          <li v-for="(item, index) in caseData.remediation_json" :key="index">
            {{ item.action }}
          </li>
        </ol>
      </section>

      <section v-if="caseData.status === 'confirmed'" class="case-detail-section">
        <h4>复测验证</h4>
        <VerificationForm
          :case-id="caseData.id"
          :revision="caseData.revision"
          :initial="caseData.verification_json"
          @saved="onVerificationSaved"
        />
        <div v-if="caseData.verification_history_json.length" class="verification-history">
          <div
            v-for="(entry, index) in caseData.verification_history_json"
            :key="index"
            class="verification-history-item"
          >
            r{{ entry.revision_from }} → r{{ entry.revision_to }} ·
            {{ entry.verified_by || '—' }} · {{ entry.verified_at || '—' }} ·
            {{ entry.closed_loop ? '闭环' : '未闭环' }}
          </div>
        </div>
      </section>
    </div>
  </BaseModal>
</template>
