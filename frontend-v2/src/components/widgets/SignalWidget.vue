<template>
  <div class="h-full flex flex-col justify-between p-1">
    <div class="grid grid-cols-2 gap-4">
      <!-- SNR Gauge 1 -->
      <div class="flex flex-col items-center glass-panel p-3 rounded-xl border border-slate-800/80">
        <div class="relative w-28 h-20 flex items-center justify-center">
          <svg class="w-full h-full" viewBox="0 0 100 60">
            <!-- Background Dial Arc -->
            <path d="M 15 50 A 40 40 0 0 1 85 50" fill="none" stroke="#1f2d4a" stroke-width="8" stroke-linecap="round" />
            <!-- Active Green Arc -->
            <path d="M 15 50 A 40 40 0 0 1 75 25" fill="none" stroke="#10b981" stroke-width="8" stroke-linecap="round" />
            <!-- Needle -->
            <line x1="50" y1="50" x2="68" y2="22" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round" />
            <circle cx="50" cy="50" r="4" fill="#38bdf8" />
          </svg>
        </div>
        <div class="text-center -mt-2">
          <div class="text-sm font-bold text-slate-100 font-mono">14.2 dB</div>
          <div class="text-[10px] text-emerald-400 font-semibold uppercase">SNR (38.5 dB)</div>
        </div>
      </div>

      <!-- BER Gauge 1 -->
      <div class="flex flex-col items-center glass-panel p-3 rounded-xl border border-slate-800/80">
        <div class="relative w-28 h-20 flex items-center justify-center">
          <svg class="w-full h-full" viewBox="0 0 100 60">
            <!-- Background Dial Arc -->
            <path d="M 15 50 A 40 40 0 0 1 85 50" fill="none" stroke="#1f2d4a" stroke-width="8" stroke-linecap="round" />
            <!-- Active Cyan Arc -->
            <path d="M 15 50 A 40 40 0 0 1 30 35" fill="none" stroke="#06b6d4" stroke-width="8" stroke-linecap="round" />
            <!-- Needle -->
            <line x1="50" y1="50" x2="28" y2="32" stroke="#06b6d4" stroke-width="2.5" stroke-linecap="round" />
            <circle cx="50" cy="50" r="4" fill="#06b6d4" />
          </svg>
        </div>
        <div class="text-center -mt-2">
          <div class="text-sm font-bold text-cyan-400 font-mono">1e-9</div>
          <div class="text-[10px] text-cyan-400 font-semibold uppercase">BER (0 Errors)</div>
        </div>
      </div>

      <!-- SNR Gauge 2 -->
      <div class="flex flex-col items-center glass-panel p-3 rounded-xl border border-slate-800/80">
        <div class="relative w-28 h-20 flex items-center justify-center">
          <svg class="w-full h-full" viewBox="0 0 100 60">
            <path d="M 15 50 A 40 40 0 0 1 85 50" fill="none" stroke="#1f2d4a" stroke-width="8" stroke-linecap="round" />
            <path d="M 15 50 A 40 40 0 0 1 80 30" fill="none" stroke="#10b981" stroke-width="8" stroke-linecap="round" />
            <line x1="50" y1="50" x2="72" y2="28" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" />
            <circle cx="50" cy="50" r="4" fill="#10b981" />
          </svg>
        </div>
        <div class="text-center -mt-2">
          <div class="text-sm font-bold text-slate-100 font-mono">92.4%</div>
          <div class="text-[10px] text-emerald-400 font-semibold uppercase">SNR Tuner 2</div>
        </div>
      </div>

      <!-- BER Gauge 2 -->
      <div class="flex flex-col items-center glass-panel p-3 rounded-xl border border-slate-800/80">
        <div class="relative w-28 h-20 flex items-center justify-center">
          <svg class="w-full h-full" viewBox="0 0 100 60">
            <path d="M 15 50 A 40 40 0 0 1 85 50" fill="none" stroke="#1f2d4a" stroke-width="8" stroke-linecap="round" />
            <path d="M 15 50 A 40 40 0 0 1 25 42" fill="none" stroke="#06b6d4" stroke-width="8" stroke-linecap="round" />
            <line x1="50" y1="50" x2="22" y2="40" stroke="#06b6d4" stroke-width="2.5" stroke-linecap="round" />
            <circle cx="50" cy="50" r="4" fill="#06b6d4" />
          </svg>
        </div>
        <div class="text-center -mt-2">
          <div class="text-sm font-bold text-cyan-400 font-mono">0</div>
          <div class="text-[10px] text-cyan-400 font-semibold uppercase">BER Tuner 2</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>
