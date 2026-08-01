<template>
  <div
    @pointerdown="$emit('bring-to-front')"
    class="bg-surface-container-low border rounded-xl shadow-glow flex flex-col justify-between transition-shadow duration-150 select-none overflow-hidden"
    :class="[
      isCustomizing ? 'border-dashed border-primary/60 bg-surface-container-low/95 shadow-2xl' : 'border-outline-variant/60 shadow-md',
      isHidden ? 'opacity-40' : 'opacity-100',
      isDragging ? 'cursor-grabbing ring-2 ring-primary/80 z-50' : '',
      isResizing ? 'ring-2 ring-secondary/80 z-50' : ''
    ]"
    :style="cardStyle"
  >
    <!-- Header (Drag Area) -->
    <div
      @pointerdown="onMovePointerDown"
      class="flex items-center justify-between border-b border-outline-variant/60 p-3 flex-shrink-0"
      :class="isCustomizing ? 'cursor-grab active:cursor-grabbing bg-primary/5 hover:bg-primary/10' : ''"
    >
      <div class="flex items-center gap-2 overflow-hidden">
        <span v-if="isCustomizing" class="material-symbols-outlined text-primary text-base flex-shrink-0" :title="t('dragToReorder')">
          open_with
        </span>
        <span class="material-symbols-outlined text-primary text-base flex-shrink-0">widgets</span>
        <h3 class="font-bold text-xs text-on-surface truncate">
          {{ translatedTitle }}
        </h3>
      </div>

      <div class="flex items-center gap-1.5 flex-shrink-0">
        <span class="px-1.5 py-0.5 rounded bg-primary/10 text-primary font-mono text-[9px] uppercase font-semibold">
          {{ widget.module_id }}
        </span>

        <!-- Hide / Show Toggle in Customization mode -->
        <button
          v-if="isCustomizing"
          @click.stop="$emit('toggle-visibility')"
          class="p-1 rounded-lg hover:bg-surface-variant transition-colors"
          :class="isHidden ? 'text-outline hover:text-primary' : 'text-primary hover:text-error'"
          :title="isHidden ? t('showWidget') : t('hideWidget')"
        >
          <span class="material-symbols-outlined text-sm block">
            {{ isHidden ? 'visibility_off' : 'visibility' }}
          </span>
        </button>

        <!-- Refresh Button in Normal Mode -->
        <button
          v-else-if="widget.endpoint"
          @click="loadData"
          :disabled="loading"
          class="p-1 rounded-lg hover:bg-surface-variant text-on-surface-variant hover:text-primary transition-colors disabled:opacity-50"
          :title="t('widgetRefresh')"
        >
          <span
            class="material-symbols-outlined text-xs block"
            :class="{ 'animate-spin': loading }"
          >
            refresh
          </span>
        </button>
      </div>
    </div>

    <!-- Content Area -->
    <div class="flex-1 p-3 overflow-y-auto space-y-2">
      <!-- Loading state (first load) -->
      <div v-if="loading && !data" class="flex items-center justify-center py-6 text-on-surface-variant gap-2 text-xs">
        <span class="material-symbols-outlined animate-spin text-primary">progress_activity</span>
        <span>{{ t('widgetLoading') }}</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error && !data" class="p-2.5 rounded-lg bg-error/10 border border-error/30 text-error text-xs space-y-2">
        <div class="flex items-center gap-1.5 font-semibold">
          <span class="material-symbols-outlined text-sm">warning</span>
          <span>{{ t('widgetError') }}</span>
        </div>
        <p class="text-[11px] opacity-90 truncate">{{ error }}</p>
        <button @click="loadData" class="px-2 py-0.5 rounded bg-error text-on-error font-semibold text-[10px] hover:opacity-90 transition-opacity">
          {{ t('widgetRefresh') }}
        </button>
      </div>

      <!-- Custom Module Vue Component if registered -->
      <component
        v-if="customComponent"
        :is="customComponent"
        :data="data"
        :loading="loading"
        :error="error"
        @refresh="loadData"
      />

      <!-- Custom Slot if provided -->
      <slot v-else-if="$slots.default" :data="data" :loading="loading" :error="error" />

      <!-- Unified Metrics View (summary / stat) -->
      <div v-else-if="data && data.metrics && data.metrics.length > 0" class="space-y-2">
        <div class="grid grid-cols-2 gap-2">
          <div
            v-for="m in data.metrics"
            :key="m.id"
            class="p-2 rounded-lg bg-surface-container-high border border-outline-variant/40 flex flex-col justify-between"
          >
            <div class="flex items-center justify-between text-[10px] text-on-surface-variant font-medium mb-0.5">
              <span class="truncate">{{ t(m.label || m.id) }}</span>
              <span v-if="m.icon" class="material-symbols-outlined text-xs" :class="getMetricStatusColor(m.status)">
                {{ m.icon }}
              </span>
            </div>
            <div class="flex items-baseline gap-1">
              <span class="font-bold text-base text-on-surface font-mono" :class="getMetricStatusColor(m.status)">
                {{ m.value }}
              </span>
              <span v-if="m.unit" class="text-[9px] text-on-surface-variant font-mono">{{ m.unit }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Items List View -->
      <div v-else-if="data && data.items && data.items.length > 0" class="space-y-1 overflow-y-auto max-h-full pr-1">
        <div
          v-for="(item, idx) in data.items"
          :key="item.id || idx"
          class="p-1.5 rounded bg-surface-container-high border border-outline-variant/30 text-[11px] flex items-center justify-between"
        >
          <span class="font-medium text-on-surface truncate">{{ item.label || item.name || item.id }}</span>
          <span v-if="item.value" class="font-mono text-on-surface-variant font-semibold ml-2 flex-shrink-0">{{ item.value }}</span>
        </div>
      </div>

      <!-- Fallback Description -->
      <div v-else class="text-xs text-on-surface-variant space-y-1">
        <p>{{ t(widget.description || 'widgetNoData') }}</p>
      </div>
    </div>

    <!-- Footer: Actions & Timestamp -->
    <div class="px-3 py-1.5 border-t border-outline-variant/40 flex justify-between items-center text-xs font-mono text-on-surface-variant flex-shrink-0">
      <span class="text-[9px] opacity-75 truncate">
        {{ lastUpdatedText }}
      </span>

      <!-- Custom Actions or Default Link -->
      <div class="flex items-center gap-1.5 flex-shrink-0">
        <template v-if="data && data.actions && data.actions.length > 0">
          <router-link
            v-for="act in data.actions"
            :key="act.path"
            :to="act.path"
            class="hover:underline text-primary flex items-center gap-0.5 font-sans font-bold text-[11px]"
          >
            <span>{{ t(act.label) }}</span>
            <span class="material-symbols-outlined text-xs">{{ act.icon || 'arrow_forward' }}</span>
          </router-link>
        </template>
        <template v-else>
          <router-link
            :to="`/${widget.module_id}`"
            class="hover:underline text-primary flex items-center gap-0.5 font-sans font-bold text-[11px]"
          >
            <span>{{ t('navigate') }}</span>
            <span class="material-symbols-outlined text-xs">arrow_forward</span>
          </router-link>
        </template>
      </div>
    </div>

    <!-- Bottom-Right Resize Handle in Customization Mode -->
    <div
      v-if="isCustomizing"
      @pointerdown.stop.prevent="onResizePointerDown"
      class="absolute bottom-0 right-0 w-5 h-5 cursor-nwse-resize flex items-center justify-center text-primary hover:text-primary-bright active:scale-125 transition-transform z-20"
      title="Изменить размер"
    >
      <span class="material-symbols-outlined text-xs block pointer-events-none">
        south_east
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { useI18n } from '@/core/i18n'
import { type ModuleWidget, type WidgetData, type WidgetStatus, fetchWidgetData } from '@/modules/widgets'
import type { WidgetRect } from '@/composables/useWidgetLayout'
import { getWidgetComponentLoader } from '@/modules/registry'

const props = withDefaults(
  defineProps<{
    widget: ModuleWidget
    rect?: WidgetRect
    isCustomizing?: boolean
    isHidden?: boolean
    isMobile?: boolean
  }>(),
  {
    rect: () => ({ x: 10, y: 10, width: 360, height: 240, zIndex: 1 }),
    isCustomizing: false,
    isHidden: false,
    isMobile: false,
  }
)

const customComponent = computed(() => {
  const loader = getWidgetComponentLoader(props.widget.component)
  return loader ? defineAsyncComponent(loader) : null
})


const emit = defineEmits<{
  (e: 'toggle-visibility'): void
  (e: 'update-rect', rectDelta: Partial<WidgetRect>): void
  (e: 'bring-to-front'): void
}>()

const { t } = useI18n()

const data = ref<WidgetData | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const lastUpdatedTime = ref<string>('')
let timer: ReturnType<typeof setInterval> | null = null

const isDragging = ref(false)
const isResizing = ref(false)

const cardStyle = computed(() => {
  if (props.isMobile) {
    return {
      position: 'relative' as const,
      width: '100%',
      minHeight: '180px',
    }
  }
  return {
    position: 'absolute' as const,
    left: `${props.rect.x}px`,
    top: `${props.rect.y}px`,
    width: `${props.rect.width}px`,
    height: `${props.rect.height}px`,
    zIndex: props.rect.zIndex || 1,
  }
})

const translatedTitle = computed(() => {
  if (data.value?.title) {
    return t(data.value.title)
  }
  return t(props.widget.title || props.widget.id)
})

const lastUpdatedText = computed(() => {
  if (!lastUpdatedTime.value) {
    return props.widget.endpoint ? '' : 'Internal'
  }
  return `${t('widgetLastUpdated')}: ${lastUpdatedTime.value}`
})

function getMetricStatusColor(status?: WidgetStatus): string {
  switch (status) {
    case 'ok':
      return 'text-tertiary font-semibold'
    case 'warning':
      return 'text-amber-500 font-semibold'
    case 'error':
      return 'text-error font-semibold'
    case 'info':
    default:
      return 'text-primary font-semibold'
  }
}

// ── Mouse Drag & Move Mechanics ────────────────────────────────────────────────
function onMovePointerDown(e: PointerEvent) {
  if (!props.isCustomizing) return
  emit('bring-to-front')
  isDragging.value = true

  const startX = e.clientX
  const startY = e.clientY
  const initialX = props.rect.x
  const initialY = props.rect.y

  function onPointerMove(moveEv: PointerEvent) {
    const dx = moveEv.clientX - startX
    const dy = moveEv.clientY - startY
    emit('update-rect', {
      x: Math.max(0, initialX + dx),
      y: Math.max(0, initialY + dy),
    })
  }

  function onPointerUp() {
    isDragging.value = false
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
  }

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}

// ── Mouse Resize Mechanics ─────────────────────────────────────────────────────
function onResizePointerDown(e: PointerEvent) {
  emit('bring-to-front')
  isResizing.value = true

  const startX = e.clientX
  const startY = e.clientY
  const initialW = props.rect.width
  const initialH = props.rect.height

  function onPointerMove(moveEv: PointerEvent) {
    const dw = moveEv.clientX - startX
    const dh = moveEv.clientY - startY
    emit('update-rect', {
      width: Math.max(260, initialW + dw),
      height: Math.max(160, initialH + dh),
    })
  }

  function onPointerUp() {
    isResizing.value = false
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
  }

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}

async function loadData() {
  if (!props.widget.endpoint || document.hidden) return
  loading.value = true
  error.value = null
  try {
    const res = await fetchWidgetData(props.widget.endpoint)
    data.value = res
    lastUpdatedTime.value = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch (err: any) {
    console.error(`Error loading widget ${props.widget.id}:`, err)
    error.value = err?.response?.data?.detail || err?.message || 'Failed to fetch widget'
  } finally {
    loading.value = false
  }
}

function handleVisibilityChange() {
  if (!document.hidden && props.widget.endpoint) {
    loadData()
  }
}

onMounted(() => {
  if (props.widget.endpoint) {
    loadData()
    if (props.widget.refresh_interval && props.widget.refresh_interval > 0) {
      timer = setInterval(loadData, props.widget.refresh_interval * 1000)
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
  }
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>
