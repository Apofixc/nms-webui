<template>
  <div class="p-4 sm:p-6 lg:p-8 w-full min-w-0 max-w-6xl 2xl:max-w-7xl mx-auto">
    <header class="mb-8">
      <div class="flex items-center gap-2">
        <h1 class="text-2xl font-semibold text-white">Общая информация</h1>
        <button
          type="button"
          :aria-expanded="showTelegrafHint"
          :title="showTelegrafHint ? 'Свернуть подсказку' : 'Как настроить Telegraf'"
          @click="showTelegrafHint = !showTelegrafHint"
          class="flex-shrink-0 w-7 h-7 rounded-full border border-surface-600 bg-surface-800 text-slate-400 hover:text-white hover:border-surface-500 flex items-center justify-center text-sm font-medium transition-colors"
        >
          ?
        </button>
      </div>
      <p class="text-slate-400 mt-1">Состояние инстансов Astra: каналы, мониторы, тюнеры, ресурсы</p>

      <div
        v-show="showTelegrafHint"
        class="mt-4 rounded-xl border border-surface-600 bg-surface-800/80 p-4 text-sm text-slate-300 space-y-3"
      >
        <p class="font-medium text-white">Как настроить Telegraf для связи с NMS</p>
        <p>Метрики системы (CPU, память, диск) отображаются при получении данных из Telegraf. Telegraf может работать на том же сервере, что и Astra, или на отдельном — в обоих случаях настройте сбор и отправку метрик в NMS.</p>
        <ul class="list-disc list-inside space-y-1 text-slate-400">
          <li>Установите Telegraf на хост, метрики которого нужны (тот же сервер, что и NMS, или в одной сети).</li>
          <li>Включите inputs: <code class="bg-surface-700 px-1 rounded">cpu</code>, <code class="bg-surface-700 px-1 rounded">mem</code>, <code class="bg-surface-700 px-1 rounded">disk</code>, <code class="bg-surface-700 px-1 rounded">system</code> (load).</li>
          <li>Добавьте output <code class="bg-surface-700 px-1 rounded">[[outputs.http]]</code> с URL NMS: <code class="bg-surface-700 px-1 rounded">url = "http://127.0.0.1:9000/api/system/metrics"</code> (или адрес хоста NMS). Можно оставить output в InfluxDB — Telegraf шлёт данные всем получателям одновременно.</li>
        </ul>
        <p class="text-slate-500 text-xs">Telegraf отправляет данные в NMS (push). Настройте в Telegraf второй output — HTTP на URL NMS (например <code class="bg-surface-700 px-1 rounded">http://127.0.0.1:9000/api/system/metrics</code>). NMS не обращается к удалённым серверам.</p>
        <button
          type="button"
          @click="showTelegrafHint = false"
          class="text-slate-500 hover:text-slate-400 text-xs"
        >
          Свернуть
        </button>
      </div>
    </header>

    <!-- Блок системных метрик (от Telegraf push), по запросу при открытии вкладки -->
    <section
      v-if="systemInfo.available && hasSystemMetrics"
      class="mb-8 rounded-2xl border border-surface-700 bg-surface-800/60 p-5"
    >
      <h2 class="text-lg font-medium text-white mb-4">Система (хост)</h2>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
        <div v-if="systemInfo.cpu_usage_percent != null" class="text-slate-400">
          <span class="block text-slate-500">CPU</span>
          <span class="text-slate-300 font-mono">{{ systemInfo.cpu_usage_percent }}%</span>
        </div>
        <div v-if="systemInfo.mem_used_percent != null" class="text-slate-400">
          <span class="block text-slate-500">Память</span>
          <span class="text-slate-300 font-mono">{{ systemInfo.mem_used_percent }}%</span>
          <span v-if="systemInfo.mem_total_kb" class="text-slate-500 text-xs"> ({{ memFmt(systemInfo.mem_used_kb, systemInfo.mem_total_kb) }})</span>
        </div>
        <div v-if="systemInfo.disk_used_percent != null" class="text-slate-400">
          <span class="block text-slate-500">Диск</span>
          <span class="text-slate-300 font-mono">{{ systemInfo.disk_used_percent }}%</span>
        </div>
        <div v-if="systemInfo.load1 != null" class="text-slate-400">
          <span class="block text-slate-500">Load (1/5/15)</span>
          <span class="text-slate-300 font-mono">{{ systemInfo.load1?.toFixed(2) ?? '—' }} / {{ systemInfo.load5?.toFixed(2) ?? '—' }} / {{ systemInfo.load15?.toFixed(2) ?? '—' }}</span>
        </div>
      </div>
    </section>

    <div v-if="loading && !instances.length" class="flex justify-center py-20">
      <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
    </div>

    <div v-else-if="!instances.length" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center">
      <p class="text-slate-400">Нет инстансов.</p>
      <p class="text-sm text-slate-500 mt-2">Добавьте их на вкладке <router-link to="/instances" class="text-accent hover:underline">Управление экземплярами</router-link>.</p>
    </div>

    <div v-else class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <article
        v-for="inst in instances"
        :key="inst.id"
        class="rounded-2xl border bg-surface-800/60 overflow-hidden transition-all duration-300 hover:shadow-card hover:border-surface-700"
        :class="inst.reachable ? 'border-surface-700' : 'border-danger/30'"
      >
        <div class="p-5 flex items-start justify-between">
          <div class="flex items-center gap-3">
            <span
              class="w-3 h-3 rounded-full flex-shrink-0"
              :class="inst.reachable ? 'bg-success shadow-[0_0_8px_rgba(52,211,153,0.5)] animate-pulse-soft' : 'bg-danger'"
            />
            <div>
              <h2 class="font-semibold text-white">{{ inst.label }}</h2>
              <p class="text-sm text-slate-500 font-mono">:{{ inst.port }}</p>
            </div>
          </div>
          <span
            class="text-xs font-medium px-2.5 py-1 rounded-full"
            :class="inst.reachable ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'"
          >
            {{ inst.reachable ? 'Online' : 'Offline' }}
          </span>
        </div>

        <template v-if="inst.reachable && inst.data">
          <div class="px-5 pb-4 space-y-3 text-sm">
            <div class="flex justify-between text-slate-400">
              <span>Hostname</span>
              <span class="text-slate-300 font-mono">{{ inst.data.hostname || '—' }}</span>
            </div>
            <div class="flex justify-between text-slate-400">
              <span>Astra</span>
              <span class="text-slate-300 font-mono">{{ inst.data.astra_version || '—' }}</span>
            </div>
            <div class="flex justify-between text-slate-400">
              <span>Время сервера</span>
              <span class="text-slate-300">{{ inst.data.server_time || '—' }}</span>
            </div>
            <div class="flex justify-between text-slate-400">
              <span>Uptime</span>
              <span class="text-slate-300">{{ inst.data.uptime_human || '—' }}</span>
            </div>
            <div v-if="inst.data.stats" class="grid grid-cols-2 gap-2">
              <div class="flex justify-between text-slate-400">
                <span>Каналы</span>
                <span class="text-slate-300 font-mono">{{ inst.data.stats.active_channels ?? '—' }}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>Мониторы</span>
                <span class="text-slate-300 font-mono">{{ inst.monitors_count ?? '—' }}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>Адаптеры</span>
                <span class="text-slate-300 font-mono">{{ inst.data.stats.active_adapters ?? '—' }}</span>
              </div>
            </div>
            <div v-if="inst.data.resources" class="pt-2 border-t border-surface-700 grid grid-cols-2 gap-2">
              <div class="flex justify-between text-slate-400">
                <span>PID</span>
                <span class="text-slate-300 font-mono">{{ inst.data.resources.pid ?? '—' }}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>Потоки</span>
                <span class="text-slate-300 font-mono">{{ inst.data.resources.cpu?.threads ?? '—' }}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>CPU %</span>
                <span class="text-slate-300 font-mono">{{ cpuUsage(inst.data.resources) }}</span>
              </div>
              <div class="flex justify-between text-slate-400 col-span-2">
                <span>Память (RSS)</span>
                <span class="text-slate-300 font-mono">{{ memoryFmt(inst.data.resources) }}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>Память Lua</span>
                <span class="text-slate-300 font-mono">{{ luaMemFmt(inst.data.resources) }}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>Память (virtual)</span>
                <span class="text-slate-300 font-mono">{{ virtualMemFmt(inst.data.resources) }}</span>
              </div>
            </div>
          </div>
          <div class="px-5 pb-5 pt-2 border-t border-surface-700 flex justify-between items-center gap-2">
            <button
              type="button"
              title="Очистить метрики"
              @click="clearCache(inst)"
              :disabled="clearCacheLoading === inst.id"
              class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50"
            >
              <svg v-if="clearCacheLoading !== inst.id" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              <span v-else class="inline-block w-5 h-5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
            </button>
            <div class="flex gap-2">
              <button
                type="button"
                title="Перезагрузка"
                @click="openActionModal(inst, 'reload')"
                class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
              <button
                type="button"
                title="Выключить"
                @click="openActionModal(inst, 'exit')"
                class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" />
                </svg>
              </button>
            </div>
          </div>
        </template>
        <div v-else-if="!inst.reachable" class="px-5 pb-5 text-sm text-slate-500">
          Нет данных (инстанс недоступен)
        </div>
      </article>
    </div>

    <!-- Модальное окно: перезагрузка / выключение с таймером -->
    <div v-if="actionModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" @click.self="actionModal = null">
      <div class="rounded-2xl bg-surface-800 border border-surface-600 shadow-xl w-full max-w-sm p-6" @click.stop>
        <h3 class="text-lg font-medium text-white mb-2">
          {{ actionModal.action === 'reload' ? 'Перезагрузка' : 'Выключение' }} — {{ actionModal.inst.label }}
        </h3>
        <p class="text-sm text-slate-400 mb-4">
          {{ actionModal.action === 'reload' ? 'Перезагрузка Astra' : 'Выключение процесса' }} через
          <strong class="text-white">{{ actionModal.delay }}</strong> сек после подтверждения.
        </p>
        <div class="flex gap-2 mb-4">
          <label class="text-sm text-slate-400">Задержка (сек):</label>
          <select
            v-model.number="actionModal.delay"
            class="rounded bg-surface-900 border border-surface-600 px-2 py-1 text-white text-sm"
          >
            <option :value="5">5</option>
            <option :value="10">10</option>
            <option :value="30">30</option>
            <option :value="60">60</option>
          </select>
        </div>
        <div class="flex gap-2">
          <button
            type="button"
            @click="confirmAction"
            :disabled="actionModal?.sending"
            class="flex-1 rounded-lg bg-accent/20 text-accent border border-accent/50 px-4 py-2 font-medium hover:bg-accent/30 disabled:opacity-50"
          >
            {{ actionModal?.sending ? 'Выполняется…' : 'Подтвердить' }}
          </button>
          <button
            type="button"
            @click="actionModal = null"
            class="rounded-lg bg-surface-700 text-slate-300 px-4 py-2 font-medium hover:bg-surface-600"
          >
            Отмена
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../api'

const loading = ref(true)
const instances = ref([])
const actionModal = ref(null)
const clearCacheLoading = ref(null)
const showTelegrafHint = ref(false)
const systemInfo = ref({ available: false })
let intervalId = null

const hasSystemMetrics = computed(() => {
  const s = systemInfo.value
  return s.available && (s.cpu_usage_percent != null || s.mem_used_percent != null || s.disk_used_percent != null || s.load1 != null)
})

function memFmt(usedKb, totalKb) {
  if (usedKb == null || totalKb == null) return ''
  const u = Number(usedKb) / 1024
  const t = Number(totalKb) / 1024
  const uStr = t >= 1024 ? `${(u / 1024).toFixed(1)} GB` : `${Math.round(u)} MB`
  const tStr = t >= 1024 ? `${(t / 1024).toFixed(1)} GB` : `${Math.round(t)} MB`
  return `${uStr} / ${tStr}`
}

function cpuUsage(res) {
  if (!res?.cpu) return '—'
  const u = res.cpu.usage
  return typeof u === 'number' ? `${u.toFixed(1)}%` : '—'
}

function memoryFmt(res) {
  if (!res?.memory?.resident) return '—'
  const mb = res.memory.resident / 1024
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${Math.round(mb)} MB`
}

function luaMemFmt(res) {
  const kb = res?.lua_mem_kb ?? res?.memory?.lua
  if (kb == null) return '—'
  const n = Number(kb)
  if (n >= 1024) return `${(n / 1024).toFixed(1)} MB`
  return `${Math.round(n)} KB`
}

function virtualMemFmt(res) {
  const v = res?.memory?.virtual
  if (v == null) return '—'
  const kb = Number(v)
  const mb = kb / 1024
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${Math.round(mb)} MB`
}

function openActionModal(inst, action) {
  actionModal.value = { inst, action, delay: 10, sending: false }
}

async function confirmAction() {
  if (!actionModal.value?.inst) return
  const { inst, action, delay } = actionModal.value
  actionModal.value.sending = true
  try {
    if (action === 'reload') {
      await api.instanceSystemReload(inst.id, delay)
    } else {
      await api.instanceSystemExit(inst.id, delay)
    }
    actionModal.value = null
    await load()
  } catch (e) {
    actionModal.value.sending = false
    actionModal.value.error = e.message || 'Ошибка'
  }
}

async function clearCache(inst) {
  if (inst?.id == null) return
  clearCacheLoading.value = inst.id
  try {
    await api.instanceSystemClearCache(inst.id)
    await load()
  } catch {
    // ignore
  } finally {
    clearCacheLoading.value = null
  }
}

async function load() {
  loading.value = true
  try {
    const res = await api.instancesStatus()
    instances.value = res.instances || []
  } catch {
    instances.value = []
  } finally {
    loading.value = false
  }
}

async function loadSystemInfo() {
  try {
    const res = await api.systemInfo()
    systemInfo.value = res || { available: false }
  } catch {
    systemInfo.value = { available: false }
  }
}

onMounted(() => {
  loadSystemInfo()
  load()
  intervalId = setInterval(load, 10000)
})
onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>
