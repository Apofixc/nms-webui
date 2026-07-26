<template>
  <div class="h-full flex flex-col justify-between overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full text-left text-xs font-mono">
        <thead class="text-[10px] text-slate-400 uppercase bg-slate-900/80 border-b border-slate-800">
          <tr>
            <th class="py-2 px-3">Channel</th>
            <th class="py-2 px-3">Bitrate</th>
            <th class="py-2 px-3">SNR</th>
            <th class="py-2 px-3">BER</th>
            <th class="py-2 px-3 text-right">Network</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/50">
          <tr v-for="ch in channels" :key="ch.name" class="hover:bg-slate-800/40 transition-colors">
            <td class="py-2 px-3 font-semibold text-slate-200 font-sans flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              {{ ch.name }}
            </td>
            <td class="py-2 px-3 text-slate-300">{{ ch.bitrate }}</td>
            <td class="py-2 px-3 text-emerald-400 font-semibold">{{ ch.snr }}</td>
            <td class="py-2 px-3 text-slate-400">{{ ch.ber }}</td>
            <td class="py-2 px-3 text-right">
              <span class="text-[10px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded font-sans">
                {{ ch.network }}
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
  { name: 'Astra', bitrate: '295 MB', snr: '40 b/s', ber: '38', network: 'UDP' },
  { name: 'Astra2', bitrate: '141 MB', snr: '40 b/s', ber: '36', network: 'HTTP' },
  { name: 'Astra HD', bitrate: '720 MB', snr: '50 b/s', ber: '45', network: 'HLS' },
  { name: 'Astra Sports', bitrate: '34 MB', snr: '30 b/s', ber: '47', network: 'RTSP' },
  { name: 'Astra4', bitrate: '139 MB', snr: '40 b/s', ber: '43', network: 'UDP' },
  { name: 'Astra News', bitrate: '240 MB', snr: '40 b/s', ber: '34', network: 'HTTP' },
  { name: 'Astra6', bitrate: '6 MB', snr: '30 b/s', ber: '38', network: 'UDP' },
])
</script>
