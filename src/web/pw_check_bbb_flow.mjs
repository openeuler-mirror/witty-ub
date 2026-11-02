import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } })
const logs = []
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`))
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`))
page.on('request', (r) => {
  if (r.url().includes('list_flow_summary')) logs.push(`[req] ${r.url()} body=${r.postData()}`)
})
page.on('response', async (r) => {
  if (r.url().includes('list_flow_summary')) {
    const t = await r.text().catch(() => '')
    logs.push(`[resp ${r.status()}] len=${t.length} head=${t.slice(0, 200)}`)
  }
})
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(2500)
// 点击资产库 "bbb"
const clicked = await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === 'bbb')
  const target = els.find((e) => e.closest('button, [role="button"], a')) || els[0]
  if (!target) return false
  ;(target.closest('button, [role="button"], a') || target).click()
  return true
})
console.log('CLICKED_ASSET:', clicked)
await page.waitForTimeout(4000)
// 点击 "时延故障监控"
const clicked2 = await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim().includes('时延故障监控'))
  const target = els[0]
  if (!target) return false
  ;(target.closest('button, a, li, [role="button"]') || target).click()
  return true
})
console.log('CLICKED_MONITOR:', clicked2)
await page.waitForTimeout(12000)
// 检查 flow 卡片状态
const flowState = await page.evaluate(() => {
  const card = [...document.querySelectorAll('.flow-summary-card')][0]
  if (!card) return { found: false }
  return {
    found: true,
    stateText: card.querySelector('.chart-state')?.textContent ?? null,
    graphCount: card.querySelectorAll('.echarts-flow-chart').length,
    decompText: card.querySelector('.flow-decomp-metrics')?.textContent ?? null,
    canvasCount: card.querySelectorAll('canvas').length,
  }
})
console.log('FLOW_STATE:', JSON.stringify(flowState))
const thresholdText = await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.includes('当前阈值'))
  return els.map((e) => e.textContent).slice(0, 2)
})
console.log('THRESHOLD_TEXT:', JSON.stringify(thresholdText))
await page.screenshot({ path: '/tmp/bbb_flow_page.png', fullPage: false })
console.log('LOGS:')
for (const l of logs) console.log(l.slice(0, 400))
await browser.close()
