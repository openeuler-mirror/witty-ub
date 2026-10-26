import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), 'utf8')

const FORM = read('../src/components/report/VerificationForm.vue')
const API = read('../src/api/diagCaseLibrary.ts')
const DETAIL = read('../src/components/knowledge/DiagCaseDetailModal.vue')

test('验证回填携带页面所见 revision', () => {
  assert.match(API, /expected_revision: expectedRevision/)
  assert.match(FORM, /props\.revision,/)
  assert.match(DETAIL, /:revision="caseData\.revision"/)
})

test('闭环校验先于提交，缺少方法与结果时拒绝保存', () => {
  assert.match(
    FORM,
    /if \(closedLoop\.value && \(!method\.value\.trim\(\) \|\| !observedResult\.value\.trim\(\)\)\)/,
  )
  assert.match(FORM, /标记闭环时必须填写验证方法和实测结果/)
})

test('验证时间提交完整 ISO，不截断时区', () => {
  assert.match(FORM, /verified_at: new Date\(\)\.toISOString\(\)/)
  assert.doesNotMatch(FORM, /toISOString\(\)\.slice/)
  assert.doesNotMatch(FORM, /replace\(['"]T['"], ['"] ['"]\)/)
})

test('回填使用页面操作人并保留备注', () => {
  assert.match(FORM, /verified_by: reviewer/)
  assert.match(FORM, /notes: notes\.value\.trim\(\) \|\| null/)
})

test('详情按 revision 区间展示验证历史', () => {
  assert.match(DETAIL, /verification_history_json/)
  assert.match(DETAIL, /r\{\{ entry\.revision_from \}\} → r\{\{ entry\.revision_to \}\}/)
  assert.match(DETAIL, /entry\.closed_loop \? '闭环' : '未闭环'/)
})

test('保存后刷新详情并通知工作台', () => {
  assert.match(DETAIL, /const onVerificationSaved = async \(\) => \{\s*await load\(\)\s*bumpCaseVersion\(\)/)
})
