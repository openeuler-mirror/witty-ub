import assert from 'node:assert/strict'
import test from 'node:test'
import { canVerifyFault, caseRefsForFault, isFaultVerified, unmatchedCaseRefs, verificationInput, verifySelectedFaults } from '../src/utils/caseWorkflow.ts'

test('AI 声称 confirmed 不代表实操验证，suspected 也允许人工核验', () => {
  for (const status of ['confirmed', 'suspected', 'unknown']) {
    const fault = { fault_id: 'F01', status }
    assert.equal(isFaultVerified(fault), false)
    assert.equal(canVerifyFault(fault), true)
  }
})

test('只认当前版本已确认且闭环的逐故障案例，过期或他故障不混用', () => {
  const fault = { fault_id: 'F01' }
  const ref = { source_fault_id: 'F01', is_current_version: true, status: 'confirmed', closed_loop: true }
  assert.equal(isFaultVerified(fault, [ref]), true)
  assert.equal(canVerifyFault(fault, [ref]), false)
  for (const change of [{ is_current_version: false }, { status: 'draft' }, { status: 'archived' }, { closed_loop: false }, { source_fault_id: 'F02' }]) {
    assert.equal(isFaultVerified(fault, [{ ...ref, ...change }]), false)
  }
  assert.equal(canVerifyFault({ fault_id: null }), false)
  assert.equal(canVerifyFault({ fault_id: 'F01', synthetic: true }), false)
  assert.equal(canVerifyFault({ fault_id: 'F01', excluded: true }), false)
})

test('提交需操作人与定界结论检验结果，并携带看到的文档哈希，不要求再次修复', () => {
  assert.throws(() => verificationInput(' ', '结果', 'hash'), /操作人/)
  assert.throws(() => verificationInput('a', ' ', 'hash'), /定界结论检验结果/)
  assert.throws(() => verificationInput('a', '结果', null), /版本不可校验/)
  assert.deepEqual(verificationInput(' a ', ' 日志证据与定界结论一致 ', 'hash-1'), {
    expected_sidecar_hash: 'hash-1', verified_by: 'a', observed_result: '日志证据与定界结论一致', method: '定界文档人工检验',
  })
})

test('批量实操验证顺序提交，逐条显示成功失败，失败不阻塞后续结论', async () => {
  let active = 0
  const calls = []
  const progress = []
  const result = await verifySelectedFaults(['F01', 'F02', 'F03', 'F01'], async (faultId) => {
    assert.equal(active++, 0)
    calls.push(faultId)
    await Promise.resolve()
    active--
    if (faultId === 'F02') throw new Error('报告已变化，请刷新')
    return { case: { id: `case-${faultId}` } }
  }, (outcome) => progress.push(outcome))
  assert.deepEqual(calls, ['F01', 'F02', 'F03'])
  assert.deepEqual(result, [
    { faultId: 'F01', caseId: 'case-F01' },
    { faultId: 'F02', error: '报告已变化，请刷新' },
    { faultId: 'F03', caseId: 'case-F03' },
  ])
  assert.deepEqual(progress, result)
})

test('后端未返回案例时不虚报验证成功', async () => {
  const [result] = await verifySelectedFaults(['F01'], async () => ({ case: null }))
  assert.equal(result.caseId, undefined)
  assert.match(result.error, /未返回已验证案例/)
})

test('关联案例按故障归入结论卡片，未绑定或结论缺失的案例不丢失', () => {
  const refs = [{ source_fault_id: 'F01' }, { source_fault_id: 'F02' }, {}, { source_fault_id: null }]
  assert.deepEqual(caseRefsForFault(refs, 'F01'), [refs[0]])
  assert.deepEqual(caseRefsForFault(refs, null), refs.slice(2))
  assert.deepEqual(unmatchedCaseRefs(refs, [{ fault_id: 'F01' }]), refs.slice(1))
})
