import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } })
const logs = []
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`))
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`))
page.on('request', (r) => {
  if (r.url().includes('list_flow_summary')) logs.push(`[req] ${r.url()}`)
})
page.on('response', async (r) => {
  if (r.url().includes('list_flow_summary')) {
    const t = await r.text().catch(() => '')
    logs.push(`[resp ${r.status()}] len=${t.length} body=${t.slice(0, 200)}`)
  }
})
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(3000)
// 点击资产库 "333"
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === '333')
  const target = els.find((e) => e.closest('button, [role="button"], a')) || els[0]
  ;(target.closest('button, [role="button"], a') || target).click()
})
await page.waitForTimeout(4000)
// 点击 "时延故障监控"
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim().includes('时延故障监控'))
  const target = els[0]
  if (target) (target.closest('button, a, li, [role="button"]') || target).click()
})
await page.waitForTimeout(10000)
// 打印页面上出现的 tab/标题
const pageText = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('button')].map((b) => b.textContent.trim()).filter((t) => t && t.length < 30)
  return btns.slice(0, 60)
})
console.log('BUTTONS:', JSON.stringify(pageText, null, 2))
// 点击时延页的"异常Trace列表" tab（用 aggregate-tab-item class 定位）
await page.evaluate(() => {
  const btns = [...document.querySelectorAll('.aggregate-tab-item')]
  const target = btns.find((b) => b.textContent.trim() === '异常Trace列表')
  if (target) target.click()
})
await page.waitForTimeout(3000)
// 打印表格行内容
const rows = await page.evaluate(() => {
  const all = [...document.querySelectorAll('tr')].map((r) => r.textContent.trim().slice(0, 120)).filter(Boolean)
  return all.slice(0, 15)
})
console.log('ROWS:', JSON.stringify(rows, null, 2))
// 点击包含 trace id 的行
const clicked = await page.evaluate(() => {
  const rows = [...document.querySelectorAll('tr')]
  const clickable = rows.find((r) => r.textContent.match(/[0-9a-f]{8}-[0-9a-f]{4}/) && !r.querySelector('th'))
  if (clickable) {
    clickable.click()
    return clickable.textContent.trim().slice(0, 150)
  }
  return ''
})
console.log('CLICKED:', clicked)
await page.waitForTimeout(10000)
const modal = await page.evaluate(() => {
  const containers = [...document.querySelectorAll('.trace-flow-chart')]
  return {
    modalOpen: !!document.querySelector('.trace-modal-content'),
    traceFlowContainers: containers.length,
    canvases: containers.map((c) => ({
      w: c.clientWidth,
      h: c.clientHeight,
      canvasCount: c.querySelectorAll('canvas').length,
    })),
    traceFlowSection: document.querySelector('.trace-flow-section')?.innerText.slice(0, 300) ?? '',
  }
})
console.log('MODAL:', JSON.stringify(modal, null, 2))
// 检查弹窗 canvas 像素
const pixels = await page.evaluate(() => {
  return [...document.querySelectorAll('.trace-flow-chart canvas')].map((c) => {
    const ctx = c.getContext('2d')
    const d = ctx.getImageData(0, 0, c.width, c.height).data
    let nonEmpty = 0
    for (let i = 0; i < d.length; i += 4) {
      if (d[i] !== 0 || d[i + 1] !== 0 || d[i + 2] !== 0 || d[i + 3] !== 0) nonEmpty++
    }
    return { nonEmpty, total: c.width * c.height }
  })
})
console.log('MODAL_PIXELS:', JSON.stringify(pixels))
console.log('LOGS:', JSON.stringify(logs, null, 2))
await browser.close()
