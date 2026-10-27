import { ref } from 'vue'

const open = ref(false)
const reportId = ref('')
const sourceFaultId = ref('')
const resume = ref(false)

export function useReportWorkbench() {
  const openReport = (id: string, faultId = '') => {
    reportId.value = id
    sourceFaultId.value = faultId
    resume.value = false
    open.value = true
  }
  const closeReport = () => {
    open.value = false
    resume.value = false
  }
  const suspendReport = () => { open.value = false }
  const resumeReport = () => { resume.value = true; open.value = true }
  return { open, reportId, sourceFaultId, resume, openReport, closeReport, suspendReport, resumeReport }
}
