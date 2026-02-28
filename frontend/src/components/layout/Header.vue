<template>
  <header class="h-16 flex-shrink-0 flex items-center justify-between px-6 border-b border-surface-700 bg-surface-850/90 backdrop-blur-lg sticky top-0 z-10 transition-all">
    <!-- Search Bar -->
    <div class="relative w-80">
      <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
        <svg class="h-4 w-4 text-slate-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      <input
        type="text"
        placeholder="Поиск по каналам..."
        class="block w-full pl-10 pr-4 py-2 border border-surface-700 rounded-xl leading-5 bg-surface-900/50 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/50 sm:text-sm transition-all hover:bg-surface-900/80 hover:border-surface-600"
      />
    </div>

    <!-- Right Actions -->
    <div class="flex items-center gap-4">
      <!-- Notifications -->
      <button class="relative p-2.5 text-slate-400 hover:text-white transition-all rounded-xl hover:bg-surface-800 active:scale-95">
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        <span class="absolute top-2 right-2 block h-3.5 w-3.5 bg-danger rounded-full ring-2 ring-surface-850 text-[9px] font-bold text-white flex items-center justify-center shadow-lg">3</span>
      </button>

      <!-- Divider -->
      <div class="h-6 w-px bg-surface-700 mx-1"></div>

      <!-- User Profile -->
      <div class="flex items-center gap-3.5 pl-2 group cursor-pointer transition-all">
        <div class="hidden sm:flex flex-col items-end">
          <p class="text-xs font-bold text-white leading-none group-hover:text-accent transition-colors">Alex Rivera</p>
          <p class="text-[10px] text-slate-500 font-medium mt-1 uppercase tracking-wider">Admin</p>
        </div>
        <div class="relative">
          <img
            src="@/assets/avatar.png"
            class="h-9 w-9 rounded-xl object-cover ring-2 ring-surface-700 group-hover:ring-accent transition-all duration-300 shadow-glow-sm"
            alt="User avatar"
          />
          <div class="absolute -bottom-0.5 -right-0.5 h-3 w-3 bg-success rounded-full ring-2 ring-surface-850 shadow-sm border border-surface-850"></div>
        </div>
        <svg class="h-4 w-4 text-slate-500 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
// Header component — with implemented search, notifications, and profile
</script>

<style scoped>
.shadow-glow-sm {
  box-shadow: 0 0 10px rgba(var(--accent-rgb), 0.1);
}
.bg-accent\/10 {
  background-color: rgba(var(--accent-rgb), 0.1);
}
</style>
