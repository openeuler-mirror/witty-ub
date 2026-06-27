/**
 * 表格排序状态管理 Composable
 * 
 * 排序交互逻辑：
 * - 第1次点击表头：将字段加入排序列表，默认降序(desc)
 * - 第2次点击同一字段：切换为升序(asc)
 * - 第3次点击同一字段：从排序列表中移除
 * 
 * 支持多字段排序，按加入顺序确定优先级
 * 
 * 优化特性：
 * - 防抖：短时间内多次点击只执行最后一次排序请求
 * - 请求取消：新请求发起时取消之前未完成的请求
 * - 排序状态锁：请求期间禁用表头点击
 */

export type SortOrder = 'asc' | 'desc'

export type SortField = {
  field: string
  order: SortOrder
}

import { ref, computed, type Ref } from 'vue'

export function useTableSort(defaultSort: SortField[] = [], onSortChange?: () => void) {
  const sortFields: Ref<SortField[]> = ref([...defaultSort])
  
  // 防抖计时器
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  
  // 排序状态锁（是否正在加载）
  const isSorting = ref(false)
  
  // AbortController用于取消请求
  let abortController: AbortController | null = null
  
  // 待处理的排序请求标志（当请求正在进行时，用户点击会设置此标志）
  const hasPendingSort = ref(false)

  /**
   * 处理表头点击事件（带防抖和状态锁）
   * @param field 字段名称
   */
  const handleHeaderClick = (field: string) => {
    // 更新排序状态（无论是否正在排序，都需要更新）
    const existingIndex = sortFields.value.findIndex((s) => s.field === field)

    if (existingIndex === -1) {
      // 第1次点击：加入排序列表，默认降序
      sortFields.value.push({ field, order: 'desc' })
    } else {
      const existingSort = sortFields.value[existingIndex]
      if (!existingSort) return
      if (existingSort.order === 'desc') {
        // 第2次点击：切换为升序
        existingSort.order = 'asc'
      } else {
        // 第3次点击：移除该字段
        sortFields.value.splice(existingIndex, 1)
      }
    }
    
    // 如果正在排序中，标记有待处理请求，等待当前请求完成后再执行
    if (isSorting.value) {
      hasPendingSort.value = true
      return
    }
    
    // 否则触发排序变化回调（带防抖）
    triggerSortChange()
  }
  
  /**
   * 触发排序变化（带防抖）
   */
  const triggerSortChange = () => {
    if (!onSortChange) return
    
    // 取消之前的防抖计时器
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    
    // 设置新的防抖计时器（300ms延迟）
    debounceTimer = setTimeout(() => {
      // 取消之前未完成的请求
      if (abortController) {
        abortController.abort()
        abortController = null
      }
      
      // 创建新的AbortController
      abortController = new AbortController()
      
      // 设置排序状态锁
      isSorting.value = true
      hasPendingSort.value = false
      
      try {
        onSortChange()
      } finally {
        // 请求完成后释放锁（实际应在请求完成时手动调用releaseSortLock）
        // 这里只是一个兜底，建议在调用方的请求完成后调用releaseSortLock
      }
    }, 300)
  }
  
  /**
   * 释放排序状态锁（应在请求完成时调用）
   */
  const releaseSortLock = () => {
    isSorting.value = false
    abortController = null
    
    // 如果有待处理的排序请求，立即触发新请求
    if (hasPendingSort.value) {
      triggerSortChange()
    }
  }
  
  /**
   * 获取当前的AbortSignal（用于取消请求）
   */
  const getAbortSignal = () => {
    return abortController?.signal
  }

  /**
   * 获取字段的当前排序状态
   * @param field 字段名称
   * @returns 'asc' | 'desc' | null (null表示未排序)
   */
  const getSortOrder = (field: string): SortOrder | null => {
    const sortField = sortFields.value.find((s) => s.field === field)
    return sortField?.order ?? null
  }

  /**
   * 检查字段是否在排序列表中
   */
  const isFieldSorted = (field: string): boolean => {
    return sortFields.value.some((s) => s.field === field)
  }

  /**
   * 获取排序字段列表（用于API请求）
   */
  const getSortFields = computed(() => sortFields.value)

  /**
   * 设置排序字段
   */
  const setSortFields = (fields: SortField[]) => {
    sortFields.value = [...fields]
  }

  return {
    sortFields,
    handleHeaderClick,
    getSortOrder,
    isFieldSorted,
    getSortFields,
    setSortFields,
    isSorting,
    releaseSortLock,
    getAbortSignal,
  }
}
