import { onBeforeUnmount, onMounted, watch } from 'vue'
import type { LogKnowledge } from '../types'
import { useAssets, type AppView } from './useAssets'

// 顶层导航与 URL hash 的双向同步：
// - 程序内导航（view/selectedAsset 变化）→ 写 hash（浏览器后退可回到上一页面）
// - 浏览器后退/前进、手改 URL → 解析 hash 恢复 view 与资产上下文
// hash 形态：#/assets（列表）| #/assets/{kbId}（资产工作区）| #/knowledge
const VIEW_SEGMENTS: AppView[] = ['assets', 'home', 'knowledge']

const hashOf = (view: AppView, assetId: string | null): string => {
  if (view === 'home') return assetId ? `#/assets/${assetId}` : '#/assets'
  if (view === 'assets') return '#/assets'
  return `#/${view}`
}

export function useNavigation() {
  const assets = useAssets()
  const { view, selectedAsset, enterAsset, assets: assetList, loadAssets } = assets

  let applyingHash = false

  const applyHash = async (raw: string) => {
    // 恢复期间抑制 watch 回写：enterAsset 分两步赋值（selectedAsset → view），
    // 同步 watch 在两步之间会算出中间态 hash（#/assets）并改写 URL，
    // 直达 #/assets/{kbId} 或浏览器前进会被弹回列表。恢复流程以 URL 为准，不回写。
    applyingHash = true
    try {
      const segment = raw.replace(/^#\/?/, '')
      const [head, kbId] = segment.split('/')
      const target = VIEW_SEGMENTS.find((item) => item === head)
      if (!target) {
        view.value = 'assets'
        window.location.hash = '#/assets'
        return
      }
      // #/assets/{kbId} 的工作区视图由 enterAsset 落位；已选中同一资产时直接恢复，避免留在列表页
      view.value = head === 'assets' && kbId ? 'home' : target
      if (head === 'assets' && kbId && selectedAsset.value?.id !== kbId) {
        // 从 URL 恢复资产上下文：列表里找，找不到再拉详情（期间面包屑短暂空白可接受）
        const known =
          assetList.value.find((asset) => asset.id === kbId) ??
          ({ id: kbId, name: '', description: '' } as LogKnowledge)
        await enterAsset(known)
      }
    } finally {
      applyingHash = false
    }
  }

  const onHashChange = (event: HashChangeEvent) => {
    if (applyingHash) {
      applyingHash = false
      return
    }
    const oldUrl = new URL(event.oldURL)
    const newUrl = new URL(event.newURL)
    if (oldUrl.hash === newUrl.hash) return
    void applyHash(newUrl.hash)
  }

  watch(
    [view, selectedAsset],
    ([nextView, asset]) => {
      // hash 恢复流程中以 URL 为准，不回写（避免中间态覆盖目标 hash）
      if (applyingHash) return
      const target = hashOf(nextView, asset?.id ?? null)
      if (window.location.hash === target) return
      applyingHash = true
      window.location.hash = target
    },
    { flush: 'sync' },
  )

  onMounted(async () => {
    window.addEventListener('hashchange', onHashChange)
    // 资产列表先加载，hash 恢复时能优先命中已知资产
    await loadAssets()
    if (window.location.hash && window.location.hash !== '#/') {
      await applyHash(window.location.hash)
    } else {
      window.location.hash = hashOf(view.value, selectedAsset.value?.id ?? null)
    }
  })

  onBeforeUnmount(() => {
    window.removeEventListener('hashchange', onHashChange)
  })
}
