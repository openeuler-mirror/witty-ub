import { ref } from 'vue'

const open = ref(false)
const caseId = ref('')
// Case mutations bump this token so an open report workbench reloads its refs.
const caseVersion = ref(0)

export function useDiagCaseDetail() {
  const bumpCaseVersion = () => {
    caseVersion.value += 1
  }
  const openCase = (id: string) => {
    caseId.value = id
    open.value = true
  }
  const closeCase = () => {
    open.value = false
    bumpCaseVersion()
  }
  return { open, caseId, caseVersion, bumpCaseVersion, openCase, closeCase }
}
