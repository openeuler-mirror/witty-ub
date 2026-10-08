/** 后端时间统一为「服务器本地墙钟、无 offset」的 YYYY-MM-DD HH:MM:SS[.mmm]。 */
export const displayServerTime = (raw: string | undefined | null): string => {
  if (!raw) return '-'
  // Do not convert through Date: that would replace the server timezone with
  // the browser timezone and hide a server timezone change after page refresh.
  // offset 后缀已不再下发，正则仍保留以兼容历史数据。
  const match = raw.trim().match(
    /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$/,
  )
  return match ? `${match[1]} ${match[2]}` : raw
}

/** Convert a browser-local asset date filter to an absolute UTC timestamp. */
export const formatAssetTimeFilter = (value: string): string | undefined => {
  if (!value) return undefined
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) throw new Error('创建时间格式无效')
  return date.toISOString()
}
