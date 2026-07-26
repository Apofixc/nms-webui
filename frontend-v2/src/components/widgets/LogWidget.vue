<template>
  <div class="h-full flex flex-col justify-between font-mono text-[11px] overflow-hidden">
    <div class="flex-1 overflow-y-auto space-y-1.5 pr-1">
      <div v-for="(log, idx) in logs" :key="idx" class="flex items-start gap-2 py-0.5 border-b border-slate-800/40">
        <span class="text-slate-500 text-[10px] whitespace-nowrap">{{ log.time }}</span>
        <span
          :class="[
            'text-[9px] px-1 rounded uppercase font-bold',
            log.level === 'INFO' ? 'bg-blue-500/20 text-blue-400' :
            log.level === 'WARN' ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'
          ]"
        >
          {{ log.level }}
        </span>
        <span class="text-slate-300 truncate">{{ log.msg }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const logs = ref([
  { time: '22:45:12', level: 'INFO', msg: 'Astra instance #1 stream cache refreshed' },
  { time: '22:44:50', level: 'OK', msg: 'DVB-S2 Adapter 0 locked on 11494H' },
  { time: '22:44:18', level: 'WARN', msg: 'Submodule playlist sync delay 12ms' },
  { time: '22:43:05', level: 'INFO', msg: 'NMS Module registry sync complete' },
])
</script>
