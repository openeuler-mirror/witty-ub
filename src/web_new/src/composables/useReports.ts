import { ref } from 'vue'
import { fetchDiagnosticReports, type DiagnosticReportItem } from '../api/diagnosticReport'

let state: ReturnType<typeof createReportsState> | null = null

export function useReports() {
  if (!state) state = createReportsState()
  return state
}

function createReportsState() {
  // 资产工作区「报告」子页列表（本资产库，一次拉满展示量）
  const assetReports = ref<DiagnosticReportItem[]>([])
  const assetReportsTotal = ref(0)
  const assetReportsLoading = ref(false)
  const assetReportsError = ref('')
  let assetReportsKbId = ''

  const loadAssetReports = async (kbId: string, pageCnt: number) => {
    assetReportsKbId = kbId
    assetReportsLoading.value = true
    assetReportsError.value = ''
    try {
      const result = await fetchDiagnosticReports({ kbId, pageNum: 1, pageCnt })
      if (assetReportsKbId !== kbId) return
      assetReports.value = result.items ?? []
      assetReportsTotal.value = result.total ?? 0
    } catch (err) {
      if (assetReportsKbId !== kbId) return
      assetReports.value = []
      assetReportsError.value = err instanceof Error ? err.message : '诊断报告加载失败'
    } finally {
      if (assetReportsKbId === kbId) assetReportsLoading.value = false
    }
  }

  return {
    assetReports,
    assetReportsTotal,
    assetReportsLoading,
    assetReportsError,
    loadAssetReports,
  }
}
