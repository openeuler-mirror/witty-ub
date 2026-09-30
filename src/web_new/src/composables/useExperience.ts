import { computed, reactive, ref } from 'vue'
import { errorText } from '../utils/format'
import { useToast } from './useToast'
import type { ExperienceItem, ExperienceType } from '../api/experience'
import { listExperiences, getExperience, createExperience, deleteExperience } from '../api/experience'

let state: ReturnType<typeof createExperienceState> | null = null

export function useExperience() {
  if (!state) state = createExperienceState()
  return state
}

const PAGE_SIZE = 12

function createExperienceState() {
  const { toast } = useToast()

  const expType = ref<ExperienceType>('SKILL')
  const items = ref<ExperienceItem[]>([])
  const loading = ref(false)
  const error = ref('')
  const page = ref(1)
  const total = ref(0)
  const searchKey = ref('')

  const filteredItems = computed(() => {
    const keyword = searchKey.value.trim().toLowerCase()
    if (!keyword) return items.value
    return items.value.filter(
      (item) =>
        item.name.toLowerCase().includes(keyword) ||
        item.description.toLowerCase().includes(keyword) ||
        item.keywords.some((kw) => kw.toLowerCase().includes(keyword)),
    )
  })

  const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / PAGE_SIZE)))
  const pagedItems = computed(() =>
    filteredItems.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE),
  )

  const loadList = async () => {
    loading.value = true
    error.value = ''
    try {
      const result = await listExperiences({ exp_type: expType.value, page: 1, page_size: 100 })
      items.value = result.items ?? []
      total.value = result.total ?? 0
      page.value = 1
    } catch (e) {
      error.value = errorText(e)
      items.value = []
    } finally {
      loading.value = false
    }
  }

  const switchType = async (type: ExperienceType) => {
    if (expType.value === type) return
    expType.value = type
    searchKey.value = ''
    await loadList()
  }

  // ---- 查看 ----
  const detailOpen = ref(false)
  const detailLoading = ref(false)
  const detailItem = ref<ExperienceItem | null>(null)

  const openDetail = async (item: ExperienceItem) => {
    detailOpen.value = true
    detailLoading.value = true
    detailItem.value = null
    try {
      const detail = await getExperience(item.id)
      detailItem.value = detail
    } catch (e) {
      toast(errorText(e), 'error')
      detailItem.value = item
    } finally {
      detailLoading.value = false
    }
  }

  const closeDetail = () => {
    detailOpen.value = false
    detailItem.value = null
  }

  // ---- 添加 ----
  const addOpen = ref(false)
  const saving = ref(false)
  const addForm = reactive({
    name: '',
    description: '',
    keywords: '',
    content: '',
  })
  const addError = ref('')

  const openAdd = () => {
    addForm.name = ''
    addForm.description = ''
    addForm.keywords = ''
    addForm.content = ''
    addError.value = ''
    addOpen.value = true
  }

  const closeAdd = () => {
    if (saving.value) return
    addOpen.value = false
  }

  const saveAdd = async () => {
    const name = addForm.name.trim()
    if (!name) {
      addError.value = '请输入名称'
      return
    }
    if (!addForm.description.trim()) {
      addError.value = '请输入描述'
      return
    }
    saving.value = true
    addError.value = ''
    try {
      const keywords = addForm.keywords
        .split(/[,\n，]/)
        .map((k) => k.trim())
        .filter(Boolean)
      await createExperience({
        exp_type: expType.value,
        name,
        description: addForm.description.trim(),
        keywords,
        content: addForm.content,
      })
      toast('创建成功', 'success')
      addOpen.value = false
      await loadList()
    } catch (e) {
      addError.value = errorText(e)
    } finally {
      saving.value = false
    }
  }

  // ---- 删除 ----
  const removeItem = async (item: ExperienceItem) => {
    if (!window.confirm(`确认删除「${item.name}」？该操作将同时删除源文件，不可恢复。`)) return
    try {
      await deleteExperience(item.id)
      toast('已删除', 'success')
      await loadList()
    } catch (e) {
      toast(errorText(e), 'error')
    }
  }

  return {
    expType,
    items,
    loading,
    error,
    page,
    total,
    searchKey,
    filteredItems,
    totalPages,
    pagedItems,
    loadList,
    switchType,
    // detail
    detailOpen,
    detailLoading,
    detailItem,
    openDetail,
    closeDetail,
    // add
    addOpen,
    saving,
    addForm,
    addError,
    openAdd,
    closeAdd,
    saveAdd,
    // delete
    removeItem,
  }
}
