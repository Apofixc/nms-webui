<template>
  <div class="min-h-full p-6 flex flex-col gap-6 w-full animate-fade-in text-on-surface">
    <!-- Configuration Content Area -->
    <div class="flex-1 flex flex-col gap-6 w-full pb-12 min-w-0">
      <!-- Status Toast / Alert -->
      <div
        v-if="statusMessage"
        :class="[
          'px-4 py-3 rounded-xl flex items-center justify-between shadow-glow text-xs font-semibold animate-fade-in',
          statusType === 'success' ? 'bg-tertiary/15 border border-tertiary/40 text-tertiary' : 'bg-error/15 border border-error/40 text-error'
        ]"
      >
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-base">
            {{ statusType === 'success' ? 'check_circle' : 'error' }}
          </span>
          <span>{{ statusMessage }}</span>
        </div>
        <button @click="statusMessage = ''" class="hover:opacity-75">
          <span class="material-symbols-outlined text-sm">close</span>
        </button>
      </div>

      <!-- Page Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="font-bold text-2xl text-on-surface">{{ t('systemAdmin') }}</h1>
          <p class="text-xs text-on-surface-variant mt-1">{{ t('systemAdminSub') }}</p>
        </div>
      </div>

      <div class="grid grid-cols-12 gap-6">
        <!-- Backup & Restore Card -->
        <div class="col-span-12 lg:col-span-6 bg-surface-container-low border border-outline-variant p-6 rounded-xl shadow-glow space-y-4">
          <div class="flex items-center gap-2 border-b border-outline-variant/60 pb-3">
            <span class="material-symbols-outlined text-primary text-xl">backup</span>
            <h2 class="font-bold text-sm text-on-surface">{{ t('backupRestore') }}</h2>
          </div>

          <p class="text-xs text-on-surface-variant leading-relaxed">
            {{ t('backupDesc') }}
          </p>

          <div class="flex flex-wrap gap-3 pt-2">
            <button
              v-if="hasPermission('system.admin')"
              @click="downloadBackup"
              :disabled="isDownloading"
              class="bg-primary text-on-primary px-4 py-2 rounded text-xs font-semibold transition-colors shadow-glow hover:bg-primary-fixed flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <span v-if="isDownloading" class="material-symbols-outlined text-sm animate-spin">sync</span>
              <span v-else class="material-symbols-outlined text-sm">download</span>
              <span>{{ t('downloadBackup') }}</span>
            </button>

            <label
              v-if="hasPermission('system.admin')"
              class="bg-surface-container-high border border-outline-variant text-on-surface px-4 py-2 rounded text-xs font-semibold hover:bg-surface-bright transition-colors flex items-center gap-2 cursor-pointer"
            >
              <span class="material-symbols-outlined text-sm">upload_file</span>
              <span>{{ isRestoring ? 'Восстановление...' : t('restoreBackup') }}</span>
              <input type="file" accept=".db" class="hidden" @change="handleFileRestore" :disabled="isRestoring" />
            </label>
          </div>
        </div>

        <!-- Active Sessions & Security Card -->
        <div class="col-span-12 lg:col-span-6 bg-surface-container-low border border-outline-variant p-6 rounded-xl shadow-glow space-y-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3 mb-3">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-tertiary text-xl">devices</span>
                <h2 class="font-bold text-sm text-on-surface">{{ t('activeSessions') }}</h2>
              </div>
              <button
                v-if="hasPermission('system.admin')"
                @click="terminateAllSessions"
                :disabled="isTerminating"
                class="px-3 py-1 bg-error/20 text-error hover:bg-error/30 rounded border border-error/40 text-xs font-semibold transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
              >
                <span class="material-symbols-outlined text-sm">lock_reset</span>
                <span>{{ t('terminateAllSessions') }}</span>
              </button>
            </div>

            <div class="space-y-2 max-h-44 overflow-y-auto pr-1">
              <div
                v-for="session in sessions"
                :key="session.id"
                class="flex items-center justify-between p-2.5 bg-surface-container-highest rounded-lg border border-outline-variant/30 text-xs"
              >
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full" :class="session.is_active ? 'bg-tertiary' : 'bg-outline'" />
                  <span class="font-bold text-on-surface">{{ session.username }}</span>
                  <span class="text-[10px] font-mono text-on-surface-variant">({{ session.role_name }})</span>
                </div>
                <div class="text-[11px] text-outline font-mono">
                  {{ session.last_login || 'В сети' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- System Logs Viewer (Full Width) -->
        <div class="col-span-12 bg-surface-container-low border border-outline-variant p-6 rounded-xl shadow-glow space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-4 border-b border-outline-variant/60 pb-3">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-xl">terminal</span>
              <div>
                <h2 class="font-bold text-sm text-on-surface">{{ t('systemLogs') }}</h2>
                <p class="text-[11px] text-on-surface-variant">{{ t('systemLogsSub') }}</p>
              </div>
            </div>

            <!-- Filters & Controls -->
            <div class="flex flex-wrap items-center gap-3">
              <!-- Log File Selector -->
              <div class="flex items-center gap-1 text-xs">
                <span class="text-on-surface-variant font-medium">{{ t('logFile') }}:</span>
                <select
                  v-model="selectedLog"
                  @change="fetchLogs"
                  class="bg-surface-container-lowest text-on-surface font-mono text-xs py-1 px-2.5 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none"
                >
                  <option v-for="log in availableLogs" :key="log.name" :value="log.name">
                    {{ log.name }} ({{ formatSize(log.size_bytes) }})
                  </option>
                </select>
              </div>

              <!-- Log Level Selector -->
              <div class="flex items-center gap-1 text-xs">
                <span class="text-on-surface-variant font-medium">{{ t('logLevel') }}:</span>
                <select
                  v-model="selectedLevel"
                  @change="fetchLogs"
                  class="bg-surface-container-lowest text-on-surface font-mono text-xs py-1 px-2.5 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none"
                >
                  <option value="ALL">ALL</option>
                  <option value="ERROR">ERROR</option>
                  <option value="WARN">WARN</option>
                  <option value="INFO">INFO</option>
                </select>
              </div>

              <!-- Search Input -->
              <div class="relative">
                <input
                  v-model="searchQuery"
                  @input="fetchLogs"
                  type="text"
                  placeholder="Поиск в логах..."
                  class="bg-surface-container-lowest text-on-surface font-mono text-xs py-1 pl-7 pr-2.5 rounded border border-outline-variant focus:ring-1 focus:ring-primary outline-none w-36 sm:w-48"
                />
                <span class="material-symbols-outlined absolute left-2 top-1.5 text-xs text-outline pointer-events-none">search</span>
              </div>

              <!-- Auto-refresh Toggle -->
              <label class="flex items-center gap-1.5 text-xs text-on-surface-variant cursor-pointer select-none">
                <input type="checkbox" v-model="autoRefresh" class="accent-primary" />
                <span>{{ t('autoRefresh') }}</span>
              </label>

              <!-- Manual Refresh Button -->
              <button
                @click="fetchLogs"
                class="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors"
                title="Обновить"
              >
                <span class="material-symbols-outlined text-sm" :class="{ 'animate-spin': isFetchingLogs }">refresh</span>
              </button>
            </div>
          </div>

          <!-- Log Content Container (Terminal Window) -->
          <div class="relative">
            <div
              ref="terminalRef"
              class="h-96 bg-zinc-950 text-zinc-200 font-mono text-xs p-4 rounded-xl shadow-inner border border-outline-variant/40 overflow-y-auto space-y-1 select-text"
            >
              <div v-if="logLines.length === 0" class="text-zinc-500 italic py-8 text-center">
                Логи отсутствуют или не содержат совпадающих строк
              </div>

              <div
                v-for="(line, index) in logLines"
                :key="index"
                :class="getLineClass(line)"
                class="whitespace-pre-wrap break-all leading-relaxed"
              >
                {{ line }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from '@/core/i18n'
import { hasPermission } from '@/core/auth'
import {
  apiDownloadBackup,
  apiRestoreBackup,
  apiFetchLogList,
  apiFetchLogContent,
  apiFetchActiveSessions,
  apiTerminateAllSessions,
} from '@/core/api'

const { t } = useI18n()

// Status notification state
const statusMessage = ref('')
const statusType = ref<'success' | 'error'>('success')

// Backup & Restore State
const isDownloading = ref(false)
const isRestoring = ref(false)

// Session Management State
const sessions = ref<any[]>([])
const isTerminating = ref(false)

// Logs State
const availableLogs = ref<any[]>([])
const selectedLog = ref('backend.log')
const selectedLevel = ref('ALL')
const searchQuery = ref('')
const logLines = ref<string[]>([])
const isFetchingLogs = ref(false)
const autoRefresh = ref(false)
let refreshTimer: any = null

function showNotification(msg: string, type: 'success' | 'error' = 'success') {
  statusMessage.value = msg
  statusType.value = type
  setTimeout(() => {
    if (statusMessage.value === msg) statusMessage.value = ''
  }, 5000)
}

function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function getLineClass(line: string) {
  const l = line.toUpperCase()
  if (l.includes('ERROR') || l.includes('CRITICAL') || l.includes('EXCEPTION')) {
    return 'text-red-400 font-semibold bg-red-950/20 px-1 rounded'
  }
  if (l.includes('WARN') || l.includes('WARNING')) {
    return 'text-amber-300'
  }
  if (l.includes('INFO')) {
    return 'text-cyan-300'
  }
  if (l.includes('DEBUG')) {
    return 'text-zinc-500'
  }
  return 'text-zinc-300'
}

async function downloadBackup() {
  isDownloading.value = true
  try {
    const blob = await apiDownloadBackup()
    const url = window.URL.createObjectURL(new Blob([blob]))
    const a = document.createElement('a')
    a.href = url
    a.download = `nms-backup-${new Date().toISOString().slice(0, 10)}.db`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    a.remove()

    showNotification('Резервная копия успешно создана и скачана')
  } catch (err: any) {
    showNotification(err?.response?.data?.detail || err.message || 'Ошибка генерации бэкапа', 'error')
  } finally {
    isDownloading.value = false
  }
}

async function handleFileRestore(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  const file = input.files[0]
  if (!confirm(t('restoreConfirm'))) {
    input.value = ''
    return
  }

  isRestoring.value = true
  try {
    await apiRestoreBackup(file)

    showNotification('База данных успешно восстановлена. Обновите страницу.')
    setTimeout(() => window.location.reload(), 1500)
  } catch (err: any) {
    showNotification(err?.response?.data?.detail || err.message || 'Не удалось восстановить базу данных', 'error')
  } finally {
    isRestoring.value = false
    input.value = ''
  }
}

async function fetchSessions() {
  try {
    sessions.value = await apiFetchActiveSessions()
  } catch (e) {
    // ignore session fetch error
  }
}

async function terminateAllSessions() {
  if (!confirm(t('terminateAllConfirm'))) return

  isTerminating.value = true
  try {
    await apiTerminateAllSessions()
    showNotification('Все сторонние сессии успешно аннулированы')
    await fetchSessions()
  } catch (err: any) {
    showNotification(err?.response?.data?.detail || err.message || 'Ошибка завершения сессий', 'error')
  } finally {
    isTerminating.value = false
  }
}

async function fetchLogList() {
  try {
    availableLogs.value = await apiFetchLogList()
  } catch (e) {
    // ignore
  }
}

async function fetchLogs() {
  isFetchingLogs.value = true
  try {
    const data = await apiFetchLogContent(selectedLog.value, {
      lines: 200,
      level: selectedLevel.value,
      search: searchQuery.value,
    })
    logLines.value = data.content || []
  } catch (e) {
    // ignore log fetch error
  } finally {
    isFetchingLogs.value = false
  }
}

onMounted(async () => {
  await fetchLogList()
  await fetchLogs()
  await fetchSessions()

  refreshTimer = setInterval(() => {
    if (autoRefresh.value) {
      fetchLogs()
    }
  }, 3000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>
