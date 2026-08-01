<template>
  <div class="p-6 bg-background min-h-full space-y-6 text-on-surface animate-fade-in">
    <!-- Header / Toolbar -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-outline-variant/60 pb-4">
      <div>
        <h1 class="font-bold text-xl text-on-surface flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">dashboard</span>
          <span>{{ t('dashboard') }}</span>
        </h1>
        <p class="text-xs text-on-surface-variant">
          {{ t('widgetsTitle') }}
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          v-if="isCustomizing"
          @click="handleResetLayout"
          class="px-3 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-container-high text-on-surface hover:bg-surface-bright text-xs font-semibold flex items-center gap-1.5 transition-colors"
        >
          <span class="material-symbols-outlined text-sm">restart_alt</span>
          <span>{{ t('resetLayout') }}</span>
        </button>

        <button
          @click="isCustomizing = !isCustomizing"
          class="px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-glow"
          :class="isCustomizing ? 'bg-primary text-on-primary hover:opacity-90' : 'bg-surface-container-high border border-outline-variant/60 text-on-surface hover:bg-surface-bright'"
        >
          <span class="material-symbols-outlined text-sm">
            {{ isCustomizing ? 'check' : 'tune' }}
          </span>
          <span>{{ isCustomizing ? t('doneCustomizing') : t('customizeDashboard') }}</span>
        </button>
      </div>
    </div>

    <!-- Customization Banner / Controls -->
    <div
      v-if="isCustomizing"
      class="p-4 rounded-xl bg-primary/10 border border-primary/30 space-y-3 animate-fade-in"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 text-xs font-semibold text-primary">
          <span class="material-symbols-outlined text-base">info</span>
          <span>{{ t('dragToReorder') }}</span>
        </div>
        <span class="text-[11px] font-mono text-on-surface-variant">
          {{ hiddenWidgetIds.size > 0 ? t('hiddenWidgetsCount', { count: hiddenWidgetIds.size }) : '' }}
        </span>
      </div>

      <div class="flex flex-wrap gap-2 pt-1">
        <button
          v-for="w in sortedWidgets"
          :key="w.id"
          @click="toggleVisibility(w.id)"
          class="px-2.5 py-1 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition-colors"
          :class="isWidgetHidden(w.id) ? 'bg-surface-variant text-on-surface-variant border-outline-variant/40 hover:border-primary' : 'bg-primary/20 text-primary border-primary/40 font-semibold'"
        >
          <span class="material-symbols-outlined text-xs">
            {{ isWidgetHidden(w.id) ? 'visibility_off' : 'visibility' }}
          </span>
          <span>{{ t(w.title || w.id) }}</span>
        </button>
      </div>
    </div>

    <!-- Active Widgets Section -->
    <div v-if="displayedWidgets.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <WidgetRenderer
        v-for="(w, idx) in displayedWidgets"
        :key="w.id"
        :widget="w"
        :is-customizing="isCustomizing"
        :is-hidden="isWidgetHidden(w.id)"
        @toggle-visibility="toggleVisibility(w.id)"
        @drag-start="handleDragStart(idx)"
        @drag-over="handleDragOver"
        @drop="handleDrop(idx)"
      />
    </div>

    <!-- Empty State: All widgets hidden -->
    <div
      v-else-if="activeWidgets.length > 0 && hiddenWidgetIds.size === activeWidgets.length"
      class="p-8 text-center rounded-xl bg-surface-container-low border border-outline-variant/60 space-y-3"
    >
      <span class="material-symbols-outlined text-4xl text-outline">visibility_off</span>
      <p class="text-xs text-on-surface-variant font-medium">
        {{ t('allWidgetsHidden') }}
      </p>
    </div>

    <!-- Empty State: No widgets loaded -->
    <div
      v-else-if="activeWidgets.length === 0"
      class="p-8 text-center rounded-xl bg-surface-container-low border border-outline-variant/60 space-y-2"
    >
      <span class="material-symbols-outlined text-4xl text-outline">widgets</span>
      <p class="text-xs text-on-surface-variant font-medium">
        {{ t('noWidgets') }}
      </p>
    </div>

    <!-- Installed Modules Overview Section -->
    <div class="bg-surface-container-low border border-outline-variant/60 rounded-xl p-5 shadow-glow">
      <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3 mb-3">
        <h2 class="font-bold text-sm text-on-surface flex items-center gap-2">
          <span class="material-symbols-outlined text-primary">view_module</span>
          <span>{{ t('modulesCount') }} ({{ loadedModuleIds.length }})</span>
        </h2>
        <router-link to="/settings/modules" class="text-xs font-mono text-primary hover:underline">
          {{ t('manage') }} &rarr;
        </router-link>
      </div>

      <div v-if="loadedModuleIds.length === 0" class="text-center py-4">
        <p class="text-xs text-on-surface-variant font-mono">
          {{ t('noLoadedModulesIn') }} <code class="text-primary bg-primary/10 px-1 py-0.5 rounded">backend/modules/</code>
        </p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div
          v-for="mod in modules"
          :key="mod.id"
          class="flex items-center justify-between px-3 py-2 rounded-lg bg-surface-container-high border border-outline-variant/40"
        >
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full" :class="mod.enabled ? 'bg-tertiary' : 'bg-outline'" />
            <span class="text-xs font-semibold text-on-surface">{{ translateModuleName(mod.name) }}</span>
            <span class="font-mono text-[10px] text-on-surface-variant">v{{ mod.version }}</span>
          </div>
          <span :class="['text-[11px] px-2 py-0.5 rounded font-mono', mod.enabled ? 'bg-tertiary/20 text-tertiary' : 'bg-surface-variant text-outline']">
            {{ mod.enabled ? t('active') : t('disabled') }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAppStore } from '@/core/store'
import { useI18n } from '@/core/i18n'
import { storeToRefs } from 'pinia'
import { loadModuleWidgets, activeWidgets, type ModuleWidget } from '@/modules/widgets'
import WidgetRenderer from '@/components/common/WidgetRenderer.vue'
import { useWidgetLayout } from '@/composables/useWidgetLayout'

const store = useAppStore()
const { t, translateModuleName } = useI18n()
const { modules, loadedModuleIds } = storeToRefs(store)

const {
  hiddenWidgetIds,
  widgetOrder,
  isCustomizing,
  toggleVisibility,
  isWidgetHidden,
  moveWidget,
  resetLayout,
  syncAvailableWidgets,
} = useWidgetLayout()

const draggedIndex = ref<number | null>(null)

// Sort all active widgets according to saved order
const sortedWidgets = computed<ModuleWidget[]>(() => {
  if (widgetOrder.value.length === 0) {
    return activeWidgets.value
  }
  const map = new Map(activeWidgets.value.map((w) => [w.id, w]))
  const result: ModuleWidget[] = []

  // First add in user order
  widgetOrder.value.forEach((id) => {
    const w = map.get(id)
    if (w) {
      result.push(w)
      map.delete(id)
    }
  })
  // Then append any remaining new widgets
  map.forEach((w) => result.push(w))
  return result
})

// Filter widgets depending on customization mode
const displayedWidgets = computed<ModuleWidget[]>(() => {
  if (isCustomizing.value) {
    return sortedWidgets.value
  }
  return sortedWidgets.value.filter((w) => !isWidgetHidden(w.id))
})

watch(
  activeWidgets,
  (newWidgets) => {
    syncAvailableWidgets(newWidgets)
  },
  { immediate: true }
)

function handleDragStart(index: number) {
  draggedIndex.value = index
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
}

function handleDrop(targetIndex: number) {
  if (draggedIndex.value !== null && draggedIndex.value !== targetIndex) {
    moveWidget(draggedIndex.value, targetIndex)
  }
  draggedIndex.value = null
}

function handleResetLayout() {
  resetLayout(activeWidgets.value)
}

onMounted(() => {
  loadModuleWidgets()
})
</script>
