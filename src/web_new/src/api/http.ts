import type { ApiResponse } from '../types'

export const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

export const request = async <T>(path: string, init: RequestInit = {}): Promise<T> => {
  const hasBody = !!init.body
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })
  const data = (await response.json().catch(() => null)) as ApiResponse<T> | null
  if (!response.ok || !data) {
    throw new Error(data?.message || `请求失败：${response.status}`)
  }
  if (typeof data.code === 'number' && data.code !== 200) {
    throw new Error(data.message || '接口返回异常')
  }
  return (data.result ?? data.data ?? data) as T
}
