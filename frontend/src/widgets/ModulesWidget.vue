<template>
  <div class="h-full flex flex-col justify-start space-y-2 font-sans overflow-hidden">
    <!-- Summary Info Header -->
    <div class="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-surface-container-high/60 border border-outline-variant/30 text-xs flex-shrink-0">
      <span class="text-[11px] font-medium text-on-surface-variant flex items-center gap-1.5">
        <span class="material-symbols-outlined text-sm text-primary">view_module</span>
        <span>{{ t('moduleStatusSummary') || 'Состояние модулей' }}</span>
      </span>
      <span class="px-2 py-0.5 rounded bg-tertiary/15 text-tertiary font-mono text-[10px] font-bold">
        {{ loadedCount }} / {{ totalCount }} {{ t('loaded') || 'загружено' }}
      </span>
    </div>

    <!-- Modules List -->
    <div class="flex-1 overflow-y-auto space-y-1.5 pr-1">
      <div
        v-for="item in items"
        :key="item.id"
        class="p-2.5 rounded-lg bg-surface-container-high border border-outline-variant/30 text-xs transition-colors hover:border-outline-variant/60"
      >
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2 min-w-0">
            <span class="material-symbols-outlined text-sm flex-shrink-0" :class="item.loaded ? 'text-tertiary' : (item.error ? 'text-error' : 'text-on-surface-variant')">
              {{ item.loaded ? 'extension' : (item.error ? 'warning' : 'block') }}
            </span>
            <div class="min-w-0 flex flex-col">
              <span class="font-bold text-on-surface truncate" :title="item.id">
                {{ t(item.name || item.id) }}
              </span>
              <span class="text-[10px] text-on-surface-variant font-mono">id: {{ item.id }} • v{{ item.version || '1.0.0' }}</span>
            </div>
          </div>

          <!-- Status badge -->
          <div class="flex items-center gap-1.5 flex-shrink-0">
            <span
              class="px-2 py-0.5 rounded-full font-mono text-[10px] font-bold flex items-center gap-1"
              :class="getStatusBadgeClass(item)"
            >
              <span
                class="w-1.5 h-1.5 rounded-full"
                :class="item.loaded ? 'bg-tertiary animate-pulse' : (item.error ? 'bg-error' : 'bg-outline')"
              />
              {{ item.value }}
            </span>

            <!-- Error toggle button if error present -->
            <button
              v-if="item.error"
              @click="toggleError(item.id)"
              class="p-1 rounded text-error hover:bg-error/15 transition-colors cursor-pointer"
              :title="t('viewError') || 'Посмотреть ошибку'"
            >
              <span class="material-symbols-outlined text-sm block">
                {{ expandedErrors[item.id] ? 'expand_less' : 'info' }}
              </span>
            </button>
          </div>
        </div>

        <!-- Expanded Error Details Box -->
        <div v-if="item.error && expandedErrors[item.id]" class="mt-2 p-2.5 rounded bg-error/10 border border-error/30 text-error text-[11px] font-mono whitespace-pre-wrap break-all space-y-1">
          <div class="flex items-center gap-1 font-bold">
            <span class="material-symbols-outlined text-xs">error</span>
            <span>{{ t('moduleLoadError') || 'Ошибка загрузки модуля' }}:</span>
          </div>
          <p class="opacity-95 leading-relaxed">{{ item.error }}</p>
        </div>
      </div>

      <div v-if="items.length === 0" class="py-6 text-center text-on-surface-variant text-xs">
        {{ t('noModulesFound') }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from '@/core/i18n'
import type { WidgetProps, WidgetEmits } from '@/modules/widgets'

const props = defineProps<WidgetProps>()
defineEmits<WidgetEmits>()

const { t } = useI18n()

const expandedErrors = ref<Record<string, boolean>>({})

function toggleError(id: string) {
  expandedErrors.value[id] = !expandedErrors.value[id]
}

const items = computed(() => {
  return props.data?.items || []
})

const totalCount = computed(() => items.value.length)
const loadedCount = computed(() => items.value.filter((i: any) => i.loaded).length)

function getStatusBadgeClass(item: any) {
  if (item.loaded) {
    return 'bg-tertiary/15 text-tertiary border border-tertiary/30'
  }
  if (item.error) {
    return 'bg-error/15 text-error border border-error/30'
  }
  return 'bg-surface-variant text-on-surface-variant border border-outline-variant/30'
}
</script>
