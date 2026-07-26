<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-slate-100">Мониторинг Сигналов и Битрейта Astra</h2>
        <p class="text-xs text-slate-400">Гистограммы телеметрии, счетчики ошибок Continuity Counter и уровень шумов SNR/BER</p>
      </div>

      <div class="text-xs text-emerald-400 font-mono bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        Живой поток метрик активен
      </div>
    </div>

    <!-- Telemetry Widgets Row -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <div class="glass-panel rounded-2xl p-5 border border-slate-800/80 space-y-4 shadow-xl">
        <h3 class="text-sm font-bold text-slate-200">История суммарного битрейта (Kbps)</h3>
        <BitrateWidget />
      </div>

      <div class="glass-panel rounded-2xl p-5 border border-slate-800/80 space-y-4 shadow-xl">
        <h3 class="text-sm font-bold text-slate-200">Метрики тюнеров DVB (SNR / BER)</h3>
        <SignalWidget />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import BitrateWidget from '@/components/widgets/BitrateWidget.vue'
import SignalWidget from '@/components/widgets/SignalWidget.vue'
</script>
