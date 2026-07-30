<template>
  <div class="min-h-full p-6 flex flex-col gap-6 w-full animate-fade-in text-on-surface">
    <!-- Toast Notification -->
    <ToastNotification />

    <!-- Configuration Content Area -->
    <div class="flex-1 flex flex-col gap-6 w-full pb-12 min-w-0">

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
              <div v-if="hasPermission('system.admin')" class="flex items-center gap-2">
                <button
                  @click="terminateAllSessions(true)"
                  :disabled="isTerminating"
                  class="px-2.5 py-1 bg-tertiary/20 text-tertiary hover:bg-tertiary/30 rounded border border-tertiary/40 text-[11px] font-semibold transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
                  :title="lang === 'ru' ? 'Завершить сессии других пользователей' : 'Terminate other sessions'"
                >
                  <span class="material-symbols-outlined text-xs">shield_lock</span>
                  <span>{{ lang === 'ru' ? 'Завершить остальные' : 'Terminate Others' }}</span>
                </button>
                <button
                  @click="terminateAllSessions(false)"
                  :disabled="isTerminating"
                  class="px-2.5 py-1 bg-error/20 text-error hover:bg-error/30 rounded border border-error/40 text-[11px] font-semibold transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50"
                  :title="lang === 'ru' ? 'Завершить абсолютно все сессии' : 'Terminate all sessions'"
                >
                  <span class="material-symbols-outlined text-xs">lock_reset</span>
                  <span>{{ lang === 'ru' ? 'Все и выйти' : 'All & Logout' }}</span>
                </button>
              </div>
            </div>

            <div class="space-y-2 max-h-48 overflow-y-auto pr-1">
              <div v-if="sessions.length === 0" class="text-xs text-on-surface-variant py-4 text-center">
                {{ lang === 'ru' ? 'Нет активных сессий' : 'No active sessions' }}
              </div>
              <div
                v-for="session in sessions"
                :key="session.id"
                class="flex items-center justify-between p-2.5 bg-surface-container-highest rounded-lg border border-outline-variant/30 text-xs"
              >
                <div class="flex items-center gap-2 overflow-hidden">
                  <span class="w-2 h-2 rounded-full bg-tertiary flex-shrink-0" />
                  <span class="font-bold text-on-surface truncate">{{ session.username }}</span>
                  <span v-if="session.is_current" class="px-1 py-0.2 rounded bg-tertiary/20 text-tertiary text-[9px] font-bold border border-tertiary/30">
                    {{ lang === 'ru' ? 'Текущая' : 'Current' }}
                  </span>
                  <span class="text-[10px] font-mono text-on-surface-variant flex-shrink-0">({{ session.role_name }})</span>
                  <span class="text-[10px] text-outline font-mono truncate hidden sm:inline" :title="session.user_agent">
                    [{{ session.ip_address || 'local' }}]
                  </span>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0 ml-2">
                  <span class="text-[11px] text-outline font-mono">
                    {{ formatTime(session.last_seen) }}
                  </span>
                  <button
                    v-if="hasPermission('system.admin')"
                    @click="revokeSession(session)"
                    class="px-2 py-0.5 rounded bg-error/15 text-error border border-error/30 hover:bg-error/25 text-[10px] font-bold cursor-pointer transition-colors"
                  >
                    {{ lang === 'ru' ? 'Отозвать' : 'Revoke' }}
                  </button>
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
                  <option v-for="log in availableLogs" :key="log.id || log.name" :value="log.id || log.name">
                    [{{ log.category || 'system' }}] {{ log.name || log.id }} {{ log.size_bytes !== undefined ? '(' + formatSize(log.size_bytes) + ')' : '' }}
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
                  <option value="DEBUG">DEBUG</option>
                </select>
              </div>

              <!-- Search Input -->
              <div class="relative">
                <input
                  v-model="searchQuery"
                  @input="fetchLogs"
                  type="text"
                  :placeholder="t('searchLogsPlaceholder')"
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
                :title="t('refresh')"
              >
                <span class="material-symbols-outlined text-sm" :class="{ 'animate-spin': isFetchingLogs }">refresh</span>
              </button>

              <!-- Clear Screen Button -->
              <button
                @click="clearLogsView"
                class="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors"
                :title="t('clearLogsScreen')"
              >
                <span class="material-symbols-outlined text-sm">cleaning_services</span>
              </button>

              <!-- Add Remote Source Button -->
              <button
                @click="showAddRemoteModal = true"
                class="px-2 py-1 rounded bg-primary/10 text-primary hover:bg-primary/20 transition-colors text-xs flex items-center gap-1 font-medium"
                :title="t('addRemoteLogServer')"
              >
                <span class="material-symbols-outlined text-sm">add_link</span>
                <span>{{ t('remoteServer') }}</span>
              </button>

              <!-- Download Log Button -->
              <a
                :href="`/api/system/logs/${selectedLog}/download`"
                download
                class="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-colors"
                :title="t('downloadLogTooltip')"
              >
                <span class="material-symbols-outlined text-sm">download</span>
              </a>
            </div>
          </div>

          <!-- Log Content Container (Terminal Window) -->
          <div class="relative">
            <div
              ref="terminalRef"
              class="h-96 bg-zinc-950 text-zinc-200 font-mono text-xs p-4 rounded-xl shadow-inner border border-outline-variant/40 overflow-y-auto space-y-1 select-text"
            >
              <div v-if="logLines.length === 0" class="text-zinc-500 italic py-8 text-center">
                {{ t('logsEmptyOrNoMatch') }}
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

    <!-- Add Remote Log Source Modal -->
    <div v-if="showAddRemoteModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div class="bg-surface-container-low border border-outline-variant p-6 rounded-2xl max-w-md w-full shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <h3 class="font-bold text-sm text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary text-base">add_link</span>
            <span>{{ t('addRemoteLogServer') }}</span>
          </h3>
          <button @click="showAddRemoteModal = false" class="text-on-surface-variant hover:text-on-surface">
            <span class="material-symbols-outlined text-sm">close</span>
          </button>
        </div>

        <div class="space-y-3 font-mono text-xs">
          <div>
            <label class="block text-on-surface-variant mb-1 font-sans font-medium">{{ t('sourceName') }}</label>
            <input v-model="newRemoteName" type="text" :placeholder="t('sourceNamePlaceholder')" class="w-full bg-surface-container-lowest text-on-surface px-3 py-1.5 rounded border border-outline-variant outline-none focus:ring-1 focus:ring-primary" />
          </div>

          <div>
            <label class="block text-on-surface-variant mb-1 font-sans font-medium">{{ t('serverRestApiUrl') }}</label>
            <input v-model="newRemoteUrl" type="text" placeholder="http://192.168.1.50:9000/api/system/logs/backend.log" class="w-full bg-surface-container-lowest text-on-surface px-3 py-1.5 rounded border border-outline-variant outline-none focus:ring-1 focus:ring-primary" />
          </div>

          <div>
            <label class="block text-on-surface-variant mb-1 font-sans font-medium">{{ t('apiTokenOptional') }}</label>
            <input v-model="newRemoteToken" type="password" placeholder="Bearer token" class="w-full bg-surface-container-lowest text-on-surface px-3 py-1.5 rounded border border-outline-variant outline-none focus:ring-1 focus:ring-primary" />
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-outline-variant/60">
          <button @click="showAddRemoteModal = false" class="px-3 py-1.5 rounded text-xs text-on-surface-variant hover:bg-surface-variant">{{ t('cancel') }}</button>
          <button @click="submitAddRemoteSource" :disabled="isSubmittingRemote || !newRemoteName || !newRemoteUrl" class="px-4 py-1.5 rounded text-xs bg-primary text-on-primary font-medium hover:bg-primary/90 disabled:opacity-50">
            {{ isSubmittingRemote ? (lang === 'ru' ? 'Сохранение...' : 'Saving...') : t('saveButton') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/core/i18n'
import { hasPermission, clearAuthSession } from '@/core/auth'
import { useToast } from '@/composables/useToast'
import ToastNotification from '@/components/ToastNotification.vue'
import {
  apiDownloadBackup,
  apiRestoreBackup,
  apiFetchLogList,
  apiFetchLogContent,
  apiAddRemoteLogSource,
  apiDeleteRemoteLogSource,
  apiFetchActiveSessions,
  apiTerminateAllSessions,
  apiRevokeSession,
  apiRevokeMySession,
} from '@/core/api'

const router = useRouter()
const { t, lang } = useI18n()
const { showToast } = useToast()

// Status notification state
const statusMessage = ref('')
const statusType = ref<'success' | 'error'>('success')


// Remote Log Sources State
const showAddRemoteModal = ref(false)
const newRemoteName = ref('')
const newRemoteUrl = ref('')
const newRemoteToken = ref('')
const isSubmittingRemote = ref(false)

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

function formatTime(ts: string) {
  if (!ts) return t('online')
  let s = String(ts).trim()
  if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?$/.test(s)) {
    s = s.replace(' ', 'T') + 'Z'
  }
  try {
    return new Date(s).toLocaleTimeString(lang.value === 'ru' ? 'ru-RU' : 'en-US', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return new Date(s).toLocaleTimeString()
  }
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
  if (l.includes('ERROR') || l.includes('CRITICAL') || l.includes('EXCEPTION') || l.includes('TRACEBACK') || l.includes('FAILED')) {
    return 'text-red-400 font-semibold bg-red-950/30 px-1.5 py-0.5 rounded border-l-2 border-red-500'
  }
  if (l.includes('WARN') || l.includes('WARNING')) {
    return 'text-amber-300 font-medium'
  }
  if (l.includes('INFO') || l.includes('SUCCESS')) {
    return 'text-cyan-300'
  }
  if (l.includes('DEBUG')) {
    return 'text-zinc-500 font-mono'
  }
  if (/^\s+File "|\s+in \w+/.test(line)) {
    return 'text-rose-300/80 font-mono text-[11px] pl-4'
  }
  return 'text-zinc-300'
}

function clearLogsView() {
  logLines.value = []
  showToast(t('logsCleared'))
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

    showNotification(t('backupCreatedSuccess'))
  } catch (err: any) {
    showNotification(err?.response?.data?.detail || err.message || t('backupGenerateError'), 'error')
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

    showNotification(t('dbRestoredSuccess'))
    setTimeout(() => window.location.reload(), 1500)
  } catch (err: any) {
    showNotification(err?.response?.data?.detail || err.message || t('dbRestoreError'), 'error')
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

async function revokeSession(session: any) {
  const confirmMsg = `${t('confirmRevokeSessionUser')} ${session.username}?`
  if (!confirm(confirmMsg)) return

  try {
    if (session.is_current) {
      await apiRevokeMySession(session.id)
      clearAuthSession()
      router.push('/login')
      return
    }
    await apiRevokeSession(session.id)
    showNotification(t('sessionRevokedSuccess'))
    await fetchSessions()
  } catch (err: any) {
    showNotification(err?.response?.data?.detail || err.message || t('sessionRevokeError'), 'error')
  }
}

async function terminateAllSessions(keepCurrent = true) {
  const msg = keepCurrent
    ? t('confirmTerminateAllUserSessions')
    : t('confirmTerminateAllSessionsCurrent')

  if (!confirm(msg)) return

  isTerminating.value = true
  try {
    await apiTerminateAllSessions(keepCurrent)
    if (!keepCurrent) {
      clearAuthSession()
      router.push('/login')
      return
    }
    showNotification(t('allOtherSessionsTerminated'))
    await fetchSessions()
  } catch (err: any) {
    showNotification(err?.response?.data?.detail || err.message || t('terminateSessionsError'), 'error')
  } finally {
    isTerminating.value = false
  }
}

async function submitAddRemoteSource() {
  if (!newRemoteName.value || !newRemoteUrl.value) return
  isSubmittingRemote.value = true
  try {
    await apiAddRemoteLogSource({
      name: newRemoteName.value,
      url: newRemoteUrl.value,
      api_token: newRemoteToken.value || undefined,
    })
    showNotification(t('remoteServerAdded'))
    showAddRemoteModal.value = false
    newRemoteName.value = ''
    newRemoteUrl.value = ''
    newRemoteToken.value = ''
    await fetchLogList()
  } catch (err: any) {
    showNotification(err?.response?.data?.detail || err.message || t('remoteServerAddError'), 'error')
  } finally {
    isSubmittingRemote.value = false
  }
}

async function deleteRemoteSource(sourceId: string) {
  if (!confirm(t('confirmDeleteRemoteServer'))) return
  try {
    await apiDeleteRemoteLogSource(sourceId)
    showNotification(t('remoteServerDeleted'))
    await fetchLogList()
    selectedLog.value = 'backend.log'
    await fetchLogs()
  } catch (err: any) {
    showNotification(err?.response?.data?.detail || err.message || t('remoteServerDeleteError'), 'error')
  }
}

async function fetchLogList() {
  try {
    availableLogs.value = await apiFetchLogList()
  } catch (e) {
    // ignore
  }
}

let activeWebSocket: WebSocket | null = null

function connectWebSocketStream() {
  if (activeWebSocket) {
    activeWebSocket.close()
    activeWebSocket = null
  }
  if (!autoRefresh.value) return

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/system/logs/${selectedLog.value}/stream?level=${selectedLevel.value}&search=${encodeURIComponent(searchQuery.value)}`

  try {
    activeWebSocket = new WebSocket(wsUrl)
    activeWebSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data && Array.isArray(data.content)) {
          logLines.value = data.content
        }
      } catch (e) {
        // ignore parse error
      }
    }
    activeWebSocket.onerror = () => {
      // fallback to polling on error
    }
  } catch (e) {
    // fallback
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

watch([autoRefresh, selectedLog, selectedLevel], () => {
  connectWebSocketStream()
})

onMounted(async () => {
  await fetchLogList()
  await fetchLogs()
  await fetchSessions()

  refreshTimer = setInterval(() => {
    if (autoRefresh.value && (!activeWebSocket || activeWebSocket.readyState !== WebSocket.OPEN)) {
      fetchLogs()
    }
  }, 3000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (activeWebSocket) activeWebSocket.close()
})
</script>
