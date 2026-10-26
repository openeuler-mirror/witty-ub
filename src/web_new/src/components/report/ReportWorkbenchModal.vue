<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BaseModal from '../common/BaseModal.vue'
import VerificationForm from './VerificationForm.vue'
import {
  confirmDiagnosticReport,
  createCaseFromReport,
  diagnosticReportHtmlUrl,
  fetchDiagnosticReport,
  previewReportCase,
  type CreateCaseFromReportResult,
  type DiagnosticReportDetailResult,
  type ReportCasePreview,
  type ReportCaseRef,
  type ReportFaultSummary,
} from '../../api/diagnosticReport'
import type { DiagCaseVerification } from '../../api/diagCaseLibrary'
import { useDiagCaseDetail } from '../../composables/useDiagCaseDetail'
import { useOperator } from '../../composables/useOperator'
import { useReportWorkbench } from '../../composables/useReportWorkbench'
import { useToast } from '../../composables/useToast'

const { open, reportId, sourceFaultId, closeReport } = useReportWorkbench()
const { openCase, caseVersion } = useDiagCaseDetail()
const { operator, setOperator, requireOperator } = useOperator()
const { toast } = useToast()

const loading = ref(false)
const error = ref('')
const detail = ref<DiagnosticReportDetailResult | null>(null)
const confirming = ref(false)
const previewFaultId = ref('')
const preview = ref<ReportCasePreview | null>(null)
const previewLoading = ref(false)
const creating = ref(false)
const created = ref<CreateCaseFromReportResult | null>(null)
const verifyingCaseId = ref('')
const highlightFaultId = ref('')

const report = computed(() => detail.value?.report ?? null)
const faults = computed<ReportFaultSummary[]>(() => report.value?.fault_summaries ?? [])
const previewDraft = computed(
  () => (preview.value?.draft ?? {}) as Record<string, unknown>,
)
const previewTitle = computed(() => String(previewDraft.value.title ?? '—'))
const previewSymptom = computed(() => String(previewDraft.value.symptom_summary ?? '—'))
const previewRootCause = computed(() =>
  String(previewDraft.value.root_cause_summary ?? '—'),
)
const previewEvidenceCount = computed(() =>
  Array.isArray(previewDraft.value.evidence_json)
    ? previewDraft.value.evidence_json.length
    : 0,
)
const previewRemediationCount = computed(() =>
  Array.isArray(previewDraft.value.remediation_json)
    ? previewDraft.value.remediation_json.length
    : 0,
)
const verificationTarget = computed(() => {
  if (!verifyingCaseId.value || !report.value) return null
  return (
    report.value.case_refs.find((item) => item.case_id === verifyingCaseId.value) ?? null
  )
})

const REVIEW_META: Record<string, { label: string; cls: string }> = {
  unconfirmed: { label: '未确认', cls: 'badge-pending' },
  confirmed: { label: '已确认', cls: 'badge-success' },
  stale: { label: '确认已过期', cls: 'badge-warning' },
  unavailable: { label: '当前不可校验', cls: 'badge-failed' },
}
const REVIEW_DEFAULT = { label: '未确认', cls: 'badge-pending' }
const reviewMeta = (status: string) => REVIEW_META[status] ?? REVIEW_DEFAULT

const VERIFICATION_META: Record<string, string> = {
  verified: '已验证',
  confirmed_unverified: '已确认未验证',
  report_only: '仅报告',
  suspected: '待确认',
  legacy_unverified: '旧案例未验证',
}
const verificationLabel = (value: string) => VERIFICATION_META[value] ?? value

const classificationText = (fault: ReportFaultSummary) => {
  if (!fault.classification.first_level_label && !fault.classification.second_level_label) {
    return '未分类'
  }
  return [fault.classification.first_level_label, fault.classification.second_level_label]
    .filter(Boolean)
    .join(' / ')
}

const MISSING_LABELS: Record<string, string> = {
  symptom_summary: '缺少现象摘要',
  root_cause_summary: '缺少根因摘要',
  evidence_json: '缺少证据锚点',
  remediation_json: '缺少处置步骤',
  matchable_signal: '缺少可匹配信号',
  label_invalid: '故障分类不合法',
  label_taxonomy_unavailable: '分类字典不可用',
}
const missingLabel = (value: string) => MISSING_LABELS[value] ?? value

const refsFor = (faultId: string | null): ReportCaseRef[] =>
  report.value?.case_refs.filter((item) => item.source_fault_id === faultId) ?? []

const initialVerification = (refItem: ReportCaseRef): DiagCaseVerification => ({
  method: refItem.verification_method,
  observed_result: refItem.observed_result,
  closed_loop: refItem.closed_loop,
  verified_by: refItem.verified_by,
  verified_at: refItem.verified_at,
})

const load = async () => {
  if (!reportId.value) return
  loading.value = true
  error.value = ''
  try {
    detail.value = await fetchDiagnosticReport(reportId.value)
    highlightFaultId.value = sourceFaultId.value
  } catch (err) {
    error.value = err instanceof Error ? err.message : '报告加载失败'
    detail.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => [open.value, reportId.value],
  () => {
    if (!open.value) return
    created.value = null
    preview.value = null
    verifyingCaseId.value = ''
    void load()
  },
  { immediate: true },
)

// 案例确认、验证回填或详情关闭后，工作台里的关联案例状态同步刷新。
watch(caseVersion, () => {
  if (open.value) void load()
})

const confirmReport = async () => {
  const reviewer = requireOperator()
  if (!reviewer) {
    error.value = '请先填写操作人'
    return
  }
  if (!report.value?.current_sidecar_hash) return
  confirming.value = true
  error.value = ''
  try {
    await confirmDiagnosticReport(
      reportId.value,
      report.value.current_sidecar_hash,
      reviewer,
    )
    toast('报告已确认', 'success')
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '报告确认失败'
  } finally {
    confirming.value = false
  }
}

const startPreview = async (fault: ReportFaultSummary) => {
  if (!fault.fault_id) return
  previewLoading.value = true
  error.value = ''
  created.value = null
  try {
    preview.value = await previewReportCase(reportId.value, fault.fault_id)
    previewFaultId.value = fault.fault_id
  } catch (err) {
    error.value = err instanceof Error ? err.message : '建案预览失败'
  } finally {
    previewLoading.value = false
  }
}

const createDraft = async () => {
  if (!preview.value) return
  const reviewer = requireOperator()
  if (!reviewer) {
    error.value = '请先填写操作人'
    return
  }
  creating.value = true
  error.value = ''
  try {
    created.value = await createCaseFromReport(
      preview.value.report_id,
      preview.value.source_fault_id,
      preview.value.expected_sidecar_hash,
      reviewer,
    )
    preview.value = null
    toast('案例草稿已生成', 'success')
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案例草稿生成失败'
  } finally {
    creating.value = false
  }
}

const toggleVerification = (caseId: string) => {
  verifyingCaseId.value = verifyingCaseId.value === caseId ? '' : caseId
}

const openHtml = () => {
  if (report.value) window.open(diagnosticReportHtmlUrl(report.value.report_id), '_blank', 'noopener')
}
</script>

<template>
  <BaseModal :open="open" size="doc" title="报告工作台" @close="closeReport">
    <div v-if="loading" class="empty">
      <div class="icon">⏳</div>
      <div>正在加载报告...</div>
    </div>
    <div v-else-if="error" class="error-banner" role="alert">
      {{ error }}
      <button class="btn btn-sm btn-default" type="button" @click="load">重试</button>
    </div>
    <div v-else-if="report" class="report-workbench">
      <header class="report-workbench-header">
        <div>
          <div class="report-workbench-title">{{ report.title || report.file_name }}</div>
          <div class="report-workbench-meta">
            {{ report.kb_name || report.kb_id || '—' }} · {{ report.operation || '—' }} ·
            {{ report.generated_at || '—' }}
          </div>
        </div>
        <div class="report-workbench-actions">
          <span class="badge" :class="reviewMeta(report.review_status).cls">
            {{ reviewMeta(report.review_status).label }}
          </span>
          <button class="btn btn-sm btn-default" type="button" @click="openHtml">
            打开原报告
          </button>
        </div>
      </header>

      <div class="form-row">
        <div class="form-group" style="flex: 1">
          <label class="form-label">操作人</label>
          <input
            class="input"
            :value="operator"
            placeholder="报告确认/建案/验证操作人"
            @input="setOperator(($event.target as HTMLInputElement).value)"
          />
        </div>
        <div class="form-group" style="align-self: flex-end">
          <button
            class="btn btn-primary"
            type="button"
            :disabled="confirming || !report.current_sidecar_hash"
            @click="confirmReport"
          >
            {{ report.review_status === 'confirmed' ? '重新确认当前版本' : '确认整份报告' }}
          </button>
        </div>
      </div>

      <div v-if="report.review_status !== 'confirmed'" class="hint-block">
        报告需要人工确认后才能从故障生成案例；侧车内容变化会使确认自动过期。
      </div>
      <div v-if="created" class="success-block">
        已生成案例草稿 {{ created.case_no || created.case_id }}，请到「诊断案例」中审核确认。
        <span v-if="created.missing_fields.length">
          仍缺少：{{ created.missing_fields.map(missingLabel).join('、') }}
        </span>
      </div>

      <section class="report-fault-list">
        <article
          v-for="(fault, index) in faults"
          :key="index"
          class="report-fault-card"
          :class="{ 'is-highlighted': highlightFaultId && fault.fault_id === highlightFaultId }"
        >
          <header class="report-fault-header">
            <div>
              <span class="report-fault-id">{{ fault.fault_id || '合成键' }}</span>
              <span class="report-fault-title">{{ fault.title || '未命名故障' }}</span>
            </div>
            <div class="report-fault-badges">
              <span class="badge">{{ fault.status || 'suspected' }}</span>
              <span class="badge">{{ fault.category || 'unknown' }}</span>
              <span
                class="badge"
                :class="{
                  'badge-success': fault.classification.status === 'pair',
                  'badge-warning':
                    fault.classification.status === 'first_only' ||
                    fault.classification.status === 'empty',
                  'badge-failed':
                    fault.classification.status === 'invalid' ||
                    fault.classification.status === 'unavailable',
                }"
              >
                {{ classificationText(fault) }}
              </span>
            </div>
          </header>
          <div v-if="fault.classification.error" class="form-error">
            分类异常：{{ fault.classification.error }}
          </div>
          <div v-if="!fault.indexable" class="hint-block">
            {{ fault.excluded ? '该故障已被报告排除，不能建案' : '故障ID不稳定，需补齐稳定 ID 后重新渲染' }}
          </div>

          <div class="report-fault-cases">
            <div v-if="refsFor(fault.fault_id).length === 0" class="hint">暂无关联案例</div>
            <div
              v-for="item in refsFor(fault.fault_id)"
              :key="item.case_id"
              class="report-case-ref"
            >
              <button class="btn-text btn" type="button" @click="openCase(item.case_id)">
                {{ item.case_no || item.case_id }}
              </button>
              <span class="badge">{{ item.status }}</span>
              <span class="badge" :class="{ 'badge-success': item.verification === 'verified' }">
                {{ verificationLabel(item.verification) }}
              </span>
              <span v-if="!item.is_current_version" class="badge badge-warning">来源版本已变化</span>
              <span v-if="item.closed_loop" class="case-ref-verification">
                {{ item.verified_by || '—' }} · {{ item.verified_at || '—' }}
              </span>
              <button
                v-if="item.status === 'confirmed' && item.is_current_version"
                class="btn btn-sm btn-default"
                type="button"
                @click="toggleVerification(item.case_id)"
              >
                {{ verifyingCaseId === item.case_id ? '收起验证' : '回填验证' }}
              </button>
            </div>
            <VerificationForm
              v-if="verificationTarget && verificationTarget.source_fault_id === fault.fault_id"
              :case-id="verificationTarget.case_id"
              :revision="verificationTarget.revision"
              :initial="initialVerification(verificationTarget)"
              @saved="load"
            />
          </div>

          <div class="report-fault-actions">
            <button
              v-if="fault.indexable && fault.fault_id"
              class="btn btn-sm btn-primary"
              type="button"
              :disabled="report.review_status !== 'confirmed' || previewLoading"
              @click="startPreview(fault)"
            >
              生成案例草稿
            </button>
          </div>
        </article>
      </section>

      <section v-if="preview" class="report-case-preview">
        <h4>建案预览：{{ preview.source_fault_id }}</h4>
        <div class="case-detail-grid">
          <div><span>标题</span>{{ previewTitle }}</div>
          <div><span>现象</span>{{ previewSymptom }}</div>
          <div><span>根因</span>{{ previewRootCause }}</div>
          <div><span>分类</span>{{ preview.classification.first_level_label || '未分类' }} / {{ preview.classification.second_level_label || '—' }}</div>
          <div><span>证据</span>{{ previewEvidenceCount }} 条</div>
          <div><span>处置</span>{{ previewRemediationCount }} 步</div>
        </div>
        <div v-if="preview.missing_fields.length" class="form-error">
          确认前仍缺少：{{ preview.missing_fields.map(missingLabel).join('、') }}
        </div>
        <div class="report-fault-actions">
          <button class="btn btn-default" type="button" @click="preview = null">取消</button>
          <button class="btn btn-primary" type="button" :disabled="creating" @click="createDraft">
            {{ creating ? '生成中...' : '生成案例草稿' }}
          </button>
        </div>
      </section>
    </div>
  </BaseModal>
</template>
