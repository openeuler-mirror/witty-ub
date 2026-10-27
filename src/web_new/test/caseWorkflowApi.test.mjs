import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { collectPages } from '../src/utils/caseWorkflow.ts'

const createApi = (file, request) => {
  const source = readFileSync(new URL(`../src/api/${file}`, import.meta.url), 'utf8')
    .replace(/^import .*\n/gm, '')
  const js = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText
  const exports = {}
  new Function('exports', 'request', 'apiBase', js)(exports, request, '')
  return exports
}

test('正式库默认检索 confirmed，待验证显式包含 draft 与 confirmed', async () => {
  const calls = []
  const api = createApi('diagCaseLibrary.ts', async (path, init) => { calls.push({ path, body: JSON.parse(init.body) }); return { total: 0, matches: [] } })
  await api.searchDiagCases()
  assert.deepEqual(calls[0].body, { scope: 'library', include_status: ['confirmed'], page_num: 1, page_cnt: 50 })
  await api.searchDiagCases({ scope: 'pending', pageNum: 2, pageCnt: 200 })
  assert.deepEqual(calls[1].body, { scope: 'pending', include_status: ['draft', 'confirmed'], page_num: 2, page_cnt: 200 })
})

test('逐故障实操验证是一次独立请求，携带用户实测信息与版本哈希', async () => {
  const calls = []
  const api = createApi('diagnosticReport.ts', async (path, init) => { calls.push({ path, init }); return { case: { id: 'case-1' } } })
  const body = { expected_sidecar_hash: 'hash', verified_by: 'operator', observed_result: '现场恢复', method: '现场实操验证' }
  assert.deepEqual(await api.verifyReportFault('report/1', 'fault/1', body), { case: { id: 'case-1' } })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].path, '/diagnostic_report/report%2F1/faults/fault%2F1/verify')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].init.body), body)
})

test('导入发送文件表单，跨资产报告列表不携带 kb_id', async () => {
  const calls = []
  const api = createApi('diagnosticReport.ts', async (path, init) => { calls.push({ path, init }); return {} })
  const form = new FormData()
  form.append('file', new File(['{}'], 'cases.json'))
  await api.importCases(form)
  assert.equal(calls[0].path, '/diagnostic_report/import')
  assert.equal(calls[0].init.body, form)
  await api.fetchDiagnosticReports({ pageNum: 2, pageCnt: 200 })
  assert.deepEqual(JSON.parse(calls[1].init.body), { page_num: 2, page_cnt: 100 })
})

test('服务器路径导入发送 JSON 对象，配置只读取允许根目录接口', async () => {
  const calls = []
  const result = { batch_id: 'batch' }
  const api = createApi('diagnosticReport.ts', async (path, init) => { calls.push({ path, init }); return result })
  const body = { path: '/readonly/reports', operator: '人员', source_name: '来源', declared_verified: true }
  assert.equal(await api.importReportPath(body), result)
  assert.equal(calls[0].path, '/diagnostic_report/import/path')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].init.body), body)
  await api.fetchImportOptions()
  assert.deepEqual(calls[1], { path: '/diagnostic_report/import/options', init: undefined })
  assert.equal(calls.length, 2)
})

test('报告请求遵守每页一百条限制，超过两百条也完整读取', async () => {
  const reports = Array.from({ length: 253 }, (_, report_id) => ({ report_id }))
  const pages = []
  const api = createApi('diagnosticReport.ts', async (path, init) => {
    assert.equal(path, '/diagnostic_report/list')
    const body = JSON.parse(init.body)
    assert.ok(body.page_cnt <= 100, '报告列表每页上限为100')
    pages.push(body)
    return { total: reports.length, items: reports.slice((body.page_num - 1) * body.page_cnt, body.page_num * body.page_cnt) }
  })
  assert.deepEqual(await collectPages((pageNum, pageCnt) => api.fetchDiagnosticReports({ pageNum, pageCnt }), 100), reports)
  assert.deepEqual(pages, [
    { page_num: 1, page_cnt: 100 }, { page_num: 2, page_cnt: 100 }, { page_num: 3, page_cnt: 100 },
  ])
})

test('无来源案例直接实操验证并携带页面 revision，不经过报告流程', async () => {
  const calls = []
  const response = { case: { id: 'case/1', status: 'confirmed', revision: 8, verification_json: { closed_loop: true } }, source_report: { status: 'independent' } }
  const api = createApi('diagCaseLibrary.ts', async (path, init) => { calls.push({ path, init }); return response })
  const body = { expected_revision: 7, verified_by: 'operator', observed_result: '现场处置并复测恢复', method: '现场实操验证' }
  assert.deepEqual(await api.verifyDiagCase('case/1', body), response)
  assert.equal(calls.length, 1)
  assert.equal(calls[0].path, '/diag_case_library/case%2F1/verify')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].init.body), body)
})

test('multipart 由浏览器生成类型边界，JSON 请求维持原行为', async () => {
  const source = readFileSync(new URL('../src/api/http.ts', import.meta.url), 'utf8')
    .replace(/^import .*\n/gm, '')
    .replace(/export const apiBase = .*\n/, 'const apiBase = ""\n')
  const js = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText
  const exports = {}
  const calls = []
  const fetch = async (_url, init) => {
    calls.push(init)
    return { ok: true, json: async () => ({ code: 200, result: { ok: true } }) }
  }
  new Function('exports', 'fetch', js)(exports, fetch)
  await exports.request('/json', { method: 'POST', body: '{}' })
  await exports.request('/upload', { method: 'POST', body: new FormData() })
  assert.equal(calls[0].headers['Content-Type'], 'application/json')
  assert.equal(calls[1].headers['Content-Type'], undefined)
})
