<template>
  <header class="h-16 flex-shrink-0 bg-surface-dim/80 backdrop-blur-sm border-b border-outline-variant px-6 flex items-center justify-between text-on-surface z-40">
    <div class="flex items-center gap-3">
      <button
        @click="toggleSidebar"
        class="p-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-colors rounded-lg flex items-center justify-center cursor-pointer"
        :title="isSidebarCollapsed ? t('expandSidebar') : t('collapseSidebar')"
      >
        <span class="material-symbols-outlined text-[22px]">
          {{ isSidebarCollapsed ? 'menu' : 'menu_open' }}
        </span>
      </button>
    </div>

    <div class="flex items-center gap-6">
      <!-- Actions & User Profile Pill -->
      <div class="flex items-center gap-3">
        <!-- User Profile Badge -->
        <router-link to="/settings/profile" class="flex items-center gap-3 pl-3 border-l border-outline-variant hover:opacity-90 transition-opacity">
          <div class="flex flex-col items-end hidden lg:flex">
            <span class="text-xs font-bold text-on-surface leading-none">{{ currentUser?.full_name || t('roleAdmin') }}</span>
            <span class="text-[10px] text-primary font-mono uppercase tracking-tighter mt-0.5">{{ getRoleTitle(currentUser?.role_name || '') || t('roleSuperuser') }}</span>
          </div>
          <div class="w-8 h-8 rounded-full bg-primary/20 border border-primary/50 flex items-center justify-center font-mono font-bold text-xs text-primary shadow-glow flex-shrink-0 overflow-hidden">
            <img v-if="currentUser?.avatar" :src="currentUser.avatar" alt="Avatar" class="w-full h-full object-cover" />
            <span v-else>{{ initials }}</span>
          </div>
        </router-link>

        <!-- Logout Button -->
        <button
          v-if="isAuthEnabled"
          @click="handleLogout"
          :title="t('logoutTitle')"
          class="p-2 text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors rounded-lg flex items-center justify-center ml-1"
        >
          <span class="material-symbols-outlined text-[20px]">logout</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/core/i18n'
import { getStoredUser, getStoredToken, clearAuthSession } from '@/core/auth'
import { apiLogout } from '@/core/api'
import { useWebSocket } from '@/composables/useWebSocket'
import { useAppStore } from '@/core/store'
import { storeToRefs } from 'pinia'

const store = useAppStore()
const { isSidebarCollapsed } = storeToRefs(store)
const { toggleSidebar } = store

const { t, getRoleTitle } = useI18n()
const router = useRouter()
const currentUser = ref(getStoredUser())
const hasUnread = ref(false)

const isAuthEnabled = computed(() => {
  const token = getStoredToken()
  return token !== 'system_disabled_auth' && currentUser.value?.auth_enabled !== false
})

const { isConnected, lastEvent } = useWebSocket()

watch(lastEvent, (event) => {
  if (event) {
    hasUnread.value = true
  }
})

const initials = computed(() => {
  const name = currentUser.value?.full_name || t('defaultAdminUser')
  return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
})

async function handleLogout() {
  try {
    await apiLogout()
  } catch {}
  clearAuthSession()
  router.push('/login')
}

function syncUser() {
  currentUser.value = getStoredUser()
}

onMounted(() => {
  syncUser()
  window.addEventListener('nms-user-updated', syncUser)
})

onBeforeUnmount(() => {
  window.removeEventListener('nms-user-updated', syncUser)
})
</script>
