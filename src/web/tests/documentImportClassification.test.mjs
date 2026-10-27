import assert from 'node:assert/strict'
import test from 'node:test'
import {
  documentClassificationText, filterDocuments, formatReportTime, matchesDocumentClassification,
  pathImportInput, submitReportImport, UNCLASSIFIED, validDocumentClassifications,
} from '../src/utils/caseWorkflow.ts'

const pair = (first, second) => ({ first_level_label: first, second_level_label: second, status: 'pair' })
const empty = { first_level_label: null, second_level_label: null, status: 'empty' }

test('文档匹配任一故障，同一文档多故障及重复分类只计一份，二级必须与同一故障一级配对', () => {
  const documents = [
    { report_id: 'multi', classifications: [pair('A', 'a'), pair('B', 'b'), pair('A', 'a')] },
    { report_id: 'single', classifications: [pair('A', 'b')] },
  ]
  assert.deepEqual(filterDocuments(documents, 'all', 'A').map((item) => item.report_id), ['multi', 'single'])
  assert.deepEqual(filterDocuments(documents, 'all', 'A', 'a').map((item) => item.report_id), ['multi'])
  assert.deepEqual(filterDocuments(documents, 'all', 'A', 'b').map((item) => item.report_id), ['single'])
  assert.equal(documentClassificationText(documents[0]), 'A / a、B / b')
})

test('待验证与分类取交集，不依赖生成案例，未分类必须有明确 empty 故障', () => {
  const documents = [
    { report_id: 'pending', validation_status: 'pending', classifications: [pair('A', 'a'), empty] },
    { report_id: 'done', validation_status: 'validated', classifications: [pair('A', 'a')] },
    { report_id: 'other', validation_status: 'pending', classifications: [pair('B', 'b')] },
    { report_id: 'old', validation_status: 'pending' },
    { report_id: 'invalid', classifications: [{ ...empty, status: 'invalid' }] },
    { report_id: 'unavailable', classifications: [{ ...empty, status: 'unavailable' }] },
  ]
  assert.deepEqual(filterDocuments(documents, 'pending', 'A').map((item) => item.report_id), ['pending'])
  assert.deepEqual(filterDocuments(documents, 'all', UNCLASSIFIED).map((item) => item.report_id), ['pending'])
  assert.equal(documentClassificationText(documents[3]), '⚠ 无有效分类')
  assert.equal(documentClassificationText(documents[4]), '⚠ 无有效分类')
  assert.equal(documentClassificationText({ classifications: [empty] }), '未分类')
  assert.equal(documentClassificationText({
    classifications: [pair('A', 'a'), { ...pair('B', 'b'), status: 'invalid' }],
  }), 'A / a（部分分类异常）')
  assert.equal(matchesDocumentClassification(documents[3], 'A'), false)
  const invalidWithLabels = { classifications: [{ ...pair('A', 'a'), status: 'invalid' }] }
  assert.equal(matchesDocumentClassification(invalidWithLabels, 'A', 'a'), false)
  assert.deepEqual(validDocumentClassifications(invalidWithLabels), [])
  const firstOnly = { classifications: [{ first_level_label: 'A', second_level_label: null, status: 'first_only' }] }
  assert.equal(matchesDocumentClassification(firstOnly, 'A'), true)
  assert.equal(matchesDocumentClassification(firstOnly, 'A', 'a'), false)
})

test('上传与服务器路径模式分流 FormData 和 JSON 对象，路径未启用时禁止请求', async () => {
  const calls = []
  const batch = { batch_id: 'batch' }
  const api = {
    upload: async (body) => { calls.push(['upload', body]); return batch },
    path: async (body) => { calls.push(['path', body]); return batch },
  }
  const input = {
    mode: 'upload', file: new File(['{}'], 'report.json'), path: '/readonly/report.json',
    operator: ' 人员 ', sourceName: ' 来源 ', verified: false,
  }
  assert.equal(await submitReportImport(input, null, api), batch)
  assert.ok(calls[0][1] instanceof FormData)
  assert.equal(calls[0][1].get('file').name, 'report.json')
  assert.equal(calls[0][1].get('declared_verified'), 'false')
  assert.equal(await submitReportImport({ ...input, mode: 'path', file: null },
    { path_import_enabled: true, allowed_roots: ['/readonly'] }, api), batch)
  assert.deepEqual(calls[1], ['path', {
    path: '/readonly/report.json', operator: '人员', source_name: '来源', declared_verified: false,
  }])
  await assert.rejects(submitReportImport({ ...input, mode: 'path' }, null, api), /未启用/)
  await assert.rejects(submitReportImport({ ...input, mode: 'path' },
    { path_import_enabled: false, allowed_roots: [] }, api), /未启用/)
  assert.equal(calls.length, 2)
  await submitReportImport({ ...input, file: new File(['zip'], 'report.zip') }, null, api)
  assert.equal(calls[2][1].get('file').name, 'report.zip')
})

test('服务器路径只接受手工输入的绝对路径，不接受相对路径、本地文件 URL 或空输入', () => {
  for (const path of ['', 'relative/report.json', 'file:///local/report.json', 'C:\\local\\report.json', '/safe/\nreport.json']) {
    assert.throws(() => pathImportInput(path, '人员', '来源', true), /服务器.*绝对路径/)
  }
  assert.deepEqual(pathImportInput(' /readonly/reports ', ' 人员 ', ' 来源 ', true), {
    path: '/readonly/reports', operator: '人员', source_name: '来源', declared_verified: true,
  })
  assert.throws(() => pathImportInput('/readonly', '', '来源', true), /操作人/)
  assert.throws(() => pathImportInput('/readonly', '人员', '', true), /来源/)
})

test('生成时间固定 UTC+8：显式时区等价，无时区 SQL 按服务器墙钟，日期保留，非法不伪造', () => {
  const expected = '2026-10-27 08:09:10 (UTC+8)'
  for (const value of [
    '2026-10-27T00:09:10.123Z', '2026-10-27T08:09:10+08:00',
    '2026-10-26T19:09:10-05:00', '2026-10-27 08:09:10', '2026-10-27T08:09:10.999',
  ]) assert.equal(formatReportTime(value), expected, value)
  assert.equal(formatReportTime('2026-10-27'), '2026-10-27')
  for (const value of [null, '', 'not-a-time', '2026-02-30', '2026-02-30T12:00:00Z', '2026-10-27T25:00:00', '2026-10-27T12:00:00+25:00']) {
    assert.equal(formatReportTime(value), '—', value)
  }
})
