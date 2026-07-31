<template>
  <aside class="w-56 shrink-0 hidden md:flex flex-col gap-2 border-r border-outline-variant pr-4">
    <div class="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-2 pl-2 font-bold">
      {{ t('configGroups') }}
    </div>

    <!-- Pinned Top Item: Module Management -->
    <router-link
      to="/settings/modules"
      class="w-full text-left flex items-center gap-3 py-2 px-3 rounded-lg text-sm transition-all border font-bold"
      :class="$route.path === '/settings/modules'
        ? 'bg-surface-container-highest border-outline-variant text-on-surface shadow-glow'
        : 'text-on-surface-variant border-transparent hover:bg-surface-variant/40 hover:text-on-surface'"
    >
      <span
        class="material-symbols-outlined text-[20px]"
        :class="$route.path === '/settings/modules' ? 'text-primary' : ''"
      >
        view_module
      </span>
      <span>{{ t('moduleManagement') }}</span>
    </router-link>

    <!-- Sub-list of Modules with Config Schema -->
    <div v-if="configurableModules.length > 0" class="mt-2 ml-3 pl-3 border-l border-outline-variant/50 space-y-1">
      <div class="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider py-1 opacity-70">
        {{ t('moduleSettingsTitle') }}
      </div>
      <router-link
        v-for="mod in configurableModules"
        :key="mod.id"
        :to="`/settings/modules/${mod.id}`"
        class="w-full text-left flex items-center justify-between gap-2 py-1.5 px-2.5 rounded-md text-xs transition-colors border"
        :class="$route.path === `/settings/modules/${mod.id}`
          ? 'bg-primary/10 border-primary/30 text-primary font-bold'
          : 'text-on-surface-variant border-transparent hover:bg-surface-variant/40 hover:text-on-surface'"
      >
        <span class="truncate">{{ t(mod.name || mod.id) }}</span>
        <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :class="mod.enabled ? 'bg-tertiary' : 'bg-outline-variant'"></span>
      </router-link>
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
