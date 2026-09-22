<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'
import { useModalLayer } from '../../composables/useModalLayer'

/**
 * 统一弹窗容器：滚动隔离、Esc/遮罩层级、焦点进出、dialog 语义都在这里收口。
 * 自定义标题栏用 #header 插槽（另用 label 提供无障碍名称）；不要再手写 .modal-overlay。
 */
const props = withDefaults(
  defineProps<{
    open: boolean
    /** 标题栏文案，同时作为弹窗的无障碍名称 */
    title?: string
    /** 使用 #header 插槽时的无障碍名称 */
    label?: string
    /** sm=480 md=520 lg=580 xl=详情大弹窗 drawer=右侧抽屉 */
    size?: 'sm' | 'md' | 'lg' | 'xl' | 'drawer'
    closeOnEsc?: boolean
    closeOnOverlay?: boolean
  }>(),
  { size: 'md', closeOnEsc: true, closeOnOverlay: true },
)

const emit = defineEmits<{ close: [] }>()

const { isTopLayer } = useModalLayer(() => props.open)
const headingId = useId()
const panel = ref<HTMLElement | null>(null)
let focusBeforeOpen: HTMLElement | null = null

const close = () => emit('close')

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

const focusableItems = () =>
  panel.value
    ? Array.from(panel.value.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
        (item) => item.offsetParent !== null || item === document.activeElement,
      )
    : []

const onKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    if (props.closeOnEsc && isTopLayer()) close()
    return
  }
  if (event.key !== 'Tab') return
  const items = focusableItems()
  const active = document.activeElement as HTMLElement | null
  if (items.length === 0) {
    event.preventDefault()
    panel.value?.focus({ preventScroll: true })
    return
  }
  const first = items[0]
  const last = items[items.length - 1]
  if (!first || !last) return
  if (!active || active === panel.value || !panel.value?.contains(active)) {
    event.preventDefault()
    ;(event.shiftKey ? last : first).focus()
  } else if (event.shiftKey && active === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && active === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      focusBeforeOpen =
        document.activeElement instanceof HTMLElement ? document.activeElement : null
      window.addEventListener('keydown', onKeydown)
      await nextTick()
      panel.value?.focus({ preventScroll: true })
    } else {
      window.removeEventListener('keydown', onKeydown)
      if (focusBeforeOpen?.isConnected) focusBeforeOpen.focus({ preventScroll: true })
      focusBeforeOpen = null
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="modal-overlay"
      :class="{ 'modal-overlay--drawer': size === 'drawer' }"
      @click.self="closeOnOverlay && close()"
    >
      <div
        ref="panel"
        class="modal"
        :class="`modal--${size}`"
        role="dialog"
        aria-modal="true"
        :aria-label="title ? undefined : label"
        :aria-labelledby="title ? headingId : undefined"
        tabindex="-1"
      >
        <slot name="header" :close="close">
          <div class="modal-header">
            <span :id="headingId">{{ title }}</span>
            <button class="modal-close" type="button" aria-label="关闭" @click="close">✕</button>
          </div>
        </slot>
        <div class="modal-body modal-scroll">
          <slot />
        </div>
        <div v-if="$slots.footer" class="modal-footer">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
