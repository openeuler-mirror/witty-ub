import rawDiagnosisConfig from '../../../../config/diagnosis_config.toml'
import { request } from './http'
import type { LogKnowledge } from '../types'

const toml = rawDiagnosisConfig as any

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

export type DiagnosisConfigForm = {
  logFilenamePattern: Record<DiagnosisPatternKey, string[]>
  logAnalyzerParams: Record<DiagnosisThresholdKey, number> & {
    slidingWindowPairs: { size: number; step: number }[]
    zone_anomaly_density_threshold: number
  }
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
  { key: 'c2w_p99_threshold_ms', label: 'C2W 时延 P99 阘值', description: 'Client 到 Worker' },
  { key: 'w2w_p99_threshold_ms', label: 'W2W 时延 P99 阘值', description: 'Worker 间调用' },
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

export const defaultDiagnosisConfig = (): DiagnosisConfigForm => ({
  logFilenamePattern: {
    ds_client_access_log_file: [...toml.log_filename_pattern.ds_client_access_log_file],
    ds_client_info_log_file: [...toml.log_filename_pattern.ds_client_info_log_file],
    ds_worker_access_log_file: [...toml.log_filename_pattern.ds_worker_access_log_file],
    ds_worker_info_log_file: [...toml.log_filename_pattern.ds_worker_info_log_file],
    resource_log_file: [...toml.log_filename_pattern.resource_log_file],
  },
  logAnalyzerParams: {
    total_p99_threshold_ms: toml.log_analyzer_params.total_p99_threshold_ms,
    c2w_p99_threshold_ms: toml.log_analyzer_params.c2w_p99_threshold_ms,
    w2w_p99_threshold_ms: toml.log_analyzer_params.w2w_p99_threshold_ms,
    urma_link_p99_threshold_ms: toml.log_analyzer_params.urma_link_p99_threshold_ms,
    query_meta_p99_threshold_ms: toml.log_analyzer_params.query_meta_p99_threshold_ms,
    total_p9999_threshold_ms: toml.log_analyzer_params.total_p9999_threshold_ms,
    total_pmax_threshold_ms: toml.log_analyzer_params.total_pmax_threshold_ms,
    total_ave_threshold_ms: toml.log_analyzer_params.total_ave_threshold_ms,
    slidingWindowPairs: toml.log_analyzer_params.sliding_window_sizes.map(
      (size: number, index: number) => ({
        size,
        step: toml.log_analyzer_params.sliding_window_steps[index] ?? size,
      }),
    ),
    zone_anomaly_density_threshold: toml.log_analyzer_params.zone_anomaly_density_threshold,
  },
})

type DiagnosisConfigApiModel = {
  log_filename_pattern: Record<DiagnosisPatternKey, string[]>
  log_analyzer_params: Record<DiagnosisThresholdKey, number> & {
    sliding_window_sizes: number[]
    sliding_window_steps: number[]
    zone_anomaly_density_threshold: number
  }
}

export const fromDiagnosisConfigApi = (config: DiagnosisConfigApiModel): DiagnosisConfigForm => ({
  logFilenamePattern: {
    ds_client_access_log_file: [...config.log_filename_pattern.ds_client_access_log_file],
    ds_client_info_log_file: [...config.log_filename_pattern.ds_client_info_log_file],
    ds_worker_access_log_file: [...config.log_filename_pattern.ds_worker_access_log_file],
    ds_worker_info_log_file: [...config.log_filename_pattern.ds_worker_info_log_file],
    resource_log_file: [...config.log_filename_pattern.resource_log_file],
  },
  logAnalyzerParams: {
    total_p99_threshold_ms: config.log_analyzer_params.total_p99_threshold_ms,
    c2w_p99_threshold_ms: config.log_analyzer_params.c2w_p99_threshold_ms,
    w2w_p99_threshold_ms: config.log_analyzer_params.w2w_p99_threshold_ms,
    urma_link_p99_threshold_ms: config.log_analyzer_params.urma_link_p99_threshold_ms,
    query_meta_p99_threshold_ms: config.log_analyzer_params.query_meta_p99_threshold_ms,
    total_p9999_threshold_ms: config.log_analyzer_params.total_p9999_threshold_ms,
    total_pmax_threshold_ms: config.log_analyzer_params.total_pmax_threshold_ms,
    total_ave_threshold_ms: config.log_analyzer_params.total_ave_threshold_ms,
    slidingWindowPairs: config.log_analyzer_params.sliding_window_sizes.map((size, index) => ({
      size,
      step: config.log_analyzer_params.sliding_window_steps[index] ?? size,
    })),
    zone_anomaly_density_threshold: config.log_analyzer_params.zone_anomaly_density_threshold,
  },
})

export const toDiagnosisConfigApi = (form: DiagnosisConfigForm): DiagnosisConfigApiModel => ({
  log_filename_pattern: {
    ds_client_access_log_file: [...form.logFilenamePattern.ds_client_access_log_file],
    ds_client_info_log_file: [...form.logFilenamePattern.ds_client_info_log_file],
    ds_worker_access_log_file: [...form.logFilenamePattern.ds_worker_access_log_file],
    ds_worker_info_log_file: [...form.logFilenamePattern.ds_worker_info_log_file],
    resource_log_file: [...form.logFilenamePattern.resource_log_file],
  },
  log_analyzer_params: {
    total_p99_threshold_ms: Number(form.logAnalyzerParams.total_p99_threshold_ms),
    c2w_p99_threshold_ms: Number(form.logAnalyzerParams.c2w_p99_threshold_ms),
    w2w_p99_threshold_ms: Number(form.logAnalyzerParams.w2w_p99_threshold_ms),
    urma_link_p99_threshold_ms: Number(form.logAnalyzerParams.urma_link_p99_threshold_ms),
    query_meta_p99_threshold_ms: Number(form.logAnalyzerParams.query_meta_p99_threshold_ms),
    total_p9999_threshold_ms: Number(form.logAnalyzerParams.total_p9999_threshold_ms),
    total_pmax_threshold_ms: Number(form.logAnalyzerParams.total_pmax_threshold_ms),
    total_ave_threshold_ms: Number(form.logAnalyzerParams.total_ave_threshold_ms),
    sliding_window_sizes: form.logAnalyzerParams.slidingWindowPairs.map((pair) =>
      Number(pair.size),
    ),
    sliding_window_steps: form.logAnalyzerParams.slidingWindowPairs.map((pair) =>
      Number(pair.step),
    ),
    zone_anomaly_density_threshold: Number(form.logAnalyzerParams.zone_anomaly_density_threshold),
  },
})

const configPath = (assetId: string) =>
  `/diagnosis_config/${encodeURIComponent(assetId)}?log_type=KVCache`

export const fetchDiagnosisConfig = async (assetId: string): Promise<DiagnosisConfigForm> => {
  const result = await request<{ config: DiagnosisConfigApiModel }>(configPath(assetId))
  return fromDiagnosisConfigApi(result.config)
}

export const saveDiagnosisConfig = async (
  assetId: string,
  form: DiagnosisConfigForm,
): Promise<DiagnosisConfigForm> => {
  const result = await request<{ config: DiagnosisConfigApiModel }>(configPath(assetId), {
    method: 'PUT',
    body: JSON.stringify(toDiagnosisConfigApi(form)),
  })
  return fromDiagnosisConfigApi(result.config)
}

export const resetDiagnosisConfig = async (assetId: string): Promise<DiagnosisConfigForm> => {
  const result = await request<{ config: DiagnosisConfigApiModel }>(
    `/diagnosis_config/${encodeURIComponent(assetId)}/reset?log_type=KVCache`,
    { method: 'POST' },
  )
  return fromDiagnosisConfigApi(result.config)
}

// 从其他资产库导入：拉取全部资产（分页取全），排除当前资产
export const listImportAssets = async (currentAssetId: string): Promise<LogKnowledge[]> => {
  const pageSize = 100
  let pageNum = 1
  let total = 0
  const all: LogKnowledge[] = []
  do {
    const result = await request<{ total: number; kbs: LogKnowledge[] }>('/log_kb/list', {
      method: 'POST',
      body: JSON.stringify({ page_cnt: pageSize, page_num: pageNum, created_sorted_desc: true }),
    })
    total = result.total ?? 0
    const page = result.kbs ?? []
    all.push(...page)
    pageNum += 1
    if (page.length === 0) break
  } while (all.length < total)
  return all.filter((asset) => asset.existed_status !== false && asset.id !== currentAssetId)
}
