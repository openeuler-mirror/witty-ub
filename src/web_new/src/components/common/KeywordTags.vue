<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

// 单行关键词标签：动态收缩可见数量，放不下的收进 +N，保证不出现切一半的 tag
const props = withDefaults(defineProps<{ keywords: string[]; max?: number }>(), { max: 5 })

const el = ref<HTMLElement | null>(null)
const visibleCount = ref(props.max)
let observer: ResizeObserver | null = null
let runId = 0

const adjust = () => {
  const id = ++runId
  visibleCount.value = Math.min(props.max, props.keywords.length)
  requestAnimationFrame(() => {
    const node = el.value
    if (!node || id !== runId) return
    const step = () => {
      if (id !== runId) return
      if (visibleCount.value > 0 && node.scrollWidth > node.clientWidth + 1) {
        visibleCount.value -= 1
        requestAnimationFrame(step)
      }
    }
    step()
  })
}

watch(() => [props.keywords, props.max], adjust)

onMounted(() => {
  adjust()
  observer = new ResizeObserver(adjust)
  if (el.value) observer.observe(el.value)
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div ref="el" class="keyword-tags">
    <span
      v-for="kw in keywords.slice(0, visibleCount)"
      :key="kw"
      class="keyword-tag"
      :title="kw"
      >{{ kw }}</span
    >
    <span v-if="keywords.length > visibleCount" class="keyword-tag-more"
      >+{{ keywords.length - visibleCount }}</span
    >
  </div>
</template>

<style scoped>
.keyword-tags {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  min-width: 0;
  overflow: hidden;
}

.keyword-tag {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--primary-bg);
  color: var(--primary);
  font-size: 11px;
  white-space: nowrap;
}

.keyword-tag-more {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--text3);
  white-space: nowrap;
}
</style>
