<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

// 单接口分析用的接口选择器：颜色圆点 + 接口名 + 请求量/成功率，支持搜索与键盘选择。
// 不用原生 select 是因为 21 个接口只靠名字无法分辨（颜色与请求量才是选中依据）。
type IfaceOption = {
  name: string
  color: string
  requestCount?: number
  successRate?: number | null
  status?: string
}

const props = defineProps<{
  modelValue: string
  options: IfaceOption[]
  placeholder?: string
}>()
const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()

const open = ref(false)
const keyword = ref('')
const activeIndex = ref(0)
const rootRef = ref<HTMLElement | null>(null)
const filterRef = ref<HTMLInputElement | null>(null)

const selected = computed(
  () => props.options.find((option) => option.name === props.modelValue) ?? null,
)
const filtered = computed(() => {
  const kw = keyword.value.trim().toUpperCase()
  return kw
    ? props.options.filter((option) => option.name.toUpperCase().includes(kw))
    : props.options
})

const openPanel = async () => {
  open.value = true
  keyword.value = ''
  const index = filtered.value.findIndex((option) => option.name === props.modelValue)
  activeIndex.value = index >= 0 ? index : 0
  await nextTick()
  filterRef.value?.focus()
}

const closePanel = () => {
  open.value = false
  keyword.value = ''
}

const choose = (name: string) => {
  emit('update:modelValue', name)
  closePanel()
}

const moveActive = (step: number) => {
  const total = filtered.value.length
  if (!total) return
  activeIndex.value = (activeIndex.value + step + total) % total
}

const onKeydown = (event: KeyboardEvent) => {
  if (!open.value) {
    if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') openPanel()
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveActive(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveActive(-1)
  } else if (event.key === 'Enter') {
    event.preventDefault()
    const option = filtered.value[activeIndex.value]
    if (option) choose(option.name)
  } else if (event.key === 'Escape') {
    closePanel()
  }
}

// 筛选后原来的高亮下标可能越界
const onFilterInput = () => {
  activeIndex.value = 0
}

const onDocumentMouseDown = (event: MouseEvent) => {
  if (!open.value) return
  if (rootRef.value && !rootRef.value.contains(event.target as Node)) closePanel()
}

onMounted(() => document.addEventListener('mousedown', onDocumentMouseDown))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocumentMouseDown))
</script>

<template>
  <div ref="rootRef" class="iface-picker" @keydown="onKeydown">
    <button
      type="button"
      class="iface-picker-trigger"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click="open ? closePanel() : openPanel()"
    >
      <span
        class="series-dot"
        :style="{ backgroundColor: selected?.color ?? 'var(--border)' }"
        aria-hidden="true"
      ></span>
      <span class="iface-picker-name">{{ selected?.name || placeholder || '选择接口' }}</span>
      <span v-if="selected?.requestCount != null" class="iface-picker-trigger-meta">
        {{ selected.requestCount.toLocaleString() }} 请求
      </span>
      <span class="iface-picker-caret" aria-hidden="true">▾</span>
    </button>

    <div v-if="open" class="iface-picker-panel">
      <input
        ref="filterRef"
        v-model="keyword"
        class="iface-picker-filter"
        type="text"
        placeholder="搜索接口…"
        autocomplete="off"
        aria-label="搜索接口"
        @input="onFilterInput"
      />
      <ul class="iface-picker-list" role="listbox">
        <li v-for="(option, index) in filtered" :key="option.name">
          <button
            type="button"
            role="option"
            :aria-selected="option.name === modelValue"
            :class="[
              'iface-picker-option',
              { active: index === activeIndex, current: option.name === modelValue },
            ]"
            @mousemove="activeIndex = index"
            @click="choose(option.name)"
          >
            <span
              class="series-dot"
              :style="{ backgroundColor: option.color }"
              aria-hidden="true"
            ></span>
            <span class="iface-picker-option-name">{{ option.name }}</span>
            <span class="iface-picker-option-meta">
              <span>{{ option.requestCount?.toLocaleString() ?? '—' }}</span>
              <span>{{ option.successRate != null ? option.successRate + '%' : '—' }}</span>
              <span v-if="option.status && option.status !== '正常'" class="badge badge-warning">
                偏高
              </span>
            </span>
          </button>
        </li>
      </ul>
      <div v-if="filtered.length === 0" class="iface-picker-empty">没有匹配的接口</div>
    </div>
  </div>
</template>
