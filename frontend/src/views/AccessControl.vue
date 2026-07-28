<template>
  <div class="p-6 flex-1 max-w-6xl w-full mx-auto space-y-6 animate-fade-in text-on-surface">
    <!-- Roles Management Section -->
    <section class="bg-surface-container-low border border-outline-variant rounded-xl p-6 flex flex-col gap-6 shadow-glow">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="font-bold text-lg text-on-surface">Roles Management</h2>
          <p class="text-xs text-on-surface-variant mt-1">Define and manage custom access roles across system modules.</p>
        </div>
        <button class="bg-primary-container hover:bg-primary-fixed text-on-primary-container px-4 py-1.5 rounded text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-glow">
          <span class="material-symbols-outlined text-[18px]">add</span> Add New Role
        </button>
      </div>

      <div class="border border-outline-variant rounded-lg overflow-hidden bg-surface overflow-x-auto">
        <table class="w-full text-left text-sm whitespace-nowrap">
          <thead class="text-xs text-on-surface-variant bg-surface-container-lowest border-b border-outline-variant font-mono uppercase">
            <tr>
              <th class="px-4 py-3 font-semibold">Role Name</th>
              <th class="px-4 py-3 font-semibold">Description</th>
              <th class="px-4 py-3 font-semibold">Users</th>
              <th class="px-4 py-3 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/50">
            <tr v-for="role in roles" :key="role.name" class="hover:bg-surface-container-lowest transition-colors group">
              <td class="px-4 py-3 font-bold text-on-surface flex items-center gap-2">
                <span class="w-2 h-2 rounded-full" :class="role.badgeColor" />
                {{ role.name }}
              </td>
              <td class="px-4 py-3 text-on-surface-variant text-xs">{{ role.description }}</td>
              <td class="px-4 py-3 font-mono text-primary text-xs">{{ role.usersCount }}</td>
              <td class="px-4 py-3 text-right">
                <button class="text-on-surface-variant hover:text-primary transition-colors p-1">
                  <span class="material-symbols-outlined text-[18px]">edit</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Permissions Matrix Section -->
    <section class="bg-surface-container-low border border-outline-variant rounded-xl p-6 flex flex-col gap-4 shadow-glow">
      <h2 class="font-bold text-lg text-on-surface">Permissions Matrix</h2>
      <p class="text-xs text-on-surface-variant">Fine-grained capability configuration per module group.</p>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        <div v-for="perm in permissions" :key="perm.id" class="p-4 bg-surface-container-highest rounded-lg border border-outline-variant/30 flex items-start justify-between">
          <div>
            <p class="text-xs font-bold text-on-surface font-mono">{{ perm.code }}</p>
            <p class="text-[11px] text-on-surface-variant mt-1">{{ perm.label }}</p>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="perm.enabled" class="sr-only peer" />
            <div class="w-8 h-4 bg-surface-variant rounded-full peer-checked:bg-primary/20 peer-checked:after:translate-x-full peer-checked:after:bg-primary transition-all after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-on-surface-variant after:rounded-full after:h-3 after:w-3 after:transition-all" />
          </label>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const roles = ref([
  { name: 'Superuser', description: 'Full system access and destructive capabilities', usersCount: 3, badgeColor: 'bg-primary' },
  { name: 'Admin', description: 'Administrative control, limited destructive actions', usersCount: 12, badgeColor: 'bg-tertiary' },
  { name: 'Operator', description: 'Monitoring and alarm acknowledgment', usersCount: 28, badgeColor: 'bg-amber-400' },
  { name: 'Viewer', description: 'Read-only access to metrics and reports', usersCount: 5, badgeColor: 'bg-outline' }
])

const permissions = ref([
  { id: '1', code: 'telemetry:write', label: 'Modify live stream telemetry configurations', enabled: true },
  { id: '2', code: 'modules:restart', label: 'Restart service instances remotely', enabled: true },
  { id: '3', code: 'users:manage', label: 'Create and remove operator accounts', enabled: false },
  { id: '4', code: 'logs:export', label: 'Download encrypted audit logs', enabled: true }
])
</script>
