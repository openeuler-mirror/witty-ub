<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  updateDiagCaseVerification,
  type DiagCaseDetail,
  type DiagCaseVerification,
} from '../../api/diagCaseLibrary'
import { useOperator } from '../../composables/useOperator'
import { useToast } from '../../composables/useToast'

const props = withDefaults(
  defineProps<{
    caseId: string
    revision: number
    initial?: DiagCaseVerification | null
    disabled?: boolean
  }>(),
  { initial: null, disabled: false },
)
const emit = defineEmits<{ saved: [DiagCaseDetail] }>()

const { operator, setOperator, requireOperator } = useOperator()
const { toast } = useToast()

const method = ref('')
const observedResult = ref('')
const closedLoop = ref(false)
const notes = ref('')
const saving = ref(false)
const error = ref('')

const loadInitial = (value: DiagCaseVerification | null | undefined) => {
  method.value = value?.method ?? ''
  observedResult.value = value?.observed_result ?? ''
  closedLoop.value = Boolean(value?.closed_loop)
  notes.value = value?.notes ?? ''
}
watch(() => props.initial, loadInitial, { immediate: true })

const save = async () => {
  const reviewer = requireOperator()
  if (!reviewer) {
    error.value = '请先填写操作人'
    return
  }
  if (closedLoop.value && (!method.value.trim() || !observedResult.value.trim())) {
    error.value = '标记闭环时必须填写验证方法和实测结果'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const result = await updateDiagCaseVerification(
      props.caseId,
      {
        method: method.value.trim() || null,
        observed_result: observedResult.value.trim() || null,
        closed_loop: closedLoop.value,
        verified_by: reviewer,
        verified_at: new Date().toISOString(),
        notes: notes.value.trim() || null,
      },
      props.revision,
    )
    toast('验证结果已保存', 'success')
    emit('saved', result)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '验证结果保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="verification-form">
    <div class="form-row">
      <div class="form-group" style="flex: 1">
        <label class="form-label">操作人</label>
        <input
          class="input"
          :value="operator"
          :disabled="disabled || saving"
          placeholder="确认/验证操作人"
          @input="setOperator(($event.target as HTMLInputElement).value)"
        />
      </div>
    </div>
    <div class="form-row">
      <div class="form-group" style="flex: 1">
        <label class="form-label">验证方法</label>
        <input class="input" v-model="method" :disabled="disabled || saving" />
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">实测结果</label>
      <textarea
        class="textarea"
        rows="2"
        v-model="observedResult"
        :disabled="disabled || saving"
        placeholder="只填写真实复测观察，不要复制预期结果"
      ></textarea>
    </div>
    <div class="form-group">
      <label class="form-label">备注</label>
      <input class="input" v-model="notes" :disabled="disabled || saving" />
    </div>
    <label class="form-check">
      <input type="checkbox" v-model="closedLoop" :disabled="disabled || saving" />
      复测已闭环
    </label>
    <div v-if="error" class="form-error">{{ error }}</div>
    <div class="verification-actions">
      <button
        class="btn btn-primary btn-sm"
        type="button"
        :disabled="disabled || saving"
        @click="save"
      >
        {{ saving ? '保存中...' : '保存验证结果' }}
      </button>
    </div>
  </div>
</template>
