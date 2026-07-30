import { onMounted, onBeforeUnmount, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useConfirm } from '@/composables/useConfirm'
import { useI18n } from '@/core/i18n'

export function useDirtyGuard(isDirty: Ref<boolean>) {
  const { showConfirm } = useConfirm()
  const { t } = useI18n()

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
      title: t('unsavedChangesTitle'),
      message: t('unsavedChangesText'),
      confirmText: t('leave'),
      cancelText: t('stay'),
      isDanger: true,
    })

    return confirmed
  })
}
