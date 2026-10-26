import { computed, reactive, ref } from 'vue'
import { errorText } from '../utils/format'
import {
  fetchCaseCategories,
  fetchCases,
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
  }
}
