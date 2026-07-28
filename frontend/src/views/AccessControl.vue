<template>
  <div class="p-6 w-full space-y-6 pb-20 text-on-surface animate-fade-in relative">
    <!-- Toast Notification -->
    <Transition name="toast">
      <div v-if="toastMessage" class="fixed bottom-6 right-6 z-50 bg-tertiary-container border border-tertiary text-on-tertiary-container px-4 py-3 rounded-lg shadow-glow flex items-center gap-3">
        <span class="material-symbols-outlined text-[20px] text-tertiary">check_circle</span>
        <span class="text-xs font-semibold font-mono">{{ toastMessage }}</span>
      </div>
    </Transition>

    <!-- Roles Management -->
    <section class="bg-surface-container-low border border-outline-variant rounded-lg p-6 flex flex-col gap-6 shadow-glow">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="font-bold text-base text-on-surface">{{ t('rolesManagement') }}</h2>
          <p class="text-xs text-on-surface-variant mt-1">{{ t('rolesMgmtSub') }}</p>
        </div>
        <button
          @click="openAddRoleModal"
          class="bg-primary-container hover:bg-primary-fixed text-on-primary-container px-4 py-1.5 rounded text-sm font-semibold transition-colors flex items-center gap-2 shadow-[0_0_10px_rgba(34,211,238,0.2)] hover:shadow-[0_0_15px_rgba(34,211,238,0.4)] cursor-pointer"
        >
          <span class="material-symbols-outlined text-[18px]">add</span> {{ t('addNewRole') }}
        </button>
      </div>

      <div class="border border-outline-variant rounded overflow-hidden bg-surface overflow-x-auto">
        <table class="w-full text-left text-sm whitespace-nowrap">
          <thead class="text-xs text-on-surface-variant bg-surface-container-lowest border-b border-outline-variant font-mono uppercase">
            <tr>
              <th class="px-4 py-3 font-medium">{{ t('roleName') }}</th>
              <th class="px-4 py-3 font-medium">{{ t('description') }}</th>
              <th class="px-4 py-3 font-medium">{{ t('usersCount') }}</th>
              <th class="px-4 py-3 font-medium text-right">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/50">
            <tr v-for="role in roles" :key="role.id" class="hover:bg-surface-container-lowest transition-colors group">
              <td class="px-4 py-3 font-medium text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-primary text-[18px]">shield</span>
                <span>{{ role.name }}</span>
              </td>
              <td class="px-4 py-3 text-on-surface-variant text-xs">{{ role.description }}</td>
              <td class="px-4 py-3 font-mono text-on-surface text-xs">{{ role.usersCount }}</td>
              <td class="px-4 py-3 text-right">
                <button @click="openEditRoleModal(role)" class="text-on-surface-variant hover:text-primary transition-colors p-1 cursor-pointer">
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
        <h2 class="font-bold text-base text-on-surface">{{ t('permissionsMatrix') }}</h2>
        <p class="text-xs text-on-surface-variant mt-1">{{ t('permMatrixSub') }}</p>
      </div>

      <div class="border border-outline-variant rounded overflow-hidden bg-surface overflow-x-auto">
        <table class="w-full text-center text-sm whitespace-nowrap">
          <thead class="text-xs text-on-surface-variant bg-surface-container-lowest border-b border-outline-variant font-mono uppercase">
            <tr>
              <th class="px-4 py-3 font-medium text-left border-r border-outline-variant/50">{{ t('permission') }}</th>
              <th class="px-4 py-3 font-medium border-r border-outline-variant/50">Superuser</th>
              <th class="px-4 py-3 font-medium border-r border-outline-variant/50">Admin</th>
              <th class="px-4 py-3 font-medium border-r border-outline-variant/50">Operator</th>
              <th class="px-4 py-3 font-medium">Viewer</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/50">
            <tr v-for="perm in matrixPermissions" :key="perm.key" class="hover:bg-surface-container-lowest transition-colors">
              <td class="px-4 py-3 text-left font-mono text-xs text-on-surface-variant border-r border-outline-variant/50">{{ perm.key }}</td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <span v-if="perm.fixedSuper" class="material-symbols-outlined text-primary text-[20px]">check_circle</span>
                <UiToggle v-else :modelValue="perm.superuser" @update:modelValue="val => updatePerm(perm, 'superuser', val)" />
              </td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <UiToggle :modelValue="perm.admin" @update:modelValue="val => updatePerm(perm, 'admin', val)" />
              </td>
              <td class="px-4 py-3 border-r border-outline-variant/50">
                <UiToggle :modelValue="perm.operator" @update:modelValue="val => updatePerm(perm, 'operator', val)" />
              </td>
              <td class="px-4 py-3">
                <UiToggle :modelValue="perm.viewer" :disabled="perm.viewerDisabled" @update:modelValue="val => updatePerm(perm, 'viewer', val)" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Security Policies -->
    <section class="bg-surface-container-low border border-outline-variant rounded-lg p-6 flex flex-col gap-6 relative overflow-hidden shadow-glow">
      <div class="absolute top-0 left-0 w-1 h-full bg-primary/30" />
      <div class="flex items-center justify-between">
        <div>
          <h2 class="font-bold text-base text-on-surface">{{ t('securityPolicies') }}</h2>
          <p class="text-xs text-on-surface-variant mt-1">{{ t('secPoliciesSub') }}</p>
        </div>
        <button
          @click="saveSecurityPolicies"
          class="bg-primary text-on-primary px-4 py-1.5 rounded text-xs font-semibold shadow-glow hover:bg-primary-container transition-colors cursor-pointer"
        >
          Сохранить политики
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Login Rate Limiting -->
        <div class="flex flex-col gap-4 bg-surface p-4 rounded border border-outline-variant/50 md:col-span-2">
          <h3 class="text-sm font-semibold text-on-surface">{{ t('loginRateLimiting') }}</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col justify-center">
              <label class="block text-xs font-semibold text-on-surface mb-2">{{ t('maxAttemptsLabel') }}</label>
              <div class="flex items-center gap-3">
                <input v-model="maxAttempts" type="number" class="w-24 bg-surface-container-lowest text-on-surface border border-outline-variant rounded px-3 py-1.5 text-xs font-mono focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none font-medium" />
                <span class="text-xs text-on-surface-variant">{{ t('failedLogins') }}</span>
              </div>
            </div>
            <div class="flex flex-col justify-center">
              <label class="block text-xs font-semibold text-on-surface mb-2">{{ t('lockoutDurationLabel') }}</label>
              <div class="flex items-center gap-3">
                <input v-model="lockoutDuration" type="number" class="w-24 bg-surface-container-lowest text-on-surface border border-outline-variant rounded px-3 py-1.5 text-xs font-mono focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none font-medium" />
                <span class="text-xs text-on-surface-variant">{{ t('minutes') }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Session Lifecycle -->
        <div class="flex flex-col gap-4 bg-surface p-4 rounded border border-outline-variant/50 md:col-span-2">
          <h3 class="text-sm font-semibold text-on-surface">{{ t('sessionLifecycle') }}</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col justify-center">
              <label class="block text-xs font-semibold text-on-surface mb-2">{{ t('sessionTtl') }}</label>
              <div class="flex items-center gap-3">
                <input v-model="sessionTtl" type="number" class="w-24 bg-surface-container-lowest text-on-surface border border-outline-variant rounded px-3 py-1.5 text-xs font-mono focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none font-medium" />
                <span class="text-xs text-on-surface-variant">{{ t('hours') }}</span>
              </div>
            </div>
            <div class="flex flex-col justify-center">
              <label class="block text-xs font-semibold text-on-surface mb-2">{{ t('inactivityTimeout') }}</label>
              <div class="flex items-center gap-3">
                <input v-model="inactivityTimeout" type="number" class="w-24 bg-surface-container-lowest text-on-surface border border-outline-variant rounded px-3 py-1.5 text-xs font-mono focus:border-primary-container focus:ring-1 focus:ring-primary-container outline-none font-medium" />
                <span class="text-xs text-on-surface-variant">{{ t('minutes') }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Force MFA -->
        <div class="flex items-center justify-between bg-surface p-4 rounded border border-outline-variant/50 md:col-span-2">
          <div>
            <span class="block text-xs font-semibold text-on-surface">{{ t('forceMfa') }}</span>
            <span class="block text-xs text-on-surface-variant mt-0.5">{{ t('mfaSub') }}</span>
          </div>
          <UiToggle v-model="forceMfa" />
        </div>
      </div>
    </section>

    <!-- Modal: Add/Edit Role -->
    <div v-if="isRoleModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 w-full max-w-md shadow-2xl space-y-5 animate-fade-in">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <h3 class="font-bold text-lg text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">shield</span>
            <span>{{ editingRole ? 'Редактировать роль' : 'Добавить роль' }}</span>
          </h3>
          <button @click="isRoleModalOpen = false" class="text-on-surface-variant hover:text-on-surface">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <form @submit.prevent="saveRole" class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">Название роли</label>
            <input
              v-model="roleForm.name"
              type="text"
              required
              placeholder="Security Specialist"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none font-mono"
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">Описание</label>
            <textarea
              v-model="roleForm.description"
              required
              rows="3"
              placeholder="Полное описание прав этой роли в системе"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          <div class="flex justify-end gap-3 pt-3 border-t border-outline-variant/60">
            <button
              type="button"
              @click="isRoleModalOpen = false"
              class="px-4 py-2 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold hover:bg-surface-bright"
            >
              Отмена
            </button>
            <button
              type="submit"
              class="px-4 py-2 rounded bg-primary text-on-primary text-xs font-semibold shadow-glow hover:bg-primary-container"
            >
              Сохранить роль
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import UiToggle from '@/components/common/UiToggle.vue'
import { useI18n } from '@/core/i18n'
import { apiFetchRoles, apiCreateRole, apiUpdateRole } from '@/core/api'

const { t } = useI18n()
const toastMessage = ref('')

function showToast(msg: string) {
  toastMessage.value = msg
  setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
}

// ── Security Policies State ──
const maxAttempts = ref(5)
const lockoutDuration = ref(15)
const sessionTtl = ref(12)
const inactivityTimeout = ref(30)
const forceMfa = ref(true)

function saveSecurityPolicies() {
  showToast('Политики безопасности успешно обновлены')
}

// ── Roles State ──
interface RoleItem {
  id: string
  name: string
  description: string
  usersCount: number
  is_system?: boolean
  permissions?: string[]
}

const roles = ref<RoleItem[]>([])
const isLoadingRoles = ref(false)

async function loadRoles() {
  isLoadingRoles.value = true
  try {
    const data = await apiFetchRoles()
    roles.value = (data || []).map((r: any) => ({
      id: r.id,
      name: r.name,
      description: r.description,
      usersCount: r.users_count || 0,
      is_system: r.is_system,
      permissions: r.permissions || []
    }))
  } catch (err) {
    console.error('Failed to load roles:', err)
  } finally {
    isLoadingRoles.value = false
  }
}

const isRoleModalOpen = ref(false)
const editingRole = ref<RoleItem | null>(null)
const roleForm = reactive({ name: '', description: '' })

function openAddRoleModal() {
  editingRole.value = null
  roleForm.name = ''
  roleForm.description = ''
  isRoleModalOpen.value = true
}

function openEditRoleModal(role: RoleItem) {
  editingRole.value = role
  roleForm.name = role.name
  roleForm.description = role.description
  isRoleModalOpen.value = true
}

async function saveRole() {
  try {
    if (editingRole.value) {
      await apiUpdateRole(editingRole.value.id, {
        name: roleForm.name,
        description: roleForm.description,
        permission_ids: editingRole.value.permissions || []
      })
      showToast(`Роль "${roleForm.name}" успешно обновлена`)
    } else {
      await apiCreateRole({
        name: roleForm.name,
        description: roleForm.description,
        permission_ids: ['audit.view']
      })
      showToast(`Роль "${roleForm.name}" успешно создана`)
    }
    await loadRoles()
    isRoleModalOpen.value = false
  } catch (err: any) {
    showToast(`Ошибка: ${err?.response?.data?.detail || 'Не удалось сохранить роль'}`)
  }
}

// ── Permissions Matrix State ──
interface PermRow {
  key: string
  fixedSuper?: boolean
  superuser: boolean
  admin: boolean
  operator: boolean
  viewer: boolean
  viewerDisabled?: boolean
}

const matrixPermissions = ref<PermRow[]>([
  { key: 'devices:read', fixedSuper: true, superuser: true, admin: true, operator: true, viewer: true },
  { key: 'devices:write', superuser: true, admin: true, operator: false, viewer: false, viewerDisabled: true },
  { key: 'topology:edit', superuser: true, admin: true, operator: true, viewer: false },
  { key: 'users:manage', superuser: true, admin: false, operator: false, viewer: false, viewerDisabled: true },
  { key: 'logs:view', fixedSuper: true, superuser: true, admin: true, operator: true, viewer: true }
])

function updatePerm(perm: PermRow, roleKey: 'superuser' | 'admin' | 'operator' | 'viewer', val: boolean) {
  perm[roleKey] = val
  showToast(`Права для ${perm.key} обновлены`)
}

onMounted(() => {
  loadRoles()
})
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(1rem);
}
</style>


