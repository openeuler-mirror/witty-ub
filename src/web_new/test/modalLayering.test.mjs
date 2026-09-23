import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { join, relative } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const srcDir = fileURLToPath(new URL('../src', import.meta.url))
const read = (path) => readFileSync(path, 'utf8')

const vueFilesUnder = (dir) =>
  readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) return vueFilesUnder(path)
    return entry.name.endsWith('.vue') ? [path] : []
  })

test('弹窗遮罩只能由 BaseModal 渲染', () => {
  const offenders = vueFilesUnder(srcDir)
    .filter((path) => !path.endsWith('common/BaseModal.vue'))
    .filter((path) => read(path).includes('modal-overlay'))
    .map((path) => relative(srcDir, path))

  assert.deepEqual(
    offenders,
    [],
    '禁止手写 .modal-overlay：请改用 components/common/BaseModal.vue，' +
      '否则会丢失文档滚动锁、滚动链隔离与 Esc 层级处理',
  )
})

test('弹窗滚动隔离：滚动锁类名与样式、滚动链护栏必须同时存在', () => {
  const css = read(join(srcDir, 'assets/main.css'))
  const layer = read(join(srcDir, 'composables/useModalLayer.ts'))
  const baseModal = read(join(srcDir, 'components/common/BaseModal.vue'))

  const lockClass = layer.match(/SCROLL_LOCK_CLASS = '([^']+)'/)?.[1]
  assert.ok(lockClass, 'useModalLayer 必须定义滚动锁类名')
  assert.match(
    css,
    new RegExp(`html\\.${lockClass}\\s*\\{[^}]*overflow:\\s*hidden`, 's'),
    `main.css 缺少 html.${lockClass} 的滚动锁样式，弹窗打开时背景仍可滚动`,
  )
  assert.match(
    css,
    /\.modal-overlay\s*\{[^}]*overscroll-behavior:\s*none/s,
    '遮罩层需要 overscroll-behavior: none，避免指针停在遮罩上时滚动背景',
  )
  assert.match(
    css,
    /\.modal-overlay \.modal-body\s*\{[^}]*overscroll-behavior:\s*contain/s,
    '弹窗内容区需要 overscroll-behavior: contain，避免滚动链传给背后页面',
  )
  assert.doesNotMatch(
    css,
    /\.modal-overlay \*\s*\{/,
    '不要给弹窗内所有元素加 overscroll-behavior：表格等无滚内容的容器会吞掉滚轮手势',
  )
  assert.doesNotMatch(
    css,
    new RegExp(`html\\.${lockClass}\\s*\\{[^}]*overscroll-behavior`, 's'),
    '滚动锁不要设置 overscroll-behavior：根容器上写 none 会连带关闭弹窗内容区的弹性回弹，' +
      '冻结页面位置用 overflow: hidden 即可',
  )
  assert.match(baseModal, /useModalLayer/, 'BaseModal 必须接入 useModalLayer，否则不会锁定文档滚动')
})
