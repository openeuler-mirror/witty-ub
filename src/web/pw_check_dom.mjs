import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })
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
await page.waitForTimeout(12000)
// dump 所有 monitor-card 的标题和内部 table 状态
const cards = await page.evaluate(() => {
  return [...document.querySelectorAll('.monitor-card')].map((c) => ({
    cls: c.className,
    title: c.querySelector('.monitor-card-title')?.textContent?.trim().slice(0, 60) ?? '',
    hasTable: !!c.querySelector('table'),
    tableRows: c.querySelectorAll('table tbody tr').length,
    tableText: c.querySelector('table tbody')?.textContent?.trim().slice(0, 200) ?? '',
    tabText: [...c.querySelectorAll('.aggregate-tab-item')].map((b) => ({ t: b.textContent.trim(), a: b.className.includes('active') })),
  }))
})
console.log('CARDS:', JSON.stringify(cards, null, 2))
// 所有 table 元素
const tables = await page.evaluate(() => {
  return [...document.querySelectorAll('table')].map((t) => ({
    inHostSlot: !!t.closest('.host-slot'),
    header: [...t.querySelectorAll('thead th')].map((h) => h.textContent.trim()).slice(0, 10),
    rows: t.querySelectorAll('tbody tr').length,
    rowText: t.querySelector('tbody tr')?.textContent?.trim().slice(0, 150) ?? '',
  }))
})
console.log('TABLES:', JSON.stringify(tables, null, 2))
await browser.close()
