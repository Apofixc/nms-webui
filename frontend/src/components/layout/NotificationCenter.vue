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
          <!-- Звук переключатель -->
          <button
            type="button"
            @click="toggleSound(!notifSoundEnabled)"
            :class="[
              'p-1 rounded transition-colors flex items-center justify-center cursor-pointer',
              notifSoundEnabled ? 'text-primary hover:bg-primary/10' : 'text-on-surface-variant/40 hover:bg-surface-variant/50'
            ]"
            :title="notifSoundEnabled ? (t('soundNotifications') || 'Звуковые уведомления включены') : (t('soundNotificationsSub') || 'Звуковые уведомления выключены')"
          >
            <span class="material-symbols-outlined text-[18px]">
              {{ notifSoundEnabled ? 'volume_up' : 'volume_off' }}
            </span>
          </button>

          <!-- Push переключатель -->
          <button
            type="button"
            @click="togglePush(!notifPushEnabled)"
            :class="[
              'p-1 rounded transition-colors flex items-center justify-center cursor-pointer relative',
              isPushPermissionDenied
                ? 'text-amber-400 hover:bg-amber-500/10'
                : notifPushEnabled
                ? 'text-primary hover:bg-primary/10'
                : 'text-on-surface-variant/40 hover:bg-surface-variant/50'
            ]"
            :title="
              isPushPermissionDenied
                ? (t('pushPermissionDenied') || 'Внимание: Push-уведомления заблокированы в настройках вашго браузера')
                : notifPushEnabled
                ? (t('pushNotifications') || 'Push-уведомления включены')
                : (t('pushNotificationsSub') || 'Push-уведомления выключены')
            "
          >
            <span class="material-symbols-outlined text-[18px]">
              {{ isPushPermissionDenied ? 'notifications_off' : (notifPushEnabled ? 'notifications_active' : 'notifications_off') }}
            </span>
            <span
              v-if="isPushPermissionDenied"
              class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-amber-500 rounded-full animate-ping"
            ></span>
            <span
              v-if="isPushPermissionDenied"
              class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-amber-500 rounded-full"
            ></span>
          </button>

          <!-- Snooze / Временное отключение кнопка -->
          <div class="relative">
            <button
              type="button"
              @click="isSnoozeMenuOpen = !isSnoozeMenuOpen"
              :class="[
                'p-1 rounded transition-colors flex items-center justify-center cursor-pointer',
                isGlobalMuted() ? 'text-warning bg-warning/10 animate-pulse' : 'text-on-surface-variant/40 hover:bg-surface-variant/50'
              ]"
              :title="isGlobalMuted() ? `${t('tempMuteActive')} ${formatMuteTime(notifMutedUntil)}` : (t('tempMuteTitle') || 'Временное отключение')"
            >
              <span class="material-symbols-outlined text-[18px]">
                {{ isGlobalMuted() ? 'notifications_paused' : 'do_not_disturb_on' }}
              </span>
            </button>

            <!-- Выпадающее меню временного отключения -->
            <div
              v-if="isSnoozeMenuOpen"
              class="absolute right-0 mt-1 w-44 bg-surface-container-highest border border-outline-variant rounded-lg shadow-lg z-50 py-1 text-xs"
            >
              <div class="px-3 py-1 text-[10px] font-bold text-on-surface-variant uppercase border-b border-outline-variant/40">
                {{ t('tempMuteGlobal') }}
              </div>
              <button
                @click="snoozeGlobal(900)"
                class="w-full text-left px-3 py-1.5 hover:bg-primary/10 hover:text-primary transition-colors flex items-center justify-between"
              >
                <span>{{ t('mute15m') }}</span>
              </button>
              <button
                @click="snoozeGlobal(3600)"
                class="w-full text-left px-3 py-1.5 hover:bg-primary/10 hover:text-primary transition-colors flex items-center justify-between"
              >
                <span>{{ t('mute1h') }}</span>
              </button>
              <button
                @click="snoozeGlobal(28800)"
                class="w-full text-left px-3 py-1.5 hover:bg-primary/10 hover:text-primary transition-colors flex items-center justify-between"
              >
                <span>{{ t('mute8h') }}</span>
              </button>
              <button
                @click="snoozeGlobal(86400)"
                class="w-full text-left px-3 py-1.5 hover:bg-primary/10 hover:text-primary transition-colors flex items-center justify-between"
              >
                <span>{{ t('mute24h') }}</span>
              </button>
              <button
                @click="snoozeGlobal(-1)"
                class="w-full text-left px-3 py-1.5 hover:bg-primary/10 hover:text-primary font-semibold transition-colors flex items-center gap-1 text-warning"
              >
                <span class="material-symbols-outlined text-[14px]">pause_circle</span>
                <span>{{ t('muteIndefinitely') }}</span>
              </button>
              <div v-if="isGlobalMuted()" class="border-t border-outline-variant/40 mt-1 pt-1">
                <button
                  @click="snoozeGlobal(null)"
                  class="w-full text-left px-3 py-1.5 text-primary font-semibold hover:bg-primary/10 transition-colors flex items-center gap-1"
                >
                  <span class="material-symbols-outlined text-[14px]">notifications_active</span>
                  <span>{{ t('unmute') }}</span>
                </button>
              </div>
            </div>

          </div>

          <div class="w-px h-4 bg-outline-variant/60 mx-0.5"></div>

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
            class="p-1 text-on-surface-variant hover:text-error hover:bg-error/10 rounded transition-colors cursor-pointer"
            :title="t('clearRead') || 'Очистить прочитанные'"
          >
            <span class="material-symbols-outlined text-[18px]">delete_sweep</span>
          </button>
        </div>
      </div>

      <!-- Предупреждение об активном режиме Не беспокоить -->
      <div v-if="isGlobalMuted()" class="px-3 py-1.5 bg-warning/15 border-b border-warning/30 text-warning text-[11px] font-semibold flex items-center justify-between">
        <div class="flex items-center gap-1.5">
          <span class="material-symbols-outlined text-sm">notifications_paused</span>
          <span>{{ t('tempMuteActive') }} {{ formatMuteTime(notifMutedUntil) }}</span>
        </div>
        <button @click="snoozeGlobal(null)" class="text-xs underline hover:opacity-80 cursor-pointer">
          {{ t('unmute') }}
        </button>
      </div>


      <!-- Предупреждение о блокировке Push в браузере -->
      <div v-if="pushBlockedWarning" class="px-3 py-2 bg-amber-500/10 border-b border-amber-500/30 text-amber-300 text-[11px] leading-snug flex items-center gap-2">
        <span class="material-symbols-outlined text-sm flex-shrink-0">warning</span>
        <span class="flex-1">{{ t('pushPermissionDenied') || 'Push-уведомления заблокированы в браузере' }}</span>
        <button @click="pushBlockedWarning = false" class="text-amber-300 hover:text-white cursor-pointer">
          <span class="material-symbols-outlined text-xs">close</span>
        </button>
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

      <!-- Поиск и чипсы фильтрации -->
      <div class="px-3 py-2 border-b border-outline-variant/50 bg-surface-dim/30 flex flex-col gap-2">
        <!-- Поисковое поле -->
        <div class="relative flex items-center bg-surface-container-low border border-outline-variant/60 focus-within:border-primary/80 focus-within:ring-1 focus-within:ring-primary/20 rounded-lg px-2.5 py-1 transition-all">
          <span class="material-symbols-outlined text-[17px] text-on-surface-variant/60 flex-shrink-0 mr-1.5 select-none">search</span>
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('searchNotificationsPlaceholder') || 'Поиск по уведомлениям...'"
            class="w-full bg-transparent text-xs text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="text-on-surface-variant/50 hover:text-on-surface cursor-pointer p-0.5 ml-1 transition-colors rounded-full hover:bg-surface-variant/50 flex items-center justify-center"
            :title="t('clearSearch') || 'Очистить поиск'"
          >
            <span class="material-symbols-outlined text-[14px]">close</span>
          </button>
        </div>

        <!-- Компактные чипсы фильтрации -->
        <div class="flex flex-wrap items-center gap-1 py-0.5 text-[11px] font-medium">
          <button
            @click="selectedSeverity = ''"
            :class="[
              'px-2 py-0.5 rounded-full transition-all cursor-pointer whitespace-nowrap border',
              !selectedSeverity
                ? 'bg-primary/20 text-primary border-primary/40 font-bold shadow-xs'
                : 'bg-surface-variant/30 text-on-surface-variant/80 border-transparent hover:bg-surface-variant/60 hover:text-on-surface'
            ]"
          >
            {{ t('all') || 'Все' }}
          </button>
          <button
            @click="selectedSeverity = selectedSeverity === 'error' ? '' : 'error'"
            :class="[
              'px-2 py-0.5 rounded-full transition-all flex items-center gap-1 cursor-pointer whitespace-nowrap border',
              selectedSeverity === 'error'
                ? 'bg-error/20 text-error border-error/40 font-bold shadow-xs'
                : 'bg-surface-variant/30 text-on-surface-variant/80 border-transparent hover:bg-error/15 hover:text-error'
            ]"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-error flex-shrink-0"></span>
            <span>{{ t('filterErrors') || 'Ошибки' }}</span>
          </button>
          <button
            @click="selectedSeverity = selectedSeverity === 'warning' ? '' : 'warning'"
            :class="[
              'px-2 py-0.5 rounded-full transition-all flex items-center gap-1 cursor-pointer whitespace-nowrap border',
              selectedSeverity === 'warning'
                ? 'bg-warning/20 text-warning border-warning/40 font-bold shadow-xs'
                : 'bg-surface-variant/30 text-on-surface-variant/80 border-transparent hover:bg-warning/15 hover:text-warning'
            ]"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-warning flex-shrink-0"></span>
            <span>{{ t('filterWarnings') || 'Предупреждения' }}</span>
          </button>
          <button
            @click="selectedSeverity = selectedSeverity === 'info' ? '' : 'info'"
            :class="[
              'px-2 py-0.5 rounded-full transition-all flex items-center gap-1 cursor-pointer whitespace-nowrap border',
              selectedSeverity === 'info'
                ? 'bg-info/20 text-info border-info/40 font-bold shadow-xs'
                : 'bg-surface-variant/30 text-on-surface-variant/80 border-transparent hover:bg-info/15 hover:text-info'
            ]"
          >
            <span>{{ t('filterInfo') || 'Инфо' }}</span>
          </button>
          <button
            @click="selectedSeverity = selectedSeverity === 'success' ? '' : 'success'"
            :class="[
              'px-2 py-0.5 rounded-full transition-all flex items-center gap-1 cursor-pointer whitespace-nowrap border',
              selectedSeverity === 'success'
                ? 'bg-success/20 text-success border-success/40 font-bold shadow-xs'
                : 'bg-surface-variant/30 text-on-surface-variant/80 border-transparent hover:bg-success/15 hover:text-success'
            ]"
          >
            <span>{{ t('filterSuccess') || 'Успех' }}</span>
          </button>
        </div>
      </div>

        <!-- Список уведомлений -->
        <div class="flex-1 overflow-y-auto divide-y divide-outline-variant/40 custom-scrollbar">
          <div v-if="loading && items.length === 0" class="p-6 text-center text-on-surface-variant text-xs">
            <span class="material-symbols-outlined animate-spin text-lg mb-1">progress_activity</span>
            <p>{{ t('loading') || 'Загрузка...' }}</p>
          </div>

          <div v-else-if="filteredItems.length === 0" class="p-8 text-center text-on-surface-variant text-xs">
            <span class="material-symbols-outlined text-3xl opacity-40 mb-1">notifications_off</span>
            <p>{{ t('noNotifications') || 'Нет уведомлений' }}</p>
          </div>

          <template v-else>
            <div
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
                  <div class="flex items-center gap-1.5 min-w-0">
                    <h4 class="text-xs font-bold text-on-surface truncate">{{ item.title }}</h4>
                    <span
                      v-if="item.group_count && item.group_count > 1"
                      class="px-1.5 py-0.2 bg-primary/20 text-primary text-[10px] font-extrabold rounded-full flex-shrink-0"
                      :title="`Повторилось ${item.group_count} раз`"
                    >
                      ×{{ item.group_count }}
                    </span>
                  </div>
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
                  <span v-if="item.target_url || item.entity_id" class="text-[9px] text-primary flex items-center gap-0.5 font-medium">
                    <span class="material-symbols-outlined text-[12px]">open_in_new</span>
                    <span>{{ t('openDetails') || 'Открыть' }}</span>
                  </span>
                </div>
              </div>

              <!-- Действия одной строкой -->
              <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                <button
                  v-if="item.module_id && item.module_id !== 'core'"
                  @click.stop="snoozeModule(item.module_id, isModuleMuted(item.module_id) ? null : 3600)"
                  :class="[
                    'p-1 rounded transition-colors',
                    isModuleMuted(item.module_id) ? 'text-warning bg-warning/10' : 'text-on-surface-variant hover:text-warning hover:bg-warning/10'
                  ]"
                  :title="isModuleMuted(item.module_id) ? `${t('unmuteModule')} (${t('tempMuteActive')} ${formatMuteTime(getModuleMuteUntil(item.module_id))})` : `${t('snoozeModule')} (1ч)`"
                >
                  <span class="material-symbols-outlined text-[16px]">
                    {{ isModuleMuted(item.module_id) ? 'notifications_paused' : 'schedule' }}
                  </span>
                </button>
                <button
                  v-if="item.module_id && item.module_id !== 'core'"
                  @click.stop="quickUnsubscribeModule(item.module_id)"
                  class="p-1 text-on-surface-variant hover:text-warning hover:bg-warning/10 rounded transition-colors"
                  :title="t('muteModuleQuick')"
                >
                  <span class="material-symbols-outlined text-[16px]">notifications_off</span>
                </button>

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

            <!-- Подгрузка дополнительных элементов -->
            <div v-if="hasMore" class="p-2 text-center border-t border-outline-variant/30">
              <button
                @click="loadMore"
                :disabled="loadingMore"
                class="text-xs text-primary hover:underline font-semibold py-1 px-3 rounded hover:bg-primary/10 transition-colors disabled:opacity-50"
              >
                <span v-if="loadingMore" class="material-symbols-outlined animate-spin text-xs align-middle mr-1">progress_activity</span>
                {{ t('loadMore') || 'Загрузить ещё' }}
              </button>
            </div>
          </template>
        </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/core/i18n'
import { useWebSocket } from '@/composables/useWebSocket'
import { playPresetSound, unlockAudioContext, DEFAULT_SEVERITY_SOUNDS } from '@/core/audio'
import {
  apiFetchNotifications,
  apiMarkNotificationRead,
  apiMarkAllNotificationsRead,
  apiDeleteNotification,
  apiClearReadNotifications,
  apiFetchNotificationPreferences,
  apiUpdateNotificationPreferences,
  apiFetchNotificationModules,
} from '@/core/api'

interface NotificationItem {
  id: number
  module_id: string
  user_id: string
  title: string
  body: string
  severity: string
  category?: string
  entity_id?: string | null
  target_url?: string | null
  group_count?: number
  created_at: number
  read_at?: number | null
}

const router = useRouter()
const { t } = useI18n()
const { lastEvent, isLeader } = useWebSocket()

const isOpen = ref(false)
const loading = ref(false)
const loadingMore = ref(false)
const filterUnread = ref(false)
const searchQuery = ref('')
const selectedSeverity = ref('')
const selectedCategory = ref('')
const containerRef = ref<HTMLElement | null>(null)

const notifPushEnabled = ref(true)
const notifSoundEnabled = ref(true)
const notifSoundSignals = ref<Record<string, string>>({})
const notifModuleRules = ref<Record<string, { sound_signal?: string; muted_until?: number | null }>>({})
const notifMutedUntil = ref<number | null>(null)
const isSnoozeMenuOpen = ref(false)
const pushBlockedWarning = ref(false)

function isGlobalMuted(): boolean {
  if (notifMutedUntil.value === null || notifMutedUntil.value === undefined) return false
  if (notifMutedUntil.value === -1) return true
  return notifMutedUntil.value * 1000 > Date.now()
}

function getModuleMuteUntil(modId: string): number | null {
  return notifModuleRules.value[modId]?.muted_until ?? null
}

function isModuleMuted(modId: string): boolean {
  const until = getModuleMuteUntil(modId)
  if (until === null || until === undefined) return false
  if (until === -1) return true
  return until * 1000 > Date.now()
}

function formatMuteTime(ts: number | null | undefined): string {
  if (ts === null || ts === undefined) return ''
  if (ts === -1) return t('tempMuteIndefinite') || 'до включения вручную'
  const d = new Date(ts * 1000)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })
}

async function snoozeGlobal(seconds: number | null) {
  if (seconds === null) {
    notifMutedUntil.value = null
  } else if (seconds === -1) {
    notifMutedUntil.value = -1
  } else {
    notifMutedUntil.value = Math.floor(Date.now() / 1000) + seconds
  }
  isSnoozeMenuOpen.value = false
  isSavingPreferences.value = true
  try {
    await apiUpdateNotificationPreferences({
      muted_until: notifMutedUntil.value,
    })
  } catch (err) {
    console.error('Failed to update snooze preferences:', err)
  } finally {
    isSavingPreferences.value = false
  }
}

async function snoozeModule(modId: string, seconds: number | null) {
  if (!modId || modId === 'core') return
  let mUntil: number | null = null
  if (seconds === -1) {
    mUntil = -1
  } else if (seconds !== null) {
    mUntil = Math.floor(Date.now() / 1000) + seconds
  }
  const currentRules = { ...notifModuleRules.value }
  const cur = currentRules[modId] || {}
  currentRules[modId] = { ...cur, muted_until: mUntil }
  notifModuleRules.value = currentRules
  try {
    await apiUpdateNotificationPreferences({
      module_rules: currentRules,
    })
  } catch (err) {
    console.error('Failed to update module snooze:', err)
  }
}


const items = ref<NotificationItem[]>([])
const readInSessionIds = ref(new Set<number>())
const isSavingPreferences = ref(false)
const unreadCount = ref(0)
const totalCount = ref(0)
const filteredTotalCount = ref(0)
const liveCount = ref(0)
const PAGE_SIZE = 30
let fetchedFromDbCount = 0
let currentRequestId = 0

const isPushPermissionDenied = ref(false)

function checkPushPermission() {
  if (typeof window === 'undefined' || !('Notification' in window)) return
  isPushPermissionDenied.value = Notification.permission === 'denied'
  if (notifPushEnabled.value && isPushPermissionDenied.value) {
    pushBlockedWarning.value = true
  } else if (!notifPushEnabled.value || Notification.permission === 'granted') {
    pushBlockedWarning.value = false
  }
}

async function loadNotificationPreferences() {
  if (isSavingPreferences.value) return
  try {
    const prefs = await apiFetchNotificationPreferences()
    if (!isSavingPreferences.value) {
      notifPushEnabled.value = prefs.push_enabled ?? true
      notifSoundEnabled.value = prefs.sound_enabled ?? true
      notifSoundSignals.value = prefs.sound_signals || {}
      notifModuleRules.value = prefs.module_rules || {}
      notifMutedUntil.value = prefs.muted_until ?? null
      checkPushPermission()
    }
  } catch (err) {
    console.error('Failed to load notification preferences:', err)
  }
}

async function saveNotificationPreferences() {
  isSavingPreferences.value = true
  try {
    await apiUpdateNotificationPreferences({
      push_enabled: notifPushEnabled.value,
      sound_enabled: notifSoundEnabled.value,
      muted_until: notifMutedUntil.value,
    })
  } catch (err) {
    console.error('Failed to save notification preferences:', err)
  } finally {
    isSavingPreferences.value = false
  }
}

async function togglePush(val: boolean) {
  checkPushPermission()
  if (val) {
    if ('Notification' in window) {
      if (Notification.permission === 'denied') {
        isPushPermissionDenied.value = true
        pushBlockedWarning.value = true
        return
      } else if (Notification.permission === 'default') {
        const perm = await Notification.requestPermission()
        if (perm !== 'granted') {
          isPushPermissionDenied.value = perm === 'denied'
          pushBlockedWarning.value = true
          return
        }
      }
    }
    isPushPermissionDenied.value = false
    pushBlockedWarning.value = false
    notifPushEnabled.value = true
  } else {
    pushBlockedWarning.value = false
    notifPushEnabled.value = false
  }
  saveNotificationPreferences()
}

function toggleSound(val: boolean) {
  notifSoundEnabled.value = val
  if (val) {
    unlockAudioContext()
    playNotificationSound()
  }
  saveNotificationPreferences()
}


const filteredItems = computed(() => {
  if (filterUnread.value) {
    return items.value.filter((i) => !i.read_at || readInSessionIds.value.has(i.id))
  }
  return items.value
})

const hasMore = computed(() => {
  const loadedCount = filterUnread.value ? filteredItems.value.length : items.value.length
  return loadedCount < filteredTotalCount.value
})

async function fetchNotifications() {
  const requestId = ++currentRequestId
  loading.value = true
  try {
    const data = await apiFetchNotifications({
      limit: PAGE_SIZE,
      offset: 0,
      unread_only: filterUnread.value,
      severity: selectedSeverity.value || undefined,
      category: selectedCategory.value || undefined,
      search: searchQuery.value.trim() || undefined,
    })
    if (requestId !== currentRequestId) return
    items.value = data.items || []
    fetchedFromDbCount = items.value.length
    unreadCount.value = data.unread_count || 0
    totalCount.value = data.total || 0
    filteredTotalCount.value = data.filtered_total ?? (filterUnread.value ? unreadCount.value : totalCount.value)
    liveCount.value = 0
  } catch (err) {
    if (requestId === currentRequestId) {
      console.error('Failed to fetch notifications:', err)
    }
  } finally {
    if (requestId === currentRequestId) {
      loading.value = false
    }
  }
}

watch([filterUnread, selectedSeverity, selectedCategory], () => {
  fetchNotifications()
})

let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, () => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    fetchNotifications()
  }, 300)
})

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  loadingMore.value = true
  const requestId = ++currentRequestId
  try {
    const offset = fetchedFromDbCount
    const data = await apiFetchNotifications({
      limit: PAGE_SIZE,
      offset: offset,
      unread_only: filterUnread.value,
      severity: selectedSeverity.value || undefined,
      category: selectedCategory.value || undefined,
      search: searchQuery.value.trim() || undefined,
    })
    if (requestId !== currentRequestId) return
    const newItems: NotificationItem[] = data.items || []
    const existingIds = new Set(items.value.map((i) => i.id))
    let addedCount = 0
    for (const item of newItems) {
      if (!existingIds.has(item.id)) {
        items.value.push(item)
        addedCount++
      }
    }
    fetchedFromDbCount += newItems.length
    unreadCount.value = data.unread_count || 0
    totalCount.value = data.total || 0
    filteredTotalCount.value = data.filtered_total ?? (filterUnread.value ? unreadCount.value : totalCount.value)
  } catch (err) {
    if (requestId === currentRequestId) {
      console.error('Failed to load more notifications:', err)
    }
  } finally {
    if (requestId === currentRequestId) {
      loadingMore.value = false
    }
  }
}

function toggleDropdown() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    unlockAudioContext()
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
      readInSessionIds.value.add(id)
      unreadCount.value = Math.max(0, unreadCount.value - 1)
      if (filterUnread.value) {
        filteredTotalCount.value = Math.max(0, filteredTotalCount.value - 1)
      }
    }
  } catch (err) {
    console.error('Failed to mark read:', err)
  }
}

let lastMarkAllReadTime = 0

async function markAllRead() {
  const markTime = Date.now() / 1000
  lastMarkAllReadTime = markTime
  try {
    const res = await apiMarkAllNotificationsRead()
    const now = res?.marked_at || markTime
    lastMarkAllReadTime = now
    items.value.forEach((i) => {
      if (!i.read_at) i.read_at = now
    })
    unreadCount.value = 0
    if (filterUnread.value) {
      filteredTotalCount.value = 0
    }
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
      totalCount.value = Math.max(0, totalCount.value - 1)
      filteredTotalCount.value = Math.max(0, filteredTotalCount.value - 1)
      fetchedFromDbCount = Math.max(0, fetchedFromDbCount - 1)
    }
  } catch (err) {
    console.error('Failed to delete notification:', err)
  }
}

async function quickUnsubscribeModule(modId: string) {
  if (!modId || modId === 'core') return
  try {
    const prefs = await apiFetchNotificationPreferences()
    const updatedRules = { ...(prefs.module_rules || {}) }
    updatedRules[modId] = { ...(updatedRules[modId] || {}), enabled: false }
    await apiUpdateNotificationPreferences({
      module_rules: updatedRules,
    })
  } catch (err) {
    console.error('Failed to unsubscribe module:', err)
  }
}

async function clearRead() {
  const previousItems = [...items.value]
  const previousTotal = totalCount.value
  const previousFilteredTotal = filteredTotalCount.value
  
  // Оптимистичное удаление прочитанных уведомлений
  items.value = items.value.filter((i) => !i.read_at)
  totalCount.value = items.value.length
  if (!filterUnread.value) {
    filteredTotalCount.value = items.value.length
  }
  
  try {
    await apiClearReadNotifications()
    await fetchNotifications()
  } catch (err) {
    console.error('Failed to clear read notifications:', err)
    // Откат при сбое сети
    items.value = previousItems
    totalCount.value = previousTotal
    filteredTotalCount.value = previousFilteredTotal
  }
}

function handleItemClick(item: NotificationItem) {
  if (!item.read_at) {
    markOneRead(item.id)
  }
  if (item.target_url) {
    isOpen.value = false
    const url = item.target_url.trim()
    const isExternal = /^(https?:)?\/\//i.test(url) || (!url.startsWith('/') && !url.startsWith('#') && url.includes('.'))
    if (isExternal) {
      const fullUrl = /^(https?:)?\/\//i.test(url) ? url : `https://${url}`
      window.open(fullUrl, '_blank', 'noopener,noreferrer')
    } else {
      router.push(url)
    }
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
  const date = new Date(timestamp * 1000)
  const now = new Date()
  const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diffSec <= 60) return t('justNow') || 'только что'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} м`
  
  const isToday = date.toDateString() === now.toDateString()
  if (isToday) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString([], { day: '2-digit', month: '2-digit' })
}

function playNotificationSound(item?: NotificationItem, soundSignalFromEvt?: string) {
  try {
    let preset = soundSignalFromEvt && soundSignalFromEvt !== 'default' ? soundSignalFromEvt : ''
    if (!preset && item) {
      const modSignal = notifModuleRules.value[item.module_id]?.sound_signal
      const sevSignal = notifSoundSignals.value[item.severity]
      preset = modSignal || sevSignal || DEFAULT_SEVERITY_SOUNDS[item.severity] || 'chime'
    }
    if (!preset) {
      preset = 'chime'
    }
    playPresetSound(preset)
  } catch {
    // Игнорируем ошибки веб-аудио
  }
}

function showPushNotification(item: NotificationItem) {
  if (!('Notification' in window)) return
  if (Notification.permission === 'granted') {
    try {
      new Notification(item.title, {
        body: item.body || '',
        tag: `notif-${item.id}`,
      })
    } catch {
      // Fallback
    }
  }
}

// Live WS обновления
watch(lastEvent, (evt) => {
  if (!evt) return
  if (evt.type === 'resync_required') {
    fetchNotifications()
    return
  }
  if (evt.type === 'notification' && evt.data) {
    const newItem: NotificationItem = evt.data
    const exists = items.value.some((i) => i.id === newItem.id)
    if (!exists) {
      const isStaleFromMarkAll = lastMarkAllReadTime > 0 && newItem.created_at < (lastMarkAllReadTime - 1.0)
      if (isStaleFromMarkAll) {
        newItem.read_at = newItem.read_at || lastMarkAllReadTime
      }

      if (!filterUnread.value || !newItem.read_at) {
        items.value.unshift(newItem)
        liveCount.value++
        totalCount.value++
        filteredTotalCount.value++
      }

      if (isStaleFromMarkAll) {
        // Уведомление создано до markAllRead — не увеличиваем unreadCount
      } else if (typeof evt.unread_count === 'number') {
        unreadCount.value = evt.unread_count
      } else if (!newItem.read_at) {
        unreadCount.value++
      }

      if (!isStaleFromMarkAll && evt.sound_eligible && notifSoundEnabled.value && isLeader.value) {
        playNotificationSound(newItem, evt.sound_signal)
      }

      if (!isStaleFromMarkAll && evt.push_eligible && notifPushEnabled.value && isLeader.value) {
        showPushNotification(newItem)
      }
    }
  }
})

function handleUserGesture() {
  unlockAudioContext()
  window.removeEventListener('click', handleUserGesture)
  window.removeEventListener('keydown', handleUserGesture)
  window.removeEventListener('pointerdown', handleUserGesture)
}

onMounted(() => {
  window.addEventListener('click', handleUserGesture, { once: true })
  window.addEventListener('keydown', handleUserGesture, { once: true })
  window.addEventListener('pointerdown', handleUserGesture, { once: true })
  fetchNotifications()
  loadNotificationPreferences()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', handleUserGesture)
  window.removeEventListener('keydown', handleUserGesture)
  window.removeEventListener('pointerdown', handleUserGesture)
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
