<template>
  <div class="sticky bottom-0 left-0 right-0 z-20 glass-panel border-t border-slate-700/60 p-2.5 flex flex-col gap-2 bg-[#0d1322]/95 backdrop-blur-md shadow-2xl">
    <!-- Pinned Settings Action Button -->
    <router-link
      to="/settings"
      class="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 hover:text-blue-300 border border-blue-500/30 transition-all font-semibold text-xs shadow-md group"
      title="Глобальные настройки и менеджер модулей"
    >
      <svg class="w-4 h-4 text-blue-400 group-hover:rotate-45 transition-transform duration-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
      <span class="truncate">Настройки</span>
    </router-link>

    <!-- System Status & User Profile Widget -->
    <div class="flex items-center justify-between pt-1 text-[11px] text-slate-400 border-t border-slate-800/80">
      <div class="flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span class="font-mono text-emerald-400 font-semibold text-[10px]">ONLINE</span>
      </div>
      <div class="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 cursor-pointer">
        <div class="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-[10px]">
          A
        </div>
        <span class="truncate max-w-[80px]">Admin</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Pinned Bottom Settings Bar Component
</script>
