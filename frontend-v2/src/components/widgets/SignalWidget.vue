<template>
  <div class="h-full flex items-center justify-around gap-4">
    <!-- SNR Dial Gauge -->
    <div class="flex flex-col items-center">
      <div class="relative w-24 h-24 flex items-center justify-center">
        <!-- SVG Gauge Ring -->
        <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
          <path
            class="text-slate-800"
            stroke-width="3.5"
            stroke="currentColor"
            fill="none"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <path
            class="text-emerald-400 stroke-current transition-all duration-500"
            stroke-width="3.5"
            stroke-dasharray="92, 100"
            stroke-linecap="round"
            fill="none"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
        </svg>
        <div class="absolute text-center">
          <div class="text-lg font-bold text-slate-100">92%</div>
          <div class="text-[9px] text-slate-400 font-mono">14.2 dB</div>
        </div>
      </div>
      <span class="text-xs font-medium text-slate-300 mt-1">SNR Signal</span>
    </div>

    <!-- BER Gauge -->
    <div class="flex flex-col items-center">
      <div class="relative w-24 h-24 flex items-center justify-center">
        <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
          <path
            class="text-slate-800"
            stroke-width="3.5"
            stroke="currentColor"
            fill="none"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <path
            class="text-cyan-400 stroke-current transition-all duration-500"
            stroke-width="3.5"
            stroke-dasharray="98, 100"
            stroke-linecap="round"
            fill="none"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
        </svg>
        <div class="absolute text-center">
          <div class="text-sm font-bold text-cyan-400 font-mono">1e-9</div>
          <div class="text-[9px] text-slate-400">Zero Error</div>
        </div>
      </div>
      <span class="text-xs font-medium text-slate-300 mt-1">BER Error</span>
    </div>
  </div>
</template>

<script setup lang="ts">
// SignalWidget Component
</script>
