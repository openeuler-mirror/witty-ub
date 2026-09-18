/**
 * 日志解析配置的字段定义与「界面可见性」策略（纯逻辑，不依赖 TOML / 网络，便于单测）。
 *
 * 可见性口径对齐当前后端实现（见 harness `references/decisions.md` 第 3 节）：
 * - 后端解析链路真正消费：`total_p99_threshold_ms`（外加 `log_filename_pattern.*`，见 `PATTERN_TYPES`）；
 * - 新版前端自己用（总览表 / 曲线异常标色）：P99.99 / Pmax / 均值；
 * - 其余（C2W / W2W / URMA 建链 / QueryMeta 四个阶段阈值、滑动窗口对、区间异常密度阈值）
 *   当前没有任何消费方 → 界面隐藏。字段仍随配置保存 / 导入导出，**后端实现对应判定后把键从
 *   `HIDDEN_*` 移出即可重新显示**。
 */

export type DiagnosisPatternKey =
  | 'ds_client_access_log_file'
  | 'ds_client_info_log_file'
  | 'ds_worker_access_log_file'
  | 'ds_worker_info_log_file'
  | 'resource_log_file'

export type DiagnosisThresholdKey =
  | 'total_p99_threshold_ms'
  | 'c2w_p99_threshold_ms'
  | 'w2w_p99_threshold_ms'
  | 'urma_link_p99_threshold_ms'
  | 'query_meta_p99_threshold_ms'
  | 'total_p9999_threshold_ms'
  | 'total_pmax_threshold_ms'
  | 'total_ave_threshold_ms'

export type SlidingWindowPair = { size: number; step: number }

export type AnalyzerParams = Record<DiagnosisThresholdKey, number> & {
  slidingWindowPairs: SlidingWindowPair[]
  zone_anomaly_density_threshold: number
}

export type DiagnosisConfigForm = {
  logFilenamePattern: Record<DiagnosisPatternKey, string[]>
  logAnalyzerParams: AnalyzerParams
}

export const PATTERN_TYPES: { key: DiagnosisPatternKey; label: string }[] = [
  { key: 'ds_client_access_log_file', label: '客户端接口日志' },
  { key: 'ds_client_info_log_file', label: 'SDK 客户端运行日志' },
  { key: 'ds_worker_access_log_file', label: 'Worker 接口日志' },
  { key: 'ds_worker_info_log_file', label: 'Worker 运行日志' },
  { key: 'resource_log_file', label: '资源日志' },
]

export const THRESHOLD_OPTIONS: {
  key: DiagnosisThresholdKey
  label: string
  description: string
}[] = [
  { key: 'total_p99_threshold_ms', label: '总时延 P99 阈值', description: '端到端总耗时' },
  { key: 'c2w_p99_threshold_ms', label: 'C2W 时延 P99 阈值', description: 'Client 到 Worker' },
  { key: 'w2w_p99_threshold_ms', label: 'W2W 时延 P99 阈值', description: 'Worker 间调用' },
  {
    key: 'urma_link_p99_threshold_ms',
    label: 'URMA 建链 P99 阈值',
    description: 'URMA 链路建立耗时',
  },
  {
    key: 'query_meta_p99_threshold_ms',
    label: 'QueryMeta 时延阈值',
    description: '查询元数据时延阈值',
  },
  {
    key: 'total_p9999_threshold_ms',
    label: '总时延 P9999 阈值',
    description: '端到端总耗时 99.99 百分位',
  },
  { key: 'total_pmax_threshold_ms', label: '总时延 Pmax 阈值', description: '端到端总耗时最大值' },
  { key: 'total_ave_threshold_ms', label: '总时延均值阈值', description: '端到端总耗时平均值' },
]

/** 后端解析 worker 判定时真的会读的阈值。 */
const BACKEND_CONSUMED_THRESHOLD_KEYS: DiagnosisThresholdKey[] = ['total_p99_threshold_ms']

/** 后端不读、由新版前端总览的异常标色使用的阈值。 */
const FRONTEND_CONSUMED_THRESHOLD_KEYS: DiagnosisThresholdKey[] = [
  'total_p9999_threshold_ms',
  'total_pmax_threshold_ms',
  'total_ave_threshold_ms',
]

/** 界面上可编辑的阈值 = 后端生效 + 前端标色。 */
export const EDITABLE_THRESHOLD_KEYS: DiagnosisThresholdKey[] = [
  ...BACKEND_CONSUMED_THRESHOLD_KEYS,
  ...FRONTEND_CONSUMED_THRESHOLD_KEYS,
]

export const EDITABLE_THRESHOLD_OPTIONS = THRESHOLD_OPTIONS.filter((option) =>
  EDITABLE_THRESHOLD_KEYS.includes(option.key),
)

/** 后端尚未消费、界面隐藏的阈值。 */
export const HIDDEN_THRESHOLD_KEYS: DiagnosisThresholdKey[] = THRESHOLD_OPTIONS.map(
  (option) => option.key,
).filter((key) => !EDITABLE_THRESHOLD_KEYS.includes(key))

const isPositiveDecimal = (value: unknown) =>
  /^[0-9]+(?:\.[0-9]+)?$/.test(String(value)) && Number(value) > 0 && Number.isFinite(Number(value))

const isPositiveInteger = (value: unknown) =>
  /^[0-9]+$/.test(String(value)) && Number(value) > 0 && Number.isFinite(Number(value))

/** 阈值合法性（上限与后端 `LatencyThreshold` 一致，避免保存被 422）。 */
export const isValidThresholdValue = (value: unknown): boolean =>
  isPositiveDecimal(value) && Number(value) <= 1000

const areHiddenParamsValid = (params: AnalyzerParams): boolean => {
  if (!HIDDEN_THRESHOLD_KEYS.every((key) => isValidThresholdValue(params[key]))) return false
  const pairsValid = params.slidingWindowPairs.every(
    ({ size, step }) =>
      isPositiveInteger(size) &&
      Number(size) <= 10000 &&
      isPositiveInteger(step) &&
      Number(step) <= 1000,
  )
  if (!pairsValid) return false
  const density = params.zone_anomaly_density_threshold
  return isPositiveDecimal(density) && Number(density) <= 1
}

/**
 * 隐藏字段保存时原样透传；只有值不合法（老配置 / 手工改过）才回落到默认配置 ——
 * 界面上已经没有这些输入框，不能让一个看不见的字段把整单保存卡成 422。
 */
export const sanitizeHiddenParams = (
  params: AnalyzerParams,
  defaults: AnalyzerParams,
): AnalyzerParams => {
  if (areHiddenParamsValid(params)) return params
  return {
    ...params,
    ...Object.fromEntries(HIDDEN_THRESHOLD_KEYS.map((key) => [key, defaults[key]])),
    slidingWindowPairs: defaults.slidingWindowPairs.map((pair) => ({ ...pair })),
    zone_anomaly_density_threshold: defaults.zone_anomaly_density_threshold,
  }
}

export const withSanitizedHiddenParams = (
  form: DiagnosisConfigForm,
  defaults: DiagnosisConfigForm,
): DiagnosisConfigForm => ({
  logFilenamePattern: form.logFilenamePattern,
  logAnalyzerParams: sanitizeHiddenParams(form.logAnalyzerParams, defaults.logAnalyzerParams),
})
