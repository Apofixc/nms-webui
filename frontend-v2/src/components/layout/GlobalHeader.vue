<template>
  <header class="h-14 glass-header px-6 flex items-center justify-between flex-shrink-0 z-10">
    <!-- Left: Search & Navigation Tabs -->
    <div class="flex items-center gap-6">
      <div class="relative w-64">
        <svg class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="text"
          placeholder="Поиск по модулям, каналам..."
          class="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-700/60 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/60 transition-colors"
        />
      </div>

      <!-- Quick Section Tabs -->
      <nav class="flex items-center gap-1">
        <router-link
          to="/dashboard"
          v-slot="{ isActive }"
        >
          <button :class="['px-3 py-1.5 rounded-lg text-xs font-medium transition-all', isActive ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'text-slate-400 hover:text-slate-200']">
            Дашборд
          </button>
        </router-link>

        <router-link
          to="/modules"
          v-slot="{ isActive }"
        >
          <button :class="['px-3 py-1.5 rounded-lg text-xs font-medium transition-all', isActive ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'text-slate-400 hover:text-slate-200']">
            Реестр модулей
          </button>
        </router-link>

        <router-link
          to="/settings"
          v-slot="{ isActive }"
        >
          <button :class="['px-3 py-1.5 rounded-lg text-xs font-medium transition-all', isActive ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'text-slate-400 hover:text-slate-200']">
            Настройки
          </button>
        </router-link>
      </nav>
    </div>

    <!-- Right: Telemetry & Status Gauges -->
    <div class="flex items-center gap-5">
      <!-- Telemetry Gauges -->
      <div class="hidden lg:flex items-center gap-4 text-xs bg-slate-900/50 px-3 py-1.5 rounded-lg border border-slate-800">
        <!-- CPU Gauge -->
        <div class="flex items-center gap-1.5">
          <span class="text-slate-400 font-mono text-[10px]">CPU</span>
          <div class="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div class="h-full bg-emerald-400 rounded-full" style="width: 24%"></div>
          </div>
          <span class="text-slate-300 font-mono text-[10px]">24%</span>
        </div>

        <!-- RAM Gauge -->
        <div class="flex items-center gap-1.5">
          <span class="text-slate-400 font-mono text-[10px]">RAM</span>
          <div class="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div class="h-full bg-blue-400 rounded-full" style="width: 42%"></div>
          </div>
          <span class="text-slate-300 font-mono text-[10px]">42%</span>
        </div>

        <!-- Net Gauge -->
        <div class="flex items-center gap-1.5">
          <span class="text-slate-400 font-mono text-[10px]">NET</span>
          <span class="text-emerald-400 font-mono text-[10px] font-semibold">1.4 Gbps</span>
        </div>
      </div>

      <!-- Notifications Icon -->
      <button class="relative p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        <span class="w-2 h-2 rounded-full bg-rose-500 absolute top-1.5 right-1.5 ring-2 ring-nms-bg"></span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
// GlobalHeader Component
</script>
