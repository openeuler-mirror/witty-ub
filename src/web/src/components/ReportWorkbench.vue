<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  confirmReport,
  createReportCase,
  fetchReportDetail,
  previewReportCase,
  reportHtmlUrl,
  type ReportCasePreview,
  type ReportDetail,
  type ReportFaultSummary,
} from '../api/diagCase'

const props = defineProps<{
  open: boolean
  reportId: string
  faultId?: string
  refreshToken?: number
}>()
const emit = defineEmits<{
  close: []
  'open-case': [caseId: string]
}>()

const loading = ref(false)
const error = ref('')
const detail = ref<ReportDetail | null>(null)
const operator = ref(localStorage.getItem('witty-operator') ?? '')
const confirming = ref(false)
const preview = ref<ReportCasePreview | null>(null)
const previewLoading = ref(false)
const creating = ref(false)
const createdText = ref('')

const report = computed(() => detail.value?.report ?? null)
const faults = computed<ReportFaultSummary[]>(() => report.value?.fault_summaries ?? [])

const reviewLabels: Record<string, string> = {
  unconfirmed: '未确认',
  confirmed: '已确认',
  stale: '确认过期',
  unavailable: '不可校验',
}
const reviewLabel = computed(
  () => reviewLabels[report.value?.review_status ?? ''] ?? '未确认',
)
const verificationLabels: Record<string, string> = {
  verified: '已验证',
  confirmed_unverified: '已确认未验证',
  report_only: '仅报告',
  suspected: '待确认',
  legacy_unverified: '旧案例未验证',
}

const classificationText = (fault: ReportFaultSummary) => {
  if (!fault.classification?.first_level_label && !fault.classification?.second_level_label) {
    return '未分类'
  }
  return [fault.classification.first_level_label, fault.classification.second_level_label]
    .filter(Boolean)
    .join(' / ')
}
const refsFor = (faultId?: string | null) =>
  report.value?.case_refs?.filter((item) => item.source_fault_id === faultId) ?? []
const missingLabels: Record<string, string> = {
  symptom_summary: '缺少现象摘要',
  root_cause_summary: '缺少根因摘要',
  evidence_json: '缺少证据锚点',
  remediation_json: '缺少处置步骤',
  matchable_signal: '缺少可匹配信号',
  label_invalid: '分类不合法',
  label_taxonomy_unavailable: '分类字典不可用',
}
const missingText = computed(() =>
  (preview.value?.missing_fields ?? []).map((item) => missingLabels[item] ?? item).join('、'),
)
const draftTitle = computed(() => String(preview.value?.draft?.title ?? '—'))

const saveOperator = () => {
  operator.value = operator.value.trim()
  if (operator.value) localStorage.setItem('witty-operator', operator.value)
  else localStorage.removeItem('witty-operator')
}

const load = async () => {
  if (!props.reportId) return
  loading.value = true
  error.value = ''
  try {
    detail.value = await fetchReportDetail(props.reportId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '报告加载失败'
    detail.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.open, props.reportId],
  () => {
    if (!props.open) return
    preview.value = null
    createdText.value = ''
    void load()
  },
  { immediate: true },
)

// 案例确认、验证回填或详情关闭后，工作台里的关联案例状态同步刷新。
watch(
  () => props.refreshToken,
  () => {
    if (props.open) void load()
  },
)

const confirmReportReview = async () => {
  saveOperator()
  if (!operator.value) {
    error.value = '请先填写操作人'
    return
  }
  const hash = report.value?.current_sidecar_hash
  if (!hash) return
  confirming.value = true
  try {
    await confirmReport(props.reportId, hash, operator.value)
    await load()
    error.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '报告确认失败'
  } finally {
    confirming.value = false
  }
}

const startPreview = async (fault: ReportFaultSummary) => {
  if (!fault.fault_id) return
  previewLoading.value = true
  createdText.value = ''
  try {
    preview.value = await previewReportCase(props.reportId, fault.fault_id)
    error.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '建案预览失败'
  } finally {
    previewLoading.value = false
  }
}

const createDraft = async () => {
  if (!preview.value) return
  saveOperator()
  if (!operator.value) {
    error.value = '请先填写操作人'
    return
  }
  creating.value = true
  try {
    const result = await createReportCase(
      preview.value.report_id,
      preview.value.source_fault_id,
      preview.value.expected_sidecar_hash,
      operator.value,
    )
    createdText.value = `已生成案例草稿 ${result.case_no || result.case_id || ''}，请到「诊断案例」审核确认`
    preview.value = null
    await load()
    error.value = ''
  } catch (err) {
    error.value = err instanceof Error ? err.message : '案例草稿生成失败'
  } finally {
    creating.value = false
  }
}

const openHtml = () => {
  if (report.value) window.open(reportHtmlUrl(report.value.report_id), '_blank', 'noopener')
}
</script>

<template>
  <div v-if="open" class="modal" @click.self="emit('close')">
    <section class="modal-content diag-workbench-content">
      <header class="modal-header">
        <span>报告工作台</span>
        <button class="close-modal" type="button" aria-label="关闭" @click="emit('close')">✕</button>
      </header>
      <div class="modal-body">
        <div v-if="loading" class="state-text">正在加载报告...</div>
        <div v-else-if="error" class="dialog-error">
          {{ error }}
          <button class="ghost-btn" type="button" @click="load">重试</button>
        </div>
        <template v-else-if="report">
          <div class="diag-detail-header">
            <div>
              <div class="diag-detail-title">{{ report.title || '未命名报告' }}</div>
              <div class="diag-detail-meta">
                {{ report.kb_name || report.kb_id || '—' }} · {{ report.operation || '—' }} ·
                {{ report.generated_at || '—' }}
              </div>
            </div>
            <div class="diag-header-actions">
              <span class="status-badge" :class="`status-${report.review_status || 'pending'}`">
                {{ reviewLabel }}
              </span>
              <button class="ghost-btn" type="button" @click="openHtml">打开原报告</button>
            </div>
          </div>

          <div class="diag-form-row">
            <label>操作人</label>
            <input class="diag-input" v-model="operator" @change="saveOperator" />
            <button
              class="primary-btn"
              type="button"
              :disabled="confirming || !report.current_sidecar_hash"
              @click="confirmReportReview"
            >
              {{ report.review_status === 'confirmed' ? '重新确认' : '确认整份报告' }}
            </button>
          </div>
          <div v-if="report.review_status !== 'confirmed'" class="diag-hint">
            报告需人工确认后才能从故障生成案例；侧车变化会使确认自动过期。
          </div>
          <div v-if="createdText" class="diag-success">{{ createdText }}</div>

          <article
            v-for="(fault, index) in faults"
            :key="index"
            class="diag-fault-card"
            :class="{ 'is-highlighted': props.faultId && fault.fault_id === props.faultId }"
          >
            <header class="diag-fault-header">
              <div>
                <span class="diag-fault-id">{{ fault.fault_id || '合成键' }}</span>
                <strong>{{ fault.title || '未命名故障' }}</strong>
              </div>
              <div class="diag-badge-row">
                <span class="status-badge">{{ fault.status || 'suspected' }}</span>
                <span class="status-badge">{{ fault.category || 'unknown' }}</span>
                <span class="status-badge">{{ classificationText(fault) }}</span>
              </div>
            </header>
            <div v-if="fault.classification?.error" class="dialog-error">
              分类异常：{{ fault.classification.error }}
            </div>
            <div v-if="!fault.indexable" class="diag-hint">
              {{ fault.excluded ? '该故障已被报告排除' : '故障ID不稳定，不能建案' }}
            </div>
            <div class="diag-case-refs">
              <div v-if="refsFor(fault.fault_id).length === 0" class="diag-hint">暂无关联案例</div>
              <div v-for="item in refsFor(fault.fault_id)" :key="item.case_id" class="diag-case-ref">
                <button class="table-link-btn" type="button" @click="emit('open-case', item.case_id)">
                  {{ item.case_no || item.case_id }}
                </button>
                <span class="status-badge">{{ item.status }}</span>
                <span class="status-badge">{{ verificationLabels[item.verification] || item.verification }}</span>
                <span v-if="!item.is_current_version" class="status-badge status-running">来源版本已变化</span>
                <button
                  v-if="item.status === 'confirmed' && item.is_current_version"
                  class="ghost-btn"
                  type="button"
                  @click="emit('open-case', item.case_id)"
                >
                  回填验证
                </button>
              </div>
            </div>
            <div class="diag-actions">
              <button
                v-if="fault.indexable && fault.fault_id"
                class="primary-btn"
                type="button"
                :disabled="report.review_status !== 'confirmed' || previewLoading"
                @click="startPreview(fault)"
              >
                生成案例草稿
              </button>
            </div>
          </article>

          <section v-if="preview" class="diag-preview">
            <h4>建案预览：{{ preview.source_fault_id }}</h4>
            <div class="diag-grid">
              <div><span>标题</span>{{ draftTitle }}</div>
              <div><span>分类</span>{{ preview.classification.first_level_label || '未分类' }} / {{ preview.classification.second_level_label || '—' }}</div>
              <div><span>目标报告版本</span>{{ preview.expected_sidecar_hash.slice(0, 12) }}…</div>
            </div>
            <div v-if="preview.missing_fields.length" class="dialog-error">
              确认前仍缺少：{{ missingText }}
            </div>
            <div class="diag-actions">
              <button class="ghost-btn" type="button" @click="preview = null">取消</button>
              <button class="primary-btn" type="button" :disabled="creating" @click="createDraft">
                {{ creating ? '生成中...' : '生成案例草稿' }}
              </button>
            </div>
          </section>
        </template>
      </div>
    </section>
  </div>
</template>
