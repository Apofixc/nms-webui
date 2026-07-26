<template>
  <div class="h-full flex flex-col justify-between overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-left text-xs">
        <thead class="text-[10px] text-slate-400 uppercase bg-slate-900/60 font-mono">
          <tr>
            <th class="py-2 px-3">Канал</th>
            <th class="py-2 px-3">Битрейт</th>
            <th class="py-2 px-3">SNR</th>
            <th class="py-2 px-3">Статус</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/60">
          <tr v-for="ch in channels" :key="ch.id" class="hover:bg-slate-800/40 transition-colors">
            <td class="py-2 px-3 font-medium text-slate-200 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              {{ ch.name }}
            </td>
            <td class="py-2 px-3 font-mono text-slate-300">{{ ch.bitrate }}</td>
            <td class="py-2 px-3 font-mono text-emerald-400">{{ ch.snr }}</td>
            <td class="py-2 px-3">
              <span class="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-mono">
                ONLINE
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const channels = ref([
  { id: '1', name: 'Astra TV HD', bitrate: '18.5 Mbps', snr: '94%' },
  { id: '2', name: 'Sports 1HD', bitrate: '16.2 Mbps', snr: '92%' },
  { id: '3', name: 'News 24 4K', bitrate: '28.0 Mbps', snr: '96%' },
  { id: '4', name: 'Discovery HD', bitrate: '14.8 Mbps', snr: '90%' },
])
</script>
