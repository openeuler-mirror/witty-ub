import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), 'utf8')

const SECTION = read('../src/components/knowledge/DiagCaseSection.vue')
const DETAIL = read('../src/components/knowledge/DiagCaseDetailModal.vue')
const API = read('../src/api/diagCaseLibrary.ts')

test('二级分类选项依赖一级分类', () => {
  assert.match(SECTION, /taxonomy\.value\?\.pairs\.find/)
  assert.match(SECTION, /pair\?\.second_level_labels \?\? \[\]/)
  assert.match(SECTION, /:disabled="!firstLabel \|\| unclassifiedOnly"/)
})

test('切换一级分类会清空二级分类并重新检索', () => {
  assert.match(SECTION, /const changeFirst = \(\) => \{\s*secondLabel\.value = ''/)
})

test('仅未分类过滤会清空分类条件并传给后端', () => {
  assert.match(SECTION, /const changeUnclassified = \(\) => \{[\s\S]*firstLabel\.value = ''[\s\S]*secondLabel\.value = ''/)
  assert.match(API, /if \(params\.unclassifiedOnly\) body\.unclassified_only = true/)
})

test('分类空值区分未分类与来源待核对', () => {
  assert.match(SECTION, /item\.label_taxonomy_version \? '未分类' : '未分类 \/ 来源待核对'/)
  assert.match(DETAIL, /item\?\.label_taxonomy_version \? '未分类' : '未分类 \/ 来源待核对'/)
})

test('案例状态与验证状态分开展示', () => {
  assert.match(SECTION, /item\.status !== 'confirmed'.*未确认/s)
  assert.match(DETAIL, /verificationText/)
  assert.match(SECTION, /\{\{ item\.case\.status \}\}/)
})

test('来源导航覆盖五种状态且只对当前版本开放跳转', () => {
  for (const [status, text] of [
    ['valid', '源报告当前版本有效'],
    ['stale', '源报告版本已变化'],
    ['deleted', '源报告不可用'],
    ['unavailable', '暂时无法校验源报告'],
    ['independent', '无关联报告'],
  ]) {
    assert.ok(DETAIL.includes(`${status}: '${text}'`), `缺少来源状态：${status}`)
  }
  assert.match(DETAIL, /source\.value\?\.status === 'valid' && source\.value\.report_id/)
})

test('案例列表只对有效来源报告开放跳转', () => {
  assert.match(SECTION, /item\.case\.report_id && item\.source_report\?\.status === 'valid'/)
  assert.match(SECTION, /@click="openReport\(item\.case\.report_id, item\.case\.source_fault_id \?\? ''\)"/)
  assert.match(SECTION, /reportStatusText\(item\.source_report\?\.status\)/)
})
