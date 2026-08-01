<template>
  <aside class="w-64 shrink-0 hidden md:flex flex-col gap-4 border-r border-outline-variant/40 pr-4">
    <!-- Section 1: Top-level Management -->
    <div class="space-y-1">
      <router-link
        to="/settings/modules"
        class="w-full flex items-center justify-between gap-2.5 py-2.5 px-3 rounded-xl text-xs font-semibold transition-all border whitespace-nowrap"
        :class="$route.path === '/settings/modules'
          ? 'bg-primary/10 border-primary/40 text-primary font-bold shadow-glow'
          : 'text-on-surface-variant border-transparent hover:bg-surface-variant/40 hover:text-on-surface'"
      >
        <div class="flex items-center gap-2.5 min-w-0">
          <span
            class="material-symbols-outlined text-lg flex-shrink-0"
            :class="$route.path === '/settings/modules' ? 'text-primary' : 'text-on-surface-variant/80'"
          >
            widgets
          </span>
          <span class="truncate">{{ t('moduleManagement') }}</span>
        </div>
      </router-link>
    </div>

    <!-- Section 2: Module Configurations -->
    <div v-if="configurableModules.length > 0" class="space-y-2">
      <div class="flex items-center gap-1.5 px-2 font-mono text-[10px] text-on-surface-variant uppercase tracking-widest font-bold opacity-80">
        <span class="material-symbols-outlined text-xs text-secondary">tune</span>
        <span>{{ t('moduleSettingsTitle') }}</span>
      </div>

      <div class="space-y-1 pl-1">
        <router-link
          v-for="mod in configurableModules"
          :key="mod.id"
          :to="`/settings/modules/${mod.id}`"
          class="w-full flex items-center justify-between gap-2 py-2 px-3 rounded-lg text-xs transition-all border"
          :class="$route.path === `/settings/modules/${mod.id}`
            ? 'bg-surface-container-high border-outline-variant text-on-surface font-bold shadow-glow border-l-2 !border-l-primary'
            : 'text-on-surface-variant border-transparent hover:bg-surface-variant/40 hover:text-on-surface'"
        >
          <div class="flex items-center gap-2 min-w-0">
            <span
              class="material-symbols-outlined text-base flex-shrink-0"
              :class="$route.path === `/settings/modules/${mod.id}` ? 'text-primary' : 'text-on-surface-variant/60'"
            >
              settings
            </span>
            <span class="truncate">{{ t(mod.name || mod.id) }}</span>
          </div>

          <span
            class="w-2 h-2 rounded-full flex-shrink-0"
            :class="mod.enabled ? 'bg-tertiary shadow-[0_0_6px_rgba(74,222,128,0.5)]' : 'bg-outline-variant'"
          ></span>
        </router-link>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '@/core/i18n'
import { fetchModules } from '@/core/api'

const $route = useRoute()
const { t } = useI18n()
const configurableModules = ref<any[]>([])

onMounted(async () => {
  try {
    const res = await fetchModules(true, false)
    const items = res.items || []
    configurableModules.value = items.filter((m: any) => m.config_schema && Object.keys(m.config_schema.properties || {}).length > 0)
  } catch (e) {
    console.error('Failed to load configurable modules for rail:', e)
  }
})
</script>
