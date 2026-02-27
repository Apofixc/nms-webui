<template>
  <div class="p-6 animate-fade-in">
    <div class="max-w-4xl mx-auto space-y-6">
      <!-- Page header -->
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
        <p class="mt-1 text-sm text-slate-400">NMS-WebUI — обзор системы</p>
      </div>

      <!-- Status cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card title="Backend" :hoverable="true">
          <div class="flex items-center gap-3">
            <span
              :class="[
                'w-3 h-3 rounded-full',
                backendOk ? 'bg-success animate-pulse-soft' : 'bg-danger',
              ]"
            />
            <span class="text-sm" :class="backendOk ? 'text-success' : 'text-danger'">
              {{ backendOk ? 'Подключён' : 'Недоступен' }}
            </span>
          </div>
        </Card>

        <Card title="Модули" :hoverable="true">
          <div class="text-2xl font-bold text-white">
            {{ loadedModuleIds.length }}
          </div>
          <p class="text-xs text-slate-500 mt-1">загружено</p>
        </Card>

        <Card title="Система" :hoverable="true">
          <div class="text-sm text-slate-400">
            Готова к работе
          </div>
        </Card>
      </div>

      <!-- Empty state -->
      <Card v-if="loadedModuleIds.length === 0">
        <div class="text-center py-8">
          <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-surface-750 flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-white mb-2">Нет загруженных модулей</h3>
          <p class="text-sm text-slate-400 max-w-md mx-auto">
            Добавьте модули в <code class="text-accent/80 bg-accent/10 px-1 rounded">backend/modules/</code>
            с файлом <code class="text-accent/80 bg-accent/10 px-1 rounded">manifest.yaml</code>
            и перезапустите backend.
          </p>
        </div>
      </Card>

      <!-- Loaded modules list -->
      <Card v-else title="Загруженные модули">
        <div class="space-y-2">
          <div
            v-for="mod in modules"
            :key="mod.id"
            class="flex items-center justify-between px-4 py-3 rounded-lg bg-surface-750/50 hover:bg-surface-700/50 transition-colors"
          >
            <div>
              <span class="text-sm font-medium text-white">{{ mod.name }}</span>
              <span class="ml-2 text-xs text-slate-500">v{{ mod.version }}</span>
            </div>
            <span
              :class="[
                'text-xs px-2 py-0.5 rounded-full',
                mod.enabled
                  ? 'bg-success/20 text-success'
                  : 'bg-slate-700 text-slate-400',
              ]"
            >
              {{ mod.enabled ? 'Активен' : 'Отключён' }}
            </span>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/core/store'
import { storeToRefs } from 'pinia'
import Card from '@/components/ui/Card.vue'

const store = useAppStore()
const { backendOk, modules, loadedModuleIds } = storeToRefs(store)
</script>
