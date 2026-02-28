<template>
  <aside class="w-60 flex-shrink-0 h-full flex flex-col overflow-hidden bg-surface-800/90 border-r border-surface-700">
    <!-- Logo -->
    <div class="h-16 flex-shrink-0 border-b border-surface-700 bg-gradient-to-br from-surface-800 to-surface-850 flex items-center px-5">
      <h1 class="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
        <span class="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center text-accent font-mono text-sm shadow-glow">NMS</span>
        <span>NMS-WebUI</span>
      </h1>
    </div>

    <!-- Navigation Groups -->
    <nav class="p-3 flex-1 min-h-0 overflow-y-auto">
      <!-- Static Main Link -->
      <router-link
        to="/"
        class="flex items-center gap-3 px-3 py-2.5 mb-2 rounded-lg text-white font-medium hover:bg-surface-700 transition-all group"
        active-class="bg-accent/10 !text-accent shadow-glow-sm"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 opacity-70 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
        <span>Дашборд</span>
      </router-link>

      <div v-for="group in sidebarGroups" :key="group.id" class="mb-1">
        <button
          type="button"
          class="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg text-left font-medium text-white bg-surface-750 hover:bg-surface-700 transition-colors"
          @click="toggleGroup(group.id)"
        >
          <span>{{ group.label }}</span>
          <span
            class="text-slate-400 text-sm transition-transform duration-200"
            :class="groupOpen[group.id] && 'rotate-180'"
          >▾</span>
        </button>
        <transition
          enter-active-class="transition ease-out duration-200"
          enter-from-class="opacity-0 -translate-y-1"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition ease-in duration-150"
          leave-from-class="opacity-100 translate-y-0"
          leave-to-class="opacity-0 -translate-y-1"
        >
          <div v-show="groupOpen[group.id]" class="mt-1 ml-2 pl-4 border-l border-surface-700 space-y-0.5">
            <router-link
              v-for="item in group.items"
              :key="item.path"
              :to="item.path"
              class="flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-surface-750 transition-colors block"
              active-class="!text-accent !bg-accent/10"
            >
              <span class="w-1.5 h-1.5 rounded-full bg-current opacity-60" />
              {{ item.label }}
            </router-link>
          </div>
        </transition>
      </div>

      <!-- Empty state -->
      <div v-if="sidebarGroups.length === 0" class="px-3 py-6 text-center">
        <p class="text-sm text-slate-500">Нет загруженных модулей</p>
        <p class="text-xs text-slate-600 mt-1">Добавьте модули в backend/modules/</p>
      </div>
    </nav>

    <!-- Footer nav items -->
    <div class="p-3 flex-shrink-0 border-t border-surface-700">
      <router-link
        v-for="item in footerItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center gap-2 px-3 py-2.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-750 transition-colors"
        active-class="!text-accent !bg-accent/10"
      >
        <svg v-if="item.icon === 'settings'" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 flex-shrink-0 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span>{{ item.label }}</span>
      </router-link>

      <!-- Settings link fallback (when no modules define footer items) -->
      <router-link
        v-if="footerItems.length === 0"
        to="/settings"
        class="flex items-center gap-2 px-3 py-2.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-750 transition-colors"
        active-class="!text-accent !bg-accent/10"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 flex-shrink-0 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span>Настройки</span>
      </router-link>
    </div>

    <!-- Backend status -->
    <div class="p-3 flex-shrink-0 border-t border-surface-700">
      <div v-if="!backendOk" class="text-xs text-danger bg-danger/10 rounded-lg p-2">
        Backend недоступен. Запустите:<br>
        <code class="block mt-1 text-[10px] break-all">uvicorn backend.main:app --port 9000</code>
      </div>
      <div v-else class="text-xs text-success/80">API подключён</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useAppStore } from '@/core/store'
import { storeToRefs } from 'pinia'

const store = useAppStore()
const { sidebarGroups, footerItems, groupOpen, backendOk } = storeToRefs(store)
const { toggleGroup } = store
</script>
