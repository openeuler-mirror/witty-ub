import { request } from './http'

export type DiagCaseVerification = {
  method?: string | null
  observed_result?: string | null
  closed_loop?: boolean
  verified_at?: string | null
  verified_by?: string | null
  notes?: string | null
}

export type DiagCaseVerificationHistory = {
  revision_from?: number
  revision_to?: number
  verified_by?: string | null
  verified_at?: string | null
  method?: string | null
  observed_result?: string | null
  closed_loop?: boolean
}

export type DiagCase = {
  id: string
  case_no: string | null
  status: string
  revision: number
  created_by: string | null
  confirmed_by: string | null
  confirmed_at: string | null
  title: string | null
  report_id: string | null
  source_fault_id: string | null
  source_fault_hash: string | null
  first_level_label: string | null
  second_level_label: string | null
  label_taxonomy_version: string | null
  log_type: string | null
  kb_id: string | null
  kb_name: string | null
  operation: string | null
  fault_type: string
  status_codes: string[]
  failure_mode_ids: string[]
  log_keywords: string[]
  confidence: number
  symptom_summary: string
  root_cause_summary: string
  root_cause_detail: string | null
  evidence_json: Array<Record<string, unknown>>
  counter_evidence_json: Array<Record<string, unknown>>
  remediation_json: Array<Record<string, unknown>>
  verification_json: DiagCaseVerification | null
  verification_history_json: DiagCaseVerificationHistory[]
  relations_json: Array<Record<string, unknown>>
  created_at: string
  updated_at: string
}

export type SourceReport = {
  status: string
  report_id: string | null
  source_fault_id: string | null
  report_title: string | null
  source_fault_title: string | null
  review_status: string | null
  classification_status: string
  current_first_level_label: string | null
  current_second_level_label: string | null
  get_report: string | null
  get_fault: string | null
}

export type DiagCaseDetail = {
  case: DiagCase | null
  source_report: SourceReport | null
}

export type DiagCaseMatch = {
  case: DiagCase
  match_score: number
  score_norm: number
  source_report?: SourceReport | null
}

export type DiagCaseSearchResult = {
  total: number
  matches: DiagCaseMatch[]
}

export type DiagCaseSearchParams = {
  pageNum?: number
  pageCnt?: number
  firstLevelLabel?: string | null
  secondLevelLabel?: string | null
  unclassifiedOnly?: boolean
  includeStatus?: string[]
}

export const searchDiagCases = (params: DiagCaseSearchParams = {}) => {
  const body: Record<string, unknown> = {
    include_status: params.includeStatus ?? ['draft', 'confirmed', 'archived'],
    page_num: params.pageNum ?? 1,
    page_cnt: params.pageCnt ?? 50,
  }
  if (params.firstLevelLabel) body.first_level_label = params.firstLevelLabel
  if (params.secondLevelLabel) body.second_level_label = params.secondLevelLabel
  if (params.unclassifiedOnly) body.unclassified_only = true
  return request<DiagCaseSearchResult>('/diag_case_library/search', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export const fetchDiagCase = (caseId: string) =>
  request<DiagCaseDetail>(`/diag_case_library/${encodeURIComponent(caseId)}`)

export const confirmDiagCase = (caseId: string, confirmedBy: string) =>
  request<DiagCaseDetail>(
    `/diag_case_library/${encodeURIComponent(caseId)}/confirm`,
    {
      method: 'POST',
      body: JSON.stringify({ confirmed_by: confirmedBy }),
    },
  )

export const updateDiagCaseVerification = (
  caseId: string,
  verification: DiagCaseVerification,
  expectedRevision: number,
) =>
  request<DiagCaseDetail>(`/diag_case_library/${encodeURIComponent(caseId)}`, {
    method: 'PATCH',
    body: JSON.stringify({
      verification_json: verification,
      expected_revision: expectedRevision,
    }),
  })

export const archiveDiagCase = (caseId: string, archivedBy: string, reason: string) =>
  request<DiagCaseDetail>(
    `/diag_case_library/${encodeURIComponent(caseId)}/archive`,
    {
      method: 'POST',
      body: JSON.stringify({ archived_by: archivedBy, archive_reason: reason }),
    },
  )
