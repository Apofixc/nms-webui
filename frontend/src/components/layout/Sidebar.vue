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
      <!-- Health Pill -->
      <div
        class="flex items-center rounded bg-surface-container-low border border-outline-variant/40 cursor-help"
        :class="isSidebarCollapsed ? 'justify-center py-2 px-0' : 'gap-2 px-3 py-1.5'"
        :title="healthTooltip"
      >
        <div
          class="w-2 h-2 rounded-full flex-shrink-0"
          :class="healthDotClass"
        />
        <span
          v-if="!isSidebarCollapsed"
          class="font-mono text-[11px] uppercase tracking-wider font-semibold truncate"
          :class="healthTextClass"
        >
          {{ healthLabel }}
        </span>
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
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/core/store'
import { useI18n } from '@/core/i18n'
import { storeToRefs } from 'pinia'
import { hasPermission, hasAnyPermission } from '@/core/auth'
import { useWebSocket } from '@/composables/useWebSocket'

const $route = useRoute()
const { t, translateModuleName } = useI18n()
const store = useAppStore()
const { sidebarGroups, groupOpen, backendOk, isSidebarCollapsed } = storeToRefs(store)
const { toggleGroup } = store

const { isConnected: wsConnected } = useWebSocket()

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
  if (hasPermission('roles.view')) return '/settings'
  if (hasPermission('users.view')) return '/settings/users'
  if (hasPermission('system.admin')) return '/settings/system'
  return '/settings/profile'
})
</script>
