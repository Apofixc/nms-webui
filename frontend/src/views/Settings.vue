<template>
  <div class="min-h-full p-6 flex gap-6 w-full animate-fade-in text-on-surface">
    <!-- Reusable Secondary Settings Rail -->
    <SettingsRail />

    <!-- Configuration Content Area (Full Width) -->
    <div class="flex-1 flex flex-col gap-6 w-full pb-12 min-w-0">
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
        <div class="col-span-12 lg:col-span-4 bg-surface-container-low border border-outline-variant p-6 rounded-xl shadow-glow flex flex-col justify-between relative overflow-hidden group">
          <div class="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity pointer-events-none">
            <span class="material-symbols-outlined text-6xl text-primary">security</span>
          </div>
          <div class="relative z-10">
            <h3 class="font-semibold text-sm text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">verified_user</span>
              <span>Global Authentication</span>
            </h3>
            <p class="text-xs text-on-surface-variant mt-2 leading-relaxed">
              Master switch for the system-wide authorization module. Disabling this defaults all access to local bypass mode.
            </p>
          </div>
          <div class="mt-8 flex items-center justify-between bg-surface-container-highest p-4 rounded-lg border border-outline-variant/30">
            <div class="flex flex-col">
              <span class="font-mono text-[10px] text-primary uppercase tracking-widest">auth_enabled</span>
              <span class="text-xs font-bold text-on-surface mt-1">SYSTEM AUTHORIZATION</span>
            </div>
            <label class="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" v-model="authEnabled" class="sr-only peer" />
              <div class="w-14 h-7 bg-surface-variant rounded-full peer-checked:bg-primary/20 peer-checked:after:translate-x-full peer-checked:after:bg-primary transition-all after:content-[''] after:absolute after:top-1 after:left-1 after:bg-on-surface-variant after:rounded-full after:h-5 after:w-5 after:transition-all" />
            </label>
          </div>
        </div>

        <!-- Security Policies Card -->
        <div class="col-span-12 lg:col-span-8 bg-surface-container-low border border-outline-variant p-6 rounded-xl space-y-6 shadow-glow">
          <h3 class="font-semibold text-sm text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">policy</span>
            <span>Security Policies</span>
          </h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="flex items-start justify-between p-4 bg-surface-container-highest rounded-lg border border-outline-variant/20 hover:border-outline-variant transition-colors group">
              <div class="max-w-[80%]">
                <p class="text-xs font-semibold text-on-surface">Mandatory Password Change</p>
                <p class="text-[11px] text-on-surface-variant mt-1 leading-tight">Forces all new users to update credentials upon initial entry.</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer mt-1">
                <input type="checkbox" v-model="mandatoryPasswordChange" class="sr-only peer" />
                <div class="w-10 h-5 bg-surface-variant rounded-full peer-checked:bg-tertiary/20 peer-checked:after:translate-x-full peer-checked:after:bg-tertiary transition-all after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-on-surface-variant after:rounded-full after:h-4 after:w-4 after:transition-all" />
              </label>
            </div>

            <div class="bg-surface-container-highest p-4 rounded-lg border border-outline-variant/20 space-y-4">
              <h4 class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest">Rate Limiting & Lockout</h4>
              <div class="space-y-3">
                <div class="flex items-center justify-between gap-4">
                  <label class="text-xs text-on-surface">Max Login Attempts</label>
                  <input v-model="maxLoginAttempts" type="number" class="w-20 bg-surface-container-lowest text-on-surface font-mono text-xs font-bold py-1 px-2 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none" />
                </div>
                <div class="flex items-center justify-between gap-4">
                  <label class="text-xs text-on-surface">Lockout Duration (min)</label>
                  <input v-model="lockoutDuration" type="number" class="w-20 bg-surface-container-lowest text-on-surface font-mono text-xs font-bold py-1 px-2 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Audit Log Card -->
        <div class="col-span-12 bg-surface-container-low border border-outline-variant rounded-xl overflow-hidden flex flex-col shadow-glow">
          <div class="p-4 border-b border-outline-variant flex items-center justify-between">
            <div class="flex items-center gap-3">
              <h3 class="font-bold text-sm text-on-surface">Security Audit Log</h3>
              <span class="bg-error-container/20 text-error text-[10px] px-2 py-0.5 rounded border border-error/20 font-bold uppercase tracking-tighter flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-error pulse-dot" /> Live Monitor
              </span>
            </div>
            <div class="flex items-center gap-2">
              <button class="p-1.5 hover:bg-surface-variant rounded text-on-surface-variant transition-colors">
                <span class="material-symbols-outlined text-sm">filter_list</span>
              </button>
              <button class="p-1.5 hover:bg-surface-variant rounded text-on-surface-variant transition-colors">
                <span class="material-symbols-outlined text-sm">refresh</span>
              </button>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead class="bg-surface-container-highest border-b border-outline-variant/30">
                <tr class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest font-mono">
                  <th class="px-6 py-3">Timestamp</th>
                  <th class="px-6 py-3">Event Type</th>
                  <th class="px-6 py-3">User</th>
                  <th class="px-6 py-3">IP Address</th>
                  <th class="px-6 py-3">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/10 font-mono text-xs">
                <tr class="hover:bg-surface-variant/20 transition-colors">
                  <td class="px-6 py-4 text-on-surface-variant">2024-05-24 14:02:11</td>
                  <td class="px-6 py-4 font-bold text-on-surface">Login Attempt</td>
                  <td class="px-6 py-4 text-primary">eng_marcus_v</td>
                  <td class="px-6 py-4 text-on-surface-variant">192.168.1.114</td>
                  <td class="px-6 py-4">
                    <span class="flex items-center gap-2 text-tertiary font-bold">
                      <span class="w-1.5 h-1.5 rounded-full bg-tertiary" /> Success
                    </span>
                  </td>
                </tr>

                <tr class="hover:bg-surface-variant/20 transition-colors bg-error-container/5">
                  <td class="px-6 py-4 text-on-surface-variant">2024-05-24 13:58:45</td>
                  <td class="px-6 py-4 font-bold text-on-surface">Login Attempt</td>
                  <td class="px-6 py-4 text-primary">unknown_usr</td>
                  <td class="px-6 py-4 text-on-surface-variant">10.0.4.55</td>
                  <td class="px-6 py-4">
                    <span class="flex items-center gap-2 text-error font-bold">
                      <span class="w-1.5 h-1.5 rounded-full bg-error pulse-dot" /> Failure
                    </span>
                  </td>
                </tr>

                <tr class="hover:bg-surface-variant/20 transition-colors">
                  <td class="px-6 py-4 text-on-surface-variant">2024-05-24 13:40:02</td>
                  <td class="px-6 py-4 font-bold text-on-surface">User Created</td>
                  <td class="px-6 py-4 text-primary">sys_admin_prime</td>
                  <td class="px-6 py-4 text-on-surface-variant">127.0.0.1</td>
                  <td class="px-6 py-4">
                    <span class="flex items-center gap-2 text-tertiary font-bold">
                      <span class="w-1.5 h-1.5 rounded-full bg-tertiary" /> Success
                    </span>
                  </td>
                </tr>

                <tr class="hover:bg-surface-variant/20 transition-colors">
                  <td class="px-6 py-4 text-on-surface-variant">2024-05-24 13:15:22</td>
                  <td class="px-6 py-4 font-bold text-on-surface">Role Modified</td>
                  <td class="px-6 py-4 text-primary">security_lead</td>
                  <td class="px-6 py-4 text-on-surface-variant">192.168.1.10</td>
                  <td class="px-6 py-4">
                    <span class="flex items-center gap-2 text-tertiary font-bold">
                      <span class="w-1.5 h-1.5 rounded-full bg-tertiary" /> Success
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SettingsRail from '@/components/layout/SettingsRail.vue'

const authEnabled = ref(true)
const mandatoryPasswordChange = ref(true)
const maxLoginAttempts = ref(5)
const lockoutDuration = ref(30)
</script>
