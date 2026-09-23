import { onBeforeUnmount, watch } from 'vue'

/**
 * 文档滚动锁 + 弹窗层级栈（BaseModal 内部使用）。
 * 弹窗打开期间冻结文档滚动并按引用计数释放；只有最上层弹窗响应 Esc。
 */
const SCROLL_LOCK_CLASS = 'is-modal-open'

const openLayers: symbol[] = []
let savedBodyPaddingRight = ''

const lockDocumentScroll = () => {
  const root = document.documentElement
  if (root.classList.contains(SCROLL_LOCK_CLASS)) return
  // 锁滚动会隐藏滚动条，先量出滚动条宽度补齐内边距，避免背景页面横向跳动
  const scrollbarWidth = window.innerWidth - root.clientWidth
  savedBodyPaddingRight = document.body.style.paddingRight
  if (scrollbarWidth > 0) document.body.style.paddingRight = `${scrollbarWidth}px`
  root.classList.add(SCROLL_LOCK_CLASS)
}

const unlockDocumentScroll = () => {
  const root = document.documentElement
  if (!root.classList.contains(SCROLL_LOCK_CLASS)) return
  root.classList.remove(SCROLL_LOCK_CLASS)
  document.body.style.paddingRight = savedBodyPaddingRight
}

export const useModalLayer = (isOpen: () => boolean) => {
  const layer = Symbol('modal-layer')
  const layerIndex = () => openLayers.indexOf(layer)

  const isTopLayer = () => openLayers.at(-1) === layer

  const register = () => {
    if (layerIndex() !== -1) return
    openLayers.push(layer)
    lockDocumentScroll()
  }

  const unregister = () => {
    const index = layerIndex()
    if (index === -1) return
    openLayers.splice(index, 1)
    if (openLayers.length === 0) unlockDocumentScroll()
  }

  watch(isOpen, (open) => (open ? register() : unregister()), { immediate: true })
  onBeforeUnmount(unregister)

  return { isTopLayer }
}
