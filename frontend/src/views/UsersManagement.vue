<template>
  <div class="p-6 w-full flex flex-col gap-6 text-on-surface animate-fade-in">
    <!-- Action Bar -->
    <div class="flex justify-between items-center mb-2">
      <div class="flex items-center space-x-4">
        <div class="relative">
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('filterOperators')"
            class="bg-surface-container-highest border border-outline-variant text-on-surface rounded pl-10 pr-4 py-2 focus:border-primary focus:ring-1 focus:ring-primary text-sm w-80 font-mono placeholder:text-on-surface-variant outline-none"
          />
          <span class="material-symbols-outlined absolute left-3 top-2.5 text-on-surface-variant text-[20px] pointer-events-none">filter_list</span>
        </div>
        <span class="text-on-surface-variant text-sm">{{ t('showingOperators') }}: {{ filteredUsers.length }}</span>
      </div>

      <button class="bg-primary text-on-primary px-4 py-2 rounded font-semibold text-sm flex items-center shadow-glow hover:bg-primary-container transition-colors">
        <span class="material-symbols-outlined mr-2 text-[20px]">person_add</span>
        {{ t('addNewUser') }}
      </button>
    </div>

    <!-- Tactical Data Table -->
    <div class="bg-surface-container-low border border-outline-variant rounded-lg overflow-hidden w-full shadow-glow">
      <table class="w-full text-left border-collapse">
        <thead class="bg-surface-container border-b border-outline-variant text-on-surface-variant font-mono text-xs uppercase tracking-wider">
          <tr>
            <th class="px-4 py-3 font-semibold w-1/4">{{ t('user') }}</th>
            <th class="px-4 py-3 font-semibold w-1/4">{{ t('usernameId') }}</th>
            <th class="px-4 py-3 font-semibold w-1/6">{{ t('role') }}</th>
            <th class="px-4 py-3 font-semibold w-1/6">{{ t('status') }}</th>
            <th class="px-4 py-3 font-semibold text-right">{{ t('actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant">
          <!-- Row 1: Sarah Jenkins -->
          <tr class="hover:bg-surface-container-highest transition-colors group">
            <td class="px-4 py-3">
              <div class="flex items-center">
                <div class="w-10 h-10 rounded border border-outline-variant bg-primary/20 text-primary flex items-center justify-center font-mono font-bold text-xs mr-3 shadow-glow">
                  SJ
                </div>
                <div>
                  <div class="text-on-surface font-semibold text-sm">Sarah Jenkins</div>
                  <div class="text-on-surface-variant text-xs">Lead NOC Operator</div>
                </div>
              </div>
            </td>
            <td class="px-4 py-3 font-mono text-secondary text-xs">
              s.jenkins_01<br />
              <span class="text-on-surface-variant text-xs opacity-70">UID: 994-A2</span>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-1 rounded bg-surface-variant border border-outline-variant text-on-surface text-xs font-semibold">
                <span class="material-symbols-outlined text-[14px] mr-1 text-primary">admin_panel_settings</span>
                Superuser
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center space-x-2">
                <div class="w-2 h-2 rounded-full bg-tertiary shadow-glow" />
                <span class="text-tertiary text-sm">{{ t('online') }}</span>
              </div>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex justify-end space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors" title="Edit">
                  <span class="material-symbols-outlined text-[20px]">edit</span>
                </button>
                <button class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors" title="Reset Password">
                  <span class="material-symbols-outlined text-[20px]">key</span>
                </button>
                <button class="p-1.5 text-on-surface-variant hover:text-error rounded hover:bg-surface-variant transition-colors" title="Delete">
                  <span class="material-symbols-outlined text-[20px]">delete</span>
                </button>
              </div>
            </td>
          </tr>

          <!-- Row 2: Marcus Vance -->
          <tr class="hover:bg-surface-container-highest transition-colors group">
            <td class="px-4 py-3">
              <div class="flex items-center">
                <div class="w-10 h-10 rounded border border-outline-variant bg-surface-variant flex items-center justify-center text-on-surface-variant mr-3 font-bold text-xs">
                  MV
                </div>
                <div>
                  <div class="text-on-surface font-semibold text-sm">Marcus Vance</div>
                  <div class="text-on-surface-variant text-xs">Security Analyst</div>
                </div>
              </div>
            </td>
            <td class="px-4 py-3 font-mono text-secondary text-xs">
              m.vance_sec<br />
              <span class="text-on-surface-variant text-xs opacity-70">UID: 442-B7</span>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-1 rounded bg-surface-variant border border-outline-variant text-on-surface text-xs font-semibold">
                <span class="material-symbols-outlined text-[14px] mr-1 text-tertiary">manage_accounts</span>
                Operator
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center space-x-2">
                <div class="w-2 h-2 rounded-full bg-on-surface-variant" />
                <span class="text-on-surface-variant text-sm">{{ t('offline') }}</span>
              </div>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex justify-end space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors" title="Edit">
                  <span class="material-symbols-outlined text-[20px]">edit</span>
                </button>
                <button class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors" title="Reset Password">
                  <span class="material-symbols-outlined text-[20px]">key</span>
                </button>
                <button class="p-1.5 text-on-surface-variant hover:text-error rounded hover:bg-surface-variant transition-colors" title="Delete">
                  <span class="material-symbols-outlined text-[20px]">delete</span>
                </button>
              </div>
            </td>
          </tr>

          <!-- Row 3: System Auditor (Locked) -->
          <tr class="hover:bg-surface-container-highest transition-colors group opacity-60">
            <td class="px-4 py-3">
              <div class="flex items-center">
                <div class="w-10 h-10 rounded border border-error-container bg-surface-variant flex items-center justify-center text-error mr-3">
                  <span class="material-symbols-outlined text-[20px]">person_off</span>
                </div>
                <div>
                  <div class="text-on-surface font-semibold text-sm">System Auditor</div>
                  <div class="text-on-surface-variant text-xs">External Compliance</div>
                </div>
              </div>
            </td>
            <td class="px-4 py-3 font-mono text-secondary text-xs">
              ext_audit_09<br />
              <span class="text-on-surface-variant text-xs opacity-70">UID: EXT-99</span>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-1 rounded bg-surface-variant border border-outline-variant text-on-surface text-xs font-semibold">
                <span class="material-symbols-outlined text-[14px] mr-1 text-on-surface-variant">visibility</span>
                Viewer
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="flex items-center space-x-2 text-error">
                <span class="material-symbols-outlined text-[16px]">lock</span>
                <span class="text-sm font-semibold">{{ t('locked') }}</span>
              </div>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex justify-end space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors" title="Edit">
                  <span class="material-symbols-outlined text-[20px]">edit</span>
                </button>
                <button class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors" title="Reset Password">
                  <span class="material-symbols-outlined text-[20px]">key</span>
                </button>
                <button class="p-1.5 text-on-surface-variant hover:text-error rounded hover:bg-surface-variant transition-colors" title="Delete">
                  <span class="material-symbols-outlined text-[20px]">delete</span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="mt-4 text-center text-on-surface-variant text-sm font-mono">
      {{ t('endOfUserList') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from '@/core/i18n'

const { t } = useI18n()
const searchQuery = ref('')

const users = ref([
  { id: '1', name: 'Sarah Jenkins', username: 's.jenkins_01' },
  { id: '2', name: 'Marcus Vance', username: 'm.vance_sec' },
  { id: '3', name: 'System Auditor', username: 'ext_audit_09' }
])

const filteredUsers = computed(() => {
  if (!searchQuery.value.trim()) return users.value
  const q = searchQuery.value.toLowerCase()
  return users.value.filter(u => u.name.toLowerCase().includes(q) || u.username.toLowerCase().includes(q))
})
</script>
