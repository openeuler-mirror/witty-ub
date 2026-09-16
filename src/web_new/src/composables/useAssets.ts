import { computed, reactive, ref } from 'vue'
import type { AssetModalMode, LogKnowledge } from '../types'
import { errorText, paginate } from '../utils/format'
import { useToast } from './useToast'
import { useServiceHealth } from './useServiceHealth'
import { createLogKb, deleteLogKb, getLogKb, listAllLogKbs, updateLogKb } from '../api/logKnowledge'

let state: ReturnType<typeof createAssetsState> | null = null

export function useAssets() {
  if (!state) state = createAssetsState()
  return state
}

function createAssetsState() {
  const { toast } = useToast()
  const { writeRestricted, writeRestrictedMessage } = useServiceHealth()

  const view = ref<'assets' | 'home'>('assets')
  const assetTab = ref<'overview' | 'tasks'>('overview')

  const assets = ref<LogKnowledge[]>([])
  const assetsLoading = ref(false)
  const assetsError = ref('')
  const isInitialDataUnavailable = computed(
    () => Boolean(assetsError.value) && assets.value.length === 0 && !selectedAsset.value,
  )
  const searchMode = ref<'all' | 'name' | 'desc'>('all')
  const searchKey = ref('')
  const assetPage = ref(1)
  const assetPageSize = 12

  const filteredAssets = computed(() => {
    const keyword = searchKey.value.trim().toLowerCase()
    let list = assets.value
    if (keyword) {
      list = list.filter((asset) => {
        if (searchMode.value === 'name') return asset.name.toLowerCase().includes(keyword)
        if (searchMode.value === 'desc') return asset.description.toLowerCase().includes(keyword)
        return (
          asset.name.toLowerCase().includes(keyword) ||
          asset.description.toLowerCase().includes(keyword)
        )
      })
    }
    return list
  })

  const assetPages = computed(() =>
    Math.max(1, Math.ceil(filteredAssets.value.length / assetPageSize)),
  )
  const pagedAssets = computed(() => paginate(filteredAssets.value, assetPage.value, assetPageSize))

  const loadAssets = async () => {
    assetsLoading.value = true
    assetsError.value = ''
    try {
      assets.value = await listAllLogKbs()
    } catch (error) {
      assetsError.value = errorText(error)
    } finally {
      assetsLoading.value = false
    }
  }

  const selectedAsset = ref<LogKnowledge | null>(null)
  const assetLoading = ref(false)
  const assetError = ref('')

  const enterAsset = async (asset: LogKnowledge) => {
    selectedAsset.value = asset
    view.value = 'home'
    assetTab.value = 'overview'
    assetError.value = ''
    assetLoading.value = true
    // 任务列表与资产详情并行拉取。否则分析页会先按「上一个库/空列表」画一屏空图表，
    // 等任务列表返回后再切成空态或真实数据。
    const { useTasks } = await import('./useTasks')
    const tasksPromise = useTasks().loadLogFiles(asset.id)
    try {
      const result = await getLogKb(asset.id)
      if (result.kb) selectedAsset.value = result.kb
    } catch (error) {
      assetError.value = errorText(error)
    } finally {
      assetLoading.value = false
    }
    await Promise.all([tasksPromise, loadAssets()])
  }

  const goAssetList = () => {
    view.value = 'assets'
    selectedAsset.value = null
    assetTab.value = 'overview'
  }

  const assetModalOpen = ref(false)
  const assetModalMode = ref<AssetModalMode>('create')
  const savingAsset = ref(false)
  const assetForm = reactive({ name: '', description: '' })
  const assetFormError = ref('')

  const openAssetModal = (asset?: LogKnowledge | null) => {
    assetModalMode.value = asset ? 'edit' : 'create'
    assetForm.name = asset?.name ?? ''
    assetForm.description = asset?.description ?? ''
    assetFormError.value = ''
    assetModalOpen.value = true
  }

  const closeAssetModal = () => {
    if (savingAsset.value) return
    assetModalOpen.value = false
  }

  const saveAsset = async () => {
    if (writeRestricted.value) {
      assetFormError.value = writeRestrictedMessage.value
      return
    }
    const name = assetForm.name.trim()
    const description = assetForm.description.trim()
    if (!name || !description) {
      assetFormError.value = '请填写资产库名称和简介'
      return
    }
    if (
      assetModalMode.value === 'create' &&
      assets.value.some((asset) => asset.existed_status !== false && asset.name.trim() === name)
    ) {
      assetFormError.value = '资产库名称已存在'
      return
    }
    savingAsset.value = true
    assetFormError.value = ''
    try {
      if (assetModalMode.value === 'create') {
        await createLogKb(name, description)
        toast('资产库创建成功', 'success')
      } else if (selectedAsset.value) {
        await updateLogKb(selectedAsset.value.id, name, description)
        if (selectedAsset.value) {
          selectedAsset.value = { ...selectedAsset.value, name, description }
        }
        toast('资产库已更新', 'success')
      }
      assetModalOpen.value = false
      await loadAssets()
    } catch (error) {
      assetFormError.value = errorText(error)
    } finally {
      savingAsset.value = false
    }
  }

  const deleteAsset = async (asset: LogKnowledge) => {
    // 后端为硬删除级联：进程树停不下来会直接取消删除，数据不可恢复，必须说清。
    if (
      !window.confirm(
        `确认删除资产库「${asset.name}」？该资产库下的所有日志解析任务及解析、诊断数据将被永久删除。`,
      )
    ) {
      return
    }
    try {
      await deleteLogKb(asset.id)
      if (selectedAsset.value?.id === asset.id) goAssetList()
      toast('资产库已删除', 'success')
      await loadAssets()
    } catch (error) {
      toast(errorText(error), 'error')
    }
  }

  return {
    view,
    assetTab,
    assets,
    assetsLoading,
    assetsError,
    isInitialDataUnavailable,
    searchMode,
    searchKey,
    assetPage,
    filteredAssets,
    assetPages,
    pagedAssets,
    loadAssets,
    selectedAsset,
    assetError,
    enterAsset,
    goAssetList,
    assetModalOpen,
    assetModalMode,
    savingAsset,
    assetForm,
    assetFormError,
    openAssetModal,
    closeAssetModal,
    saveAsset,
    deleteAsset,
  }
}
