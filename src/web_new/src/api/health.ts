import { request } from './http'

// /health_check 在磁盘降级（warning / critical）时仍返回 200 + status=ok，
// 只把 writable 置 false；数据库不可用时返回 503，由调用方按「上一次结论」处理。
export type ServiceHealth = {
  status?: string
  writable?: boolean
  disk_mode?: string
  free_disk_bytes?: number
  minimum_free_disk_bytes?: number
  critical_free_disk_bytes?: number
  recovery_free_disk_bytes?: number
  message?: string | null
}

export const getServiceHealth = () => request<ServiceHealth>('/health_check')
