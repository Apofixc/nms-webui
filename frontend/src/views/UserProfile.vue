<template>
  <div class="p-6 w-full flex flex-col lg:flex-row gap-6 text-on-surface animate-fade-in relative">
    <!-- Toast Notification -->
    <Transition name="toast">
      <div
        v-if="toastMessage"
        class="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-glow flex items-center gap-3 border"
        :class="toastIsError ? 'bg-error-container border-error text-on-error-container' : 'bg-tertiary-container border-tertiary text-on-tertiary-container'"
      >
        <span class="material-symbols-outlined text-[20px]" :class="toastIsError ? 'text-error' : 'text-tertiary'">
          {{ toastIsError ? 'error' : 'check_circle' }}
        </span>
        <span class="text-xs font-semibold font-mono">{{ toastMessage }}</span>
      </div>
    </Transition>

    <!-- Left Column -->
    <div class="lg:w-1/3 flex flex-col gap-6">
      <!-- Avatar Card -->
      <div class="bg-surface-container-high border border-outline-variant rounded-lg p-6 shadow-glow backdrop-blur-sm flex flex-col items-center text-center">
        <div class="relative mb-4">
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="onFileSelected"
          />
          <div
            v-if="avatarUrl"
            class="w-32 h-32 rounded-full border-2 border-indigo-500 overflow-hidden shadow-glow flex items-center justify-center bg-surface-container-highest"
          >
            <img :src="avatarUrl" alt="Avatar" class="w-full h-full object-cover" />
          </div>
          <div
            v-else
            class="w-32 h-32 rounded-full border-2 border-indigo-500 bg-indigo-100 text-indigo-700 dark:bg-primary/20 dark:text-primary dark:border-primary flex items-center justify-center font-mono font-bold text-3xl shadow-glow uppercase select-none"
          >
            {{ initials }}
          </div>
          <div
            class="absolute bottom-0 right-0 w-4 h-4 rounded-full border-2 border-surface-container-high transition-colors"
            :class="!isSessionTerminated ? 'bg-emerald-500' : 'bg-rose-500'"
            :title="!isSessionTerminated ? t('active') : t('sessionTerminated')"
          />
        </div>

        <h2 class="font-bold text-lg text-on-surface mb-0.5">{{ fullName || username || '—' }}</h2>
        <p class="text-on-surface-variant font-semibold text-xs mb-1">{{ role || 'User' }}</p>
        <p class="text-on-surface-variant/70 font-mono text-[11px] mb-4">UID: {{ uid || '—' }}</p>

        <div class="w-full flex justify-between items-center bg-surface-container p-2.5 rounded mb-4 border border-outline-variant text-xs font-mono">
          <span class="text-on-surface-variant">{{ t('status') }}: 
            <span v-if="!isSessionTerminated" class="text-emerald-500 font-bold">{{ t('active') }}</span>
            <span v-else class="text-rose-500 font-bold">{{ t('sessionTerminated') }}</span>
          </span>
          <span class="text-on-surface-variant text-[11px]">{{ currentTime }}</span>
        </div>

        <div class="flex w-full gap-2 text-xs">
          <button
            @click="triggerUpload"
            class="flex-1 bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-300 dark:bg-secondary-container dark:text-on-surface dark:border-outline-variant py-2 px-3 rounded transition-colors font-semibold border flex items-center justify-center gap-1 cursor-pointer"
          >
            <span class="material-symbols-outlined text-[16px]">upload</span>
            {{ t('upload') }}
          </button>
          <button
            @click="handleResetAvatar"
            class="flex-1 bg-rose-50 text-rose-600 hover:bg-rose-100 border-rose-200 dark:bg-transparent dark:text-error dark:border-outline-variant py-2 px-3 rounded transition-colors font-semibold border flex items-center justify-center gap-1 cursor-pointer"
          >
            <span class="material-symbols-outlined text-[16px]">restart_alt</span>
            {{ t('reset') }}
          </button>
        </div>
      </div>

      <!-- Security Settings Card -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow">
        <h3 class="font-semibold text-sm text-on-surface mb-4 pb-2 border-b border-outline-variant flex items-center gap-2">
          <span class="material-symbols-outlined text-[18px]">security</span>
          <span>{{ t('securityPolicies') }}</span>
        </h3>

        <!-- Status / Error Banner -->
        <div
          v-if="statusMessage"
          class="mb-4 p-2.5 rounded text-xs font-mono flex items-center gap-2"
          :class="isError ? 'bg-error/15 text-error border border-error/30' : 'bg-tertiary/15 text-tertiary border border-tertiary/30'"
        >
          <span class="material-symbols-outlined text-[16px]">{{ isError ? 'warning' : 'check_circle' }}</span>
          <span>{{ statusMessage }}</span>
        </div>

        <form @submit.prevent="handleChangePassword" class="flex flex-col gap-4 text-xs">
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('currentPassword') }}</label>
            <input
              v-model="oldPassword"
              type="password"
              required
              class="bg-surface-container-highest text-on-surface font-mono px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('newPassword') }}</label>
            <input
              v-model="newPassword"
              type="password"
              required
              class="bg-surface-container-highest text-on-surface font-mono px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('confirmPassword') }}</label>
            <input
              v-model="confirmPassword"
              type="password"
              required
              class="bg-surface-container-highest text-on-surface font-mono px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
          </div>
          <button
            type="submit"
            class="bg-indigo-600 text-white hover:bg-indigo-700 border-transparent dark:bg-surface-variant dark:text-on-surface dark:border-outline-variant py-2 px-3 rounded transition-colors font-semibold border mt-2 cursor-pointer flex items-center justify-center gap-1 shadow-sm"
          >
            <span class="material-symbols-outlined text-[16px]">lock_reset</span>
            {{ t('changePassword') }}
          </button>
        </form>
      </div>
    </div>

    <!-- Right Column -->
    <div class="lg:w-2/3 flex flex-col gap-6">
      <!-- Personal Information -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow space-y-4">
        <h2 class="font-bold text-base text-on-surface pb-2 border-b border-outline-variant">{{ t('personalInfo') }}</h2>
        <form @submit.prevent="saveProfile" class="flex flex-col gap-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('fullName') }}</label>
              <input
                v-model="fullName"
                type="text"
                required
                class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">
                {{ t('department') }}
                <span class="text-on-surface-variant/50 lowercase text-[9px]">{{ t('readonlyField') }}</span>
              </label>
              <input
                v-model="department"
                type="text"
                readonly
                disabled
                class="bg-surface-container-highest/50 text-on-surface-variant font-mono text-xs px-3 py-2 rounded border border-outline-variant/60 cursor-not-allowed"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">
                {{ t('role') }}
                <span class="text-on-surface-variant/50 lowercase text-[9px]">{{ t('readonlyField') }}</span>
              </label>
              <input
                v-model="role"
                type="text"
                readonly
                disabled
                class="bg-surface-container-highest/50 text-on-surface-variant font-mono text-xs px-3 py-2 rounded border border-outline-variant/60 cursor-not-allowed"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('emailAddress') }}</label>
              <input
                v-model="email"
                type="email"
                class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
          </div>
          <div class="flex justify-end pt-2">
            <button
              type="submit"
              :disabled="isSaving"
              class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs px-6 py-2 rounded transition-colors shadow-glow cursor-pointer flex items-center gap-2 disabled:opacity-50"
            >
              <span v-if="isSaving" class="animate-spin material-symbols-outlined text-[16px]">progress_activity</span>
              <span v-else class="material-symbols-outlined text-[16px]">save</span>
              {{ t('saveChanges') }}
            </button>
          </div>
        </form>
      </div>

      <!-- Appearance & Regionality -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow space-y-4">
        <h2 class="font-bold text-base text-on-surface pb-2 border-b border-outline-variant">{{ t('appearanceRegionality') }}</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('theme') }}</label>
            <select
              v-model="selectedTheme"
              class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            >
              <option value="system">System</option>
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('language') }}</label>
            <select
              :value="lang"
              @change="onLangChange"
              class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            >
              <option value="ru">Русский (RU)</option>
              <option value="en">English (US)</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('timezone') }}</label>
            <select
              v-model="selectedTimezone"
              class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            >
              <option value="utc+3">UTC+3 (MSK)</option>
              <option value="utc">UTC</option>
              <option value="est">EST</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('tableDensity') }}</label>
            <select
              v-model="selectedDensity"
              class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            >
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
          <div>
            <h2 class="font-bold text-base text-on-surface">{{ t('activeSessions') }}</h2>
            <p class="text-on-surface-variant text-xs">{{ t('terminateSessionsSub') }}</p>
          </div>
          <button
            @click="handleTerminateSessions"
            class="bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs px-4 py-2 rounded transition-colors flex items-center gap-1 cursor-pointer shadow-glow"
          >
            <span class="material-symbols-outlined text-[16px]">logout</span>
            {{ t('terminateAllSessions') }}
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr class="border-b border-outline-variant text-on-surface-variant uppercase tracking-wider text-[11px]">
                <th class="py-2.5 px-3">{{ t('ipAddress') }}</th>
                <th class="py-2.5 px-3">{{ t('deviceBrowser') }}</th>
                <th class="py-2.5 px-3">{{ t('loginTime') }}</th>
                <th class="py-2.5 px-3">{{ t('status') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/50 text-on-surface">
              <tr class="hover:bg-surface-variant/30 transition-colors">
                <td class="py-2.5 px-3">{{ userIp }}</td>
                <td class="py-2.5 px-3">{{ userAgent }}</td>
                <td class="py-2.5 px-3">{{ t('today') }}, {{ loginTime }}</td>
                <td class="py-2.5 px-3">
                  <span v-if="!isSessionTerminated" class="text-emerald-500 font-bold flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 shadow-glow animate-pulse"></span>
                    {{ t('currentSessionActive') }}
                  </span>
                  <span v-else class="text-rose-500 font-bold flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-full bg-rose-500"></span>
                    {{ t('sessionTerminated') }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n, type Language } from '@/core/i18n'
import { getStoredUser, clearAuthSession, updateStoredUser } from '@/core/auth'
import { apiChangePassword, apiGetMe, apiLogout, apiTerminateSessions, apiUpdateMe } from '@/core/api'
import { applyTheme, applyDensity, applyTimezone, formatTimeWithTimezone } from '@/utils/theme'

const router = useRouter()
const { lang, setLanguage, t } = useI18n()

// Form & Profile State
const fullName = ref('')
const username = ref('')
const email = ref('')
const role = ref('')
const uid = ref('')
const avatarUrl = ref('')
const department = ref('Network Operations')

// Password State
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const statusMessage = ref('')
const isError = ref(false)

// UI Feedback
const isSaving = ref(false)
const toastMessage = ref('')
const toastIsError = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const isSessionTerminated = ref(false)

// Session info
const userIp = ref('127.0.0.1')
const userAgent = ref('Browser Session')
const loginTime = ref('14:32 UTC')
const currentTime = ref('14:32:11 UTC')

// Appearance settings
const selectedTheme = ref(localStorage.getItem('nms_theme') || 'dark')
const selectedTimezone = ref(localStorage.getItem('nms_timezone') || 'utc+3')
const selectedDensity = ref(localStorage.getItem('nms_density') || 'standard')

// Calculate Initials from Full Name or Username
const initials = computed(() => {
  const name = fullName.value.trim() || username.value.trim()
  if (!name) return 'US'
  const parts = name.split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
})

function showToast(msg: string, isErr = false) {
  toastMessage.value = msg
  toastIsError.value = isErr
  setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
}

function updateClock() {
  currentTime.value = formatTimeWithTimezone(new Date(), selectedTimezone.value)
}

async function loadProfile() {
  const localUser = getStoredUser()
  if (localUser) {
    fullName.value = localUser.full_name || ''
    username.value = localUser.username || ''
    email.value = localUser.email || ''
    role.value = localUser.role_name || ''
    uid.value = localUser.uid || ''
  }
  try {
    const me = await apiGetMe()
    if (me) {
      fullName.value = me.full_name || ''
      username.value = me.username || ''
      email.value = me.email || ''
      role.value = me.role_name || ''
      uid.value = me.uid || ''
      if (me.avatar) {
        avatarUrl.value = me.avatar
      }
    }
  } catch (err) {
    // fallback to local user
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

function onFileSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  const file = target.files[0]
  if (file.size > 2 * 1024 * 1024) {
    showToast('Размер файла не должен превышать 2 МБ', true)
    return
  }
  const reader = new FileReader()
  reader.onload = async (e) => {
    const result = e.target?.result as string
    avatarUrl.value = result
    try {
      await apiUpdateMe({ avatar: result })
      showToast('Аватар успешно обновлен')
    } catch {
      showToast('Ошибка при сохранении аватара', true)
    }
  }
  reader.readAsDataURL(file)
}

async function handleResetAvatar() {
  avatarUrl.value = ''
  try {
    await apiUpdateMe({ avatar: '' })
    showToast('Аватар сброшен к инициалам')
  } catch {
    showToast('Ошибка при сбросе аватара', true)
  }
}

async function saveProfile() {
  if (!fullName.value.trim()) {
    showToast('ФИО не может быть пустым', true)
    return
  }
  isSaving.value = true
  try {
    await apiUpdateMe({
      full_name: fullName.value.trim(),
      email: email.value.trim(),
    })
    updateStoredUser({
      full_name: fullName.value.trim(),
      email: email.value.trim(),
    })
    showToast('Данные профиля успешно сохранены')
  } catch (err: any) {
    showToast(err?.response?.data?.detail || 'Ошибка сохранения профиля', true)
  } finally {
    isSaving.value = false
  }
}

async function handleChangePassword() {
  statusMessage.value = ''
  if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
    statusMessage.value = 'Заполните все поля смены пароля'
    isError.value = true
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    statusMessage.value = 'Новый пароль и подтверждение не совпадают'
    isError.value = true
    return
  }
  if (newPassword.value.length < 4) {
    statusMessage.value = 'Пароль должен состоять минимум из 4 символов'
    isError.value = true
    return
  }
  try {
    await apiChangePassword(oldPassword.value, newPassword.value)
    statusMessage.value = 'Пароль успешно изменен'
    isError.value = false
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    showToast('Пароль успешно обновлен')
  } catch (err: any) {
    statusMessage.value = err?.response?.data?.detail || 'Не удалось изменить пароль'
    isError.value = true
  }
}

function onLangChange(e: Event) {
  const target = e.target as HTMLSelectElement
  setLanguage(target.value as Language)
}

async function handleTerminateSessions() {
  isSessionTerminated.value = true
  showToast('Завершение сессий на всех устройствах...')
  try {
    await apiTerminateSessions()
  } catch {
    await apiLogout().catch(() => {})
  }
  setTimeout(() => {
    clearAuthSession()
    router.push('/login')
  }, 1000)
}

// Detection for user agent
function detectSession() {
  const ua = navigator.userAgent
  let browser = 'Browser'
  if (ua.includes('Chrome')) browser = 'Chrome'
  else if (ua.includes('Firefox')) browser = 'Firefox'
  else if (ua.includes('Safari')) browser = 'Safari'

  let os = 'OS'
  if (ua.includes('Mac')) os = 'macOS'
  else if (ua.includes('Win')) os = 'Windows'
  else if (ua.includes('Linux')) os = 'Linux'

  userAgent.value = `${os} / ${browser}`
}

watch(selectedTheme, (val) => {
  applyTheme(val)
})

watch(selectedTimezone, (val) => {
  applyTimezone(val)
  updateClock()
})

watch(selectedDensity, (val) => {
  applyDensity(val)
})

onMounted(() => {
  loadProfile()
  detectSession()
  updateClock()
  setInterval(updateClock, 1000)
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
  transform: translateY(20px);
}
</style>
