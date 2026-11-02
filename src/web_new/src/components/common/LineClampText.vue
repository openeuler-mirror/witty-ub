<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

// 多行文本精确截断：高度/行号由外部样式控制（固定 height + overflow hidden），
// 溢出时二分削减字符拼上"…"，观感与原生 ellipsis 一致。
// 不用 display:-webkit-box + line-clamp：HeadlessChrome 149+ 会把该组合
// 规范化为 flow-root 导致截断失效。
const props = defineProps<{ text: string }>()

const el = ref<HTMLElement | null>(null)
let observer: ResizeObserver | null = null

const check = () => {
  const node = el.value
  if (!node) return
  const full = props.text ?? ''
  node.textContent = full
  if (node.scrollHeight <= node.clientHeight + 1) return

  let low = 0
  let high = full.length - 1
  let fit = 0
  while (low <= high) {
    const mid = (low + high) >> 1
    node.textContent = `${full.slice(0, mid)}…`
    if (node.scrollHeight <= node.clientHeight + 1) {
      fit = mid
      low = mid + 1
    } else {
      high = mid - 1
    }
  }
  node.textContent = `${full.slice(0, fit)}…`
}

watch(
  () => props.text,
  () => requestAnimationFrame(check),
)

onMounted(() => {
  check()
  observer = new ResizeObserver(check)
  if (el.value) observer.observe(el.value)
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div ref="el" class="line-clamp-text">{{ text }}</div>
</template>

<style scoped>
.line-clamp-text {
  overflow: hidden;
}
</style>
