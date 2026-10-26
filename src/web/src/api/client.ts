export const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

type ApiEnvelope<T> = {
  code?: number
  message?: string
  result?: T
  data?: T
}

export const request = async <T>(path: string, init: RequestInit = {}): Promise<T> => {
  const hasBody = !!init.body
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })
  const payload = (await response.json().catch(() => null)) as ApiEnvelope<T> | null
  if (!response.ok || !payload) {
    throw new Error(payload?.message || `请求失败：${response.status}`)
  }
  if (typeof payload.code === 'number' && payload.code !== 200) {
    throw new Error(payload.message || '接口返回异常')
  }
  return (payload.result ?? payload.data ?? payload) as T
}
