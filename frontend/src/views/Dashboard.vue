<template>
  <div class="p-6 bg-background min-h-full space-y-5 text-on-surface animate-fade-in flex flex-col">
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

      <div class="flex flex-wrap items-center gap-2">
        <!-- Snap to Grid Toggle -->
        <label v-if="isCustomizing" class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-container-high text-xs font-semibold cursor-pointer select-none">
          <input type="checkbox" v-model="snapToGrid" class="rounded accent-primary" />
          <span>{{ t('snapToGrid') }}</span>
        </label>

        <!-- Reset Positions Button -->
        <button
          v-if="isCustomizing"
          @click="handleResetLayout"
          class="px-3 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-container-high text-on-surface hover:bg-surface-bright text-xs font-semibold flex items-center gap-1.5 transition-colors"
        >
          <span class="material-symbols-outlined text-sm">restart_alt</span>
          <span>{{ t('resetLayout') }}</span>
        </button>

        <!-- Customize Windows Toggle -->
        <button
          @click="isCustomizing = !isCustomizing"
          class="px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-glow"
          :class="isCustomizing ? 'bg-primary text-on-primary hover:opacity-90' : 'bg-surface-container-high border border-outline-variant/60 text-on-surface hover:bg-surface-bright'"
        >
          <span class="material-symbols-outlined text-sm">
            {{ isCustomizing ? 'check' : 'open_with' }}
          </span>
          <span>{{ isCustomizing ? t('doneCustomizing') : t('customizeDashboard') }}</span>
        </button>
      </div>
    </div>

    <!-- Customization Banner / Controls -->
    <div
      v-if="isCustomizing"
      class="p-4 rounded-xl bg-primary/10 border border-primary/30 space-y-2 animate-fade-in"
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
          v-for="w in activeWidgets"
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

    <!-- Desktop / Mobile Windows Canvas Container -->
    <div
      class="flex-1 w-full bg-surface-container-lowest/50 border border-outline-variant/40 rounded-2xl p-2"
      :class="isMobile ? 'flex flex-col gap-3 min-h-0' : 'min-h-[750px] relative overflow-auto shadow-inner'"
    >
      <!-- Grid Lines Background Pattern (Desktop only) -->
      <div v-if="!isMobile" class="absolute inset-0 pointer-events-none opacity-15 bg-[radial-gradient(#859397_1px,transparent_1px)] [background-size:20px_20px]" />

      <!-- Displayed Movable Widget Windows -->
      <template v-if="displayedWidgets.length > 0">
        <WidgetRenderer
          v-for="(w, idx) in displayedWidgets"
          :key="w.id"
          :widget="w"
          :rect="getWidgetRect(w.id, idx)"
          :is-customizing="isCustomizing && !isMobile"
          :is-hidden="isWidgetHidden(w.id)"
          :is-mobile="isMobile"
          @toggle-visibility="toggleVisibility(w.id)"
          @update-rect="(rect) => updateWidgetRect(w.id, rect, idx)"
          @bring-to-front="bringToFront(w.id)"
        />
      </template>

      <!-- Empty State: All windows hidden -->
      <div
        v-else-if="activeWidgets.length > 0 && hiddenWidgetIds.size === activeWidgets.length"
        class="flex flex-col items-center justify-center p-8 text-center space-y-3"
        :class="isMobile ? 'py-12' : 'absolute inset-0'"
      >
        <span class="material-symbols-outlined text-4xl text-outline">visibility_off</span>
        <p class="text-xs text-on-surface-variant font-medium max-w-sm">
          {{ t('allWidgetsHidden') }}
        </p>
      </div>

      <!-- Empty State: No widgets loaded -->
      <div
        v-else-if="activeWidgets.length === 0"
        class="flex flex-col items-center justify-center p-8 text-center space-y-2"
        :class="isMobile ? 'py-12' : 'absolute inset-0'"
      >
        <span class="material-symbols-outlined text-4xl text-outline">widgets</span>
        <p class="text-xs text-on-surface-variant font-medium">
          {{ t('noWidgets') }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from '@/core/i18n'
import { loadModuleWidgets, activeWidgets, type ModuleWidget } from '@/modules/widgets'
import WidgetRenderer from '@/components/common/WidgetRenderer.vue'
import { useWidgetLayout } from '@/composables/useWidgetLayout'

const { t } = useI18n()

const {
  hiddenWidgetIds,
  isCustomizing,
  snapToGrid,
  isMobile,
  toggleVisibility,
  isWidgetHidden,
  bringToFront,
  getWidgetRect,
  updateWidgetRect,
  resetLayout,
} = useWidgetLayout()

// Filter widgets depending on customization mode
const displayedWidgets = computed<ModuleWidget[]>(() => {
  if (isCustomizing.value) {
    return activeWidgets.value
  }
  return activeWidgets.value.filter((w) => !isWidgetHidden(w.id))
})

function handleResetLayout() {
  resetLayout(activeWidgets.value)
}

onMounted(() => {
  loadModuleWidgets()
})
</script>
