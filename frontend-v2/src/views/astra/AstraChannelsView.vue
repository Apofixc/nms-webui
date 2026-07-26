<template>
  <div class="space-y-6">
    <!-- Header Controls -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          ТВ-Каналы и Потоки Astra
          <span class="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-mono">
            {{ channels.length }} каналов в эфире
          </span>
        </h2>
        <p class="text-xs text-slate-400">Управление входными/выходными потоками вещания, предпросмотр и диагностика</p>
      </div>

      <div class="flex items-center gap-3">
        <input
          type="text"
          v-model="searchQuery"
          placeholder="Фильтр каналов..."
          class="px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-700/80 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
        <button
          @click="showAddModal = true"
          class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-blue-600/20 transition-all flex items-center gap-1.5"
        >
          + Добавить канал
        </button>
      </div>
    </div>

    <!-- Channels Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="ch in filteredChannels"
        :key="ch.id"
        class="glass-panel rounded-2xl p-4 border border-slate-800/80 space-y-4 hover:border-blue-500/40 transition-all shadow-xl relative group"
      >
        <!-- Card Header -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 flex items-center justify-center font-bold text-sm text-blue-400">
              {{ ch.name.substring(0, 2) }}
            </div>
            <div>
              <h3 class="text-sm font-bold text-slate-100">{{ ch.name }}</h3>
              <p class="text-[10px] text-slate-400 font-mono">{{ ch.type }} | {{ ch.ip }}</p>
            </div>
          </div>

          <span
            :class="[
              'text-[9px] px-2 py-0.5 rounded font-mono font-bold uppercase border',
              ch.status === 'ONLINE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
            ]"
          >
            {{ ch.status }}
          </span>
        </div>

        <!-- Metrics & Gauges -->
        <div class="space-y-2 text-xs font-mono bg-slate-900/40 p-3 rounded-xl border border-slate-800">
          <div class="flex justify-between text-slate-400">
            <span>Битрейт потока:</span>
            <span class="text-slate-100 font-bold">{{ ch.bitrate }}</span>
          </div>

          <div class="flex justify-between text-slate-400">
            <span>Уровень сигнала SNR:</span>
            <span class="text-emerald-400 font-bold">{{ ch.snr }}</span>
          </div>

          <div class="flex justify-between text-slate-400">
            <span>Ошибки BER / CC:</span>
            <span class="text-cyan-400 font-bold">{{ ch.ber }} / 0</span>
          </div>

          <!-- Signal Bar -->
          <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden mt-1">
            <div class="h-full bg-emerald-400 rounded-full" :style="{ width: ch.snr }"></div>
          </div>
        </div>

        <!-- Action Controls -->
        <div class="flex items-center justify-between pt-1">
          <button
            @click="playStream(ch)"
            class="px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 text-xs font-semibold transition-all flex items-center gap-1.5"
          >
            ▶ Предпросмотр
          </button>
          <div class="flex items-center gap-2 text-slate-500 text-xs">
            <button class="hover:text-slate-200">⚙️</button>
            <button class="hover:text-rose-400">🗑️</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const searchQuery = ref('')
const showAddModal = ref(false)

const channels = ref([
  { id: '1', name: 'Astra TV HD', type: 'UDP/Multicast', ip: 'udp://239.255.1.1:1234', bitrate: '18.5 Mbps', snr: '94%', ber: '0', status: 'ONLINE' },
  { id: '2', name: 'Sports 1HD', type: 'HTTP/TS', ip: 'http://127.0.0.1:8000/sports', bitrate: '16.2 Mbps', snr: '92%', ber: '1e-9', status: 'ONLINE' },
  { id: '3', name: 'News 24 4K', type: 'HLS', ip: 'http://127.0.0.1:8000/news/index.m3u8', bitrate: '28.0 Mbps', snr: '96%', ber: '0', status: 'ONLINE' },
  { id: '4', name: 'Discovery HD', type: 'UDP/Multicast', ip: 'udp://239.255.1.4:1234', bitrate: '14.8 Mbps', snr: '90%', ber: '0', status: 'ONLINE' },
  { id: '5', name: 'EuroNews', type: 'HTTP/TS', ip: 'http://127.0.0.1:8000/euronews', bitrate: '12.4 Mbps', snr: '91%', ber: '0', status: 'ONLINE' },
  { id: '6', name: 'Cinema Max', type: 'UDP/Multicast', ip: 'udp://239.255.1.6:1234', bitrate: '21.0 Mbps', snr: '95%', ber: '0', status: 'ONLINE' },
])

const filteredChannels = computed(() => {
  if (!searchQuery.value) return channels.value
  return channels.value.filter(ch => ch.name.toLowerCase().includes(searchQuery.value.toLowerCase()))
})

function playStream(ch: any) {
  alert(`Запуск предпросмотра плеера для ${ch.name} (${ch.ip})`)
}
</script>
