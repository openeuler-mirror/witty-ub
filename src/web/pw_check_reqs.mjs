import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })
const reqs = []
page.on('request', (r) => {
  const u = r.url()
  if (u.includes('/log_parse_result') || u.includes('/list_flow_summary') || u.includes('/abnormal') || u.includes('aggregated')) {
    let body = ''
    try {
      body = r.postData()?.slice(0, 300) ?? ''
    } catch {}
    reqs.push(`[REQ] ${r.method()} ${u.replace('http://localhost:5173', '')} ${body}`)
  }
})
page.on('response', async (r) => {
  const u = r.url()
  if (u.includes('/log_parse_result') || u.includes('/list_flow_summary') || u.includes('/abnormal') || u.includes('aggregated')) {
    const t = await r.text().catch(() => '')
    reqs.push(`[RESP ${r.status()}] ${u.replace('http://localhost:5173', '')} len=${t.length} ${t.slice(0, 150)}`)
  }
})
page.on('console', (m) => reqs.push(`[console ${m.type()}] ${m.text().slice(0, 200)}`))
page.on('pageerror', (e) => reqs.push(`[pageerror] ${e.message}`))
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
const tabs = await page.evaluate(() => [...document.querySelectorAll('.aggregate-tab-item')].map((b) => ({ t: b.textContent.trim(), active: b.className.includes('active') })))
console.log('TABS:', JSON.stringify(tabs))
// 点击异常Trace列表 tab
await page.evaluate(() => {
  const btns = [...document.querySelectorAll('.aggregate-tab-item')]
  const target = btns.find((b) => b.textContent.trim() === '异常Trace列表')
  if (target) target.click()
})
await page.waitForTimeout(5000)
const bodyState = await page.evaluate(() => ({
  traceSectionText: document.querySelector('.monitor-card.host-slot')?.innerText.slice(0, 500) ?? '',
  abnormalEmpty: document.body.innerText.includes('暂无符合条件的请求'),
  hasTraceTable: !!document.querySelector('.monitor-card.host-slot table'),
}))
console.log('BODY_STATE:', JSON.stringify(bodyState, null, 2))
console.log('REQS:', JSON.stringify(reqs, null, 2))
await browser.close()
