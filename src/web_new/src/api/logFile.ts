import { apiBase, request } from './http'
import type { ApiResponse, LogFileModel } from '../types'

export const listLogFiles = async (
  kbId: string,
  pageCnt: number,
  pageNum: number,
  extra: Record<string, unknown> = {},
) =>
  request<{ total: number; log_files: LogFileModel[] }>(`/log_file/list/${kbId}`, {
    method: 'POST',
    body: JSON.stringify({
      created_sorted_desc: true,
      page_cnt: pageCnt,
      page_num: pageNum,
      ...extra,
    }),
  })

export const listAllLogFiles = async (kbId: string) => {
  const first = await listLogFiles(kbId, 1, 1)
  const total = first.total ?? 0
  const all = total > 1 ? await listLogFiles(kbId, total, 1) : first
  return (all.log_files ?? []).filter((file) => file.existed_status !== false)
}

/** 上传结果：后端可能「受理了请求但一个文件都没登记」（非 zip 会被静默跳过），必须回传 id 列表。 */
export type UploadLogFilesOutcome = {
  logFileIds: string[]
  message: string
}

export const uploadLogFilesJson = async (
  kbId: string,
  configs: Array<Record<string, unknown>>,
  parseConfig?: Record<string, unknown>,
): Promise<UploadLogFilesOutcome> => {
  const body: Record<string, unknown> = { upload_log_file_configs: configs }
  if (parseConfig && Object.keys(parseConfig).length > 0) body.parse_config = parseConfig
  const result = await request<{ log_file_ids?: string[] }>(`/log_file/${kbId}`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return { logFileIds: result?.log_file_ids ?? [], message: '' }
}

export const uploadLogFilesMultipart = async (
  kbId: string,
  configs: Array<Record<string, unknown>>,
  files: File[],
  parseConfig?: Record<string, unknown>,
): Promise<UploadLogFilesOutcome> => {
  const formData = new FormData()
  formData.append('upload_log_file_configs', JSON.stringify(configs))
  if (parseConfig && Object.keys(parseConfig).length > 0) {
    formData.append('parse_config', JSON.stringify(parseConfig))
  }
  files.forEach((file) => formData.append('file', file))
  const response = await fetch(`${apiBase}/log_file/${kbId}`, {
    method: 'POST',
    body: formData,
  })
  const data = (await response.json().catch(() => null)) as ApiResponse<{
    log_file_ids?: string[]
  }> | null
  if (!response.ok || !data || (typeof data.code === 'number' && data.code !== 200)) {
    throw new Error(data?.message || `请求失败：${response.status}`)
  }
  const result = data.result ?? data.data
  return { logFileIds: result?.log_file_ids ?? [], message: data.message ?? '' }
}

export const runLogFile = (logFileId: string, run: boolean) =>
  request(`/log_file/run/${logFileId}?run=${run}`, { method: 'PUT' })

export const deleteLogFile = (logFileId: string) =>
  request(`/log_file/${logFileId}`, { method: 'DELETE' })

export const runBrpcDiagnosis = (logFileId: string, startTime: string) =>
  request(`/log_file/${logFileId}/brpc-diagnosis`, {
    method: 'POST',
    body: JSON.stringify({ start_time: startTime }),
  })
