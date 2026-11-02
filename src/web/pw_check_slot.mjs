import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })
page.on('console', (m) => console.log('[console]', m.type(), m.text().slice(0, 200)))
page.on('pageerror', (e) => console.log('[pageerror]', e.message))
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(2000)
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
// 点击全局第一个"异常Trace列表" tab
await page.evaluate(() => {
  const btns = [...document.querySelectorAll('.aggregate-tab-item')]
  const target = btns.find((b) => b.textContent.trim() === '异常Trace列表')
  if (target) target.click()
})
await page.waitForTimeout(5000)
// dump host-slot 卡片内 tab 激活状态与表格 HTML 摘要
const state = await page.evaluate(() => {
  const slots = [...document.querySelectorAll('.monitor-card.host-slot')]
  return slots.map((s, i) => {
    const activeTab = s.querySelector('.aggregate-tab-item.active')?.textContent?.trim() ?? ''
    const table = s.querySelector('table')
    const rows = table ? [...table.querySelectorAll('tbody tr')] : []
    return {
      idx: i,
      activeTab,
      hasTable: !!table,
      rowCount: rows.length,
      firstRow: rows[0]?.textContent?.trim().slice(0, 120) ?? '',
    }
  })
})
console.log('SLOTS:', JSON.stringify(state, null, 2))
// 检查 trace 列表表格是否在第一个 slot
const firstSlot = await page.evaluate(() => {
  const s = document.querySelectorAll('.monitor-card.host-slot')[0]
  return s?.innerHTML.slice(0, 800) ?? ''
})
console.log('FIRST_SLOT_HTML:', JSON.stringify(firstSlot.slice(0, 600)))
// 尝试点击第一个 slot 内的第一个可点击行
const clicked = await page.evaluate(() => {
  const s = document.querySelectorAll('.monitor-card.host-slot')[0]
  const row = s?.querySelector('tbody tr') ?? s?.querySelector('[class*="row"]')
  if (row) {
    row.click()
    return row.textContent.trim().slice(0, 100)
  }
  return ''
})
console.log('CLICKED:', clicked)
await page.waitForTimeout(8000)
const modal = await page.evaluate(() => ({
  modalOpen: !!document.querySelector('.trace-modal-content'),
  flowSection: !!document.querySelector('.trace-flow-section'),
  charts: [...document.querySelectorAll('.trace-flow-chart')].map((c) => ({ w: c.clientWidth, h: c.clientHeight, canvas: c.querySelectorAll('canvas').length })),
}))
console.log('MODAL:', JSON.stringify(modal))
await browser.close()
