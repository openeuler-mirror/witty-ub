import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { collectPages } from '../src/utils/caseWorkflow.ts'

const source = readFileSync(new URL('../src/api/diagCase.ts', import.meta.url), 'utf8')
const apiJs = ts.transpileModule(source.replace(/^import .*\n/gm, '').replace(/export \{ apiBase \}/, ''), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText
const createApi = (request) => {
  const exports = {}
  new Function('exports', 'request', 'apiBase', apiJs)(exports, request, '')
  return exports
}

test('逐故障验证只发起一次请求，携带实测结果与当前版本并正确编码来源标识', async () => {
  const calls = []
  const api = createApi(async (path, init) => { calls.push({ path, init }); return { case: { id: 'case-1' } } })
  const body = { expected_sidecar_hash: 'hash', verified_by: 'operator', observed_result: '现场恢复', method: '现场实操验证' }
  assert.deepEqual(await api.verifyReportFault('report/1', 'fault/1', body), { case: { id: 'case-1' } })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].path, '/diagnostic_report/report%2F1/faults/fault%2F1/verify')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].init.body), body)
})

test('外部导入直接提交 FormData，不把文件变为 JSON 或携带资产范围', async () => {
  const form = new FormData()
  form.append('file', new File(['{}'], 'cases.json'))
  const calls = []
  const api = createApi(async (path, init) => { calls.push({ path, init }); return { items: [] } })
  await api.importCases(form)
  assert.equal(calls[0].path, '/diagnostic_report/import')
  assert.equal(calls[0].init.body, form)
  await api.fetchReports(2, 200)
  assert.deepEqual(JSON.parse(calls[1].init.body), { page_num: 2, page_cnt: 100 })
})

test('服务器路径导入发送 JSON 对象，配置只读取允许根目录接口', async () => {
  const calls = []
  const result = { batch_id: 'batch' }
  const api = createApi(async (path, init) => { calls.push({ path, init }); return result })
  const body = { path: '/readonly/reports', operator: '人员', source_name: '来源', declared_verified: true }
  assert.equal(await api.importReportPath(body), result)
  assert.equal(calls[0].path, '/diagnostic_report/import/path')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].init.body), body)
  await api.fetchImportOptions()
  assert.deepEqual(calls[1], { path: '/diagnostic_report/import/options', init: undefined })
  assert.equal(calls.length, 2)
})

test('报告分页遵守后端每页最多一百条，跨页读完所有待验证报告', async () => {
  const reports = Array.from({ length: 253 }, (_, report_id) => ({ report_id }))
  const pages = []
  const api = createApi(async (path, init) => {
    assert.equal(path, '/diagnostic_report/list')
    const body = JSON.parse(init.body)
    assert.ok(body.page_cnt <= 100, '报告列表每页上限为100')
    pages.push(body)
    return { total: reports.length, items: reports.slice((body.page_num - 1) * body.page_cnt, body.page_num * body.page_cnt) }
  })
  assert.deepEqual(await collectPages(api.fetchReports, 100), reports)
  assert.deepEqual(pages, [
    { page_num: 1, page_cnt: 100 }, { page_num: 2, page_cnt: 100 }, { page_num: 3, page_cnt: 100 },
  ])
})

test('无来源案例实操验证只提交一次版本锁定请求，不依赖报告标识', async () => {
  const calls = []
  const response = { case: { id: 'case/1', status: 'confirmed', revision: 8, verification_json: { closed_loop: true } }, source_report: { status: 'independent' } }
  const api = createApi(async (path, init) => { calls.push({ path, init }); return response })
  const body = { expected_revision: 7, verified_by: 'operator', observed_result: '现场处置并复测恢复', method: '现场实操验证' }
  assert.deepEqual(await api.verifyDiagCase('case/1', body), response)
  assert.equal(calls.length, 1)
  assert.equal(calls[0].path, '/diag_case_library/case%2F1/verify')
  assert.equal(calls[0].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[0].init.body), body)
})

test('JSON 请求设置类型，multipart 则让浏览器生成含 boundary 的类型', async () => {
  const clientSource = readFileSync(new URL('../src/api/client.ts', import.meta.url), 'utf8')
    .replace(/export const apiBase = .*\n/, 'const apiBase = ""\n')
  const clientJs = ts.transpileModule(clientSource, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText
  const exports = {}
  const calls = []
  const fetch = async (_url, init) => {
    calls.push(init)
    return { ok: true, json: async () => ({ code: 200, result: { ok: true } }) }
  }
  new Function('exports', 'fetch', clientJs)(exports, fetch)
  await exports.request('/json', { method: 'POST', body: '{}' })
  await exports.request('/upload', { method: 'POST', body: new FormData() })
  assert.equal(calls[0].headers['Content-Type'], 'application/json')
  assert.equal(calls[1].headers['Content-Type'], undefined)
})
