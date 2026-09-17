// 坏日志跳过告警：① 纯逻辑（从任务报告里挑 `[skip]`）② App.vue 里那段模板的真实 SSR 渲染。
// 模板是从 App.vue 源码里切出来的，所以模板本身也被测到，而不只是纯函数。
import assert from 'node:assert/strict'
import test from 'node:test'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { compile } from '@vue/compiler-dom'
import * as Vue from 'vue'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { collectSkippedFileAlerts, SKIPPED_REPORT_PREFIX } from '../src/utils/skipAlerts.ts'

// ── ① 纯逻辑 ────────────────────────────────────────────────────────────
test('跳过告警：只挑 [skip] 前缀的报告，去掉前缀后原样返回', () => {
  const alerts = collectSkippedFileAlerts([
    { message: 'Task initialized' },
    { message: '[skip] 跳过 2 个坏日志文件：a.log.gz（OSError: unexpected end of file）；b.log（ComputeError: invalid utf8）' },
    { message: '[timing] {"total_s":1.2}' },
  ])
  assert.equal(alerts.length, 1)
  assert.equal(
    alerts[0],
    '跳过 2 个坏日志文件：a.log.gz（OSError: unexpected end of file）；b.log（ComputeError: invalid utf8）',
  )
  assert.ok(!alerts[0].includes(SKIPPED_REPORT_PREFIX), '展示文案里不应再带 [skip] 前缀')
})

test('跳过告警：没有报告 / 空列表 / 空 message / null 都不产生告警', () => {
  assert.deepEqual(collectSkippedFileAlerts(undefined), [])
  assert.deepEqual(collectSkippedFileAlerts(null), [])
  assert.deepEqual(collectSkippedFileAlerts([]), [])
  assert.deepEqual(collectSkippedFileAlerts([{ message: null }, { message: '   ' }, {}]), [])
  assert.deepEqual(collectSkippedFileAlerts([{ message: '[skip]    ' }]), [], '只有前缀没有内容 → 不算告警')
})

test('跳过告警：前缀必须在开头，正文里出现不算', () => {
  const alerts = collectSkippedFileAlerts([
    { message: '解析完成，详见 [skip] 记录' },
    { message: 'skip 前缀缺方括号' },
  ])
  assert.deepEqual(alerts, [])
})

// ── ② 模板渲染 ──────────────────────────────────────────────────────────
const APP_VUE = resolve(dirname(fileURLToPath(import.meta.url)), '../src/App.vue')

const readAppVue = () => {
  const candidates = [
    APP_VUE,
    resolve(process.cwd(), 'src/App.vue'),
    resolve(process.cwd(), 'src/web/src/App.vue'),
  ]
  for (const candidate of candidates) {
    if (existsSync(candidate)) return readFileSync(candidate, 'utf8')
  }
  throw new Error(`找不到 App.vue，试过：${candidates.join(' / ')}（请在 src/web 下运行）`)
}

const ALERT_START = '<div v-if="hasSkippedFileAlerts(file)" class="log-file-skip-alert" role="alert">'

/** 从 App.vue 源码里切出告警那一段（按 <div>/</div> 配平）。 */
const extractSkipAlert = (source) => {
  const start = source.indexOf(ALERT_START)
  assert.notEqual(start, -1, `App.vue 里找不到告警模板，测试需要同步更新：${ALERT_START}`)
  const tags = /<div[\s>]|<\/div>/g
  tags.lastIndex = start
  let depth = 0
  for (let match = tags.exec(source); match; match = tags.exec(source)) {
    depth += match[0] === '</div>' ? -1 : 1
    if (depth === 0) return source.slice(start, match.index + match[0].length)
  }
  throw new Error('告警模板的 <div> 没有配平')
}

const alertTemplate = extractSkipAlert(readAppVue())
const { code } = compile(alertTemplate, { mode: 'function', prefixIdentifiers: true })
const alertRender = new Function('Vue', code)(Vue)
assert.equal(typeof alertRender, 'function', '告警模板编译失败')

const stripComments = (html) => html.replace(/<!--[\s\S]*?-->/g, '')

const renderItem = async (taskReports) => {
  const file = { id: 'f1', name: 'demo', task: { id: 't1', task_reports: taskReports } }
  return stripComments(
    await renderToString(
      createSSRApp({
        render: alertRender,
        setup: () => ({
          file,
          getSkippedFileAlerts: (target) => collectSkippedFileAlerts(target.task?.task_reports),
          hasSkippedFileAlerts: (target) => collectSkippedFileAlerts(target.task?.task_reports).length > 0,
        }),
      }),
    ),
  )
}

test('模板渲染：有 [skip] 报告 → 渲染出告警条与逐条文案', async () => {
  const html = await renderItem([
    { message: 'Task initialized' },
    { message: '[skip] 跳过 1 个坏日志文件：ds_client_access_9999.log.gz（OSError: unexpected end of file）' },
  ])
  assert.match(html, /class="log-file-skip-alert"/)
  assert.match(html, /role="alert"/)
  assert.match(html, /已跳过读不出来的日志文件/)
  assert.match(
    html,
    /跳过 1 个坏日志文件：ds_client_access_9999\.log\.gz（OSError: unexpected end of file）/,
  )
  assert.equal((html.match(/log-file-skip-alert-line/g) ?? []).length, 1)
  assert.doesNotMatch(html, /\[skip\]/, '前缀不该出现在页面上')
})

test('模板渲染：没有 [skip] 报告 → 整块不渲染', async () => {
  const html = await renderItem([{ message: 'Task initialized' }, { message: 'Task completed successfully' }])
  assert.equal(html.trim(), '', `没有告警时不该有输出，实际：${JSON.stringify(html)}`)
})

test('模板渲染：多条跳过告警逐条渲染', async () => {
  const html = await renderItem([
    { message: '[skip] 跳过 2 个坏日志文件：a.gz（OSError）；b.log（ComputeError）' },
    { message: '[skip] 跳过 1 个坏日志文件：c.gz（OSError）' },
  ])
  assert.equal((html.match(/log-file-skip-alert-line/g) ?? []).length, 2)
  assert.match(html, /a\.gz/)
  assert.match(html, /c\.gz/)
})
