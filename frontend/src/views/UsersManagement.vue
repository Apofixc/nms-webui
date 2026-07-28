<template>
  <div class="p-6 flex-1 max-w-6xl w-full mx-auto space-y-6 animate-fade-in text-on-surface">
    <!-- Action Bar -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
      <div class="flex items-center space-x-3">
        <div class="relative">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Filter operators..."
            class="bg-surface-container-highest border border-outline-variant text-on-surface rounded pl-9 pr-4 py-1.5 focus:border-primary focus:ring-1 focus:ring-primary text-xs w-72 font-mono placeholder:text-on-surface-variant"
          />
          <span class="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px] pointer-events-none">filter_list</span>
        </div>
        <span class="text-on-surface-variant font-mono text-xs">Showing {{ filteredUsers.length }} Active Operators</span>
      </div>

      <button class="bg-primary text-on-primary px-4 py-2 rounded text-xs font-bold flex items-center gap-1.5 shadow-glow hover:bg-primary-container transition-colors">
        <span class="material-symbols-outlined text-[18px]">person_add</span>
        <span>Add New User</span>
      </button>
    </div>

    <!-- Tactical Data Table -->
    <div class="bg-surface-container-low border border-outline-variant rounded-xl overflow-hidden shadow-glow">
      <table class="w-full text-left border-collapse">
        <thead class="bg-surface-container border-b border-outline-variant text-on-surface-variant font-mono text-xs uppercase tracking-wider">
          <tr>
            <th class="px-4 py-3 font-semibold">User</th>
            <th class="px-4 py-3 font-semibold">Username / ID</th>
            <th class="px-4 py-3 font-semibold">Role</th>
            <th class="px-4 py-3 font-semibold">Status</th>
            <th class="px-4 py-3 font-semibold text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant text-xs font-sans">
          <tr v-for="user in filteredUsers" :key="user.id" class="hover:bg-surface-container-lowest transition-colors">
            <td class="px-4 py-3 font-bold text-on-surface flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-primary/20 border border-primary/50 text-primary font-mono font-bold flex items-center justify-center text-xs flex-shrink-0">
                {{ user.avatar }}
              </div>
              <div>
                <span class="block font-bold text-on-surface">{{ user.name }}</span>
                <span class="block text-[10px] text-on-surface-variant font-mono">{{ user.email }}</span>
              </div>
            </td>
            <td class="px-4 py-3 font-mono text-primary font-bold">{{ user.username }}</td>
            <td class="px-4 py-3">
              <span class="px-2 py-0.5 rounded font-mono text-[11px] bg-surface-container-highest border border-outline-variant/40 text-on-surface">
                {{ user.role }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span :class="['px-2 py-0.5 rounded-full font-mono text-[10px] font-bold uppercase', user.status === 'Active' ? 'bg-tertiary/20 text-tertiary' : 'bg-surface-variant text-outline']">
                {{ user.status }}
              </span>
            </td>
            <td class="px-4 py-3 text-right">
              <button class="text-on-surface-variant hover:text-primary p-1 transition-colors">
                <span class="material-symbols-outlined text-[18px]">more_vert</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const searchQuery = ref('')

const users = ref([
  { id: '1', name: 'Mihail Apofixc', username: 'admin', email: 'admin@nms.net', role: 'Superuser', status: 'Active', avatar: 'MA' },
  { id: '2', name: 'Alexey NetOps', username: 'operator-1', email: 'alexey@nms.net', role: 'Operator', status: 'Active', avatar: 'AN' },
  { id: '3', name: 'Elena System', username: 'elena-sys', email: 'elena@nms.net', role: 'Admin', status: 'Active', avatar: 'ES' },
  { id: '4', name: 'Guest Monitor', username: 'guest', email: 'guest@nms.net', role: 'Viewer', status: 'Disabled', avatar: 'GM' }
])

const filteredUsers = computed(() => {
  if (!searchQuery.value.trim()) return users.value
  const q = searchQuery.value.toLowerCase()
  return users.value.filter(u => u.name.toLowerCase().includes(q) || u.username.toLowerCase().includes(q))
})
</script>
