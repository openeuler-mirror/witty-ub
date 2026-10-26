import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })
page.on('pageerror', (e) => console.log('[pageerror]', e.message))
page.on('console', (m) => { if (m.type() === 'error') console.log('[console error]', m.text()) })
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(3000)
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === '333')
  const target = els.find((e) => e.closest('button, [role="button"], a')) || els[0]
  ;(target.closest('button, [role="button"], a') || target).click()
})
await page.waitForTimeout(5000)
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim().includes('时延故障监控'))
  const target = els[0]
  if (target) (target.closest('button, a, li, [role="button"]') || target).click()
})
await page.waitForTimeout(15000)
// 精确分析总览两个 canvas 的颜色像素
const analysis = await page.evaluate(() => {
  const canvases = [...document.querySelectorAll('.flow-summary-card .echarts-flow-chart canvas')]
  return canvases.map((c, i) => {
    const ctx = c.getContext('2d')
    const d = ctx.getImageData(0, 0, c.width, c.height).data
    const colors = new Set()
    let nonEmpty = 0
    for (let p = 0; p < d.length; p += 4) {
      const r = d[p], g = d[p + 1], b = d[p + 2], a = d[p + 3]
      if (a > 0) {
        nonEmpty++
        colors.add(`${r >> 4},${g >> 4},${b >> 4}`)
      }
    }
    return { idx: i, nonEmpty, total: c.width * c.height, distinctColorBuckets: colors.size }
  })
})
console.log('CANVAS_ANALYSIS:', JSON.stringify(analysis, null, 2))
// 检查标题和阈值文本
const cardText = await page.evaluate(() => document.querySelector('.flow-summary-card')?.innerText.slice(0, 300) ?? '')
console.log('CARD_TEXT:', JSON.stringify(cardText))
await page.screenshot({ path: 'pw_final_333.png', fullPage: false })
await browser.close()
