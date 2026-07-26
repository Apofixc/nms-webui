<template>
  <div class="h-full flex flex-col justify-between p-1">
    <!-- Graph Header Stats -->
    <div class="flex items-center justify-between mb-2 text-xs">
      <div class="flex items-center gap-3">
        <div>
          <span class="text-slate-400 text-[10px]">Astra Total Bitrate:</span>
          <span class="text-emerald-400 font-mono font-bold ml-1">29,540 Kbps</span>
        </div>
        <div>
          <span class="text-slate-400 text-[10px]">CC Errors:</span>
          <span class="text-rose-400 font-mono font-bold ml-1">0</span>
        </div>
      </div>
      <div class="text-[10px] text-slate-500 font-mono">Range: 0 - 30,000 Kbps</div>
    </div>

    <!-- High-res SVG Bitrate Waveform -->
    <div class="flex-1 relative min-h-[160px] bg-slate-900/60 rounded-xl p-2 border border-slate-800/80 flex items-center">
      <!-- Y-Axis Grid Lines & Labels -->
      <div class="absolute left-2 top-2 bottom-6 flex flex-col justify-between text-[9px] font-mono text-slate-500 pointer-events-none">
        <span>30,000</span>
        <span>20,000</span>
        <span>10,000</span>
        <span>0</span>
      </div>

      <svg class="w-full h-full pl-8" viewBox="0 0 500 150" preserveAspectRatio="none">
        <defs>
          <linearGradient id="bitrateGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#10b981" stop-opacity="0.4" />
            <stop offset="100%" stop-color="#10b981" stop-opacity="0.0" />
          </linearGradient>
        </defs>

        <!-- Grid Lines -->
        <line x1="0" y1="20" x2="500" y2="20" stroke="#1f2d4a" stroke-dasharray="4 4" />
        <line x1="0" y1="65" x2="500" y2="65" stroke="#1f2d4a" stroke-dasharray="4 4" />
        <line x1="0" y1="110" x2="500" y2="110" stroke="#1f2d4a" stroke-dasharray="4 4" />

        <!-- Filled Gradient Path -->
        <path
          d="M 0 130 Q 30 40, 60 90 T 120 30 T 180 110 T 240 25 T 300 80 T 360 35 T 420 100 T 500 40 L 500 140 L 0 140 Z"
          fill="url(#bitrateGrad)"
        />

        <!-- Main Neon Line -->
        <path
          d="M 0 130 Q 30 40, 60 90 T 120 30 T 180 110 T 240 25 T 300 80 T 360 35 T 420 100 T 500 40"
          fill="none"
          stroke="#10b981"
          stroke-width="2.5"
        />

        <!-- Secondary CC Error Line (Orange/Red) -->
        <path
          d="M 0 135 L 50 135 L 100 135 L 150 132 L 200 135 L 250 135 L 300 135 L 350 130 L 400 135 L 450 135 L 500 135"
          fill="none"
          stroke="#f43f5e"
          stroke-width="1.5"
        />
      </svg>
    </div>

    <!-- X-Axis Timestamps -->
    <div class="flex justify-between text-[10px] text-slate-500 font-mono pt-1.5 px-2">
      <span>09:00</span>
      <span>06:00</span>
      <span>10:20</span>
      <span>16:15</span>
      <span>16:30</span>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>
