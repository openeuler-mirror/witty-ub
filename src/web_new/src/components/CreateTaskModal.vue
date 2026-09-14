<script setup lang="ts">
import BaseModal from './common/BaseModal.vue'
import { useTasks } from '../composables/useTasks'

const {
  showCreateTask,
  savingTask,
  taskError,
  newTask,
  closeCreateTask,
  onTaskFilesChange,
  canSubmitTask,
  createTask,
} = useTasks()
</script>

<template>
  <!-- ============ 创建任务弹窗 ============ -->
  <BaseModal :open="showCreateTask" size="lg" title="创建任务" @close="closeCreateTask">
    <div class="form-group">
      <label class="form-label">任务名称</label>
      <input class="input" v-model="newTask.name" placeholder="留空则使用日志文件名" />
    </div>
    <div class="form-group">
      <label class="form-label">任务类型</label>
      <label class="radio">
        <input type="radio" value="KVCache" v-model="newTask.taskType" /> KVCache 日志
      </label>
      <label class="radio">
        <input type="radio" value="UBSocket" v-model="newTask.taskType" /> UBSocket 接口
      </label>
    </div>
    <div class="form-group">
      <label class="form-label">日志来源</label>
      <label class="radio"
        ><input type="radio" value="local" v-model="newTask.sourceType" /> 本地路径</label
      >
      <label class="radio"
        ><input type="radio" value="remote" v-model="newTask.sourceType" /> 远程 URL</label
      >
      <label class="radio"
        ><input type="radio" value="upload" v-model="newTask.sourceType" /> 上传文件</label
      >
    </div>
    <div v-if="newTask.sourceType === 'local'" class="form-group">
      <input
        class="input"
        v-model="newTask.source"
        placeholder="/home/xxx/logs/ds_client_access.log"
      />
    </div>
    <div v-else-if="newTask.sourceType === 'remote'" class="form-group">
      <input class="input" v-model="newTask.source" placeholder="https://example.com/logs.zip" />
    </div>
    <div v-else class="form-group">
      <input type="file" multiple class="file-input" @change="onTaskFilesChange" />
      <div class="file-hint">支持 .log / .gz / .zip，可多选</div>
    </div>
    <div class="advanced-toggle" @click="newTask.advanced = !newTask.advanced">
      {{ newTask.advanced ? '▼' : '▶' }} 高级配置
    </div>
    <div v-if="newTask.advanced" class="form-row">
      <div class="form-group">
        <label class="form-label">起始时间</label>
        <input class="input" type="datetime-local" v-model="newTask.timeStart" />
      </div>
      <div class="form-group">
        <label class="form-label">结束时间</label>
        <input class="input" type="datetime-local" v-model="newTask.timeEnd" />
      </div>
      <div class="form-group">
        <label class="form-label">最小耗时阈值(ms)</label>
        <input class="input" type="number" min="0" v-model.number="newTask.minElapsedMs" />
      </div>
    </div>
    <div v-if="taskError" class="form-error">{{ taskError }}</div>

    <template #footer>
      <button class="btn btn-default" @click="closeCreateTask">取消</button>
      <button class="btn btn-primary" :disabled="savingTask || !canSubmitTask" @click="createTask">
        {{ savingTask ? '提交中...' : '确认创建' }}
      </button>
    </template>
  </BaseModal>
</template>
