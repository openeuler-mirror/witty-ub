import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const panelSource = readFileSync(
  new URL('../src/components/agent/AgentChatPanel.vue', import.meta.url),
  'utf8',
)
const script = panelSource.slice(0, panelSource.indexOf('<template>'))
const style = panelSource.slice(panelSource.indexOf('<style scoped>'))

// 取单个 CSS 规则块：要求 `选择器 {` 紧邻（避免命中 `.agent-fab svg {` 之类），
// hint 用来跳过同名选择器的重置/媒体查询块
const ruleBlock = (selector, hint) => {
  let start = style.indexOf(`${selector} {`)
  while (start > 0) {
    const end = style.indexOf('}', start)
    const block = style.slice(start, end)
    if (!hint || block.includes(hint)) return block
    start = style.indexOf(`${selector} {`, start + 1)
  }
  assert.fail(`找不到 ${selector} 规则${hint ? `（含 ${hint}）` : ''}`)
}

// 取一条 @media 块的完整内容（按花括号配对，避免只看第一行）
const mediaBlock = (maxWidth) => {
  const start = style.indexOf(`@media (max-width: ${maxWidth}px) {`)
  assert.ok(start > 0, `找不到 @media (max-width: ${maxWidth}px)`)
  let depth = 0
  for (let index = style.indexOf('{', start); index < style.length; index += 1) {
    if (style[index] === '{') depth += 1
    if (style[index] === '}') {
      depth -= 1
      if (depth === 0) return style.slice(start, index)
    }
  }
  assert.fail(`@media (max-width: ${maxWidth}px) 花括号不配对`)
}

// 贴边距离：按钮 距右/下 16px；面板 左/右/下 8px、上 12px
test('Agent 按钮与面板的贴边距离', () => {
  const fab = ruleBlock('.agent-fab', 'position: fixed')
  const panel = ruleBlock('.agent-chat-panel', 'position: fixed')

  assert.match(fab, /right:\s*16px/, '按钮距右边界')
  assert.match(fab, /bottom:\s*16px/, '按钮距下边界')
  assert.match(panel, /right:\s*8px/, '面板距右边界')
  assert.match(panel, /bottom:\s*8px/, '面板距下边界')
  assert.match(panel, /width:\s*calc\(100vw - 16px\)/, '面板宽度：左右各 8px')
  assert.match(panel, /height:\s*calc\(100vh - 20px\)/, '面板高度：上 12px、下 8px')

  assert.doesNotMatch(
    mediaBlock(900),
    /\.agent-chat-panel\s*\{/,
    '面板贴边距离只在基础规则里定义一次',
  )
  assert.doesNotMatch(mediaBlock(600), /(right|bottom):\s*\d+px/, '小屏断点只调整按钮尺寸')
})

// 变形起点是按钮矩形：折叠帧按矩形比例缩放，再用 translate 补齐两者右下角的偏差
test('Agent 面板可从按钮处变形，偏差由折叠帧补齐', () => {
  const fab = ruleBlock('.agent-fab', 'position: fixed')
  const panel = ruleBlock('.agent-chat-panel', 'position: fixed')

  assert.match(fab, /right:\s*16px/, '按钮矩形是折叠帧的基准')
  assert.match(fab, /bottom:\s*16px/)
  assert.match(panel, /right:\s*8px/, '面板矩形是折叠帧的另一基准')
  assert.match(panel, /bottom:\s*8px/)
  assert.match(
    panel,
    /transform-origin:\s*right\s+bottom/,
    '变形原点必须是右下角（按钮所在角），否则折叠帧会跑偏',
  )
  assert.match(
    panel,
    /overflow:\s*hidden/,
    '面板需要 overflow: hidden，变形过程中内容才会随窗口一起裁切',
  )
})

// 打开期间按钮隐藏，面板覆盖按钮所在角落
test('Agent 按钮打开期间让位给面板', () => {
  assert.match(panelSource, /'agent-fab-hidden':\s*fabHidden/, 'FAB 必须绑定隐藏态类名，打开时让位')
  assert.match(
    ruleBlock('.agent-fab-hidden'),
    /visibility:\s*hidden/,
    '隐藏态不能只靠 z-index：按钮与面板同角重叠，必须真正隐藏（且不可点）',
  )
  assert.match(ruleBlock('.agent-fab-hidden'), /pointer-events:\s*none/)

  const openPanel = script.slice(
    script.indexOf('const openPanel'),
    script.indexOf('const closePanel'),
  )
  assert.match(openPanel, /fabHidden\.value = true/, '打开面板时要隐藏 FAB')

  const closePanel = script.slice(
    script.indexOf('const closePanel'),
    script.indexOf('let restored'),
  )
  assert.match(closePanel, /fabHidden\.value = false/, '收拢动画结束后要恢复 FAB')
})

test('Agent 面板变形以按钮矩形为折叠帧，且不再叠加旧入场动画', () => {
  // 折叠帧 = 按两个方向的尺寸比 scale + 补齐右下角偏差
  assert.match(
    script,
    /const scaleX = fabRect\.width \/ panelRect\.width/,
    '折叠帧必须按按钮与面板的尺寸比缩放',
  )
  assert.match(script, /const scaleY = fabRect\.height \/ panelRect\.height/)
  assert.match(
    script,
    /translate\(\$\{fabRect\.right - panelRect\.right\}px/,
    '折叠帧必须补齐两个右下角的偏差',
  )
  // Chrome 不会补间 linear-gradient，色变靠「按钮色罩」的 opacity 补间实现
  assert.match(
    panelSource,
    /<span ref="tintRef" class="agent-panel-morph-tint"/,
    '变形需要一层与按钮同渐变的色罩，负责把按钮色化开成窗口',
  )
  const tint = ruleBlock('.agent-panel-morph-tint')
  assert.match(tint, /background:\s*linear-gradient\(145deg,\s*#4f8cff,\s*#4f46e5\)/)
  assert.match(tint, /opacity:\s*0/, '色罩静态必须透明，否则面板平时被盖住')
  assert.match(tint, /pointer-events:\s*none/)
  assert.match(script, /const tintEl = tintRef\.value/, '色罩 opacity 必须由变形动画驱动')
  assert.match(
    script,
    /from: 1,\s*to: 0,\s*duration: MORPH_TINT_OPEN_MS/,
    '打开时色罩由不透明淡出（按钮渐变 → 窗口白）',
  )
  assert.match(
    script,
    /from: 0,\s*to: 1,\s*duration: MORPH_CLOSE_MS/,
    '关闭时色罩回到不透明，终帧与按钮同色',
  )
  assert.match(
    script,
    /runMorph\(\[collapsed, panelFrame\(\)\], MORPH_OPEN_MS/,
    '打开必须从折叠帧补间到常规帧',
  )
  assert.match(
    script,
    /runMorph\(\[panelFrame\(\), collapsed\], MORPH_CLOSE_MS/,
    '关闭必须从常规帧补间回折叠帧（面板收回按钮）',
  )
  assert.match(script, /prefersReducedMotion/, '系统开启「减少动态效果」时应跳过变形动画')
  assert.doesNotMatch(
    style,
    /animation:\s*agent-panel-in/,
    '旧的 CSS 入场动画会与 JS 变形抢视觉，必须移除',
  )
})

// 面板尺寸 = 视口减贴边（左右 8px、上 12px、下 8px），宽度另有 1240px 上限
test('Agent 面板尺寸按视口减边距计算，宽度保留上限', () => {
  const panel = ruleBlock('.agent-chat-panel', 'position: fixed')

  assert.match(panel, /width:\s*calc\(100vw - 16px\)/)
  assert.match(panel, /height:\s*calc\(100vh - 20px\)/)
  assert.match(panel, /max-width:\s*1240px/, '宽屏下保留面板宽度上限')
  assert.match(panel, /max-height:\s*calc\(100vh - 20px\)/, '高度跟随贴边，不设固定上限')
  assert.match(script, /const PANEL_MAX_WIDTH = 1240/, '拖拽缩放的宽度上限与 CSS 同源')
  assert.match(script, /Math\.min\(PANEL_MAX_WIDTH, window\.innerWidth - 16\)/)
})
