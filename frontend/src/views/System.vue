<template>
  <div class="p-8 max-w-6xl mx-auto">
    <header class="mb-8">
      <h1 class="text-2xl font-semibold text-white">Система</h1>
      <p class="text-slate-400 mt-1">Сеть и информация об API по инстансу</p>
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
    <div v-else class="space-y-6">
      <section v-if="hostname" class="rounded-xl border border-surface-700 bg-surface-800/60 p-5">
        <h2 class="text-sm font-medium text-slate-400 mb-2">Hostname</h2>
        <p class="font-mono text-white">{{ hostname.hostname }}</p>
      </section>
      <section v-if="interfaces && Object.keys(interfaces).length" class="rounded-xl border border-surface-700 bg-surface-800/60 p-5">
        <h2 class="text-sm font-medium text-slate-400 mb-3">Сетевые интерфейсы</h2>
        <ul class="space-y-2">
          <li v-for="(iface, name) in interfaces" :key="name" class="flex items-center gap-4">
            <span class="font-mono text-accent w-24">{{ name }}</span>
            <span class="text-sm text-slate-300">{{ (iface.ipv4 || []).join(', ') || '—' }}</span>
          </li>
        </ul>
      </section>
      <section v-if="utilsInfo" class="rounded-xl border border-surface-700 bg-surface-800/60 p-5">
        <h2 class="text-sm font-medium text-slate-400 mb-2">API / Utils</h2>
        <p class="text-sm text-slate-300">API version: <span class="text-white">{{ utilsInfo.api_version }}</span>, library: <span class="text-white">{{ utilsInfo.library_version }}</span></p>
      </section>
      <p v-if="!loading && loadError" class="text-amber-400/90 text-sm">Инстанс недоступен: {{ loadError }}</p>
      <p v-else-if="!loading && !hostname && !(interfaces && Object.keys(interfaces).length) && !utilsInfo" class="text-slate-400">Выберите инстанс или данные недоступны.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import api from '../api'

const instances = ref([])
const selectedId = ref(0)
const loading = ref(false)
const hostname = ref(null)
const interfaces = ref(null)
const utilsInfo = ref(null)
const loadError = ref('')

async function load() {
  if (instances.value.length === 0) return
  loading.value = true
  loadError.value = ''
  hostname.value = null
  interfaces.value = null
  utilsInfo.value = null
  try {
    const [h, i, u] = await Promise.all([
      api.instanceSystemHostname(selectedId.value),
      api.instanceSystemInterfaces(selectedId.value),
      api.instanceUtilsInfo(selectedId.value),
    ])
    hostname.value = h
    interfaces.value = i
    utilsInfo.value = u
  } catch (e) {
    hostname.value = null
    interfaces.value = null
    utilsInfo.value = null
    const msg = e?.message || String(e)
    try {
      const d = typeof msg === 'string' && msg.startsWith('{') ? JSON.parse(msg) : null
      loadError.value = (d?.detail ?? msg).slice(0, 200)
    } catch {
      loadError.value = msg.slice(0, 200)
    }
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
