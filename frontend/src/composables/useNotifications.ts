import { apiCreateNotification, type NotificationCreatePayload, type NotificationItem } from '@/core/api'
import { useToast } from '@/composables/useToast'

export function useNotifications() {
  const { showToast } = useToast()

  /**
   * Отправить новое уведомление в Центр Уведомлений
   * @param payload Данные уведомления (title, message, type, category, link, user_id)
   * @param showLocalToast Отобразить ли мгновенно всплывающий toast (по умолчанию true)
   */
  async function notify(
    payload: NotificationCreatePayload,
    showLocalToast = true
  ): Promise<NotificationItem | null> {
    try {
      if (showLocalToast) {
        const isError = payload.type === 'error'
        showToast(`${payload.title}: ${payload.message}`, isError)
      }
      return await apiCreateNotification(payload)
    } catch (err) {
      console.error('Failed to create notification via useNotifications:', err)
      return null
    }
  }

  return {
    notify,
  }
}
