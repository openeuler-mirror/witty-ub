/** Display asset timestamps in the timezone of the machine running the browser. */
export const displayServerTime = (raw: string | undefined | null): string => {
  if (!raw) return '-'
  const match = raw
    .trim()
    .match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?$/)
  if (!match) return raw
  // Legacy responses have no offset, so their source timezone is unknown.
  if (!match[3]) return `${match[1]} ${match[2]}`
  const date = new Date(raw.trim().replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return raw
  const pad = (value: number) => String(value).padStart(2, '0')
  // Use the offset at this timestamp so historical daylight saving is correct.
  const offset = -date.getTimezoneOffset()
  const hours = Math.floor(Math.abs(offset) / 60)
  const minutes = Math.abs(offset) % 60
  const timezone = `UTC${offset >= 0 ? '+' : '-'}${hours}${minutes ? `:${pad(minutes)}` : ''}`
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())} (${timezone})`
}

/** Convert a browser-local asset date filter to an absolute UTC timestamp. */
export const formatAssetTimeFilter = (value: string): string | undefined => {
  if (!value) return undefined
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) throw new Error('创建时间格式无效')
  return date.toISOString()
}
