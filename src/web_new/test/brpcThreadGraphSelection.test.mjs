import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const css = readFileSync(new URL('../src/assets/main.css', import.meta.url), 'utf8')
const panelSource = readFileSync(
  new URL('../src/components/overview/OverviewPanel.vue', import.meta.url),
  'utf8',
)

// 取单个 CSS 规则块：选择器与 `{` 紧邻，避免命中同前缀的长选择器（如 .graph-node-interface）
const ruleBlock = (selector) => {
  const start = css.indexOf(`${selector} {`)
  assert.ok(start >= 0, `找不到 ${selector} 规则`)
  return css.slice(start, css.indexOf('}', start))
}

// 回归：故障模式视图里点选节点后，选中节点必须与接口节点可区分。
// 若 .graph-node.active 把描边色改成主色蓝，故障模式节点（红）会被刷成蓝框白底 = 接口节点同貌。
test('节点选中态不得改写类型描边色，改用墨色外环', () => {
  const active = ruleBlock('.graph-node.active')

  assert.doesNotMatch(
    active,
    /border-color\s*:/,
    '选中态改描边色会抹掉类型语义（红=故障模式 / 蓝=接口），只能加外环',
  )
  assert.match(active, /outline:\s*2px solid #0f172a/, '选中态用墨色外环表达')
  assert.match(active, /outline-offset:\s*2px/, '外环与节点留 2px 间隙，避免与类型描边糊在一起')
})

test('选中态保留类型底色，接口与故障模式节点仍可区分', () => {
  assert.match(ruleBlock('.graph-node-interface.active'), /background:\s*#e8f1ff/)
  assert.match(ruleBlock('.graph-node-mode.active'), /background:\s*#fdecec/)
})

test('图例与详情卡同步「选中节点」语义', () => {
  assert.match(panelSource, /graph-legend-selected/, '图例必须给出选中节点色块')
  assert.match(
    css,
    /\.graph-legend-selected\s*\{[^}]*outline:\s*2px solid #0f172a/,
    '图例色块要画出墨色外环，才和图上的选中态一致',
  )
  assert.match(panelSource, /墨色外环=已选中/, '图例提示要说明外环含义')

  assert.match(panelSource, /graph-node-detail-interface/, '选中详情卡按节点类型区分配色')
  assert.match(panelSource, /graph-node-detail-mode/)
  assert.match(ruleBlock('.graph-node-detail-interface'), /background:\s*#eff6ff/)
  assert.match(ruleBlock('.graph-node-detail-mode'), /background:\s*#fef2f2/)
  assert.match(
    panelSource,
    /graph-node-type-chip-interface/,
    '详情卡要标明「接口节点 / 故障模式节点」',
  )
  assert.match(panelSource, /graph-node-type-chip-mode/)
  assert.match(
    panelSource,
    /:aria-pressed="brpcSelectedGraphNodeId === node\.id"/,
    '节点按钮要用 aria-pressed 暴露选中态',
  )
})
