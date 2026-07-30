<template>
  <div class="p-6 w-full flex flex-col gap-6 text-on-surface animate-fade-in relative">
    <!-- Toast Notification -->
    <ToastNotification />

    <!-- Action Bar -->
    <div class="flex justify-between items-center mb-2 flex-wrap gap-4">
      <div class="flex items-center space-x-3 flex-wrap gap-y-2">
        <!-- Search Input -->
        <div class="relative">
          <input
            v-model="searchQuery"
            @input="handleSearch"
            type="text"
            :placeholder="t('filterOperators')"
            class="bg-surface-container-highest border border-outline-variant text-on-surface rounded pl-10 pr-4 py-2 focus:border-primary focus:ring-1 focus:ring-primary text-sm w-72 font-mono placeholder:text-on-surface-variant outline-none"
          />
          <span class="material-symbols-outlined absolute left-3 top-2.5 text-on-surface-variant text-[20px] pointer-events-none">filter_list</span>
        </div>

        <!-- Status Filter -->
        <select
          v-model="statusFilter"
          class="bg-surface-container-highest border border-outline-variant text-on-surface rounded px-3 py-2 text-xs font-mono outline-none focus:border-primary cursor-pointer"
        >
          <option value="all">{{ t('filterStatusAll') }}</option>
          <option value="active">{{ t('filterStatusActive') }}</option>
          <option value="locked">{{ t('filterStatusLocked') }}</option>
          <option value="mfa">{{ t('filterStatusMfa') }}</option>
        </select>

        <span class="text-on-surface-variant text-xs font-mono">{{ t('showingOperators') }}: {{ filteredUsers.length }}</span>
      </div>

      <div class="flex items-center gap-2">
        <!-- Export Buttons -->
        <button
          @click="exportUsersCSV"
          class="bg-surface-container-high border border-outline-variant hover:bg-surface-bright text-on-surface px-3 py-2 rounded text-xs font-mono flex items-center gap-1.5 transition-colors cursor-pointer"
          :title="t('exportCSV')"
        >
          <span class="material-symbols-outlined text-[16px]">csv</span>
          <span>{{ t('exportCSV') }}</span>
        </button>
        <button
          @click="exportUsersJSON"
          class="bg-surface-container-high border border-outline-variant hover:bg-surface-bright text-on-surface px-3 py-2 rounded text-xs font-mono flex items-center gap-1.5 transition-colors cursor-pointer"
          :title="t('exportJSON')"
        >
          <span class="material-symbols-outlined text-[16px]">json</span>
          <span>{{ t('exportJSON') }}</span>
        </button>

        <button
          v-if="hasPermission('users.manage')"
          @click="openAddUserModal"
          class="bg-primary text-on-primary px-4 py-2 rounded font-semibold text-sm flex items-center shadow-glow hover:bg-primary-container transition-colors cursor-pointer ml-2"
        >
          <span class="material-symbols-outlined mr-2 text-[20px]">person_add</span>
          {{ t('addNewUser') }}
        </button>
      </div>
    </div>

    <!-- Bulk Action Bar -->
    <div v-if="selectedUserIds.length > 0" class="bg-surface-container-high border border-primary/40 p-3 rounded-lg flex items-center justify-between shadow-glow animate-fade-in font-mono text-xs">
      <div class="flex items-center gap-2 text-primary font-bold">
        <span class="material-symbols-outlined text-sm">checklist</span>
        <span>{{ t('selectedUsersCount') }}: {{ selectedUserIds.length }}</span>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="handleBulkAction('lock')"
          class="px-3 py-1.5 rounded bg-surface-variant hover:bg-surface-bright text-on-surface flex items-center gap-1 cursor-pointer"
        >
          <span class="material-symbols-outlined text-xs">lock</span>
          <span>{{ t('lockSelected') }}</span>
        </button>
        <button
          @click="handleBulkAction('unlock')"
          class="px-3 py-1.5 rounded bg-surface-variant hover:bg-surface-bright text-on-surface flex items-center gap-1 cursor-pointer"
        >
          <span class="material-symbols-outlined text-xs">lock_open</span>
          <span>{{ t('unlockSelected') }}</span>
        </button>
        <div class="flex items-center gap-1">
          <select
            v-model="bulkRoleId"
            class="bg-surface-container-lowest border border-outline-variant text-on-surface px-2 py-1.5 rounded text-xs outline-none"
          >
            <option value="">{{ t('selectRolePlaceholder') }}</option>
            <option v-for="r in rolesList" :key="r.id" :value="r.id">{{ getRoleTitle(r.name) }}</option>
          </select>
          <button
            @click="handleBulkAction('set_role')"
            :disabled="!bulkRoleId"
            class="px-3 py-1.5 rounded bg-primary text-on-primary font-bold flex items-center gap-1 cursor-pointer disabled:opacity-50"
          >
            <span>{{ t('applyRole') }}</span>
          </button>
        </div>
        <button
          @click="handleBulkAction('terminate_sessions')"
          class="px-3 py-1.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30 flex items-center gap-1 cursor-pointer"
        >
          <span class="material-symbols-outlined text-xs">logout</span>
          <span>{{ t('revokeSessionsSelected') }}</span>
        </button>
        <button
          @click="selectedUserIds = []; selectAll = false"
          class="p-1.5 text-on-surface-variant hover:text-on-surface cursor-pointer"
          :title="t('clearSelection')"
        >
          <span class="material-symbols-outlined text-sm">close</span>
        </button>
      </div>
    </div>

    <!-- Data Table -->
    <div class="bg-surface-container-low border border-outline-variant rounded-lg overflow-hidden w-full shadow-glow">
      <table class="w-full text-left border-collapse">
        <thead class="bg-surface-container border-b border-outline-variant text-on-surface-variant font-mono text-xs uppercase tracking-wider">
          <tr>
            <th class="px-3 py-3 w-8">
              <input type="checkbox" v-model="selectAll" @change="toggleSelectAll" class="rounded border-outline-variant bg-surface-container-high text-primary focus:ring-primary" />
            </th>
            <th class="px-4 py-3 font-semibold w-1/4">{{ t('user') }}</th>
            <th class="px-4 py-3 font-semibold w-1/4">{{ t('usernameId') }}</th>
            <th class="px-4 py-3 font-semibold w-1/6">{{ t('role') }}</th>
            <th class="px-4 py-3 font-semibold w-1/6">{{ t('status') }}</th>
            <th class="px-4 py-3 font-semibold text-right">{{ t('actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant">
          <tr v-if="isLoading" class="text-center">
            <td colspan="6" class="px-4 py-8 text-on-surface-variant font-mono text-sm">
              {{ t('loadingUserList') }}
            </td>
          </tr>
          <tr
            v-else
            v-for="user in filteredUsers"
            :key="user.id"
            class="hover:bg-surface-container-highest transition-colors group"
            :class="user.isLocked && 'opacity-60'"
          >
            <!-- Checkbox Cell -->
            <td class="px-3 py-3">
              <input type="checkbox" :value="user.id" v-model="selectedUserIds" class="rounded border-outline-variant bg-surface-container-high text-primary focus:ring-primary" />
            </td>

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
                  @click="openUserSessionsModal(user)"
                  class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors cursor-pointer"
                  :title="t('activeDevicesSessions')"
                >
                  <span class="material-symbols-outlined text-[20px]">devices</span>
                </button>
                <button
                  v-if="hasPermission('users.manage')"
                  @click="openEditUserModal(user)"
                  class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors cursor-pointer"
                  :title="t('editTooltip')"
                >
                  <span class="material-symbols-outlined text-[20px]">edit</span>
                </button>
                <button
                  v-if="hasPermission('users.manage')"
                  @click="toggleLockUser(user)"
                  class="p-1.5 text-on-surface-variant hover:text-amber-400 rounded hover:bg-surface-variant transition-colors cursor-pointer"
                  :title="user.isLocked ? t('unlock') : t('lock')"
                >
                  <span class="material-symbols-outlined text-[20px]">{{ user.isLocked ? 'lock_open' : 'lock' }}</span>
                </button>
                <button
                  v-if="hasPermission('users.manage')"
                  @click="openResetPasswordModal(user)"
                  class="p-1.5 text-on-surface-variant hover:text-primary rounded hover:bg-surface-variant transition-colors cursor-pointer"
                  :title="t('resetPasswordTooltip')"
                >
                  <span class="material-symbols-outlined text-[20px]">key</span>
                </button>
                <button
                  v-if="hasPermission('users.manage')"
                  @click="terminateUserSessions(user)"
                  class="p-1.5 text-on-surface-variant hover:text-amber-400 rounded hover:bg-surface-variant transition-colors cursor-pointer"
                  :title="t('terminateUserSessionsTooltip')"
                >
                  <span class="material-symbols-outlined text-[20px]">logout</span>
                </button>
                <button
                  v-if="hasPermission('users.manage')"
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
        <span>{{ t('showingUsersRange') }} {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, totalUsers) }} {{ t('of') }} {{ totalUsers }}</span>
        <div class="flex items-center gap-3">
          <span>{{ t('pageOf') }} {{ currentPage }} {{ t('of') }} {{ totalPages }}</span>
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
            <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">{{ t('passwordLabel') }}</label>
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

    <!-- Modal: User Active Sessions -->
    <div v-if="isUserSessionsModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 font-mono">
      <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 w-full max-w-lg shadow-2xl space-y-4 animate-fade-in">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <h3 class="font-bold text-base text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">devices</span>
            <span>{{ t('activeDevicesSessions') }}</span>
          </h3>
          <button @click="isUserSessionsModalOpen = false" class="text-on-surface-variant hover:text-on-surface cursor-pointer">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <p class="text-xs text-on-surface-variant">
          {{ selectedUser?.name }} ({{ selectedUser?.username }})
        </p>

        <div class="max-h-60 overflow-y-auto space-y-2">
          <div v-if="isUserSessionsLoading" class="text-center py-6 text-xs text-on-surface-variant">
            {{ t('loadingSessions') }}
          </div>
          <div v-else-if="userSessions.length === 0" class="text-center py-6 text-xs text-on-surface-variant">
            {{ t('noActiveSessionsFound') }}
          </div>
          <div
            v-else
            v-for="sess in userSessions"
            :key="sess.id"
            class="p-3 bg-surface-container-highest rounded border border-outline-variant/30 flex items-center justify-between text-xs"
          >
            <div class="space-y-0.5 max-w-[70%]">
              <div class="font-bold text-on-surface truncate" :title="sess.user_agent">{{ sess.user_agent || t('browserSession') }}</div>
              <div class="text-[10px] text-outline flex items-center gap-2">
                <span>IP: {{ sess.ip_address || 'local' }}</span>
                <span>• {{ t('active') }}: {{ formatTime(sess.last_seen) }}</span>
              </div>
            </div>
            <button
              @click="revokeUserSession(sess.id)"
              class="px-2.5 py-1 rounded bg-error/15 text-error border border-error/30 hover:bg-error/25 transition-colors text-[11px] font-bold cursor-pointer"
            >
              {{ t('revoke') }}
            </button>
          </div>
        </div>

        <div class="flex justify-end pt-3 border-t border-outline-variant/60">
          <button
            @click="isUserSessionsModalOpen = false"
            class="px-4 py-2 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold hover:bg-surface-bright cursor-pointer"
          >
            {{ t('cancel') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useI18n } from '@/core/i18n'
import { hasPermission } from '@/core/auth'
import { useToast } from '@/composables/useToast'
import ToastNotification from '@/components/ToastNotification.vue'

import {
  apiFetchUsers,
  apiCreateUser,
  apiUpdateUser,
  apiDeleteUser,
  apiFetchRoles,
  apiTerminateUserSessions,
  apiFetchUserSessions,
  apiRevokeSession,
  apiBulkUsersAction,
} from '@/core/api'

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
  mfa_enabled?: boolean
  mustChangePassword?: boolean
}

const { t, lang, getRoleTitle, translateApiError, formatDateTime } = useI18n()
const { showToast } = useToast()

// Status Filter & Export State
const statusFilter = ref<'all' | 'active' | 'locked' | 'mfa'>('all')

const filteredUsers = computed(() => {
  return users.value.filter((u) => {
    if (statusFilter.value === 'active') return !u.isLocked
    if (statusFilter.value === 'locked') return u.isLocked
    if (statusFilter.value === 'mfa') return Boolean(u.mfa_enabled)
    return true
  })
})

function exportUsersCSV() {
  const headers = ['ID', 'Username', 'Name', 'Title', 'Email', 'Role', 'Status', 'MFA']
  const rows = filteredUsers.value.map(u => [
    u.id,
    u.username,
    `"${(u.name || '').replace(/"/g, '""')}"`,
    `"${(u.title || '').replace(/"/g, '""')}"`,
    u.email || '',
    u.role,
    u.isLocked ? 'Locked' : 'Active',
    u.mfa_enabled ? 'Yes' : 'No'
  ])
  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `users_export_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
  showToast(`${t('exportCSV')}: OK`)
}

function exportUsersJSON() {
  const data = JSON.stringify(filteredUsers.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `users_export_${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  showToast(`${t('exportJSON')}: OK`)
}


// Bulk Action State
const selectedUserIds = ref<string[]>([])
const selectAll = ref(false)
const bulkRoleId = ref('')

function toggleSelectAll() {
  if (selectAll.value) {
    selectedUserIds.value = users.value.map((u) => u.id)
  } else {
    selectedUserIds.value = []
  }
}

async function handleBulkAction(action: string) {
  if (!selectedUserIds.value.length) return
  if (action === 'set_role' && !bulkRoleId.value) return
  try {
    const res = await apiBulkUsersAction(selectedUserIds.value, action, bulkRoleId.value || undefined)
    showToast(t('bulkActionSuccess', { count: res.count }))
    selectedUserIds.value = []
    selectAll.value = false
    bulkRoleId.value = ''
    await loadData()
  } catch (err: any) {
    showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || t('errorBulkAction')}`)
  }
}

// User Sessions Modal State
interface UserSessionItem {
  id: string
  ip_address: string
  user_agent: string
  created_at: string
  last_seen: string
}

const isUserSessionsModalOpen = ref(false)
const isUserSessionsLoading = ref(false)
const userSessions = ref<UserSessionItem[]>([])

async function openUserSessionsModal(user: UserItem) {
  selectedUser.value = user
  isUserSessionsModalOpen.value = true
  isUserSessionsLoading.value = true
  try {
    userSessions.value = await apiFetchUserSessions(user.id)
  } catch (err) {
    console.error('Failed to fetch user sessions:', err)
  } finally {
    isUserSessionsLoading.value = false
  }
}

async function revokeUserSession(sessionId: string) {
  try {
    await apiRevokeSession(sessionId)
    showToast(t('sessionRevoked'))
    if (selectedUser.value) {
      userSessions.value = await apiFetchUserSessions(selectedUser.value.id)
    }
    await loadData()
  } catch (err: any) {
    showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || t('errorRevokingSession')}`)
  }
}

function formatTime(ts: string) {
  if (!ts) return ''
  return formatDateTime(ts)
}

// Search & Pagination State
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(15)
const totalUsers = ref(0)
const isLoading = ref(false)
let searchTimeout: any = null

const users = ref<UserItem[]>([])
const rolesList = ref<Array<{ id: string; name: string }>>([])


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
      mfa_enabled: Boolean(u.mfa_enabled),
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

async function terminateUserSessions(user: UserItem) {
  try {
    await apiTerminateUserSessions(user.id)
    showToast(t('userSessionsTerminated', { name: user.name }))
  } catch (err: any) {
    showToast(`${t('errorPrefix')}: ${translateApiError(err, 'errorTerminatingSessions')}`)
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
    showToast(`${t('errorPrefix')}: ${translateApiError(err, 'userSaveError')}`)
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
      showToast(`${t('errorPrefix')}: ${translateApiError(err, 'passwordResetError')}`)
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
      showToast(`${t('errorPrefix')}: ${translateApiError(err, 'userDeleteError')}`)
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
