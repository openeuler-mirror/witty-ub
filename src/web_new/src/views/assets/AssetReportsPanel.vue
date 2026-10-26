<script setup lang="ts">
import { watch } from 'vue'
import { useAssets } from '../../composables/useAssets'
import { useReports } from '../../composables/useReports'
import { diagnosticReportHtmlUrl, type DiagnosticReportItem } from '../../api/diagnosticReport'

// 资产工作区「报告」子页：只看当前资产库的报告，跨库查阅去对应资产库
const { selectedAsset } = useAssets()
const {
  assetReports,
  assetReportsTotal,
  assetReportsLoading,
  assetReportsError,
  loadAssetReports,
} = useReports()

const openReport = (report: DiagnosticReportItem) => {
  window.open(diagnosticReportHtmlUrl(report.report_id), '_blank', 'noopener')
}

const displayText = (value: string | number | null | undefined, fallback = '—') => {
  if (value === null || value === undefined || value === '') return fallback
  return String(value)
}

type IndexStatusMeta = { label: string; cls: string }

const INDEX_STATUS_META: Record<string, IndexStatusMeta> = {
  indexed: { label: '已索引', cls: 'badge-success' },
  partial: { label: '部分索引', cls: 'badge-warning' },
  pending: { label: '待索引', cls: 'badge-pending' },
  failed: { label: '索引失败', cls: 'badge-failed' },
  not_applicable: { label: '无需索引', cls: 'badge-cancelled' },
}
const INDEX_STATUS_DEFAULT: IndexStatusMeta = { label: '未知', cls: 'badge-cancelled' }

const indexStatusMeta = (report: DiagnosticReportItem): IndexStatusMeta =>
  INDEX_STATUS_META[report.index_status] ?? INDEX_STATUS_DEFAULT

const reload = () => {
  const kbId = selectedAsset.value?.id
  if (kbId) void loadAssetReports(kbId, 50)
}

watch(
  () => selectedAsset.value?.id,
  () => reload(),
  { immediate: true },
)
</script>
<template>
  <div class="operate-bar">
    <div class="operate-right">
      <span style="font-size: 13px; color: var(--text2)">共 {{ assetReportsTotal }} 份报告</span>
      <button class="btn btn-default" type="button" :disabled="assetReportsLoading" @click="reload">
        刷新
      </button>
    </div>
  </div>

  <div v-if="assetReportsLoading && assetReports.length === 0" class="empty">
    <div class="icon">⏳</div>
    <div>正在加载诊断报告...</div>
  </div>
  <div v-else-if="assetReportsError" class="error-banner">{{ assetReportsError }}</div>
  <div v-else-if="assetReports.length === 0" class="empty">
    <div class="icon">📄</div>
    <div>暂无诊断报告</div>
    <div class="hint">在「分析」页通过 AI 故障诊断助手生成报告后，会在此查阅</div>
  </div>
  <div v-else class="table-wrap">
    <table class="task-table">
      <thead>
        <tr>
          <th>标题</th>
          <th>时间范围</th>
          <th class="num">故障数</th>
          <th>现象索引</th>
          <th class="num">案例</th>
          <th>生成时间</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="report in assetReports" :key="report.report_id">
          <td class="task-name-cell">
            <div class="task-name-block">
              <div class="task-name" :title="report.report_id">
                {{ displayText(report.title, report.file_name) }}
                <span
                  v-if="report.has_sidecar === false"
                  class="badge badge-cancelled"
                  title="侧车 JSON 缺失，标题与故障数等信息不可用"
                >
                  无侧车数据
                </span>
              </div>
              <div v-if="report.operation" class="task-path">
                {{ report.operation }}
              </div>
            </div>
          </td>
          <td>
            <template v-if="report.time_range_start || report.time_range_end">
              {{ displayText(report.time_range_start) }} ~ {{ displayText(report.time_range_end) }}
            </template>
            <template v-else>—</template>
          </td>
          <td class="num">
            {{ report.has_sidecar === false ? '—' : displayText(report.fault_count) }}
          </td>
          <td>
            <span
              class="badge"
              :class="indexStatusMeta(report).cls"
              :title="report.index_error || undefined"
            >
              {{ indexStatusMeta(report).label }}
            </span>
          </td>
          <td class="num">{{ report.case_count }}</td>
          <td>{{ displayText(report.generated_at) }}</td>
          <td>
            <button class="btn btn-sm btn-primary" type="button" @click="openReport(report)">
              查看
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
