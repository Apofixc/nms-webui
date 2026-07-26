<template>
  <aside class="w-64 h-screen glass-sidebar flex flex-col flex-shrink-0 select-none border-r border-slate-800/80 relative">
    <!-- Sidebar Header / Logo -->
    <div class="h-14 px-4 flex items-center justify-between border-b border-slate-800/80 flex-shrink-0 bg-[#0b0f19]/40">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 via-indigo-500 to-cyan-400 p-0.5 shadow-lg shadow-blue-500/20 flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div>
          <h1 class="font-bold text-sm text-slate-100 tracking-tight flex items-center gap-1">
            NMS Console <span class="text-[10px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1 rounded">v2</span>
          </h1>
          <p class="text-[10px] text-slate-400">Broadcast Manager</p>
        </div>
      </div>
    </div>

    <!-- Scrollable Middle Section for Modules & Submodules -->
    <div class="flex-1 overflow-y-auto px-3 py-3 space-y-5 custom-scroll">
      <div v-for="group in sidebarGroups" :key="group.id" class="space-y-1">
        <!-- Group Header -->
        <div class="px-2 text-[10px] font-semibold text-slate-400 tracking-wider uppercase flex items-center justify-between">
          <span>{{ group.label }}</span>
          <span class="w-1.5 h-1.5 rounded-full bg-slate-700"></span>
        </div>

        <!-- Group Items (Modules & Submodules) -->
        <div class="space-y-0.5 mt-1">
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            v-slot="{ isActive }"
          >
            <div
              :class="[
                'flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 group cursor-pointer',
                item.submodule_id ? 'ml-3 border-l-2 border-slate-800 pl-3' : '',
                isActive
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-md shadow-blue-500/10 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              ]"
            >
              <component
                :is="getIconComponent(item.icon)"
                :class="['w-4 h-4 transition-colors', isActive ? 'text-blue-400' : 'text-slate-400 group-hover:text-slate-200']"
              />
              <span class="truncate">{{ item.label }}</span>
              <span v-if="item.submodule_id" class="ml-auto text-[9px] bg-slate-800 text-slate-400 px-1 rounded">sub</span>
            </div>
          </router-link>
        </div>
      </div>
    </div>

    <!-- Pinned Fixed Bottom Settings Bar -->
    <PinnedBottomSettingsBar />
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getSidebarGroups } from '@/modules/registry'
import PinnedBottomSettingsBar from './PinnedBottomSettingsBar.vue'

const sidebarGroups = computed(() => getSidebarGroups())

function getIconComponent(iconName?: string | null) {
  // Inline SVG icon renderer helper
  return {
    template: `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    `
  }
}
</script>
