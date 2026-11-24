<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { fetchClassifierTraining, retryClassifierTraining } from '../api/faultClassifier'
import { classifierTrainingNotice, type ClassifierTrainingStatus } from '../utils/classifierTraining'

const props = defineProps<{ refreshToken?: number; operator?: string }>()
const state = ref<ClassifierTrainingStatus | null>(null)
const unavailable = ref(false)
const retrying = ref(false)
const notice = computed(() => classifierTrainingNotice(state.value, unavailable.value))
let timer: ReturnType<typeof setTimeout> | undefined
let controller: AbortController | undefined
let mounted = false
let sequence = 0
const refresh = async () => {
  if (timer) clearTimeout(timer)
  controller?.abort()
  controller = new AbortController()
  const current = ++sequence
  try {
    const result = await fetchClassifierTraining(controller.signal)
    if (mounted && current === sequence) { state.value = result; unavailable.value = false }
  } catch (error) {
    if (mounted && current === sequence && !(error instanceof DOMException && error.name === 'AbortError')) unavailable.value = true
  } finally {
    if (mounted && current === sequence) timer = setTimeout(() => void refresh(), notice.value.busy ? 2000 : 5000)
  }
}
const retry = async () => {
  if (!props.operator?.trim() || retrying.value) return
  retrying.value = true
  try { state.value = await retryClassifierTraining(props.operator.trim()); unavailable.value = false }
  catch { unavailable.value = true }
  finally { retrying.value = false; void refresh() }
}
onMounted(() => { mounted = true; void refresh() })
watch(() => props.refreshToken, () => { if (mounted) void refresh() })
onBeforeUnmount(() => { mounted = false; sequence++; controller?.abort(); if (timer) clearTimeout(timer) })
</script>

<template>
  <aside class="classifier-training" :class="notice.tone" :role="['failed', 'insufficient_data'].includes(state?.status ?? '') ? 'alert' : 'status'" aria-live="polite" :aria-busy="notice.busy">
    <span class="training-icon" :class="{ spinning: notice.busy }" aria-hidden="true">{{ notice.busy ? '◌' : ['failed', 'insufficient_data'].includes(state?.status ?? '') ? '!' : '✓' }}</span>
    <div class="training-copy">
      <strong>{{ notice.title }}</strong>
      <p v-if="notice.detail">{{ notice.detail }}</p>
      <small v-if="state?.status === 'ready' && state.completed_at">完成时间：{{ state.completed_at.replace('T', ' ') }}</small>
    </div>
    <button v-if="state?.status === 'failed' && operator?.trim()" type="button" :disabled="retrying" @click="retry">{{ retrying ? '正在提交…' : '重新训练' }}</button>
  </aside>
</template>

<style scoped>
.classifier-training { display: flex; align-items: flex-start; gap: 12px; margin: 0 0 18px; padding: 16px 18px; border: 1px solid #d3deeb; border-left-width: 4px; border-radius: 8px; background: #f4f7fb; color: #44556d; }
.classifier-training.warning { background: #fff8e8; border-color: #dca02b; color: #805611; }
.classifier-training.success { background: #ecf8f1; border-color: #3b9a68; color: #236745; }
.classifier-training.danger { background: #fff1f0; border-color: #cf6660; color: #9d3c37; }
.training-icon { font-size: 24px; line-height: 1; flex: none; }
.training-copy { min-width: 0; flex: 1; }
.training-copy strong { font-size: 16px; }
.training-copy p { margin: 5px 0 0; font-size: 14px; line-height: 1.6; }
.training-copy small { display: block; margin-top: 5px; opacity: .8; }
button { cursor: pointer; background: transparent; color: inherit; border: 1px solid currentColor; border-radius: 5px; padding: 6px 12px; }
.spinning { animation: training-spin 1s linear infinite; }
@keyframes training-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinning { animation: none; } }
</style>
