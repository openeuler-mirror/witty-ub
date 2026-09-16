import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(
  new URL('../src/components/agent/AgentChatPanel.vue', import.meta.url),
  'utf8',
)
const style = source.slice(source.indexOf('<style scoped>'))

// 取规则块；hint 用来跳过同名选择器的重置/媒体查询块
const ruleBlock = (selector, hint) => {
  let start = style.indexOf(`${selector} {`)
  while (start > 0) {
    const block = style.slice(start, style.indexOf('}', start))
    if (!hint || block.includes(hint)) return block
    start = style.indexOf(`${selector} {`, start + 1)
  }
  assert.fail(`找不到 ${selector} 规则${hint ? `（含 ${hint}）` : ''}`)
}

// 用户报障：鼠标停在面板头部、会话区顶栏、输入区滚动时，手势穿透到面板背后的页面。
// 根因：面板外壳只是 overflow: hidden（内容不溢出、滚不动），也没有 overscroll-behavior，
// 滚轮沿祖先链一路交给文档；对话区正常是因为它自己带了 contain。
test('Agent 面板外壳阻断滚动链，滚轮不穿透到背后页面', () => {
  const panel = ruleBlock('.agent-chat-panel', 'position: fixed')

  assert.match(panel, /overflow:\s*hidden/, '面板需要 overflow: hidden 才能裁切变形过程')
  assert.match(
    panel,
    /overscroll-behavior:\s*contain/,
    '缺少 overscroll-behavior: contain 时，头部/会话区顶栏/输入区的滚轮会把页面滚走',
  )
})

// 外壳阻断链的前提是「面板内该滚的地方仍然能滚」：这些区域必须继续各自 contain
test('面板内的滚动区保留自身的 overscroll-behavior: contain', () => {
  const scrollers = [
    ['.agent-auth-page', 'overflow-y: auto'],
    ['.agent-option-list', 'overflow-y: auto'],
    ['.agent-session-list', 'overflow-y: auto'],
    ['.agent-chat-messages', 'overflow-y: auto'],
  ]

  for (const [selector, hint] of scrollers) {
    assert.match(
      ruleBlock(selector, hint),
      /overscroll-behavior:\s*contain/,
      `${selector} 需要自己阻断滚动链，否则滚到边界会带动页面`,
    )
  }
})
