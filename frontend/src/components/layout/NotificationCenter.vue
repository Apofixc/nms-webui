<template>
  <div class="relative" ref="containerRef">
    <!-- Иконка колокольчика со счетчиком -->
    <button
      @click="toggleDropdown"
      class="relative p-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-colors rounded-lg flex items-center justify-center cursor-pointer"
      :title="t('notificationsTitle') || 'Уведомления'"
    >
      <span class="material-symbols-outlined text-[22px]">notifications</span>
      
      <!-- Пульсирующий индикатор / счетчик -->
      <span
        v-if="unreadCount > 0"
        class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 bg-error text-on-error font-bold text-[10px] rounded-full flex items-center justify-center leading-none shadow-sm animate-pulse"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- Выпадающее окно уведомлений -->
    <div
      v-if="isOpen"
      class="absolute right-0 mt-2 w-80 sm:w-96 bg-surface-container-high border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden flex flex-col max-h-[480px] animate-in fade-in zoom-in-95 duration-150"
    >
      <!-- Шапка поповера -->
      <div class="px-4 py-3 border-b border-outline-variant flex items-center justify-between bg-surface-dim/40">
        <div class="flex items-center gap-2">
          <span class="font-bold text-sm text-on-surface">{{ t('notifications') || 'Уведомления' }}</span>
          <span v-if="unreadCount > 0" class="px-2 py-0.5 bg-primary/20 text-primary text-xs font-semibold rounded-full">
            {{ unreadCount }} {{ t('unread') || 'непрочитанных' }}
          </span>
        </div>

        <div class="flex items-center gap-1">
          <button
            v-if="unreadCount > 0"
            @click="markAllRead"
            class="text-xs text-primary hover:underline px-2 py-1 rounded transition-colors hover:bg-primary/10"
            :title="t('markAllRead') || 'Прочитать все'"
          >
            {{ t('markAllRead') || 'Прочитать все' }}
          </button>
          <button
            @click="clearRead"
            class="p-1 text-on-surface-variant hover:text-error hover:bg-error/10 rounded transition-colors"
            :title="t('clearRead') || 'Очистить прочитанные'"
          >
            <span class="material-symbols-outlined text-[18px]">delete_sweep</span>
          </button>
        </div>
      </div>

      <!-- Вкладки фильтрации -->
      <div class="flex border-b border-outline-variant text-xs font-semibold bg-surface/50">
        <button
          @click="filterUnread = false"
          :class="[
            'flex-1 py-2 text-center transition-colors border-b-2',
            !filterUnread ? 'border-primary text-primary font-bold bg-surface-variant/30' : 'border-transparent text-on-surface-variant hover:text-on-surface'
          ]"
        >
          {{ t('all') || 'Все' }}
        </button>
        <button
          @click="filterUnread = true"
          :class="[
            'flex-1 py-2 text-center transition-colors border-b-2',
            filterUnread ? 'border-primary text-primary font-bold bg-surface-variant/30' : 'border-transparent text-on-surface-variant hover:text-on-surface'
          ]"
        >
          {{ t('unreadOnly') || 'Непрочитанные' }} ({{ unreadCount }})
        </button>
      </div>

      <!-- Список уведомлений -->
      <div class="flex-1 overflow-y-auto divide-y divide-outline-variant/40 custom-scrollbar">
        <div v-if="loading" class="p-6 text-center text-on-surface-variant text-xs">
          <span class="material-symbols-outlined animate-spin text-lg mb-1">progress_activity</span>
          <p>{{ t('loading') || 'Загрузка...' }}</p>
        </div>

        <div v-else-if="filteredItems.length === 0" class="p-8 text-center text-on-surface-variant text-xs">
          <span class="material-symbols-outlined text-3xl opacity-40 mb-1">notifications_off</span>
          <p>{{ t('noNotifications') || 'Нет уведомлений' }}</p>
        </div>

        <div
          v-else
          v-for="item in filteredItems"
          :key="item.id"
          @click="handleItemClick(item)"
          :class="[
            'p-3 flex items-start gap-3 transition-colors cursor-pointer group hover:bg-surface-variant/40',
            !item.read_at ? 'bg-primary/5' : 'opacity-75'
          ]"
        >
          <!-- Иконка по severity -->
          <div :class="['mt-0.5 w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-sm', getSeverityClass(item.severity)]">
            <span class="material-symbols-outlined text-[18px]">{{ getSeverityIcon(item.severity) }}</span>
          </div>

          <!-- Контент -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between gap-2">
              <h4 class="text-xs font-bold text-on-surface truncate">{{ item.title }}</h4>
              <span class="text-[10px] text-on-surface-variant/70 flex-shrink-0 font-mono">
                {{ formatTime(item.created_at) }}
              </span>
            </div>
            <p v-if="item.body" class="text-xs text-on-surface-variant mt-0.5 line-clamp-2 leading-relaxed">
              {{ item.body }}
            </p>
            <div class="flex items-center gap-2 mt-1">
              <span v-if="item.module_id && item.module_id !== 'core'" class="text-[9px] px-1.5 py-0.2 bg-surface-variant/60 text-on-surface-variant rounded font-mono">
                {{ item.module_id }}
              </span>
            </div>
          </div>

          <!-- Действия одной строкой -->
          <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
            <button
              v-if="!item.read_at"
              @click.stop="markOneRead(item.id)"
              class="p-1 text-primary hover:bg-primary/20 rounded transition-colors"
              :title="t('markRead') || 'Прочитано'"
            >
              <span class="material-symbols-outlined text-[16px]">done</span>
            </button>
            <button
              @click.stop="removeOne(item.id)"
              class="p-1 text-on-surface-variant hover:text-error hover:bg-error/10 rounded transition-colors"
              :title="t('delete') || 'Удалить'"
            >
              <span class="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useI18n } from '@/core/i18n'
import { useWebSocket } from '@/composables/useWebSocket'
import {
  apiFetchNotifications,
  apiMarkNotificationRead,
  apiMarkAllNotificationsRead,
  apiDeleteNotification,
  apiClearReadNotifications,
} from '@/core/api'

interface NotificationItem {
  id: number
  module_id: string
  user_id: string
  title: string
  body: string
  severity: string
  entity_id?: string | null
  created_at: number
  read_at?: number | null
}


const { t } = useI18n()
const { lastEvent } = useWebSocket()

const isOpen = ref(false)
const loading = ref(false)
const filterUnread = ref(false)
const containerRef = ref<HTMLElement | null>(null)

const items = ref<NotificationItem[]>([])
const unreadCount = ref(0)

const filteredItems = computed(() => {
  if (filterUnread.value) {
    return items.value.filter((i) => !i.read_at)
  }
  return items.value
})

async function fetchNotifications() {
  loading.value = true
  try {
    const data = await apiFetchNotifications({ limit: 50 })
    items.value = data.items || []
    unreadCount.value = data.unread_count || 0
  } catch (err) {
    console.error('Failed to fetch notifications:', err)
  } finally {
    loading.value = false
  }
}

function toggleDropdown() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    fetchNotifications()
  }
}

function handleClickOutside(event: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

async function markOneRead(id: number) {
  try {
    await apiMarkNotificationRead(id)
    const item = items.value.find((i) => i.id === id)
    if (item && !item.read_at) {
      item.read_at = Date.now() / 1000
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  } catch (err) {
    console.error('Failed to mark read:', err)
  }
}

async function markAllRead() {
  try {
    await apiMarkAllNotificationsRead()
    const now = Date.now() / 1000
    items.value.forEach((i) => {
      if (!i.read_at) i.read_at = now
    })
    unreadCount.value = 0
  } catch (err) {
    console.error('Failed to mark all read:', err)
  }
}

async function removeOne(id: number) {
  try {
    await apiDeleteNotification(id)
    const idx = items.value.findIndex((i) => i.id === id)
    if (idx !== -1) {
      if (!items.value[idx].read_at) {
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      }
      items.value.splice(idx, 1)
    }
  } catch (err) {
    console.error('Failed to delete notification:', err)
  }
}

async function clearRead() {
  try {
    await apiClearReadNotifications()
    items.value = items.value.filter((i) => !i.read_at)
  } catch (err) {
    console.error('Failed to clear read notifications:', err)
  }
}

function handleItemClick(item: NotificationItem) {
  if (!item.read_at) {
    markOneRead(item.id)
  }
}

function getSeverityIcon(severity: string) {
  switch (severity?.toLowerCase()) {
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

function getSeverityClass(severity: string) {
  switch (severity?.toLowerCase()) {
    case 'success':
      return 'bg-success/20 text-success'
    case 'warning':
      return 'bg-warning/20 text-warning'
    case 'error':
      return 'bg-error/20 text-error'
    default:
      return 'bg-primary/20 text-primary'
  }
}

function formatTime(timestamp: number) {
  if (!timestamp) return ''
  const diffSec = Math.floor(Date.now() / 1000 - timestamp)
  if (diffSec < 60) return t('justNow') || 'только что'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} м`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} ч`
  return `${Math.floor(diffSec / 86400)} д`
}

// Live WS обновления
watch(lastEvent, (evt) => {
  if (evt && evt.type === 'notification' && evt.data) {
    const newItem: NotificationItem = evt.data
    const exists = items.value.some((i) => i.id === newItem.id)
    if (!exists) {
      items.value.unshift(newItem)
      if (typeof evt.unread_count === 'number') {
        unreadCount.value = evt.unread_count
      } else {
        unreadCount.value++
      }
    }
  }
})

onMounted(() => {
  fetchNotifications()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(150, 150, 150, 0.3);
  border-radius: 4px;
}
</style>
