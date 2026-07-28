<template>
  <div class="p-6 w-full flex flex-col lg:flex-row gap-6 text-on-surface animate-fade-in">
    <!-- Left Column -->
    <div class="lg:w-1/3 flex flex-col gap-6">
      <!-- Avatar Card -->
      <div class="bg-surface-container-high border border-outline-variant rounded-lg p-6 shadow-glow backdrop-blur-sm flex flex-col items-center text-center">
        <div class="relative mb-4">
          <div class="w-32 h-32 rounded-full border-2 border-primary bg-primary/20 flex items-center justify-center text-primary font-mono font-bold text-3xl shadow-glow">
            SJ
          </div>
          <div class="absolute bottom-0 right-0 w-4 h-4 bg-tertiary-fixed rounded-full border-2 border-surface-container-high" />
        </div>
        <h2 class="font-bold text-lg text-on-surface mb-0.5">Sarah Jenkins</h2>
        <p class="text-on-surface-variant font-semibold text-xs mb-4">Lead Engineer</p>
        <div class="w-full flex justify-between items-center bg-surface-container p-2.5 rounded mb-4 border border-outline-variant text-xs font-mono">
          <span class="text-on-surface-variant">Status: <span class="text-tertiary-fixed font-bold">Active</span></span>
          <span class="text-on-surface-variant text-[11px]">14:32:11 UTC</span>
        </div>
        <div class="flex w-full gap-2 text-xs">
          <button class="flex-1 bg-secondary-container text-on-surface py-2 px-3 rounded hover:bg-surface-bright transition-colors font-semibold border border-outline-variant">
            Upload
          </button>
          <button class="flex-1 bg-transparent text-error py-2 px-3 rounded hover:bg-error/10 transition-colors font-semibold border border-outline-variant">
            Reset
          </button>
        </div>
      </div>

      <!-- Security Settings Card -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow">
        <h3 class="font-semibold text-sm text-on-surface mb-4 pb-2 border-b border-outline-variant flex items-center gap-2">
          <span class="material-symbols-outlined text-[18px]">security</span>
          <span>Security Settings</span>
        </h3>
        <div class="flex flex-col gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Current Password</label>
            <input type="password" class="bg-surface-container-highest text-on-surface font-mono px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">New Password</label>
            <input type="password" class="bg-surface-container-highest text-on-surface font-mono px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Confirm New Password</label>
            <input type="password" class="bg-surface-container-highest text-on-surface font-mono px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" />
          </div>
          <button class="bg-surface-variant text-on-surface py-2 px-3 rounded hover:bg-surface-bright transition-colors font-semibold border border-outline-variant mt-2">
            Change Password
          </button>
        </div>
      </div>
    </div>

    <!-- Right Column -->
    <div class="lg:w-2/3 flex flex-col gap-6">
      <!-- Personal Information -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow space-y-4">
        <h2 class="font-bold text-base text-on-surface pb-2 border-b border-outline-variant">Personal Information</h2>
        <form @submit.prevent class="flex flex-col gap-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Full Name</label>
              <input v-model="fullName" type="text" class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Department</label>
              <input v-model="department" type="text" class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Role</label>
              <input v-model="role" type="text" class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Email Address</label>
              <input v-model="email" type="email" class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all" />
            </div>
          </div>
          <div class="flex justify-end pt-2">
            <button type="button" class="bg-primary text-on-primary font-semibold text-xs px-6 py-2 rounded hover:bg-primary-fixed transition-colors shadow-glow">
              Save Changes
            </button>
          </div>
        </form>
      </div>

      <!-- Appearance & Regionality -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow space-y-4">
        <h2 class="font-bold text-base text-on-surface pb-2 border-b border-outline-variant">Appearance & Regionality</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Theme</label>
            <select v-model="selectedTheme" class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all">
              <option value="system">System</option>
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Language</label>
            <select v-model="selectedLanguage" class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all">
              <option value="en">English (US)</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Timezone</label>
            <select v-model="selectedTimezone" class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary transition-all">
              <option value="utc+3">UTC+3</option>
              <option value="utc">UTC</option>
              <option value="est">EST</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">Table Density</label>
            <select v-model="selectedDensity" class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all">
              <option value="compact">Compact</option>
              <option value="standard">Standard</option>
              <option value="relaxed">Relaxed</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Active Sessions -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow space-y-4">
        <div class="flex justify-between items-center pb-2 border-b border-outline-variant">
          <h2 class="font-bold text-base text-on-surface">Active Sessions</h2>
          <button class="bg-error text-on-error font-semibold text-xs px-4 py-2 rounded hover:bg-error/90 transition-colors">
            Terminate All Other Sessions
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr class="border-b border-outline-variant text-on-surface-variant uppercase tracking-wider text-[11px]">
                <th class="py-2.5 px-3">IP Address</th>
                <th class="py-2.5 px-3">Device / Browser</th>
                <th class="py-2.5 px-3">Login Time</th>
                <th class="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/50 text-on-surface">
              <tr class="hover:bg-surface-variant/30 transition-colors">
                <td class="py-2.5 px-3">192.168.1.42</td>
                <td class="py-2.5 px-3">MacBook Pro / Chrome</td>
                <td class="py-2.5 px-3">Today, 14:32 UTC</td>
                <td class="py-2.5 px-3"><span class="text-tertiary-fixed font-bold">Current Session</span></td>
              </tr>
              <tr class="hover:bg-surface-variant/30 transition-colors">
                <td class="py-2.5 px-3">10.0.0.15</td>
                <td class="py-2.5 px-3">Windows 10 / Firefox</td>
                <td class="py-2.5 px-3">Yesterday, 09:15 UTC</td>
                <td class="py-2.5 px-3"><span class="text-on-surface-variant">Active</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const fullName = ref('Sarah Jenkins')
const department = ref('Network Operations Core')
const role = ref('Lead Engineer')
const email = ref('s.jenkins@netops.sys')

const selectedTheme = ref('dark')
const selectedLanguage = ref('en')
const selectedTimezone = ref('utc+3')
const selectedDensity = ref('standard')
</script>
