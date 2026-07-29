<template>
  <div class="min-h-full p-6 flex flex-col gap-6 w-full animate-fade-in text-on-surface">
    <!-- Configuration Content Area (Full Width) -->
    <div class="flex-1 flex flex-col gap-6 w-full pb-12 min-w-0">
      <!-- Success Toast / Banner -->
      <div
        v-if="saveSuccess"
        class="bg-tertiary/15 border border-tertiary/40 text-tertiary px-4 py-2.5 rounded-xl flex items-center justify-between shadow-glow text-xs font-semibold animate-fade-in"
      >
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-base text-tertiary">check_circle</span>
          <span>{{ lang === 'ru' ? 'Параметры безопасности успешно сохранены' : 'Security settings saved successfully' }}</span>
        </div>
        <button @click="saveSuccess = false" class="text-tertiary hover:opacity-75 cursor-pointer">
          <span class="material-symbols-outlined text-sm">close</span>
        </button>
      </div>

      <!-- Toast Notification for Roles/RBAC -->
      <Transition name="toast">
        <div v-if="toastMessage" class="fixed bottom-6 right-6 z-50 bg-tertiary-container border border-tertiary text-on-tertiary-container px-4 py-3 rounded-lg shadow-glow flex items-center gap-3">
          <span class="material-symbols-outlined text-[20px] text-tertiary">check_circle</span>
          <span class="text-xs font-semibold font-mono">{{ toastMessage }}</span>
        </div>
      </Transition>

      <div class="flex items-center justify-between">
        <div>
          <h1 class="font-bold text-2xl text-on-surface">{{ t('accessIdentity') }}</h1>
          <p class="text-xs text-on-surface-variant mt-1">{{ t('accessIdentitySub') }}</p>
        </div>
        <div class="flex items-center gap-3">
          <button
            @click="exportLogs"
            :disabled="isExporting"
            class="px-4 py-1.5 rounded border border-outline-variant text-on-surface hover:bg-surface-container-high transition-colors text-xs font-semibold flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <span class="material-symbols-outlined text-sm">download</span>
            <span>{{ isExporting ? (lang === 'ru' ? 'Экспорт...' : 'Exporting...') : t('exportLogs') }}</span>
          </button>
          <button
            @click="saveSettings"
            :disabled="isSaving"
            class="bg-primary text-on-primary px-4 py-1.5 rounded text-xs font-semibold transition-colors shadow-glow hover:bg-primary-fixed flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <span v-if="isSaving" class="material-symbols-outlined text-sm animate-spin">sync</span>
            <span v-else class="material-symbols-outlined text-sm">save</span>
            <span>{{ isSaving ? (lang === 'ru' ? 'Сохранение...' : 'Saving...') : t('applyChanges') }}</span>
          </button>
        </div>
      </div>

      <!-- ── SECTION 1: SECURITY POLICIES & AUTH ────────────────────────── -->
      <div class="grid grid-cols-12 gap-6">
        <!-- Global Auth Card -->
        <div class="col-span-12 lg:col-span-4 bg-surface-container-low border border-outline-variant p-6 rounded-xl shadow-glow flex flex-col justify-between relative overflow-hidden group">
          <div class="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-20 transition-opacity pointer-events-none">
            <span class="material-symbols-outlined text-6xl text-primary">security</span>
          </div>
          <div class="relative z-10">
            <h3 class="font-semibold text-sm text-on-surface flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">verified_user</span>
              <span>{{ t('globalAuth') }}</span>
            </h3>
            <p class="text-xs text-on-surface-variant mt-2 leading-relaxed">
              {{ t('globalAuthDesc') }}
            </p>
          </div>
          <div class="mt-8 flex items-center justify-between bg-surface-container-highest p-4 rounded-lg border border-outline-variant/30">
            <div class="flex flex-col">
              <span class="font-mono text-[10px] text-primary uppercase tracking-widest">auth_enabled</span>
              <span class="text-xs font-bold text-on-surface mt-1">{{ t('systemAuth') }}</span>
            </div>
            <UiToggle v-model="authEnabled" />
          </div>
        </div>

        <!-- Security Policies & Lifecycle Card -->
        <div class="col-span-12 lg:col-span-8 bg-surface-container-low border border-outline-variant p-6 rounded-xl space-y-6 shadow-glow">
          <h3 class="font-semibold text-sm text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">policy</span>
            <span>{{ t('securityPolicies') }}</span>
          </h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Password Policy -->
            <div class="flex items-center justify-between p-4 bg-surface-container-highest rounded-lg border border-outline-variant/20 hover:border-outline-variant transition-colors">
              <div class="max-w-[75%]">
                <p class="text-xs font-semibold text-on-surface">{{ t('mandatoryPassword') }}</p>
                <p class="text-[11px] text-on-surface-variant mt-1 leading-tight">{{ t('mandatoryPasswordDesc') }}</p>
              </div>
              <UiToggle v-model="mandatoryPasswordChange" />
            </div>

            <!-- MFA / 2FA Policy -->
            <div class="flex items-center justify-between p-4 bg-surface-container-highest rounded-lg border border-outline-variant/20 hover:border-outline-variant transition-colors">
              <div class="max-w-[75%]">
                <div class="flex items-center gap-2">
                  <p class="text-xs font-semibold text-on-surface">{{ lang === 'ru' ? 'Принудительная 2FA (MFA)' : 'Force 2FA (MFA)' }}</p>
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-tertiary/20 text-tertiary border border-tertiary/30">{{ lang === 'ru' ? 'Активно' : 'Active' }}</span>
                </div>
                <p class="text-[11px] text-on-surface-variant mt-1 leading-tight">{{ lang === 'ru' ? 'Требовать 2FA для всех пользователей' : 'Enforce multi-factor auth for all users' }}</p>
              </div>
              <UiToggle v-model="forceMfa" />
            </div>

            <!-- Rate Limiting & Lockout -->
            <div class="bg-surface-container-highest p-4 rounded-lg border border-outline-variant/20 space-y-3">
              <h4 class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest flex items-center gap-1">
                <span class="material-symbols-outlined text-xs text-primary">lock_reset</span>
                {{ t('rateLimitingLockout') }}
              </h4>
              <div class="space-y-2">
                <div class="flex items-center justify-between gap-4">
                  <label class="text-xs text-on-surface">{{ t('maxLoginAttempts') }}</label>
                  <input v-model="maxLoginAttempts" type="number" min="1" max="20" class="w-20 bg-surface-container-lowest text-on-surface font-mono text-xs font-bold py-1 px-2 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none" />
                </div>
                <div class="flex items-center justify-between gap-4">
                  <label class="text-xs text-on-surface">{{ t('lockoutDuration') }} ({{ lang === 'ru' ? 'мин' : 'mins' }})</label>
                  <input v-model="lockoutDuration" type="number" min="1" max="1440" class="w-20 bg-surface-container-lowest text-on-surface font-mono text-xs font-bold py-1 px-2 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none" />
                </div>
              </div>
            </div>

            <!-- Session Lifecycle -->
            <div class="bg-surface-container-highest p-4 rounded-lg border border-outline-variant/20 space-y-3">
              <h4 class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest flex items-center gap-1">
                <span class="material-symbols-outlined text-xs text-primary">schedule</span>
                {{ lang === 'ru' ? 'Жизненный цикл сессий' : 'Session Lifecycle' }}
              </h4>
              <div class="space-y-2">
                <div class="flex items-center justify-between gap-4">
                  <label class="text-xs text-on-surface">{{ lang === 'ru' ? 'Время жизни (TTL сессии)' : 'Session TTL' }} ({{ lang === 'ru' ? 'час' : 'hrs' }})</label>
                  <input v-model="sessionTtl" type="number" min="1" max="168" class="w-20 bg-surface-container-lowest text-on-surface font-mono text-xs font-bold py-1 px-2 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none" />
                </div>
                <div class="flex items-center justify-between gap-4">
                  <label class="text-xs text-on-surface">{{ lang === 'ru' ? 'Таймаут неактивности' : 'Inactivity Timeout' }} ({{ lang === 'ru' ? 'мин' : 'mins' }})</label>
                  <input v-model="inactivityTimeout" type="number" min="1" max="1440" class="w-20 bg-surface-container-lowest text-on-surface font-mono text-xs font-bold py-1 px-2 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none" />
                </div>
              </div>
            </div>

            <!-- Password Complexity Policy -->
            <div class="bg-surface-container-highest p-4 rounded-lg border border-outline-variant/20 space-y-3 md:col-span-2">
              <h4 class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest flex items-center gap-1">
                <span class="material-symbols-outlined text-xs text-primary">key</span>
                {{ lang === 'ru' ? 'Политика сложности паролей' : 'Password Complexity Policy' }}
              </h4>
              <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 items-center">
                <div class="flex items-center justify-between gap-2">
                  <label class="text-xs text-on-surface">{{ lang === 'ru' ? 'Мин. длина' : 'Min length' }}</label>
                  <input v-model="minPasswordLength" type="number" min="4" max="64" class="w-16 bg-surface-container-lowest text-on-surface font-mono text-xs font-bold py-1 px-2 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none" />
                </div>
                <label class="flex items-center gap-2 cursor-pointer text-xs text-on-surface">
                  <input v-model="requireUppercase" type="checkbox" class="rounded border-outline-variant text-primary focus:ring-primary" />
                  <span>{{ lang === 'ru' ? 'Заглавные (A-Z)' : 'Uppercase (A-Z)' }}</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer text-xs text-on-surface">
                  <input v-model="requireDigits" type="checkbox" class="rounded border-outline-variant text-primary focus:ring-primary" />
                  <span>{{ lang === 'ru' ? 'Цифры (0-9)' : 'Digits (0-9)' }}</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer text-xs text-on-surface">
                  <input v-model="requireSpecialChars" type="checkbox" class="rounded border-outline-variant text-primary focus:ring-primary" />
                  <span>{{ lang === 'ru' ? 'Спецсимволы (!@#$)' : 'Special (!@#$)' }}</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- ── SECTION 2: ROLES & PERMISSIONS (RBAC) ────────────────────────── -->
        <div class="col-span-12 bg-surface-container-low border border-outline-variant rounded-xl p-6 flex flex-col gap-6 shadow-glow">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="font-bold text-base text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">admin_panel_settings</span>
                <span>{{ t('rolesManagement') }}</span>
              </h3>
              <p class="text-xs text-on-surface-variant mt-1">{{ t('rolesMgmtSub') }}</p>
            </div>
            <button
              v-if="hasPermission('roles.manage')"
              @click="openAddRoleModal"
              class="bg-primary-container hover:bg-primary-fixed text-on-primary-container px-4 py-1.5 rounded text-sm font-semibold transition-colors flex items-center gap-2 shadow-[0_0_10px_rgba(34,211,238,0.2)] cursor-pointer"
            >
              <span class="material-symbols-outlined text-[18px]">add</span> {{ t('addNewRole') }}
            </button>
          </div>

          <!-- Roles Table -->
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
                    <span>{{ getRoleTitle(role.name) }}</span>
                  </td>
                  <td class="px-4 py-3 text-on-surface-variant text-xs">{{ getRoleDescription(role.name, role.description) }}</td>
                  <td class="px-4 py-3 font-mono text-on-surface text-xs">{{ role.usersCount }}</td>
                  <td class="px-4 py-3 text-right">
                    <div class="flex justify-end items-center space-x-2">
                      <button v-if="hasPermission('roles.manage')" @click="openEditRoleModal(role)" class="text-on-surface-variant hover:text-primary transition-colors p-1 cursor-pointer" :title="t('editTooltip')">
                        <span class="material-symbols-outlined text-[16px]">edit</span>
                      </button>
                      <button v-if="hasPermission('roles.manage') && !role.is_system && role.id !== '1'" @click="deleteRoleConfirm(role)" class="text-on-surface-variant hover:text-error transition-colors p-1 cursor-pointer" :title="t('deleteTooltip')">
                        <span class="material-symbols-outlined text-[16px]">delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Permissions Matrix -->
          <div class="mt-4 flex flex-col gap-3">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h4 class="font-bold text-sm text-on-surface flex items-center gap-2">
                  <span class="material-symbols-outlined text-primary text-lg">grid_view</span>
                  {{ t('permissionsMatrix') }}
                </h4>
                <p class="text-xs text-on-surface-variant mt-0.5">{{ t('permMatrixSub') }}</p>
              </div>
              <div class="relative w-64">
                <input
                  v-model="permSearchQuery"
                  type="text"
                  :placeholder="lang === 'ru' ? 'Поиск разрешений...' : 'Search permissions...'"
                  class="w-full bg-surface-container-highest border border-outline-variant text-on-surface rounded pl-8 pr-3 py-1.5 text-xs font-mono outline-none focus:border-primary"
                />
                <span class="material-symbols-outlined absolute left-2.5 top-2 text-on-surface-variant text-[16px]">search</span>
              </div>
            </div>

            <div class="border border-outline-variant rounded overflow-hidden bg-surface overflow-x-auto">
              <table class="w-full text-center text-sm whitespace-nowrap">
                <thead class="text-xs text-on-surface-variant bg-surface-container-lowest border-b border-outline-variant font-mono uppercase">
                  <tr>
                    <th class="px-4 py-3 font-medium text-left border-r border-outline-variant/50">{{ t('permission') }}</th>
                    <th v-for="r in roles" :key="r.id" class="px-4 py-3 font-medium border-r border-outline-variant/50">
                      {{ getRoleTitle(r.name) }}
                    </th>
                  </tr>
                </thead>
                <tbody v-for="(perms, category) in groupedPermissions" :key="category" class="divide-y divide-outline-variant/30 border-b border-outline-variant">
                  <!-- Category Header Row -->
                  <tr class="bg-surface-container-high/60 font-bold text-xs">
                    <td class="px-4 py-2 text-left text-primary font-mono flex items-center gap-2 border-r border-outline-variant/50">
                      <span class="material-symbols-outlined text-[16px]">{{ category.toLowerCase().includes('модуль') || category.toLowerCase().includes('module') ? 'extension' : 'shield' }}</span>
                      <span>{{ category }}</span>
                      <span class="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded font-normal">({{ perms.length }})</span>
                    </td>
                    <td v-for="r in roles" :key="r.id" class="px-4 py-1.5 border-r border-outline-variant/50 text-center">
                      <button
                        v-if="r.id !== '1'"
                        @click="toggleCategoryForRole(r, perms, !isCategoryAllSelected(r, perms))"
                        class="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-variant/80 hover:bg-primary/20 hover:text-primary transition-colors cursor-pointer"
                        :title="lang === 'ru' ? 'Переключить всю группу для роли' : 'Toggle group for role'"
                      >
                        {{ isCategoryAllSelected(r, perms) ? (lang === 'ru' ? 'Снять все' : 'Clear all') : (lang === 'ru' ? 'Выбрать все' : 'Select all') }}
                      </button>
                      <span v-else class="text-[10px] font-mono text-outline uppercase font-normal">ALL</span>
                    </td>
                  </tr>

                  <!-- Permission Items Rows -->
                  <tr v-for="perm in perms" :key="perm.id" class="hover:bg-surface-container-lowest transition-colors">
                    <td class="px-4 py-2.5 text-left font-mono text-xs text-on-surface-variant border-r border-outline-variant/50">
                      <div class="font-bold text-on-surface flex items-center gap-1.5">
                        <span>{{ perm.name || perm.id }}</span>
                        <span class="text-[10px] opacity-60 font-normal">({{ perm.id }})</span>
                      </div>
                      <div class="text-[10px] text-outline">{{ perm.description || perm.name }}</div>
                    </td>
                    <td v-for="r in roles" :key="r.id" class="px-4 py-2.5 border-r border-outline-variant/50">
                      <UiToggle
                        :modelValue="hasRolePerm(r, perm.id)"
                        :disabled="r.id === '1'"
                        @update:modelValue="val => toggleRolePerm(r, perm.id, val)"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- ── SECTION 3: AUDIT LOGS MONITOR ────────────────────────── -->
        <div class="col-span-12 bg-surface-container-low border border-outline-variant rounded-xl overflow-hidden flex flex-col shadow-glow">
          <div class="p-4 border-b border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <h3 class="font-bold text-sm text-on-surface">{{ t('securityAuditLog') }}</h3>
              <span class="bg-error-container/20 text-error text-[10px] px-2 py-0.5 rounded border border-error/20 font-bold uppercase tracking-tighter flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-error pulse-dot" /> {{ t('liveMonitor') }}
              </span>
            </div>
            <div class="flex items-center gap-3">
              <div class="relative w-48 sm:w-64">
                <span class="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">search</span>
                <input
                  v-model="searchQuery"
                  type="text"
                  :placeholder="t('auditSearchPlaceholder')"
                  class="w-full bg-surface-container-lowest border border-outline-variant rounded-lg pl-8 pr-3 py-1 text-xs text-on-surface font-mono placeholder:text-outline focus:border-primary focus:outline-none"
                />
              </div>

              <!-- Filter menu button -->
              <div class="relative">
                <button
                  @click="showFilterMenu = !showFilterMenu"
                  class="p-1.5 hover:bg-surface-variant rounded text-on-surface-variant transition-colors cursor-pointer flex items-center"
                  :class="selectedFilterCategory !== 'all' ? 'bg-primary/20 text-primary border border-primary/40' : ''"
                  :title="lang === 'ru' ? 'Фильтр событий' : 'Filter events'"
                >
                  <span class="material-symbols-outlined text-sm">filter_list</span>
                </button>

                <!-- Filter dropdown -->
                <div
                  v-if="showFilterMenu"
                  class="absolute right-0 mt-2 w-48 bg-surface-container-high border border-outline-variant rounded-lg shadow-xl py-1 z-20 text-xs font-mono"
                >
                  <button
                    @click="setCategory('all')"
                    class="w-full text-left px-3 py-1.5 hover:bg-surface-variant flex items-center justify-between"
                    :class="selectedFilterCategory === 'all' ? 'text-primary font-bold bg-surface-variant/40' : 'text-on-surface'"
                  >
                    <span>{{ lang === 'ru' ? 'Все события' : 'All events' }}</span>
                    <span v-if="selectedFilterCategory === 'all'" class="material-symbols-outlined text-xs">check</span>
                  </button>
                  <button
                    @click="setCategory('errors')"
                    class="w-full text-left px-3 py-1.5 hover:bg-surface-variant flex items-center justify-between"
                    :class="selectedFilterCategory === 'errors' ? 'text-error font-bold bg-surface-variant/40' : 'text-on-surface'"
                  >
                    <span>{{ lang === 'ru' ? 'Ошибки / Сбои' : 'Errors / Failures' }}</span>
                    <span v-if="selectedFilterCategory === 'errors'" class="material-symbols-outlined text-xs">check</span>
                  </button>
                  <button
                    @click="setCategory('auth')"
                    class="w-full text-left px-3 py-1.5 hover:bg-surface-variant flex items-center justify-between"
                    :class="selectedFilterCategory === 'auth' ? 'text-tertiary font-bold bg-surface-variant/40' : 'text-on-surface'"
                  >
                    <span>{{ lang === 'ru' ? 'Авторизация' : 'Authentication' }}</span>
                    <span v-if="selectedFilterCategory === 'auth'" class="material-symbols-outlined text-xs">check</span>
                  </button>
                  <button
                    @click="setCategory('user')"
                    class="w-full text-left px-3 py-1.5 hover:bg-surface-variant flex items-center justify-between"
                    :class="selectedFilterCategory === 'user' ? 'text-primary font-bold bg-surface-variant/40' : 'text-on-surface'"
                  >
                    <span>{{ lang === 'ru' ? 'Администрирование' : 'Management' }}</span>
                    <span v-if="selectedFilterCategory === 'user'" class="material-symbols-outlined text-xs">check</span>
                  </button>
                </div>
              </div>

              <button
                @click="loadLogs"
                class="p-1.5 hover:bg-surface-variant rounded text-on-surface-variant transition-colors cursor-pointer"
                :title="t('refresh')"
              >
                <span class="material-symbols-outlined text-sm">refresh</span>
              </button>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead class="bg-surface-container-highest border-b border-outline-variant/30">
                <tr class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest font-mono">
                  <th class="px-6 py-3"># ID</th>
                  <th class="px-6 py-3">{{ t('timestamp') }}</th>
                  <th class="px-6 py-3">{{ t('user') }}</th>
                  <th class="px-6 py-3">{{ t('action') }}</th>
                  <th class="px-6 py-3">{{ t('resource') }}</th>
                  <th class="px-6 py-3">{{ t('details') }}</th>
                  <th class="px-6 py-3">{{ t('ipAddress') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/10 font-mono text-xs">
                <tr v-if="isLoading" class="text-center">
                  <td colspan="7" class="py-8 text-on-surface-variant">{{ t('loadingAuditData') }}</td>
                </tr>
                <tr v-else-if="filteredLogs.length === 0" class="text-center">
                  <td colspan="7" class="py-8 text-on-surface-variant">{{ t('noEventsFound') }}</td>
                </tr>
                <tr
                  v-else
                  v-for="log in paginatedLogs"
                  :key="log.id"
                  @click="selectedLogForDetails = log"
                  class="hover:bg-surface-variant/30 transition-colors cursor-pointer group"
                >
                  <td class="px-6 py-3 text-outline font-semibold">#{{ log.id }}</td>
                  <td class="px-6 py-3 whitespace-nowrap text-on-surface-variant">{{ formatTime(log.timestamp) }}</td>
                  <td class="px-6 py-3 font-semibold text-primary">{{ log.username }}</td>
                  <td class="px-6 py-3">
                    <span :class="getActionBadgeClass(log.action)" :title="log.action">
                      {{ formatActionLabel(log.action) }}
                    </span>
                  </td>
                  <td class="px-6 py-3 text-on-surface-variant">{{ log.resource }}</td>
                  <td class="px-6 py-3 max-w-xs truncate text-on-surface flex items-center justify-between" :title="log.details || undefined">
                    <span class="truncate">{{ log.details || '-' }}</span>
                    <span class="material-symbols-outlined text-xs text-outline opacity-0 group-hover:opacity-100 transition-opacity ml-1">info</span>
                  </td>
                  <td class="px-6 py-3 text-outline whitespace-nowrap">{{ log.ip_address || 'local' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination Footer -->
          <div v-if="filteredLogs.length > 0" class="px-6 py-3 border-t border-outline-variant/30 flex items-center justify-between font-mono text-xs text-on-surface-variant bg-surface-container-highest/50">
            <span>{{ lang === 'ru' ? 'Всего записей' : 'Total events' }}: {{ filteredLogs.length }}</span>
            <div class="flex items-center gap-3">
              <span>{{ lang === 'ru' ? 'Страница' : 'Page' }} {{ currentPage }} {{ lang === 'ru' ? 'из' : 'of' }} {{ totalPages }}</span>
              <div class="flex gap-1">
                <button
                  @click="currentPage = Math.max(1, currentPage - 1)"
                  :disabled="currentPage === 1"
                  class="px-2 py-1 rounded border border-outline-variant hover:bg-surface-variant disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                >
                  &lt;
                </button>
                <button
                  @click="currentPage = Math.min(totalPages, currentPage + 1)"
                  :disabled="currentPage === totalPages"
                  class="px-2 py-1 rounded border border-outline-variant hover:bg-surface-variant disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                >
                  &gt;
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Add / Edit Role -->
    <div v-if="isRoleModalOpen" class="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 w-full max-w-md shadow-glow space-y-4">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <h3 class="font-bold text-base text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">shield</span>
            <span>{{ editingRole ? t('editRoleTitle') : t('addRoleTitle') }}</span>
          </h3>
          <button @click="isRoleModalOpen = false" class="text-on-surface-variant hover:text-on-surface cursor-pointer">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <form @submit.prevent="saveRole" class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">{{ t('roleNameLabel') }}</label>
            <input
              v-model="roleForm.name"
              type="text"
              required
              placeholder="Security Specialist"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none font-mono"
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1 font-mono">{{ t('descriptionLabel') }}</label>
            <textarea
              v-model="roleForm.description"
              required
              rows="2"
              :placeholder="t('roleDescPlaceholder')"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          </div>



          <div class="flex justify-end gap-3 pt-3 border-t border-outline-variant/60">
            <button
              type="button"
              @click="isRoleModalOpen = false"
              class="px-4 py-2 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold hover:bg-surface-bright cursor-pointer"
            >
              {{ t('cancel') }}
            </button>
            <button
              type="submit"
              class="px-4 py-2 rounded bg-primary text-on-primary text-xs font-semibold shadow-glow hover:bg-primary-container cursor-pointer"
            >
              {{ t('saveRole') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Audit Log Details -->
    <div v-if="selectedLogForDetails" class="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 w-full max-w-lg shadow-glow space-y-4 font-mono">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <h3 class="font-bold text-base text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">analytics</span>
            <span>{{ lang === 'ru' ? 'Детали события аудита' : 'Audit Event Details' }}</span>
          </h3>
          <button @click="selectedLogForDetails = null" class="text-on-surface-variant hover:text-on-surface cursor-pointer">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="space-y-3 text-xs">
          <div class="grid grid-cols-2 gap-3 bg-surface-container-highest p-3 rounded border border-outline-variant/30">
            <div>
              <span class="text-outline text-[10px] block uppercase font-bold">ID события</span>
              <span class="text-primary font-bold">#{{ selectedLogForDetails.id }}</span>
            </div>
            <div>
              <span class="text-outline text-[10px] block uppercase font-bold">Время</span>
              <span class="text-on-surface">{{ formatTime(selectedLogForDetails.timestamp) }}</span>
            </div>
            <div>
              <span class="text-outline text-[10px] block uppercase font-bold">Оператор</span>
              <span class="text-tertiary font-bold">{{ selectedLogForDetails.username }}</span>
            </div>
            <div>
              <span class="text-outline text-[10px] block uppercase font-bold">IP-адрес</span>
              <span class="text-on-surface-variant">{{ selectedLogForDetails.ip_address || 'local' }}</span>
            </div>
          </div>

          <div class="space-y-1">
            <span class="text-outline text-[10px] block uppercase font-bold">Действие</span>
            <div class="flex items-center gap-2">
              <span :class="getActionBadgeClass(selectedLogForDetails.action)">
                {{ formatActionLabel(selectedLogForDetails.action) }}
              </span>
              <span class="text-outline text-[11px]">({{ selectedLogForDetails.action }})</span>
            </div>
          </div>

          <div class="space-y-1">
            <span class="text-outline text-[10px] block uppercase font-bold">Ресурс</span>
            <div class="bg-surface-container-high p-2 rounded text-on-surface border border-outline-variant/30">
              {{ selectedLogForDetails.resource }}
            </div>
          </div>

          <div class="space-y-1">
            <span class="text-outline text-[10px] block uppercase font-bold">Контекст и детали</span>
            <div class="bg-surface-container-lowest p-3 rounded text-on-surface border border-outline-variant/40 max-h-40 overflow-y-auto font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
              {{ selectedLogForDetails.details || (lang === 'ru' ? 'Дополнительные сведения отсутствуют' : 'No additional details') }}
            </div>
          </div>
        </div>

        <div class="flex justify-end pt-2 border-t border-outline-variant/60">
          <button
            @click="selectedLogForDetails = null"
            class="px-4 py-1.5 rounded bg-surface-variant text-on-surface-variant text-xs font-semibold hover:bg-surface-bright cursor-pointer"
          >
            {{ lang === 'ru' ? 'Закрыть' : 'Close' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import UiToggle from '@/components/common/UiToggle.vue'
import {
  apiFetchAuditLogs,
  apiExportAuditLogs,
  apiFetchSecuritySettings,
  apiSaveSecuritySettings,
  apiFetchRoles,
  apiFetchPermissions,
  apiCreateRole,
  apiUpdateRole,
  apiDeleteRole,
} from '@/core/api'
import { useI18n } from '@/core/i18n'
import { hasPermission } from '@/core/auth'

const { t, lang, getRoleTitle, getRoleDescription } = useI18n()

// Selected log modal state
const selectedLogForDetails = ref<AuditLog | null>(null)

// Toast state
const toastMessage = ref('')
function showToast(msg: string) {
  toastMessage.value = msg
  setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
}

// Security Settings State
const authEnabled = ref(true)
const mandatoryPasswordChange = ref(true)
const maxLoginAttempts = ref(5)
const lockoutDuration = ref(30)
const sessionTtl = ref(12)
const inactivityTimeout = ref(30)
const forceMfa = ref(false)
const minPasswordLength = ref(8)
const requireUppercase = ref(false)
const requireDigits = ref(false)
const requireSpecialChars = ref(false)

const isSaving = ref(false)
const saveSuccess = ref(false)
const isExporting = ref(false)

// Roles & Permissions State
interface RoleItem {
  id: string
  name: string
  description: string
  usersCount: number
  is_system?: boolean
  permissions?: string[]
}

interface PermissionItem {
  id: string
  category: string
  name: string
  description: string
  module_id?: string
}

const roles = ref<RoleItem[]>([])
const permissionsList = ref<PermissionItem[]>([])
const permSearchQuery = ref('')

const groupedPermissions = computed(() => {
  const query = permSearchQuery.value.trim().toLowerCase()
  const groups: Record<string, PermissionItem[]> = {}

  for (const perm of permissionsList.value) {
    if (query) {
      const match = perm.id.toLowerCase().includes(query) ||
                    perm.name.toLowerCase().includes(query) ||
                    perm.category.toLowerCase().includes(query) ||
                    (perm.description || '').toLowerCase().includes(query)
      if (!match) continue
    }
    const cat = perm.category || (lang.value === 'ru' ? 'Система' : 'System')
    if (!groups[cat]) {
      groups[cat] = []
    }
    groups[cat].push(perm)
  }
  return groups
})

function isCategoryAllSelected(role: RoleItem, categoryPerms: PermissionItem[]): boolean {
  if (role.id === '1') return true
  const rolePerms = role.permissions || []
  return categoryPerms.every(p => rolePerms.includes(p.id))
}

async function toggleCategoryForRole(role: RoleItem, categoryPerms: PermissionItem[], enable: boolean) {
  if (role.id === '1') return
  const currentPerms = new Set(role.permissions || [])
  for (const p of categoryPerms) {
    if (enable) {
      currentPerms.add(p.id)
    } else {
      currentPerms.delete(p.id)
    }
  }
  const newPerms = Array.from(currentPerms)
  try {
    await apiUpdateRole(role.id, {
      name: role.name,
      description: role.description,
      permission_ids: newPerms,
    })
    role.permissions = newPerms
    showToast(lang.value === 'ru' ? 'Разрешения группы обновлены' : 'Group permissions updated')
  } catch (err: any) {
    showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || t('roleSaveError')}`)
  }
}

const isRoleModalOpen = ref(false)
const editingRole = ref<RoleItem | null>(null)
const roleForm = reactive({ name: '', description: '', permissions: [] as string[] })

async function loadRolesAndPermissions() {
  try {
    const [rolesData, permsData] = await Promise.all([apiFetchRoles(), apiFetchPermissions()])
    roles.value = (rolesData || []).map((r: any) => ({
      id: r.id,
      name: r.name,
      description: r.description,
      usersCount: r.users_count || 0,
      is_system: r.is_system,
      permissions: r.permissions || [],
    }))
    permissionsList.value = permsData || []
  } catch (err) {
    console.error('Failed to load roles and permissions:', err)
  }
}

function openAddRoleModal() {
  editingRole.value = null
  roleForm.name = ''
  roleForm.description = ''
  roleForm.permissions = ['audit.view']
  isRoleModalOpen.value = true
}

function openEditRoleModal(role: RoleItem) {
  editingRole.value = role
  roleForm.name = role.name
  roleForm.description = role.description
  roleForm.permissions = [...(role.permissions || [])]
  isRoleModalOpen.value = true
}

async function saveRole() {
  try {
    if (editingRole.value) {
      await apiUpdateRole(editingRole.value.id, {
        name: roleForm.name,
        description: roleForm.description,
        permission_ids: editingRole.value.permissions || [],
      })
      showToast(`"${roleForm.name}" ${t('roleUpdatedSuccess')}`)
    } else {
      await apiCreateRole({
        name: roleForm.name,
        description: roleForm.description,
        permission_ids: [],
      })
      showToast(`"${roleForm.name}" ${t('roleCreatedSuccess')}`)
    }
    await loadRolesAndPermissions()
    isRoleModalOpen.value = false
  } catch (err: any) {
    showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || t('roleSaveError')}`)
  }
}

async function deleteRoleConfirm(role: RoleItem) {
  if (confirm(lang.value === 'ru' ? `Удалить роль "${role.name}"?` : `Delete role "${role.name}"?`)) {
    try {
      await apiDeleteRole(role.id)
      showToast(lang.value === 'ru' ? `Роль "${role.name}" удалена` : `Role "${role.name}" deleted`)
      await loadRolesAndPermissions()
    } catch (err: any) {
      showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || 'Error deleting role'}`)
    }
  }
}

function hasRolePerm(role: RoleItem, permId: string): boolean {
  if (role.id === '1') return true // Superuser has all permissions
  return (role.permissions || []).includes(permId)
}

async function toggleRolePerm(role: RoleItem, permId: string, enabled: boolean) {
  if (role.id === '1') return // Protect Superuser
  const currentPerms = new Set(role.permissions || [])
  if (enabled) {
    currentPerms.add(permId)
  } else {
    currentPerms.delete(permId)
  }
  const newPerms = Array.from(currentPerms)
  try {
    await apiUpdateRole(role.id, {
      name: role.name,
      description: role.description,
      permission_ids: newPerms,
    })
    role.permissions = newPerms
    showToast(`${t('permUpdatedSuccess')}: ${permId}`)
  } catch (err: any) {
    showToast(`${t('errorPrefix')}: ${err?.response?.data?.detail || t('roleSaveError')}`)
  }
}

// Audit Log State
interface AuditLog {
  id: number
  timestamp: string
  user_id: string | null
  username: string
  action: string
  resource: string
  details: string | null
  ip_address: string | null
}

const logs = ref<AuditLog[]>([])
const isLoading = ref(false)
const searchQuery = ref('')
const selectedFilterCategory = ref<'all' | 'errors' | 'auth' | 'user'>('all')
const showFilterMenu = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
let pollTimer: any = null

function setCategory(cat: 'all' | 'errors' | 'auth' | 'user') {
  selectedFilterCategory.value = cat
  showFilterMenu.value = false
  currentPage.value = 1
}

async function loadSecuritySettings() {
  try {
    const res = await apiFetchSecuritySettings()
    if (res) {
      authEnabled.value = res.auth_enabled ?? true
      mandatoryPasswordChange.value = res.mandatory_password_change ?? true
      maxLoginAttempts.value = Number(res.max_login_attempts ?? 5)
      lockoutDuration.value = Number(res.lockout_duration ?? 30)
      sessionTtl.value = Number(res.session_ttl_hours ?? 12)
      inactivityTimeout.value = Number(res.inactivity_timeout_mins ?? 30)
      forceMfa.value = Boolean(res.force_mfa ?? false)
      minPasswordLength.value = Number(res.min_password_length ?? 8)
      requireUppercase.value = Boolean(res.require_uppercase ?? false)
      requireDigits.value = Boolean(res.require_digits ?? false)
      requireSpecialChars.value = Boolean(res.require_special_chars ?? false)
    }
  } catch (err) {
    console.error('Failed to load security settings:', err)
  }
}

async function saveSettings() {
  isSaving.value = true
  saveSuccess.value = false
  try {
    await apiSaveSecuritySettings({
      auth_enabled: authEnabled.value,
      mandatory_password_change: mandatoryPasswordChange.value,
      max_login_attempts: Number(maxLoginAttempts.value),
      lockout_duration: Number(lockoutDuration.value),
      session_ttl_hours: Number(sessionTtl.value),
      inactivity_timeout_mins: Number(inactivityTimeout.value),
      force_mfa: forceMfa.value,
      min_password_length: Number(minPasswordLength.value),
      require_uppercase: requireUppercase.value,
      require_digits: requireDigits.value,
      require_special_chars: requireSpecialChars.value,
    })
    saveSuccess.value = true
    setTimeout(() => {
      saveSuccess.value = false
    }, 4000)
  } catch (err) {
    console.error('Failed to save security settings:', err)
  } finally {
    isSaving.value = false
  }
}

async function exportLogs() {
  isExporting.value = true
  try {
    await apiExportAuditLogs()
  } catch (err) {
    console.error('Failed to export audit logs:', err)
  } finally {
    isExporting.value = false
  }
}

async function loadLogs() {
  isLoading.value = true
  try {
    const category = selectedFilterCategory.value !== 'all' ? selectedFilterCategory.value : undefined
    const search = searchQuery.value.trim() || undefined
    const res = await apiFetchAuditLogs(300, 0, category, search)
    logs.value = res.items || []
  } catch (err) {
    console.error('Failed to load audit logs:', err)
  } finally {
    isLoading.value = false
  }
}

const filteredLogs = computed(() => {
  let result = logs.value

  // Category filter
  if (selectedFilterCategory.value === 'errors') {
    result = result.filter((l) => l.action.includes('failed') || l.action.includes('delete') || l.action.includes('lockout'))
  } else if (selectedFilterCategory.value === 'auth') {
    result = result.filter((l) => l.action.startsWith('auth.'))
  } else if (selectedFilterCategory.value === 'user') {
    result = result.filter((l) => l.action.startsWith('user.') || l.action.startsWith('role.'))
  }

  // Search filter
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (l) =>
        l.username.toLowerCase().includes(q) ||
        l.action.toLowerCase().includes(q) ||
        l.resource.toLowerCase().includes(q) ||
        (l.details && l.details.toLowerCase().includes(q)) ||
        (l.ip_address && l.ip_address.toLowerCase().includes(q))
    )
  }

  return result
})

const totalPages = computed(() => Math.ceil(filteredLogs.value.length / pageSize.value) || 1)

const paginatedLogs = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredLogs.value.slice(start, start + pageSize.value)
})

function formatTime(ts: string) {
  if (!ts) return ''
  return new Date(ts).toLocaleString(lang.value === 'ru' ? 'ru-RU' : 'en-US')
}

function formatActionLabel(action: string): string {
  const isEn = lang.value === 'en'
  const actionMap: Record<string, { ru: string; en: string }> = {
    'auth.login_success': { ru: 'Успешная авторизация', en: 'Login Success' },
    'auth.login_failed': { ru: 'Ошибка авторизации', en: 'Login Failed' },
    'auth.login_lockout': { ru: 'Блокировка аккаунта', en: 'Account Lockout' },
    'auth.logout': { ru: 'Выход из системы', en: 'Logout' },
    'auth.terminate_all_sessions': { ru: 'Завершение сессий', en: 'Terminate Sessions' },
    'user.create': { ru: 'Создание пользователя', en: 'User Created' },
    'user.update': { ru: 'Обновление пользователя', en: 'User Updated' },
    'user.delete': { ru: 'Удаление пользователя', en: 'User Deleted' },
    'user.change_password': { ru: 'Смена пароля', en: 'Password Changed' },
    'user.update_profile': { ru: 'Обновление профиля', en: 'Profile Updated' },
    'role.create': { ru: 'Создание роли', en: 'Role Created' },
    'role.update': { ru: 'Обновление роли', en: 'Role Updated' },
    'system.security_settings_updated': { ru: 'Настройки безопасности', en: 'Security Settings Updated' },
    'system.disaster_recovery': { ru: 'Сброс доступа CLI', en: 'CLI Disaster Recovery' },
  }
  if (actionMap[action]) {
    return isEn ? actionMap[action].en : actionMap[action].ru
  }
  return action
}

function getActionBadgeClass(action: string) {
  if (action.includes('failed') || action.includes('delete') || action.includes('lockout')) {
    return 'px-2 py-0.5 rounded text-[10px] font-bold bg-error/20 text-error border border-error/30'
  }
  if (action.includes('login_success') || action.includes('create')) {
    return 'px-2 py-0.5 rounded text-[10px] font-bold bg-tertiary/20 text-tertiary border border-tertiary/30'
  }
  return 'px-2 py-0.5 rounded text-[10px] font-bold bg-surface-variant text-on-surface-variant border border-outline-variant'
}

onMounted(() => {
  loadSecuritySettings()
  loadRolesAndPermissions()
  loadLogs()
  pollTimer = setInterval(() => {
    loadLogs()
  }, 10000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
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
