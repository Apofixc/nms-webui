<template>
  <div class="h-full flex flex-col justify-between">
    <!-- Header info -->
    <div class="flex items-center justify-between mb-3">
      <div>
        <div class="text-xs text-slate-400 font-mono uppercase">Astra Total Output</div>
        <div class="text-xl font-bold text-slate-100 flex items-center gap-2">
          6.85 Gbps
          <span class="text-xs font-normal text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
            +3.4%
          </span>
        </div>
      </div>
      <div class="text-right">
        <div class="text-[10px] text-slate-400">CC Error Rate</div>
        <div class="text-xs font-mono text-emerald-400 font-bold">0.001% (Minimal)</div>
      </div>
    </div>

    <!-- Simulated Chart Visual -->
    <div class="flex-1 min-h-[120px] relative flex items-end gap-1.5 pt-4">
      <div
        v-for="(val, idx) in chartPoints"
        :key="idx"
        class="flex-1 bg-gradient-to-t from-blue-600/30 to-cyan-400 rounded-t transition-all duration-300 hover:brightness-125"
        :style="{ height: val + '%' }"
        :title="`Time: ${idx * 5}m, Rate: ${(val * 0.08).toFixed(2)} Gbps`"
      ></div>
    </div>

    <!-- Chart Footer -->
    <div class="flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-slate-800/60 mt-2 font-mono">
      <span>60m ago</span>
      <span>45m ago</span>
      <span>30m ago</span>
      <span>15m ago</span>
      <span>NOW</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const chartPoints = ref([45, 52, 68, 60, 75, 82, 70, 88, 92, 85, 90, 78, 85, 95, 88, 92])
</script>
