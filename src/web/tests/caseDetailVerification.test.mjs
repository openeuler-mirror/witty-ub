import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'
import ts from 'typescript'
import * as vue from 'vue'
import * as workflow from '../src/utils/caseWorkflow.ts'

const source = parse(readFileSync(new URL('../src/components/DiagCaseDetail.vue', import.meta.url), 'utf8')).descriptor.scriptSetup.content
const js = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText
const createDetail = (verifyDiagCase = async () => { throw new Error('unexpected request') }) => {
  const events = []
  const storage = new Map()
  const require = (name) => {
    if (name === 'vue') return { ...vue, watch: () => {} }
    if (name.endsWith('/api/diagCase')) return { verifyDiagCase }
    if (name.endsWith('/utils/caseWorkflow')) return workflow
    throw new Error(`Unexpected import: ${name}`)
  }
  const state = new Function('require', 'exports', 'defineProps', 'defineEmits', 'localStorage',
    `${js}\nreturn { detail, canVerify, verified, submitVerification, operator, observedResult, verificationError, savedMessage }`)(
    require, {}, () => ({ open: true, caseId: 'independent' }), () => (...args) => events.push(args),
    { getItem: (key) => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  )
  state.detail.value = { case: { id: 'independent', status: 'draft', revision: 7 }, source_report: { status: 'independent' } }
  return { ...state, events, storage }
}

test('草稿与未闭环确认案例均可直接实操验证，已验证与归档详情保持只读', () => {
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

test('直接验证校验人员与结果，成功后使用返回详情并通知列表刷新一次', async () => {
  const calls = []
  const result = { case: { id: 'independent', status: 'confirmed', revision: 8, verification_json: { closed_loop: true } }, source_report: { status: 'independent' } }
  const state = createDetail(async (...args) => { calls.push(args); return result })
  await state.submitVerification()
  assert.match(state.verificationError.value, /操作人/)
  state.operator.value = ' operator '
  await state.submitVerification()
  assert.match(state.verificationError.value, /定界结论检验结果/)
  assert.equal(calls.length, 0)
  state.observedResult.value = ' 实操复测恢复 '
  await state.submitVerification()
  assert.deepEqual(calls, [['independent', { expected_revision: 7, verified_by: 'operator', observed_result: '实操复测恢复', method: '定界文档人工检验' }]])
  assert.equal(state.detail.value.case.revision, 8)
  assert.equal(state.canVerify.value, false)
  assert.deepEqual(state.events, [['changed']])
  assert.equal(state.storage.get('witty-operator'), 'operator')
})

test('版本冲突保留用户输入与待验证状态，不虚报成功或刷新列表', async () => {
  const state = createDetail(async () => { throw new Error('案例版本已变化，请刷新') })
  state.operator.value = 'operator'
  state.observedResult.value = '真实复测记录'
  await state.submitVerification()
  assert.match(state.verificationError.value, /版本已变化/)
  assert.equal(state.observedResult.value, '真实复测记录')
  assert.equal(state.canVerify.value, true)
  assert.deepEqual(state.events, [])
})
