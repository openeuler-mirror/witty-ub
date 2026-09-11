<script setup lang="ts">
/**
 * 三段式表格（对齐旧版）：左固定 / 中间横向滚动 / 右固定。
 * 三块行高由同一套 CSS 类保证一致，因此天然逐行对齐；
 * 支持可选展开行（明细子表头 + 多行子数据）。
 */
const props = withDefaults(
  defineProps<{
    rows: any[]
    rowKey: (row: any) => string
    /** 左固定块列宽（px 数组），用于生成 grid-template-columns */
    leftCols: string[]
    /** 中间滚动区总宽度（px），未传则按列宽自动 */
    midWidth?: string
    /** 展开相关（不传则不具备展开能力） */
    expandedKey?: string
    subRowsOf?: (row: any) => any[]
    subKey?: (row: any) => string
  }>(),
  { midWidth: '', expandedKey: '', subRowsOf: undefined, subKey: undefined },
)

const leftTemplate = () => props.leftCols.join(' ')
</script>

<template>
  <div class="bt-table">
    <!-- 左固定 -->
    <div class="bt-block bt-left">
      <div class="bt-row bt-head" :style="{ gridTemplateColumns: leftTemplate() }">
        <slot name="left-head" />
      </div>
      <template v-for="row in rows" :key="rowKey(row)">
        <div class="bt-row bt-main" :style="{ gridTemplateColumns: leftTemplate() }">
          <slot name="left" :row="row" />
        </div>
        <template v-if="subRowsOf && expandedKey === rowKey(row)">
          <div class="bt-row bt-subhead" :style="{ gridTemplateColumns: leftTemplate() }">
            <slot name="left-subhead" :row="row" />
          </div>
          <div
            v-for="sub in subRowsOf(row)"
            :key="subKey ? subKey(sub) : rowKey(row)"
            class="bt-row bt-subrow"
            :style="{ gridTemplateColumns: leftTemplate() }"
          >
            <slot name="left-sub" :row="sub" />
          </div>
        </template>
      </template>
    </div>

    <!-- 中间：横向滚动 -->
    <div class="bt-block bt-mid">
      <div class="bt-mid-inner" :style="midWidth ? { width: midWidth } : {}">
        <div class="bt-row bt-head bt-mid-grid"><slot name="mid-head" /></div>
        <template v-for="row in rows" :key="`m-${rowKey(row)}`">
          <div class="bt-row bt-main bt-mid-grid"><slot name="mid" :row="row" /></div>
          <template v-if="subRowsOf && expandedKey === rowKey(row)">
            <div class="bt-row bt-subhead bt-mid-grid">
              <slot name="mid-subhead" :row="row" />
            </div>
            <div
              v-for="sub in subRowsOf(row)"
              :key="`ms-${subKey ? subKey(sub) : rowKey(row)}`"
              class="bt-row bt-subrow bt-mid-grid"
            >
              <slot name="mid-sub" :row="sub" />
            </div>
          </template>
        </template>
      </div>
    </div>

    <!-- 右固定 -->
    <div class="bt-block bt-right">
      <div class="bt-row bt-head bt-right-grid"><slot name="right-head" /></div>
      <template v-for="row in rows" :key="`r-${rowKey(row)}`">
        <div class="bt-row bt-main bt-right-grid"><slot name="right" :row="row" /></div>
        <template v-if="subRowsOf && expandedKey === rowKey(row)">
          <div class="bt-row bt-subhead bt-right-grid">
            <slot name="right-subhead" :row="row" />
          </div>
          <div
            v-for="sub in subRowsOf(row)"
            :key="`rs-${subKey ? subKey(sub) : rowKey(row)}`"
            class="bt-row bt-subrow bt-right-grid"
          >
            <slot name="right-sub" :row="sub" />
          </div>
        </template>
      </template>
    </div>
  </div>
</template>
