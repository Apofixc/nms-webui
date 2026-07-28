<template>
  <header class="h-16 flex-shrink-0 bg-surface-dim/80 backdrop-blur-sm border-b border-outline-variant px-6 flex items-center justify-between text-on-surface z-40">
    <div class="flex items-center gap-2 font-mono text-xs text-on-surface-variant">
      <span class="w-2 h-2 rounded-full" :class="isConnected ? 'bg-tertiary shadow-glow' : 'bg-error'" />
      <span>{{ isConnected ? 'WS Live Connection' : 'WS Offline' }}</span>
    </div>

    <div class="flex items-center gap-6">
      <!-- Actions & User Profile Pill -->
      <div class="flex items-center gap-3">
        <!-- Notifications Button -->
        <button class="p-2 hover:text-primary transition-colors cursor-pointer rounded-full hover:bg-surface-variant/50 relative text-on-surface-variant flex items-center justify-center">
          <span class="material-symbols-outlined text-[20px]">notifications_active</span>
          <span v-if="hasUnread" class="w-2 h-2 rounded-full bg-tertiary absolute top-1.5 right-1.5" />
        </button>

        <!-- User Profile Badge -->
        <router-link to="/settings/profile" class="flex items-center gap-3 pl-3 border-l border-outline-variant hover:opacity-90 transition-opacity">
          <div class="flex flex-col items-end hidden lg:flex">
            <span class="text-xs font-bold text-on-surface leading-none">{{ currentUser?.full_name || 'Администратор' }}</span>
            <span class="text-[10px] text-indigo-600 dark:text-primary font-mono uppercase tracking-tighter mt-0.5">{{ currentUser?.role_name || 'SUPERUSER' }}</span>
          </div>
          <div class="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-300 dark:bg-primary/20 dark:text-primary dark:border-primary/50 flex items-center justify-center font-mono font-bold text-xs shadow-glow flex-shrink-0">
            {{ initials }}
          </div>
        </router-link>

        <!-- Logout Button -->
        <button
          @click="handleLogout"
          title="Выйти из системы"
          class="p-2 text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors rounded-lg flex items-center justify-center ml-1"
        >
          <span class="material-symbols-outlined text-[20px]">logout</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/core/i18n'
import { getStoredUser, clearAuthSession } from '@/core/auth'
import { apiLogout } from '@/core/api'
import { useWebSocket } from '@/composables/useWebSocket'

const { t } = useI18n()
const router = useRouter()
const currentUser = ref(getStoredUser())
const hasUnread = ref(false)

const { isConnected, lastEvent } = useWebSocket()

watch(lastEvent, (event) => {
  if (event) {
    hasUnread.value = true
  }
})

const initials = computed(() => {
  const name = currentUser.value?.full_name || 'Admin User'
  return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
})

async function handleLogout() {
  try {
    await apiLogout()
  } catch {}
  clearAuthSession()
  router.push('/login')
}

onMounted(() => {
  currentUser.value = getStoredUser()
})
</script>
