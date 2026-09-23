<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  page: number
  pages: number
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:page': [page: number]
}>()

const jumpInput = ref(String(props.page))

const pageWindow = computed(() => {
  const pageCount = Math.max(1, props.pages)
  const current = Math.min(Math.max(1, props.page), pageCount)
  const visible = new Set<number>([1, pageCount])
  const start = Math.max(1, current - 2)
  const end = Math.min(pageCount, current + 2)
  for (let page = start; page <= end; page += 1) visible.add(page)

  const pages = [...visible].sort((first, second) => first - second)
  const window: number[] = []
  pages.forEach((page, index) => {
    const previousPage = pages[index - 1]
    if (previousPage !== undefined && page - previousPage > 1) {
      window.push(previousPage === 1 ? -1 : -2)
    }
    window.push(page)
  })
  return window
})

watch(
  () => props.page,
  (page) => {
    jumpInput.value = String(page)
  },
)

const goPage = (page: number) => {
  const next = Math.min(Math.max(1, page), Math.max(1, props.pages))
  emit('update:page', next)
  jumpInput.value = String(next)
}

const jump = () => {
  const value = Number(jumpInput.value)
  goPage(Number.isFinite(value) ? Math.round(value) : 1)
}
</script>

<template>
  <div class="page-nav">
    <button
      class="pn-btn"
      type="button"
      :disabled="disabled || page <= 1"
      @click="goPage(page - 1)"
    >
      上一页
    </button>
    <span class="pn-pages" aria-label="页码">
      <button
        v-for="pageNum in pageWindow"
        :key="`page-${pageNum}`"
        class="pn-btn pn-page"
        :class="{ active: pageNum === page, ellipsis: pageNum < 0 }"
        type="button"
        :disabled="disabled || pageNum < 0 || pageNum === page"
        @click="pageNum > 0 && goPage(pageNum)"
      >
        {{ pageNum < 0 ? '…' : pageNum }}
      </button>
    </span>
    <button
      class="pn-btn"
      type="button"
      :disabled="disabled || page >= pages"
      @click="goPage(page + 1)"
    >
      下一页
    </button>
    <span class="pn-jump">
      <span class="pn-info">第 {{ page }} / {{ pages }} 页</span>
      <input
        v-model="jumpInput"
        class="pn-input"
        type="number"
        min="1"
        :max="pages"
        :disabled="disabled"
        aria-label="跳转页码"
        @keyup.enter="jump"
      />
      <button class="pn-btn pn-jump-btn" type="button" :disabled="disabled" @click="jump">
        跳转
      </button>
    </span>
  </div>
</template>

<style scoped>
.page-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.pn-pages {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.pn-btn {
  height: 26px;
  min-width: 26px;
  padding: 0 8px;
  font-size: 12px;
  line-height: 1;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.pn-btn:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.pn-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pn-page.active {
  color: #fff;
  background: var(--primary);
  border-color: var(--primary);
}

.pn-page.ellipsis {
  border-color: transparent;
  background: transparent;
  cursor: default;
}

.pn-jump {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.pn-info {
  font-size: 12px;
  color: var(--text2);
  white-space: nowrap;
}

.pn-input {
  width: 58px;
  height: 26px;
  padding: 0 6px;
  font-size: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  background: var(--surface);
}
</style>
