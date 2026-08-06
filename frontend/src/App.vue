<template>
  <MainLayout />
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import MainLayout from '@/components/layout/MainLayout.vue'
import { useAppStore } from '@/core/store'
import { preloadModuleRoutes } from '@/modules/registry'
import { apiGetMe } from '@/core/api'
import { isAuthenticated, updateStoredUser } from '@/core/auth'
import { useWebSocket } from '@/composables/useWebSocket'

const store = useAppStore()
const { onEvent } = useWebSocket()

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    store.triggerSettingsUpdate()
  }
}

onMounted(async () => {
  onEvent('module_settings_changed', () => {
    store.triggerSettingsUpdate()
  })

  if (isAuthenticated()) {
    try {
      const me = await apiGetMe()
      if (me) {
        updateStoredUser({
          permissions: me.permissions,
          role_id: me.role_id,
          role_name: me.role_name,
          full_name: me.full_name,
          email: me.email,
          avatar: me.avatar,
        })
      }
    } catch (e) {
      // ignore auth fetch failure
    }
  }
  await store.checkBackend()
  await store.loadModules()
  // Preload module views after initial render
  setTimeout(() => {
    preloadModuleRoutes()
  }, 300)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>
