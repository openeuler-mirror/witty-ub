<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import BaseModal from './BaseModal.vue'
import type { LogKnowledge } from '../../types'
import { useServiceHealth } from '../../composables/useServiceHealth'
import {
  defaultDiagnosisConfig,
  fetchDiagnosisConfig,
  listImportAssets,
  resetDiagnosisConfig,
  saveDiagnosisConfig,
} from '../../api/diagnosisConfig'
import {
  EDITABLE_THRESHOLD_OPTIONS,
  PATTERN_TYPES,
  isValidThresholdValue,
  withSanitizedHiddenParams,
  type DiagnosisConfigForm,
  type DiagnosisPatternKey,
} from '../../utils/parseConfigFields'

const props = defineProps<{
  asset: LogKnowledge | null
  assetType: 'kvcache' | 'brpc'
  open: boolean
}>()
const emit = defineEmits<{ (e: 'update:open', value: boolean): void }>()

// 磁盘降级（只读）时后端不再接受写入：配置仍可查看/导入对比，但不能保存
const { writeRestricted, writeRestrictedMessage } = useServiceHealth()

const parseConfigSummary =
  '各资产库配置相互独立，仅对后续添加的日志解析任务生效，未进行配置时使用默认配置'

const draft = reactive<DiagnosisConfigForm>(defaultDiagnosisConfig())
const patternInputs = reactive<Record<DiagnosisPatternKey, string>>({
  ds_client_access_log_file: '',
  ds_client_info_log_file: '',
  ds_worker_access_log_file: '',
  ds_worker_info_log_file: '',
  resource_log_file: '',
})
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const validationError = ref('')
const invalidFields = ref(new Set<string>())
const resetSnapshot = ref('')
const importAssets = ref<LogKnowledge[]>([])
const importAssetId = ref('')
const importing = ref(false)
const importMessage = ref('')

const close = () => emit('update:open', false)

const fillDraft = (config: DiagnosisConfigForm) => {
  Object.assign(draft, JSON.parse(JSON.stringify(config)))
}

const initDrawer = async () => {
  error.value = ''
  validationError.value = ''
  invalidFields.value = new Set()
  resetSnapshot.value = ''
  importAssetId.value = ''
  importMessage.value = ''
  importAssets.value = []
  fillDraft(defaultDiagnosisConfig())
  if (!props.asset || props.assetType === 'brpc') return
  loading.value = true
  try {
    fillDraft(await fetchDiagnosisConfig(props.asset.id))
    importAssets.value = await listImportAssets(props.asset.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '读取日志解析配置失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) void initDrawer()
  },
)

const addPattern = (key: DiagnosisPatternKey) => {
  const pattern = patternInputs[key].trim()
  if (!pattern || draft.logFilenamePattern[key].includes(pattern)) return
  draft.logFilenamePattern[key].push(pattern)
  patternInputs[key] = ''
}

const removePattern = (key: DiagnosisPatternKey, index: number) => {
  draft.logFilenamePattern[key].splice(index, 1)
}

const validate = () => {
  const invalid = new Set<string>()
  // 上限与后端 schema 一致，避免保存后请求被 422 拒绝
  EDITABLE_THRESHOLD_OPTIONS.forEach(({ key }) => {
    if (!isValidThresholdValue(draft.logAnalyzerParams[key])) invalid.add(key)
  })
  invalidFields.value = invalid
  if (invalid.size > 0) {
    validationError.value = '参数填写不合法，请检查红色输入框'
    return false
  }
  const emptyPattern = PATTERN_TYPES.find(({ key }) => draft.logFilenamePattern[key].length === 0)
  if (emptyPattern) {
    error.value = `${emptyPattern.label}至少需要一个 Pattern`
    return false
  }
  validationError.value = ''
  return true
}

const resetDraft = () => {
  fillDraft(defaultDiagnosisConfig())
  // 草稿与默认值一致时保存走可信 reset 接口
  resetSnapshot.value = JSON.stringify(draft)
  validationError.value = ''
  invalidFields.value = new Set()
  error.value = ''
}

const importFromAsset = async () => {
  if (!importAssetId.value || importing.value) return
  importing.value = true
  error.value = ''
  importMessage.value = ''
  try {
    const source = importAssets.value.find(({ id }) => id === importAssetId.value)
    fillDraft(await fetchDiagnosisConfig(importAssetId.value))
    validationError.value = ''
    invalidFields.value = new Set()
    resetSnapshot.value = ''
    importMessage.value = `已导入“${source?.name || '所选资产库'}”的配置，保存后生效`
  } catch (err) {
    error.value = err instanceof Error ? err.message : '导入其他资产库配置失败'
  } finally {
    importing.value = false
  }
}

const save = async () => {
  if (!props.asset || saving.value) return
  if (writeRestricted.value) {
    error.value = writeRestrictedMessage.value
    return
  }
  error.value = ''
  if (!validate()) return
  saving.value = true
  try {
    // 重置后草稿与默认一致：走可信 reset 接口恢复
    const saved =
      resetSnapshot.value !== '' && resetSnapshot.value === JSON.stringify(draft)
        ? await resetDiagnosisConfig(props.asset.id)
        : // 隐藏字段（后端尚未消费）原样透传，非法值回落到默认，避免看不见的字段把保存卡成 422
          await saveDiagnosisConfig(
            props.asset.id,
            withSanitizedHiddenParams(draft, defaultDiagnosisConfig()),
          )
    fillDraft(saved)
    close()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '保存日志解析配置失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <BaseModal
    :open="open"
    size="drawer"
    :label="`日志解析配置 · ${asset?.name || '-'}`"
    @close="close"
  >
    <template #header>
      <div class="agent-header">
        日志解析配置 · {{ asset?.name || '-' }}
        <button class="close" aria-label="关闭" @click="close">✕</button>
      </div>
    </template>
    <div v-if="assetType === 'brpc'" class="empty" style="padding: 48px 0">
      <div class="icon">🔒</div>
      <div>UBSocket 日志解析暂不支持配置</div>
    </div>
    <template v-else>
      <div v-if="error" class="error-banner">{{ error }}</div>
      <div v-if="validationError" class="error-banner">{{ validationError }}</div>
      <div v-if="writeRestricted" class="error-banner">
        {{ writeRestrictedMessage }}；配置暂不可修改。
      </div>
      <div v-if="loading" class="empty" style="padding: 48px 0">
        <div class="icon">⏳</div>
        <div>正在加载配置...</div>
      </div>
      <template v-else>
        <p class="parse-summary">{{ parseConfigSummary }}</p>

        <section class="parse-section">
          <h3>从其他资产库导入</h3>
          <div class="import-row">
            <select class="select" v-model="importAssetId" style="flex: 1">
              <option value="">选择资产库...</option>
              <option v-for="item in importAssets" :key="item.id" :value="item.id">
                {{ item.name }}
              </option>
            </select>
            <button
              class="btn btn-default btn-sm"
              :disabled="!importAssetId || importing"
              @click="importFromAsset"
            >
              {{ importing ? '导入中...' : '导入' }}
            </button>
          </div>
          <div v-if="importMessage" class="import-message">{{ importMessage }}</div>
        </section>

        <section class="parse-section">
          <h3>日志文件名 Pattern</h3>
          <div v-for="type in PATTERN_TYPES" :key="type.key" class="pattern-block">
            <div class="pattern-label">{{ type.label }}</div>
            <div class="pattern-chips">
              <span
                v-for="(pattern, index) in draft.logFilenamePattern[type.key]"
                :key="pattern"
                class="pattern-chip"
              >
                {{ pattern }}
                <button class="chip-remove" @click="removePattern(type.key, index)">✕</button>
              </span>
              <span v-if="draft.logFilenamePattern[type.key].length === 0" class="pattern-empty">
                暂无 Pattern
              </span>
            </div>
            <div class="pattern-add">
              <input
                class="input"
                :placeholder="`添加 ${type.label} Pattern，如 *client*.log`"
                v-model="patternInputs[type.key]"
                @keydown.enter.prevent="addPattern(type.key)"
              />
              <button class="btn btn-default btn-sm" @click="addPattern(type.key)">添加</button>
            </div>
          </div>
        </section>

        <section class="parse-section">
          <h3>时延异常阈值（ms）</h3>
          <div class="threshold-grid">
            <label
              v-for="option in EDITABLE_THRESHOLD_OPTIONS"
              :key="option.key"
              class="threshold-item"
            >
              <span class="threshold-label">{{ option.label }}</span>
              <input
                class="input"
                :class="{ invalid: invalidFields.has(option.key) }"
                type="text"
                v-model="draft.logAnalyzerParams[option.key]"
              />
              <span class="threshold-desc">{{ option.description }}</span>
            </label>
          </div>
        </section>
      </template>
    </template>

    <template v-if="assetType !== 'brpc'" #footer>
      <button class="btn btn-default" :disabled="loading || saving" @click="resetDraft">
        恢复默认
      </button>
      <button
        class="btn btn-primary"
        :disabled="loading || saving || writeRestricted"
        :title="writeRestricted ? writeRestrictedMessage : ''"
        @click="save"
      >
        {{ saving ? '保存中...' : '保存' }}
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
.parse-summary {
  font-size: 12px;
  color: var(--text2);
  margin: 0 0 16px;
}
.parse-section {
  margin-bottom: 20px;
}
.parse-section h3 {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 10px;
}
.import-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.import-message {
  margin-top: 8px;
  font-size: 12px;
  color: var(--primary, #2563eb);
}
.pattern-block {
  margin-bottom: 12px;
}
.pattern-label {
  font-size: 12px;
  color: var(--text2);
  margin-bottom: 4px;
}
.pattern-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}
.pattern-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-family: monospace;
  background: var(--bg2, #f3f4f6);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 6px;
}
.chip-remove {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 11px;
  color: var(--text3);
  padding: 0;
}
.pattern-empty {
  font-size: 12px;
  color: var(--text3);
}
.pattern-add {
  display: flex;
  gap: 8px;
}
.pattern-add .input {
  flex: 1;
}
.threshold-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.threshold-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.threshold-label {
  font-size: 12px;
}
.threshold-desc {
  font-size: 11px;
  color: var(--text3);
}
.input.invalid {
  border-color: var(--danger, #dc2626);
}
</style>
