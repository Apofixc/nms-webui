<template>
  <div class="p-6 flex-1 max-w-6xl w-full mx-auto animate-fade-in text-on-surface">
    <div class="grid grid-cols-12 gap-6">
      <!-- Left Column: Profile Card & Tokens -->
      <div class="col-span-12 lg:col-span-4 space-y-6">
        <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 shadow-glow text-center space-y-4">
          <div class="w-20 h-20 mx-auto rounded-full bg-primary/20 border-2 border-primary flex items-center justify-center font-mono font-bold text-2xl text-primary shadow-glow">
            AD
          </div>
          <div>
            <h2 class="font-bold text-lg text-on-surface">Admin User</h2>
            <span class="text-[10px] font-mono text-primary uppercase tracking-wider font-bold">SUPERUSER / ROOT</span>
            <p class="text-xs text-on-surface-variant mt-1 font-mono">Operator ID: ops-880219</p>
          </div>

          <div class="pt-4 border-t border-outline-variant/40 flex justify-around text-center text-xs font-mono">
            <div>
              <span class="block text-on-surface-variant">Active Sessions</span>
              <span class="text-on-surface font-bold">2 Live</span>
            </div>
            <div>
              <span class="block text-on-surface-variant">2FA Status</span>
              <span class="text-tertiary font-bold">Enabled</span>
            </div>
          </div>
        </div>

        <!-- API Tokens Card -->
        <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 space-y-4 shadow-glow">
          <h3 class="font-bold text-sm text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">key</span>
            <span>API Tokens</span>
          </h3>
          <p class="text-xs text-on-surface-variant leading-relaxed">System authorization tokens for script and automated deployment calls.</p>

          <div class="bg-surface-container-highest p-3 rounded-lg border border-outline-variant/30 flex items-center justify-between font-mono text-xs text-primary">
            <span class="truncate">nms_live_token_99182a...</span>
            <button class="text-on-surface-variant hover:text-on-surface text-[11px] underline ml-2">Copy</button>
          </div>
        </div>
      </div>

      <!-- Right Column: Account Details Form -->
      <div class="col-span-12 lg:col-span-8 bg-surface-container-low border border-outline-variant rounded-xl p-6 space-y-6 shadow-glow">
        <div class="flex items-center justify-between border-b border-outline-variant pb-3">
          <h3 class="font-bold text-base text-on-surface">Account Credentials</h3>
          <button class="bg-primary text-on-primary px-4 py-1.5 rounded text-xs font-bold shadow-glow hover:bg-primary-fixed transition-colors">
            Save Profile
          </button>
        </div>

        <form @submit.prevent class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block font-mono text-[10px] text-on-surface-variant uppercase tracking-wider mb-1 font-bold">Full Name</label>
              <input
                v-model="name"
                type="text"
                class="w-full bg-surface-container-highest border border-outline-variant rounded px-3 py-2 text-xs font-mono text-on-surface focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label class="block font-mono text-[10px] text-on-surface-variant uppercase tracking-wider mb-1 font-bold">Operator Email</label>
              <input
                v-model="email"
                type="email"
                class="w-full bg-surface-container-highest border border-outline-variant rounded px-3 py-2 text-xs font-mono text-on-surface focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div class="pt-4 border-t border-outline-variant/40">
            <h4 class="font-bold text-xs text-on-surface mb-3 uppercase tracking-wider font-mono">Password Update</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block font-mono text-[10px] text-on-surface-variant uppercase tracking-wider mb-1 font-bold">Current Access Code</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  class="w-full bg-surface-container-highest border border-outline-variant rounded px-3 py-2 text-xs font-mono text-on-surface focus:border-primary"
                />
              </div>
              <div>
                <label class="block font-mono text-[10px] text-on-surface-variant uppercase tracking-wider mb-1 font-bold">New Access Code</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  class="w-full bg-surface-container-highest border border-outline-variant rounded px-3 py-2 text-xs font-mono text-on-surface focus:border-primary"
                />
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const name = ref('Admin User')
const email = ref('admin@nms.net')
</script>
