import { computed, reactive, ref } from 'vue'
import { errorText } from '../utils/format'
import { useToast } from './useToast'
import {
  createCategory,
  deleteCase,
  deleteCategory,
  deleteType,
  fetchCaseCategories,
  fetchCases,
  updateCase,
  updateCategory,
  updateType,
  type CaseCategory,
  type CaseRecord,
} from '../api/caseLibrary'

/** 侧栏选中范围：全部 / 某大类 / 某故障类型（按名称） */
export type CaseScope =
  | { kind: 'all' }
  | { kind: 'category'; id: string }
  | { kind: 'type'; name: string }

let state: ReturnType<typeof createCaseLibraryState> | null = null

export function useCaseLibrary() {
  if (!state) state = createCaseLibraryState()
  return state
}

function createCaseLibraryState() {
  const { toast } = useToast()

  const cases = ref<CaseRecord[]>([])
  const categories = ref<CaseCategory[]>([])
  const loading = ref(false)
  const error = ref('')

  const scope = ref<CaseScope>({ kind: 'all' })
  const filterText = ref('')
  const expanded = reactive(new Set<string>())

  const load = async () => {
    loading.value = true
    error.value = ''
    try {
      const [caseList, catList] = await Promise.all([fetchCases(), fetchCaseCategories()])
      cases.value = caseList ?? []
      categories.value = catList ?? []
    } catch (err) {
      error.value = errorText(err)
    } finally {
      loading.value = false
    }
  }

  const filteredCategories = computed(() => {
    const keyword = filterText.value.trim().toLowerCase()
    if (!keyword) return categories.value
    return categories.value.filter(
      (cat) =>
        cat.name.toLowerCase().includes(keyword) ||
        (cat.types ?? []).some((t) => t.name.toLowerCase().includes(keyword)),
    )
  })

  const scopedCases = computed(() => {
    const current = scope.value
    if (current.kind === 'all') return cases.value
    if (current.kind === 'category') {
      const cat = categories.value.find((item) => item.id === current.id)
      const typeNames = new Set((cat?.types ?? []).map((t) => t.name))
      const name = cat?.name ?? ''
      return cases.value.filter(
        (item) => item.case_category === name || typeNames.has(item.root_cause_type),
      )
    }
    return cases.value.filter((item) => item.root_cause_type === current.name)
  })

  const selectAll = () => {
    scope.value = { kind: 'all' }
  }
  const selectCategory = (id: string) => {
    scope.value = { kind: 'category', id }
    expanded.add(id)
  }
  const selectType = (name: string) => {
    scope.value = { kind: 'type', name }
  }
  const toggleExpand = (id: string) => {
    if (expanded.has(id)) expanded.delete(id)
    else expanded.add(id)
  }

  const scopeTitle = computed(() => {
    const current = scope.value
    if (current.kind === 'all') return '全部案例'
    if (current.kind === 'category')
      return categories.value.find((item) => item.id === current.id)?.name ?? '分类案例'
    return current.name
  })

  // ===== 案例分类编辑（行内 datalist 选或输） =====
  const editingCaseId = ref('')
  const editCaseCategory = ref('')
  const editCaseType = ref('')

  const startEditCase = (item: CaseRecord) => {
    editingCaseId.value = item.id
    editCaseCategory.value = item.case_category ?? ''
    editCaseType.value = item.root_cause_type ?? ''
  }
  const cancelEditCase = () => {
    editingCaseId.value = ''
  }
  const saveEditCase = async (item: CaseRecord) => {
    try {
      await updateCase(item.id, {
        caseCategory: editCaseCategory.value.trim(),
        rootCauseType: editCaseType.value.trim(),
      })
      toast('案例分类已更新', 'success')
      editingCaseId.value = ''
      await load()
    } catch (err) {
      toast(errorText(err), 'error')
    }
  }

  const removeCase = async (item: CaseRecord) => {
    if (!window.confirm(`确认删除案例「${item.root_cause_type}」？该操作不可恢复。`)) return
    try {
      await deleteCase(item.id)
      toast('案例已删除', 'success')
      await load()
    } catch (err) {
      toast(errorText(err), 'error')
    }
  }

  // ===== 大类 / 类型元数据管理 =====
  // 编辑草稿用非空对象：id 为空串表示未处于编辑态，模板 v-model 无需空值窄化
  const editingCategory = reactive({ id: '', name: '', description: '' })
  const editingType = reactive({ id: '', name: '', description: '' })
  const creatingCategory = ref(false)
  const newCategoryName = ref('')

  const startEditCategory = (cat: CaseCategory) => {
    editingCategory.id = cat.id
    editingCategory.name = cat.name
    editingCategory.description = cat.description ?? ''
    editingType.id = ''
  }
  const cancelEditCategory = () => {
    editingCategory.id = ''
  }
  const saveEditCategory = async () => {
    if (!editingCategory.id) return
    try {
      await updateCategory(editingCategory.id, {
        name: editingCategory.name,
        description: editingCategory.description,
      })
      toast('分类已更新', 'success')
      editingCategory.id = ''
      await load()
    } catch (err) {
      toast(errorText(err), 'error')
    }
  }

  const removeCategory = async (cat: CaseCategory) => {
    const recursive =
      (cat.case_count ?? 0) > 0 || (cat.types ?? []).some((t) => (t.case_count ?? 0) > 0)
    const message = recursive
      ? `分类「${cat.name}」下仍有案例。确认递归删除该分类及其全部子类型与案例？该操作不可恢复。`
      : `确认删除分类「${cat.name}」？`
    if (!window.confirm(message)) return
    try {
      await deleteCategory(cat.id, recursive)
      toast('分类已删除', 'success')
      if (scope.value.kind === 'category' && scope.value.id === cat.id) selectAll()
      await load()
    } catch (err) {
      toast(errorText(err), 'error')
    }
  }

  const submitCreateCategory = async () => {
    const name = newCategoryName.value.trim()
    if (!name) return
    try {
      await createCategory(name)
      toast('分类已创建', 'success')
      creatingCategory.value = false
      newCategoryName.value = ''
      await load()
    } catch (err) {
      toast(errorText(err), 'error')
    }
  }

  const startEditType = (t: { id?: string; name: string; description: string }) => {
    if (!t.id) return
    editingType.id = t.id
    editingType.name = t.name
    editingType.description = t.description ?? ''
    editingCategory.id = ''
  }
  const cancelEditType = () => {
    editingType.id = ''
  }
  const saveEditType = async () => {
    if (!editingType.id) return
    try {
      await updateType(editingType.id, {
        name: editingType.name,
        description: editingType.description,
      })
      toast('类型已更新', 'success')
      editingType.id = ''
      await load()
    } catch (err) {
      toast(errorText(err), 'error')
    }
  }

  const removeType = async (t: { id?: string; name: string; case_count?: number }) => {
    if (!t.id) return
    const recursive = (t.case_count ?? 0) > 0
    const message = recursive
      ? `类型「${t.name}」下有 ${t.case_count} 条案例。确认递归删除类型及全部案例？该操作不可恢复。`
      : `确认删除类型「${t.name}」？`
    if (!window.confirm(message)) return
    try {
      await deleteType(t.id, recursive)
      toast('类型已删除', 'success')
      if (scope.value.kind === 'type' && scope.value.name === t.name) selectAll()
      await load()
    } catch (err) {
      toast(errorText(err), 'error')
    }
  }

  return {
    cases,
    categories,
    loading,
    error,
    scope,
    filterText,
    expanded,
    load,
    filteredCategories,
    scopedCases,
    scopeTitle,
    selectAll,
    selectCategory,
    selectType,
    toggleExpand,
    editingCaseId,
    editCaseCategory,
    editCaseType,
    startEditCase,
    cancelEditCase,
    saveEditCase,
    removeCase,
    editingCategory,
    editingType,
    creatingCategory,
    newCategoryName,
    startEditCategory,
    cancelEditCategory,
    saveEditCategory,
    removeCategory,
    submitCreateCategory,
    startEditType,
    cancelEditType,
    saveEditType,
    removeType,
  }
}
