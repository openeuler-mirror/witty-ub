export type CaseScope = 'library' | 'pending'
export type KnowledgeView = 'documents' | 'library'
export type DocumentFilter = 'all' | 'pending'
export type DocumentValidation = {
  classifications?: DocumentClassification[]
  validation_status?: 'pending' | 'partial' | 'validated' | 'unavailable'
  validated_fault_count?: number
  indexable_fault_count?: number | null
  fault_count?: number | null
  verified_case_count?: number
  report_available?: boolean
}
export type DocumentClassification = {
  first_level_label: string | null
  second_level_label: string | null
  status: string
  error?: string | null
}
export const validDocumentClassifications = (report: DocumentValidation) =>
  (report.classifications ?? []).filter((item) =>
    (item.status === 'pair' && Boolean(item.first_level_label) && Boolean(item.second_level_label)) ||
    (item.status === 'first_only' && Boolean(item.first_level_label) && !item.second_level_label))

export const matchesDocumentClassification = (report: DocumentValidation, first = '', second = '') => {
  if (!first && !second) return true
  if (first === UNCLASSIFIED) return (report.classifications ?? []).some((item) =>
    item.status === 'empty' && !item.first_level_label && !item.second_level_label)
  return validDocumentClassifications(report).some((item) => matchesClassification(item, first, second))
}

export const documentClassificationText = (report: DocumentValidation) => {
  const labels = validDocumentClassifications(report)
    .map((item) => [item.first_level_label, item.second_level_label].filter(Boolean).join(' / '))
  if (matchesDocumentClassification(report, UNCLASSIFIED)) labels.push('未分类')
  const text = [...new Set(labels)].join('、')
  const abnormal = report.classifications?.some((item) => ['invalid', 'unavailable'].includes(item.status))
  return text ? `${text}${abnormal ? '（部分分类异常）' : ''}` : '⚠ 无有效分类'
}
export type ClassifiedCase = {
  id: string
  status: string
  first_level_label?: string | null
  second_level_label?: string | null
  verification_json?: { closed_loop?: boolean } | null
}
export type ClassificationSelection = { first: string; second: string; page: number }
export const UNCLASSIFIED = '__unclassified__'

export const belongsToScope = (item: ClassifiedCase, scope: CaseScope) =>
  scope === 'library'
    ? item.status === 'confirmed' && item.verification_json?.closed_loop === true
    : item.status === 'draft' ||
      (item.status === 'confirmed' && item.verification_json?.closed_loop !== true)

export const selectPrimary = (first: string): ClassificationSelection => ({
  first, second: '', page: 1,
})

export const populatedLabels = (taxonomy: string[], values: Array<string | null | undefined>) => {
  const populated = new Set(values.filter((label): label is string => Boolean(label)))
  return [...new Set([...taxonomy, ...populated])].filter((label) => populated.has(label))
}

export const caseOrigin = (item: { report_id?: string | null; confirmation_source?: string | null }) =>
  item.confirmation_source === 'import' ? '外部导入' : item.report_id ? '现场诊断' : '独立案例'

export const matchesClassification = (
  item: Pick<ClassifiedCase, 'first_level_label' | 'second_level_label'>,
  first: string,
  second = '',
) => {
  if (first === UNCLASSIFIED) return !item.first_level_label && !item.second_level_label
  return (!first || item.first_level_label === first) &&
    (!second || item.second_level_label === second)
}

const SOURCE_LABELS: Record<string, string> = {
    valid: '查看来源定界文档',
    stale: '来源定界文档已变化',
    deleted: '来源定界文档已删除',
    unavailable: '来源定界文档暂不可用',
    independent: '独立案例',
}
export const sourceReportLabel = (status?: string | null) =>
  SOURCE_LABELS[status ?? ''] ?? '无关联定界文档'

export const materialKey = (source: 'diagnosis' | 'legacy', id: string) => `${source}:${id}`

export const matchesKeywords = (query: string, values: Array<string | null | undefined>) => {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  const text = values.filter(Boolean).join(' ').toLocaleLowerCase()
  return terms.every((term) => text.includes(term))
}

export const caseRefsForFault = <T extends { source_fault_id?: string | null }>(refs: T[], faultId?: string | null) =>
  refs.filter((item) => (item.source_fault_id ?? null) === (faultId ?? null))

export const unmatchedCaseRefs = <T extends { source_fault_id?: string | null }>(
  refs: T[], faults: Array<{ fault_id?: string | null }>,
) => refs.filter((item) => !item.source_fault_id || !faults.some((fault) => fault.fault_id === item.source_fault_id))

export type VerifiableFault = { fault_id?: string | null; synthetic?: boolean; excluded?: boolean; status?: string | null }
export type VerifiedFaultRef = { source_fault_id?: string | null; is_current_version: boolean; status: string; closed_loop: boolean }
export const isFaultVerified = (fault: VerifiableFault, refs: VerifiedFaultRef[] = []) =>
  Boolean(fault.fault_id) && refs.some((item) => item.source_fault_id === fault.fault_id &&
    item.is_current_version && item.status === 'confirmed' && item.closed_loop)
export const canVerifyFault = (fault: VerifiableFault, refs: VerifiedFaultRef[] = []) =>
  Boolean(fault.fault_id) && !fault.synthetic && !fault.excluded && !isFaultVerified(fault, refs)

export const reportNeedsVerification = (report: DocumentValidation) => {
  if (report.validation_status) return ['pending', 'partial'].includes(report.validation_status)
  if (report.report_available === false) return false
  const expected = report.indexable_fault_count ?? report.fault_count
  return expected == null || (report.validated_fault_count ?? report.verified_case_count ?? 0) < expected
}

export const filterDocuments = <T extends DocumentValidation>(
  documents: T[], filter: DocumentFilter, first = '', second = '',
) => documents.filter((report) => (filter !== 'pending' || reportNeedsVerification(report)) &&
  matchesDocumentClassification(report, first, second))

export const documentProgress = (report: DocumentValidation) =>
  `${report.validated_fault_count ?? report.verified_case_count ?? 0}/${report.indexable_fault_count ?? report.fault_count ?? '—'}`

/** 历史案例的来源以是否真有任务为准：批量导入的数据集带 log_file_id 但没有 task_ids。 */
export const legacyCaseOrigin = (item: { task_ids?: string[] }) =>
  item.task_ids?.length ? '任务日志自动生成' : '历史文件案例'

type LegacyFeatureSource = {
  fault_category?: string | null
  description?: string | null
  log_file_name?: string | null
  task_ids?: string[] | null
  task_names?: string[] | null
  features?: {
    latency?: {
      timeout_segments?: unknown[]
      p99_p50_ratio?: number | null
      pod_concentration?: string | null
      affected_pods_count?: number | null
    } | null
    connectivity?: {
      failure_mode_dist?: Record<string, unknown> | null
      spatial_pod?: { scope?: string | null } | null
      spatial_host?: { scope?: string | null } | null
    } | null
    summary?: {
      anomalous_event_count?: number | null
      failure_event_count?: number | null
      total_parse_result_count?: number | null
    } | null
  } | null
}

const FAULT_CATEGORY_LABELS: Record<string, string> = {
  latency: '时延故障', connectivity: '通断故障', mixed: '时延+通断', unknown: '类型未知',
}

export const legacyFaultCategoryLabel = (item: LegacyFeatureSource) =>
  FAULT_CATEGORY_LABELS[String(item.fault_category ?? '')] ?? ''

/** mixed 案例同时含时延与通断两侧证据，因此同时计入这两个筛选。 */
export const LEGACY_FAULT_FILTERS = [
  { value: '', label: '全部' },
  { value: 'latency', label: '时延' },
  { value: 'connectivity', label: '通断' },
  { value: 'unknown', label: '未标注' },
] as const
export type LegacyFaultFilter = (typeof LEGACY_FAULT_FILTERS)[number]['value']

export const matchesLegacyFault = (
  item: { fault_category?: string | null }, filter: LegacyFaultFilter,
) => {
  if (!filter) return true
  const category = String(item.fault_category ?? '') || 'unknown'
  if (filter === 'unknown') return !['latency', 'connectivity', 'mixed'].includes(category)
  return category === filter || category === 'mixed'
}

/** 超时分段既可能是字符串数组，也可能是 [名称, 数值] 对；只取名称，避免把数值串成一串。 */
const segmentNames = (values: unknown[] | undefined) => (values ?? [])
  .map((value) => (Array.isArray(value) ? value[0] : value))
  .map((value) => String(value ?? '').trim())
  .filter(Boolean)

/** 把 features 里给人看的部分摊平成「标签：值」，供案例卡片逐行展示。 */
export const legacyCaseFacts = (item: LegacyFeatureSource): { label: string, value: string }[] => {
  const facts: { label: string, value: string }[] = []
  const description = (item.description ?? '').trim()
  if (description) facts.push({ label: '说明', value: description })

  const latency = item.features?.latency
  if (latency) {
    const parts: string[] = []
    const segments = segmentNames(latency.timeout_segments)
    if (segments.length) parts.push(`超时分段 ${segments.join(' → ')}`)
    if (typeof latency.p99_p50_ratio === 'number') parts.push(`P99/P50 ${latency.p99_p50_ratio.toFixed(2)}`)
    if (latency.pod_concentration) parts.push(`Pod 集中度 ${latency.pod_concentration}`)
    if (typeof latency.affected_pods_count === 'number') parts.push(`受影响 Pod ${latency.affected_pods_count}`)
    if (parts.length) facts.push({ label: '时延特征', value: parts.join(' · ') })
  }

  const connectivity = item.features?.connectivity
  if (connectivity) {
    const parts: string[] = []
    const modes = Object.keys(connectivity.failure_mode_dist ?? {}).filter(Boolean)
    if (modes.length) parts.push(`故障模式 ${modes.join('、')}`)
    if (connectivity.spatial_pod?.scope) parts.push(`Pod 范围 ${connectivity.spatial_pod.scope}`)
    if (connectivity.spatial_host?.scope) parts.push(`节点范围 ${connectivity.spatial_host.scope}`)
    if (parts.length) facts.push({ label: '通断特征', value: parts.join(' · ') })
  }

  const summary = item.features?.summary
  if (summary) {
    const parts = ([
      ['异常事件', summary.anomalous_event_count],
      ['故障事件', summary.failure_event_count],
      ['总记录', summary.total_parse_result_count],
    ] as const)
      .filter(([, value]) => typeof value === 'number')
      .map(([label, value]) => `${label} ${value}`)
    if (parts.length) facts.push({ label: '统计', value: parts.join(' · ') })
  }

  const tasks = item.task_names?.length ? item.task_names : item.task_ids ?? []
  if (tasks.length) facts.push({ label: '关联任务', value: tasks.join('、') })

  const logName = (item.log_file_name ?? '').trim()
  if (logName && logName !== description) facts.push({ label: '日志', value: logName })
  return facts
}


export const canOpenSource = (source?: { status: string; report_id?: string | null } | null) =>
  source?.status === 'valid' && Boolean(source.report_id)

export async function collectPages<T>(
  fetchPage: (page: number, size: number) => Promise<{ total: number; items: T[] }>,
  size = 200,
): Promise<T[]> {
  const items: T[] = []
  for (let page = 1; ; page += 1) {
    const result = await fetchPage(page, size)
    items.push(...result.items)
    if (!result.items.length || items.length >= result.total) return items
  }
}

export async function loadKnowledgeWorkspace<C, D, L>(
  view: KnowledgeView,
  loaders: {
    documents: (page: number, size: number) => Promise<{ total: number; items: D[] }>
    cases: () => Promise<C[]>
    legacy: () => Promise<L[]>
  },
) {
  const [cases, documents, legacy] = await Promise.all([
    view === 'library' ? loaders.cases() : Promise.resolve([] as C[]),
    view === 'documents' ? collectPages(loaders.documents, 100) : Promise.resolve([] as D[]),
    view === 'library' ? loaders.legacy() : Promise.resolve([] as L[]),
  ])
  return { cases, documents, legacy }
}

export type VerificationOutcome = { faultId: string; caseId?: string; error?: string }
export async function verifySelectedFaults(
  faultIds: string[],
  verify: (faultId: string) => Promise<{ case: { id: string } | null }>,
  onResult?: (outcome: VerificationOutcome) => void,
) {
  const results: VerificationOutcome[] = []
  for (const faultId of new Set(faultIds)) {
    let outcome: VerificationOutcome
    try {
      const result = await verify(faultId)
      if (!result.case?.id) throw new Error('未返回已验证案例，请刷新后重试')
      outcome = { faultId, caseId: result.case.id }
    } catch (error) {
      outcome = { faultId, error: error instanceof Error ? error.message : '验证失败' }
    }
    results.push(outcome)
    onResult?.(outcome)
  }
  return results
}

export function verificationInput(operator: string, observedResult: string, hash?: string | null) {
  if (!operator.trim()) throw new Error('请填写操作人')
  if (!observedResult.trim()) throw new Error('请填写定界结论检验结果')
  if (!hash) throw new Error('文档版本不可校验，请重新加载定界文档')
  return {
    expected_sidecar_hash: hash,
    verified_by: operator.trim(),
    observed_result: observedResult.trim(),
    method: '定界文档人工检验',
  }
}

export type ImportBatch = {
  declared_verified?: boolean
  batch_id: string
  status: string
  file_count: number
  summary: {
    imported: number; duplicate: number; failed: number; reports_confirmed: number
    cases: { confirmed: number; draft: number; skipped: number; existing: number }
  }
  items: Array<{
    original_name: string; status: string; error?: string | null
    cases?: Array<{ fault_id: string; status: string; reason?: string | null; missing_fields?: string[] }>
  }>
}

export function importForm(file: File | null, operator: string, sourceName: string, verified: boolean) {
  if (!file || !/\.(json|zip)$/i.test(file.name)) throw new Error('请选择 JSON 或 ZIP 文件')
  if (!operator.trim()) throw new Error('请填写操作人')
  if (!sourceName.trim()) throw new Error('请填写案例来源')
  const form = new FormData()
  form.append('file', file)
  form.append('operator', operator.trim())
  form.append('source_name', sourceName.trim())
  form.append('declared_verified', String(verified))
  return form
}

export type ImportMode = 'upload' | 'path'
export type ImportOptions = { path_import_enabled: boolean; allowed_roots: string[] }
export type PathImportInput = { path: string; operator: string; source_name: string; declared_verified: boolean }

export function pathImportInput(path: string, operator: string, sourceName: string, verified: boolean): PathImportInput {
  const normalized = path.trim()
  if (!normalized.startsWith('/') || /[\u0000-\u001f]/.test(normalized)) {
    throw new Error('请输入服务器文件系统的绝对路径')
  }
  if (!operator.trim()) throw new Error('请填写操作人')
  if (!sourceName.trim()) throw new Error('请填写案例来源')
  return { path: normalized, operator: operator.trim(), source_name: sourceName.trim(), declared_verified: verified }
}

export async function submitReportImport(
  input: { mode: ImportMode; file: File | null; path: string; operator: string; sourceName: string; verified: boolean },
  options: ImportOptions | null,
  api: { upload: (form: FormData) => Promise<ImportBatch>; path: (body: PathImportInput) => Promise<ImportBatch> },
) {
  if (input.mode === 'upload') return api.upload(importForm(input.file, input.operator, input.sourceName, input.verified))
  if (!options?.path_import_enabled) throw new Error('服务器路径导入未启用或配置尚未加载')
  return api.path(pathImportInput(input.path, input.operator, input.sourceName, input.verified))
}

// 无时区的 SQL 时间是服务器 UTC+8 墙钟，不依赖浏览器时区。
export function formatReportTime(value?: string | null) {
  if (!value) return '—'
  const raw = value.trim()
  const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$/i)
  if (!match) return '—'
  const [, y = '', mo = '', d = '', h = '00', mi = '00', s = '00', zone] = match
  const wall = new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi, +s))
  if (wall.getUTCFullYear() !== +y || wall.getUTCMonth() !== +mo - 1 || wall.getUTCDate() !== +d ||
    wall.getUTCHours() !== +h || wall.getUTCMinutes() !== +mi || wall.getUTCSeconds() !== +s) return '—'
  if (!match[4]) return raw
  const normalized = `${y}-${mo}-${d}T${h}:${mi}:${s}${zone || '+08:00'}`
  const time = Date.parse(normalized)
  if (!Number.isFinite(time)) return '—'
  return `${new Date(time + 8 * 3600_000).toISOString().slice(0, 19).replace('T', ' ')} (UTC+8)`
}
