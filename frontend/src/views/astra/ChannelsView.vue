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
          <col style="width: 40%" />
          <col style="width: 20%" />
          <col style="width: 20%" />
          <col style="width: 20%" />
        </colgroup>
        <thead>
          <tr class="border-b border-surface-700 text-left text-slate-400">
            <th class="px-4 py-3.5 font-medium">Имя</th>
            <th class="px-4 py-3.5 font-medium">ID</th>
            <th class="px-4 py-3.5 font-medium text-center">Экземпляр</th>
            <th class="px-4 py-3.5 font-medium text-center">Порт</th>
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
              :key="ch.instance_id + ':' + ch.name"
              class="border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors"
            >
              <td class="px-4 py-3">
                <span class="block truncate max-w-full text-white" :title="ch.name">{{ ch.display_name || ch.name }}</span>
              </td>
              <td class="px-4 py-3 text-slate-500 font-mono text-xs">{{ ch.id || '—' }}</td>
              <td class="px-4 py-3 text-center">
                <span class="text-xs text-accent">#{{ ch.instance_id }}</span>
              </td>
              <td class="px-4 py-3 text-center text-slate-400">{{ ch.instance_port }}</td>
            </tr>
          </template>
        </template>
        <tbody v-else>
          <tr v-for="ch in channels" :key="ch.instance_id + ':' + ch.name" class="border-t border-surface-700/50 hover:bg-surface-750/30 transition-colors">
            <td class="px-4 py-3">
              <span class="block truncate max-w-full text-white" :title="ch.name">{{ ch.display_name || ch.name }}</span>
            </td>
            <td class="px-4 py-3 text-slate-500 font-mono text-xs">{{ ch.id || '—' }}</td>
            <td class="px-4 py-3 text-center">
              <span class="text-xs text-accent">#{{ ch.instance_id }}</span>
            </td>
            <td class="px-4 py-3 text-center text-slate-400">{{ ch.instance_port }}</td>
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
              :key="ch.instance_id + ':' + ch.name"
              class="rounded-xl border border-surface-700 bg-surface-750/50 transition-all hover:border-surface-600 p-3"
            >
              <p class="font-medium text-white truncate" :title="ch.name">{{ ch.display_name || ch.name }}</p>
              <p class="text-xs text-slate-500 mt-1 font-mono">{{ ch.id || '—' }}</p>
            </article>
          </div>
        </section>
      </template>
      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="ch in channels"
          :key="ch.instance_id + ':' + ch.name"
          class="rounded-xl border border-surface-700 bg-surface-800/60 transition-all hover:border-surface-600 p-4"
        >
          <p class="font-medium text-white truncate" :title="ch.name">{{ ch.display_name || ch.name }}</p>
          <p class="text-xs text-slate-500 mt-1 font-mono">{{ ch.id || '—' }}</p>
          <div class="flex items-center gap-2 mt-2">
            <span class="text-xs text-accent">#{{ ch.instance_id }}</span>
            <span class="text-xs text-slate-500">порт {{ ch.instance_port }}</span>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import http from '@/core/api'

const loading = ref(true)
const channels = ref<any[]>([])
const viewMode = ref<'table' | 'cards'>('table')
const groupByInstance = ref(false)

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

onMounted(load)
</script>
