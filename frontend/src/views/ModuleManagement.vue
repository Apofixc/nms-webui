<template>
  <div class="min-h-full p-6 flex gap-6 max-w-6xl w-full mx-auto animate-fade-in text-on-surface">
    <!-- Secondary Settings Rail (Left) -->
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
    </aside>

    <!-- Configuration Area -->
    <div class="flex-1 flex flex-col gap-6 min-w-0">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="font-bold text-2xl text-on-surface">Module Management</h1>
          <p class="text-xs text-on-surface-variant mt-1">Monitor and control system-level service modules.</p>
        </div>
        <button @click="reloadModules" class="bg-primary-container hover:bg-primary-fixed text-on-primary-container px-4 py-1.5 rounded text-xs font-semibold transition-colors shadow-glow">
          Scan for New Modules
        </button>
      </div>

      <!-- Metrics Grid -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
          <p class="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest">Total Modules</p>
          <p class="text-2xl font-bold text-on-surface mt-1 font-mono">{{ modules.length }}</p>
        </div>
        <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
          <p class="text-[10px] text-tertiary uppercase font-bold tracking-widest">Active</p>
          <p class="text-2xl font-bold text-tertiary mt-1 font-mono">{{ activeModulesCount }}</p>
        </div>
        <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
          <p class="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest">Standby</p>
          <p class="text-2xl font-bold text-on-surface mt-1 font-mono">{{ modules.length - activeModulesCount }}</p>
        </div>
        <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl border-error/30 shadow-glow">
          <p class="text-[10px] text-error uppercase font-bold tracking-widest font-mono">API Connection</p>
          <p class="text-sm font-bold mt-2 font-mono" :class="backendOk ? 'text-tertiary' : 'text-error'">
            {{ backendOk ? 'CONNECTED' : 'DISCONNECTED' }}
          </p>
        </div>
      </div>

      <!-- Modules Table & Details Grid -->
      <div class="grid grid-cols-12 gap-6">
        <div class="col-span-12 lg:col-span-8 bg-surface-container-low border border-outline-variant rounded-xl overflow-hidden shadow-glow">
          <div class="p-4 border-b border-outline-variant bg-surface-container-high flex items-center justify-between">
            <h3 class="font-bold text-sm text-on-surface">Module Registry</h3>
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-bold text-on-surface-variant uppercase">Filter:</span>
              <button class="px-2 py-0.5 rounded bg-primary text-on-primary-container text-[10px] font-bold">ALL</button>
              <button class="px-2 py-0.5 rounded bg-surface-variant text-on-surface-variant text-[10px] font-bold hover:text-on-surface">ACTIVE</button>
            </div>
          </div>

          <table class="w-full text-left border-collapse">
            <thead class="bg-surface-container-highest border-b border-outline-variant/30 text-[11px] font-bold text-on-surface-variant uppercase tracking-widest">
              <tr>
                <th class="px-4 py-3">Module Name</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3">Version</th>
                <th class="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/20 font-mono text-xs">
              <tr v-for="mod in modules" :key="mod.id" class="hover:bg-surface-container-highest/50 transition-colors">
                <td class="px-4 py-3.5 font-bold" :class="mod.enabled ? 'text-primary' : 'text-on-surface'">
                  {{ mod.name }}
                </td>
                <td class="px-4 py-3.5 font-bold" :class="mod.enabled ? 'text-tertiary' : 'text-outline'">
                  {{ mod.enabled ? 'Active' : 'Disabled' }}
                </td>
                <td class="px-4 py-3.5 text-on-surface-variant">v{{ mod.version }}</td>
                <td class="px-4 py-3.5 text-right">
                  <button
                    @click="toggleModule(mod.id)"
                    class="px-2.5 py-1 rounded border border-outline-variant text-[11px] hover:border-primary hover:text-primary transition-colors"
                  >
                    {{ mod.enabled ? 'Disable' : 'Enable' }}
                  </button>
                </td>
              </tr>

              <tr v-if="modules.length === 0">
                <td colspan="4" class="px-4 py-6 text-center text-on-surface-variant">
                  No backend modules installed in backend/modules/
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Module Controls Side Panel -->
        <div class="col-span-12 lg:col-span-4 space-y-4">
          <div class="bg-surface-container-low border border-primary/30 p-5 rounded-xl shadow-glow">
            <h3 class="font-bold text-sm text-primary mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined">settings_input_component</span> Core Engine Details
            </h3>

            <div class="space-y-4">
              <div class="space-y-1.5">
                <div class="flex justify-between text-xs font-mono">
                  <span class="text-on-surface-variant">CPU Usage</span>
                  <span class="text-on-surface font-bold">14.2%</span>
                </div>
                <div class="w-full bg-surface-variant h-1.5 rounded-full overflow-hidden">
                  <div class="bg-primary h-full w-[14.2%]" />
                </div>
              </div>

              <div class="space-y-1.5">
                <div class="flex justify-between text-xs font-mono">
                  <span class="text-on-surface-variant font-mono">Memory</span>
                  <span class="text-on-surface font-bold">1.2GB / 4GB</span>
                </div>
                <div class="w-full bg-surface-variant h-1.5 rounded-full overflow-hidden">
                  <div class="bg-tertiary h-full w-[30%]" />
                </div>
              </div>

              <div class="pt-3 border-t border-outline-variant/30 space-y-2">
                <button @click="reloadModules" class="w-full py-2 rounded bg-surface-container-highest border border-outline-variant text-xs font-bold hover:bg-surface-variant transition-colors text-on-surface">
                  RESTART SERVICE
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
import { computed } from 'vue'
import { useAppStore } from '@/core/store'
import { storeToRefs } from 'pinia'

const store = useAppStore()
const { backendOk, modules } = storeToRefs(store)

const activeModulesCount = computed(() => modules.value.filter(m => m.enabled).length)

function reloadModules() {
  store.loadModules()
}

function toggleModule(id: string) {
  const mod = modules.value.find(m => m.id === id)
  if (mod) {
    mod.enabled = !mod.enabled
  }
}
</script>
