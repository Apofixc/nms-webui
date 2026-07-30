import { ref } from 'vue'

export interface ToastState {
  message: string
  isError: boolean
}

const toastState = ref<ToastState>({
  message: '',
  isError: false,
})

let timer: ReturnType<typeof setTimeout> | null = null

export function useToast() {
  const showToast = (message: string, isError = false, timeoutMs = 4000) => {
    if (timer) clearTimeout(timer)
    toastState.value = { message, isError }
    timer = setTimeout(() => {
      toastState.value.message = ''
    }, timeoutMs)
  }

  const clearToast = () => {
    if (timer) clearTimeout(timer)
    toastState.value.message = ''
  }

  return {
    toastState,
    showToast,
    clearToast,
  }
}
