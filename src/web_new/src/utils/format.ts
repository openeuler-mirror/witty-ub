export const errorText = (error: unknown) =>
  error instanceof Error ? error.message : '操作失败，请稍后重试'

export const clampProgress = (value: number) => Math.min(100, Math.max(0, value))

export const formatTime = (value?: string | null) => {
  if (!value) return '—'
  return value.replace('T', ' ').slice(0, 19)
}

export const toDatetimeString = (value: string) => {
  if (!value) return undefined
  return `${value.replace('T', ' ')}:00`
}

export const paginate = <T>(list: T[], page: number, pageSize: number): T[] =>
  list.slice((page - 1) * pageSize, page * pageSize)

export const normalizeTraceOperation = (operation?: string | null) => {
  const normalized = String(operation || '')
    .trim()
    .toUpperCase()
  if (normalized.includes('GET')) return 'GET'
  if (normalized.includes('SET') || normalized.includes('CREATE') || normalized.includes('PUBLISH'))
    return 'SET'
  return '-'
}

export const extractArray = <T>(payload: unknown, keys: string[]): T[] => {
  if (Array.isArray(payload)) return payload as T[]
  if (!payload || typeof payload !== 'object') return []
  const record = payload as Record<string, unknown>
  for (const key of keys) {
    if (Array.isArray(record[key])) return record[key] as T[]
  }
  return []
}

export const normalizeTraceRow = (row: any) => {
  const totalUs =
    row.total_latency_us != null ? row.total_latency_us : (row.total_latency ?? 0) * 1000
  return {
    ...row,
    total_latency_us: totalUs,
    timestamp: row.timestamp ?? row.created_at,
  }
}

export const formatFullTimeLabel = (date: Date) => {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

export const toQueryString = (params: Record<string, string | number | undefined>) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value))
  })
  return search.toString()
}

// trace_failure_event.status_code 为 access 口径数组；兼容标量；过滤 '0'/空
export const normalizeFaultCodes = (raw: unknown): string[] => {
  const list = Array.isArray(raw) ? raw : raw == null || raw === '' ? [] : [raw]
  return [
    ...new Set(list.map((code) => String(code).trim()).filter((code) => code && code !== '0')),
  ]
}

export const normalizeFailureModeErrorCode = (rawErrorCode: string | number | null | undefined) => {
  if (rawErrorCode === null || rawErrorCode === undefined) return ''
  const errorCode = String(rawErrorCode).trim()
  if (!errorCode || ['NULL', 'NULLPTR', 'NONE', 'N/A', 'NA', '-'].includes(errorCode.toUpperCase()))
    return ''
  if (/^K_OK\(\s*\+?0+\s*\)$/i.test(errorCode)) return '0'
  const numericSuffix = errorCode.match(/\(\s*([-+]?\d+)\s*\)\s*$/)?.[1]
  if (numericSuffix) return Number(numericSuffix) === 0 ? '' : numericSuffix
  if (/^[-+]?\d+$/.test(errorCode)) return ''
  return errorCode
}

// 进程级 FATAL 故障的 error_code 为 null，但属于 access 故障，统一展示为 "FATAL"
export const failureModeDisplayCode = (
  mode?: { error_code?: string | number | null; name?: string } | null,
) => {
  if (!mode) return ''
  const errorCode = normalizeFailureModeErrorCode(mode.error_code)
  if (errorCode) return errorCode
  return (mode.name ?? '').includes('FATAL') ? 'FATAL' : ''
}

// 图表横坐标显示完整日期
export const formatChartTs = (ts: string): string => {
  const match = String(ts).match(/(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/)
  return match ? `${match[1]} ${match[2]}` : String(ts)
}

// 后端约定 "YYYY-MM-DD HH:mm:ss" 与 epoch ms 之间的显式时区转换，禁止浏览器隐式解析
export const tsToEpochMs = (ts: string): number => {
  const match = String(ts).match(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})/)
  if (!match) return NaN
  const [, y = '1970', mo = '01', d = '01', h = '00', mi = '00', s = '00'] = match
  return new Date(+y, +mo - 1, +d, +h, +mi, +s).getTime()
}

export const epochMsToTs = (ms: number): string => formatFullTimeLabel(new Date(ms))
