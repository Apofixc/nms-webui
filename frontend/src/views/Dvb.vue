<template>
  <div class="p-8 max-w-6xl mx-auto">
    <header class="mb-8">
      <h1 class="text-2xl font-semibold text-white">DVB-адаптеры</h1>
      <p class="text-slate-400 mt-1">Тюнеры по инстансу</p>
    </header>
    <div class="mb-6">
      <label class="block text-sm text-slate-400 mb-2">Инстанс</label>
      <select
        v-model="selectedId"
        class="bg-surface-750 border border-surface-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-accent/50"
      >
        <option v-for="i in instances" :key="i.id" :value="i.id">{{ i.label }} (:{{ i.port }})</option>
      </select>
    </div>
    <div v-if="loading" class="flex justify-center py-12">
      <div class="w-8 h-8 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
    </div>
    <div v-else-if="!list.length" class="rounded-xl border border-surface-700 bg-surface-800/60 p-8 text-center text-slate-400">
      Нет DVB-адаптеров или инстанс недоступен.
    </div>
    <ul v-else class="space-y-2">
      <li
        v-for="a in list"
        :key="a.name"
        class="rounded-lg border border-surface-700 bg-surface-800/60 px-4 py-3 flex items-center justify-between"
      >
        <span class="font-mono text-accent">{{ a.name }}</span>
        <span class="text-sm text-slate-400">{{ a.type || '—' }} · {{ a.frequency || '—' }}</span>
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
const list = ref([])

async function load() {
  if (instances.value.length === 0) return
  loading.value = true
  try {
    list.value = await api.instanceDvbAdapters(selectedId.value)
    if (!Array.isArray(list.value)) list.value = []
  } catch {
    list.value = []
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
