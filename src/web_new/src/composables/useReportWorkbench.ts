import { ref } from 'vue'

const open = ref(false)
const reportId = ref('')
const sourceFaultId = ref('')

export function useReportWorkbench() {
  const openReport = (id: string, faultId = '') => {
    reportId.value = id
    sourceFaultId.value = faultId
    open.value = true
  }
  const closeReport = () => {
    open.value = false
  }
  return { open, reportId, sourceFaultId, openReport, closeReport }
}
