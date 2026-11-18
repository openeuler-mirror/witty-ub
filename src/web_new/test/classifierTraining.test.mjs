import assert from 'node:assert/strict'
import test from 'node:test'
import { classifierTrainingNotice } from '../src/utils/classifierTraining.ts'

const state = (status, extras = {}) => ({ status, message: status === 'training' || status === 'pending'
  ? '故障分类器训练中，建议在训练完成后生成定界报告。' : '故障分类器训练完成，可以生成定界报告。',
  confirmed_case_count: 4, sample_count: 478, skipped_case_count: 0, model_version: 'v2',
  started_at: null, completed_at: null, pending_changes: false, error: null, ...extras })

test('训练中及待训练状态醒目提示等待完成后生成定界报告', () => {
  for (const status of ['training', 'pending']) {
    const notice = classifierTrainingNotice(state(status))
    assert.equal(notice.busy, true)
    assert.equal(notice.tone, 'warning')
    assert.match(notice.detail, /建议在训练完成后生成定界报告/)
  }
})

test('完成状态展示样本数且不把跳过案例伪装为已训练', () => {
  const notice = classifierTrainingNotice(state('ready', { skipped_case_count: 2 }))
  assert.equal(notice.title, '故障分类器训练完成')
  assert.equal(notice.tone, 'success')
  assert.match(notice.detail, /478 个训练样本/)
  assert.match(notice.detail, /2 个案例.*未纳入训练/)
})

test('训练失败和接口不可用不会显示为训练完成', () => {
  assert.equal(classifierTrainingNotice(state('failed')).tone, 'danger')
  const notice = classifierTrainingNotice(state('ready'), true)
  assert.match(notice.title, /状态暂不可用/)
  assert.equal(notice.tone, 'warning')
})

test('训练期间的新变更提示继续更新', () => {
  assert.match(classifierTrainingNotice(state('training', { pending_changes: true })).detail, /新的案例变更/)
})


test('数据不足明确展示 K4 退化原因并等待新增有效案例', () => {
  const notice = classifierTrainingNotice(state('insufficient_data', {
    message: '有效训练数据不足，已停用分类器，使用当前案例集的全特征余弦 K4。',
    training_reason: '独立来源 3 个，至少需要 20 个',
  }))
  assert.equal(notice.busy, false)
  assert.equal(notice.tone, 'warning')
  assert.match(notice.title, /训练数据不足/)
  assert.match(notice.detail, /全特征余弦 K4/)
  assert.match(notice.detail, /至少需要 20 个/)
  assert.match(notice.detail, /补充有效案例后将自动重训/)
})
