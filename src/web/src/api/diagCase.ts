import { apiBase, request } from './client'

export type ReportClassification = {
  first_level_label?: string | null
  second_level_label?: string | null
  status?: string
  error?: string | null
  taxonomy_version?: string | null
  snapshot_hash?: string | null
}

export type ReportFaultSummary = {
  fault_id?: string | null
  title?: string | null
  status?: string | null
  category?: string | null
  confidence?: number | null
  classification: ReportClassification
  indexable: boolean
  synthetic: boolean
  excluded: boolean
}

export type ReportCaseRef = {
  case_id: string
  case_no?: string | null
  source_fault_id?: string | null
  source_fault_hash?: string | null
  is_current_version: boolean
  status: string
  revision: number
  verification: string
  binding_status: string
  first_level_label?: string | null
  second_level_label?: string | null
  verification_method?: string | null
  observed_result?: string | null
  closed_loop: boolean
  verified_by?: string | null
  verified_at?: string | null
}

export type ReportItem = {
  report_id: string
  kb_id?: string | null
  kb_name?: string | null
  title?: string | null
  generated_at?: string | null
  operation?: string | null
  has_sidecar?: boolean
  review_status?: string | null
  current_sidecar_hash?: string | null
  review_confirmed_by?: string | null
  review_confirmed_at?: string | null
  case_refs?: ReportCaseRef[]
  fault_summaries?: ReportFaultSummary[]
}

export type ReportDetail = {
  report: ReportItem
  data?: Record<string, unknown> | null
}

export type ReportCasePreview = {
  report_id: string
  source_fault_id: string
  expected_sidecar_hash: string
  source_fault_hash: string
  classification: ReportClassification
  draft: Record<string, unknown>
  missing_fields: string[]
  ready: boolean
}

export type DiagCaseVerification = {
  method?: string | null
  observed_result?: string | null
  closed_loop?: boolean
  verified_at?: string | null
  verified_by?: string | null
  notes?: string | null
}

export type DiagCase = {
  id: string
  case_no?: string | null
  status: string
  revision: number
  created_by?: string | null
  confirmed_by?: string | null
  confirmed_at?: string | null
  title?: string | null
  report_id?: string | null
  source_fault_id?: string | null
  source_fault_hash?: string | null
  first_level_label?: string | null
  second_level_label?: string | null
  label_taxonomy_version?: string | null
  log_type?: string | null
  kb_id?: string | null
  kb_name?: string | null
  operation?: string | null
  fault_type?: string
  status_codes?: string[]
  failure_mode_ids?: string[]
  log_keywords?: string[]
  confidence?: number
  symptom_summary: string
  root_cause_summary: string
  root_cause_detail?: string | null
  evidence_json?: Array<Record<string, unknown>>
  remediation_json?: Array<Record<string, unknown>>
  verification_json?: DiagCaseVerification | null
  verification_history_json?: Array<Record<string, unknown>>
  updated_at: string
}

export type SourceReport = {
  status: string
  report_id?: string | null
  source_fault_id?: string | null
  report_title?: string | null
  source_fault_title?: string | null
  review_status?: string | null
  classification_status?: string
  get_report?: string | null
}

export type DiagCaseDetail = {
  case: DiagCase | null
  source_report?: SourceReport | null
}

export type DiagCaseSearchResult = {
  total: number
  matches: Array<{
    case: DiagCase
    match_score?: number
    score_norm?: number
    source_report?: SourceReport | null
  }>
}

export type LabelTaxonomy = {
  version: string
  first_level_labels: string[]
  pairs: Array<{ first_level_label: string; second_level_labels: string[] }>
}

export const fetchReportDetail = (reportId: string) =>
  request<ReportDetail>(`/diagnostic_report/${encodeURIComponent(reportId)}`)

export const confirmReport = (
  reportId: string,
  expectedSidecarHash: string,
  reviewedBy: string,
) =>
  request<ReportItem>(`/diagnostic_report/${encodeURIComponent(reportId)}/confirm`, {
    method: 'POST',
    body: JSON.stringify({
      expected_sidecar_hash: expectedSidecarHash,
      reviewed_by: reviewedBy,
    }),
  })

export const previewReportCase = (reportId: string, faultId: string) =>
  request<ReportCasePreview>(
    `/diagnostic_report/${encodeURIComponent(reportId)}/faults/${encodeURIComponent(faultId)}/case_preview`,
  )

export const createReportCase = (
  reportId: string,
  faultId: string,
  expectedSidecarHash: string,
  reviewedBy: string,
) =>
  request<{ case_id?: string | null; case_no?: string | null; missing_fields: string[] }>(
    `/diagnostic_report/${encodeURIComponent(reportId)}/faults/${encodeURIComponent(faultId)}/case`,
    {
      method: 'POST',
      body: JSON.stringify({
        expected_sidecar_hash: expectedSidecarHash,
        reviewed_by: reviewedBy,
      }),
    },
  )

export const fetchLabelTaxonomy = () => request<LabelTaxonomy>('/diagnostic_report/labels')

export const searchDiagCases = (body: Record<string, unknown>) =>
  request<DiagCaseSearchResult>('/diag_case_library/search', {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const fetchDiagCase = (caseId: string) =>
  request<DiagCaseDetail>(`/diag_case_library/${encodeURIComponent(caseId)}`)

export const confirmDiagCase = (caseId: string, confirmedBy: string) =>
  request<DiagCaseDetail>(`/diag_case_library/${encodeURIComponent(caseId)}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ confirmed_by: confirmedBy }),
  })

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

export const reportHtmlUrl = (reportId: string) =>
  `${apiBase}/diagnostic_report/${encodeURIComponent(reportId)}/html`

export { apiBase }
