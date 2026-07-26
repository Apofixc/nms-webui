<template>
  <div class="h-full flex flex-col justify-between font-mono text-[11px] overflow-hidden">
    <div class="flex-1 overflow-y-auto space-y-1 pr-1 custom-scroll">
      <div v-for="(log, idx) in logs" :key="idx" class="flex items-start gap-2 py-1 border-b border-slate-800/40 text-slate-300">
        <span class="text-slate-500 text-[10px] whitespace-nowrap font-mono">{{ log.time }}</span>
        <span class="text-slate-200 truncate">{{ log.msg }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const logs = ref([
  { time: '2023-02-25 19:15:19', msg: 'Astra claiming 136 streams being cached in RAM buffer' },
  { time: '2023-02-25 12:03:17', msg: 'Astra Network events: Adapter 0 locked frequency 11494H' },
  { time: '2023-02-25 12:03:17', msg: 'Astra Network events: Bitrate stable 29,540 Kbps' },
  { time: '2023-02-25 12:03:19', msg: 'Astra Network connected: Submodule playlist ready' },
  { time: '2023-02-25 12:03:19', msg: 'Astra Network events: DVB SNR 92.4% BER 0' },
  { time: '2023-02-25 12:03:32', msg: 'Astra Network events: All active streams running' },
  { time: '2023-02-25 12:03:39', msg: 'Astra Network events: System memory usage 42%' },
  { time: '2023-02-25 12:03:39', msg: 'Network event: configuration sync with backend' },
  { time: '2023-02-25 12:03:39', msg: 'Astra Network connected: WebSocket status 200 OK' },
  { time: '2023-02-25 12:03:51', msg: 'Network event: configuration backup completed' },
  { time: '2023-02-25 12:01:57', msg: 'Astra events: Instance #1 healthy' },
])
</script>
