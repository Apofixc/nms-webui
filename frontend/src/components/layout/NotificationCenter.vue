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
        class="absolute right-0 mt-2 w-80 sm:w-96 bg-surface-dim/95 backdrop-blur-md border border-outline-variant rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col text-on-surface"
      >
        <!-- Header -->
        <div class="p-4 border-b border-outline-variant flex items-center justify-between bg-surface-variant/20">
          <div class="flex items-center gap-2">
            <h3 class="font-bold text-sm text-on-surface">{{ t('notificationsTitle') }}</h3>
            <span v-if="unreadCount > 0" class="px-2 py-0.5 rounded-full bg-primary/20 text-primary font-mono text-xs font-semibold">
              {{ unreadCount }}
            </span>
          </div>

          <div class="flex items-center gap-2 text-xs">
            <button
              v-if="unreadCount > 0"
              @click="handleMarkAllRead"
              class="text-primary hover:underline font-medium transition-colors"
            >
              {{ t('notificationsMarkAllRead') }}
            </button>
            <span v-if="unreadCount > 0 && notifications.length > 0" class="text-outline">|</span>
            <button
              v-if="notifications.length > 0"
              @click="handleClearAll"
              class="text-on-surface-variant hover:text-error transition-colors"
            >
              {{ t('notificationsClearAll') }}
            </button>
          </div>
        </div>

        <!-- Filter Tabs -->
        <div class="px-3 py-2 border-b border-outline-variant flex items-center gap-1 overflow-x-auto text-xs bg-surface-variant/10">
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
        <div class="max-h-[380px] overflow-y-auto divide-y divide-outline-variant/30">
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
              'p-3.5 flex items-start gap-3 transition-colors group relative cursor-pointer',
              item.read ? 'opacity-75 hover:bg-surface-variant/20' : 'bg-primary/5 hover:bg-primary/10'
            ]"
          >
            <!-- Status Dot for Unread -->
            <span
              v-if="!item.read"
              class="w-2 h-2 rounded-full bg-primary absolute top-4 left-2 flex-shrink-0"
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
            <div class="flex-1 min-w-0 pr-6">
              <div class="flex items-center justify-between gap-1 mb-0.5">
                <h4 class="text-xs font-bold text-on-surface truncate">{{ item.title }}</h4>
                <span class="text-[10px] text-on-surface-variant/70 font-mono flex-shrink-0">
                  {{ formatTime(item.created_at) }}
                </span>
              </div>
              <p class="text-xs text-on-surface-variant leading-snug line-clamp-2">{{ item.message }}</p>
            </div>

            <!-- Delete Button on Hover -->
            <button
              @click.stop="handleDelete(item.id)"
              title="Удалить"
              class="opacity-0 group-hover:opacity-100 p-1 hover:text-error hover:bg-error/10 rounded-md transition-all absolute top-3 right-3 text-on-surface-variant"
            >
              <span class="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/core/i18n'
import {
  apiFetchNotifications,
  apiFetchUnreadCount,
  apiMarkNotificationRead,
  apiMarkAllNotificationsRead,
  apiDeleteNotification,
  apiClearNotifications,
  type NotificationItem
} from '@/core/api'
import { useWebSocket } from '@/composables/useWebSocket'

const { t } = useI18n()
const router = useRouter()
const containerRef = ref<HTMLElement | null>(null)

type TabType = 'all' | 'unread' | 'system' | 'errors'

const isOpen = ref(false)
const notifications = ref<NotificationItem[]>([])
const unreadCount = ref(0)
const activeTab = ref<TabType>('all')

const tabs = computed<{ id: TabType; label: string }[]>(() => [
  { id: 'all', label: t('filterAll') },
  { id: 'unread', label: t('filterUnread') },
  { id: 'system', label: t('filterSystem') },
  { id: 'errors', label: t('filterErrors') },
])

const filteredNotifications = computed(() => {
  return notifications.value.filter((n) => {
    if (activeTab.value === 'unread') return !n.read
    if (activeTab.value === 'system') return n.category === 'system'
    if (activeTab.value === 'errors') return n.type === 'error'
    return true
  })
})

const { lastEvent } = useWebSocket()

watch(lastEvent, (event) => {
  if (event && event.type === 'notification_created' && event.notification) {
    const newNotif = event.notification as NotificationItem
    notifications.value.unshift(newNotif)
    if (!newNotif.read) {
      unreadCount.value++
    }
  }
})

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
  const date = new Date(timestampStr.replace(' ', 'T'))
  const now = new Date()
  const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (isNaN(diffSec) || diffSec < 60) return t('notificationJustNow')
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} м`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} ч`
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
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
