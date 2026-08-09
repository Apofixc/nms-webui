<template>
  <div class="relative" ref="containerRef">
    <!-- Notifications Bell Button -->
    <button
      @click="toggleOpen"
      :title="t('notificationsTitle')"
      class="p-2 hover:text-primary transition-colors cursor-pointer rounded-full hover:bg-surface-variant/50 relative text-on-surface-variant flex items-center justify-center focus:outline-none"
    >
      <span class="material-symbols-outlined text-[20px]">notifications_active</span>
      <span
        v-if="unreadCount > 0"
        class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-error text-on-error font-mono text-[10px] font-bold flex items-center justify-center shadow-sm animate-pulse"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- Dropdown Popover Panel -->
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 scale-95 -translate-y-1"
      enter-to-class="opacity-100 scale-100 translate-y-0"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 scale-100 translate-y-0"
      leave-to-class="opacity-0 scale-95 -translate-y-1"
    >
      <div
        v-if="isOpen"
        class="absolute right-0 mt-2 w-[360px] sm:w-[440px] bg-surface-container-high border border-outline-variant rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col text-on-surface ring-1 ring-white/10"
      >
        <!-- Header -->
        <div class="p-3.5 border-b border-outline-variant flex items-center justify-between bg-surface-container-highest/60 gap-2">
          <div class="flex items-center gap-2 flex-shrink-0">
            <h3 class="font-bold text-sm text-on-surface whitespace-nowrap">{{ t('notificationsTitle') }}</h3>
            <span v-if="unreadCount > 0" class="px-2 py-0.5 rounded-full bg-primary/20 text-primary font-mono text-xs font-semibold">
              {{ unreadCount }}
            </span>
          </div>

          <div class="flex items-center gap-1 text-xs">
            <!-- Integration settings button -->
            <button
              @click="showIntegrationsModal = true"
              :title="t('externalIntegrationsSettingsTitle')"
              class="p-1.5 rounded-lg transition-colors flex items-center justify-center text-primary hover:bg-primary/10"
            >
              <span class="material-symbols-outlined text-[18px]">hub</span>
            </button>

            <!-- Toggles for Sound & Web Push & DND -->
            <button
              @click="toggleSound"
              :title="soundEnabled ? t('soundNotificationsEnabled') : t('soundNotificationsDisabled')"
              :class="['p-1.5 rounded-lg transition-colors flex items-center justify-center', soundEnabled ? 'text-primary hover:bg-primary/10' : 'text-on-surface-variant/40 hover:bg-surface-variant/30']"
            >
              <span class="material-symbols-outlined text-[18px]">{{ soundEnabled ? 'volume_up' : 'volume_off' }}</span>
            </button>
            <button
              @click="togglePush"
              :title="pushEnabled ? t('pushNotificationsEnabled') : t('pushNotificationsDisabled')"
              :class="['p-1.5 rounded-lg transition-colors flex items-center justify-center', pushEnabled ? 'text-primary hover:bg-primary/10' : 'text-on-surface-variant/40 hover:bg-surface-variant/30']"
            >
              <span class="material-symbols-outlined text-[18px]">{{ pushEnabled ? 'notifications_active' : 'notifications_off' }}</span>
            </button>
            <button
              @click="toggleDnd"
              :title="dndEnabled ? 'Режим НЕ БЕСПОКОИТЬ включен' : 'Режим НЕ БЕСПОКОИТЬ выключен'"
              :class="['p-1.5 rounded-lg transition-colors flex items-center justify-center', dndEnabled ? 'text-amber-400 bg-amber-500/20' : 'text-on-surface-variant/40 hover:bg-surface-variant/30']"
            >
              <span class="material-symbols-outlined text-[18px]">{{ dndEnabled ? 'do_not_disturb_on' : 'do_not_disturb_off' }}</span>
            </button>

            <span class="text-outline/40 mx-0.5">|</span>

            <!-- Mark All Read -->
            <button
              v-if="unreadCount > 0"
              @click="handleMarkAllRead"
              :title="t('notificationsMarkAllRead')"
              class="p-1.5 rounded-lg text-primary hover:bg-primary/10 transition-colors flex items-center justify-center"
            >
              <span class="material-symbols-outlined text-[18px]">done_all</span>
            </button>

            <span v-if="unreadCount > 0 && notifications.length > 0" class="text-outline/40 mx-0.5">|</span>

            <!-- Clear All -->
            <button
              v-if="notifications.length > 0"
              @click="handleClearAll"
              :title="t('notificationsClearAll')"
              class="p-1.5 rounded-lg text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors flex items-center justify-center"
            >
              <span class="material-symbols-outlined text-[18px]">delete_sweep</span>
            </button>
          </div>
        </div>

        <!-- Search Input Bar -->
        <div class="px-3 py-2 border-b border-outline-variant/30 bg-surface-container-lowest/60">
          <div class="relative flex items-center bg-surface-container-highest/50 border border-outline-variant/30 rounded-xl px-3 py-1.5 focus-within:border-primary/80 focus-within:bg-surface-container-highest focus-within:ring-2 focus-within:ring-primary/20 transition-all group">
            <span class="material-symbols-outlined text-[18px] text-on-surface-variant/60 group-focus-within:text-primary transition-colors flex-shrink-0">search</span>
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="t('searchHistoryPlaceholder')"
              class="w-full !bg-transparent text-xs !text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none ml-2"
            />
            <button
              v-if="searchQuery"
              @click="searchQuery = ''"
              class="p-0.5 text-on-surface-variant/60 hover:text-on-surface hover:bg-surface-variant/50 rounded-full transition-colors flex items-center justify-center flex-shrink-0"
            >
              <span class="material-symbols-outlined text-[14px]">close</span>
            </button>
          </div>
        </div>

        <!-- Filter Tabs -->
        <div class="px-3 py-2 border-b border-outline-variant flex items-center gap-1 overflow-x-auto text-xs bg-surface-container-lowest/40">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'px-2.5 py-1 rounded-lg font-medium transition-all whitespace-nowrap',
              activeTab === tab.id
                ? 'bg-primary text-on-primary shadow-sm'
                : 'text-on-surface-variant hover:bg-surface-variant/50'
            ]"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Notifications List -->
        <div class="max-h-[380px] overflow-y-auto">
          <div
            v-if="filteredNotifications.length === 0"
            class="py-12 px-4 text-center text-on-surface-variant/60 flex flex-col items-center justify-center gap-2"
          >
            <span class="material-symbols-outlined text-4xl opacity-40">notifications_off</span>
            <p class="text-xs font-medium">{{ t('noNotifications') }}</p>
          </div>

          <div
            v-for="item in filteredNotifications"
            :key="item.id"
            @click="handleItemClick(item)"
            :class="[
              'p-3 flex items-start gap-2.5 transition-colors group relative cursor-pointer border-b border-outline-variant/20 last:border-b-0',
              item.read
                ? 'bg-surface-container-low/60 hover:bg-surface-container-low'
                : 'bg-surface-container-highest/80 hover:bg-surface-container-highest border-l-4 border-l-primary'
            ]"
          >
            <!-- Status Dot for Unread -->
            <span
              v-if="!item.read"
              class="w-2 h-2 rounded-full bg-primary absolute top-4 left-1 flex-shrink-0"
            />

            <!-- Type Icon -->
            <div
              :class="[
                'w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ml-1',
                getTypeIconBg(item.type)
              ]"
            >
              <span class="material-symbols-outlined text-[18px]">{{ getTypeIconName(item.type) }}</span>
            </div>

            <!-- Content -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5 mb-0.5 min-w-0 flex-wrap">
                <h4 class="text-xs font-bold text-on-surface truncate">{{ t(item.title) }}</h4>
                <span
                  v-if="(item as any).repeat_count && (item as any).repeat_count > 1"
                  title="Повторяющееся уведомление (дедуплицировано)"
                  class="px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-primary/20 text-primary flex items-center gap-0.5 flex-shrink-0"
                >
                  x{{ (item as any).repeat_count }}
                </span>
                <span
                  v-if="item.status === 'resolved' || item.type === 'resolved'"
                  title="Авария автоматически закрыта (Resolved)"
                  class="px-1.5 py-0.2 text-[9px] font-semibold rounded bg-teal-500/20 text-teal-300 flex items-center gap-0.5 flex-shrink-0"
                >
                  <span class="material-symbols-outlined text-[10px]">task_alt</span>
                  Resolved
                </span>
                <span
                  v-if="item.acknowledged"
                  :title="item.acknowledged_by ? t('acknowledgedBy', { user: item.acknowledged_by }) : t('acknowledgedInWork')"
                  class="px-1.5 py-0.2 text-[9px] font-semibold rounded bg-emerald-500/20 text-emerald-400 flex items-center gap-0.5 flex-shrink-0"
                >
                  <span class="material-symbols-outlined text-[10px]">done_all</span>
                  Ack
                </span>
              </div>
              <p class="text-xs text-on-surface-variant leading-snug line-clamp-2">{{ t(item.message) }}</p>
            </div>

            <!-- Time and Action Buttons Column -->
            <div class="flex flex-col items-end gap-1 flex-shrink-0 min-w-[70px]">
              <span class="text-[10px] text-on-surface-variant/70 font-mono whitespace-nowrap">
                {{ formatTime(item.created_at) }}
              </span>
              <div class="flex items-center gap-0.5">
                <button
                  @click.stop="handleToggleRead(item)"
                  :title="item.read ? t('markAsUnread') : t('markAsRead')"
                  class="p-1 hover:text-primary hover:bg-primary/10 rounded-md transition-all text-on-surface-variant/70 flex items-center justify-center opacity-70 group-hover:opacity-100"
                >
                  <span class="material-symbols-outlined text-[16px]">{{ item.read ? 'mark_email_unread' : 'mark_email_read' }}</span>
                </button>
                <button
                  v-if="!item.acknowledged && (item.type === 'error' || item.type === 'warning')"
                  @click.stop="handleAck(item)"
                  :title="t('acknowledgeAction')"
                  class="p-1 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-md transition-all text-on-surface-variant/70 flex items-center justify-center"
                >
                  <span class="material-symbols-outlined text-[16px]">check_box</span>
                </button>
                <button
                  @click.stop="handleDelete(item.id)"
                  :title="t('delete')"
                  class="opacity-0 group-hover:opacity-100 p-1 hover:text-error hover:bg-error/10 rounded-md transition-all text-on-surface-variant flex items-center justify-center"
                >
                  <span class="material-symbols-outlined text-[16px]">close</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Modal for External Alerting Settings (Telegram, Discord, Viber, Webhooks) -->
    <AlertingSettingsModal
      :show="showIntegrationsModal"
      @close="showIntegrationsModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/core/i18n'
import AlertingSettingsModal from './AlertingSettingsModal.vue'
import {
  apiFetchNotifications,
  apiFetchUnreadCount,
  apiMarkNotificationRead,
  apiMarkNotificationUnread,
  apiMarkAllNotificationsRead,
  apiAcknowledgeNotification,
  apiDeleteNotification,
  apiClearNotifications,
  type NotificationItem
} from '@/core/api'
import { useWebSocket } from '@/composables/useWebSocket'
import { getStoredUser } from '@/core/auth'

const { t } = useI18n()
const router = useRouter()
const containerRef = ref<HTMLElement | null>(null)

type TabType = 'all' | 'unread' | 'system' | 'errors'

const isOpen = ref(false)
const showIntegrationsModal = ref(false)
const notifications = ref<NotificationItem[]>([])
const unreadCount = ref(0)
const activeTab = ref<TabType>('all')

const soundEnabled = ref(typeof window !== 'undefined' ? localStorage.getItem('nms_notif_sound') !== 'false' : true)
const pushEnabled = ref(typeof window !== 'undefined' ? localStorage.getItem('nms_notif_push') !== 'false' : true)
const dndEnabled = ref(typeof window !== 'undefined' ? localStorage.getItem('nms_notif_dnd') === 'true' : false)

function toggleSound() {
  soundEnabled.value = !soundEnabled.value
  if (typeof window !== 'undefined') {
    localStorage.setItem('nms_notif_sound', String(soundEnabled.value))
  }
}

function togglePush() {
  pushEnabled.value = !pushEnabled.value
  if (typeof window !== 'undefined') {
    localStorage.setItem('nms_notif_push', String(pushEnabled.value))
    if (pushEnabled.value && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {})
    }
  }
}

function toggleDnd() {
  dndEnabled.value = !dndEnabled.value
  if (typeof window !== 'undefined') {
    localStorage.setItem('nms_notif_dnd', String(dndEnabled.value))
  }
}

const searchQuery = ref('')
let searchTimeout: any = null

const tabs = computed<{ id: TabType; label: string }[]>(() => [
  { id: 'all', label: t('filterAll') },
  { id: 'unread', label: t('filterUnread') },
  { id: 'system', label: t('filterSystem') },
  { id: 'errors', label: t('filterErrors') },
])

const filteredNotifications = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return notifications.value.filter((n) => {
    if (activeTab.value === 'unread' && n.read) return false
    if (activeTab.value === 'system' && n.category !== 'system') return false
    if (activeTab.value === 'errors' && n.type !== 'error') return false
    
    if (query) {
      const titleMatch = n.title?.toLowerCase().includes(query)
      const msgMatch = n.message?.toLowerCase().includes(query)
      return titleMatch || msgMatch
    }
    return true
  })
})

watch(searchQuery, (newQuery) => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    if (newQuery.trim().length >= 2) {
      try {
        const results = await apiFetchNotifications(false, 50, newQuery.trim())
        // Объединяем полученные результаты с имеющимся списком без дубликатов
        const existingIds = new Set(notifications.value.map((n) => n.id))
        for (const item of results) {
          if (!existingIds.has(item.id)) {
            notifications.value.push(item)
          }
        }
      } catch {}
    }
  }, 300)
})

function playAlarmSound(type: string = 'warning') {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    
    // Частота зависит от критичности
    const freq = type === 'error' ? 987 : (type === 'warning' ? 659 : 523)
    const duration = type === 'error' ? 0.4 : 0.25

    osc.type = type === 'error' ? 'sawtooth' : 'sine'
    osc.frequency.setValueAtTime(freq, ctx.currentTime)
    if (type === 'error') {
      osc.frequency.setValueAtTime(1318, ctx.currentTime + 0.15)
    }
    gain.gain.setValueAtTime(0.08, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration)

    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + duration)
  } catch {}
}

function sendBrowserNotification(title: string, body: string) {
  if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
    try {
      new Notification(title, { body })
    } catch {}
  }
}

let lastSoundTime = 0
let soundThrottleTimeout: any = null
let pendingSoundSeverity: string | null = null

function playAlarmSoundThrottled(type: string = 'warning') {
  const severityRank: Record<string, number> = { error: 3, warning: 2, info: 1, resolved: 0, success: 0 }
  const newRank = severityRank[type] || 1
  const currentRank = pendingSoundSeverity ? (severityRank[pendingSoundSeverity] || 0) : 0

  if (newRank > currentRank) {
    pendingSoundSeverity = type
  }

  const now = Date.now()
  const elapsed = now - lastSoundTime

  if (elapsed >= 1500 && !soundThrottleTimeout) {
    lastSoundTime = now
    const soundToPlay = pendingSoundSeverity || type
    pendingSoundSeverity = null
    playAlarmSound(soundToPlay)
  } else if (!soundThrottleTimeout) {
    const remaining = Math.max(100, 1500 - elapsed)
    soundThrottleTimeout = setTimeout(() => {
      soundThrottleTimeout = null
      lastSoundTime = Date.now()
      const soundToPlay = pendingSoundSeverity || 'warning'
      pendingSoundSeverity = null
      playAlarmSound(soundToPlay)
    }, remaining)
  }
}

const { lastEvent } = useWebSocket()

watch(lastEvent, (event) => {
  if (event && event.type === 'ws_reconnected') {
    // Авто-дотягивание дельты при восстановлении связи
    loadData()
    return
  }

  if (event && event.type === 'notification_resolved') {
    const notifId = (event as any).notification_id
    const target = notifications.value.find((n) => n.id === notifId)
    if (target) {
      target.status = 'resolved'
      target.type = 'resolved'
      target.read = true
    }
    return
  }

  if (event && (event.type === 'notification_created' || event.type === 'notification_updated') && event.notification) {
    const newNotif = event.notification as NotificationItem
    const currentUser = getStoredUser()
    
    // Изоляция WebSocket: игнорируем чужие адресные уведомления
    if (newNotif.user_id && currentUser?.id && String(newNotif.user_id) !== String(currentUser.id)) {
      return
    }

    const existingIdx = notifications.value.findIndex((n) => n.id === newNotif.id)
    if (existingIdx !== -1) {
      notifications.value[existingIdx] = newNotif
    } else {
      notifications.value.unshift(newNotif)
      if (!newNotif.read) {
        unreadCount.value++
      }
    }

    if (event.type === 'notification_created' && !dndEnabled.value) {
      if (soundEnabled.value && (newNotif.type === 'error' || newNotif.type === 'warning' || newNotif.type === 'info')) {
        playAlarmSoundThrottled(newNotif.type)
      }

      if (pushEnabled.value && document.hidden && (newNotif as any).is_push === true) {
        sendBrowserNotification(newNotif.title, newNotif.message)
      }
    }
  }
})

async function handleAck(item: NotificationItem) {
  item.acknowledged = true
  try {
    const updated = await apiAcknowledgeNotification(item.id)
    if (updated) {
      Object.assign(item, updated)
    }
  } catch (err) {
    // Fail gracefully
  }
}

async function loadData() {
  try {
    const [list, countRes] = await Promise.all([
      apiFetchNotifications(false, 50),
      apiFetchUnreadCount(),
    ])
    notifications.value = list
    unreadCount.value = countRes.count
  } catch (err) {
    // Fail silently
  }
}

function toggleOpen() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    loadData()
  }
}

async function handleMarkAllRead() {
  try {
    await apiMarkAllNotificationsRead()
    notifications.value.forEach((n) => (n.read = true))
    unreadCount.value = 0
  } catch {}
}

async function handleClearAll() {
  try {
    await apiClearNotifications()
    notifications.value = []
    unreadCount.value = 0
  } catch {}
}

async function handleToggleRead(item: NotificationItem) {
  try {
    if (item.read) {
      item.read = false
      unreadCount.value++
      await apiMarkNotificationUnread(item.id)
    } else {
      item.read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
      await apiMarkNotificationRead(item.id)
    }
  } catch (e) {
    console.error('Failed to toggle read state', e)
  }
}

async function handleItemClick(item: NotificationItem) {
  if (!item.read) {
    item.read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    try {
      await apiMarkNotificationRead(item.id)
    } catch {}
  }
  if (item.link) {
    isOpen.value = false
    router.push(item.link)
  }
}

async function handleDelete(id: number) {
  const target = notifications.value.find((n) => n.id === id)
  if (target && !target.read) {
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }
  notifications.value = notifications.value.filter((n) => n.id !== id)
  try {
    await apiDeleteNotification(id)
  } catch {}
}

function getTypeIconName(type: string) {
  switch (type) {
    case 'resolved':
      return 'task_alt'
    case 'success':
      return 'check_circle'
    case 'warning':
      return 'warning'
    case 'error':
      return 'error'
    default:
      return 'info'
  }
}

function getTypeIconBg(type: string) {
  switch (type) {
    case 'resolved':
      return 'bg-teal-500/15 text-teal-400'
    case 'success':
      return 'bg-emerald-500/15 text-emerald-400'
    case 'warning':
      return 'bg-amber-500/15 text-amber-400'
    case 'error':
      return 'bg-rose-500/15 text-rose-400'
    default:
      return 'bg-primary/15 text-primary'
  }
}

function formatTime(timestampStr: string) {
  if (!timestampStr) return t('notificationJustNow')
  let str = timestampStr.trim().replace(' ', 'T')
  if (!str.endsWith('Z') && !str.includes('+')) {
    str += 'Z'
  }
  const date = new Date(str)
  const now = new Date()
  const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (isNaN(diffSec) || diffSec < 60) return t('notificationJustNow')
  if (diffSec < 3600) return t('notifTimeMinShort', { count: Math.floor(diffSec / 60) })
  if (diffSec < 86400) return t('notifTimeHourShort', { count: Math.floor(diffSec / 3600) })
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function handleClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  loadData()
  document.addEventListener('click', handleClickOutside)
  if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {})
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
