import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const srcDir = fileURLToPath(new URL('../src', import.meta.url))
const read = (path) => readFileSync(path, 'utf8')

const rendererNames = [
  'renderBrpcSuccessOverviewChart',
  'renderBrpcSingleChart',
  'renderBrpcLatencyChart',
  'renderBrpcLatencyMonitorChart',
]

const rendererBody = (source, name) => {
  const start = source.indexOf(`const ${name} = `)
  assert.ok(start > 0, `找不到 ${name}`)
  return source.slice(start, source.indexOf('\n  const render', start + 1) + 1)
}

// 用户报障：旧版每个数据点上都有小圆圈，新版把 symbol 关成了 none，单点取值很难辨认。
// 这里守住「UBSocket 接口监控四张线图必须走同一个带 symbol 的样式常量」。
test('UBSocket 接口监控曲线保留数据点圆圈', () => {
  const source = read(join(srcDir, 'composables/useOverviewData.ts'))

  assert.match(
    source,
    /const brpcLineSymbol = \{[^}]*showSymbol: true[^}]*symbol: 'circle'[^}]*symbolSize: \d+[^}]*\}/s,
    '必须定义 brpcLineSymbol（showSymbol + circle + symbolSize）',
  )

  for (const name of rendererNames) {
    const body = rendererBody(source, name)
    assert.match(body, /\.\.\.brpcLineSymbol/, `${name} 的曲线必须展开 brpcLineSymbol`)
    assert.doesNotMatch(body, /symbol: 'none'/, `${name} 不得再把曲线 symbol 关掉`)
  }
})

// 用户报障：tooltip 被「全接口总览」卡片边框裁切；且悬停具体数据点时应进一步过滤。
// 守住「四张图共用 brpcAxisTooltip：挂 body + 按窗口夹取 + 点级命中」。
test('UBSocket 接口监控 tooltip 挂 body、按视口夹取且支持点级过滤', () => {
  const source = read(join(srcDir, 'composables/useOverviewData.ts'))
  const start = source.indexOf('const brpcAxisTooltip = ')
  assert.ok(start > 0, '必须定义 brpcAxisTooltip')
  const helper = source.slice(start, source.indexOf('\n  const render', start))

  assert.match(helper, /appendToBody: true/, 'tooltip 必须挂到 body，否则会被卡片 overflow 裁切')
  assert.match(helper, /position: \(/, 'tooltip 必须自定义 position')
  assert.match(helper, /window\.innerHeight/, 'position 必须按浏览器窗口夹取（图表画布比 21 行列表矮）')
  assert.match(helper, /BRPC_TOOLTIP_POINT_RADIUS/, '必须有数据点命中半径')
  assert.match(helper, /convertToPixel/, '点级过滤要用数据点像素位置判断光标是否落在点上')
  assert.doesNotMatch(
    helper,
    /transitionDuration: 0/,
    '不得关掉 tooltip 的位移/淡入过渡（关闭动画只针对图表本身）',
  )
  assert.match(helper, /hideDelay: 0/, '光标离开后必须立即隐藏，不留驻留时间')

  for (const name of rendererNames) {
    assert.match(
      rendererBody(source, name),
      /tooltip: brpcAxisTooltip\(chart/,
      `${name} 必须使用 brpcAxisTooltip`,
    )
  }
})
