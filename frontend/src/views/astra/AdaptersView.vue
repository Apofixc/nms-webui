<template>
  <div class="p-4 sm:p-6 lg:p-8 w-full min-w-0 max-w-7xl 2xl:max-w-[90rem] mx-auto">
    <header class="mb-8 flex flex-wrap items-start justify-between gap-6">
      <div>
        <h1 class="text-2xl font-semibold text-white">DVB-адаптеры</h1>
        <p class="text-slate-400 mt-1">Мониторинг и управление тюнерами по инстансам Astra</p>
      </div>
      <div class="flex items-center gap-2">
        <select
          v-model.number="selectedInstance"
          class="rounded-lg bg-surface-800 border border-surface-600 px-3 py-2 text-white text-sm focus:border-accent outline-none"
        >
          <option v-for="inst in instances" :key="inst.id" :value="inst.id">{{ inst.label }}</option>
        </select>
        <button
          type="button"
          @click="load"
          :disabled="loading || selectedInstance == null"
          class="rounded-lg px-4 py-2 text-sm font-medium bg-surface-700 text-slate-300 hover:bg-surface-600 hover:text-white disabled:opacity-50 transition-colors"
        >
          {{ loading ? 'Загрузка…' : 'Обновить' }}
        </button>
        <button
          type="button"
          @click="scanDevices"
          :disabled="scanning || selectedInstance == null"
          class="rounded-lg px-4 py-2 text-sm font-medium bg-surface-700 text-slate-300 hover:bg-surface-600 hover:text-white disabled:opacity-50 transition-colors"
        >
          {{ scanning ? 'Сканирование…' : 'Найти устройства' }}
        </button>
        <button
          type="button"
          @click="showCreate = !showCreate"
          class="rounded-lg px-4 py-2 text-sm font-medium bg-accent/20 text-accent border border-accent/50 hover:bg-accent/30 transition-colors"
        >
          Добавить адаптер
        </button>
      </div>
    </header>

    <div v-if="error" class="mb-4 rounded-lg border border-danger/40 bg-danger/10 text-danger px-4 py-3 text-sm">
      {{ error }}
    </div>

    <!-- Найденные устройства -->
    <section v-if="devices.length" class="mb-6 rounded-xl border border-surface-700 bg-surface-800/60 p-4">
      <h2 class="text-white font-medium mb-3">Обнаруженные DVB-устройства</h2>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="(dev, i) in devices"
          :key="i"
          class="rounded-lg bg-surface-700 text-slate-300 px-3 py-1.5 text-sm font-mono"
        >
          {{ deviceLabel(dev) }}
        </span>
      </div>
    </section>

    <!-- Форма создания -->
    <section v-if="showCreate" class="mb-6 rounded-xl border border-surface-700 bg-surface-800/60 p-4">
      <h2 class="text-white font-medium mb-3">Новый адаптер</h2>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label class="text-sm text-slate-400">Имя
          <input v-model="createForm.name" type="text" class="mt-1 w-full rounded bg-surface-900 border border-surface-600 px-2 py-1.5 text-white text-sm focus:border-accent outline-none" />
        </label>
        <label class="text-sm text-slate-400">Adapter (номер)
          <input v-model.number="createForm.adapter" type="number" min="0" class="mt-1 w-full rounded bg-surface-900 border border-surface-600 px-2 py-1.5 text-white text-sm focus:border-accent outline-none" />
        </label>
        <label class="text-sm text-slate-400">Тип
          <select v-model="createForm.type" class="mt-1 w-full rounded bg-surface-900 border border-surface-600 px-2 py-1.5 text-white text-sm focus:border-accent outline-none">
            <option value="S">DVB-S</option>
            <option value="S2">DVB-S2</option>
            <option value="T">DVB-T</option>
            <option value="T2">DVB-T2</option>
            <option value="C">DVB-C</option>
          </select>
        </label>
        <label class="text-sm text-slate-400">Транспондер (freq:pol:srate)
          <input v-model="createForm.tp" type="text" placeholder="12345:H:27500" class="mt-1 w-full rounded bg-surface-900 border border-surface-600 px-2 py-1.5 text-white text-sm focus:border-accent outline-none" />
        </label>
      </div>
      <label class="mt-3 flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
        <input type="checkbox" v-model="createForm.monitor" class="rounded border-surface-600 bg-surface-800 text-accent" />
        Включить мониторинг
      </label>
      <div class="mt-4 flex gap-2">
        <button
          type="button"
          @click="createAdapter"
          :disabled="creating || !createForm.name"
          class="rounded-lg bg-accent/20 text-accent border border-accent/50 px-4 py-2 text-sm font-medium hover:bg-accent/30 disabled:opacity-50"
        >
          {{ creating ? 'Создание…' : 'Создать' }}
        </button>
        <button type="button" @click="showCreate = false" class="rounded-lg bg-surface-700 text-slate-300 px-4 py-2 text-sm font-medium hover:bg-surface-600">
          Отмена
        </button>
      </div>
    </section>

    <div v-if="loading && !adapters.length" class="flex justify-center py-20">
      <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
    </div>

    <div v-else-if="!adapters.length" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
      Нет адаптеров на выбранном инстансе.
    </div>

    <!-- Таблица адаптеров -->
    <div v-else class="w-full min-w-0 overflow-x-auto rounded-xl border border-surface-700 bg-surface-800/60">
      <table class="w-full text-sm" style="min-width: 720px;">
        <thead>
          <tr class="border-b border-surface-700 text-left text-slate-400">
            <th class="px-4 py-3.5 font-medium">Имя</th>
            <th class="px-4 py-3.5 font-medium">Статус</th>
            <th class="px-4 py-3.5 font-medium">Signal</th>
            <th class="px-4 py-3.5 font-medium">SNR</th>
            <th class="px-4 py-3.5 font-medium">BER</th>
            <th class="px-4 py-3.5 font-medium">UNC</th>
            <th class="px-4 py-3.5 font-medium">Мониторинг</th>
            <th class="px-4 py-3.5 font-medium pr-5">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in adapters" :key="a.name" class="border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors">
            <td class="px-4 py-3 text-white font-mono">{{ a.name }}</td>
            <td class="px-4 py-3">
              <span
                class="text-xs font-medium px-2.5 py-1 rounded-full"
                :class="hasLock(a) ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'"
              >
                {{ hasLock(a) ? 'Lock' : (statusOf(a) ? 'No lock' : '—') }}
              </span>
            </td>
            <td class="px-4 py-3 text-slate-300 font-mono">{{ fmt(statusOf(a)?.signal, '%') }}</td>
            <td class="px-4 py-3 text-slate-300 font-mono">{{ fmt(statusOf(a)?.snr, ' dB') }}</td>
            <td class="px-4 py-3 text-slate-300 font-mono">{{ fmt(statusOf(a)?.ber) }}</td>
            <td class="px-4 py-3 text-slate-300 font-mono">{{ fmt(statusOf(a)?.unc) }}</td>
            <td class="px-4 py-3">
              <span
                class="text-xs font-medium px-2.5 py-1 rounded-full"
                :class="a.monitored ? 'bg-success/20 text-success' : 'bg-surface-700 text-slate-400'"
              >
                {{ a.monitored ? 'Вкл' : 'Выкл' }}
              </span>
            </td>
            <td class="px-4 py-3 pr-5">
              <div class="flex gap-1.5">
                <button
                  type="button"
                  title="Поиск каналов на транспондере"
                  class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50"
                  :disabled="actioning"
                  @click="scanChannels(a)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                </button>
                <button
                  type="button"
                  title="Удалить"
                  class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50"
                  :disabled="actioning"
                  @click="deleteAdapter(a)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Результат поиска каналов -->
    <section v-if="scanResult" class="mt-6 rounded-xl border border-surface-700 bg-surface-800/60 p-4">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-white font-medium">
          Поиск каналов: {{ scanResult.name }}
          <span class="ml-2 text-xs font-normal px-2 py-0.5 rounded-full" :class="scanResult.state === 'done' ? 'bg-success/20 text-success' : scanResult.state === 'error' ? 'bg-danger/20 text-danger' : 'bg-accent/20 text-accent'">
            {{ scanResult.state }}
          </span>
        </h2>
        <button type="button" @click="scanResult = null" class="text-slate-500 hover:text-slate-300 text-sm">Закрыть</button>
      </div>
      <div v-if="(scanResult.services || []).length" class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-surface-700 text-left text-slate-400">
              <th class="px-3 py-2 font-medium">Сервис</th>
              <th class="px-3 py-2 font-medium">Провайдер</th>
              <th class="px-3 py-2 font-medium">SID</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(s, i) in scanResult.services" :key="i" class="border-t border-surface-700/50">
              <td class="px-3 py-2 text-white">{{ s.name || '—' }}</td>
              <td class="px-3 py-2 text-slate-300">{{ s.provider || '—' }}</td>
              <td class="px-3 py-2 text-slate-300 font-mono">{{ s.sid ?? s.pnr ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="text-slate-500 text-sm">{{ scanResult.state === 'running' ? 'Поиск выполняется…' : 'Сервисы не найдены.' }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import http from '@/core/api'

const instances = ref<any[]>([])
const selectedInstance = ref<number | null>(null)
const adapters = ref<any[]>([])
const statuses = ref<any[]>([])
const devices = ref<any[]>([])
const scanResult = ref<any>(null)
const loading = ref(false)
const scanning = ref(false)
const creating = ref(false)
const actioning = ref(false)
const showCreate = ref(false)
const error = ref('')
const createForm = ref<any>({ name: '', adapter: 0, type: 'S2', tp: '', monitor: true })
let pollTimer: ReturnType<typeof setInterval> | null = null
let resultTimer: ReturnType<typeof setInterval> | null = null

function statusOf(a: any) {
  return statuses.value.find((s: any) => s.name_adapter === a.name || s.name === a.name)
}

function hasLock(a: any) {
  const st = statusOf(a)?.status
  // status — битовая маска fe_status, 0x10 = FE_HAS_LOCK
  return typeof st === 'number' && st > 0 && (st & 0x10) !== 0
}

function fmt(v: any, suffix = '') {
  return v == null ? '—' : `${v}${suffix}`
}

function deviceLabel(dev: any) {
  if (typeof dev === 'string') return dev
  if (dev?.adapter != null) return `adapter${dev.adapter}: ${(dev.devices || []).join(', ')}`
  return dev?.device || dev?.name || JSON.stringify(dev)
}

async function loadInstances() {
  try {
    const { data } = await http.get('/api/instances')
    instances.value = data || []
    if (selectedInstance.value == null && instances.value.length) {
      selectedInstance.value = instances.value[0].id
    }
  } catch {
    instances.value = []
  }
}

async function load() {
  if (selectedInstance.value == null) return
  loading.value = true
  error.value = ''
  try {
    const id = selectedInstance.value
    const [aRes, sRes] = await Promise.all([
      http.get(`/api/instances/${id}/adapters`),
      http.get(`/api/instances/${id}/adapters/status`),
    ])
    adapters.value = Array.isArray(aRes.data) ? aRes.data : []
    statuses.value = Array.isArray(sRes.data) ? sRes.data : []
  } catch (e: any) {
    adapters.value = []
    statuses.value = []
    error.value = e?.response?.data?.detail || 'Инстанс недоступен'
  } finally {
    loading.value = false
  }
}

async function scanDevices() {
  if (selectedInstance.value == null) return
  scanning.value = true
  error.value = ''
  try {
    const { data } = await http.get(`/api/instances/${selectedInstance.value}/adapters/scan`)
    devices.value = Array.isArray(data) ? data : []
    if (!devices.value.length) error.value = 'DVB-устройства не найдены'
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Ошибка сканирования'
  } finally {
    scanning.value = false
  }
}

async function createAdapter() {
  if (selectedInstance.value == null || !createForm.value.name) return
  creating.value = true
  error.value = ''
  try {
    const body: any = { ...createForm.value }
    if (!body.tp) delete body.tp
    await http.post(`/api/instances/${selectedInstance.value}/adapters`, body)
    showCreate.value = false
    createForm.value = { name: '', adapter: 0, type: 'S2', tp: '', monitor: true }
    await load()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Ошибка создания адаптера'
  } finally {
    creating.value = false
  }
}

async function deleteAdapter(a: any) {
  if (selectedInstance.value == null || actioning.value) return
  actioning.value = true
  error.value = ''
  try {
    await http.delete(`/api/instances/${selectedInstance.value}/adapters/${encodeURIComponent(a.name)}`)
    await load()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Ошибка удаления'
  } finally {
    actioning.value = false
  }
}

async function scanChannels(a: any) {
  if (selectedInstance.value == null || actioning.value) return
  actioning.value = true
  error.value = ''
  const id = selectedInstance.value
  try {
    await http.post(`/api/instances/${id}/adapters/${encodeURIComponent(a.name)}/scan-channels`)
    scanResult.value = { name: a.name, state: 'running', services: [] }
    if (resultTimer) clearInterval(resultTimer)
    resultTimer = setInterval(async () => {
      try {
        const { data } = await http.get(`/api/instances/${id}/adapters/${encodeURIComponent(a.name)}/scan-result`)
        scanResult.value = { name: a.name, state: data?.state, services: data?.result?.services || [] }
        if (data?.state && data.state !== 'running' && resultTimer) {
          clearInterval(resultTimer)
          resultTimer = null
        }
      } catch {
        if (resultTimer) { clearInterval(resultTimer); resultTimer = null }
      }
    }, 3000)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Ошибка запуска поиска'
  } finally {
    actioning.value = false
  }
}

watch(selectedInstance, () => {
  devices.value = []
  scanResult.value = null
  load()
})

onMounted(async () => {
  await loadInstances()
  pollTimer = setInterval(load, 10000)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (resultTimer) clearInterval(resultTimer)
})
</script>
