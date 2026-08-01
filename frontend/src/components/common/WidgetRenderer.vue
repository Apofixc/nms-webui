<template>
  <div
    class="bg-surface-container-low border rounded-xl p-5 shadow-glow space-y-4 flex flex-col justify-between transition-all duration-200"
    :class="[
      cardSizeClass,
      isCustomizing ? 'border-dashed border-primary/60 bg-surface-container-low/80 cursor-grab active:cursor-grabbing hover:border-primary' : 'border-outline-variant/60',
      isHidden ? 'opacity-50' : 'opacity-100'
    ]"
    :draggable="isCustomizing"
    @dragstart="$emit('drag-start', $event)"
    @dragover.prevent="$emit('drag-over', $event)"
    @drop.prevent="$emit('drop', $event)"
  >
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-outline-variant/60 pb-2.5">
      <div class="flex items-center gap-2">
        <span v-if="isCustomizing" class="material-symbols-outlined text-outline text-lg cursor-grab active:cursor-grabbing" :title="t('dragToReorder')">
          drag_indicator
        </span>
        <span class="material-symbols-outlined text-primary text-lg">widgets</span>
        <h3 class="font-bold text-sm text-on-surface">
          {{ translatedTitle }}
        </h3>
      </div>

      <div class="flex items-center gap-2">
        <span class="px-2 py-0.5 rounded bg-primary/10 text-primary font-mono text-[10px] uppercase font-semibold">
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
          <span class="material-symbols-outlined text-base">
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
            class="material-symbols-outlined text-sm block"
            :class="{ 'animate-spin': loading }"
          >
            refresh
          </span>
        </button>
      </div>
    </div>

    <!-- Content Area -->
    <div class="flex-1 space-y-3">
      <!-- Loading state (first load) -->
      <div v-if="loading && !data" class="flex items-center justify-center py-6 text-on-surface-variant gap-2 text-xs">
        <span class="material-symbols-outlined animate-spin text-primary">progress_activity</span>
        <span>{{ t('widgetLoading') }}</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error && !data" class="p-3 rounded-lg bg-error/10 border border-error/30 text-error text-xs space-y-2">
        <div class="flex items-center gap-1.5 font-semibold">
          <span class="material-symbols-outlined text-sm">warning</span>
          <span>{{ t('widgetError') }}</span>
        </div>
        <p class="text-[11px] opacity-90">{{ error }}</p>
        <button @click="loadData" class="px-2.5 py-1 rounded bg-error text-on-error font-semibold text-[11px] hover:opacity-90 transition-opacity">
          {{ t('widgetRefresh') }}
        </button>
      </div>

      <!-- Unified Metrics View (summary / stat) -->
      <div v-else-if="data && data.metrics && data.metrics.length > 0" class="space-y-3">
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          <div
            v-for="m in data.metrics"
            :key="m.id"
            class="p-2.5 rounded-lg bg-surface-container-high border border-outline-variant/40 flex flex-col justify-between"
          >
            <div class="flex items-center justify-between text-[11px] text-on-surface-variant font-medium mb-1">
              <span>{{ t(m.label || m.id) }}</span>
              <span v-if="m.icon" class="material-symbols-outlined text-xs" :class="getMetricStatusColor(m.status)">
                {{ m.icon }}
              </span>
            </div>
            <div class="flex items-baseline gap-1">
              <span class="font-bold text-lg text-on-surface font-mono" :class="getMetricStatusColor(m.status)">
                {{ m.value }}
              </span>
              <span v-if="m.unit" class="text-[10px] text-on-surface-variant font-mono">{{ m.unit }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Items List View -->
      <div v-else-if="data && data.items && data.items.length > 0" class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
        <div
          v-for="(item, idx) in data.items"
          :key="item.id || idx"
          class="p-2 rounded-lg bg-surface-container-high border border-outline-variant/30 text-xs flex items-center justify-between"
        >
          <span class="font-medium text-on-surface">{{ item.label || item.name || item.id }}</span>
          <span v-if="item.value" class="font-mono text-on-surface-variant font-semibold">{{ item.value }}</span>
        </div>
      </div>

      <!-- Fallback Description (when no endpoint or static widget) -->
      <div v-else class="text-xs text-on-surface-variant space-y-2">
        <p>{{ t(widget.description || 'widgetNoData') }}</p>
      </div>
    </div>

    <!-- Footer: Actions & Timestamp -->
    <div class="pt-2 border-t border-outline-variant/40 flex justify-between items-center text-xs font-mono text-on-surface-variant">
      <span class="text-[10px] opacity-75">
        {{ lastUpdatedText }}
      </span>

      <!-- Custom Actions or Default Link -->
      <div class="flex items-center gap-2">
        <template v-if="data && data.actions && data.actions.length > 0">
          <router-link
            v-for="act in data.actions"
            :key="act.path"
            :to="act.path"
            class="hover:underline text-primary flex items-center gap-1 font-sans font-bold text-xs"
          >
            <span>{{ t(act.label) }}</span>
            <span class="material-symbols-outlined text-xs">{{ act.icon || 'arrow_forward' }}</span>
          </router-link>
        </template>
        <template v-else>
          <router-link
            :to="`/${widget.module_id}`"
            class="hover:underline text-primary flex items-center gap-1 font-sans font-bold text-xs"
          >
            <span>{{ t('navigate') }}</span>
            <span class="material-symbols-outlined text-xs">arrow_forward</span>
          </router-link>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from '@/core/i18n'
import { type ModuleWidget, type WidgetData, type WidgetStatus, fetchWidgetData } from '@/modules/widgets'

const props = withDefaults(
  defineProps<{
    widget: ModuleWidget
    isCustomizing?: boolean
    isHidden?: boolean
  }>(),
  {
    isCustomizing: false,
    isHidden: false,
  }
)

defineEmits<{
  (e: 'toggle-visibility'): void
  (e: 'drag-start', event: DragEvent): void
  (e: 'drag-over', event: DragEvent): void
  (e: 'drop', event: DragEvent): void
}>()

const { t } = useI18n()

const data = ref<WidgetData | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const lastUpdatedTime = ref<string>('')
let timer: ReturnType<typeof setInterval> | null = null

const translatedTitle = computed(() => {
  if (data.value?.title) {
    return t(data.value.title)
  }
  return t(props.widget.title || props.widget.id)
})

const cardSizeClass = computed(() => {
  switch (props.widget.size) {
    case 'large':
      return 'col-span-1 md:col-span-2 lg:col-span-3'
    case 'medium':
      return 'col-span-1 md:col-span-2 lg:col-span-1'
    case 'small':
    default:
      return 'col-span-1'
  }
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

async function loadData() {
  if (!props.widget.endpoint) return
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

onMounted(() => {
  if (props.widget.endpoint) {
    loadData()
    if (props.widget.refresh_interval && props.widget.refresh_interval > 0) {
      timer = setInterval(loadData, props.widget.refresh_interval * 1000)
    }
  }
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>
