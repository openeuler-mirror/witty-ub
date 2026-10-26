import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), 'utf8')

const OVERVIEW = read('../src/components/knowledge/AllCasesSection.vue')
const HUB = read('../src/components/knowledge/KnowledgeHubPage.vue')

test('统一入口按来源切换，诊断与文件案例不混用列表', () => {
  assert.match(HUB, /📚 案例库/)
  assert.doesNotMatch(HUB, /📋 文件案例/)
  assert.doesNotMatch(HUB, /🧭 诊断案例/)
  for (const label of ['全部来源', '诊断案例', '文件案例']) {
    assert.ok(HUB.includes(label), `缺少来源入口：${label}`)
  }
})

test('统一列表从两种来源聚合', () => {
  assert.match(OVERVIEW, /searchDiagCases\(\{ pageCnt: 200 \}\)/)
  assert.match(OVERVIEW, /fetchCases\(\)/)
  assert.match(OVERVIEW, /const merged = \[\.\.\.diagRows, \.\.\.legacyRows\]/)
})

test('行标识带来源前缀，避免新旧 ID 混用', () => {
  assert.match(OVERVIEW, /key: `diagnosis:\$\{item\.id\}`/)
  assert.match(OVERVIEW, /key: `legacy:\$\{item\.id\}`/)
})

test('文件案例保持只读，诊断案例才可打开详情', () => {
  assert.match(
    OVERVIEW,
    /if \(row\.source === 'diagnosis'\) \{\s*openCase\(row\.id\)/,
  )
  assert.match(OVERVIEW, /v-if="row\.source === 'diagnosis'"/)
})

test('旧案例沿用旧分类体系与固定信任标签', () => {
  assert.match(
    OVERVIEW,
    /\[item\.case_category \|\| '未分类', item\.root_cause_type\]/,
  )
  assert.match(OVERVIEW, /trust: '旧案例未验证'/)
  assert.doesNotMatch(OVERVIEW, /legacy_unverified/)
})

test('诊断案例确认或验证后聚合列表刷新', () => {
  assert.match(OVERVIEW, /watch\(caseVersion, \(\) => void load\(\)\)/)
})

test('诊断案例的分类与验证口径与诊断列表一致', () => {
  assert.match(OVERVIEW, /item\.label_taxonomy_version \? '未分类' : '未分类 \/ 来源待核对'/)
  assert.match(OVERVIEW, /item\.verification_json\?\.closed_loop \? '已验证' : '已确认未验证'/)
})
