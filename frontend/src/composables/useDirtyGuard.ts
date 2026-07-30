import { onMounted, onBeforeUnmount, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useConfirm } from '@/composables/useConfirm'
import { useI18n } from '@/core/i18n'

export function useDirtyGuard(isDirty: Ref<boolean>) {
  const { showConfirm } = useConfirm()
  const { lang } = useI18n()

  const handleBeforeUnload = (e: BeforeUnloadEvent) => {
    if (isDirty.value) {
      e.preventDefault()
      e.returnValue = ''
    }
  }

  onMounted(() => {
    window.addEventListener('beforeunload', handleBeforeUnload)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('beforeunload', handleBeforeUnload)
  })

  onBeforeRouteLeave(async () => {
    if (!isDirty.value) return true

    const confirmed = await showConfirm({
      title: lang.value === 'ru' ? 'Несохраненные изменения' : 'Unsaved Changes',
      message: lang.value === 'ru'
        ? 'У вас есть несохраненные изменения. Вы уверены, что хотите покинуть страницу без сохранения?'
        : 'You have unsaved changes. Are you sure you want to leave without saving?',
      confirmText: lang.value === 'ru' ? 'Покинуть' : 'Leave',
      cancelText: lang.value === 'ru' ? 'Остаться' : 'Stay',
      isDanger: true,
    })

    return confirmed
  })
}
