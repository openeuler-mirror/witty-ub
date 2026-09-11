<script setup lang="ts">
/**
 * 三段式表格：左固定 / 中间横向滚动 / 右固定。
 * 复用聚合表的 .agg-* 样式（行高、表头、三行接口表头），保证各表外观完全一致。
 * 用法：通过 left/mid/right 三类插槽渲染单元格，列宽由 leftCols / rightCols / midWidth 决定。
 */
const props = withDefaults(
  defineProps<{
    rows: any[]
    rowKey: (row: any) => string
    /** 左固定块列宽，如 ['110px','130px','150px','96px'] */
    leftCols: string[]
    /** 右固定块列宽，默认 ['110px'] */
    rightCols?: string[]
    /** 中间滚动区总宽度，如 '924px' */
    midWidth?: string
  }>(),
  { rightCols: () => ['110px'], midWidth: '' },
)

const leftTemplate = () => props.leftCols.join(' ')
const rightTemplate = () => props.rightCols.join(' ')
</script>

<template>
  <div class="agg-table">
    <div class="agg-block agg-left">
      <div class="agg-row agg-head" :style="{ gridTemplateColumns: leftTemplate() }">
        <slot name="left-head" />
      </div>
      <div
        v-for="row in rows"
        :key="`l-${rowKey(row)}`"
        class="agg-row agg-left-main"
        :style="{ gridTemplateColumns: leftTemplate() }"
      >
        <slot name="left" :row="row" />
      </div>
    </div>

    <div class="agg-block agg-mid">
      <div class="agg-mid-inner" :style="midWidth ? { width: midWidth } : {}">
        <div class="agg-row agg-head agg-mid-grid"><slot name="mid-head" /></div>
        <div
          v-for="row in rows"
          :key="`m-${rowKey(row)}`"
          class="agg-row agg-mid-grid"
        >
          <slot name="mid" :row="row" />
        </div>
      </div>
    </div>

    <div class="agg-block agg-right">
      <div class="agg-row agg-head agg-right-main" :style="{ gridTemplateColumns: rightTemplate() }">
        <slot name="right-head" />
      </div>
      <div
        v-for="row in rows"
        :key="`r-${rowKey(row)}`"
        class="agg-row agg-right-main"
        :style="{ gridTemplateColumns: rightTemplate() }"
      >
        <slot name="right" :row="row" />
      </div>
    </div>
  </div>
</template>
