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

// 用户诉求：点击后直接从按钮过渡到弹窗，由按钮变成 Agent 窗口。
// 变形起点必须是按钮的矩形，因此面板与 FAB 的右下角必须共点（否则 scale 后落不到按钮上）。
test('Agent 面板与 FAB 右下角共点，可从按钮处变形', () => {
  const fab = ruleBlock('.agent-fab', 'position: fixed')
  const panel = ruleBlock('.agent-chat-panel', 'position: fixed')

  assert.match(fab, /right:\s*28px/, 'FAB 的 right 是对齐基准')
  assert.match(fab, /bottom:\s*26px/, 'FAB 的 bottom 是对齐基准')
  assert.match(panel, /right:\s*28px/, '面板 right 必须与 FAB 相同，右下角才会共点')
  assert.match(panel, /bottom:\s*26px/, '面板 bottom 必须与 FAB 相同，不再为按钮留出下方空间')
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

// 用户诉求：节省屏幕空间——按钮变成窗口后不再与窗口同屏各占一块。
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

// 用户诉求：把 Agent 弹窗做大一点（旧值 980×800 / min-height 420）。
test('Agent 面板默认尺寸已放大', () => {
  const panel = ruleBlock('.agent-chat-panel', 'position: fixed')
  const width = Number(panel.match(/width:\s*min\((\d+)px/)?.[1])
  const height = Number(panel.match(/height:\s*min\((\d+)px/)?.[1])
  const minHeight = Number(panel.match(/min-height:\s*min\((\d+)px/)?.[1])

  assert.ok(width >= 1200, `面板默认宽度应不小于 1200px，当前 ${width}`)
  assert.ok(height >= 860, `面板默认高度应不小于 860px，当前 ${height}`)
  assert.ok(minHeight >= 520, `面板最小高度应不小于 520px，当前 ${minHeight}`)
})
