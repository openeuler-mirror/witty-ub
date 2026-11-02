import assert from 'node:assert/strict'
import test from 'node:test'
import { canVerifyFault, caseRefsForFault, isFaultVerified, unmatchedCaseRefs, verificationInput, verifySelectedFaults } from '../src/utils/caseWorkflow.ts'

test('AI 状态不是人工验证凭证，待确认故障同样可完成实操验证', () => {
  for (const status of ['confirmed', 'suspected', 'unknown']) {
    assert.equal(isFaultVerified({ fault_id: 'F01', status }), false)
    assert.equal(canVerifyFault({ fault_id: 'F01', status }), true)
  }
})

test('验证状态须来自同故障当前版本且闭环案例', () => {
  const fault = { fault_id: 'F01' }
  const ref = { source_fault_id: 'F01', is_current_version: true, status: 'confirmed', closed_loop: true }
  assert.equal(isFaultVerified(fault, [ref]), true)
  assert.equal(canVerifyFault(fault, [ref]), false)
  for (const change of [{ is_current_version: false }, { status: 'archived' }, { status: 'draft' }, { closed_loop: false }, { source_fault_id: 'F02' }]) {
    assert.equal(isFaultVerified(fault, [{ ...ref, ...change }]), false)
  }
  assert.equal(canVerifyFault({ fault_id: null }), false)
  assert.equal(canVerifyFault({ fault_id: 'F01', synthetic: true }), false)
  assert.equal(canVerifyFault({ fault_id: 'F01', excluded: true }), false)
})

test('没有操作人、定界结论检验结果或版本哈希不允许提交', () => {
  assert.throws(() => verificationInput('', '结果', 'hash'), /操作人/)
  assert.throws(() => verificationInput('a', ' ', 'hash'), /定界结论检验结果/)
  assert.throws(() => verificationInput('a', '结果', null), /版本不可校验/)
  assert.deepEqual(verificationInput(' 人员 ', ' 原始日志支持该定界结论 ', 'hash'), {
    expected_sidecar_hash: 'hash', verified_by: '人员', observed_result: '原始日志支持该定界结论', method: '定界文档人工检验',
  })
})

test('多选验证顺序执行并单独报告失败，重复选择不重复提交', async () => {
  const calls = []
  let active = false
  const progress = []
  const result = await verifySelectedFaults(['F01', 'F02', 'F03', 'F01'], async (faultId) => {
    assert.equal(active, false)
    active = true
    calls.push(faultId)
    await Promise.resolve()
    active = false
    if (faultId === 'F02') throw new Error('版本冲突')
    return { case: { id: `case-${faultId}` } }
  }, (outcome) => progress.push(outcome))
  assert.deepEqual(calls, ['F01', 'F02', 'F03'])
  assert.deepEqual(result, [
    { faultId: 'F01', caseId: 'case-F01' },
    { faultId: 'F02', error: '版本冲突' },
    { faultId: 'F03', caseId: 'case-F03' },
  ])
  assert.deepEqual(progress, result)
})

test('空案例响应不可显示为成功', async () => {
  const [result] = await verifySelectedFaults(['F01'], async () => ({ case: null }))
  assert.equal(result.caseId, undefined)
  assert.match(result.error, /未返回已验证案例/)
})

test('关联案例按故障归入结论，未绑定或结论缺失的案例不丢失', () => {
  const refs = [{ source_fault_id: 'F01' }, { source_fault_id: 'F02' }, {}, { source_fault_id: null }]
  assert.deepEqual(caseRefsForFault(refs, 'F01'), [refs[0]])
  assert.deepEqual(caseRefsForFault(refs, null), refs.slice(2))
  assert.deepEqual(unmatchedCaseRefs(refs, [{ fault_id: 'F01' }]), refs.slice(1))
})
