<template>
  <div class="space-y-6">
    <!-- Top System KPI Cards Bar -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="glass-panel rounded-xl p-4 border border-slate-800/80 flex items-center justify-between">
        <div>
          <div class="text-[11px] text-slate-400 font-mono">ВСЕГО КАНАЛОВ</div>
          <div class="text-2xl font-bold text-slate-100 mt-1">148 / 150</div>
          <div class="text-[10px] text-emerald-400 mt-0.5">148 Активны</div>
        </div>
        <div class="w-10 h-10 rounded-lg bg-blue-600/20 text-blue-400 flex items-center justify-center border border-blue-500/30">
          📺
        </div>
      </div>

      <div class="glass-panel rounded-xl p-4 border border-slate-800/80 flex items-center justify-between">
        <div>
          <div class="text-[11px] text-slate-400 font-mono">DVB АДАПТЕРЫ</div>
          <div class="text-2xl font-bold text-slate-100 mt-1">12 / 12</div>
          <div class="text-[10px] text-emerald-400 mt-0.5">TUNER LOCK 100%</div>
        </div>
        <div class="w-10 h-10 rounded-lg bg-emerald-600/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
          🛰️
        </div>
      </div>

      <div class="glass-panel rounded-xl p-4 border border-slate-800/80 flex items-center justify-between">
        <div>
          <div class="text-[11px] text-slate-400 font-mono">ОБЩИЙ БИТРЕЙТ</div>
          <div class="text-2xl font-bold text-slate-100 mt-1">6.85 Gbps</div>
          <div class="text-[10px] text-blue-400 mt-0.5">Вход/Выход OK</div>
        </div>
        <div class="w-10 h-10 rounded-lg bg-cyan-600/20 text-cyan-400 flex items-center justify-center border border-cyan-500/30">
          ⚡
        </div>
      </div>

      <div class="glass-panel rounded-xl p-4 border border-slate-800/80 flex items-center justify-between">
        <div>
          <div class="text-[11px] text-slate-400 font-mono">АКТИВНЫЕ МОДУЛИ</div>
          <div class="text-2xl font-bold text-slate-100 mt-1">4 / 4</div>
          <div class="text-[10px] text-emerald-400 mt-0.5">Система стабильна</div>
        </div>
        <div class="w-10 h-10 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
          🧩
        </div>
      </div>
    </div>

    <!-- Main Grid Dashboard -->
    <GridDashboard />
  </div>
</template>

<script setup lang="ts">
import GridDashboard from '@/components/widgets/GridDashboard.vue'
</script>
