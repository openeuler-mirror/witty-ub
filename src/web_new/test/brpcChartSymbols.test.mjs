import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const srcDir = fileURLToPath(new URL('../src', import.meta.url))
const read = (path) => readFileSync(path, 'utf8')

// 用户报障：旧版每个数据点上都有小圆圈，新版把 symbol 关成了 none，单点取值很难辨认。
// 这里守住「UBSocket 接口监控四张线图必须走同一个带 symbol 的样式常量」。
test('UBSocket 接口监控曲线保留数据点圆圈', () => {
  const source = read(join(srcDir, 'composables/useOverviewData.ts'))

  assert.match(
    source,
    /const brpcLineSymbol = \{[^}]*showSymbol: true[^}]*symbol: 'circle'[^}]*symbolSize: \d+[^}]*\}/s,
    '必须定义 brpcLineSymbol（showSymbol + circle + symbolSize）',
  )

  const renderers = [
    'renderBrpcSuccessOverviewChart',
    'renderBrpcSingleChart',
    'renderBrpcLatencyChart',
    'renderBrpcLatencyMonitorChart',
  ]
  for (const name of renderers) {
    const start = source.indexOf(`const ${name} = `)
    assert.ok(start > 0, `找不到 ${name}`)
    const body = source.slice(start, source.indexOf('\n  const render', start + 1) + 1)
    assert.match(body, /\.\.\.brpcLineSymbol/, `${name} 的曲线必须展开 brpcLineSymbol`)
    assert.doesNotMatch(body, /symbol: 'none'/, `${name} 不得再把曲线 symbol 关掉`)
  }
})
