import { ref } from 'vue'
import type { Toast } from '../types'

const toasts = ref<Toast[]>([])
let toastSequence = 0

export const useToast = () => {
  const toast = (text: string, type: Toast['type'] = 'info') => {
    const id = ++toastSequence
    toasts.value.push({ id, text, type })
    window.setTimeout(() => {
      toasts.value = toasts.value.filter((item) => item.id !== id)
    }, 3200)
  }

  return { toasts, toast }
}
