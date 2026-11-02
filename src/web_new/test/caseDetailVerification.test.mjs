import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'
import ts from 'typescript'
import * as vue from 'vue'
import * as workflow from '../src/utils/caseWorkflow.ts'

const source = parse(readFileSync(new URL('../src/components/knowledge/DiagCaseDetailModal.vue', import.meta.url), 'utf8')).descriptor.scriptSetup.content
const js = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText
const createDetail = (verifyDiagCase = async () => { throw new Error('unexpected request') }) => {
  const notifications = []
  const operator = vue.ref('')
  const require = (name) => {
    if (name === 'vue') return { ...vue, watch: () => {} }
    if (name.endsWith('/api/diagCaseLibrary')) return { verifyDiagCase }
    if (name.endsWith('/utils/caseWorkflow')) return workflow
    if (name.endsWith('/useDiagCaseDetail')) return {
      useDiagCaseDetail: () => ({ open: vue.ref(true), caseId: vue.ref('independent'), closeCase: () => {}, bumpCaseVersion: () => notifications.push('changed') }),
    }
    if (name.endsWith('/useReportWorkbench')) return { useReportWorkbench: () => ({ openReport: () => {} }) }
    if (name.endsWith('/useOperator')) return { useOperator: () => ({ operator, setOperator: (value) => { operator.value = value } }) }
    throw new Error(`Unexpected import: ${name}`)
  }
  const state = new Function('require', 'exports',
    `${js}\nreturn { detail, canVerify, verified, submitVerification, operator, observedResult, verificationError, savedMessage }`)(require, {})
  state.detail.value = { case: { id: 'independent', status: 'draft', revision: 7 }, source_report: { status: 'independent' } }
  return { ...state, notifications }
}

test('无来源草稿与未验证确认案例可直接验证，已验证或归档详情不显示验证操作', () => {
  const state = createDetail()
  assert.equal(state.canVerify.value, true)
  state.detail.value.case.status = 'confirmed'
  assert.equal(state.canVerify.value, true)
  state.detail.value.case.verification_json = { closed_loop: true }
  assert.equal(state.canVerify.value, false)
  state.detail.value.case.status = 'archived'
  state.detail.value.case.verification_json.closed_loop = false
  assert.equal(state.canVerify.value, false)
})

test('文档关联草稿只能回到定界文档检验，不提供独立案例验证操作', () => {
  const state = createDetail()
  state.detail.value.case.report_id = 'document-1'
  assert.equal(state.canVerify.value, false)
})

test('提交实测信息与页面 revision，成功后替换详情并发出案例刷新通知', async () => {
  const calls = []
  const result = { case: { id: 'independent', status: 'confirmed', revision: 8, verification_json: { closed_loop: true } }, source_report: { status: 'independent' } }
  const state = createDetail(async (...args) => { calls.push(args); return result })
  await state.submitVerification()
  assert.match(state.verificationError.value, /操作人/)
  state.operator.value = ' operator '
  await state.submitVerification()
  assert.match(state.verificationError.value, /定界结论检验结果/)
  assert.equal(calls.length, 0)
  state.observedResult.value = ' 现场实操恢复 '
  await state.submitVerification()
  assert.deepEqual(calls, [['independent', { expected_revision: 7, verified_by: 'operator', observed_result: '现场实操恢复', method: '定界文档人工检验' }]])
  assert.equal(state.detail.value.case.revision, 8)
  assert.equal(state.canVerify.value, false)
  assert.deepEqual(state.notifications, ['changed'])
})

test('版本失败保留实测记录与验证入口，不误标已验证', async () => {
  const state = createDetail(async () => { throw new Error('案例版本冲突，请刷新') })
  state.operator.value = 'operator'
  state.observedResult.value = '现场记录'
  await state.submitVerification()
  assert.match(state.verificationError.value, /版本冲突/)
  assert.equal(state.observedResult.value, '现场记录')
  assert.equal(state.canVerify.value, true)
  assert.deepEqual(state.notifications, [])
})
