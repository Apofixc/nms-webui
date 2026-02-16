<template>
  <div class="p-8 max-w-7xl mx-auto">
    <header class="mb-8 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-white">Каналы</h1>
        <p class="text-slate-400 mt-1">Все каналы по инстансам Astra</p>
      </div>
      <div class="flex flex-wrap items-center gap-4">
        <span class="text-sm text-slate-400">Всего каналов: <strong class="text-white">{{ channels.length }}</strong></span>
        <button
          type="button"
          @click="load"
          :disabled="loading"
          class="rounded-lg bg-surface-700 text-slate-300 px-4 py-2 text-sm font-medium hover:bg-surface-600 disabled:opacity-50"
        >
          {{ loading ? 'Загрузка…' : 'Обновить' }}
        </button>
      </div>
    </header>

    <div v-if="channels.length" class="mb-4 flex flex-wrap items-center gap-4 text-sm">
      <label class="flex items-center gap-2 text-slate-400 cursor-pointer">
        <input type="checkbox" v-model="groupByInstance" class="rounded border-surface-600 bg-surface-800 text-accent" />
        <span>Группировать по экземпляру</span>
      </label>
    </div>

    <div v-if="loading && !channels.length" class="flex justify-center py-20">
      <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
    </div>

    <div v-else-if="!channels.length" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
      Нет каналов или инстансы недоступны.
    </div>

    <div v-else class="rounded-xl border border-surface-700 bg-surface-800/60 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-surface-700 text-left text-slate-400">
            <th
              class="px-4 py-3 font-medium cursor-pointer select-none hover:text-white"
              @click="cycleSort"
            >
              Имя
              <span v-if="sortByName" class="ml-1 text-accent">{{ sortByName === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="px-4 py-3 font-medium">Output</th>
            <th class="px-4 py-3 font-medium w-36">Действия</th>
          </tr>
        </thead>
        <template v-if="groupByInstance">
          <template v-for="group in groupedChannels" :key="group.port">
            <tr class="bg-surface-750/50">
              <td colspan="3" class="px-4 py-2 font-mono text-accent">:{{ group.port }}</td>
            </tr>
            <tr
              v-for="ch in group.channels"
              :key="ch.instance_id + ':' + ch.name"
              class="border-t border-surface-700/50 hover:bg-surface-750/30"
            >
              <td class="px-4 py-2 align-top">
                <span
                  class="relative inline-block text-white cursor-help"
                  :title="ch.display_name ? `API: ${ch.name}` : ''"
                  @mouseenter="(e) => { previewTarget = ch; setPreviewPos(e) }"
                  @mouseleave="previewTarget = null"
                >
                  {{ ch.display_name || ch.name }}
                  <Teleport to="body">
                    <div
                      v-if="previewTarget === ch"
                      class="fixed z-50 rounded-lg border border-surface-600 bg-surface-800 shadow-xl p-3 max-w-xs pointer-events-none"
                      :style="previewStyle"
                    >
                      <p class="text-slate-500 text-xs">Превью по каналу</p>
                      <p class="text-slate-400 text-xs mt-1">Скриншот: API не реализован</p>
                    </div>
                  </Teleport>
                </span>
              </td>
              <td class="px-4 py-2 align-top">
                <template v-if="(ch.output || []).length">
                  <a
                    v-for="(url, i) in (ch.output || [])"
                    :key="i"
                    :href="isHttpUrl(url) ? url : '#'"
                    :title="url"
                    target="_blank"
                    rel="noopener"
                    class="block text-accent hover:underline truncate max-w-md"
                    @click="!isHttpUrl(url) && ($event.preventDefault(), copyUrl(url))"
                  >
                    {{ url }}
                  </a>
                </template>
                <span v-else class="text-slate-500">—</span>
              </td>
              <td class="px-4 py-2 align-top">
                <div class="flex gap-1">
                  <button
                    type="button"
                    title="Перезапуск"
                    class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50"
                    :disabled="actioning"
                    @click="restart(ch)"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    title="Отключить"
                    class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50"
                    :disabled="actioning"
                    @click="kill(ch)"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    title="Switch Input"
                    class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50"
                    :disabled="actioning"
                    @click="switchInput(ch)"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </template>
        </template>
        <tbody v-else>
          <tr
            v-for="ch in sortedChannels"
            :key="ch.instance_id + ':' + ch.name"
            class="border-t border-surface-700/50 hover:bg-surface-750/30"
          >
            <td class="px-4 py-2 align-top">
              <span
                class="relative inline-block text-white cursor-help"
                :title="ch.display_name ? `API: ${ch.name}` : ''"
                @mouseenter="(e) => { previewTarget = ch; setPreviewPos(e) }"
                @mouseleave="previewTarget = null"
              >
                {{ ch.display_name || ch.name }}
                <Teleport to="body">
                  <div
                    v-if="previewTarget === ch"
                    class="fixed z-50 rounded-lg border border-surface-600 bg-surface-800 shadow-xl p-3 max-w-xs pointer-events-none"
                    :style="previewStyle"
                  >
                    <p class="text-slate-500 text-xs">Превью по каналу</p>
                    <p class="text-slate-400 text-xs mt-1">Скриншот: API не реализован</p>
                  </div>
                </Teleport>
              </span>
            </td>
            <td class="px-4 py-2 align-top">
              <template v-if="(ch.output || []).length">
                <a
                  v-for="(url, i) in (ch.output || [])"
                  :key="i"
                  :href="isHttpUrl(url) ? url : '#'"
                  :title="url"
                  target="_blank"
                  rel="noopener"
                  class="block text-accent hover:underline truncate max-w-md"
                  @click="!isHttpUrl(url) && ($event.preventDefault(), copyUrl(url))"
                >
                  {{ url }}
                </a>
              </template>
              <span v-else class="text-slate-500">—</span>
            </td>
            <td class="px-4 py-2 align-top">
              <div class="flex gap-1">
                <button
                  type="button"
                  title="Перезапуск"
                  class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50"
                  :disabled="actioning"
                  @click="restart(ch)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </button>
                <button
                  type="button"
                  title="Отключить"
                  class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50"
                  :disabled="actioning"
                  @click="kill(ch)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" />
                  </svg>
                </button>
                <button
                  type="button"
                  title="Switch Input"
                  class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50"
                  :disabled="actioning"
                  @click="switchInput(ch)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'

const loading = ref(true)
const actioning = ref(false)
const channels = ref([])
const sortByName = ref('asc')
const groupByInstance = ref(false)
const previewTarget = ref(null)
const previewStyle = ref({})

function cycleSort() {
  if (sortByName.value === '') sortByName.value = 'asc'
  else if (sortByName.value === 'asc') sortByName.value = 'desc'
  else sortByName.value = ''
}

function isHttpUrl(s) {
  return typeof s === 'string' && (s.startsWith('http://') || s.startsWith('https://'))
}

function copyUrl(url) {
  if (navigator.clipboard) navigator.clipboard.writeText(url)
  else alert(url)
}

function setPreviewPos(e) {
  const el = e.currentTarget
  if (!el) return
  const r = el.getBoundingClientRect()
  previewStyle.value = { left: `${r.left}px`, top: `${r.bottom + 6}px` }
}

const sortedChannels = computed(() => {
  const list = [...channels.value]
  const key = (c) => (c.display_name || c.name || '')
  if (sortByName.value === 'asc') list.sort((a, b) => key(a).localeCompare(key(b)))
  else if (sortByName.value === 'desc') list.sort((a, b) => key(b).localeCompare(key(a)))
  return list
})

const groupedChannels = computed(() => {
  const byPort = new Map()
  for (const ch of sortedChannels.value) {
    const port = ch.instance_port
    if (!byPort.has(port)) byPort.set(port, { port, channels: [] })
    byPort.get(port).channels.push(ch)
  }
  return Array.from(byPort.values())
})

async function load() {
  loading.value = true
  try {
    const res = await api.aggregateChannels()
    channels.value = res.channels || []
  } catch {
    channels.value = []
  } finally {
    loading.value = false
  }
}

async function restart(ch) {
  actioning.value = true
  try {
    await api.channelKill(ch.instance_id, ch.name, true)
    await load()
  } catch (e) {
    alert(e.message)
  } finally {
    actioning.value = false
  }
}

async function kill(ch) {
  actioning.value = true
  try {
    await api.channelKill(ch.instance_id, ch.name, false)
    await load()
  } catch (e) {
    alert(e.message)
  } finally {
    actioning.value = false
  }
}

async function switchInput(ch) {
  actioning.value = true
  try {
    const data = await api.channelInputs(ch.instance_id, ch.name)
    if (data?.inputs?.length > 1) {
      alert(`Входов: ${data.inputs.length}, активный: ${data.active_input ?? 0}. Переключение — через API Astra.`)
    } else {
      alert('Один вход или данных нет.')
    }
  } catch (e) {
    alert(e.message)
  } finally {
    actioning.value = false
  }
}

onMounted(load)
</script>
