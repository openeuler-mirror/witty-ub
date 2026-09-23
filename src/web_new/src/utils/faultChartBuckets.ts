/** 故障码时序图的取数上限：桶数不超过它时后端返回的就是精确计数，超出才保峰抽稀。 */
export const FAULT_CHART_MAX_POINTS = 5000

/** 抽稀下限：跨度极小时也要留出足够点位，避免后端因为 max_points 过小而截断。 */
const FAULT_CHART_MIN_POINTS = 100

/**
 * 按数据跨度与所选粒度算出精确取数所需的上限（桶数 = 跨度 / 桶宽）。
 * 跨度未知（首次取数）时用上限值，让后端决定是否抽稀。
 */
export const faultChartMaxPoints = (spanMs: number | null, scaleSeconds: number) => {
  if (!spanMs || spanMs <= 0 || !scaleSeconds || scaleSeconds <= 0) return FAULT_CHART_MAX_POINTS
  const buckets = Math.ceil(spanMs / (scaleSeconds * 1000))
  return Math.min(FAULT_CHART_MAX_POINTS, Math.max(FAULT_CHART_MIN_POINTS, buckets))
}
