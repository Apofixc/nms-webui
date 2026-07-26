<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          Менеджер Модулей NMS
          <span class="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded font-mono">
            {{ modules.length }} загружено
          </span>
        </h2>
        <p class="text-xs text-slate-400">Управление подгружаемыми плагинами, субмодулями и их зависимостями (manifest.yaml)</p>
      </div>

      <button
        @click="refreshRegistry"
        class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 transition-all flex items-center gap-2"
      >
        🔄 Обновить реестр
      </button>
    </div>

    <!-- Modules Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="mod in modules"
        :key="mod.id"
        class="glass-panel rounded-2xl p-5 border border-slate-800/80 flex flex-col justify-between space-y-4 hover:border-blue-500/40 transition-all shadow-xl"
      >
        <!-- Top Title & Toggle -->
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-sm font-bold text-slate-100">{{ mod.name }}</h3>
              <span
                :class="[
                  'text-[9px] px-1.5 py-0.5 rounded font-mono font-semibold uppercase',
                  mod.is_submodule ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                ]"
              >
                {{ mod.is_submodule ? 'Submodule' : mod.manifest.type }}
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-1 line-clamp-2">{{ mod.manifest.description || 'Плагин системы NMS' }}</p>
          </div>

          <!-- Active Toggle -->
          <button
            @click="toggleModule(mod.id)"
            :class="[
              'w-11 h-6 rounded-full transition-colors relative p-0.5 flex-shrink-0',
              mod.manifest.enabled ? 'bg-emerald-500' : 'bg-slate-700'
            ]"
          >
            <div
              :class="[
                'w-5 h-5 rounded-full bg-white transition-transform shadow-md',
                mod.manifest.enabled ? 'translate-x-5' : 'translate-x-0'
              ]"
            ></div>
          </button>
        </div>

        <!-- Manifest Info Pills -->
        <div class="space-y-2 text-xs pt-2 border-t border-slate-800/60 font-mono">
          <div class="flex items-center justify-between text-slate-400">
            <span>ID Модуля:</span>
            <span class="text-slate-200 font-bold">{{ mod.id }}</span>
          </div>

          <div class="flex items-center justify-between text-slate-400">
            <span>Версия манифеста:</span>
            <span class="text-slate-300">v{{ mod.version }}</span>
          </div>

          <div v-if="mod.parent_id" class="flex items-center justify-between text-slate-400">
            <span>Родительский модуль:</span>
            <span class="text-amber-400 font-semibold">{{ mod.parent_id }}</span>
          </div>

          <div class="flex items-center justify-between text-slate-400">
            <span>Зависимости (deps):</span>
            <span class="text-slate-300">
              {{ mod.manifest.deps.length ? mod.manifest.deps.join(', ') : 'None' }}
            </span>
          </div>

          <div class="flex items-center justify-between text-slate-400">
            <span>Статус (Health):</span>
            <span class="text-emerald-400 flex items-center gap-1 font-sans text-[11px]">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              HEALTHY
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getModulesRegistry, initModulesRegistry } from '@/modules/registry'
import type { ModuleRegistryItem } from '@/modules/types'

const modules = ref<ModuleRegistryItem[]>([])

onMounted(async () => {
  modules.value = await initModulesRegistry()
})

async function refreshRegistry() {
  modules.value = await initModulesRegistry()
}

function toggleModule(id: string) {
  const item = modules.value.find(m => m.id === id)
  if (item) {
    item.manifest.enabled = !item.manifest.enabled
  }
}
</script>
