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
        <!-- Add Widget Button -->
        <button
          @click="isCatalogOpen = true"
          class="px-3.5 py-1.5 rounded-lg bg-primary text-on-primary hover:opacity-90 text-xs font-semibold flex items-center gap-1.5 transition-opacity shadow-glow cursor-pointer"
        >
          <span class="material-symbols-outlined text-sm">add</span>
          <span>{{ t('addWidget') }}</span>
        </button>

        <!-- Snap to Grid Toggle in Customizing mode -->
        <label v-if="isCustomizing" class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-container-high text-xs font-semibold cursor-pointer select-none">
          <input type="checkbox" v-model="snapToGrid" class="rounded accent-primary" />
          <span>{{ t('snapToGrid') }}</span>
        </label>

        <!-- 3-Mode Collision Switcher in Customizing mode -->
        <div v-if="isCustomizing" class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-container-high text-xs font-semibold select-none">
          <span class="text-on-surface-variant text-[11px] font-medium">{{ t('collisionModeTitle') }}:</span>
          <select
            :value="collisionMode"
            @change="e => setCollisionMode((e.target as HTMLSelectElement).value as CollisionMode)"
            class="bg-surface-variant text-on-surface rounded px-2 py-0.5 text-xs font-semibold border border-outline-variant/40 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
          >
            <option value="push">{{ t('collisionModePush') }}</option>
            <option value="block">{{ t('collisionModeBlock') }}</option>
            <option value="off">{{ t('collisionModeOff') }}</option>
          </select>
        </div>

        <!-- Presets Dropdown in Customizing mode -->
        <div v-if="isCustomizing" class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-container-high text-xs font-semibold select-none">
          <span class="text-on-surface-variant text-[11px] font-medium">{{ t('presetsTitle') }}:</span>
          <select
            :value="activePresetId"
            @change="e => {
              const pId = (e.target as HTMLSelectElement).value
              const found = userPresets.find(p => p.id === pId)
              if (found) applyPreset(found)
            }"
            class="bg-surface-variant text-on-surface rounded px-2 py-0.5 text-xs font-semibold border border-outline-variant/40 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
          >
            <option value="custom">{{ t('defaultPresetOption') }}</option>
            <option v-for="p in userPresets" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
          <button @click="handleSavePreset" class="p-1 rounded hover:bg-primary/20 text-primary transition-colors cursor-pointer" :title="t('savePreset')">
            <span class="material-symbols-outlined text-xs block">bookmark_add</span>
          </button>
        </div>

        <!-- Export / Import JSON in Customizing mode -->
        <template v-if="isCustomizing">
          <button
            @click="handleExportJson"
            class="px-2.5 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-container-high text-on-surface hover:bg-surface-bright text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
            :title="t('exportLayout')"
          >
            <span class="material-symbols-outlined text-xs">download</span>
            <span>{{ t('exportLayout') }}</span>
          </button>

          <button
            @click="triggerImportJson"
            class="px-2.5 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-container-high text-on-surface hover:bg-surface-bright text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
            :title="t('importLayout')"
          >
            <span class="material-symbols-outlined text-xs">upload</span>
            <span>{{ t('importLayout') }}</span>
          </button>
          <input ref="fileInputRef" type="file" accept=".json" class="hidden" @change="handleFileImport" />
        </template>

        <!-- Reset Positions Button -->
        <button
          v-if="isCustomizing"
          @click="handleResetLayout"
          class="px-3 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-container-high text-on-surface hover:bg-surface-bright text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
        >
          <span class="material-symbols-outlined text-sm">restart_alt</span>
          <span>{{ t('resetLayout') }}</span>
        </button>

        <!-- Customize Windows Toggle -->
        <button
          @click="isCustomizing = !isCustomizing"
          class="px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          :class="isCustomizing ? 'bg-secondary text-on-secondary hover:opacity-90' : 'bg-surface-container-high border border-outline-variant/60 text-on-surface hover:bg-surface-bright'"
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
        <div class="flex items-center gap-3">
          <span class="text-[11px] font-mono text-on-surface-variant">
            {{ hiddenWidgetIds.size > 0 ? t('hiddenWidgetsCount', { count: hiddenWidgetIds.size }) : '' }}
          </span>
          <button
            @click="isCatalogOpen = true"
            class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-primary/20 text-primary hover:bg-primary/30 transition-colors flex items-center gap-1 cursor-pointer"
          >
            <span class="material-symbols-outlined text-xs">add</span>
            <span>{{ t('addWidget') }}</span>
          </button>
        </div>
      </div>

      <!-- Quick Toggle Visibility for Added Widgets -->
      <div v-if="addedWidgets.length > 0" class="flex flex-wrap gap-2 pt-1">
        <button
          v-for="w in addedWidgets"
          :key="w.id"
          @click="toggleVisibility(w.id)"
          class="px-2.5 py-1 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition-colors cursor-pointer"
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

      <!-- Drag Ghost Frame in Block Mode when Colliding -->
      <div
        v-if="dragGhostRect && isCustomizing && !isMobile"
        class="absolute border-2 border-dashed border-primary/70 bg-primary/10 rounded-xl pointer-events-none z-30 transition-all duration-75"
        :style="{
          left: `${dragGhostRect.x}px`,
          top: `${dragGhostRect.y}px`,
          width: `${dragGhostRect.width}px`,
          height: `${dragGhostRect.height}px`
        }"
      />

      <!-- Red Overlay Area Fill for Blocked Collision Zone(s) -->
      <template v-if="(collisionHighlightRects.length > 0 || collisionHighlightRect) && isCustomizing && !isMobile">
        <div
          v-for="(rect, rIdx) in (collisionHighlightRects.length > 0 ? collisionHighlightRects : [collisionHighlightRect!])"
          :key="rIdx"
          class="absolute border-2 border-error bg-error/35 bg-[repeating-linear-gradient(45deg,rgba(239,68,68,0.25),rgba(239,68,68,0.25)_10px,rgba(220,38,38,0.45)_10px,rgba(220,38,38,0.45)_20px)] rounded-xl pointer-events-none z-40 animate-pulse flex items-center justify-center shadow-lg transition-all duration-75 overflow-hidden"
          :style="{
            left: `${rect.x}px`,
            top: `${rect.y}px`,
            width: `${rect.width}px`,
            height: `${rect.height}px`
          }"
        >
          <div v-if="rect.width >= 50 && rect.height >= 24" class="px-2 py-0.5 rounded bg-error text-on-error font-bold text-[10px] uppercase flex items-center gap-1 shadow-sm shrink-0">
            <span class="material-symbols-outlined text-xs">block</span>
            <span>{{ t('slotOccupied') }}</span>
          </div>
        </div>
      </template>

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
          @remove-widget="removeWidget(w.id)"
          @update-rect="(rect) => updateWidgetRect(w.id, rect, idx)"
          @clear-collision="clearCollisionHighlight"
          @bring-to-front="bringToFront(w.id)"
        />
      </template>

      <!-- Empty State: All widgets removed or hidden -->
      <div
        v-else
        class="flex flex-col items-center justify-center p-8 text-center space-y-4"
        :class="isMobile ? 'py-16' : 'absolute inset-0'"
      >
        <div class="w-16 h-16 rounded-full bg-surface-container-high flex items-center justify-center text-outline">
          <span class="material-symbols-outlined text-4xl">widgets</span>
        </div>
        <div class="space-y-1 max-w-sm">
          <p class="text-sm text-on-surface font-semibold">
            {{ t('allWidgetsHidden') }}
          </p>
        </div>
        <button
          @click="isCatalogOpen = true"
          class="px-4 py-2 rounded-xl bg-primary text-on-primary hover:opacity-90 font-semibold text-xs flex items-center gap-2 shadow-glow transition-opacity cursor-pointer"
        >
          <span class="material-symbols-outlined text-base">add</span>
          <span>{{ t('addWidget') }}</span>
        </button>
      </div>
    </div>

    <!-- Widget Catalog Modal -->
    <div
      v-if="isCatalogOpen"
      class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in"
      @click.self="isCatalogOpen = false"
    >
      <div class="bg-surface-container-high border border-outline-variant/60 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        <!-- Catalog Header -->
        <div class="flex items-center justify-between border-b border-outline-variant/40 pb-4">
          <div>
            <h2 class="font-bold text-lg text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">apps</span>
              <span>{{ t('widgetCatalog') }}</span>
            </h2>
            <p class="text-xs text-on-surface-variant mt-0.5">
              {{ t('widgetCatalogDesc') }}
            </p>
          </div>
          <button
            @click="isCatalogOpen = false"
            class="p-1.5 rounded-lg text-on-surface-variant hover:bg-surface-variant transition-colors cursor-pointer"
          >
            <span class="material-symbols-outlined text-lg block">close</span>
          </button>
        </div>

        <!-- Search Input -->
        <div class="relative">
          <span class="material-symbols-outlined absolute left-3 top-2.5 text-on-surface-variant text-sm pointer-events-none">search</span>
          <input
            v-model="catalogSearchQuery"
            type="text"
            :placeholder="t('searchWidgetCatalog')"
            class="w-full pl-9 pr-4 py-2 rounded-xl bg-surface-container-low border border-outline-variant/60 text-xs text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:border-primary"
          />
        </div>

        <!-- Catalog List -->
        <div class="flex-1 overflow-y-auto space-y-3 pr-1">
          <template v-if="filteredCatalogWidgets.length > 0">
            <div
              v-for="w in filteredCatalogWidgets"
              :key="w.id"
              class="p-4 rounded-xl border border-outline-variant/40 bg-surface-container-low hover:border-primary/50 flex items-center justify-between gap-4 transition-colors"
            >
              <div class="flex items-center gap-3 overflow-hidden">
                <div class="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
                  <span class="material-symbols-outlined text-xl">widgets</span>
                </div>
                <div class="space-y-0.5 overflow-hidden">
                  <div class="flex items-center gap-2">
                    <h3 class="font-bold text-sm text-on-surface truncate">
                      {{ t(w.title || w.id) }}
                    </h3>
                    <span class="px-1.5 py-0.5 rounded bg-primary/10 text-primary font-mono text-[9px] uppercase font-semibold">
                      {{ w.module_id }}
                    </span>
                  </div>
                  <p class="text-xs text-on-surface-variant truncate">
                    {{ t(w.description || 'widgetNoData') }}
                  </p>
                </div>
              </div>

              <!-- Action Button -->
              <button
                v-if="isWidgetActive(w.id)"
                @click="removeWidget(w.id)"
                class="px-3 py-1.5 rounded-lg border border-outline-variant/60 bg-surface-variant text-on-surface-variant text-xs font-semibold flex items-center gap-1 hover:border-error hover:text-error transition-colors flex-shrink-0 cursor-pointer"
              >
                <span class="material-symbols-outlined text-xs">check</span>
                <span>{{ t('alreadyAdded') }}</span>
              </button>
              <button
                v-else
                @click="addWidget(w.id)"
                class="px-3.5 py-1.5 rounded-lg bg-primary text-on-primary hover:opacity-90 text-xs font-semibold flex items-center gap-1 transition-opacity flex-shrink-0 shadow-sm cursor-pointer"
              >
                <span class="material-symbols-outlined text-xs">add</span>
                <span>{{ t('addButton') }}</span>
              </button>
            </div>
          </template>
          <div v-else class="py-8 text-center text-xs text-on-surface-variant">
            {{ t('noWidgets') }}
          </div>
        </div>

        <!-- Catalog Footer -->
        <div class="pt-3 border-t border-outline-variant/40 flex justify-end">
          <button
            @click="isCatalogOpen = false"
            class="px-4 py-1.5 rounded-lg bg-surface-container-highest border border-outline-variant/60 text-on-surface text-xs font-semibold hover:bg-surface-bright transition-colors cursor-pointer"
          >
            {{ t('closeModal') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from '@/core/i18n'
import { loadModuleWidgets, activeWidgets, type ModuleWidget } from '@/modules/widgets'
import WidgetRenderer from '@/components/common/WidgetRenderer.vue'
import { useWidgetLayout, type CollisionMode } from '@/composables/useWidgetLayout'

const { t } = useI18n()
const isCatalogOpen = ref(false)
const catalogSearchQuery = ref('')

const fileInputRef = ref<HTMLInputElement | null>(null)

const {
  activeWidgetIds,
  hiddenWidgetIds,
  isCustomizing,
  snapToGrid,
  collisionMode,
  collisionHighlightRect,
  collisionHighlightRects,
  dragGhostRect,
  clearCollisionHighlight,
  userPresets,
  activePresetId,
  isMobile,
  initLayout,
  isWidgetActive,
  isWidgetHidden,
  toggleVisibility,
  addWidget,
  removeWidget,
  bringToFront,
  getWidgetRect,
  setCollisionMode,
  updateWidgetRect,
  resetLayout,
  saveCurrentAsPreset,
  applyPreset,
  exportLayoutJson,
  importLayoutJson,
} = useWidgetLayout()

function handleSavePreset() {
  const name = typeof window !== 'undefined' ? window.prompt(t('enterPresetName')) : null
  if (name && name.trim()) {
    saveCurrentAsPreset(name.trim())
  }
}

function handleExportJson() {
  const jsonStr = exportLayoutJson()
  const blob = new Blob([jsonStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `nms_dashboard_layout_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function triggerImportJson() {
  fileInputRef.value?.click()
}

function handleFileImport(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (event) => {
    const content = event.target?.result as string
    if (content) {
      const ok = importLayoutJson(content)
      if (!ok) {
        alert(t('layoutImportError'))
      }
    }
  }
  reader.readAsText(file)
  target.value = ''
}

// All added widgets (active on canvas)
const addedWidgets = computed<ModuleWidget[]>(() => {
  return activeWidgets.value.filter((w) => isWidgetActive(w.id))
})

// Filter catalog widgets by search query
const filteredCatalogWidgets = computed<ModuleWidget[]>(() => {
  const query = catalogSearchQuery.value.trim().toLowerCase()
  if (!query) return activeWidgets.value
  return activeWidgets.value.filter((w) => {
    const title = t(w.title || w.id).toLowerCase()
    const desc = t(w.description || '').toLowerCase()
    const mod = (w.module_id || '').toLowerCase()
    return title.includes(query) || desc.includes(query) || mod.includes(query)
  })
})

// Filter widgets: in customization mode show all added (including hidden), in normal mode filter hidden
const displayedWidgets = computed<ModuleWidget[]>(() => {
  if (isCustomizing.value) {
    return addedWidgets.value
  }
  return addedWidgets.value.filter((w) => !isWidgetHidden(w.id))
})

function handleResetLayout() {
  resetLayout(activeWidgets.value)
}

onMounted(async () => {
  const widgets = await loadModuleWidgets()
  initLayout(widgets)
})
</script>



