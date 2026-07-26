<template>
  <div class="space-y-6">
    <!-- Module Context Header -->
    <div class="glass-panel rounded-2xl p-5 border border-slate-800/80 flex items-center justify-between shadow-xl">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-400 flex items-center justify-center font-bold text-lg">
          📡
        </div>
        <div>
          <h2 class="text-lg font-bold text-slate-100">{{ currentTitle }}</h2>
          <p class="text-xs text-slate-400 font-mono">Модульный раздел: {{ currentRouteName }}</p>
        </div>
      </div>

      <!-- Header Module KPI Stats -->
      <div class="flex items-center gap-4 text-xs font-mono">
        <div class="bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-800">
          <span class="text-slate-400">STATUS:</span>
          <span class="text-emerald-400 ml-1.5 font-bold">ONLINE</span>
        </div>
        <div class="bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-800">
          <span class="text-slate-400">LATENCY:</span>
          <span class="text-blue-400 ml-1.5 font-bold">12 ms</span>
        </div>
      </div>
    </div>

    <!-- Active View Content -->
    <div class="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-2xl min-h-[400px]">
      <div v-if="currentRouteName.includes('Channels')" class="space-y-4">
        <h3 class="text-sm font-bold text-slate-200">Управление ТВ-каналами Astra</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="i in 6" :key="i" class="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-xs text-slate-100">Astra Channel #{{ i }}</span>
              <span class="text-[9px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded font-mono">18.5 Mbps</span>
            </div>
            <div class="text-[10px] text-slate-400 font-mono">SNR: 94% | BER: 0 | Lock: OK</div>
            <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div class="h-full bg-emerald-400" style="width: 94%"></div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="currentRouteName.includes('Adapters')" class="space-y-4">
        <h3 class="text-sm font-bold text-slate-200">Статус DVB-S/S2/T2 Адаптеров</h3>
        <div class="space-y-2">
          <div v-for="i in 4" :key="i" class="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs font-mono">
            <div class="flex items-center gap-3">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span class="font-bold text-slate-200">DVB Adapter #{{ i - 1 }}</span>
              <span class="text-slate-400">(Tuner TBS-6904)</span>
            </div>
            <div class="flex items-center gap-4 text-slate-300">
              <span>Freq: 11494H</span>
              <span class="text-emerald-400 font-bold">SNR 92.4%</span>
              <span class="text-cyan-400">BER 0</span>
              <span class="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded">LOCKED</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="flex flex-col items-center justify-center py-16 text-center space-y-3">
        <div class="text-4xl">🧩</div>
        <h3 class="text-base font-bold text-slate-200">Модульная страница: {{ currentRouteName }}</h3>
        <p class="text-xs text-slate-400 max-w-md">Динамическое представление загруженного модуля NMS-WebUI v2</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentRouteName = computed(() => String(route.name || route.path))
const currentTitle = computed(() => (route.meta?.title as string) || 'Раздел модуля')
</script>
