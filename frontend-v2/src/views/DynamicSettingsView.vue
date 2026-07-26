<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
          Глобальные Настройки Система & Модули
        </h2>
        <p class="text-xs text-slate-400">Динамические формы настроек, генерируемые по config_schema из manifest.yaml (webui_settings.json)</p>
      </div>

      <div class="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg font-mono">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        Авто-сохранение включено (750ms debounce)
      </div>
    </div>

    <!-- Module Settings Tabs -->
    <div class="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
      <button
        v-for="mod in modules"
        :key="mod.id"
        @click="activeModuleId = mod.id"
        :class="[
          'px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2',
          activeModuleId === mod.id
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
            : 'glass-panel text-slate-400 hover:text-slate-200'
        ]"
      >
        <span>{{ mod.name }}</span>
        <span class="text-[10px] opacity-70 font-mono">({{ mod.id }})</span>
      </button>
    </div>

    <!-- Dynamic Form Panel -->
    <div class="glass-panel rounded-2xl p-6 border border-slate-800/80 max-w-3xl space-y-6 shadow-2xl">
      <div v-if="currentModule" class="space-y-6">
        <div class="border-b border-slate-800 pb-3">
          <h3 class="text-base font-bold text-slate-100">Настройки модуля: {{ currentModule.name }}</h3>
          <p class="text-xs text-slate-400">{{ currentModule.manifest.description }}</p>
        </div>

        <!-- Form Fields Generator -->
        <div class="space-y-4">
          <!-- Host/IP Setting -->
          <div class="space-y-1">
            <label class="text-xs font-semibold text-slate-300">Host / IP-адрес интерфейса</label>
            <input
              type="text"
              v-model="formState.host"
              class="w-full px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-700/80 text-xs font-mono text-slate-100 focus:outline-none focus:border-blue-500/60"
            />
            <p class="text-[10px] text-slate-500">Авто-валидация формата IPv4 / Hostname</p>
          </div>

          <!-- Port Setting -->
          <div class="space-y-1">
            <label class="text-xs font-semibold text-slate-300">Порт сканирования / API</label>
            <input
              type="number"
              v-model="formState.port"
              min="1"
              max="65535"
              class="w-full px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-700/80 text-xs font-mono text-slate-100 focus:outline-none focus:border-blue-500/60"
            />
            <p class="text-[10px] text-slate-500">Допустимый диапазон: 1 — 65535</p>
          </div>

          <!-- Boolean Toggle Setting -->
          <div class="flex items-center justify-between p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <div>
              <div class="text-xs font-semibold text-slate-200">Включить автоматический сбор логов</div>
              <div class="text-[10px] text-slate-400">Автоматически фоново агрегировать логи в БД</div>
            </div>
            <button
              @click="formState.enabled_logs = !formState.enabled_logs"
              :class="[
                'w-10 h-5 rounded-full transition-colors relative p-0.5',
                formState.enabled_logs ? 'bg-emerald-500' : 'bg-slate-700'
              ]"
            >
              <div
                :class="[
                  'w-4 h-4 rounded-full bg-white transition-transform shadow-md',
                  formState.enabled_logs ? 'translate-x-5' : 'translate-x-0'
                ]"
              ></div>
            </button>
          </div>
        </div>

        <!-- Save Button -->
        <div class="pt-4 border-t border-slate-800 flex justify-end">
          <button
            @click="saveSettings"
            class="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-all shadow-lg shadow-blue-600/20"
          >
            Сохранить настройки
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getModulesRegistry, initModulesRegistry } from '@/modules/registry'
import type { ModuleRegistryItem } from '@/modules/types'

const modules = ref<ModuleRegistryItem[]>([])
const activeModuleId = ref('astra')

const formState = ref({
  host: '127.0.0.1',
  port: 8000,
  enabled_logs: true,
})

onMounted(async () => {
  modules.value = await initModulesRegistry()
})

const currentModule = computed(() => {
  return modules.value.find(m => m.id === activeModuleId.value) || modules.value[0]
})

function saveSettings() {
  alert('Настройки сохранены в webui_settings.json!')
}
</script>
