<template>
  <aside class="w-64 h-screen glass-sidebar flex flex-col flex-shrink-0 select-none border-r border-slate-800/80 relative text-slate-300">
    <!-- Sidebar Header -->
    <div class="h-14 px-4 flex items-center justify-between border-b border-slate-800/80 flex-shrink-0 bg-[#0b0f19]/60">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-500 to-cyan-400 p-0.5 shadow-lg shadow-blue-500/20 flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div>
          <h1 class="font-bold text-sm text-slate-100 tracking-tight">
            NMS Console
          </h1>
          <p class="text-[10px] text-slate-400">Broadcast Engineering</p>
        </div>
      </div>
    </div>

    <!-- Main Dashboard Top Quick Link -->
    <div class="p-3 border-b border-slate-800/60">
      <router-link
        to="/dashboard"
        class="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all group"
        active-class="bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-md"
      >
        <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
        <span>Главный Дашборд</span>
      </router-link>
    </div>

    <!-- Scrollable Middle Section: Dynamic Modules & Submodules Only -->
    <div class="flex-1 overflow-y-auto px-3 py-3 space-y-4 custom-scroll">
      <!-- Astra Broadcast Category (Parent Module) -->
      <div class="space-y-1">
        <div class="flex items-center justify-between text-xs font-bold text-slate-300 px-2 py-1 cursor-pointer hover:text-white" @click="openCats.astra = !openCats.astra">
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Astra Broadcast
          </span>
          <svg :class="['w-3 h-3 text-slate-500 transition-transform', openCats.astra ? 'rotate-180' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>

        <div v-if="openCats.astra" class="pl-6 space-y-0.5 text-xs text-slate-400 border-l border-slate-800 ml-3">
          <router-link to="/astra/channels" class="block py-1.5 px-2.5 rounded hover:bg-slate-800/60 hover:text-slate-100 transition-colors" active-class="bg-blue-600/20 text-blue-400 font-semibold border-l-2 border-blue-500">
            Каналы вещания
          </router-link>
          <router-link to="/astra/adapters" class="block py-1.5 px-2.5 rounded hover:bg-slate-800/60 hover:text-slate-100 transition-colors" active-class="bg-blue-600/20 text-blue-400 font-semibold border-l-2 border-blue-500">
            DVB Адаптеры
          </router-link>
          <router-link to="/astra/monitoring" class="block py-1.5 px-2.5 rounded hover:bg-slate-800/60 hover:text-slate-100 transition-colors" active-class="bg-blue-600/20 text-blue-400 font-semibold border-l-2 border-blue-500">
            Мониторинг SNR/BER
          </router-link>
          <router-link to="/astra/playlists" class="block py-1.5 px-2.5 rounded hover:bg-slate-800/60 hover:text-amber-400 transition-colors flex items-center justify-between" active-class="bg-amber-500/20 text-amber-400 font-semibold">
            <span>Плейлисты</span>
            <span class="text-[9px] bg-amber-500/20 text-amber-400 px-1 rounded font-mono">sub</span>
          </router-link>
          <router-link to="/astra/instances" class="block py-1.5 px-2.5 rounded hover:bg-slate-800/60 hover:text-slate-100 transition-colors">
            Инстансы Astra
          </router-link>
        </div>
      </div>

      <!-- Network SNMP Category -->
      <div class="space-y-1">
        <div class="flex items-center justify-between text-xs font-bold text-slate-300 px-2 py-1 cursor-pointer hover:text-white" @click="openCats.snmp = !openCats.snmp">
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Сеть & SNMP
          </span>
          <svg :class="['w-3 h-3 text-slate-500 transition-transform', openCats.snmp ? 'rotate-180' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>

        <div v-if="openCats.snmp" class="pl-6 space-y-0.5 text-xs text-slate-400 border-l border-slate-800 ml-3">
          <router-link to="/snmp/devices" class="block py-1.5 px-2.5 rounded hover:bg-slate-800/60 hover:text-slate-100 transition-colors" active-class="bg-blue-600/20 text-blue-400 font-semibold">
            Коммутаторы SNMP
          </router-link>
        </div>
      </div>
    </div>

    <!-- Pinned Fixed Bottom Settings Bar -->
    <PinnedBottomSettingsBar />
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import PinnedBottomSettingsBar from './PinnedBottomSettingsBar.vue'

const openCats = ref({
  astra: true,
  snmp: true,
})
</script>
