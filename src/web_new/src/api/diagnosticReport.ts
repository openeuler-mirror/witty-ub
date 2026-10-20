import { request, apiBase } from './http'

export type DiagnosticReportItem = {
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
    page_cnt: params.pageCnt ?? 20,
  }
  if (params.kbId) body.kb_id = params.kbId
  return request<DiagnosticReportList>('/diagnostic_report/list', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// 报告是自包含 HTML，走 Nginx 白名单直开新窗口（地址可分享）
export const diagnosticReportHtmlUrl = (reportId: string) =>
  `${apiBase}/diagnostic_report/${encodeURIComponent(reportId)}/html`
