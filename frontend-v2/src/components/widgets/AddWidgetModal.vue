<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
    <div class="glass-panel w-full max-w-xl rounded-2xl border border-slate-700/80 p-6 shadow-2xl flex flex-col gap-5">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h3 class="text-base font-bold text-slate-100">Добавить виджет на Дашборд</h3>
          <p class="text-xs text-slate-400">Каталог виджетов от включенных модулей NMS</p>
        </div>
        <button @click="$emit('close')" class="text-slate-400 hover:text-white p-1">
          ✕
        </button>
      </div>

      <!-- Widget List -->
      <div class="space-y-3 max-h-96 overflow-y-auto pr-1">
        <div
          v-for="widget in availableWidgets"
          :key="widget.id"
          class="p-4 rounded-xl glass-panel-hover border border-slate-800/80 bg-slate-900/60 flex items-center justify-between gap-4"
        >
          <div>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-100">{{ widget.title }}</span>
              <span class="text-[9px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded">
                {{ widget.module_name }}
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-1">{{ widget.description }}</p>
          </div>
          <button
            @click="handleAdd(widget.id)"
            class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm flex-shrink-0"
          >
            + Добавить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getAvailableWidgets, addWidgetToDashboard } from '@/modules/widgets'

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits(['close'])

const availableWidgets = computed(() => getAvailableWidgets())

function handleAdd(widgetId: string) {
  addWidgetToDashboard(widgetId)
  emit('close')
}
</script>
