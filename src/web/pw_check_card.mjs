import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })
page.on('console', (m) => console.log('[console]', m.type(), m.text()))
page.on('pageerror', (e) => console.log('[pageerror]', e.message))
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(3000)
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
await page.waitForTimeout(12000)
// 滚动到 flow 区域并截图
const rect = await page.evaluate(() => {
  const h = [...document.querySelectorAll('*')].find((e) => e.children.length === 0 && e.textContent.trim().includes('角色交互时延流'))
  const card = h?.closest('.flow-summary-card') ?? h?.closest('.monitor-card')
  if (!card) return null
  const r = card.getBoundingClientRect()
  return { x: r.x, y: r.y, width: r.width, height: r.height }
})
console.log('FLOW_RECT:', JSON.stringify(rect))
if (rect) {
  await page.screenshot({ path: 'pw_flow_card.png', clip: rect, fullPage: false })
}
// 检查该卡片内实际文本
const cardText = await page.evaluate(() => {
  const h = [...document.querySelectorAll('*')].find((e) => e.children.length === 0 && e.textContent.trim().includes('角色交互时延流'))
  const card = h?.closest('.flow-summary-card') ?? h?.closest('.monitor-card')
  return card?.innerText.slice(0, 600) ?? 'NO CARD'
})
console.log('CARD_TEXT:', JSON.stringify(cardText))
// canvas 像素检查
const pixels = await page.evaluate(() => {
  return [...document.querySelectorAll('.flow-summary-card .echarts-flow-chart canvas')].map((c) => {
    const ctx = c.getContext('2d')
    const d = ctx.getImageData(0, 0, c.width, c.height).data
    let nonEmpty = 0
    for (let i = 0; i < d.length; i += 4) {
      if (d[i] !== 0 || d[i + 1] !== 0 || d[i + 2] !== 0 || d[i + 3] !== 0) nonEmpty++
    }
    return { nonEmpty, total: c.width * c.height, ratio: (nonEmpty / (c.width * c.height)).toFixed(4) }
  })
})
console.log('PIXELS:', JSON.stringify(pixels))
await browser.close()
