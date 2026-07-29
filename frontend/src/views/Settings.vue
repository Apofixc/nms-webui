<template>
  <div class="min-h-full p-6 flex gap-6 w-full animate-fade-in text-on-surface">
    <!-- Reusable Secondary Settings Rail -->
    <SettingsRail />

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
        <button @click="saveSuccess = false" class="text-tertiary hover:opacity-75">
          <span class="material-symbols-outlined text-sm">close</span>
        </button>
      </div>

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

        <!-- Security Policies Card -->
        <div class="col-span-12 lg:col-span-8 bg-surface-container-low border border-outline-variant p-6 rounded-xl space-y-6 shadow-glow">
          <h3 class="font-semibold text-sm text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">policy</span>
            <span>{{ t('securityPolicies') }}</span>
          </h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="flex items-center justify-between p-4 bg-surface-container-highest rounded-lg border border-outline-variant/20 hover:border-outline-variant transition-colors group">
              <div class="max-w-[80%]">
                <p class="text-xs font-semibold text-on-surface">{{ t('mandatoryPassword') }}</p>
                <p class="text-[11px] text-on-surface-variant mt-1 leading-tight">{{ t('mandatoryPasswordDesc') }}</p>
              </div>
              <UiToggle v-model="mandatoryPasswordChange" />
            </div>

            <div class="bg-surface-container-highest p-4 rounded-lg border border-outline-variant/20 space-y-4">
              <h4 class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest">{{ t('rateLimitingLockout') }}</h4>
              <div class="space-y-3">
                <div class="flex items-center justify-between gap-4">
                  <label class="text-xs text-on-surface">{{ t('maxLoginAttempts') }}</label>
                  <input v-model="maxLoginAttempts" type="number" min="1" max="20" class="w-20 bg-surface-container-lowest text-on-surface font-mono text-xs font-bold py-1 px-2 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none" />
                </div>
                <div class="flex items-center justify-between gap-4">
                  <label class="text-xs text-on-surface">{{ t('lockoutDuration') }}</label>
                  <input v-model="lockoutDuration" type="number" min="1" max="1440" class="w-20 bg-surface-container-lowest text-on-surface font-mono text-xs font-bold py-1 px-2 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Audit Log Card -->
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
                  v-for="log in filteredLogs"
                  :key="log.id"
                  class="hover:bg-surface-variant/20 transition-colors"
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
                  <td class="px-6 py-3 max-w-xs truncate text-on-surface" :title="log.details || undefined">
                    {{ log.details || '-' }}
                  </td>
                  <td class="px-6 py-3 text-outline whitespace-nowrap">{{ log.ip_address || 'local' }}</td>
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
import { ref, computed, onMounted } from 'vue'
import SettingsRail from '@/components/layout/SettingsRail.vue'
import UiToggle from '@/components/common/UiToggle.vue'
import {
  apiFetchAuditLogs,
  apiExportAuditLogs,
  apiFetchSecuritySettings,
  apiSaveSecuritySettings,
} from '@/core/api'
import { useI18n } from '@/core/i18n'

const { t, lang } = useI18n()

// Security Settings State
const authEnabled = ref(true)
const mandatoryPasswordChange = ref(true)
const maxLoginAttempts = ref(5)
const lockoutDuration = ref(30)

const isSaving = ref(false)
const saveSuccess = ref(false)
const isExporting = ref(false)

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

function setCategory(cat: 'all' | 'errors' | 'auth' | 'user') {
  selectedFilterCategory.value = cat
  showFilterMenu.value = false
}

async function loadSecuritySettings() {
  try {
    const res = await apiFetchSecuritySettings()
    if (res) {
      authEnabled.value = res.auth_enabled ?? true
      mandatoryPasswordChange.value = res.mandatory_password_change ?? true
      maxLoginAttempts.value = Number(res.max_login_attempts ?? 5)
      lockoutDuration.value = Number(res.lockout_duration ?? 30)
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
    const res = await apiFetchAuditLogs(200, 0)
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
    result = result.filter((l) => l.action.includes('failed') || l.action.includes('delete'))
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

function formatTime(ts: string) {
  if (!ts) return ''
  return new Date(ts).toLocaleString(lang.value === 'ru' ? 'ru-RU' : 'en-US')
}

function formatActionLabel(action: string): string {
  const isEn = lang.value === 'en'
  const actionMap: Record<string, { ru: string; en: string }> = {
    'auth.login_success': { ru: 'Успешная авторизация', en: 'Login Success' },
    'auth.login_failed': { ru: 'Ошибка авторизации', en: 'Login Failed' },
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
  if (action.includes('failed') || action.includes('delete')) {
    return 'px-2 py-0.5 rounded text-[10px] font-bold bg-error/20 text-error border border-error/30'
  }
  if (action.includes('login_success') || action.includes('create')) {
    return 'px-2 py-0.5 rounded text-[10px] font-bold bg-tertiary/20 text-tertiary border border-tertiary/30'
  }
  return 'px-2 py-0.5 rounded text-[10px] font-bold bg-surface-variant text-on-surface-variant border border-outline-variant'
}

onMounted(() => {
  loadSecuritySettings()
  loadLogs()
})
</script>
