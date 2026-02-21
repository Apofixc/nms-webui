<template>
  <div class="p-4 sm:p-6 lg:p-8 w-full min-w-0 max-w-6xl 2xl:max-w-7xl mx-auto">
    <header class="mb-8">
      <h1 class="text-2xl font-semibold text-white">Управление экземплярами</h1>
      <p class="text-slate-400 mt-1">Добавление из конфига, автосканирование портов и ручной ввод</p>
    </header>

    <!-- Лог событий (down/recovered): хранится до N последних, старые удаляются -->
    <div v-if="events.length" class="mb-6">
      <div class="flex items-center justify-between gap-3 mb-2">
        <p class="text-sm text-slate-400">
          События доступности: {{ events.length }} из {{ eventsLimit }} (старые удаляются автоматически)
        </p>
        <button
          type="button"
          @click="clearEvents"
          class="text-sm text-slate-400 hover:text-white"
        >
          Очистить
        </button>
      </div>
      <div class="space-y-2">
        <div
          v-for="(ev, idx) in events"
          :key="idx"
          role="button"
          tabindex="0"
          @click="dismissEvent(idx)"
          @keydown.enter="dismissEvent(idx)"
          class="rounded-lg border px-4 py-2 text-sm flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
          :class="ev.event === 'down' ? 'bg-danger/10 border-danger/40 text-danger' : 'bg-success/10 border-success/40 text-success'"
        >
          <span class="font-medium">{{ ev.label || `:${ev.port}` }}</span>
          <span>{{ ev.event === 'down' ? 'Недоступен' : 'Восстановлен' }}</span>
          <span class="text-slate-500 text-xs">{{ formatTime(ev.at) }}</span>
          <span class="ml-auto text-slate-500 text-xs">клик — убрать</span>
        </div>
      </div>
    </div>

    <!-- Кнопки и настройка интервала -->
    <div class="flex flex-wrap items-center gap-4 mb-8">
      <button
        type="button"
        @click="showScanModal = true"
        class="rounded-lg bg-accent/20 text-accent border border-accent/50 px-4 py-2 font-medium hover:bg-accent/30"
      >
        Сканировать порты
      </button>
      <button
        type="button"
        @click="showManualModal = true"
        class="rounded-lg bg-accent/20 text-accent border border-accent/50 px-4 py-2 font-medium hover:bg-accent/30"
      >
        Добавить вручную
      </button>
      <div class="flex items-center gap-2 ml-auto">
        <label class="text-sm text-slate-400">Интервал проверки:</label>
        <input
          v-model.number="checkIntervalInput"
          type="number"
          min="5"
          max="600"
          class="w-20 rounded-lg bg-surface-900 border border-surface-600 px-2 py-1.5 text-white text-sm focus:border-accent outline-none"
        />
        <span class="text-sm text-slate-500">сек</span>
        <button
          type="button"
          @click="applyCheckInterval"
          :disabled="savingInterval"
          class="rounded-lg bg-surface-700 text-slate-300 px-3 py-1.5 text-sm hover:bg-surface-600 disabled:opacity-50"
        >
          Применить
        </button>
      </div>
    </div>

    <!-- Модальное окно: Сканирование -->
    <div v-if="showScanModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" @click.self="showScanModal = false">
      <div class="rounded-2xl bg-surface-800 border border-surface-600 shadow-xl w-full max-w-md p-6" @click.stop>
        <h2 class="text-lg font-medium text-white mb-4">Сканирование портов</h2>
        <form @submit.prevent="runScan" class="space-y-4">
          <div>
            <label class="block text-sm text-slate-400 mb-1">Хост</label>
            <input
              v-model="scan.host"
              type="text"
              placeholder="127.0.0.1"
              class="w-full rounded-lg bg-surface-900 border border-surface-600 px-3 py-2 text-white placeholder-slate-500 focus:border-accent outline-none"
            />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm text-slate-400 mb-1">Порт от</label>
              <input
                v-model.number="scan.port_start"
                type="number"
                min="1"
                max="65535"
                class="w-full rounded-lg bg-surface-900 border border-surface-600 px-3 py-2 text-white focus:border-accent outline-none"
              />
            </div>
            <div>
              <label class="block text-sm text-slate-400 mb-1">Порт до</label>
              <input
                v-model.number="scan.port_end"
                type="number"
                min="1"
                max="65535"
                class="w-full rounded-lg bg-surface-900 border border-surface-600 px-3 py-2 text-white focus:border-accent outline-none"
              />
            </div>
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">API Key</label>
            <input
              v-model="scan.api_key"
              type="text"
              placeholder="test"
              class="w-full rounded-lg bg-surface-900 border border-surface-600 px-3 py-2 text-white placeholder-slate-500 focus:border-accent outline-none"
            />
          </div>
          <p v-if="scanResult" class="text-sm text-slate-400">
            Найдено: {{ scanResult.found?.length || 0 }}, добавлено: {{ scanResult.added?.length || 0 }}
          </p>
          <div class="flex gap-2 pt-2">
            <button
              type="submit"
              :disabled="scanning"
              class="rounded-lg bg-accent/20 text-accent border border-accent/50 px-4 py-2 font-medium hover:bg-accent/30 disabled:opacity-50"
            >
              {{ scanning ? 'Сканирование…' : 'Сканировать' }}
            </button>
            <button type="button" @click="showScanModal = false" class="rounded-lg bg-surface-700 text-slate-300 px-4 py-2 font-medium hover:bg-surface-600">
              Закрыть
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Модальное окно: Ручное добавление -->
    <div v-if="showManualModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" @click.self="showManualModal = false">
      <div class="rounded-2xl bg-surface-800 border border-surface-600 shadow-xl w-full max-w-md p-6" @click.stop>
        <h2 class="text-lg font-medium text-white mb-4">Добавить инстанс</h2>
        <form @submit.prevent="addManual" class="space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm text-slate-400 mb-1">Хост</label>
              <input
                v-model="manual.host"
                type="text"
                placeholder="127.0.0.1"
                class="w-full rounded-lg bg-surface-900 border border-surface-600 px-3 py-2 text-white placeholder-slate-500 focus:border-accent outline-none"
              />
            </div>
            <div>
              <label class="block text-sm text-slate-400 mb-1">Порт</label>
              <input
                v-model.number="manual.port"
                type="number"
                min="1"
                max="65535"
                class="w-full rounded-lg bg-surface-900 border border-surface-600 px-3 py-2 text-white focus:border-accent outline-none"
              />
            </div>
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">API Key</label>
            <input
              v-model="manual.api_key"
              type="text"
              placeholder="test"
              class="w-full rounded-lg bg-surface-900 border border-surface-600 px-3 py-2 text-white placeholder-slate-500 focus:border-accent outline-none"
            />
          </div>
          <div>
            <label class="block text-sm text-slate-400 mb-1">Подпись (необязательно)</label>
            <input
              v-model="manual.label"
              type="text"
              placeholder="Astra local"
              class="w-full rounded-lg bg-surface-900 border border-surface-600 px-3 py-2 text-white placeholder-slate-500 focus:border-accent outline-none"
            />
          </div>
          <p v-if="addError" class="text-sm text-danger">{{ addError }}</p>
          <div class="flex gap-2 pt-2">
            <button
              type="submit"
              :disabled="adding"
              class="rounded-lg bg-accent/20 text-accent border border-accent/50 px-4 py-2 font-medium hover:bg-accent/30 disabled:opacity-50"
            >
              {{ adding ? 'Добавление…' : 'Добавить' }}
            </button>
            <button type="button" @click="showManualModal = false" class="rounded-lg bg-surface-700 text-slate-300 px-4 py-2 font-medium hover:bg-surface-600">
              Закрыть
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Список инстансов со статусом -->
    <section>
      <h2 class="text-lg font-medium text-white mb-4">Инстансы в конфиге</h2>
      <div v-if="loading && !statusInstances.length" class="flex justify-center py-20">
        <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
      </div>
      <div v-else-if="!statusInstances.length" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
        Нет инстансов. Добавьте через скан или вручную.
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="inst in statusInstances"
          :key="inst.id"
          class="rounded-xl border border-surface-700 bg-surface-800/60 p-4 flex items-center justify-between flex-wrap gap-3"
        >
          <div class="flex items-center gap-3">
            <span
              class="w-3 h-3 rounded-full flex-shrink-0"
              :class="inst.reachable === true ? 'bg-success' : inst.reachable === false ? 'bg-danger' : 'bg-slate-500'"
            />
            <span class="font-mono text-accent">:{{ inst.port }}</span>
            <span class="font-medium text-white">{{ inst.label }}</span>
            <span class="text-sm text-slate-500">{{ inst.host }}</span>
            <span v-if="inst.last_check" class="text-xs text-slate-500">проверка {{ formatTime(inst.last_check) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <a :href="`http://${inst.host}:${inst.port}/`" target="_blank" rel="noopener" class="text-sm text-accent hover:underline">API</a>
            <button
              type="button"
              @click="removeInstance(inst.id)"
              class="text-sm text-danger hover:underline"
            >
              Удалить
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../api'

const loading = ref(true)
const statusInstances = ref([])
const events = ref([])
const eventsLimit = ref(50)
const checkIntervalInput = ref(30)
const savingInterval = ref(false)
const showScanModal = ref(false)
const showManualModal = ref(false)
let intervalId = null

const scan = ref({ host: '127.0.0.1', port_start: 8080, port_end: 8090, api_key: 'test' })
const scanning = ref(false)
const scanResult = ref(null)

const manual = ref({ host: '127.0.0.1', port: 8080, api_key: 'test', label: '' })
const adding = ref(false)
const addError = ref('')

function formatTime(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString()
  } catch {
    return iso
  }
}

async function loadStatus() {
  try {
    const res = await api.instancesStatus()
    statusInstances.value = res.instances || []
    events.value = res.events || []
    if (res.events_limit != null) eventsLimit.value = res.events_limit
    if (res.check_interval_sec != null) checkIntervalInput.value = res.check_interval_sec
  } catch {
    statusInstances.value = []
    events.value = []
  } finally {
    loading.value = false
  }
}

async function applyCheckInterval() {
  const sec = Number(checkIntervalInput.value)
  if (sec < 5 || sec > 600) return
  savingInterval.value = true
  try {
    await api.setCheckInterval(sec)
  } finally {
    savingInterval.value = false
  }
}

async function clearEvents() {
  try {
    await api.clearStatusEvents()
    events.value = []
  } catch {
    // ignore
  }
}

async function dismissEvent(index) {
  try {
    await api.removeStatusEvent(index)
    events.value = events.value.filter((_, i) => i !== index)
  } catch {
    // ignore
  }
}

async function runScan() {
  scanning.value = true
  scanResult.value = null
  try {
    const res = await api.instanceScan({
      host: scan.value.host,
      port_start: scan.value.port_start,
      port_end: scan.value.port_end,
      api_key: scan.value.api_key || 'test',
    })
    scanResult.value = res
    await loadStatus()
  } catch (e) {
    scanResult.value = { error: e.message }
  } finally {
    scanning.value = false
  }
}

async function addManual() {
  adding.value = true
  addError.value = ''
  try {
    await api.instanceCreate({
      host: manual.value.host,
      port: Number(manual.value.port),
      api_key: manual.value.api_key || 'test',
      label: manual.value.label || undefined,
    })
    await loadStatus()
    showManualModal.value = false
  } catch (e) {
    addError.value = e.message || 'Ошибка добавления'
  } finally {
    adding.value = false
  }
}

async function removeInstance(id) {
  if (!confirm('Удалить инстанс из конфига?')) return
  try {
    await api.instanceDelete(id)
    await loadStatus()
  } catch (e) {
    addError.value = e.message || 'Ошибка удаления'
  }
}

onMounted(() => {
  loadStatus()
  intervalId = setInterval(loadStatus, 8000)
})
onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>
