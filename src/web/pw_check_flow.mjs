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
    logs.push(`[resp ${r.status()}] len=${t.length}`)
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
await page.waitForTimeout(12000)
// 检查总览 flow 渲染状态
const overview = await page.evaluate(() => {
  const containers = [...document.querySelectorAll('.echarts-flow-chart')]
  return {
    containerCount: containers.length,
    containers: containers.map((c) => {
      const style = getComputedStyle(c)
      return {
        class: c.className,
        width: c.clientWidth,
        height: c.clientHeight,
        display: style.display,
        visibility: style.visibility,
        canvasCount: c.querySelectorAll('canvas').length,
        text: c.innerText.slice(0, 100),
      }
    }),
  }
})
console.log('OVERVIEW:', JSON.stringify(overview, null, 2))
// 查找并点击 GET/SET 标签
const tabInfo = await page.evaluate(() => {
  const tabs = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && ['GET', 'SET'].includes(e.textContent.trim()))
  return tabs.map((t) => ({ text: t.textContent.trim(), tag: t.tagName }))
})
console.log('TABS:', JSON.stringify(tabInfo))
await page.waitForTimeout(3000)
const overview2 = await page.evaluate(() => ({
  containerCount: document.querySelectorAll('.echarts-flow-chart').length,
  containers: [...document.querySelectorAll('.echarts-flow-chart')].map((c) => ({
    class: c.className,
    width: c.clientWidth,
    height: c.clientHeight,
    canvasCount: c.querySelectorAll('canvas').length,
  })),
}))
console.log('OVERVIEW2:', JSON.stringify(overview2, null, 2))
// 检查 canvas 是否真的画了内容（非空白像素统计）
const canvasPixels = await page.evaluate(() => {
  const results = [...document.querySelectorAll('.echarts-flow-chart canvas')].map((c) => {
    const ctx = c.getContext('2d')
    const data = ctx.getImageData(0, 0, c.width, c.height).data
    let nonEmpty = 0
    for (let i = 0; i < data.length; i += 4) {
      if (data[i] !== 0 || data[i + 1] !== 0 || data[i + 2] !== 0 || data[i + 3] !== 0) nonEmpty++
    }
    return { w: c.width, h: c.height, total: c.width * c.height, nonEmpty }
  })
  return results
})
console.log('CANVAS_PIXELS:', JSON.stringify(canvasPixels, null, 2))
// 截图总览 flow 区域
const flowSection = await page.evaluate(() => {
  const h = [...document.querySelectorAll('*')].find((e) => e.children.length === 0 && e.textContent.trim().startsWith('角色交互时延流'))
  return h?.closest('section')?.getBoundingClientRect() ?? null
})
if (flowSection) {
  await page.screenshot({ path: 'pw_flow_overview.png', clip: flowSection, fullPage: false })
}
// 打开异常Trace列表并点击第一行
await page.evaluate(() => {
  const els = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === '异常Trace列表')
  const target = els[0]
  if (target) (target.closest('button, [role="button"], .tab, li') || target).click()
})
await page.waitForTimeout(3000)
const traceClicked = await page.evaluate(() => {
  const rows = [...document.querySelectorAll('tr')]
  const clickable = rows.find((r) => r.textContent.match(/[0-9a-f]{8}-[0-9a-f]{4}/))
  if (clickable) {
    clickable.click()
    return true
  }
  return false
})
console.log('traceClicked:', traceClicked)
await page.waitForTimeout(8000)
const modalInfo = await page.evaluate(() => {
  const containers = [...document.querySelectorAll('.trace-flow-chart')]
  return {
    traceFlowCanvasCount: containers.map((c) => c.querySelectorAll('canvas').length),
    traceFlowContainerCount: containers.length,
    hasModal: !!document.querySelector('.trace-modal-content, .drawer'),
  }
})
console.log('MODAL:', JSON.stringify(modalInfo))
await page.screenshot({ path: 'pw_flow_full.png', fullPage: false })
console.log('LOGS:', JSON.stringify(logs, null, 2))
await browser.close()
