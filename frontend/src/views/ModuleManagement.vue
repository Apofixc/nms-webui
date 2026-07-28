<template>
  <div class="min-h-full p-6 flex gap-6 max-w-6xl w-full mx-auto animate-fade-in text-on-surface">
    <!-- Settings Rail (Secondary Nav) -->
    <aside class="w-52 shrink-0 hidden md:flex flex-col gap-2 border-r border-outline-variant pr-4">
      <div class="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-2 pl-2 font-bold">Configuration Groups</div>
      <router-link
        to="/settings/modules"
        class="w-full text-left flex items-center gap-3 py-2 px-3 rounded-lg bg-surface-container-highest border border-outline-variant text-on-surface font-bold text-sm shadow-glow transition-all"
      >
        <span class="material-symbols-outlined text-primary text-[20px]">view_module</span>
        <span>Module Management</span>
      </router-link>

      <router-link
        to="/settings"
        class="w-full text-left flex items-center gap-3 py-2 px-3 rounded-lg text-on-surface-variant hover:bg-surface-variant/40 hover:text-on-surface text-sm transition-all border border-transparent"
      >
        <span class="material-symbols-outlined text-[20px]">verified_user</span>
        <span>Access & Identity</span>
      </router-link>

      <button class="w-full text-left flex items-center gap-3 py-2 px-3 rounded-lg text-on-surface-variant hover:bg-surface-variant/40 hover:text-on-surface text-sm transition-all border border-transparent">
        <span class="material-symbols-outlined text-[20px]">videocam</span>
        <span>Video Playback Test</span>
      </button>
    </aside>

    <!-- Configuration Area -->
    <div class="flex-1 flex flex-col gap-6 max-w-6xl mx-auto w-full pb-12 min-w-0">
      <div class="flex items-center justify-between mb-2">
        <div>
          <h1 class="font-bold text-2xl text-on-surface">Module Management</h1>
          <p class="text-xs text-on-surface-variant mt-1">Monitor and control system-level service modules.</p>
        </div>
        <div class="flex items-center gap-3">
          <button @click="reloadModules" class="bg-primary-container hover:bg-primary-fixed text-on-primary-container px-4 py-1.5 rounded text-xs font-semibold transition-colors shadow-glow">
            Scan for New Modules
          </button>
        </div>
      </div>

      <!-- Top Metrics Cards -->
      <div class="grid grid-cols-12 gap-6">
        <div class="col-span-12 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="bg-surface-container-low border border-outline-variant p-4 rounded-lg shadow-glow">
            <p class="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest">Total Modules</p>
            <p class="text-2xl font-bold text-on-surface mt-1 font-mono">24</p>
            <p class="text-[10px] text-tertiary mt-1 flex items-center gap-1">
              <span class="material-symbols-outlined text-[12px]">trending_up</span> +2 new
            </p>
          </div>

          <div class="bg-surface-container-low border border-outline-variant p-4 rounded-lg shadow-glow">
            <p class="text-[10px] text-tertiary uppercase font-bold tracking-widest">Active</p>
            <p class="text-2xl font-bold text-tertiary mt-1 font-mono">18</p>
            <p class="text-[10px] text-tertiary mt-1 flex items-center gap-1">
              <span class="material-symbols-outlined text-[12px]">trending_up</span> +1 stable
            </p>
          </div>

          <div class="bg-surface-container-low border border-outline-variant p-4 rounded-lg shadow-glow">
            <p class="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest">Standby</p>
            <p class="text-2xl font-bold text-on-surface mt-1 font-mono">5</p>
          </div>

          <div class="bg-surface-container-low border border-outline-variant p-4 rounded-lg border-error/30 shadow-glow">
            <p class="text-[10px] text-error uppercase font-bold tracking-widest">Warning</p>
            <p class="text-2xl font-bold text-error mt-1 font-mono">1</p>
          </div>
        </div>

        <!-- Table Column (Left 8) -->
        <div class="col-span-12 lg:col-span-8 bg-surface-container-low border border-outline-variant rounded-xl overflow-hidden shadow-glow">
          <div class="p-4 border-b border-outline-variant bg-surface-container-high">
            <div class="flex items-center justify-between w-full">
              <h3 class="font-bold text-sm text-on-surface">Module Registry</h3>
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-bold text-on-surface-variant uppercase mr-2">Filter:</span>
                <button class="px-2 py-0.5 rounded bg-primary text-on-primary-container text-[10px] font-bold">ALL</button>
                <button class="px-2 py-0.5 rounded bg-surface-variant text-on-surface-variant text-[10px] font-bold hover:text-on-surface">ACTIVE</button>
                <button class="px-2 py-0.5 rounded bg-surface-variant text-on-surface-variant text-[10px] font-bold hover:text-on-surface">WARNING</button>
              </div>
            </div>
          </div>

          <!-- Selection Banner -->
          <div class="px-4 py-2 bg-primary/5 border-b border-outline-variant/30 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-primary">2 Modules Selected</span>
              <div class="h-4 w-px bg-outline-variant/30 mx-2" />
              <button class="text-[10px] font-bold uppercase tracking-wider text-on-surface hover:text-primary transition-colors">Restart Selected</button>
              <button class="text-[10px] font-bold uppercase tracking-wider text-error hover:opacity-80 transition-colors">Stop Selected</button>
            </div>
            <button class="text-xs text-on-surface-variant hover:text-on-surface">
              <span class="material-symbols-outlined text-sm">close</span>
            </button>
          </div>

          <table class="w-full text-left border-collapse">
            <thead class="bg-surface-container-highest border-b border-outline-variant/30">
              <tr class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest">
                <th class="px-4 py-3 w-8">
                  <input type="checkbox" checked class="rounded border-outline-variant bg-surface-container-high text-primary focus:ring-primary" />
                </th>
                <th class="px-4 py-3">Module Name</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3">Uptime</th>
                <th class="px-4 py-3">Version</th>
                <th class="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/10 font-mono text-xs">
              <tr class="bg-primary/5">
                <td class="px-4 py-4">
                  <input type="checkbox" checked class="rounded border-outline-variant bg-surface-container-high text-primary focus:ring-primary" />
                </td>
                <td class="px-4 py-4 font-bold text-primary">Core Engine</td>
                <td class="px-4 py-4 text-tertiary font-bold">Active</td>
                <td class="px-4 py-4 text-on-surface-variant">14d 02h</td>
                <td class="px-4 py-4 text-on-surface-variant">v2.4.1</td>
                <td class="px-4 py-4">
                  <span class="material-symbols-outlined text-sm cursor-pointer text-on-surface-variant hover:text-on-surface">more_vert</span>
                </td>
              </tr>
              <tr>
                <td class="px-4 py-4">
                  <input type="checkbox" checked class="rounded border-outline-variant bg-surface-container-high text-primary focus:ring-primary" />
                </td>
                <td class="px-4 py-4 font-bold text-on-surface">Auth Gateway</td>
                <td class="px-4 py-4 text-tertiary font-bold">Active</td>
                <td class="px-4 py-4 text-on-surface-variant">08d 11h</td>
                <td class="px-4 py-4 text-on-surface-variant">v1.9.0</td>
                <td class="px-4 py-4">
                  <span class="material-symbols-outlined text-sm cursor-pointer text-on-surface-variant hover:text-on-surface">more_vert</span>
                </td>
              </tr>
              <tr>
                <td class="px-4 py-4">
                  <input type="checkbox" class="rounded border-outline-variant bg-surface-container-high text-primary focus:ring-primary" />
                </td>
                <td class="px-4 py-4 font-bold text-on-surface">Data Ingest</td>
                <td class="px-4 py-4 text-error font-bold">Warning</td>
                <td class="px-4 py-4 text-on-surface-variant">00d 04h</td>
                <td class="px-4 py-4 text-on-surface-variant">v2.1.0</td>
                <td class="px-4 py-4">
                  <span class="material-symbols-outlined text-sm cursor-pointer text-on-surface-variant hover:text-on-surface">more_vert</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Details Column (Right 4) -->
        <div class="col-span-12 lg:col-span-4 space-y-4">
          <div class="bg-surface-container-low border border-primary/30 p-5 rounded-xl shadow-glow">
            <h3 class="font-bold text-sm text-primary mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined">settings_input_component</span> Core Engine Details
            </h3>

            <div class="space-y-5">
              <div class="space-y-1.5">
                <div class="flex justify-between text-xs">
                  <span class="text-on-surface-variant">CPU Usage</span>
                  <span class="text-on-surface font-mono font-bold">42%</span>
                  <span class="text-[10px] text-error flex items-center">-5% <span class="material-symbols-outlined text-[12px]">trending_down</span></span>
                </div>
                <div class="w-full bg-surface-variant h-1.5 rounded-full overflow-hidden">
                  <div class="bg-primary h-full w-[42%]" />
                </div>
              </div>

              <div class="space-y-1.5">
                <div class="flex justify-between text-xs">
                  <span class="text-on-surface-variant">Memory</span>
                  <span class="text-on-surface font-mono font-bold">1.2GB / 4GB</span>
                </div>
                <div class="w-full bg-surface-variant h-1.5 rounded-full overflow-hidden">
                  <div class="bg-tertiary h-full w-[30%]" />
                </div>
              </div>

              <div class="space-y-3 pt-3 border-t border-outline-variant/30">
                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold text-on-surface-variant uppercase">Log Level</label>
                  <select v-model="logLevel" class="bg-surface-container-high border border-outline-variant rounded px-2 py-1 text-xs text-on-surface focus:ring-1 focus:ring-primary outline-none font-mono">
                    <option value="Info">Info</option>
                    <option value="Debug">Debug</option>
                    <option value="Warning">Warning</option>
                    <option value="Error">Error</option>
                  </select>
                </div>

                <div class="flex flex-col gap-1">
                  <label class="text-[10px] font-bold text-on-surface-variant uppercase">Dependencies</label>
                  <div class="flex flex-wrap gap-1 font-mono">
                    <span class="px-2 py-0.5 bg-surface-variant rounded text-[10px] text-on-surface-variant">Auth-GW</span>
                    <span class="px-2 py-0.5 bg-surface-variant rounded text-[10px] text-on-surface-variant">DB-Cluster</span>
                  </div>
                </div>
              </div>

              <div class="grid grid-cols-1 gap-2 pt-3">
                <button class="w-full py-2 rounded bg-surface-container-highest border border-outline-variant text-xs font-bold hover:bg-surface-variant transition-colors text-on-surface">
                  RESTART MODULE
                </button>
                <button class="w-full py-2 rounded bg-surface-container-highest border border-outline-variant text-xs font-bold hover:bg-surface-variant transition-colors text-on-surface">
                  VIEW LOGS
                </button>
                <button class="w-full py-2 rounded border border-error/30 text-error text-xs font-bold hover:bg-error/10 transition-colors">
                  STOP SERVICE
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAppStore } from '@/core/store'

const store = useAppStore()
const logLevel = ref('Debug')

function reloadModules() {
  store.loadModules()
}
</script>
