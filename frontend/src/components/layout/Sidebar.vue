<template>
  <aside
    :class="isSidebarCollapsed ? 'w-16' : 'w-64'"
    class="flex-shrink-0 h-full flex flex-col overflow-hidden bg-surface-container-lowest border-r border-outline-variant text-on-surface transition-all duration-300 ease-in-out"
  >
    <!-- Header / Logo -->
    <div
      class="p-4 flex items-center border-b border-outline-variant/60 bg-surface-container-lowest flex-shrink-0"
      :class="isSidebarCollapsed ? 'justify-center p-3' : 'gap-3'"
    >
      <div class="w-9 h-9 rounded-lg bg-primary-container/20 border border-primary-container/40 flex items-center justify-center text-primary font-mono text-sm font-bold shadow-glow flex-shrink-0">
        NMS
      </div>
      <div v-if="!isSidebarCollapsed" class="min-w-0">
        <h1 class="font-bold text-base tracking-wider text-primary uppercase leading-tight font-sans truncate">NMS</h1>
        <p class="font-mono text-[10px] text-on-surface-variant uppercase truncate">Network Management System</p>
      </div>
    </div>

    <!-- Fixed Main Item (Dashboard) -->
    <div class="p-3 pb-1 flex-shrink-0" :class="isSidebarCollapsed && 'px-2'">
      <router-link
        to="/"
        class="flex items-center rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-all text-sm font-medium border-l-2 border-transparent"
        :class="isSidebarCollapsed ? 'justify-center py-2.5 px-0' : 'gap-3 px-3 py-2.5'"
        active-class="!text-primary !bg-primary/10 !border-primary font-bold"
        :title="isSidebarCollapsed ? t('dashboard') : ''"
      >
        <span class="material-symbols-outlined text-[20px] flex-shrink-0">dashboard</span>
        <span v-if="!isSidebarCollapsed" class="truncate">{{ t('dashboard') }}</span>
      </router-link>
    </div>

    <!-- Dynamic Module Navigation Groups -->
    <nav class="pb-3 flex-1 min-h-0 overflow-y-auto space-y-1" :class="isSidebarCollapsed ? 'px-2' : 'px-3'">
      <div v-for="group in sidebarGroups" :key="group.id" class="pt-1">
        <button
          v-if="!isSidebarCollapsed"
          type="button"
          class="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-left text-xs font-mono font-bold uppercase tracking-wider text-on-surface-variant hover:bg-surface-variant/40 transition-colors"
          @click="toggleGroup(group.id)"
        >
          <span class="truncate">{{ translateModuleName(group.label) }}</span>
          <span class="text-xs transition-transform duration-200 flex-shrink-0" :class="groupOpen[group.id] && 'rotate-180'">▾</span>
        </button>

        <div
          v-show="!isSidebarCollapsed ? groupOpen[group.id] : true"
          class="mt-1 space-y-0.5"
          :class="!isSidebarCollapsed && 'ml-2 pl-3 border-l border-outline-variant/50'"
        >
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="flex items-center rounded-md text-xs text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 transition-colors block border-l-2 border-transparent"
            :class="isSidebarCollapsed ? 'justify-center py-2 px-0' : 'gap-2 px-3 py-1.5'"
            active-class="!text-primary font-bold !bg-primary/10 !border-primary"
            :title="isSidebarCollapsed ? translateModuleName(item.label) : ''"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-current opacity-60 flex-shrink-0" />
            <span v-if="!isSidebarCollapsed" class="truncate">{{ translateModuleName(item.label) }}</span>
          </router-link>
        </div>
      </div>
    </nav>

    <!-- Footer Area -->
    <div class="p-3 border-t border-outline-variant/60 space-y-2 flex-shrink-0" :class="isSidebarCollapsed && 'px-2'">
      <!-- Health Pill with Interactive Status Popover -->
      <div class="relative">
        <button
          type="button"
          class="w-full flex items-center rounded bg-surface-container-low border border-outline-variant/40 hover:bg-surface-variant/40 transition-colors cursor-pointer"
          :class="isSidebarCollapsed ? 'justify-center py-2 px-0' : 'gap-2 px-3 py-1.5'"
          @click="showHealthDetails = !showHealthDetails"
          :title="healthTooltip"
        >
          <div
            class="w-2 h-2 rounded-full flex-shrink-0"
            :class="healthDotClass"
          />
          <span
            v-if="!isSidebarCollapsed"
            class="font-mono text-[11px] uppercase tracking-wider font-semibold truncate flex-1 text-left"
            :class="healthTextClass"
          >
            {{ healthLabel }}
          </span>
          <span v-if="!isSidebarCollapsed" class="text-[10px] text-on-surface-variant/70 font-mono">ℹ</span>
        </button>

        <!-- Connection Details Popover -->
        <div
          v-if="showHealthDetails"
          :class="isSidebarCollapsed ? 'absolute bottom-0 left-full ml-2 w-72' : 'absolute bottom-full left-0 right-0 mb-2'"
          class="p-3 rounded-lg bg-surface-container-high border border-outline-variant shadow-xl z-50 text-xs font-sans text-on-surface space-y-2 overflow-hidden"
        >
          <div class="flex items-center justify-between border-b border-outline-variant/60 pb-1.5 gap-1">
            <span class="font-bold text-[11px] uppercase tracking-wider text-primary font-mono truncate">Состояние NMS</span>
            <button @click.stop="showHealthDetails = false" class="text-on-surface-variant hover:text-on-surface text-xs font-bold px-1 flex-shrink-0">✕</button>
          </div>

          <!-- REST API -->
          <div class="flex items-center justify-between text-[11px] gap-1">
            <span class="text-on-surface-variant truncate">REST API:</span>
            <span class="font-medium flex-shrink-0" :class="backendOk ? 'text-tertiary' : 'text-error'">
              {{ backendOk ? '🟢 В сети' : '🔴 Офлайн' }}
            </span>
          </div>

          <!-- WebSocket Status -->
          <div class="flex items-center justify-between text-[11px] gap-1">
            <span class="text-on-surface-variant truncate">WebSocket:</span>
            <span class="font-medium flex-shrink-0" :class="wsConnected ? 'text-tertiary' : 'text-error'">
              {{ wsConnected ? '🟢 В сети' : '🔴 Офлайн' }}
            </span>
          </div>

          <!-- RTT / Latency -->
          <div v-if="wsConnected" class="flex items-center justify-between text-[11px] gap-1">
            <span class="text-on-surface-variant truncate">Задержка (RTT):</span>
            <span class="font-mono font-semibold flex-shrink-0" :class="connectionQuality === 'excellent' ? 'text-tertiary' : connectionQuality === 'good' ? 'text-primary' : 'text-warning'">
              {{ rtt !== null ? `${rtt} мс` : '—' }}
            </span>
          </div>

          <!-- Tab Leader Role -->
          <div v-if="wsConnected" class="flex items-center justify-between text-[11px] gap-1">
            <span class="text-on-surface-variant truncate">Режим вкладки:</span>
            <span class="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface-variant/60 text-on-surface flex-shrink-0">
              {{ isLeader ? '👑 Лидер' : '📑 Ведомая' }}
            </span>
          </div>

          <!-- Active Topics -->
          <div v-if="wsConnected" class="flex items-center justify-between text-[11px] gap-1">
            <span class="text-on-surface-variant truncate">Подписки:</span>
            <span class="font-mono font-medium flex-shrink-0">{{ activeTopicsCount }} топик(а)</span>
          </div>

          <!-- Last Event -->
          <div v-if="lastEvent" class="pt-1.5 border-t border-outline-variant/40 text-[10px] space-y-0.5">
            <div class="text-on-surface-variant flex justify-between gap-1 items-center">
              <span class="truncate">Событие:</span>
              <span class="font-mono text-primary truncate flex-shrink-0 max-w-[110px] text-right">{{ lastEvent.type || 'event' }}</span>
            </div>
          </div>

          <!-- Server WS Metrics (for Admins) -->
          <div v-if="serverMetrics" class="pt-1.5 border-t border-outline-variant/40 space-y-1">
            <div class="text-[10px] font-bold text-primary font-mono uppercase tracking-wider">Серверные WS метрики</div>
            <div class="flex justify-between text-[10px] gap-1">
              <span class="text-on-surface-variant truncate">Всего сокетов:</span>
              <span class="font-mono font-medium flex-shrink-0">{{ serverMetrics.active_connections }}</span>
            </div>
            <div class="flex justify-between text-[10px] gap-1">
              <span class="text-on-surface-variant truncate">Отправлено / Принято:</span>
              <span class="font-mono flex-shrink-0">{{ serverMetrics.total_sent }} / {{ serverMetrics.total_received }}</span>
            </div>
            <div class="flex justify-between text-[10px] gap-1">
              <span class="text-on-surface-variant truncate">Потеряно кадров:</span>
              <span class="font-mono flex-shrink-0" :class="serverMetrics.total_dropped > 0 ? 'text-error font-bold' : 'text-on-surface-variant'">
                {{ serverMetrics.total_dropped }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <router-link
        to="/docs"
        class="flex items-center rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 text-xs font-medium transition-colors border-l-2 border-transparent"
        :class="[
          isSidebarCollapsed ? 'justify-center py-2 px-0' : 'gap-3 px-3 py-2',
          $route.path === '/docs' && '!text-primary !bg-primary/10 font-bold !border-primary'
        ]"
        :title="isSidebarCollapsed ? t('documentation') : ''"
      >
        <span class="material-symbols-outlined text-[18px] flex-shrink-0">description</span>
        <span v-if="!isSidebarCollapsed" class="truncate">{{ t('documentation') }}</span>
      </router-link>

      <router-link
        v-if="hasAnyPermission(['roles.view', 'users.view', 'modules.view', 'system.admin'])"
        :to="defaultSettingsPath"
        class="flex items-center rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 text-xs font-medium transition-colors border-l-2 border-transparent"
        :class="[
          isSidebarCollapsed ? 'justify-center py-2 px-0' : 'gap-3 px-3 py-2',
          $route.path.startsWith('/settings') && '!text-primary !bg-primary/10 font-bold !border-primary'
        ]"
        :title="isSidebarCollapsed ? t('settings') : ''"
      >
        <span class="material-symbols-outlined text-[18px] flex-shrink-0">settings</span>
        <span v-if="!isSidebarCollapsed" class="truncate">{{ t('settings') }}</span>
      </router-link>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/core/store'
import { useI18n } from '@/core/i18n'
import { storeToRefs } from 'pinia'
import { hasPermission, hasAnyPermission } from '@/core/auth'
import { useWebSocket } from '@/composables/useWebSocket'
import { apiGetWsMetrics } from '@/core/api'

const $route = useRoute()
const { t, translateModuleName } = useI18n()
const store = useAppStore()
const { sidebarGroups, groupOpen, backendOk, isSidebarCollapsed } = storeToRefs(store)
const { toggleGroup } = store

const { isConnected: wsConnected, rtt, isLeader, activeTopicsCount, connectionQuality, lastEvent, ping } = useWebSocket()
const showHealthDetails = ref(false)

interface ServerWsMetrics {
  active_connections: number
  total_sent: number
  total_received: number
  total_dropped: number
}
const serverMetrics = ref<ServerWsMetrics | null>(null)

watch(showHealthDetails, async (val) => {
  if (val) {
    if (wsConnected.value) {
      ping()
    }
    if (hasPermission('system.admin')) {
      serverMetrics.value = await apiGetWsMetrics()
    }
  }
})

const healthState = computed(() => {
  if (!backendOk.value) return 'offline'
  if (!wsConnected.value) return 'degraded'
  return 'optimal'
})

const healthLabel = computed(() => {
  if (healthState.value === 'optimal') return t('healthOptimal')
  if (healthState.value === 'degraded') return t('healthDegraded')
  return t('healthOffline')
})

const healthTooltip = computed(() => {
  if (healthState.value === 'optimal') return t('healthOptimalTooltip')
  if (healthState.value === 'degraded') return t('healthDegradedTooltip')
  return t('healthOfflineTooltip')
})

const healthDotClass = computed(() => {
  if (healthState.value === 'optimal') return 'bg-tertiary pulse-dot'
  if (healthState.value === 'degraded') return 'bg-warning'
  return 'bg-error'
})

const healthTextClass = computed(() => {
  if (healthState.value === 'optimal') return 'text-tertiary'
  if (healthState.value === 'degraded') return 'text-warning'
  return 'text-error'
})

const defaultSettingsPath = computed(() => {
  if (hasPermission('modules.view')) return '/settings/modules'
  if (hasPermission('roles.view')) return '/settings/access-control'
  if (hasPermission('users.view')) return '/settings/users'
  if (hasPermission('system.admin')) return '/settings/system'
  return '/settings/profile'
})
</script>
