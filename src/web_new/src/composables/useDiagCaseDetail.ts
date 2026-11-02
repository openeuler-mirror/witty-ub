import { ref } from 'vue'

const open = ref(false)
const caseId = ref('')
const returnToReport = ref(false)
// Case mutations bump this token so an open report workbench reloads its refs.
const caseVersion = ref(0)

export function useDiagCaseDetail() {
  const bumpCaseVersion = () => {
    caseVersion.value += 1
  }
  const openCase = (id: string, fromReport = false) => {
    caseId.value = id
    returnToReport.value = fromReport
    open.value = true
  }
  const closeCase = () => {
    open.value = false
    returnToReport.value = false
  }
  return { open, caseId, returnToReport, caseVersion, bumpCaseVersion, openCase, closeCase }
}
