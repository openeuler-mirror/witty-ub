import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })
const reqs = []
page.on('request', (r) => {
  if (r.url().includes('list_flow_summary')) {
    let body = ''
    try { body = r.postData()?.slice(0, 200) ?? '' } catch {}
    reqs.push(`[REQ] ${body}`)
  }
})
page.on('response', async (r) => {
  if (r.url().includes('list_flow_summary')) {
    const t = await r.text().catch(() => '')
    reqs.push(`[RESP ${r.status()}] len=${t.length}`)
  }
})
page.on('pageerror', (e) => reqs.push(`[pageerror] ${e.message}`))
page.on('console', (m) => {
  if (m.type() === 'error' || m.type() === 'warning') reqs.push(`[console ${m.type()}] ${m.text().slice(0, 300)}`)
})
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(2000)
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === '333')
  const target = els.find((e) => e.closest('button, [role="button"], a')) || els[0]
  ;(target.closest('button, [role="button"], a') || target).click()
})
await page.waitForTimeout(5000)
// 点击"通断故障监控"
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim().includes('通断故障监控'))
  const target = els[0]
  if (target) (target.closest('button, a, li, [role="button"]') || target).click()
})
await page.waitForTimeout(15000)
// 点击通断页的"异常Trace列表" tab
await page.evaluate(() => {
  const slots = [...document.querySelectorAll('.monitor-card.host-slot')]
  const btns = slots.flatMap((h) => [...h.querySelectorAll('.aggregate-tab-item')])
  const target = btns.find((b) => b.textContent.trim() === '异常Trace列表')
  if (target) target.click()
})
await page.waitForTimeout(5000)
// 点击第一个"查看链路"按钮（通断页）
const clicked = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('button.metric-action-btn.detail-action-btn, button[class*="detail"]')]
  if (btns.length === 0) return 'NO BTN'
  btns[0].click()
  return 'clicked'
})
console.log('CLICKED:', clicked)
await page.waitForTimeout(10000)
const modal = await page.evaluate(() => {
  const modalEl = document.querySelector('.trace-modal-content')
  const chartContainers = [...document.querySelectorAll('.trace-flow-chart')]
  return {
    modalOpen: !!modalEl,
    flowSectionCount: document.querySelectorAll('.trace-flow-section').length,
    modalTitle: modalEl?.querySelector('h2')?.textContent ?? '',
    chartContainers: chartContainers.map((c) => ({ w: c.clientWidth, h: c.clientHeight, canvas: c.querySelectorAll('canvas').length })),
  }
})
console.log('MODAL:', JSON.stringify(modal, null, 2))
if (modal.modalOpen) {
  const px = await page.evaluate(() => {
    return [...document.querySelectorAll('.trace-flow-chart canvas')].map((c) => {
      const ctx = c.getContext('2d')
      const d = ctx.getImageData(0, 0, c.width, c.height).data
      let n = 0
      for (let i = 0; i < d.length; i += 4) if (d[i] !== 0 || d[i + 1] !== 0 || d[i + 2] !== 0 || d[i + 3] !== 0) n++
      return { nonEmpty: n, total: c.width * c.height }
    })
  })
  console.log('MODAL_PIXELS:', JSON.stringify(px))
}
console.log('REQS:', JSON.stringify(reqs, null, 2))
await browser.close()
