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

const store = useAppStore()
let eventSource: EventSource | null = null

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    store.triggerSettingsUpdate()
  }
}

function initSSE() {
  if (eventSource) eventSource.close()
  
  eventSource = new EventSource('/api/events')
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'module_settings_changed') {
        store.triggerSettingsUpdate()
      }
    } catch (e) {
      // ignore parse errors
    }
  }
  
  eventSource.onerror = () => {
    // optional: retry logic is built-in to EventSource
  }
}

onMounted(async () => {
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
  initSSE()
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  if (eventSource) eventSource.close()
})
</script>
