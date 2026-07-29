<template>
  <aside class="w-64 flex-shrink-0 h-full flex flex-col overflow-hidden bg-surface-container-lowest border-r border-outline-variant text-on-surface">
    <!-- Header / Logo -->
    <div class="p-4 flex items-center gap-3 border-b border-outline-variant/60 bg-surface-container-lowest flex-shrink-0">
      <div class="w-9 h-9 rounded-lg bg-primary-container/20 border border-primary-container/40 flex items-center justify-center text-primary font-mono text-sm font-bold shadow-glow flex-shrink-0">
        NMS
      </div>
      <div class="min-w-0">
        <h1 class="font-bold text-base tracking-wider text-primary uppercase leading-tight font-sans truncate">NMS</h1>
        <p class="font-mono text-[10px] text-on-surface-variant uppercase truncate">Network Management System</p>
      </div>
    </div>

    <!-- Main Navigation Items -->
    <nav class="p-3 flex-1 min-h-0 overflow-y-auto space-y-1">
      <router-link
        to="/"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-all text-sm font-medium border-l-2 border-transparent"
        active-class="!text-primary !bg-primary/10 !border-primary font-bold"
      >
        <span class="material-symbols-outlined text-[20px] flex-shrink-0">dashboard</span>
        <span class="truncate">{{ t('dashboard') }}</span>
      </router-link>

      <a
        href="#"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-all text-sm font-medium border-l-2 border-transparent"
      >
        <span class="material-symbols-outlined text-[20px] flex-shrink-0">hub</span>
        <span class="truncate">{{ t('topology') }}</span>
      </a>

      <a
        href="#"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-all text-sm font-medium border-l-2 border-transparent"
      >
        <span class="material-symbols-outlined text-[20px] flex-shrink-0">warning</span>
        <span class="truncate">{{ t('faults') }}</span>
      </a>

      <a
        href="#"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-all text-sm font-medium border-l-2 border-transparent"
      >
        <span class="material-symbols-outlined text-[20px] flex-shrink-0">insights</span>
        <span class="truncate">{{ t('performance') }}</span>
      </a>

      <!-- Dynamic Module Navigation Groups -->
      <div v-for="group in sidebarGroups" :key="group.id" class="pt-2">
        <button
          type="button"
          class="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-left text-xs font-mono font-bold uppercase tracking-wider text-on-surface-variant hover:bg-surface-variant/40 transition-colors"
          @click="toggleGroup(group.id)"
        >
          <span class="truncate">{{ group.label }}</span>
          <span class="text-xs transition-transform duration-200 flex-shrink-0" :class="groupOpen[group.id] && 'rotate-180'">▾</span>
        </button>

        <div v-show="groupOpen[group.id]" class="mt-1 ml-2 pl-3 border-l border-outline-variant/50 space-y-0.5">
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 transition-colors block border-l-2 border-transparent"
            active-class="!text-primary font-bold !bg-primary/10 !border-primary"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-current opacity-60 flex-shrink-0" />
            <span class="truncate">{{ item.label }}</span>
          </router-link>
        </div>
      </div>
    </nav>

    <!-- Footer Area -->
    <div class="p-3 border-t border-outline-variant/60 space-y-2 flex-shrink-0">
      <!-- Health Pill -->
      <div class="flex items-center gap-2 px-3 py-1.5 rounded bg-surface-container-low border border-outline-variant/40">
        <div class="w-2 h-2 rounded-full bg-tertiary pulse-dot flex-shrink-0" />
        <span class="font-mono text-[11px] text-tertiary uppercase tracking-wider font-semibold truncate">
          {{ backendOk ? t('healthOptimal') : t('healthOffline') }}
        </span>
      </div>

      <a
        href="https://github.com/Apofixc/nms-webui"
        target="_blank"
        class="flex items-center gap-3 px-3 py-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 text-xs font-medium transition-colors border-l-2 border-transparent"
      >
        <span class="material-symbols-outlined text-[18px] flex-shrink-0">description</span>
        <span class="truncate">{{ t('documentation') }}</span>
      </a>

      <router-link
        v-if="hasAnyPermission(['settings.view', 'roles.view', 'users.view', 'modules.view', 'system.admin'])"
        to="/settings"
        class="flex items-center gap-3 px-3 py-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 text-xs font-medium transition-colors border-l-2 border-transparent"
        :class="$route.path.startsWith('/settings') && '!text-primary !bg-primary/10 font-bold !border-primary'"
      >
        <span class="material-symbols-outlined text-[18px] flex-shrink-0">settings</span>
        <span class="truncate">{{ t('settings') }}</span>
      </router-link>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAppStore } from '@/core/store'
import { useI18n } from '@/core/i18n'
import { storeToRefs } from 'pinia'
import { hasAnyPermission } from '@/core/auth'

const $route = useRoute()
const { t } = useI18n()
const store = useAppStore()
const { sidebarGroups, groupOpen, backendOk } = storeToRefs(store)
const { toggleGroup } = store
</script>
