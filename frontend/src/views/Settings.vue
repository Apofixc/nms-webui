<template>
  <div class="min-h-full p-6 flex gap-6 max-w-6xl w-full mx-auto animate-fade-in text-on-surface">
    <!-- Secondary Settings Rail (Left) -->
    <aside class="w-52 shrink-0 hidden md:flex flex-col gap-2 border-r border-outline-variant pr-4">
      <div class="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest mb-2 pl-2 font-bold">Configuration Groups</div>
      <router-link
        to="/settings/modules"
        class="w-full text-left flex items-center gap-3 py-2 px-3 rounded-lg text-on-surface-variant hover:bg-surface-variant/40 hover:text-on-surface text-sm transition-all border border-transparent"
      >
        <span class="material-symbols-outlined text-[20px]">view_module</span>
        <span>Module Management</span>
      </router-link>

      <router-link
        to="/settings"
        class="w-full text-left flex items-center gap-3 py-2 px-3 rounded-lg bg-surface-container-highest border border-outline-variant text-on-surface font-bold text-sm shadow-glow transition-all"
      >
        <span class="material-symbols-outlined text-primary text-[20px]">verified_user</span>
        <span>Access & Identity</span>
      </router-link>
    </aside>

    <!-- Configuration Content Area -->
    <div class="flex-1 flex flex-col gap-6 min-w-0">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="font-bold text-2xl text-on-surface">Access & Identity</h1>
          <p class="text-xs text-on-surface-variant mt-1">Manage global authentication policies and monitor security events.</p>
        </div>
        <div class="flex items-center gap-3">
          <button class="px-4 py-1.5 rounded border border-outline-variant text-on-surface hover:bg-surface-container-high transition-colors text-xs font-semibold">Export Logs</button>
          <button class="bg-primary text-on-primary px-4 py-1.5 rounded text-xs font-semibold transition-colors shadow-glow hover:bg-primary-fixed">Apply Changes</button>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-6">
        <!-- Global Auth Card -->
        <div class="col-span-12 lg:col-span-5 bg-surface-container-low border border-outline-variant p-5 rounded-xl shadow-glow flex flex-col justify-between relative overflow-hidden group">
          <div class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity pointer-events-none">
            <span class="material-symbols-outlined text-6xl text-primary">security</span>
          </div>
          <div>
            <h3 class="font-semibold text-sm text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">verified_user</span>
              <span>Global Authentication</span>
            </h3>
            <p class="text-xs text-on-surface-variant mt-2 leading-relaxed">
              Master switch for the system-wide authorization module. Disabling this defaults all access to local bypass mode.
            </p>
          </div>
          <div class="mt-6 flex items-center justify-between bg-surface-container-highest p-3 rounded-lg border border-outline-variant/30">
            <div class="flex flex-col">
              <span class="font-mono text-[10px] text-primary uppercase tracking-widest">auth_enabled</span>
              <span class="text-xs font-bold text-on-surface mt-0.5">SYSTEM AUTHORIZATION</span>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="authEnabled" class="sr-only peer" />
              <div class="w-11 h-6 bg-surface-variant rounded-full peer-checked:bg-primary/20 peer-checked:after:translate-x-full peer-checked:after:bg-primary transition-all after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-on-surface-variant after:rounded-full after:h-5 after:w-5 after:transition-all" />
            </label>
          </div>
        </div>

        <!-- Security Policies Card -->
        <div class="col-span-12 lg:col-span-7 bg-surface-container-low border border-outline-variant p-5 rounded-xl space-y-4 shadow-glow">
          <h3 class="font-semibold text-sm text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">policy</span>
            <span>Security Policies</span>
          </h3>

          <div class="space-y-3">
            <div class="flex items-start justify-between p-3 bg-surface-container-highest rounded-lg border border-outline-variant/20">
              <div>
                <p class="text-xs font-semibold text-on-surface">Mandatory Password Change</p>
                <p class="text-[11px] text-on-surface-variant mt-0.5">Forces all new users to update credentials upon initial entry.</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="forcePasswordChange" class="sr-only peer" />
                <div class="w-9 h-5 bg-surface-variant rounded-full peer-checked:bg-tertiary/20 peer-checked:after:translate-x-full peer-checked:after:bg-tertiary transition-all after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-on-surface-variant after:rounded-full after:h-4 after:w-4 after:transition-all" />
              </label>
            </div>

            <div class="flex items-start justify-between p-3 bg-surface-container-highest rounded-lg border border-outline-variant/20">
              <div>
                <p class="text-xs font-semibold text-on-surface">Two-Factor Authentication (2FA)</p>
                <p class="text-[11px] text-on-surface-variant mt-0.5">Enforces TOTP hardware token requirement for superusers.</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="twoFactorRequired" class="sr-only peer" />
                <div class="w-9 h-5 bg-surface-variant rounded-full peer-checked:bg-tertiary/20 peer-checked:after:translate-x-full peer-checked:after:bg-tertiary transition-all after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-on-surface-variant after:rounded-full after:h-4 after:w-4 after:transition-all" />
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const authEnabled = ref(true)
const forcePasswordChange = ref(true)
const twoFactorRequired = ref(false)
</script>
