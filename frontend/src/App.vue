<template>
  <MainLayout />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import MainLayout from '@/components/layout/MainLayout.vue'
import { useAppStore } from '@/core/store'
import { preloadModuleRoutes } from '@/modules/registry'

const store = useAppStore()

onMounted(async () => {
  await store.checkBackend()
  await store.loadModules()
  // Preload module views after initial render
  setTimeout(() => {
    preloadModuleRoutes()
  }, 300)
})
</script>
