import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const app = readFileSync(new URL('../src/App.vue', import.meta.url), 'utf8')
const loaderSource = app.slice(
  app.indexOf('const loadCaseLibrary = async () => {'),
  app.indexOf('const loadCategories = async () => {'),
)
const { outputText } = ts.transpileModule(loaderSource, {
  compilerOptions: { target: ts.ScriptTarget.ES2022 },
})

const createLoader = (request) => {
  const state = {
    caseLibrary: { value: [] },
    caseCategories: { value: [] },
    caseLibraryActiveTab: { value: '' },
    caseLibraryLoading: { value: false },
    caseLibraryError: { value: '上次加载失败' },
  }
  const load = new Function('request', ...Object.keys(state), `${outputText}; return loadCaseLibrary`)(
    request, ...Object.values(state),
  )
  return { state, load }
}

for (const failedPath of ['/case_library/list', '/case_library/categories']) {
  test(`failure of ${failedPath} is shown instead of an empty library`, async () => {
    const { state, load } = createLoader(async (path) => {
      if (path === failedPath) throw new Error('请求失败：502')
      return []
    })
    await load()
    assert.equal(state.caseLibraryError.value, '请求失败：502')
    assert.equal(state.caseLibraryLoading.value, false)
    assert.deepEqual(state.caseLibrary.value, [])
    assert.deepEqual(state.caseCategories.value, [])
  })
}

test('successful loading clears the previous error and selects all cases', async () => {
  const cases = [{ id: 'case-1', root_cause_type: 'timeout' }]
  const categories = [{ id: 'cat-1', types: [{ name: 'timeout' }] }]
  const { state, load } = createLoader(async (path) =>
    path.endsWith('/list') ? cases : categories,
  )
  await load()
  assert.equal(state.caseLibraryError.value, '')
  assert.equal(state.caseLibraryLoading.value, false)
  assert.equal(state.caseLibrary.value, cases)
  assert.equal(state.caseCategories.value, categories)
  assert.equal(state.caseLibraryActiveTab.value, '__all__')
})
