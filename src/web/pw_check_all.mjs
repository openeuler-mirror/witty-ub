import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })
async function goAsset(name) {
  await page.evaluate((n) => {
    const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === n)
    const target = els.find((e) => e.closest('button, [role="button"], a')) || els[0]
    if (target) (target.closest('button, [role="button"], a') || target).click()
  }, name)
  await page.waitForTimeout(5000)
  await page.evaluate(() => {
    const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim().includes('时延故障监控'))
    const target = els[0]
    if (target) (target.closest('button, a, li, [role="button"]') || target).click()
  })
  await page.waitForTimeout(12000)
}
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(3000)
for (const name of ['111', '222', '444']) {
  await goAsset(name)
  const state = await page.evaluate(() => {
    const card = document.querySelector('.flow-summary-card')
    const canvases = [...document.querySelectorAll('.flow-summary-card .echarts-flow-chart canvas')]
    const px = canvases.map((c) => {
      const ctx = c.getContext('2d')
      const d = ctx.getImageData(0, 0, c.width, c.height).data
      let n = 0
      let colored = 0
      for (let i = 0; i < d.length; i += 4) {
        if (d[i] !== 0 || d[i + 1] !== 0 || d[i + 2] !== 0 || d[i + 3] !== 0) {
          n++
          if (d[i] !== d[i + 1] || d[i + 1] !== d[i + 2]) colored++
        }
      }
      return { nonEmpty: n, colored, total: c.width * c.height }
    })
    return {
      assetName: document.querySelector('.asset-detail-title, .current-asset')?.textContent?.trim() || '',
      hasCard: !!card,
      text: card?.innerText.slice(0, 200) ?? '',
      canvases,
    }
  })
  console.log(`=== ${name} ===`, JSON.stringify(state))
}
await browser.close()
