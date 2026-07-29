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
          to="/settings/modules"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface whitespace-nowrap"
          active-class="!border-primary !text-primary font-bold"
        >
          {{ t('moduleManagement') }}
        </router-link>

        <router-link
          to="/settings"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface whitespace-nowrap"
          :class="$route.path === '/settings' && '!border-primary !text-primary font-bold'"
        >
          {{ t('accessIdentity') }}
        </router-link>

        <router-link
          to="/settings/users"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface whitespace-nowrap"
          active-class="!border-primary !text-primary font-bold"
        >
          {{ t('usersManagement') }}
        </router-link>

        <router-link
          to="/settings/access-control"
          class="py-3.5 px-1 border-b-2 transition-all border-transparent text-on-surface-variant hover:text-on-surface whitespace-nowrap"
          active-class="!border-primary !text-primary font-bold"
        >
          {{ t('accessControl') }}
        </router-link>

        <router-link
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
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" v-if="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'
import { useI18n } from '@/core/i18n'

const { t } = useI18n()
</script>

<style scoped>
.page-enter-active,
.page-leave-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.page-enter-from { opacity: 0; transform: translateY(4px); }
.page-leave-to { opacity: 0; transform: translateY(-2px); }
</style>
