<template>
  <div class="p-4 sm:p-6 lg:p-8 w-full min-w-0 max-w-7xl 2xl:max-w-[90rem] mx-auto">
    <header class="mb-8">
      <div class="flex flex-wrap items-start justify-between gap-6">
        <div>
          <h1 class="text-2xl font-semibold text-white">Каналы</h1>
          <p class="text-slate-400 mt-1">Все каналы по инстансам Astra</p>
        </div>
        <div class="rounded-xl border border-surface-600 bg-surface-800/80 p-2 flex flex-wrap items-center gap-2">
          <div class="flex items-center gap-2 px-3 py-2 rounded-lg">
            <span class="text-xs text-slate-500 font-medium">Список каналов</span>
            <span class="text-sm font-semibold text-white tabular-nums">{{ channels.length }}</span>
          </div>
          <span class="w-px h-8 bg-surface-600 flex-shrink-0" aria-hidden="true" />
          <div class="flex items-center rounded-lg p-0.5 bg-surface-700/50" role="group" aria-label="Вид">
            <button
              type="button"
              :class="viewMode === 'table' ? 'bg-surface-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-surface-700'"
              class="rounded-md px-4 py-2 text-sm font-medium transition-colors"
              @click="viewMode = 'table'"
            >
              Таблица
            </button>
            <button
              type="button"
              :class="viewMode === 'cards' ? 'bg-surface-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-surface-700'"
              class="rounded-md px-4 py-2 text-sm font-medium transition-colors"
              @click="viewMode = 'cards'"
            >
              Карточки
            </button>
          </div>
          <span class="w-px h-8 bg-surface-600 flex-shrink-0" aria-hidden="true" />
          <label class="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-surface-700/50 transition-colors">
            <input type="checkbox" v-model="groupByInstance" class="rounded border-surface-600 bg-surface-800 text-accent" />
            <span class="text-sm text-slate-400">Группировать по экземпляру</span>
          </label>
          <span class="w-px h-8 bg-surface-600 flex-shrink-0" aria-hidden="true" />
          <button
            type="button"
            @click="load"
            :disabled="loading"
            class="rounded-lg px-4 py-2 text-sm font-medium bg-surface-700 text-slate-300 hover:bg-surface-600 hover:text-white disabled:opacity-50 transition-colors"
          >
            {{ loading ? 'Загрузка…' : 'Обновить' }}
          </button>
        </div>
      </div>
    </header>

    <div v-if="loading && !channels.length" class="flex justify-center py-20">
      <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
    </div>

    <div v-else-if="!channels.length" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
      Нет каналов или инстансы недоступны.
    </div>

    <!-- Таблица -->
    <div v-else-if="viewMode === 'table'" class="w-full min-w-0 overflow-x-auto rounded-xl border border-surface-700 bg-surface-800/60">
      <table class="w-full text-sm" style="table-layout: fixed; min-width: 600px;">
        <colgroup>
          <col style="width: 160px" />
          <col style="width: 112px" />
          <col style="width: 344px" />
          <col style="width: 120px" />
        </colgroup>
        <thead>
          <tr class="border-b border-surface-700 text-left text-slate-400">
            <th class="px-4 py-3.5 font-medium">Имя <span class="ml-1 text-accent">↑</span></th>
            <th class="px-3 py-3.5 font-medium">Превью</th>
            <th class="px-4 py-3.5 font-medium">Output</th>
            <th class="px-4 py-3.5 font-medium pr-5">Действия</th>
          </tr>
        </thead>
        <template v-if="groupByInstance">
          <template v-for="(group, gi) in groupedChannels" :key="group.port">
            <tr :class="gi > 0 ? 'border-t-2 border-surface-600' : ''">
              <td colspan="4" class="px-4 py-3 bg-surface-750/80 border-b border-surface-600">
                <div class="flex items-center gap-3">
                  <span class="w-1 h-6 rounded-full bg-accent flex-shrink-0" aria-hidden="true" />
                  <span class="font-mono font-semibold text-accent">:{{ group.port }}</span>
                  <span class="text-slate-500 text-sm">Экземпляр</span>
                  <span class="text-slate-500 text-sm font-normal tabular-nums">{{ group.channels.length }} {{ pluralChannels(group.channels.length) }}</span>
                </div>
              </td>
            </tr>
            <tr
              v-for="ch in group.channels"
              :key="channelKey(ch)"
              class="border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors"
            >
              <td class="px-4 py-3 align-middle min-h-[72px]">
                <span class="block truncate max-w-full text-white" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</span>
              </td>
              <td class="px-3 py-3 align-middle min-h-[72px]">
                <div class="relative inline-block w-24 h-14 rounded-lg overflow-hidden bg-surface-700 border border-surface-600 flex-shrink-0">
                  <span class="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">—</span>
                </div>
              </td>
              <td class="px-4 py-3 align-middle min-h-[72px]">
                <div class="relative">
                  <template v-if="(ch.output || []).length">
                    <button
                      type="button"
                      class="text-accent hover:underline text-left text-sm"
                      @click.stop="toggleOutputDropdown(channelKey(ch))"
                    >
                      Список адресов выходов ({{ (ch.output || []).length }})
                    </button>
                    <div
                      v-if="expandedOutputKey === channelKey(ch)"
                      class="absolute left-0 top-full mt-1 z-10 min-w-[200px] max-w-[320px] rounded-lg border border-surface-600 bg-surface-800 shadow-xl py-2 max-h-60 overflow-y-auto"
                      @click.stop
                    >
                      <button
                        v-for="(url, i) in (ch.output || [])"
                        :key="i"
                        type="button"
                        class="block w-full text-left px-3 py-1.5 text-sm text-accent hover:bg-surface-700 truncate"
                        :title="url"
                        @click="closeOutputDropdown"
                      >
                        {{ url }}
                      </button>
                    </div>
                  </template>
                  <span v-else class="text-slate-500">—</span>
                </div>
              </td>
              <td class="px-4 py-3 align-middle w-[120px] pr-5">
                <div class="flex gap-1.5 flex-shrink-0">
                  <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                  </button>
                  <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                  </button>
                </div>
              </td>
            </tr>
          </template>
        </template>
        <tbody v-else>
          <tr v-for="ch in channels" :key="channelKey(ch)" class="border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors">
            <td class="px-4 py-3 align-middle min-h-[72px]">
              <span class="block truncate max-w-full text-white" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</span>
            </td>
            <td class="px-3 py-3 align-middle min-h-[72px]">
              <div class="relative inline-block w-24 h-14 rounded-lg overflow-hidden bg-surface-700 border border-surface-600 flex-shrink-0">
                <span class="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">—</span>
              </div>
            </td>
            <td class="px-4 py-3 align-middle min-h-[72px]">
              <div class="relative">
                <template v-if="(ch.output || []).length">
                  <button
                    type="button"
                    class="text-accent hover:underline text-left text-sm"
                    @click.stop="toggleOutputDropdown(channelKey(ch))"
                  >
                    Список адресов выходов ({{ (ch.output || []).length }})
                  </button>
                  <div
                    v-if="expandedOutputKey === channelKey(ch)"
                    class="absolute left-0 top-full mt-1 z-10 min-w-[200px] max-w-[320px] rounded-lg border border-surface-600 bg-surface-800 shadow-xl py-2 max-h-60 overflow-y-auto"
                    @click.stop
                  >
                    <button
                      v-for="(url, i) in (ch.output || [])"
                      :key="i"
                      type="button"
                      class="block w-full text-left px-3 py-1.5 text-sm text-accent hover:bg-surface-700 truncate"
                      :title="url"
                      @click="closeOutputDropdown"
                    >
                      {{ url }}
                    </button>
                  </div>
                </template>
                <span v-else class="text-slate-500">—</span>
              </div>
            </td>
            <td class="px-4 py-3 align-middle w-[120px] pr-5">
              <div class="flex gap-1.5 flex-shrink-0">
                <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                </button>
                <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Карточки -->
    <div v-else class="space-y-6">
      <template v-if="groupByInstance">
        <section v-for="group in groupedChannels" :key="group.port" class="rounded-xl border border-surface-700 bg-surface-800/60">
          <div class="px-4 py-3 flex items-center gap-3 border-b border-surface-700 bg-surface-750/80">
            <span class="w-1 h-5 rounded-full bg-accent flex-shrink-0" />
            <span class="font-mono font-semibold text-accent">:{{ group.port }}</span>
            <span class="text-slate-500 text-sm">Экземпляр · {{ group.channels.length }} {{ pluralChannels(group.channels.length) }}</span>
          </div>
          <div class="p-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <article
              v-for="ch in group.channels"
              :key="channelKey(ch)"
              class="rounded-xl border border-surface-700 bg-surface-750/50 transition-all hover:border-surface-600"
            >
              <p class="p-3 pb-0 font-medium text-white truncate" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</p>
              <div class="p-3">
                <div class="relative w-full aspect-video rounded-xl bg-surface-800 border border-surface-600 overflow-hidden ring-1 ring-black/20 shadow-inner">
                  <span class="absolute inset-0 flex items-center justify-center text-slate-500 text-sm">—</span>
                </div>
              </div>
              <div class="px-3 pb-2 min-h-[2.5rem] flex flex-col justify-center">
                <div class="relative">
                  <template v-if="(ch.output || []).length">
                    <button
                      type="button"
                      class="text-accent hover:underline text-left text-sm"
                      @click.stop="toggleOutputDropdown(channelKey(ch))"
                    >
                      Список адресов выходов ({{ (ch.output || []).length }})
                    </button>
                    <div
                      v-if="expandedOutputKey === channelKey(ch)"
                      class="absolute left-0 top-full mt-1 z-20 min-w-[200px] max-w-[320px] rounded-lg border border-surface-600 bg-surface-800 shadow-xl py-2 max-h-60 overflow-y-auto"
                      @click.stop
                    >
                      <button
                        v-for="(url, i) in (ch.output || [])"
                        :key="i"
                        type="button"
                        class="block w-full text-left px-3 py-1.5 text-sm text-accent hover:bg-surface-700 truncate"
                        :title="url"
                        @click="closeOutputDropdown"
                      >
                        {{ url }}
                      </button>
                    </div>
                  </template>
                  <span v-else class="text-slate-500 text-xs">—</span>
                </div>
              </div>
              <div class="px-3 pb-3 flex gap-2">
                <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                </button>
                <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
                </button>
              </div>
            </article>
          </div>
        </section>
      </template>
      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="ch in channels"
          :key="channelKey(ch)"
          class="rounded-xl border border-surface-700 bg-surface-800/60 transition-all hover:border-surface-600"
        >
          <p class="p-3 pb-0 font-medium text-white truncate" :title="ch.display_name ? `API: ${ch.name}` : ''">{{ ch.display_name || ch.name }}</p>
          <div class="p-3">
            <div class="relative w-full aspect-video rounded-xl bg-surface-800 border border-surface-600 overflow-hidden ring-1 ring-black/20 shadow-inner">
              <span class="absolute inset-0 flex items-center justify-center text-slate-500 text-sm">—</span>
            </div>
          </div>
          <div class="px-3 pb-2 min-h-[2.5rem] flex flex-col justify-center">
            <div class="relative">
              <template v-if="(ch.output || []).length">
                <button
                  type="button"
                  class="text-accent hover:underline text-left text-sm"
                  @click.stop="toggleOutputDropdown(channelKey(ch))"
                >
                  Список адресов выходов ({{ (ch.output || []).length }})
                </button>
                <div
                  v-if="expandedOutputKey === channelKey(ch)"
                  class="absolute left-0 top-full mt-1 z-20 min-w-[200px] max-w-[320px] rounded-lg border border-surface-600 bg-surface-800 shadow-xl py-2 max-h-60 overflow-y-auto"
                  @click.stop
                >
                  <button
                    v-for="(url, i) in (ch.output || [])"
                    :key="i"
                    type="button"
                    class="block w-full text-left px-3 py-1.5 text-sm text-accent hover:bg-surface-700 truncate"
                    :title="url"
                    @click="closeOutputDropdown"
                  >
                    {{ url }}
                  </button>
                </div>
              </template>
              <span v-else class="text-slate-500 text-xs">—</span>
            </div>
          </div>
          <div class="px-3 pb-3 flex gap-2">
            <button type="button" title="Перезапуск" class="rounded-lg bg-surface-700 text-slate-300 p-2 hover:bg-surface-600 disabled:opacity-50" :disabled="actioning" @click="restart(ch)">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            </button>
            <button type="button" title="Отключить" class="rounded-lg bg-danger/20 text-danger border border-danger/40 p-2 hover:bg-danger/30 disabled:opacity-50" :disabled="actioning" @click="kill(ch)">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.36 6.64a9 9 0 11-12.73 0M12 2v10" /></svg>
            </button>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import http from '@/core/api'

const loading = ref(true)
const actioning = ref(false)
const channels = ref<any[]>([])
const viewMode = ref<'table' | 'cards'>('table')
const groupByInstance = ref(false)

const expandedOutputKey = ref<string | null>(null)
let outputDropdownClickOutside: (() => void) | null = null

function channelKey(ch: any) {
  return `${ch.instance_id}:${ch.name}`
}

const groupedChannels = computed(() => {
  const map = new Map<number, any[]>()
  for (const ch of channels.value) {
    const port = ch.instance_port ?? 0
    if (!map.has(port)) map.set(port, [])
    map.get(port)!.push(ch)
  }
  return [...map.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([port, chs]) => ({ port, channels: chs }))
})

function pluralChannels(n: number) {
  if (n === 1) return 'канал'
  if (n >= 2 && n <= 4) return 'канала'
  return 'каналов'
}

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/api/aggregate/channels')
    channels.value = data?.channels || []
  } catch {
    channels.value = []
  } finally {
    loading.value = false
  }
}

function toggleOutputDropdown(key: string) {
  const next = expandedOutputKey.value === key ? null : key
  expandedOutputKey.value = next
  if (outputDropdownClickOutside) {
    document.removeEventListener('click', outputDropdownClickOutside)
    outputDropdownClickOutside = null
  }
  if (next) {
    nextTick(() => {
      outputDropdownClickOutside = () => {
        expandedOutputKey.value = null
        if (outputDropdownClickOutside) document.removeEventListener('click', outputDropdownClickOutside)
        outputDropdownClickOutside = null
      }
      setTimeout(() => { if (outputDropdownClickOutside) document.addEventListener('click', outputDropdownClickOutside) }, 0)
    })
  }
}

function closeOutputDropdown() {
  expandedOutputKey.value = null
  if (outputDropdownClickOutside) {
    document.removeEventListener('click', outputDropdownClickOutside)
    outputDropdownClickOutside = null
  }
}

async function restart(ch: any) {
  if (!ch || actioning.value) return
  actioning.value = true
  try {
    await http.post(`/api/instances/${ch.instance_id}/channels/${encodeURIComponent(ch.name)}/restart`)
  } catch (err: any) {
    console.error('Restart failed', err)
  } finally {
    actioning.value = false
  }
}

async function kill(ch: any) {
  if (!ch || actioning.value) return
  actioning.value = true
  try {
    await http.post(`/api/instances/${ch.instance_id}/channels/${encodeURIComponent(ch.name)}/stop`)
  } catch (err: any) {
    console.error('Stop failed', err)
  } finally {
    actioning.value = false
  }
}

onMounted(load)
</script>
