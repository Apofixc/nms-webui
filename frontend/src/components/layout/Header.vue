<template>
  <header class="h-16 flex-shrink-0 bg-surface-dim/80 backdrop-blur-sm border-b border-outline-variant px-6 flex items-center justify-end text-on-surface z-40">
    <div class="flex items-center gap-6">
      <!-- Search Bar -->
      <div class="relative w-64 hidden lg:block">
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[20px] pointer-events-none">search</span>
        <input
          type="text"
          :placeholder="t('searchPlaceholder')"
          class="w-full bg-surface-container-high border border-outline-variant rounded-lg pl-10 pr-3 py-1.5 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary font-sans transition-colors placeholder:text-outline-variant"
        />
      </div>

      <!-- Actions & User Profile Pill -->
      <div class="flex items-center gap-3">
        <!-- Language Switcher (RU / EN) -->
        <div class="flex items-center bg-surface-container-highest border border-outline-variant/60 rounded-lg p-0.5 font-mono text-[11px] font-bold">
          <button
            @click="setLanguage('ru')"
            class="px-2 py-0.5 rounded transition-colors cursor-pointer"
            :class="lang === 'ru' ? 'bg-primary text-on-primary-container shadow-sm' : 'text-on-surface-variant hover:text-on-surface'"
          >
            RU
          </button>
          <button
            @click="setLanguage('en')"
            class="px-2 py-0.5 rounded transition-colors cursor-pointer"
            :class="lang === 'en' ? 'bg-primary text-on-primary-container shadow-sm' : 'text-on-surface-variant hover:text-on-surface'"
          >
            EN
          </button>
        </div>

        <!-- Notifications Button -->
        <button class="p-2 hover:text-primary transition-colors cursor-pointer rounded-full hover:bg-surface-variant/50 relative text-on-surface-variant flex items-center justify-center">
          <span class="material-symbols-outlined text-[20px]">notifications_active</span>
          <span class="w-2 h-2 rounded-full bg-tertiary absolute top-1.5 right-1.5" />
        </button>

        <!-- User Profile Badge -->
        <router-link to="/settings/profile" class="flex items-center gap-3 pl-3 border-l border-outline-variant hover:opacity-90 transition-opacity">
          <div class="flex flex-col items-end hidden lg:flex">
            <span class="text-xs font-bold text-on-surface leading-none">Admin User</span>
            <span class="text-[10px] text-primary font-mono uppercase tracking-tighter mt-0.5">{{ t('superuser') }}</span>
          </div>
          <div class="w-8 h-8 rounded-full bg-primary/20 border border-primary/50 flex items-center justify-center font-mono font-bold text-xs text-primary shadow-glow flex-shrink-0">
            AD
          </div>
        </router-link>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useI18n } from '@/core/i18n'
const { lang, setLanguage, t } = useI18n()
</script>
