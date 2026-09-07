<script setup lang="ts">
import { useTasks } from '../composables/useTasks'

const {
  brpcModalOpen,
  brpcTargetFile,
  brpcStartTime,
  brpcSaving,
  brpcError,
  runBrpcDiagnosis,
} = useTasks()
</script>

<template>
  <!-- ============ UBSocket 诊断弹窗 ============ -->
  <div class="modal-overlay" v-if="brpcModalOpen" @click.self="brpcModalOpen = false">
    <div class="modal" style="width: 480px">
      <div class="modal-header">
        运行 UBSocket 诊断
        <button class="modal-close" @click="brpcModalOpen = false">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label required">日志扫描开始时间（UTC+8）</label>
          <input class="input" type="datetime-local" v-model="brpcStartTime" />
          <div class="file-hint">任务将从该时间开始扫描 UBSocket 日志，直至工具启动时间。</div>
        </div>
        <div v-if="brpcError" class="form-error">{{ brpcError }}</div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-default" @click="brpcModalOpen = false">取消</button>
        <button class="btn btn-primary" :disabled="brpcSaving || !brpcStartTime" @click="runBrpcDiagnosis">
          {{ brpcSaving ? '提交中...' : '运行诊断' }}
        </button>
      </div>
    </div>
  </div>

</template>
