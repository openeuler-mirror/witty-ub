import assert from 'node:assert/strict'
import test from 'node:test'
import { verificationInput, verifySelectedFaults } from '../src/utils/caseWorkflow.ts'

test('文档人工检验以用户看到的哈希锁定版本，不自行生成检验时间或信任 AI 状态', () => {
  assert.deepEqual(verificationInput(' 操作人 ', ' 原始日志证据支持该定界结论 ', 'observed-hash'), {
    expected_sidecar_hash: 'observed-hash',
    verified_by: '操作人',
    observed_result: '原始日志证据支持该定界结论',
    method: '定界文档人工检验',
  })
})

test('同批次使用同一份用户核验信息，服务端版本冲突保留为逐条失败', async () => {
  const body = verificationInput('a', '文档与原始日志核对一致', 'hash-before-change')
  const requests = []
  const results = await verifySelectedFaults(['F01', 'F02'], async (faultId) => {
    requests.push({ faultId, ...body })
    if (faultId === 'F02') throw new Error('报告已更新，请重新核对')
    return { case: { id: 'case-1' } }
  })
  assert.deepEqual(requests.map((request) => request.expected_sidecar_hash), ['hash-before-change', 'hash-before-change'])
  assert.equal(results[0].caseId, 'case-1')
  assert.match(results[1].error, /重新核对/)
})
