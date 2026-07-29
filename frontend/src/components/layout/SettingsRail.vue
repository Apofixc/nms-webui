<template>
  <aside class="w-52 shrink-0 hidden md:flex flex-col gap-2 border-r border-outline-variant pr-4">
    <div class="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-2 pl-2 font-bold">
      {{ t('configGroups') }}
    </div>

    <!-- Module Management -->
    <router-link
      to="/settings/modules"
      class="w-full text-left flex items-center gap-3 py-2 px-3 rounded-lg text-sm transition-all border"
      :class="$route.path === '/settings/modules'
        ? 'bg-surface-container-highest border-outline-variant text-on-surface font-bold shadow-glow'
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
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useI18n } from '@/core/i18n'

const $route = useRoute()
const { t } = useI18n()
</script>
