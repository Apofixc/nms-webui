import { ref } from 'vue'

export interface ConfirmOptions {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  isDanger?: boolean
}

interface ConfirmState extends ConfirmOptions {
  resolve: (value: boolean) => void
}

const confirmState = ref<ConfirmState | null>(null)

export function useConfirm() {
  const showConfirm = (options: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      confirmState.value = {
        ...options,
        resolve,
      }
    })
  }

  const handleConfirm = () => {
    if (confirmState.value) {
      confirmState.value.resolve(true)
      confirmState.value = null
    }
  }

  const handleCancel = () => {
    if (confirmState.value) {
      confirmState.value.resolve(false)
      confirmState.value = null
    }
  }

  return {
    confirmState,
    showConfirm,
    handleConfirm,
    handleCancel,
  }
}
