import {
  apiCreateNotification,
  apiFetchUnreadCount,
  apiMarkNotificationRead,
  apiMarkAllNotificationsRead,
  apiAcknowledgeNotification,
  type NotificationCreatePayload,
  type NotificationItem,
} from '@/core/api'
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

  /**
   * Получить количество непрочитанных уведомлений
   */
  async function fetchUnreadCount(): Promise<number> {
    try {
      const res = await apiFetchUnreadCount()
      return res.count
    } catch (err) {
      console.error('Failed to fetch unread count:', err)
      return 0
    }
  }

  /**
   * Отметить уведомление как прочитанное
   */
  async function markAsRead(id: number): Promise<boolean> {
    try {
      await apiMarkNotificationRead(id)
      return true
    } catch (err) {
      console.error(`Failed to mark notification ${id} as read:`, err)
      return false
    }
  }

  /**
   * Отметить все уведомления как прочитанные
   */
  async function markAllAsRead(): Promise<boolean> {
    try {
      await apiMarkAllNotificationsRead()
      return true
    } catch (err) {
      console.error('Failed to mark all notifications as read:', err)
      return false
    }
  }

  /**
   * Квитировать (подтвердить) аварию
   */
  async function acknowledge(id: number): Promise<NotificationItem | null> {
    try {
      return await apiAcknowledgeNotification(id)
    } catch (err) {
      console.error(`Failed to acknowledge notification ${id}:`, err)
      return null
    }
  }

  return {
    notify,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    acknowledge,
  }
}

