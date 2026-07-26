<template>
  <div class="space-y-6">
    <!-- Top Dashboard Bar -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-slate-100">Главный Дашборд NMS</h2>
        <p class="text-xs text-slate-400">Кастомизируемый обзор метрик и телеметрии активных модулей</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="showModal = true"
          class="px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-blue-600/20 transition-all flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Добавить виджет
        </button>
      </div>
    </div>

    <!-- Widgets Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="item in placedWidgets"
        :key="item.instance_id"
        :class="[
          'glass-panel rounded-2xl p-4 border border-slate-800/80 relative group shadow-xl flex flex-col justify-between transition-all duration-200 hover:border-slate-700',
          item.size === 'lg' ? 'md:col-span-2 lg:col-span-2' : '',
          item.size === 'xl' ? 'md:col-span-2 lg:col-span-3' : ''
        ]"
      >
        <!-- Widget Top Drag/Remove Header -->
        <div class="flex items-center justify-between border-b border-slate-800/60 pb-2 mb-3">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-blue-400"></span>
            <span class="text-xs font-semibold text-slate-200">{{ getWidgetTitle(item.widget_id) }}</span>
          </div>
          <button
            @click="removeWidget(item.instance_id)"
            class="text-slate-500 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity p-1 text-xs"
            title="Удалить виджет"
          >
            ✕
          </button>
        </div>

        <!-- Widget Component Body -->
        <div class="flex-1 min-h-[140px]">
          <component :is="getWidgetComponent(item.widget_id)" />
        </div>
      </div>
    </div>

    <!-- Add Widget Modal -->
    <AddWidgetModal :isOpen="showModal" @close="showModal = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { getPlacedWidgets, getAvailableWidgets, removeWidgetFromDashboard } from '@/modules/widgets'
import BitrateWidget from './BitrateWidget.vue'
import SignalWidget from './SignalWidget.vue'
import ChannelTableWidget from './ChannelTableWidget.vue'
import LogWidget from './LogWidget.vue'
import AddWidgetModal from './AddWidgetModal.vue'

const showModal = ref(false)
const placedWidgets = computed(() => getPlacedWidgets().value)
const availableWidgets = computed(() => getAvailableWidgets())

const componentMap: Record<string, any> = {
  BitrateWidget,
  SignalWidget,
  ChannelTableWidget,
  LogWidget,
}

function getWidgetTitle(widgetId: string) {
  const w = availableWidgets.value.find(item => item.id === widgetId)
  return w?.title || 'Виджет'
}

function getWidgetComponent(widgetId: string) {
  const w = availableWidgets.value.find(item => item.id === widgetId)
  if (w && componentMap[w.component]) {
    return componentMap[w.component]
  }
  return BitrateWidget
}

function removeWidget(instanceId: string) {
  removeWidgetFromDashboard(instanceId)
}
</script>
