import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const APP_VUE = readFileSync(resolve(HERE, '../src/App.vue'), 'utf8')
const MAIN_CSS = readFileSync(resolve(HERE, '../src/assets/main.css'), 'utf8')

test('故障模式图使用有界视口，而不是按完整图尺寸扩张 Canvas', () => {
  assert.doesNotMatch(APP_VUE, /brpcThreadFailureGraph(?:Width|Height)/)
  assert.doesNotMatch(APP_VUE, /width:\s*layout\.dataWidth/)
  assert.doesNotMatch(APP_VUE, /height:\s*layout\.dataHeight/)
  assert.doesNotMatch(APP_VUE, /\bdata(?:Width|Height),/)
  assert.match(
    MAIN_CSS,
    /\.brpc-thread-failure-graph-viewport\s*\{[^}]*height:\s*clamp\(420px, 62vh, 680px\)/s,
  )
  assert.match(MAIN_CSS, /\.brpc-thread-failure-graph\s*\{[^}]*width:\s*100%;[^}]*height:\s*100%/s)
})

test('大图保留全部节点和边，但跳过高成本精细避障', () => {
  assert.match(APP_VUE, /BRPC_THREAD_GRAPH_DETAILED_ROUTING_MAX_NODES = 120/)
  assert.match(APP_VUE, /if \(!useDetailedEdgeRouting\) return/)
  assert.match(APP_VUE, /data: \[\.\.\.chartNodes, \.\.\.chartBoundaryNodes\]/)
  assert.match(APP_VUE, /links: chartLinks/)
  assert.match(APP_VUE, /nodeScaleRatio: 0\.05/)
  assert.match(APP_VUE, /left: layout\.viewportPaddingX/)
  assert.match(APP_VUE, /top: layout\.viewportPaddingY/)
  assert.match(APP_VUE, /preserveAspect: true/)
  assert.match(APP_VUE, /scaleLimit: \{ min: 0\.2, max: 50 \}/)
})

test('图布局复用 computed 缓存且渲染失败有可见提示', () => {
  assert.match(APP_VUE, /const layout = brpcThreadFailureGraphLayout\.value/)
  assert.doesNotMatch(APP_VUE, /const layout = getBrpcThreadFailureGraphLayout\(graph\)/)
  assert.match(APP_VUE, /brpcThreadFailureGraphRenderError\.value\s*=/)
  assert.match(APP_VUE, /v-else-if="brpcThreadFailureGraphRenderError"/)
})
