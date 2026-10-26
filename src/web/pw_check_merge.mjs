import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1720, height: 1500 } })
const logs = []
page.on('console', (m) => {
  if (m.type() === 'error') logs.push(`[error] ${m.text().slice(0, 200)}`)
})
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message.slice(0, 200)}`))
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(2500)
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === '333')
  const target = els.find((e) => e.closest('button, [role="button"], a')) || els[0]
  ;(target.closest('button, [role="button"], a') || target).click()
})
await page.waitForTimeout(4000)
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim().includes('时延故障监控'))
  const target = els[0]
  if (target) (target.closest('button, a, li, [role="button"]') || target).click()
})
await page.waitForTimeout(15000)
const state = await page.evaluate(() => {
  const chartCard = document.querySelector('.monitor-card.top-slow-chart-card')
  const listCard = document.querySelector('.monitor-card.top-slow-trace-list-card')
  const table = chartCard?.querySelector('.top-slow-trace-table')
  const frame = chartCard?.querySelector('.top-slow-trace-frame')
  const chips = table ? [...table.querySelectorAll('.role-chip')].slice(0, 12).map((c) => ({ cls: c.className, txt: c.textContent.trim() })) : []
  const chipRoles = table ? [...new Set([...table.querySelectorAll('.role-chip')].map((c) => c.className))] : []
  const leftRows = table ? table.querySelectorAll('.aggregate-fixed-left > .aggregate-body-row').length : 0
  const dataHeaders = table ? [...table.querySelectorAll('.fault-trace-scroll-grid.aggregate-table-header .aggregate-cell')].map((c) => c.textContent.trim().split('\n')[0].trim()) : []
  const breakdownBars = table ? table.querySelectorAll('.latency-breakdown-bar').length : 0
  const breakdownSegments = table ? table.querySelectorAll('.latency-breakdown-segment').length : 0
  const pagination = table ? table.querySelector('.aggregate-pagination')?.textContent.trim() : ''
  const pageBtns = table ? [...table.querySelectorAll('.pagination-page-btn')].map((b) => b.textContent.trim()) : []
  const headerScrollbarVisible = table ? !!table.querySelector('.aggregate-latency-scrollbar .aggregate-latency-scrollbar-spacer') : false
  return {
    separateListCardExists: !!listCard,
    mergedTableInChartCard: !!table,
    chartCardTitles: chartCard ? [...chartCard.querySelectorAll('.monitor-card-title')].map((t) => t.textContent.trim().slice(0, 60)) : [],
    chipCount: chips.length,
    chipRoles,
    sampleChips: chips.slice(0, 6),
    leftRows,
    dataHeaders,
    breakdownBars,
    breakdownSegments,
    pagination,
    pageBtns,
    headerScrollbarVisible,
    frameMaxHeight: frame ? frame.style.maxHeight : '',
  }
})
console.log('STATE:', JSON.stringify(state, null, 2))
// 翻页测试：点击第 2 页
await page.evaluate(() => {
  const btns = [...document.querySelectorAll('.top-slow-trace-table .pagination-page-btn')]
  const page2 = btns.find((b) => b.textContent.trim() === '2')
  if (page2) page2.click()
})
await page.waitForTimeout(1500)
const page2 = await page.evaluate(() => {
  const table = document.querySelector('.top-slow-trace-table')
  const active = table?.querySelector('.pagination-page-btn.active')?.textContent.trim()
  const firstTrace = table?.querySelector('.aggregate-fixed-left > .aggregate-body-row .trace-id-text')?.textContent.trim()
  return { active, firstTrace }
})
console.log('PAGE2:', JSON.stringify(page2))
// 切到异常Trace列表 tab 验证 pod 标签
await page.evaluate(() => {
  const btns = [...document.querySelectorAll('.aggregate-tab-item')]
  const target = btns.find((b) => b.textContent.trim() === '异常Trace列表')
  if (target) target.click()
})
await page.waitForTimeout(4000)
const abnormal = await page.evaluate(() => {
  const chips = [...document.querySelectorAll('.abnormal-trace-frame:not(.fault-trace-list) .role-chip')]
  return {
    chipCount: chips.length,
    roles: [...new Set(chips.map((c) => c.className))].slice(0, 10),
    sample: chips.slice(0, 6).map((c) => ({ cls: c.className, txt: c.textContent.trim() })),
  }
})
console.log('ABNORMAL:', JSON.stringify(abnormal, null, 2))
console.log('LOGS:', JSON.stringify(logs, null, 2))
await page.screenshot({ path: 'pw_merged_top500.png', fullPage: false })
await browser.close()
