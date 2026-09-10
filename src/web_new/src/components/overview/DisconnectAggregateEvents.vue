<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useOverviewData } from '../../composables/useOverviewData'
import PageNav from '../common/PageNav.vue'

const {
  currentOp,
  disconnectFilter,
  enterFaultAggPairDetail,
  faultAggErrCodes,
  faultAggError,
  faultAggExpandedBucket,
  faultAggExpandedKey,
  faultAggInterval,
  faultAggIntervalOptions,
  faultAggLoading,
  faultAggPage,
  faultAggPages,
  faultAggPairs,
  faultAggPairsErrCodes,
  faultAggPairsLoading,
  faultAggPairsPage,
  faultAggPairsPages,
  faultAggPairsSortBy,
  faultAggPairsSortDesc,
  faultAggPairsSortField,
  faultAggPairsTotal,
  faultAggRows,
  faultAggSortBy,
  faultAggSortDesc,
  faultAggSortField,
  faultAggTotal,
  faultTimeRange,
  loadFaultAggEvents,
  loadFaultAggPairs,
  toggleFaultAggBucket,
} = useOverviewData()

const bucketKey = (row: { start_time: string; end_time: string }) =>
  `${row.start_time}|${row.end_time}`
const aggCount = (row: { status_code_cnt: Record<string, number> }, code: string) =>
  row.status_code_cnt?.[code] ?? 0

const reload = () => {
  faultAggSortField.value = 'timestamp'
  faultAggSortDesc.value = false
  faultAggExpandedKey.value = ''
  void loadFaultAggEvents(1)
}

onMounted(reload)
watch([faultAggInterval, currentOp, () => disconnectFilter.time.value], reload)
</script>

<template>
  <div class="aggregate-notes" role="note">
    <span>服务端完整聚合，不受主视图 2500 条明细保护上限影响</span>
    <span>不随单日志文件选择收窄</span>
    <span>接口时间右边界为闭区间，与故障诊断页半开区间不同</span>
  </div>

  <section class="section-card">
    <header class="aggregate-header">
      <div>
        <h2 class="section-card-title">故障时间桶矩阵</h2>
        <p>
          {{ currentOp }} ·
          {{ faultTimeRange ? `${faultTimeRange.start} ~ ${faultTimeRange.end}` : '全部时段' }}
        </p>
      </div>
      <label class="aggregate-scale" for="fault-agg-interval">
        <span>聚合尺度</span>
        <select id="fault-agg-interval" class="select" v-model="faultAggInterval">
          <option v-for="opt in faultAggIntervalOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </label>
    </header>

    <div v-if="faultAggError" class="error-banner">{{ faultAggError }}</div>
    <div v-if="faultAggLoading && faultAggRows.length === 0" class="empty aggregate-empty">
      <div class="icon">⏳</div>
      <div>聚合事件加载中…</div>
    </div>
    <div v-else-if="faultAggRows.length === 0" class="empty aggregate-empty">
      <div class="icon">📭</div>
      <div>{{ faultTimeRange ? '当前时间范围内无聚合故障事件' : '暂无聚合故障事件' }}</div>
    </div>

    <template v-else>
      <div class="table-wrap" role="region" tabindex="0" aria-label="通断聚合事件表，可左右滚动">
        <table class="fault-agg-table">
          <thead>
            <tr>
              <th class="expand-column"></th>
              <th class="sortable" @click="faultAggSortBy('timestamp')">
                开始时间
                <span v-if="faultAggSortField === 'timestamp'" class="sort-mark">{{
                  faultAggSortDesc ? '↓' : '↑'
                }}</span>
              </th>
              <th>结束时间</th>
              <th
                v-for="code in faultAggErrCodes"
                :key="code"
                class="sortable num"
                @click="faultAggSortBy(code)"
              >
                {{ code === 'all' ? '故障总数' : `故障码 ${code}` }}
                <span v-if="faultAggSortField === code" class="sort-mark">{{
                  faultAggSortDesc ? '↓' : '↑'
                }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in faultAggRows" :key="bucketKey(row)">
              <tr
                :class="{ 'row-expanded': bucketKey(row) === faultAggExpandedKey }"
                @click="toggleFaultAggBucket(row)"
              >
                <td class="expand-mark">
                  {{ bucketKey(row) === faultAggExpandedKey ? '▾' : '▸' }}
                </td>
                <td class="mono">{{ row.start_time }}</td>
                <td class="mono">{{ row.end_time }}</td>
                <td v-for="code in faultAggErrCodes" :key="code" class="num">
                  {{ aggCount(row, code) || '-' }}
                </td>
              </tr>
              <tr v-if="bucketKey(row) === faultAggExpandedKey" class="pair-subrow">
                <td :colspan="3 + faultAggErrCodes.length">
                  <div class="pair-heading">
                    <strong>桶内故障链路</strong>
                    <span>{{ row.start_time }} ~ {{ row.end_time }}</span>
                  </div>
                  <div v-if="faultAggPairsLoading" class="hint pair-state">IP 对加载中…</div>
                  <div v-else-if="faultAggPairs.length === 0" class="hint pair-state">
                    该时间桶内无源/目标 IP 对
                  </div>
                  <template v-else>
                    <table class="fault-agg-pair-table">
                      <thead>
                        <tr>
                          <th>源 IP</th>
                          <th>目标 IP</th>
                          <th
                            v-for="code in faultAggPairsErrCodes"
                            :key="code"
                            class="sortable num"
                            @click.stop="faultAggPairsSortBy(code)"
                          >
                            {{ code === 'all' ? '故障总数' : `故障码 ${code}` }}
                            <span v-if="faultAggPairsSortField === code" class="sort-mark">{{
                              faultAggPairsSortDesc ? '↓' : '↑'
                            }}</span>
                          </th>
                          <th>证据</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="pair in faultAggPairs" :key="pair.src_ip + '→' + pair.dst_ip">
                          <td class="mono">{{ pair.src_ip || '-' }}</td>
                          <td class="mono">{{ pair.dst_ip || '-' }}</td>
                          <td v-for="code in faultAggPairsErrCodes" :key="code" class="num">
                            {{ aggCount(pair, code) || '-' }}
                          </td>
                          <td>
                            <button
                              class="btn btn-sm btn-primary"
                              @click.stop="
                                enterFaultAggPairDetail(
                                  pair.src_ip,
                                  pair.dst_ip,
                                  faultAggExpandedBucket!,
                                )
                              "
                            >
                              查看故障 Trace
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    <footer class="aggregate-footer">
                      <span>共 {{ faultAggPairsTotal }} 对</span>
                      <PageNav
                        v-if="faultAggPairsPages > 1"
                        :page="faultAggPairsPage"
                        :pages="faultAggPairsPages"
                        @update:page="loadFaultAggPairs"
                      />
                    </footer>
                  </template>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <footer class="aggregate-footer">
        <span>共 {{ faultAggTotal }} 桶{{ faultAggLoading ? ' · 刷新中…' : '' }}</span>
        <PageNav
          v-if="faultAggPages > 1"
          :page="faultAggPage"
          :pages="faultAggPages"
          @update:page="loadFaultAggEvents"
        />
      </footer>
    </template>
  </section>
</template>

<style scoped>
.aggregate-header p {
  margin: 0;
  color: var(--text2);
  font-size: 12px;
  line-height: 1.6;
}
.aggregate-notes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  padding: 9px 14px;
  margin-bottom: 16px;
  border-left: 3px solid #f59e0b;
  background: #fffbeb;
  color: #92400e;
  font-size: 11px;
}
.aggregate-header,
.aggregate-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.aggregate-header {
  margin-bottom: 14px;
}
.aggregate-scale {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text2);
  font-size: 12px;
}
.aggregate-footer {
  margin-top: 12px;
  color: var(--text2);
  font-size: 12px;
}
.aggregate-empty {
  padding: 38px 0;
}
.fault-agg-table,
.fault-agg-pair-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.fault-agg-table th,
.fault-agg-table td,
.fault-agg-pair-table th,
.fault-agg-pair-table td {
  padding: 9px 10px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.fault-agg-table th {
  background: var(--bg);
  color: var(--text2);
  font-size: 12px;
  font-weight: 600;
}
.sortable {
  cursor: pointer;
  user-select: none;
}
.sortable:hover,
.sort-mark {
  color: var(--primary);
}
.num {
  text-align: right !important;
}
.expand-column {
  width: 40px;
}
.expand-mark {
  color: var(--text3);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}
.fault-agg-table tbody tr:not(.pair-subrow) {
  cursor: pointer;
}
.fault-agg-table tbody tr:not(.pair-subrow):hover,
.row-expanded {
  background: var(--primary-bg);
}
.pair-subrow > td {
  padding: 14px 18px 16px 40px;
  background: var(--bg);
}
.pair-heading {
  display: flex;
  justify-content: space-between;
  margin-bottom: 9px;
  color: var(--text2);
  font-size: 11px;
}
.pair-heading strong {
  color: var(--text);
  font-size: 12px;
}
.pair-state {
  padding: 12px 0;
}
.fault-agg-pair-table {
  background: var(--surface);
  border: 1px solid var(--border);
}
.fault-agg-pair-table th {
  background: var(--primary-bg);
  color: var(--text2);
  font-size: 11px;
}
@media (max-width: 800px) {
  .aggregate-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
