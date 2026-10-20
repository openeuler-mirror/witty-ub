import { request, apiBase } from './http'

export type CaseCategory = {
  id: string
  name: string
  description: string
  case_count: number
  types: CaseType[]
  /** 未分类兜底组：无元数据 id */
  is_uncategorized?: boolean
}

export type CaseType = {
  id?: string
  name: string
  description: string
  case_count: number
}

export type CaseRecord = {
  id: string
  kb_id?: string
  case_category?: string
  root_cause_type: string
  fault_category?: string
  description?: string
  task_ids?: string[]
  task_names?: string[]
  log_file_id?: string
  log_file_name?: string
  attachment_path?: string
  created_at?: string
  features?: {
    latency?: {
      timeout_segments?: string[]
      p99_p50_ratio?: number
      pod_concentration?: string
    }
    connectivity?: {
      failure_mode_dist?: Record<string, number>
      spatial_pod?: { scope?: string }
      spatial_host?: { scope?: string }
    }
    summary?: {
      anomalous_event_count?: number
      failure_event_count?: number
      total_parse_result_count?: number
    }
  }
}

export const fetchCases = () => request<CaseRecord[]>('/case_library/list')

export const fetchCaseCategories = () => request<CaseCategory[]>('/case_library/categories')

export const updateCase = (caseId: string, patch: { caseCategory?: string; rootCauseType?: string }) =>
  request<CaseRecord>(`/case_library/${caseId}`, {
    method: 'PUT',
    body: JSON.stringify({
      case_category: patch.caseCategory ?? null,
      root_cause_type: patch.rootCauseType ?? null,
    }),
  })

export const deleteCase = (caseId: string) =>
  request<null>(`/case_library/${caseId}`, { method: 'DELETE' })

export const createCategory = (name: string, description = '') =>
  request<CaseCategory>('/case_library/categories', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  })

export const updateCategory = (categoryId: string, patch: { name?: string; description?: string }) =>
  request<CaseCategory>(`/case_library/categories/${categoryId}`, {
    method: 'PUT',
    body: JSON.stringify(patch),
  })

export const deleteCategory = (categoryId: string, recursive: boolean) =>
  request<null>(`/case_library/categories/${categoryId}?recursive=${recursive}`, {
    method: 'DELETE',
  })

export const createType = (categoryId: string, name: string, description = '') =>
  request<CaseType>('/case_library/types', {
    method: 'POST',
    body: JSON.stringify({ category_id: categoryId, name, description }),
  })

export const updateType = (typeId: string, patch: { name?: string; description?: string }) =>
  request<CaseType>(`/case_library/types/${typeId}`, {
    method: 'PUT',
    body: JSON.stringify(patch),
  })

export const deleteType = (typeId: string, recursive: boolean) =>
  request<null>(`/case_library/types/${typeId}?recursive=${recursive}`, { method: 'DELETE' })

export const caseAttachmentUrl = (caseId: string) =>
  `${apiBase}/case_library/attachment/${encodeURIComponent(caseId)}`
