<template>
  <div class="p-6 bg-background min-h-full space-y-6 text-on-surface animate-fade-in">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-outline-variant/60 pb-4">
      <div>
        <h1 class="text-xl font-bold tracking-tight text-on-surface flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">security</span>
          <span>Журнал системного аудита</span>
        </h1>
        <p class="text-xs text-on-surface-variant mt-1 font-mono">
          Лог событий безопасности, входов в систему и действий администраторов
        </p>
      </div>

      <button
        @click="loadLogs"
        class="px-3 py-1.5 bg-surface-container-high hover:bg-surface-bright text-xs font-mono text-on-surface rounded-lg border border-outline-variant transition-colors flex items-center gap-1.5"
      >
        <span class="material-symbols-outlined text-sm">refresh</span>
        <span>Обновить</span>
      </button>
    </div>

    <!-- Filters & Table -->
    <div class="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-glow space-y-4">
      <div class="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center">
        <div class="relative w-full sm:w-80">
          <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">search</span>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Поиск по событию, пользователю, IP..."
            class="w-full bg-surface-container-lowest border border-outline-variant rounded-lg pl-9 pr-3 py-1.5 text-xs text-on-surface font-mono placeholder:text-outline focus:border-primary focus:outline-none"
          />
        </div>
        <div class="text-xs font-mono text-on-surface-variant">
          Всего записей: <span class="text-primary font-bold">{{ filteredLogs.length }}</span>
        </div>
      </div>

      <!-- Audit Logs Table -->
      <div class="overflow-x-auto rounded-lg border border-outline-variant/40">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-surface-container-high border-b border-outline-variant/60 text-[11px] font-mono text-on-surface-variant uppercase tracking-wider">
              <th class="py-2.5 px-4"># ID</th>
              <th class="py-2.5 px-4">Время</th>
              <th class="py-2.5 px-4">Пользователь</th>
              <th class="py-2.5 px-4">Действие</th>
              <th class="py-2.5 px-4">Ресурс</th>
              <th class="py-2.5 px-4">Детали</th>
              <th class="py-2.5 px-4">IP адрес</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/30 text-xs font-mono">
            <tr v-if="isLoading" class="text-center">
              <td colspan="7" class="py-8 text-on-surface-variant">Загрузка данных аудита...</td>
            </tr>
            <tr v-else-if="filteredLogs.length === 0" class="text-center">
              <td colspan="7" class="py-8 text-on-surface-variant">События не найдены</td>
            </tr>
            <tr
              v-else
              v-for="log in filteredLogs"
              :key="log.id"
              class="hover:bg-surface-container-high/50 transition-colors"
            >
              <td class="py-2.5 px-4 text-outline font-semibold">#{{ log.id }}</td>
              <td class="py-2.5 px-4 whitespace-nowrap text-on-surface-variant">{{ formatTime(log.timestamp) }}</td>
              <td class="py-2.5 px-4 font-semibold text-primary">
                {{ log.username }}
              </td>
              <td class="py-2.5 px-4">
                <span :class="getActionBadgeClass(log.action)">
                  {{ log.action }}
                </span>
              </td>
              <td class="py-2.5 px-4 text-on-surface-variant">{{ log.resource }}</td>
              <td class="py-2.5 px-4 max-w-xs truncate text-on-surface" :title="log.details || undefined">
                {{ log.details || '-' }}
              </td>
              <td class="py-2.5 px-4 text-outline whitespace-nowrap">{{ log.ip_address || 'local' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiFetchAuditLogs } from '@/core/api'

interface AuditLog {
  id: number
  timestamp: string
  user_id: string | null
  username: string
  action: string
  resource: string
  details: string | null
  ip_address: string | null
}

const logs = ref<AuditLog[]>([])
const isLoading = ref(false)
const searchQuery = ref('')

async function loadLogs() {
  isLoading.value = true
  try {
    const res = await apiFetchAuditLogs(200, 0)
    logs.value = res.items || []
  } catch (err) {
    console.error('Failed to load audit logs:', err)
  } finally {
    isLoading.value = false
  }
}

const filteredLogs = computed(() => {
  if (!searchQuery.value.trim()) return logs.value
  const q = searchQuery.value.toLowerCase()
  return logs.value.filter(
    (l) =>
      l.username.toLowerCase().includes(q) ||
      l.action.toLowerCase().includes(q) ||
      l.resource.toLowerCase().includes(q) ||
      (l.details && l.details.toLowerCase().includes(q)) ||
      (l.ip_address && l.ip_address.toLowerCase().includes(q))
  )
})

function formatTime(ts: string) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('ru-RU')
}

function getActionBadgeClass(action: string) {
  if (action.includes('login_failed') || action.includes('delete')) {
    return 'px-2 py-0.5 rounded text-[10px] font-bold bg-error/20 text-error border border-error/30'
  }
  if (action.includes('login_success') || action.includes('create')) {
    return 'px-2 py-0.5 rounded text-[10px] font-bold bg-tertiary/20 text-tertiary border border-tertiary/30'
  }
  return 'px-2 py-0.5 rounded text-[10px] font-bold bg-surface-variant text-on-surface-variant border border-outline-variant'
}

onMounted(() => {
  loadLogs()
})
</script>
