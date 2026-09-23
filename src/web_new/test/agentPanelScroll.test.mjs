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

// 面板外壳不是滚动容器：自身阻断滚动链后，滚轮不会沿祖先链落到文档
test('Agent 面板外壳阻断滚动链，滚轮不穿透到背后页面', () => {
  const panel = ruleBlock('.agent-chat-panel', 'position: fixed')

  assert.match(panel, /overflow:\s*hidden/, '面板需要 overflow: hidden 才能裁切变形过程')
  assert.match(panel, /overscroll-behavior:\s*contain/, '面板外壳需要阻断滚动链')
})

// 面板内的滚动区域各自阻断滚动链
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
      `${selector} 需要自己阻断滚动链`,
    )
  }
})

// 工具条在滚动区之外，卡片区独立滚动
test('会话工具条固定，卡片区独立滚动', () => {
  const manager = ruleBlock('.agent-session-manager', 'flex-direction: column')
  const toolbar = ruleBlock('.agent-session-toolbar', 'align-items: center')
  const list = ruleBlock('.agent-session-list', 'overflow-y: auto')

  assert.doesNotMatch(manager, /overflow-y:\s*auto/, '工具条应位于滚动区之外')
  assert.match(toolbar, /flex:\s*0 0 auto/, '工具条不参与伸缩')
  assert.match(list, /overscroll-behavior:\s*contain/, '卡片区需要阻断滚动链')
  assert.match(list, /flex:\s*1 1 auto/, '卡片区撑满工具条以下的面积')
  assert.match(list, /min-height:\s*0/, '缺少 min-height: 0 时 flex 会压扁卡片而非滚动')
})
