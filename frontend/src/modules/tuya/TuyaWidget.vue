<template>
  <div class="h-full flex flex-col justify-between space-y-2">
    <!-- Header Summary Badge -->
    <div class="flex items-center justify-between p-2 rounded-lg bg-surface-container-high border border-outline-variant/40">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-primary text-sm">nest_ecosystem_network</span>
        <span class="text-xs font-semibold text-on-surface">{{ t('tuyaWidgetTitle') }}</span>
      </div>
      <span class="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-mono text-[10px] font-bold">
        {{ t('tuyaTotalDevices') }}: {{ totalDevices }}
      </span>
    </div>

    <!-- Quick Status Cards -->
    <div class="grid grid-cols-2 gap-2 flex-1">
      <div class="p-2 rounded-lg bg-tertiary/10 border border-tertiary/30 flex flex-col justify-between">
        <div class="flex items-center justify-between text-[10px] text-tertiary font-medium">
          <span>{{ t('tuyaOnline') }}</span>
          <span class="material-symbols-outlined text-xs">check_circle</span>
        </div>
        <div class="font-bold text-lg text-tertiary font-mono">
          {{ onlineDevices }}
        </div>
      </div>

      <div class="p-2 rounded-lg bg-warning/10 border border-warning/30 flex flex-col justify-between">
        <div class="flex items-center justify-between text-[10px] text-warning font-medium">
          <span>{{ t('tuyaOffline') }}</span>
          <span class="material-symbols-outlined text-xs">error</span>
        </div>
        <div class="font-bold text-lg text-warning font-mono">
          {{ offlineDevices }}
        </div>
      </div>
    </div>

    <!-- Extra Custom Action -->
    <div class="pt-1 flex items-center justify-between">
      <span class="text-[10px] text-on-surface-variant italic">{{ t('customModuleUI') }}</span>
      <button
        @click="$emit('refresh')"
        :disabled="loading"
        class="px-2 py-1 rounded text-[10px] font-semibold bg-primary text-on-primary hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-1"
      >
        <span class="material-symbols-outlined text-xs" :class="{ 'animate-spin': loading }">refresh</span>
        <span>{{ t('widgetRefresh') }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/core/i18n'
import type { WidgetData } from '@/modules/widgets'

const props = defineProps<{
  data: WidgetData | null
  loading: boolean
  error?: string | null
}>()

defineEmits<{
  (e: 'refresh'): void
}>()

const { t } = useI18n()

const totalDevices = computed(() => props.data?.extra?.total ?? 0)
const onlineDevices = computed(() => props.data?.extra?.online ?? 0)
const offlineDevices = computed(() => props.data?.extra?.offline ?? 0)
</script>

