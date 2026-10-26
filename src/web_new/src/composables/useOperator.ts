import { ref } from 'vue'

const STORAGE_KEY = 'witty-operator'
const operator = ref(
  typeof localStorage === 'undefined' ? '' : localStorage.getItem(STORAGE_KEY) ?? '',
)

export function useOperator() {
  const setOperator = (value: string) => {
    operator.value = value.trim()
    if (typeof localStorage !== 'undefined') {
      if (operator.value) localStorage.setItem(STORAGE_KEY, operator.value)
      else localStorage.removeItem(STORAGE_KEY)
    }
  }
  const requireOperator = () => operator.value.trim()
  return { operator, setOperator, requireOperator }
}
