import { computed, reactive, ref } from 'vue'
import type { AssetModalMode, LogKnowledge } from '../types'
import { errorText, paginate } from '../utils/format'
import { useToast } from './useToast'
import { useServiceHealth } from './useServiceHealth'
import { createLogKb, deleteLogKb, getLogKb, listAllLogKbs, updateLogKb } from '../api/logKnowledge'
import { listLogFiles } from '../api/logFile'
import { listTasks } from '../api/task'

type AssetLatestTask = { status: string; taskType: string; createdAt: string }

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

  // 资产卡片摘要（当前页）：最新一条任务（轻量、不含 task_reports）+ 日志文件数。
  // 两项各自独立失败：取不到的那一项保持 undefined —— 卡片不渲染状态徽标、计数显示 `—`，
  // 避免误报「暂无任务」或把不准确的计数显示出来。
  const assetLatestTasks = ref<Record<string, AssetLatestTask | null>>({})
  const assetLogFileCounts = ref<Record<string, number>>({})

  const loadAssetCardSummaries = async (list: LogKnowledge[]) => {
    const pending = list
      .map((asset) => asset.id)
      .filter((id) => id && (!(id in assetLatestTasks.value) || !(id in assetLogFileCounts.value)))
    if (pending.length === 0) return

    const results = await Promise.all(
      pending.map(async (id) => {
        const [task, count] = await Promise.all([
          listTasks({ kb_id: id, created_sorted_desc: true, page_cnt: 1, page_num: 1 })
            .then(({ tasks }) => tasks?.[0] ?? null)
            .catch(() => undefined),
          // 文件数只认 /log_file/list 的 total；资产列表里的 task_cnt 在 UBSocket 资产上不刷新
          listLogFiles(id, 1, 1)
            .then(({ total }) => total ?? 0)
            .catch(() => undefined),
        ])
        return [id, task, count] as const
      }),
    )

    const nextTasks = { ...assetLatestTasks.value }
    const nextCounts = { ...assetLogFileCounts.value }
    for (const [id, task, count] of results) {
      if (task !== undefined) {
        nextTasks[id] = task
          ? {
              status: task.status ?? '',
              taskType: task.task_type ?? '',
              createdAt: task.created_at ?? '',
            }
          : null
      }
      if (count !== undefined) nextCounts[id] = count
    }
    assetLatestTasks.value = nextTasks
    assetLogFileCounts.value = nextCounts
  }

  const loadAssets = async () => {
    assetsLoading.value = true
    assetsError.value = ''
    assetLatestTasks.value = {}
    assetLogFileCounts.value = {}
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
    assetLatestTasks,
    assetLogFileCounts,
    loadAssetCardSummaries,
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
