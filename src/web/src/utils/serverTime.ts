/** Asset API timestamps already carry the server's current local time and offset. */
export const displayServerTime = (raw: string | undefined | null): string => {
  if (!raw) return '-'
  // Do not convert through Date: that would replace the server timezone with
  // the browser timezone and hide a server timezone change after page refresh.
  const match = raw.trim().match(
    /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$/,
  )
  return match ? `${match[1]} ${match[2]}` : raw
}
