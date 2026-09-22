<script setup lang="ts">
import BaseModal from './common/BaseModal.vue'
import { useAssets } from '../composables/useAssets'
import { useServiceHealth } from '../composables/useServiceHealth'

const {
  assetModalOpen,
  assetModalMode,
  savingAsset,
  assetForm,
  assetFormError,
  closeAssetModal,
  saveAsset,
} = useAssets()

// 磁盘降级（只读）时后端不再接受写入，界面同步禁用保存
const { writeRestricted, writeRestrictedMessage } = useServiceHealth()
</script>

<template>
  <!-- ============ 资产弹窗 ============ -->
  <BaseModal
    :open="assetModalOpen"
    size="md"
    :title="assetModalMode === 'create' ? '创建资产' : '编辑资产'"
    @close="closeAssetModal"
  >
    <div class="form-group">
      <label class="form-label required">资产库名称</label>
      <input class="input" v-model="assetForm.name" placeholder="例如：生产环境日志库" />
    </div>
    <div class="form-group">
      <label class="form-label required">简介</label>
      <textarea
        class="textarea"
        v-model="assetForm.description"
        rows="3"
        placeholder="资产库用途 / 日志路径说明"
      ></textarea>
    </div>
    <div v-if="assetFormError" class="form-error">{{ assetFormError }}</div>
    <div v-if="writeRestricted" class="error-banner">{{ writeRestrictedMessage }}</div>

    <template #footer>
      <button class="btn btn-default" @click="closeAssetModal">取消</button>
      <button
        class="btn btn-primary"
        :disabled="savingAsset || writeRestricted"
        :title="writeRestricted ? writeRestrictedMessage : ''"
        @click="saveAsset"
      >
        {{ savingAsset ? '保存中...' : '保存' }}
      </button>
    </template>
  </BaseModal>
</template>
