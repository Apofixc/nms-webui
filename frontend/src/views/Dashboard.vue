<template>
  <div class="p-6 bg-background min-h-full space-y-6 text-on-surface animate-fade-in">
    <!-- Dashboard Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Active Faults - Left Column -->
      <div class="lg:col-span-4 flex flex-col">
        <div class="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-glow flex flex-col h-[360px]">
          <div class="flex items-center justify-between mb-4 border-b border-outline-variant/60 pb-3 flex-shrink-0">
            <h2 class="font-bold text-base text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-error">warning</span>
              <span>{{ t('activeFaults') }}</span>
            </h2>
            <span class="bg-error-container text-on-error-container font-mono text-xs px-2 py-0.5 rounded font-semibold">{{ t('criticalCount') }}</span>
          </div>

          <div class="space-y-3 overflow-y-auto pr-1 flex-1">
            <div class="bg-surface-container-high p-3 rounded-lg border-l-4 border-error">
              <div class="flex justify-between items-start mb-1">
                <span class="font-mono text-xs font-semibold text-error">NODE-X-77</span>
                <span class="font-mono text-[10px] text-outline">10:42:01</span>
              </div>
              <p class="text-xs text-on-surface-variant">{{ t('activeFault1') }}</p>
            </div>

            <div class="bg-surface-container-high p-3 rounded-lg border-l-4 border-error">
              <div class="flex justify-between items-start mb-1">
                <span class="font-mono text-xs font-semibold text-error">ROUTER-CORE-2</span>
                <span class="font-mono text-[10px] text-outline">10:39:14</span>
              </div>
              <p class="text-xs text-on-surface-variant">{{ t('activeFault2') }}</p>
            </div>

            <div class="bg-surface-container-high p-3 rounded-lg border-l-4 border-amber-400">
              <div class="flex justify-between items-start mb-1">
                <span class="font-mono text-xs font-semibold text-amber-400">SW-DIST-A</span>
                <span class="font-mono text-[10px] text-outline">10:15:22</span>
              </div>
              <p class="text-xs text-on-surface-variant">{{ t('activeFault3') }}</p>
            </div>

            <div class="bg-surface-container-high p-3 rounded-lg border-l-4 border-amber-400">
              <div class="flex justify-between items-start mb-1">
                <span class="font-mono text-xs font-semibold text-amber-400">FW-EDGE-1</span>
                <span class="font-mono text-[10px] text-outline">09:55:00</span>
              </div>
              <p class="text-xs text-on-surface-variant">{{ t('activeFault4') }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Center Column -->
      <div class="lg:col-span-8 flex flex-col gap-6">
        <!-- Network Topology Card -->
        <div class="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 h-[360px] flex flex-col relative overflow-hidden shadow-glow">
          <div class="flex items-center justify-between mb-4 z-10 relative border-b border-outline-variant/60 pb-3 flex-shrink-0">
            <h2 class="font-bold text-base text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">hub</span>
              <span>{{ t('topologyMap') }}</span>
            </h2>
            <div class="flex gap-2">
              <button class="px-2.5 py-1 text-xs bg-surface-variant text-on-surface rounded hover:bg-surface-bright transition-colors font-mono">{{ t('zoomIn') }}</button>
              <button class="px-2.5 py-1 text-xs bg-surface-variant text-on-surface rounded hover:bg-surface-bright transition-colors font-mono">{{ t('zoomOut') }}</button>
            </div>
          </div>

          <!-- Topology Diagram -->
          <div class="flex-1 bg-surface-container-lowest rounded-lg border border-outline-variant/40 relative flex items-center justify-center overflow-hidden">
            <div class="absolute inset-0 opacity-20 bg-[radial-gradient(#859397_1px,transparent_1px)] [background-size:24px_24px]" />
            <div class="relative w-full h-full max-w-lg mx-auto">
              <!-- Central Core Router Node -->
              <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-14 h-14 rounded-full bg-surface-container border-2 border-primary flex items-center justify-center z-10 shadow-glow">
                <span class="material-symbols-outlined text-primary">router</span>
              </div>
              <!-- Edge Nodes -->
              <div class="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-surface-container border border-tertiary flex items-center justify-center z-10">
                <span class="material-symbols-outlined text-tertiary text-sm">dns</span>
              </div>
              <div class="absolute top-1/4 left-3/4 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-surface-container border border-error flex items-center justify-center z-10">
                <span class="material-symbols-outlined text-error text-sm">warning</span>
              </div>
              <div class="absolute top-3/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-surface-container border border-tertiary flex items-center justify-center z-10">
                <span class="material-symbols-outlined text-tertiary text-sm">dns</span>
              </div>
              <div class="absolute top-3/4 left-3/4 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-surface-container border border-tertiary flex items-center justify-center z-10">
                <span class="material-symbols-outlined text-tertiary text-sm">dns</span>
              </div>

              <!-- Topology Connections SVG -->
              <svg class="absolute inset-0 w-full h-full pointer-events-none z-0">
                <line class="opacity-50" stroke="#61f6b9" stroke-dasharray="4 4" stroke-width="2" x1="25%" x2="50%" y1="25%" y2="50%" />
                <line class="opacity-80" stroke="#ffb4ab" stroke-width="2" x1="75%" x2="50%" y1="25%" y2="50%" />
                <line class="opacity-50" stroke="#61f6b9" stroke-width="2" x1="25%" x2="50%" y1="75%" y2="50%" />
                <line class="opacity-50" stroke="#61f6b9" stroke-width="2" x1="75%" x2="50%" y1="75%" y2="50%" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom Row: Metrics & Devices -->
      <div class="lg:col-span-12 grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Throughput Chart Card -->
        <div class="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 flex flex-col shadow-glow">
          <h2 class="font-bold text-sm text-on-surface flex items-center gap-2 mb-3 border-b border-outline-variant/60 pb-2">
            <span class="material-symbols-outlined text-primary">insights</span>
            <span>{{ t('throughput') }}</span>
          </h2>
          <div class="flex-1 bg-surface-container-lowest rounded-lg border border-outline-variant/40 relative p-3 flex items-end h-32">
            <svg class="w-full h-24" preserveAspectRatio="none" viewBox="0 0 100 40">
              <path d="M0,35 Q10,20 20,25 T40,15 T60,20 T80,5 T100,10 L100,40 L0,40 Z" fill="rgba(138, 235, 255, 0.15)" />
              <path d="M0,35 Q10,20 20,25 T40,15 T60,20 T80,5 T100,10" fill="none" stroke="#8aebff" stroke-width="2" />
            </svg>
          </div>
        </div>

        <!-- Device Status Summary -->
        <div class="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 flex flex-col shadow-glow">
          <h2 class="font-bold text-sm text-on-surface flex items-center gap-2 mb-3 border-b border-outline-variant/60 pb-2">
            <span class="material-symbols-outlined text-tertiary">devices</span>
            <span>{{ t('deviceStatus') }}</span>
          </h2>
          <div class="space-y-3 justify-center flex-1 flex flex-col">
            <div>
              <div class="flex justify-between font-mono text-xs mb-1">
                <span class="text-tertiary font-semibold">{{ t('online') }} (85%)</span>
                <span class="text-on-surface">1,420</span>
              </div>
              <div class="h-2 bg-surface-variant rounded-full overflow-hidden">
                <div class="h-full bg-tertiary w-[85%]" />
              </div>
            </div>

            <div>
              <div class="flex justify-between font-mono text-xs mb-1">
                <span class="text-amber-400 font-semibold">{{ t('statusDegraded') }} (10%)</span>
                <span class="text-on-surface">167</span>
              </div>
              <div class="h-2 bg-surface-variant rounded-full overflow-hidden">
                <div class="h-full bg-amber-400 w-[10%]" />
              </div>
            </div>

            <div>
              <div class="flex justify-between font-mono text-xs mb-1">
                <span class="text-error font-semibold">{{ t('offline') }} (5%)</span>
                <span class="text-on-surface">84</span>
              </div>
              <div class="h-2 bg-surface-variant rounded-full overflow-hidden">
                <div class="h-full bg-error w-[5%]" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Modules Section -->
      <div class="lg:col-span-12 bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-glow">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3 mb-3">
          <h2 class="font-bold text-sm text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">view_module</span>
            <span>{{ t('modulesCount') }} ({{ loadedModuleIds.length }})</span>
          </h2>
          <router-link to="/settings/modules" class="text-xs font-mono text-primary hover:underline">{{ t('manage') }} &rarr;</router-link>
        </div>

        <div v-if="loadedModuleIds.length === 0" class="text-center py-4">
          <p class="text-xs text-on-surface-variant font-mono">{{ t('noLoadedModulesIn') }} <code class="text-primary bg-primary/10 px-1 py-0.5 rounded">backend/modules/</code></p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div
            v-for="mod in modules"
            :key="mod.id"
            class="flex items-center justify-between px-3 py-2 rounded-lg bg-surface-container-high border border-outline-variant/40"
          >
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full" :class="mod.enabled ? 'bg-tertiary' : 'bg-outline'" />
              <span class="text-xs font-semibold text-on-surface">{{ mod.name }}</span>
              <span class="font-mono text-[10px] text-on-surface-variant">v{{ mod.version }}</span>
            </div>
            <span :class="['text-[11px] px-2 py-0.5 rounded font-mono', mod.enabled ? 'bg-tertiary/20 text-tertiary' : 'bg-surface-variant text-outline']">
              {{ mod.enabled ? t('active') : t('disabled') }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/core/store'
import { useI18n } from '@/core/i18n'
import { storeToRefs } from 'pinia'

const store = useAppStore()
const { t } = useI18n()
const { backendOk, modules, loadedModuleIds } = storeToRefs(store)
</script>
