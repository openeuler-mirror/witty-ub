<script setup lang="ts">
import BaseModal from './common/BaseModal.vue'
import { useTasks } from '../composables/useTasks'

const { brpcModalOpen, brpcTargetFile, brpcStartTime, brpcSaving, brpcError, runBrpcDiagnosis } =
  useTasks()
</script>

<template>
  <!-- ============ UBSocket 诊断弹窗 ============ -->
  <BaseModal
    :open="brpcModalOpen"
    size="sm"
    title="运行 UBSocket 诊断"
    @close="brpcModalOpen = false"
  >
    <div class="form-group">
      <label class="form-label required">日志扫描开始时间（UTC+8）</label>
      <input class="input" type="datetime-local" v-model="brpcStartTime" />
      <div class="file-hint">任务将从该时间开始扫描 UBSocket 日志，直至工具启动时间。</div>
    </div>
    <div v-if="brpcError" class="form-error">{{ brpcError }}</div>

    <template #footer>
      <button class="btn btn-default" @click="brpcModalOpen = false">取消</button>
      <button
        class="btn btn-primary"
        :disabled="brpcSaving || !brpcStartTime"
        @click="runBrpcDiagnosis"
      >
        {{ brpcSaving ? '提交中...' : '运行诊断' }}
      </button>
    </template>
  </BaseModal>
</template>
