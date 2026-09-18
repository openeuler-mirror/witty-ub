#!/usr/bin/env node
/**
 * 前端消费的后端接口快照（模型字段 + 调用到的路径）。
 *
 * 上游后端更新后，前端必须对齐接口：跑一次 `--check`，逐条看差异是
 * 「新增字段（通常可直接用）」「字段消失/改名（前端必须改）」「枚举/类型变化
 * （前端判定逻辑要跟着改）」，再决定本页 UI 要不要动。
 *
 * 快照默认落在本地 agent harness（`.agents/skills/web-new-dev/references/`），不进仓库；
 * 可用 WITTY_API_SNAPSHOT 指定其它路径。
 *
 * 用法：
 *   API_BASE_URL=http://<backend>:9772 node scripts/api-models-snapshot.mjs            # 打印当前接口
 *   API_BASE_URL=http://<backend>:9772 node scripts/api-models-snapshot.mjs --write    # 覆盖快照
 *   API_BASE_URL=http://<backend>:9772 node scripts/api-models-snapshot.mjs --check    # 与快照比较
 *   node scripts/api-models-snapshot.mjs --from /tmp/openapi.json --check             # 从本地 openapi.json 比较
 */
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const SNAPSHOT_PATH =
  process.env.WITTY_API_SNAPSHOT ??
  join(HERE, '..', '..', '..', '.agents', 'skills', 'web-new-dev', 'references', 'api-models.snapshot.json')

/** 前端直接读字段的后端模型；字段消失/改名会直接让界面显示不出来。 */
const MODELS = [
  'LogKnowledgeModel',
  'LogFileModel',
  'TaskModel',
  'TaskReportModel',
  'UploadLogFilesMsg',
  'LogParseResultModel',
  'LogFailureEventModel',
  'DiagnosisConfigResult',
  'KVCacheDiagnosisConfig',
  'GetLatencyMetricsMsg',
  'GetErrCodeMetricsMsg',
]

/** 前端调用的路径（方法 + 模板路径，`{}` 内参数名不参与比较）。 */
const ENDPOINTS = [
  ['GET', '/health_check'],
  ['POST', '/log_kb/list'],
  ['POST', '/log_kb'],
  ['GET', '/log_kb/{kb_id}'],
  ['PUT', '/log_kb/{kb_id}'],
  ['DELETE', '/log_kb/{kb_id}'],
  ['POST', '/log_file/list/{kb_id}'],
  ['POST', '/log_file/{kb_id}'],
  ['PUT', '/log_file/run/{log_file_id}'],
  ['DELETE', '/log_file/{log_file_id}'],
  ['POST', '/log_file/{log_file_id}/brpc-diagnosis'],
  ['POST', '/task/list'],
  ['GET', '/diagnosis_config/{kb_id}'],
  ['PUT', '/diagnosis_config/{kb_id}'],
  ['POST', '/diagnosis_config/{kb_id}/reset'],
  ['POST', '/log_parse_result/list'],
  ['POST', '/log_parse_result/metrics/latency'],
  ['POST', '/log_failure_event_result/list_log_events'],
  ['POST', '/log_failure_event_result/list_trace_events'],
  ['POST', '/log_failure_event_result/list_src_dst_aggregated_failure_events'],
  ['POST', '/log_failure_event_result/list_time_aggregated_failure_events'],
  ['POST', '/log_failure_event_result/metrics/err_code'],
  ['POST', '/aggregated_event/list_time_window'],
  ['GET', '/failure_mode/{failure_mode_id}'],
  ['GET', '/brpc_profiling/knowledge/{kb_id}'],
  ['GET', '/brpc-diagnosis/batch/{batch_id}'],
]

const args = process.argv.slice(2)
const fromIndex = args.indexOf('--from')
const fromFile = fromIndex >= 0 ? args[fromIndex + 1] : null
const baseUrl = (
  process.env.API_BASE_URL ??
  process.env.VITE_API_BASE_URL ??
  'http://127.0.0.1:9772'
).replace(/\/+$/, '')

const typeOf = (schema) => {
  if (!schema) return 'unknown'
  if (schema.$ref) return schema.$ref.split('/').pop()
  if (Array.isArray(schema.enum)) return `enum(${schema.enum.join('|')})`
  if (Array.isArray(schema.anyOf)) return schema.anyOf.map(typeOf).join(' | ')
  if (Array.isArray(schema.allOf)) return schema.allOf.map(typeOf).join(' & ')
  if (schema.type === 'array') return `array<${typeOf(schema.items)}>`
  if (schema.anyOf) return schema.anyOf.map(typeOf).join(' | ')
  return schema.type ?? 'any'
}

const normalizePath = (path) => path.replace(/\{[^}]+\}/g, '{}')

const buildSnapshot = (openapi) => {
  const schemas = openapi.components?.schemas ?? {}
  const paths = openapi.paths ?? {}

  const models = {}
  for (const name of MODELS) {
    const schema = schemas[name]
    if (!schema) {
      models[name] = { missing: true }
      continue
    }
    const properties = {}
    for (const [field, fieldSchema] of Object.entries(schema.properties ?? {})) {
      properties[field] = typeOf(fieldSchema)
    }
    models[name] = {
      required: [...(schema.required ?? [])].sort(),
      properties: Object.fromEntries(
        Object.entries(properties).sort(([a], [b]) => (a < b ? -1 : 1)),
      ),
    }
  }

  const endpoints = {}
  for (const [method, template] of ENDPOINTS) {
    const wanted = normalizePath(template)
    const key = `${method} ${wanted}`
    // 同一路径模板可能同时挂多个方法（如 /log_file/{id} 的 GET/PUT/DELETE），
    // 必须按「模板 + 方法」一起匹配。
    const hit = Object.keys(paths).find(
      (path) => normalizePath(path) === wanted && paths[path]?.[method.toLowerCase()],
    )
    endpoints[key] = hit ? { path: hit } : { missing: true }
  }

  return { models, endpoints }
}

const diffSnapshots = (expected, actual) => {
  const lines = []
  for (const name of new Set([...Object.keys(expected.models), ...Object.keys(actual.models)])) {
    const before = expected.models[name]
    const after = actual.models[name]
    if (!before || !after) {
      lines.push(`model ${name}: ${before ? '快照有、后端没有' : '后端新增'}`)
      continue
    }
    if (before.missing || after.missing) {
      if (before.missing !== after.missing)
        lines.push(`model ${name}: missing ${before.missing} → ${after.missing}`)
      continue
    }
    const fields = new Set([...Object.keys(before.properties), ...Object.keys(after.properties)])
    for (const field of fields) {
      const oldType = before.properties[field]
      const newType = after.properties[field]
      if (oldType === undefined) lines.push(`model ${name}.${field}: 后端新增 ${newType}`)
      else if (newType === undefined) lines.push(`model ${name}.${field}: 后端删除（前端必须跟进）`)
      else if (oldType !== newType) lines.push(`model ${name}.${field}: ${oldType} → ${newType}`)
    }
    const requiredBefore = before.required.join(',')
    const requiredAfter = after.required.join(',')
    if (requiredBefore !== requiredAfter) {
      lines.push(`model ${name}: required ${requiredBefore} → ${requiredAfter}`)
    }
  }
  for (const key of new Set([
    ...Object.keys(expected.endpoints),
    ...Object.keys(actual.endpoints),
  ])) {
    const before = expected.endpoints[key]
    const after = actual.endpoints[key]
    if (!before || !after)
      lines.push(`endpoint ${key}: ${before ? '快照有、后端没有' : '后端新增'}`)
    else if (Boolean(before.missing) !== Boolean(after.missing)) {
      lines.push(`endpoint ${key}: missing ${before.missing} → ${after.missing}`)
    }
  }
  return lines
}

const loadOpenapi = async () => {
  if (fromFile) {
    if (!existsSync(fromFile)) {
      console.error(`openapi 文件不存在: ${fromFile}`)
      process.exit(2)
    }
    return JSON.parse(readFileSync(fromFile, 'utf8'))
  }
  const response = await fetch(`${baseUrl}/openapi.json`)
  if (!response.ok) {
    console.error(`拉取 ${baseUrl}/openapi.json 失败: HTTP ${response.status}`)
    process.exit(2)
  }
  return await response.json()
}

const snapshot = buildSnapshot(await loadOpenapi())

if (args.includes('--write')) {
  writeFileSync(SNAPSHOT_PATH, `${JSON.stringify(snapshot, null, 2)}\n`)
  console.log(`快照已写入 ${SNAPSHOT_PATH}`)
} else if (args.includes('--check')) {
  if (!existsSync(SNAPSHOT_PATH)) {
    console.error(`快照不存在：${SNAPSHOT_PATH}`)
    console.error('快照随本地 harness 保存（不进仓库）。先跑一次 `npm run api:snapshot` 生成。')
    process.exit(2)
  }
  const expected = JSON.parse(readFileSync(SNAPSHOT_PATH, 'utf8'))
  const lines = diffSnapshots(expected, snapshot)
  if (lines.length === 0) {
    console.log('接口快照一致：模型字段与前端调用的路径都没有变化')
  } else {
    console.log(`接口快照有 ${lines.length} 处差异（前 = 快照，后 = 当前后端）：`)
    for (const line of lines) console.log(`  - ${line}`)
    process.exit(1)
  }
} else {
  console.log(JSON.stringify(snapshot, null, 2))
}
