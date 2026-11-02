import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage()
const logs = []
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`))
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`))
page.on('request', (r) => {
  if (r.url().includes('list_flow_summary')) logs.push(`[req] ${r.url()}`)
})
page.on('response', async (r) => {
  if (r.url().includes('list_flow_summary')) {
    const t = await r.text().catch(() => '')
    logs.push(`[resp ${r.status()}] ${t.slice(0, 300)}`)
  }
})
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(4000)
// 点击资产库 "333"
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === '333')
  const target = els.find((e) => e.closest('button, [role="button"], a')) || els[0]
  ;(target.closest('button, [role="button"], a') || target).click()
})
await page.waitForTimeout(5000)
// 点击 "时延故障监控" 导航
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim().includes('时延故障监控'))
  const target = els[0]
  if (target) (target.closest('button, a, li, [role="button"]') || target).click()
})
await page.waitForTimeout(12000)
// 打开异常 trace 列表 tab
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === '异常Trace列表')
  const target = els[0]
  if (target) (target.closest('button, [role="button"], .tab, li') || target).click()
})
await page.waitForTimeout(3000)
// 点击第一行 trace 打开详情弹窗
const clickedTrace = await page.evaluate(() => {
  const rows = [...document.querySelectorAll('tr')]
  const clickable = rows.find((r) => r.textContent.includes('trace') || r.textContent.match(/[0-9a-f]{8}-[0-9a-f]{4}/))
  if (clickable) {
    clickable.click()
    return clickable.textContent.slice(0, 200)
  }
  return ''
})
console.log('clicked trace row:', clickedTrace)
await page.waitForTimeout(10000)
const info = await page.evaluate(() => ({
  modalOpen: !!document.querySelector('.trace-modal-content'),
  hasTraceFlowSection: !!document.querySelector('.trace-flow-section'),
  traceFlowText: document.querySelector('.trace-flow-section')?.innerText.slice(0, 400) ?? '',
  traceFlowCanvas: document.querySelectorAll('.trace-flow-chart canvas').length,
  bodySnippet: document.body.innerText.slice(-1200),
}))
console.log(JSON.stringify({ logs: logs.slice(0, 40), info }, null, 2))
await browser.close()
