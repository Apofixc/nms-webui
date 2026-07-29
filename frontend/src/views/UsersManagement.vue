<template>
  <div class="p-6 w-full flex flex-col gap-6 text-on-surface animate-fade-in relative">
    <!-- Toast Notification -->
    <Transition name="toast">
      <div v-if="toastMessage" class="fixed bottom-6 right-6 z-50 bg-tertiary-container border border-tertiary text-on-tertiary-container px-4 py-3 rounded-lg shadow-glow flex items-center gap-3">
        <span class="material-symbols-outlined text-[20px] text-tertiary">check_circle</span>
        <span class="text-xs font-semibold font-mono">{{ toastMessage }}</span>
      </div>
    </Transition>

    <!-- Action Bar -->
    <div class="flex justify-between items-center mb-2">
      <div class="flex items-center space-x-4">
        <div class="relative">
          <input
            v-model="searchQuery"
            @input="handleSearch"
            type="text"
            :placeholder="t('filterOperators')"
            class="bg-surface-container-highest border border-outline-variant text-on-surface rounded pl-10 pr-4 py-2 focus:border-primary focus:ring-1 focus:ring-primary text-sm w-80 font-mono placeholder:text-on-surface-variant outline-none"
          />
          <span class="material-symbols-outlined absolute left-3 top-2.5 text-on-surface-variant text-[20px] pointer-events-none">filter_list</span>
        </div>
        <span class="text-on-surface-variant text-sm">{{ t('showingOperators') }}: {{ totalUsers }}</span>
      </div>

      <button
        @click="openAddUserModal"
        class="bg-primary text-on-primary px-4 py-2 rounded font-semibold text-sm flex items-center shadow-glow hover:bg-primary-container transition-colors cursor-pointer"
      >
        <span class="material-symbols-outlined mr-2 text-[20px]">person_add</span>
        {{ t('addNewUser') }}
      </button>
    </div>

    <!-- Data Table -->
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
          <tr v-if="isLoading" class="text-center">
            <td colspan="5" class="px-4 py-8 text-on-surface-variant font-mono text-sm">
              {{ lang === 'ru' ? 'Загрузка списка пользователей...' : 'Loading user list...' }}
            </td>
          </tr>
          <tr
            v-else
            v-for="user in users"
            :key="user.id"
            class="hover:bg-surface-container-highest transition-colors group"
            :class="user.isLocked && 'opacity-60'"
          >
            <!-- User Profile Cell -->
            <td class="px-4 py-3">
              <div class="flex items-center">
                <div
                  class="w-10 h-10 rounded border border-outline-variant flex items-center justify-center font-mono font-bold text-xs mr-3 shadow-glow overflow-hidden flex-shrink-0"
                  :class="user.role === 'Superuser' ? 'bg-primary/20 text-primary border-primary/40' : 'bg-surface-variant text-on-surface-variant'"
                >
                  <img v-if="user.avatar" :src="user.avatar" class="w-full h-full object-cover" alt="Avatar" />
                  <span v-else-if="user.isLocked" class="material-symbols-outlined text-error text-[20px]">person_off</span>
                  <span v-else>{{ getInitials(user.name) }}</span>
                </div>
                <div>
                  <div class="text-on-surface font-semibold text-sm">{{ user.name }}</div>
                  <div class="text-on-surface-variant text-xs flex flex-col">
                    <span v-if="user.title" class="font-medium text-on-surface-variant">{{ user.title }}</span>
                    <span v-if="user.email" class="text-outline text-[11px] font-mono">{{ user.email }}</span>
                  </div>
                </div>
              </div>
            </td>

            <!-- Username & UID -->
            <td class="px-4 py-3 font-mono text-secondary text-xs">
              {{ user.username }}<br />
              <span class="text-on-surface-variant text-xs opacity-70">UID: {{ user.uid }}</span>
            </td>

            <!-- Role Badge -->
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-1 rounded bg-surface-variant border border-outline-variant text-on-surface text-xs font-semibold">
                <span
                  class="material-symbols-outlined text-[14px] mr-1"
                  :class="{
                    'text-primary': user.role === 'Superuser',
                    'text-tertiary': user.role === 'Operator',
                    'text-on-surface-variant': user.role === 'Viewer'
                  }"
                >
                  {{ user.role === 'Superuser' ? 'admin_panel_settings' : user.role === 'Operator' ? 'manage_accounts' : 'visibility' }}
                </span>
                {{ getRoleTitle(user.role) }}
              </span>
            </td>

            <!-- Dynamic Real-time Status Indicator -->
            <td class="px-4 py-3">
              <div v-if="user.isLocked" class="flex items-center space-x-2 text-error">
                <span class="material-symbols-outlined text-[16px]">lock</span>
                <span class="text-sm font-semibold">{{ t('locked') }}</span>
              </div>
              <div v-else-if="user.isOnline" class="flex items-center space-x-2">
                <div class="w-2 h-2 rounded-full bg-tertiary shadow-glow animate-pulse" />
                <span class="text-tertiary text-sm font-semibold">{{ t('online') }}</span>
              </div>
              <div v-else class="flex items-center space-x-2">
                <div class="w-2 h-2 rounded-full bg-on-surface-variant/60" />
                <span class="text-on-surface-variant text-sm">{{ t('offline') }}</span>
              </div>
            </td>

            <!-- Actions Row -->
            <td class="px-4 py-3 text-right">
              <div class="flex justify-end space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  @click="openEditUserModal(user)"
                  class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors cursor-pointer"
                  :title="t('editTooltip')"
                >
                  <span class="material-symbols-outlined text-[20px]">edit</span>
                </button>
                <button
                  @click="toggleLockUser(user)"
                  class="p-1.5 text-on-surface-variant hover:text-amber-400 rounded hover:bg-surface-variant transition-colors cursor-pointer"
                  :title="user.isLocked ? t('unlock') : t('lock')"
                >
                  <span class="material-symbols-outlined text-[20px]">{{ user.isLocked ? 'lock_open' : 'lock' }}</span>
                </button>
                <button
                  @click="openResetPasswordModal(user)"
                  class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors cursor-pointer"
                  :title="t('resetPasswordTooltip')"
                >
                  <span class="material-symbols-outlined text-[20px]">key</span>
                </button>
                <button
                  @click="confirmDeleteUser(user)"
                  class="p-1.5 text-on-surface-variant hover:text-error rounded hover:bg-surface-variant transition-colors cursor-pointer"
                  :title="t('deleteTooltip')"
                >
                  <span class="material-symbols-outlined text-[20px]">delete</span>
                </button>
              </div>
            </td>
          </tr>

          <!-- Empty Search Results -->
          <tr v-if="!isLoading && users.length === 0">
            <td colspan="5" class="px-4 py-8 text-center text-on-surface-variant text-sm font-mono">
              {{ t('noUsersFound') }} "{{ searchQuery }}"
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Server-side Pagination Footer -->
      <div v-if="totalUsers > 0" class="px-4 py-3 border-t border-outline-variant flex items-center justify-between font-mono text-xs text-on-surface-variant bg-surface-container/50">
        <span>Пользователи: {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, totalUsers) }} из {{ totalUsers }}</span>
        <div class="flex items-center gap-3">
          <span>Страница {{ currentPage }} из {{ totalPages }}</span>
          <div class="flex gap-1">
            <button
              @click="changePage(currentPage - 1)"
              :disabled="currentPage === 1"
              class="px-2 py-1 rounded border border-outline-variant hover:bg-surface-variant disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
            >
              &lt;
            </button>
            <button
              @click="changePage(currentPage + 1)"
              :disabled="currentPage >= totalPages"
              class="px-2 py-1 rounded border border-outline-variant hover:bg-surface-variant disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
            >
              &gt;
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Add / Edit User -->
    <div v-if="isUserModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 w-full max-w-md shadow-2xl space-y-5 animate-fade-in">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <h3 class="font-bold text-lg text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">{{ editingUserId ? 'manage_accounts' : 'person_add' }}</span>
            <span>{{ editingUserId ? t('editUserTitle') : t('addUserTitle') }}</span>
          </h3>
          <button @click="closeUserModal" class="text-on-surface-variant hover:text-on-surface cursor-pointer">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <form @submit.prevent="saveUser" class="space-y-4">
          <!-- Full Name -->
          <div>
            <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">{{ t('fullNameLabel') }}</label>
            <input
              v-model="userForm.name"
              type="text"
              required
              :placeholder="t('fullNamePlaceholder')"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          <!-- Separated: Title / Department and Email -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">{{ t('titleDepartmentLabel') }}</label>
              <input
                v-model="userForm.title"
                type="text"
                :placeholder="t('titleDepartmentPlaceholder')"
                class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              />
            </div>
            <div>
              <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">E-mail</label>
              <input
                v-model="userForm.email"
                type="email"
                placeholder="user@nms.local"
                class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none font-mono"
              />
            </div>
          </div>

          <!-- Username & UID -->
          <div class="grid gap-3" :class="editingUserId ? 'grid-cols-2' : 'grid-cols-1'">
            <div>
              <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">{{ t('usernameLabel') }}</label>
              <input
                v-model="userForm.username"
                type="text"
                required
                :placeholder="t('usernamePlaceholder')"
                class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none font-mono"
              />
            </div>
            <div v-if="editingUserId">
              <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">{{ t('uidLabel') }}</label>
              <input
                v-model="userForm.uid"
                type="text"
                disabled
                class="w-full bg-surface-container border border-outline-variant/40 rounded px-3 py-2 text-xs text-on-surface-variant font-mono cursor-not-allowed opacity-70"
              />
            </div>
          </div>

          <!-- Password (for new users) -->
          <div v-if="!editingUserId">
            <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">Пароль</label>
            <input
              v-model="userForm.password"
              type="password"
              required
              placeholder="••••••••"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none font-mono"
            />
          </div>

          <!-- Role & Account Lock -->
          <div class="grid gap-3" :class="editingUserId ? 'grid-cols-2' : 'grid-cols-1'">
            <div>
              <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">{{ t('roleLabel') }}</label>
              <select
                v-model="userForm.role_id"
                class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              >
                <option v-for="r in rolesList" :key="r.id" :value="r.id">{{ getRoleTitle(r.name) }}</option>
              </select>
            </div>

            <div v-if="editingUserId" class="flex flex-col justify-end">
              <label class="flex items-center gap-2 cursor-pointer py-2">
                <input
                  v-model="userForm.isLocked"
                  type="checkbox"
                  class="rounded border-outline-variant bg-surface-container-high text-error focus:ring-error"
                />
                <span class="text-xs font-semibold text-on-surface">{{ t('lockAccessLabel') }}</span>
              </label>
            </div>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                v-model="userForm.mustChangePassword"
                type="checkbox"
                class="rounded border-outline-variant bg-surface-container-high text-primary focus:ring-primary"
              />
              <span class="text-xs font-semibold text-on-surface">{{ t('mustChangePasswordLabel') }}</span>
            </label>
          </div>

          <div class="flex justify-end gap-3 pt-3 border-t border-outline-variant/60">
            <button
              type="button"
              @click="closeUserModal"
              class="px-4 py-2 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold hover:bg-surface-bright transition-colors cursor-pointer"
            >
              {{ t('cancel') }}
            </button>
            <button
              type="submit"
              class="px-4 py-2 rounded bg-primary text-on-primary text-xs font-semibold shadow-glow hover:bg-primary-container transition-colors cursor-pointer"
            >
              {{ t('saveUser') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Password Reset -->
    <div v-if="isPasswordModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 w-full max-w-md shadow-2xl space-y-5 animate-fade-in">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <h3 class="font-bold text-lg text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">key</span>
            <span>{{ t('passwordResetTitle') }}</span>
          </h3>
          <button @click="isPasswordModalOpen = false" class="text-on-surface-variant hover:text-on-surface cursor-pointer">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <p class="text-xs text-on-surface-variant">
          {{ selectedUser?.name }} ({{ selectedUser?.username }}).
        </p>

        <form @submit.prevent="submitPasswordReset" class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">{{ t('newPassword') }}</label>
            <div class="flex gap-2">
              <input
                v-model="newPassword"
                type="text"
                required
                :placeholder="t('newPasswordPlaceholder')"
                class="flex-1 bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none font-mono"
              />
              <button
                type="button"
                @click="generateRandomPassword"
                class="px-3 py-2 rounded bg-surface-variant text-on-surface text-xs font-mono font-bold hover:bg-surface-bright cursor-pointer"
              >
                {{ t('generate') }}
              </button>
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-3 border-t border-outline-variant/60">
            <button
              type="button"
              @click="isPasswordModalOpen = false"
              class="px-4 py-2 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold hover:bg-surface-bright cursor-pointer"
            >
              {{ t('cancel') }}
            </button>
            <button
              type="submit"
              class="px-4 py-2 rounded bg-primary text-on-primary text-xs font-semibold shadow-glow hover:bg-primary-container cursor-pointer"
            >
              {{ t('updatePassword') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Delete Confirmation -->
    <div v-if="isDeleteModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div class="bg-surface-container-low border border-error/40 rounded-xl p-6 w-full max-w-md shadow-2xl space-y-5 animate-fade-in">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <h3 class="font-bold text-lg text-error flex items-center gap-2">
            <span class="material-symbols-outlined text-error">warning</span>
            <span>{{ t('deleteUserTitle') }}</span>
          </h3>
          <button @click="isDeleteModalOpen = false" class="text-on-surface-variant hover:text-on-surface cursor-pointer">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <p class="text-xs text-on-surface-variant">
          {{ selectedUser?.name }}
        </p>

        <div class="flex justify-end gap-3 pt-3 border-t border-outline-variant/60">
          <button
            @click="isDeleteModalOpen = false"
            class="px-4 py-2 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold hover:bg-surface-bright cursor-pointer"
          >
            {{ t('cancel') }}
          </button>
          <button
            @click="deleteSelectedUser"
            class="px-4 py-2 rounded bg-error text-on-error text-xs font-semibold hover:bg-error/80 shadow-glow cursor-pointer"
          >
            {{ t('confirmDelete') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useI18n } from '@/core/i18n'
import { apiFetchUsers, apiCreateUser, apiUpdateUser, apiDeleteUser, apiFetchRoles } from '@/core/api'

export interface UserItem {
  id: string
  name: string
  title: string
  email: string
  username: string
  uid: string
  role: string
  role_id: string
  avatar?: string
  isOnline: boolean
  isLocked: boolean
  mustChangePassword?: boolean
}

const { t, lang, getRoleTitle } = useI18n()

// Search & Pagination State
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(15)
const totalUsers = ref(0)
const isLoading = ref(false)
let searchTimeout: any = null

const users = ref<UserItem[]>([])
const rolesList = ref<Array<{ id: string; name: string }>>([])
const toastMessage = ref('')

const totalPages = computed(() => Math.ceil(totalUsers.value / pageSize.value) || 1)

async function loadData() {
  isLoading.value = true
  try {
    const [usersRes, rawRoles] = await Promise.all([
      apiFetchUsers({
        page: currentPage.value,
        page_size: pageSize.value,
        search: searchQuery.value.trim() || undefined,
      }),
      apiFetchRoles(),
    ])

    rolesList.value = rawRoles || []

    const rawItems = Array.isArray(usersRes) ? usersRes : (usersRes?.items || [])
    totalUsers.value = Array.isArray(usersRes) ? usersRes.length : (usersRes?.total || rawItems.length)

    users.value = rawItems.map((u: any) => ({
      id: u.id,
      name: u.full_name,
      title: u.title || '',
      email: u.email || '',
      username: u.username,
      uid: u.uid,
      role: u.role_name,
      role_id: u.role_id,
      avatar: u.avatar || undefined,
      isOnline: Boolean(u.is_online),
      isLocked: !u.is_active,
      mustChangePassword: !!u.must_change_password,
    }))
  } catch (err) {
    console.error('Failed to fetch users:', err)
  } finally {
    isLoading.value = false
  }
}

function handleSearch() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadData()
  }, 350)
}

function changePage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadData()
}

function getInitials(name: string) {
  if (!name) return 'OP'
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function showToast(msg: string) {
  toastMessage.value = msg
  setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
}

async function toggleLockUser(user: UserItem) {
  try {
    const newLockState = !user.isLocked
    await apiUpdateUser(user.id, { is_active: !newLockState })
    user.isLocked = newLockState
    showToast(user.isLocked ? `${user.name} ${t('userLockedToast')}` : `${user.name} ${t('userUnlockedToast')}`)
  } catch (err: any) {
    showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || t('statusChangeError')}`)
  }
}

// ── Modals State ──────────────────────────────────────────────────
const isUserModalOpen = ref(false)
const editingUserId = ref<string | null>(null)
const userForm = reactive({
  name: '',
  title: '',
  email: '',
  username: '',
  password: '',
  uid: '',
  role_id: '2',
  isLocked: false,
  mustChangePassword: true,
})

function openAddUserModal() {
  editingUserId.value = null
  userForm.name = ''
  userForm.title = ''
  userForm.email = ''
  userForm.username = ''
  userForm.password = ''
  userForm.uid = `UID-${Math.floor(100 + Math.random() * 900)}`
  userForm.role_id = rolesList.value[0]?.id || '2'
  userForm.isLocked = false
  userForm.mustChangePassword = true
  isUserModalOpen.value = true
}

function openEditUserModal(user: UserItem) {
  editingUserId.value = user.id
  userForm.name = user.name
  userForm.title = user.title
  userForm.email = user.email
  userForm.username = user.username
  userForm.password = ''
  userForm.uid = user.uid
  userForm.role_id = user.role_id
  userForm.isLocked = user.isLocked
  userForm.mustChangePassword = !!user.mustChangePassword
  isUserModalOpen.value = true
}

function closeUserModal() {
  isUserModalOpen.value = false
}

async function saveUser() {
  try {
    if (editingUserId.value) {
      await apiUpdateUser(editingUserId.value, {
        full_name: userForm.name,
        title: userForm.title,
        email: userForm.email,
        role_id: userForm.role_id,
        is_active: !userForm.isLocked,
        password: userForm.password || undefined,
        must_change_password: userForm.mustChangePassword,
      })
      showToast(`${userForm.name} ${t('userUpdatedSuccess')}`)
    } else {
      await apiCreateUser({
        username: userForm.username,
        password: userForm.password || 'password123',
        full_name: userForm.name,
        title: userForm.title,
        email: userForm.email,
        uid: userForm.uid,
        role_id: userForm.role_id,
        is_active: !userForm.isLocked,
        must_change_password: userForm.mustChangePassword,
      })
      showToast(`${userForm.name} ${t('userCreatedSuccess')}`)
    }
    await loadData()
    closeUserModal()
  } catch (err: any) {
    showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || t('userSaveError')}`)
  }
}

// Password Reset Modal
const isPasswordModalOpen = ref(false)
const selectedUser = ref<UserItem | null>(null)
const newPassword = ref('')

function openResetPasswordModal(user: UserItem) {
  selectedUser.value = user
  generateRandomPassword()
  isPasswordModalOpen.value = true
}

function generateRandomPassword() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$'
  let pwd = ''
  for (let i = 0; i < 12; i++) {
    pwd += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  newPassword.value = pwd
}

async function submitPasswordReset() {
  if (selectedUser.value) {
    try {
      await apiUpdateUser(selectedUser.value.id, { password: newPassword.value })
      showToast(`${selectedUser.value.username}: ${t('passwordResetSuccess')}`)
    } catch (err: any) {
      showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || t('passwordResetError')}`)
    }
  }
  isPasswordModalOpen.value = false
}

// Delete User Modal
const isDeleteModalOpen = ref(false)

function confirmDeleteUser(user: UserItem) {
  selectedUser.value = user
  isDeleteModalOpen.value = true
}

async function deleteSelectedUser() {
  if (selectedUser.value) {
    try {
      await apiDeleteUser(selectedUser.value.id)
      showToast(`${selectedUser.value.name} ${t('userDeletedSuccess')}`)
      await loadData()
    } catch (err: any) {
      showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || t('userDeleteError')}`)
    }
  }
  isDeleteModalOpen.value = false
}

onMounted(() => {
  loadData()
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
