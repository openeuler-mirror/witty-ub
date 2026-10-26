import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), 'utf8')

const OVERVIEW = read('../src/components/knowledge/AllCasesSection.vue')
const HUB = read('../src/components/knowledge/KnowledgeHubPage.vue')
const LEGACY = read('../src/components/knowledge/CaseLibrarySection.vue')
const LEGACY_STATE = read('../src/composables/useCaseLibrary.ts')

test('统一入口按来源切换，诊断与文件案例不混用列表', () => {
  assert.match(HUB, /📚 案例库/)
  assert.doesNotMatch(HUB, /📋 文件案例/)
  assert.doesNotMatch(HUB, /🧭 诊断案例/)
  for (const label of ['全部来源', '诊断案例', '文件案例']) {
    assert.ok(HUB.includes(label), `缺少来源入口：${label}`)
  }
})

test('统一列表分页加载两种来源，不截断超出单页的案例', () => {
  assert.match(OVERVIEW, /const DIAG_PAGE_SIZE = 200/)
  assert.match(OVERVIEW, /do \{[\s\S]*pageNum[\s\S]*pageCnt: DIAG_PAGE_SIZE/)
  assert.match(OVERVIEW, /while \(collected\.length < total\)/)
  assert.match(OVERVIEW, /fetchCases\(\)/)
  assert.match(OVERVIEW, /const merged = \[\.\.\.diagRows, \.\.\.legacyRows\]/)
})

test('统一列表按固定页大小渲染并提供翻页', () => {
  assert.match(OVERVIEW, /const PAGE_SIZE = 50/)
  assert.match(OVERVIEW, /const totalPages = computed/)
  assert.match(OVERVIEW, /const pagedRows = computed/)
  assert.match(OVERVIEW, /v-for="row in pagedRows"/)
  assert.match(OVERVIEW, /<PageNav v-if="rows\.length > PAGE_SIZE"/)
  assert.match(OVERVIEW, /共 \{\{ rows\.length \}\} 条/)
})

test('行标识带来源前缀，避免新旧 ID 混用', () => {
  assert.match(OVERVIEW, /key: `diagnosis:\$\{match\.case\.id\}`/)
  assert.match(OVERVIEW, /key: `legacy:\$\{item\.id\}`/)
})

test('文件案例保持只读，诊断案例才可打开详情', () => {
  assert.match(
    OVERVIEW,
    /if \(row\.source === 'diagnosis'\) \{\s*openCase\(row\.id\)/,
  )
  assert.match(OVERVIEW, /v-if="row\.source === 'diagnosis'"/)
})

test('来源报告只在当前版本有效时提供链接', () => {
  assert.match(OVERVIEW, /reportStatus: match\.source_report\?\.status \?\? 'unavailable'/)
  assert.match(OVERVIEW, /row\.reportId && row\.reportStatus === 'valid'/)
  assert.match(OVERVIEW, /reportStatusText\(row\.reportStatus\)/)
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

test('文件案例分栏与旧前端一致，只保留查看能力', () => {
  assert.match(LEGACY, /caseAttachmentUrl\(c\.id\)/)
  assert.doesNotMatch(LEGACY, /startEditCase|removeCase|saveEditCase/)
  assert.doesNotMatch(LEGACY, /新建分类|修改分类|删除分类/)
  assert.doesNotMatch(LEGACY_STATE, /updateCase|deleteCase|updateCategory|deleteCategory|updateType|deleteType/)
})
