<template>
  <div v-if="$route.path === '/login'" class="h-screen w-full overflow-hidden bg-background">
    <router-view />
  </div>

  <div v-else class="h-screen min-h-0 w-full flex flex-shrink-0 overflow-hidden bg-background text-on-surface">
    <Sidebar />
    <main class="flex-1 min-h-0 min-w-0 flex flex-col overflow-hidden">
      <Header />

      <!-- Fixed Secondary Horizontal Navigation Bar for Settings Routes -->
      <nav
        v-if="$route.path.startsWith('/settings')"
        class="bg-surface-container-low border-b border-outline-variant px-6 flex items-center gap-6 text-sm font-medium flex-shrink-0 z-30 overflow-x-auto"
      >
        <router-link
          v-if="hasPermission('modules.view')"
          to="/settings/modules"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface whitespace-nowrap"
          active-class="!border-primary !text-primary font-bold"
        >
          {{ t('moduleManagement') }}
        </router-link>

        <router-link
          v-if="hasPermission('roles.view')"
          to="/settings"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface whitespace-nowrap"
          :class="$route.path === '/settings' && '!border-primary !text-primary font-bold'"
        >
          {{ t('accessIdentity') }}
        </router-link>

        <router-link
          v-if="hasPermission('users.view')"
          to="/settings/users"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface whitespace-nowrap"
          active-class="!border-primary !text-primary font-bold"
        >
          {{ t('usersManagement') }}
        </router-link>


        <router-link
          v-if="hasPermission('system.admin')"
          to="/settings/system"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface whitespace-nowrap"
          active-class="!border-primary !text-primary font-bold"
        >
          {{ t('systemAdmin') }}
        </router-link>

        <router-link
          to="/settings/profile"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface whitespace-nowrap"
          active-class="!border-primary !text-primary font-bold"
        >
          {{ t('userProfile') }}
        </router-link>
      </nav>

      <!-- Main Content Area -->
      <div class="flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden bg-background">
        <router-view v-slot="{ Component, route }">
          <transition name="page" mode="out-in">
            <component :is="Component" :key="route.path" v-if="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <!-- Modal: Idle Session Timeout Warning -->
    <div v-if="isIdleWarningOpen" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-surface-container-low border border-amber-500/50 rounded-xl p-6 w-full max-w-md shadow-glow space-y-4 text-on-surface">
        <div class="flex items-center gap-3 border-b border-outline-variant/60 pb-3">
          <span class="material-symbols-outlined text-amber-400 text-3xl">schedule</span>
          <div>
            <h3 class="font-bold text-base text-on-surface">{{ lang === 'ru' ? 'Завершение сессии' : 'Session Timeout Warning' }}</h3>
            <p class="text-xs text-on-surface-variant">{{ lang === 'ru' ? 'Обнаружено длительное отсутствие активности' : 'Inactivity detected' }}</p>
          </div>
        </div>

        <div class="text-center py-2 space-y-2">
          <p class="text-xs text-on-surface-variant">
            {{ lang === 'ru' ? 'Ваша сессия будет автоматически завершена через:' : 'Your session will expire in:' }}
          </p>
          <div class="text-3xl font-mono font-bold text-amber-400">
            00:{{ countdownSeconds < 10 ? '0' + countdownSeconds : countdownSeconds }}
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 pt-3 border-t border-outline-variant/60">
          <button
            @click="forceLogout"
            class="px-4 py-2 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold hover:bg-surface-bright cursor-pointer"
          >
            {{ lang === 'ru' ? 'Выйти' : 'Logout' }}
          </button>
          <button
            @click="extendSession"
            class="px-4 py-2 rounded bg-primary text-on-primary text-xs font-semibold shadow-glow hover:bg-primary-container cursor-pointer flex items-center gap-1.5"
          >
            <span class="material-symbols-outlined text-sm">refresh</span>
            <span>{{ lang === 'ru' ? 'Продлить сессию' : 'Extend Session' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import { useI18n } from '@/core/i18n'
import { useIdleTimeout } from '@/core/useIdleTimeout'
import { hasPermission } from '@/core/auth'

const { t, lang } = useI18n()
const { isIdleWarningOpen, countdownSeconds, extendSession, forceLogout } = useIdleTimeout()
</script>

<style scoped>
.page-enter-active,
.page-leave-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.page-enter-from { opacity: 0; transform: translateY(4px); }
.page-leave-to { opacity: 0; transform: translateY(-2px); }
</style>
