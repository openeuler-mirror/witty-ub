import { request, apiBase } from './http'
import type { DiagCaseDetail } from './diagCaseLibrary'
import type { DocumentClassification, ImportBatch, ImportOptions, PathImportInput } from '../utils/caseWorkflow'

export type DiagnosticReportItem = {
  classifications?: DocumentClassification[]
  report_id: string
  kb_id: string | null
  kb_name: string | null
  title: string | null
  generated_at: string | null
  operation: string | null
  time_range_start: string | null
  time_range_end: string | null
  fault_count: number | null
  file_name: string
  file_size: number
  has_sidecar: boolean
  index_status: string
  index_error: string | null
  status_counts: Record<string, number>
  indexable_fault_count: number | null
  confirmed_fault_count: number | null
  case_count: number
  verified_case_count: number
  validation_status?: 'pending' | 'partial' | 'validated' | 'unavailable'
  validated_fault_count?: number
  report_available: boolean
  review_status: string
  current_sidecar_hash: string | null
  review_confirmed_by: string | null
  review_confirmed_at: string | null
  review_confirmation_source: string | null
  imported: boolean
  source_name?: string | null
}

export type ReportClassification = {
  first_level_label: string | null
  second_level_label: string | null
  status: string
  error: string | null
  taxonomy_version: string | null
  snapshot_hash: string | null
}

export type ReportFaultSummary = {
  fault_id: string | null
  title: string | null
  status: string | null
  category: string | null
  confidence: number | null
  classification: ReportClassification
  indexable: boolean
  synthetic: boolean
  excluded: boolean
}

export type ReportCaseRef = {
  case_id: string
  case_no: string | null
  source_fault_id: string | null
  source_fault_hash: string | null
  is_current_version: boolean
  status: string
  revision: number
  verification: string
  binding_status: string
  first_level_label: string | null
  second_level_label: string | null
  verification_method: string | null
  observed_result: string | null
  closed_loop: boolean
  verified_by: string | null
  verified_at: string | null
}

export type DiagnosticReportDetail = DiagnosticReportItem & {
  case_refs: ReportCaseRef[]
  fault_summaries: ReportFaultSummary[]
}

export type DiagnosticReportDetailResult = {
  report: DiagnosticReportDetail
  data: Record<string, unknown> | null
}

export type DiagnosticReportFaultResult = {
  report: DiagnosticReportDetail
  fault: Record<string, unknown>
  classification: ReportClassification
  case_refs: ReportCaseRef[]
}

export type ReportLabelPair = {
  first_level_label: string
  second_level_labels: string[]
}

export type ReportLabelTaxonomy = {
  version: string
  first_level_labels: string[]
  pairs: ReportLabelPair[]
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

export type CreateCaseFromReportResult = {
  case_id: string | null
  case_no: string | null
  missing_fields: string[]
}

export type DiagnosticReportList = {
  total: number
  items: DiagnosticReportItem[]
}

export const fetchDiagnosticReports = async (params: {
  kbId?: string | null
  pageNum?: number
  pageCnt?: number
}): Promise<DiagnosticReportList> => {
  const body: { kb_id?: string; page_num: number; page_cnt: number } = {
    page_num: params.pageNum ?? 1,
    page_cnt: Math.min(params.pageCnt ?? 20, 100),
  }
  if (params.kbId) body.kb_id = params.kbId
  return request<DiagnosticReportList>('/diagnostic_report/list', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export const fetchDiagnosticReport = (reportId: string) =>
  request<DiagnosticReportDetailResult>(
    `/diagnostic_report/${encodeURIComponent(reportId)}`,
  )

export const verifyReportFault = (
  reportId: string,
  faultId: string,
  body: { expected_sidecar_hash: string; verified_by: string; observed_result: string; method?: string },
) =>
  request<DiagCaseDetail>(
    `/diagnostic_report/${encodeURIComponent(reportId)}/faults/${encodeURIComponent(faultId)}/verify`,
    { method: 'POST', body: JSON.stringify(body) },
  )

export const importCases = (body: FormData) =>
  request<ImportBatch>('/diagnostic_report/import', { method: 'POST', body })

export const importReportPath = (body: PathImportInput) =>
  request<ImportBatch>('/diagnostic_report/import/path', { method: 'POST', body: JSON.stringify(body) })

export const fetchImportOptions = () =>
  request<ImportOptions>('/diagnostic_report/import/options')

export const fetchDiagnosticReportFault = (reportId: string, faultId: string) =>
  request<DiagnosticReportFaultResult>(
    `/diagnostic_report/${encodeURIComponent(reportId)}/faults/${encodeURIComponent(faultId)}`,
  )

export const confirmDiagnosticReport = (
  reportId: string,
  expectedSidecarHash: string,
  reviewedBy: string,
) =>
  request<DiagnosticReportDetail>(
    `/diagnostic_report/${encodeURIComponent(reportId)}/confirm`,
    {
      method: 'POST',
      body: JSON.stringify({
        expected_sidecar_hash: expectedSidecarHash,
        reviewed_by: reviewedBy,
      }),
    },
  )

export const fetchReportLabelTaxonomy = () =>
  request<ReportLabelTaxonomy>('/diagnostic_report/labels')

export const previewReportCase = (reportId: string, faultId: string) =>
  request<ReportCasePreview>(
    `/diagnostic_report/${encodeURIComponent(reportId)}/faults/${encodeURIComponent(faultId)}/case_preview`,
  )

export const createCaseFromReport = (
  reportId: string,
  faultId: string,
  expectedSidecarHash: string,
  reviewedBy: string,
) =>
  request<CreateCaseFromReportResult>(
    `/diagnostic_report/${encodeURIComponent(reportId)}/faults/${encodeURIComponent(faultId)}/case`,
    {
      method: 'POST',
      body: JSON.stringify({
        expected_sidecar_hash: expectedSidecarHash,
        reviewed_by: reviewedBy,
      }),
    },
  )

// 报告是自包含 HTML，走 Nginx 白名单直开新窗口（地址可分享）
export const diagnosticReportHtmlUrl = (reportId: string) =>
  `${apiBase}/diagnostic_report/${encodeURIComponent(reportId)}/html`
