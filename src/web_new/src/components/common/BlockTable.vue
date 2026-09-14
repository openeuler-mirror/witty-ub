<script setup lang="ts">
/**
 * 三段式表格：左固定 / 中间横向滚动 / 右固定。
 * 复用聚合表的 .agg-* 样式（表头 56、主行 44、子表头 32、三行接口表头 132/列）。
 * 支持可选展开：传 expandedKey + subRowsOf（+ subKey）后，展开行的三条子槽位生效。
 * 三块是三个独立列块，内容换行后各块行高会不一致；这里按行同步 min-height，
 * 保证左/中/右逐行对齐（内容型表格允许换行时的必要条件）。
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    rows: any[]
    rowKey: (row: any) => string
    leftCols: string[]
    rightCols?: string[]
    midWidth?: string
    /** 中间区各列宽度，如 ['220px','260px','240px']；不传则按 132px 均分 */
    midCols?: string[]
    expandedKey?: string
    subRowsOf?: (row: any) => any[]
    subKey?: (sub: any) => string
  }>(),
  {
    rightCols: () => ['110px'],
    midWidth: '',
    midCols: () => [],
    expandedKey: '',
    subRowsOf: undefined,
    subKey: undefined,
  },
)

const leftTemplate = () => props.leftCols.join(' ')
const rightTemplate = () => props.rightCols.join(' ')
const midTemplate = () =>
  props.midCols.length
    ? props.midCols.join(' ')
    : `repeat(${Math.max(1, props.midCols.length)}, 132px)`
const midGridStyle = () => (props.midCols.length ? { gridTemplateColumns: midTemplate() } : {})
const subId = (row: any, sub: any) => (props.subKey ? props.subKey(sub) : props.rowKey(row))

const rootEl = ref<HTMLElement | null>(null)
let resizeObserver: ResizeObserver | null = null
let mutationObserver: MutationObserver | null = null
let syncScheduled = false

// 中区多一层 .agg-mid-inner（承载固定内宽），行在它下面
const rowsOfBlock = (block: Element) => {
  const container = block.querySelector(':scope > .agg-mid-inner') ?? block
  return Array.from(container.children).filter((el) =>
    el.classList.contains('agg-row'),
  ) as HTMLElement[]
}

/** 三块逐行取最大高度回写 min-height；先清空再测量，保证内容变短时也能收回 */
const syncRowHeights = () => {
  const root = rootEl.value
  if (!root) return
  const blocks = Array.from(root.querySelectorAll<HTMLElement>('.agg-block'))
  if (blocks.length < 2) return
  const rowsPerBlock = blocks.map(rowsOfBlock)
  rowsPerBlock.forEach((rows) => rows.forEach((row) => row.style.removeProperty('min-height')))
  const rowCount = Math.max(...rowsPerBlock.map((rows) => rows.length))
  for (let index = 0; index < rowCount; index += 1) {
    const rows = rowsPerBlock
      .map((list) => list[index])
      .filter((row): row is HTMLElement => Boolean(row))
    if (rows.length < 2) continue
    const max = Math.ceil(Math.max(...rows.map((row) => row.getBoundingClientRect().height)))
    rows.forEach((row) => {
      if (row.getBoundingClientRect().height < max) row.style.minHeight = `${max}px`
    })
  }
}

const scheduleSync = () => {
  if (syncScheduled) return
  syncScheduled = true
  void nextTick(() => {
    syncScheduled = false
    syncRowHeights()
  })
}

watch(
  () => [props.rows, props.expandedKey, props.midCols, props.leftCols, props.rightCols],
  scheduleSync,
  { deep: false },
)

onMounted(() => {
  scheduleSync()
  if (typeof ResizeObserver !== 'undefined' && rootEl.value) {
    resizeObserver = new ResizeObserver(scheduleSync)
    resizeObserver.observe(rootEl.value)
  }
  // 单元格内容延后到达（如故障模式名称异步加载）时也要重新对齐；
  // 只监听结构/文本，不监听属性，避免回写 min-height 触发自循环
  if (typeof MutationObserver !== 'undefined' && rootEl.value) {
    mutationObserver = new MutationObserver(scheduleSync)
    mutationObserver.observe(rootEl.value, { childList: true, subtree: true, characterData: true })
  }
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  mutationObserver?.disconnect()
  mutationObserver = null
})
</script>

<template>
  <div ref="rootEl" class="agg-table">
    <div class="agg-block agg-left">
      <div class="agg-row agg-head" :style="{ gridTemplateColumns: leftTemplate() }">
        <slot name="left-head" />
      </div>
      <template v-for="row in rows" :key="`l-${rowKey(row)}`">
        <div class="agg-row agg-left-main" :style="{ gridTemplateColumns: leftTemplate() }">
          <slot name="left" :row="row" />
        </div>
        <template v-if="subRowsOf && expandedKey === rowKey(row)">
          <div
            class="agg-row agg-subhead agg-left-main"
            :style="{ gridTemplateColumns: leftTemplate() }"
          >
            <slot name="left-subhead" :row="row" />
          </div>
          <div
            v-for="sub in subRowsOf(row)"
            :key="`ls-${subId(row, sub)}`"
            class="agg-row agg-subrow agg-left-main"
            :style="{ gridTemplateColumns: leftTemplate() }"
          >
            <slot name="left-sub" :row="sub" />
          </div>
        </template>
      </template>
    </div>

    <div class="agg-block agg-mid">
      <div class="agg-mid-inner" :style="midWidth ? { width: midWidth } : {}">
        <div class="agg-row agg-head agg-mid-grid" :style="midGridStyle()">
          <slot name="mid-head" />
        </div>
        <template v-for="row in rows" :key="`m-${rowKey(row)}`">
          <div class="agg-row agg-mid-grid" :style="midGridStyle()">
            <slot name="mid" :row="row" />
          </div>
          <template v-if="subRowsOf && expandedKey === rowKey(row)">
            <div class="agg-row agg-subhead agg-mid-grid" :style="midGridStyle()">
              <slot name="mid-subhead" :row="row" />
            </div>
            <div
              v-for="sub in subRowsOf(row)"
              :key="`ms-${subId(row, sub)}`"
              class="agg-row agg-subrow agg-mid-grid"
              :style="midGridStyle()"
            >
              <slot name="mid-sub" :row="sub" />
            </div>
          </template>
        </template>
      </div>
    </div>

    <div class="agg-block agg-right">
      <div
        class="agg-row agg-head agg-right-main"
        :style="{ gridTemplateColumns: rightTemplate() }"
      >
        <slot name="right-head" />
      </div>
      <template v-for="row in rows" :key="`r-${rowKey(row)}`">
        <div class="agg-row agg-right-main" :style="{ gridTemplateColumns: rightTemplate() }">
          <slot name="right" :row="row" />
        </div>
        <template v-if="subRowsOf && expandedKey === rowKey(row)">
          <div
            class="agg-row agg-subhead agg-right-main"
            :style="{ gridTemplateColumns: rightTemplate() }"
          >
            <slot name="right-subhead" :row="row" />
          </div>
          <div
            v-for="sub in subRowsOf(row)"
            :key="`rs-${subId(row, sub)}`"
            class="agg-row agg-subrow agg-right-main"
            :style="{ gridTemplateColumns: rightTemplate() }"
          >
            <slot name="right-sub" :row="sub" />
          </div>
        </template>
      </template>
    </div>
  </div>
</template>
