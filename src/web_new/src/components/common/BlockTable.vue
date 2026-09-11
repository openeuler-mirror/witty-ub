<script setup lang="ts">
/**
 * 三段式表格：左固定 / 中间横向滚动 / 右固定。
 * 复用聚合表的 .agg-* 样式（表头 56、主行 44、子表头 32、三行接口表头 132/列）。
 * 支持可选展开：传 expandedKey + subRowsOf（+ subKey）后，展开行的三条子槽位生效。
 */
const props = withDefaults(
  defineProps<{
    rows: any[]
    rowKey: (row: any) => string
    leftCols: string[]
    rightCols?: string[]
    midWidth?: string
    expandedKey?: string
    subRowsOf?: (row: any) => any[]
    subKey?: (sub: any) => string
  }>(),
  {
    rightCols: () => ['110px'],
    midWidth: '',
    expandedKey: '',
    subRowsOf: undefined,
    subKey: undefined,
  },
)

const leftTemplate = () => props.leftCols.join(' ')
const rightTemplate = () => props.rightCols.join(' ')
const subId = (row: any, sub: any) => (props.subKey ? props.subKey(sub) : props.rowKey(row))
</script>

<template>
  <div class="agg-table">
    <div class="agg-block agg-left">
      <div class="agg-row agg-head" :style="{ gridTemplateColumns: leftTemplate() }">
        <slot name="left-head" />
      </div>
      <template v-for="row in rows" :key="`l-${rowKey(row)}`">
        <div class="agg-row agg-left-main" :style="{ gridTemplateColumns: leftTemplate() }">
          <slot name="left" :row="row" />
        </div>
        <template v-if="subRowsOf && expandedKey === rowKey(row)">
          <div class="agg-row agg-subhead agg-left-main" :style="{ gridTemplateColumns: leftTemplate() }">
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
        <div class="agg-row agg-head agg-mid-grid"><slot name="mid-head" /></div>
        <template v-for="row in rows" :key="`m-${rowKey(row)}`">
          <div class="agg-row agg-mid-grid">
            <slot name="mid" :row="row" />
          </div>
          <template v-if="subRowsOf && expandedKey === rowKey(row)">
            <div class="agg-row agg-subhead agg-mid-grid">
              <slot name="mid-subhead" :row="row" />
            </div>
            <div
              v-for="sub in subRowsOf(row)"
              :key="`ms-${subId(row, sub)}`"
              class="agg-row agg-subrow agg-mid-grid"
            >
              <slot name="mid-sub" :row="sub" />
            </div>
          </template>
        </template>
      </div>
    </div>

    <div class="agg-block agg-right">
      <div class="agg-row agg-head agg-right-main" :style="{ gridTemplateColumns: rightTemplate() }">
        <slot name="right-head" />
      </div>
      <template v-for="row in rows" :key="`r-${rowKey(row)}`">
        <div class="agg-row agg-right-main" :style="{ gridTemplateColumns: rightTemplate() }">
          <slot name="right" :row="row" />
        </div>
        <template v-if="subRowsOf && expandedKey === rowKey(row)">
          <div class="agg-row agg-subhead agg-right-main" :style="{ gridTemplateColumns: rightTemplate() }">
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
