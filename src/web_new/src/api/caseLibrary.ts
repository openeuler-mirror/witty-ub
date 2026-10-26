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

export const caseAttachmentUrl = (caseId: string) =>
  `${apiBase}/case_library/attachment/${encodeURIComponent(caseId)}`
