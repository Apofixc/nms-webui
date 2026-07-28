<template>
  <div class="p-6 w-full space-y-6 pb-20 text-on-surface animate-fade-in">
    <!-- Roles Management -->
    <section class="bg-surface-container-low border border-outline-variant rounded-lg p-6 flex flex-col gap-6 shadow-glow">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="font-bold text-base text-on-surface">Roles Management</h2>
          <p class="text-xs text-on-surface-variant mt-1">Define and manage custom access roles.</p>
        </div>
        <button class="bg-primary-container hover:bg-primary-fixed text-on-primary-container px-4 py-1.5 rounded text-sm font-semibold transition-colors flex items-center gap-2 shadow-[0_0_10px_rgba(34,211,238,0.2)] hover:shadow-[0_0_15px_rgba(34,211,238,0.4)]">
          <span class="material-symbols-outlined text-[18px]">add</span> Add New Role
        </button>
      </div>

      <div class="border border-outline-variant rounded overflow-hidden bg-surface overflow-x-auto">
        <table class="w-full text-left text-sm whitespace-nowrap">
          <thead class="text-xs text-on-surface-variant bg-surface-container-lowest border-b border-outline-variant font-mono uppercase">
            <tr>
              <th class="px-4 py-3 font-medium">Role Name</th>
              <th class="px-4 py-3 font-medium">Description</th>
              <th class="px-4 py-3 font-medium">Users</th>
              <th class="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/50">
            <tr class="hover:bg-surface-container-lowest transition-colors group">
              <td class="px-4 py-3 font-medium text-on-surface">Superuser</td>
              <td class="px-4 py-3 text-on-surface-variant text-xs">Full system access</td>
              <td class="px-4 py-3 font-mono text-on-surface text-xs">3</td>
              <td class="px-4 py-3 text-right">
                <button class="text-on-surface-variant hover:text-primary transition-colors p-1">
                  <span class="material-symbols-outlined text-[16px]">edit</span>
                </button>
              </td>
            </tr>
            <tr class="hover:bg-surface-container-lowest transition-colors group">
              <td class="px-4 py-3 font-medium text-on-surface">Admin</td>
              <td class="px-4 py-3 text-on-surface-variant text-xs">Administrative control, limited destructive actions</td>
              <td class="px-4 py-3 font-mono text-on-surface text-xs">12</td>
              <td class="px-4 py-3 text-right">
                <button class="text-on-surface-variant hover:text-primary transition-colors p-1">
                  <span class="material-symbols-outlined text-[16px]">edit</span>
                </button>
              </td>
            </tr>
            <tr class="hover:bg-surface-container-lowest transition-colors group">
              <td class="px-4 py-3 font-medium text-on-surface">Operator</td>
              <td class="px-4 py-3 text-on-surface-variant text-xs">Manage network state and configurations</td>
              <td class="px-4 py-3 font-mono text-on-surface text-xs">45</td>
              <td class="px-4 py-3 text-right">
                <button class="text-on-surface-variant hover:text-primary transition-colors p-1">
                  <span class="material-symbols-outlined text-[16px]">edit</span>
                </button>
              </td>
            </tr>
            <tr class="hover:bg-surface-container-lowest transition-colors group">
              <td class="px-4 py-3 font-medium text-on-surface">Viewer</td>
              <td class="px-4 py-3 text-on-surface-variant text-xs">Read-only access to dashboards and logs</td>
              <td class="px-4 py-3 font-mono text-on-surface text-xs">120</td>
              <td class="px-4 py-3 text-right">
                <button class="text-on-surface-variant hover:text-primary transition-colors p-1">
                  <span class="material-symbols-outlined text-[16px]">edit</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Permissions Matrix -->
    <section class="bg-surface-container-low border border-outline-variant rounded-lg p-6 flex flex-col gap-6 shadow-glow">
      <div>
        <h2 class="font-bold text-base text-on-surface">Permissions Matrix</h2>
        <p class="text-xs text-on-surface-variant mt-1">Granular role-based access control for system resources.</p>
      </div>

      <div class="border border-outline-variant rounded overflow-hidden bg-surface overflow-x-auto">
        <table class="w-full text-center text-sm whitespace-nowrap">
          <thead class="text-xs text-on-surface-variant bg-surface-container-lowest border-b border-outline-variant font-mono uppercase">
            <tr>
              <th class="px-4 py-3 font-medium text-left border-r border-outline-variant/50">Permission</th>
              <th class="px-4 py-3 font-medium border-r border-outline-variant/50">Superuser</th>
              <th class="px-4 py-3 font-medium border-r border-outline-variant/50">Admin</th>
              <th class="px-4 py-3 font-medium border-r border-outline-variant/50">Operator</th>
              <th class="px-4 py-3 font-medium">Viewer</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/50">
            <!-- devices:read -->
            <tr class="hover:bg-surface-container-lowest transition-colors">
              <td class="px-4 py-3 text-left font-mono text-xs text-on-surface-variant border-r border-outline-variant/50">devices:read</td>
              <td class="px-4 py-3 border-r border-outline-variant/50"><span class="material-symbols-outlined text-primary text-[20px]">check_circle</span></td>
              <td class="px-4 py-3 border-r border-outline-variant/50"><span class="material-symbols-outlined text-primary text-[20px]">check_circle</span></td>
              <td class="px-4 py-3 border-r border-outline-variant/50"><span class="material-symbols-outlined text-primary text-[20px]">check_circle</span></td>
              <td class="px-4 py-3"><span class="material-symbols-outlined text-primary text-[20px]">check_circle</span></td>
            </tr>

            <!-- devices:write -->
            <tr class="hover:bg-surface-container-lowest transition-colors">
              <td class="px-4 py-3 text-left font-mono text-xs text-on-surface-variant border-r border-outline-variant/50">devices:write</td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
              <td class="px-4 py-3">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" disabled class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface/50 after:border-surface/50 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container/50" />
                </label>
              </td>
            </tr>

            <!-- topology:edit -->
            <tr class="hover:bg-surface-container-lowest transition-colors">
              <td class="px-4 py-3 text-left font-mono text-xs text-on-surface-variant border-r border-outline-variant/50">topology:edit</td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
              <td class="px-4 py-3">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
            </tr>

            <!-- users:manage -->
            <tr class="hover:bg-surface-container-lowest transition-colors">
              <td class="px-4 py-3 text-left font-mono text-xs text-on-surface-variant border-r border-outline-variant/50">users:manage</td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:border-surface after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container" />
                </label>
              </td>
              <td class="px-4 py-3">
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" disabled class="sr-only peer" />
                  <div class="w-9 h-5 bg-surface-variant/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface/50 after:border-surface/50 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-container/50" />
                </label>
              </td>
            </tr>

            <!-- logs:view -->
            <tr class="hover:bg-surface-container-lowest transition-colors">
              <td class="px-4 py-3 text-left font-mono text-xs text-on-surface-variant border-r border-outline-variant/50">logs:view</td>
              <td class="px-4 py-3 border-r border-outline-variant/50"><span class="material-symbols-outlined text-primary text-[20px]">check_circle</span></td>
              <td class="px-4 py-3 border-r border-outline-variant/50"><span class="material-symbols-outlined text-primary text-[20px]">check_circle</span></td>
              <td class="px-4 py-3 border-r border-outline-variant/50"><span class="material-symbols-outlined text-primary text-[20px]">check_circle</span></td>
              <td class="px-4 py-3"><span class="material-symbols-outlined text-primary text-[20px]">check_circle</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Security Policies -->
    <section class="bg-surface-container-low border border-outline-variant rounded-lg p-6 flex flex-col gap-6 relative overflow-hidden shadow-glow">
      <div class="absolute top-0 left-0 w-1 h-full bg-primary/30" />
      <div>
        <h2 class="font-bold text-base text-on-surface">Security Policies</h2>
        <p class="text-xs text-on-surface-variant mt-1">Manage global security settings for authentication and sessions.</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Login Rate Limiting -->
        <div class="flex flex-col gap-4 bg-surface p-4 rounded border border-outline-variant/50 md:col-span-2">
          <h3 class="text-sm font-semibold text-on-surface">Login Rate Limiting</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col justify-center">
              <label class="block text-xs font-semibold text-on-surface mb-2">Max Attempts</label>
              <div class="flex items-center gap-3">
                <input v-model="maxAttempts" type="number" class="w-24 bg-surface-container-lowest text-on-surface border border-outline-variant rounded px-3 py-1.5 text-xs font-mono focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none font-medium" />
                <span class="text-xs text-on-surface-variant">failed logins</span>
              </div>
            </div>
            <div class="flex flex-col justify-center">
              <label class="block text-xs font-semibold text-on-surface mb-2">Lockout Duration</label>
              <div class="flex items-center gap-3">
                <input v-model="lockoutDuration" type="number" class="w-24 bg-surface-container-lowest text-on-surface border border-outline-variant rounded px-3 py-1.5 text-xs font-mono focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none font-medium" />
                <span class="text-xs text-on-surface-variant">minutes</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Session Lifecycle -->
        <div class="flex flex-col gap-4 bg-surface p-4 rounded border border-outline-variant/50 md:col-span-2">
          <h3 class="text-sm font-semibold text-on-surface">Session Lifecycle</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col justify-center">
              <label class="block text-xs font-semibold text-on-surface mb-2">Session TTL (Time-to-Live)</label>
              <div class="flex items-center gap-3">
                <input v-model="sessionTtl" type="number" class="w-24 bg-surface-container-lowest text-on-surface border border-outline-variant rounded px-3 py-1.5 text-xs font-mono focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none font-medium" />
                <span class="text-xs text-on-surface-variant">hours</span>
              </div>
            </div>
            <div class="flex flex-col justify-center">
              <label class="block text-xs font-semibold text-on-surface mb-2">Inactivity Timeout</label>
              <div class="flex items-center gap-3">
                <input v-model="inactivityTimeout" type="number" class="w-24 bg-surface-container-lowest text-on-surface border border-outline-variant rounded px-3 py-1.5 text-xs font-mono focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none font-medium" />
                <span class="text-xs text-on-surface-variant">minutes</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Force MFA -->
        <div class="flex items-center justify-between bg-surface p-4 rounded border border-outline-variant/50 md:col-span-2">
          <div>
            <span class="block text-xs font-semibold text-on-surface">Force Multi-Factor Authentication (MFA)</span>
            <span class="block text-xs text-on-surface-variant mt-0.5">Mandatory 2FA for all user roles.</span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="forceMfa" class="sr-only peer" />
            <div class="w-11 h-6 bg-surface-variant rounded-full peer peer-checked:bg-primary-container peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-surface after:rounded-full after:h-5 after:w-5 after:transition-all" />
          </label>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const maxAttempts = ref(5)
const lockoutDuration = ref(15)
const sessionTtl = ref(12)
const inactivityTimeout = ref(30)
const forceMfa = ref(true)
</script>
