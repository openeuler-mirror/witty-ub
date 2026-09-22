import { request } from './http'
import type { LogKnowledge } from '../types'

export const listLogKbs = async (pageCnt = 50, pageNum = 1) =>
  request<{ total: number; kbs: LogKnowledge[] }>('/log_kb/list', {
    method: 'POST',
    body: JSON.stringify({
      created_sorted_desc: true,
      page_cnt: pageCnt,
      page_num: pageNum,
    }),
  })

export const listAllLogKbs = async () => {
  const first = await listLogKbs(50, 1)
  const total = first.total ?? 0
  const all = total > (first.kbs?.length ?? 0) ? await listLogKbs(total, 1) : first
  return (all.kbs ?? []).filter((asset) => asset.existed_status !== false)
}

export const getLogKb = (kbId: string) => request<{ kb: LogKnowledge | null }>(`/log_kb/${kbId}`)

export const createLogKb = (name: string, description: string) =>
  request('/log_kb', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  })

export const updateLogKb = (kbId: string, name: string, description: string) =>
  request(`/log_kb/${kbId}`, {
    method: 'PUT',
    body: JSON.stringify({ name, description }),
  })

export const deleteLogKb = (kbId: string) =>
  request<{ kb_id: string | null }>(`/log_kb/${kbId}`, { method: 'DELETE' })
