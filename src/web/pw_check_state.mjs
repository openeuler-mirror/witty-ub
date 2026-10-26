import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })
page.on('console', (m) => console.log('[console]', m.type(), m.text()))
page.on('pageerror', (e) => console.log('[pageerror]', e.message))
await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForTimeout(3000)
// 打印所有资产库按钮文本
const assets = await page.evaluate(() => {
  return [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && ['111', '222', '333', '444'].includes(e.textContent.trim())).map((e) => ({ text: e.textContent.trim(), tag: e.tagName }))
})
console.log('ASSETS:', JSON.stringify(assets))
// 点击333
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === '333')
  const target = els.find((e) => e.closest('button, [role="button"], a')) || els[0]
  ;(target.closest('button, [role="button"], a') || target).click()
})
await page.waitForTimeout(6000)
// 点击"时延故障监控"（列出所有匹配元素）
const navMatches = await page.evaluate(() => {
  return [...document.querySelectorAll('*')].filter((e) => e.textContent.trim().includes('时延故障监控')).slice(0, 10).map((e) => ({
    tag: e.tagName,
    cls: e.className,
    text: e.textContent.trim().slice(0, 40),
    children: e.children.length,
  }))
})
console.log('NAV_MATCHES:', JSON.stringify(navMatches, null, 2))
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim().includes('时延故障监控'))
  const target = els[0]
  if (target) (target.closest('button, a, li, [role="button"]') || target).click()
})
await page.waitForTimeout(15000)
// dump 页面中所有包含"角色交互"或"Flow"的元素
const flowEls = await page.evaluate(() => {
  const out = []
  const all = [...document.querySelectorAll('*')]
  for (const e of all) {
    const t = e.textContent?.trim() ?? ''
    if (t.includes('角色交互') || t.includes('Read Flow') || t.includes('Write Flow')) {
      out.push({ tag: e.tagName, cls: String(e.className).slice(0, 60), text: t.slice(0, 80), children: e.children.length })
    }
  }
  return out.slice(0, 20)
})
console.log('FLOW_ELS:', JSON.stringify(flowEls, null, 2))
// 检查 body 里是否有"暂无角色交互时延数据"
const states = await page.evaluate(() => ({
  noFlowData: document.body.innerText.includes('暂无角色交互时延数据'),
  loadingFlow: document.body.innerText.includes('正在加载角色交互时延流'),
  flowError: document.body.innerText.includes('加载角色交互时延流失败'),
}))
console.log('STATES:', JSON.stringify(states))
// 检查 tab 区域
const tabs = await page.evaluate(() => [...document.querySelectorAll('.aggregate-tab-item')].map((b) => b.textContent.trim()))
console.log('TABS:', JSON.stringify(tabs))
await page.screenshot({ path: 'pw_state.png', fullPage: true })
await browser.close()
