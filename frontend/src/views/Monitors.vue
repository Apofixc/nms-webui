<template>
  <div class="p-4 sm:p-6 lg:p-8 w-full min-w-0 max-w-6xl 2xl:max-w-7xl mx-auto">
    <header class="mb-8">
      <h1 class="text-2xl font-semibold text-white">Мониторы</h1>
      <p class="text-slate-400 mt-1">Активные мониторы по инстансам</p>
    </header>
    <div class="mb-6">
      <label class="block text-sm text-slate-400 mb-2">Инстанс</label>
      <select v-model="selectedId" class="bg-surface-750 border border-surface-700 rounded-lg px-4 py-2 text-white">
        <option v-for="i in instances" :key="i.id" :value="i.id">{{ i.label }} (:{{ i.port }})</option>
      </select>
    </div>
    <div v-if="loading" class="flex justify-center py-12">
      <div class="w-8 h-8 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
    </div>
    <div v-else-if="status" class="rounded-xl border border-surface-700 bg-surface-800/60 p-5 mb-6">
      <p class="text-sm text-slate-400">Всего: <strong class="text-white">{{ status.total }}</strong>, OK: <span class="text-success">{{ status.ok }}</span>, Ошибки: <span class="text-danger">{{ status.error }}</span></p>
    </div>
    <ul v-if="monitors.length" class="space-y-2">
      <li v-for="m in monitors" :key="m.name" class="rounded-lg border border-surface-700 bg-surface-800/60 px-4 py-3 flex items-center justify-between">
        <span class="font-medium text-white">{{ m.display_name || m.name }}</span>
        <span class="text-sm text-slate-500">{{ m.type || '—' }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import api from '../api'

const instances = ref([])
const selectedId = ref(0)
const loading = ref(false)
const monitors = ref([])
const status = ref(null)

async function load() {
  if (instances.value.length === 0) return
  loading.value = true
  monitors.value = []
  status.value = null
  try {
    const [mon, st] = await Promise.all([
      api.instanceMonitors(selectedId.value),
      api.instanceMonitorsStatus(selectedId.value),
    ])
    monitors.value = Array.isArray(mon) ? mon : []
    status.value = st
  } catch {
    monitors.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    instances.value = await api.instances()
    if (instances.value.length) selectedId.value = instances.value[0].id
    await load()
  } catch {
    instances.value = []
  }
})

watch(selectedId, load)
</script>
