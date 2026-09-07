<script setup lang="ts">
import { useAssets } from '../composables/useAssets'

const {
  assetModalOpen,
  assetModalMode,
  savingAsset,
  assetForm,
  assetFormError,
  closeAssetModal,
  saveAsset,
} = useAssets()
</script>

<template>
  <!-- ============ 资产弹窗 ============ -->
  <div class="modal-overlay" v-if="assetModalOpen" @click.self="closeAssetModal">
    <div class="modal" style="width: 520px">
      <div class="modal-header">
        {{ assetModalMode === 'create' ? '创建资产' : '编辑资产' }}
        <button class="modal-close" @click="closeAssetModal">✕</button>
      </div>
      <div class="modal-body">
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
      </div>
      <div class="modal-footer">
        <button class="btn btn-default" @click="closeAssetModal">取消</button>
        <button class="btn btn-primary" :disabled="savingAsset" @click="saveAsset">
          {{ savingAsset ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>
  </div>

</template>
