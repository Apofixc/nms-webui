<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div class="w-full max-w-2xl bg-surface-container-high border border-outline-variant rounded-2xl shadow-2xl overflow-hidden flex flex-col text-on-surface max-h-[90vh] ring-1 ring-white/10">
        <!-- Modal Header -->
        <div class="p-4 border-b border-outline-variant flex items-center justify-between bg-surface-container-highest/60">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">hub</span>
            <h3 class="font-bold text-base text-on-surface">{{ t('notificationIntegrationsTitle') }}</h3>
          </div>
          <button @click="close" class="p-1 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40">
            <span class="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        <!-- Navigation Tabs -->
        <div class="flex border-b border-outline-variant/40 bg-surface-container-lowest/40 px-4 pt-2 gap-2 text-xs">
          <button
            @click="activeTab = 'channels'"
            :class="[
              'px-3 py-1.5 font-medium rounded-t-lg transition-colors border-b-2',
              activeTab === 'channels'
                ? 'border-primary text-primary bg-surface-container-high'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            ]"
          >
            {{ t('channelsTab') || 'Каналы рассылки' }}
          </button>
          <button
            @click="activeTab = 'logs'"
            :class="[
              'px-3 py-1.5 font-medium rounded-t-lg transition-colors border-b-2',
              activeTab === 'logs'
                ? 'border-primary text-primary bg-surface-container-high'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            ]"
          >
            {{ t('logsTab') || 'Журнал доставки' }}
          </button>
        </div>

        <!-- Content Body: Channels -->
        <div v-if="activeTab === 'channels'" class="p-4 overflow-y-auto space-y-4 flex-1">
          <!-- Action bar -->
          <div class="flex items-center justify-between">
            <p class="text-xs text-on-surface-variant">
              {{ t('notificationIntegrationsSubtitle') }}
            </p>
            <button
              @click="openAddModal"
              class="px-3 py-1.5 rounded-xl bg-primary text-on-primary font-medium text-xs flex items-center gap-1 hover:bg-primary/90 shadow-sm"
            >
              <span class="material-symbols-outlined text-sm">add</span>
              {{ t('addChannel') }}
            </button>
          </div>

          <!-- Integrations List -->
          <div v-if="loading" class="py-8 text-center text-xs text-on-surface-variant">
            {{ t('loadingConfigurations') }}
          </div>

          <div v-else-if="integrations.length === 0" class="py-8 text-center border border-dashed border-outline-variant rounded-xl p-6 text-on-surface-variant/60 space-y-2 bg-surface-variant/10">
            <span class="material-symbols-outlined text-3xl opacity-40">hub</span>
            <p class="text-xs font-medium">{{ t('channelsNotConfigured') }}</p>
            <p class="text-[11px] text-on-surface-variant/50">{{ t('addChannelDescription') }}</p>
          </div>

          <div v-else class="space-y-2.5">
            <div
              v-for="item in integrations"
              :key="item.id"
              class="p-3.5 rounded-xl bg-surface-container-low border border-outline-variant/40 flex items-center justify-between gap-3"
            >
              <div class="flex items-center gap-3 min-w-0">
                <div class="w-9 h-9 rounded-xl flex items-center justify-center bg-primary/10 text-primary font-bold">
                  <span class="material-symbols-outlined text-xl">{{ getProviderIcon(item.type) }}</span>
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <h4 class="text-xs font-bold text-on-surface truncate">{{ item.name }}</h4>
                    <span
                      :class="[
                        'px-1.5 py-0.2 text-[10px] font-semibold rounded uppercase',
                        item.enabled ? 'bg-tertiary/20 text-tertiary' : 'bg-outline/20 text-on-surface-variant/60'
                      ]"
                    >
                      {{ item.enabled ? t('active') : t('disabled') }}
                    </span>
                    <span class="px-1.5 py-0.2 text-[10px] rounded bg-primary/10 text-primary font-mono uppercase">
                      {{ item.type }}
                    </span>
                  </div>
                  <p class="text-[11px] text-on-surface-variant/70 mt-0.5">
                    {{ t('minLevel') }}: <strong class="uppercase text-on-surface">{{ item.min_type }}</strong>
                  </p>
                </div>
              </div>

              <div class="flex items-center gap-1.5 flex-shrink-0">
                <button
                  @click="handleTest(item)"
                  :disabled="testingId === item.id"
                  :title="t('sendTestNotification')"
                  class="px-2.5 py-1 rounded-lg border border-outline-variant/60 text-xs font-medium hover:bg-surface-variant/40 transition-colors flex items-center gap-1"
                >
                  <span class="material-symbols-outlined text-sm">{{ testingId === item.id ? 'sync' : 'send' }}</span>
                  {{ t('testButton') }}
                </button>
                <button
                  @click="handleDelete(item.id!)"
                  :title="t('delete')"
                  class="p-1 hover:text-error hover:bg-error/10 rounded-lg text-on-surface-variant transition-colors"
                >
                  <span class="material-symbols-outlined text-base">delete</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Channel Add Form -->
          <div v-if="showForm" class="p-4 rounded-xl border border-primary/30 bg-surface-container-highest/80 space-y-3">
            <h4 class="text-xs font-bold text-on-surface">
              {{ t('newIntegrationChannel') }}
            </h4>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label class="block text-on-surface-variant mb-1 font-medium">{{ t('channelNameLabel') }}</label>
                <input
                  v-model="form.name"
                  type="text"
                  :placeholder="t('telegramGroupPlaceholder')"
                  class="w-full px-3 py-1.5 rounded-lg !bg-surface-container-low border border-outline-variant !text-on-surface focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label class="block text-on-surface-variant mb-1 font-medium">{{ t('serviceTypeLabel') }}</label>
                <select
                  v-model="form.type"
                  class="w-full px-3 py-1.5 rounded-lg !bg-surface-container-low border border-outline-variant !text-on-surface focus:outline-none focus:border-primary"
                >
                  <option value="telegram">Telegram Bot</option>
                  <option value="discord">Discord Webhook</option>
                  <option value="viber">Viber Bot API</option>
                  <option value="email">Email (SMTP)</option>
                  <option value="webhook">Custom Webhook (JSON)</option>
                  <option value="syslog">Syslog Server (SIEM)</option>
                </select>
              </div>
            </div>

            <!-- Dynamic Config Inputs -->
            <div v-if="form.type === 'telegram'" class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label class="block text-on-surface-variant mb-1 font-medium">Bot Token</label>
                <input v-model="form.config.bot_token" type="password" placeholder="123456:ABC-DEF1234..." class="w-full px-3 py-1.5 rounded-lg !bg-surface-container-low border border-outline-variant !text-on-surface font-mono focus:outline-none focus:border-primary" />
              </div>
              <div>
                <label class="block text-on-surface-variant mb-1 font-medium">Chat ID / Channel</label>
                <input v-model="form.config.chat_id" type="text" placeholder="-100123456789..." class="w-full px-3 py-1.5 rounded-lg !bg-surface-container-low border border-outline-variant !text-on-surface font-mono focus:outline-none focus:border-primary" />
              </div>
            </div>

            <div v-if="form.type === 'discord'" class="text-xs">
              <label class="block text-on-surface-variant mb-1 font-medium">Discord Webhook URL</label>
              <input v-model="form.config.webhook_url" type="text" placeholder="https://discord.com/api/webhooks/..." class="w-full px-3 py-1.5 rounded-lg !bg-surface-container-low border border-outline-variant !text-on-surface font-mono focus:outline-none focus:border-primary" />
            </div>

            <div v-if="form.type === 'viber'" class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label class="block text-on-surface-variant mb-1 font-medium">Auth Token</label>
                <input v-model="form.config.auth_token" type="password" placeholder="4c8b..." class="w-full px-3 py-1.5 rounded-lg !bg-surface-container-low border border-outline-variant !text-on-surface font-mono focus:outline-none focus:border-primary" />
              </div>
              <div>
                <label class="block text-on-surface-variant mb-1 font-medium">Receiver User ID</label>
                <input v-model="form.config.receiver_id" type="text" placeholder="viber_user_id..." class="w-full px-3 py-1.5 rounded-lg !bg-surface-container-low border border-outline-variant !text-on-surface font-mono focus:outline-none focus:border-primary" />
              </div>
            </div>

            <div v-if="form.type === 'webhook'" class="text-xs">
              <label class="block text-on-surface-variant mb-1 font-medium">Webhook URL</label>
              <input v-model="form.config.webhook_url" type="text" placeholder="https://api.company.com/v1/alerts" class="w-full px-3 py-1.5 rounded-lg !bg-surface-container-low border border-outline-variant !text-on-surface font-mono focus:outline-none focus:border-primary" />
            </div>

            <div class="flex items-center justify-end gap-2 pt-2">
              <button @click="showForm = false" class="px-3 py-1.5 rounded-xl text-xs text-on-surface-variant hover:bg-surface-variant/40">
                {{ t('cancel') }}
              </button>
              <button @click="handleSave" class="px-4 py-1.5 rounded-xl bg-primary text-on-primary font-medium text-xs hover:bg-primary/90">
                {{ t('saveChannel') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Content Body: Delivery Logs -->
        <div v-else-if="activeTab === 'logs'" class="p-4 overflow-y-auto space-y-3 flex-1">
          <div v-if="loadingLogs" class="py-8 text-center text-xs text-on-surface-variant">
            {{ t('loadingLogs') || 'Загрузка журнала...' }}
          </div>
          <div v-else-if="logs.length === 0" class="py-8 text-center text-xs text-on-surface-variant/60">
            {{ t('emptyLogs') || 'История отправки пуста' }}
          </div>
          <div v-else class="space-y-2 text-xs">
            <div
              v-for="log in logs"
              :key="log.id"
              class="p-2.5 rounded-xl bg-surface-container-low border border-outline-variant/30 flex items-center justify-between gap-2"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span
                    :class="[
                      'w-2 h-2 rounded-full',
                      log.success ? 'bg-emerald-400' : 'bg-rose-400'
                    ]"
                  />
                  <span class="font-bold text-on-surface truncate">{{ log.title }}</span>
                  <span class="px-1.5 py-0.2 text-[9px] rounded uppercase font-mono bg-surface-variant text-on-surface-variant">
                    {{ log.channel_type }}
                  </span>
                </div>
                <p class="text-[11px] text-on-surface-variant mt-0.5 line-clamp-1">
                  {{ log.message }}
                </p>
                <p v-if="log.error_message" class="text-[10px] text-rose-400 mt-0.5">
                  Ошибка: {{ log.error_message }}
                </p>
              </div>
              <div class="text-[10px] font-mono text-on-surface-variant/60 flex-shrink-0">
                {{ log.created_at }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from '@/core/i18n'
import {
  apiFetchAlertChannels,
  apiCreateAlertChannel,
  apiDeleteAlertChannel,
  apiTestAlertChannel,
  apiFetchAlertLog,
  type AlertChannel,
  type AlertLogEntry
} from '@/core/alerting-api'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits(['close'])
const { t } = useI18n()

const activeTab = ref<'channels' | 'logs'>('channels')
const loading = ref(false)
const loadingLogs = ref(false)
const testingId = ref<string | null>(null)
const integrations = ref<AlertChannel[]>([])
const logs = ref<AlertLogEntry[]>([])
const showForm = ref(false)

const form = ref<AlertChannel>({
  name: '',
  type: 'telegram',
  enabled: true,
  min_type: 'warning',
  categories: '*',
  config: {}
})

function close() {
  emit('close')
}

function getProviderIcon(type: string) {
  switch (type) {
    case 'telegram': return 'send'
    case 'discord': return 'chat'
    case 'viber': return 'phone_iphone'
    case 'email': return 'mail'
    case 'syslog': return 'terminal'
    default: return 'webhook'
  }
}

async function loadIntegrations() {
  loading.value = true
  try {
    integrations.value = await apiFetchAlertChannels()
  } catch (err) {
    // Fail silently
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  loadingLogs.value = true
  try {
    logs.value = await apiFetchAlertLog()
  } catch (err) {
    // Fail silently
  } finally {
    loadingLogs.value = false
  }
}

function openAddModal() {
  form.value = {
    name: '',
    type: 'telegram',
    enabled: true,
    min_type: 'warning',
    categories: '*',
    config: {}
  }
  showForm.value = true
}

async function handleSave() {
  if (!form.value.name.trim()) return
  try {
    await apiCreateAlertChannel(form.value)
    showForm.value = false
    loadIntegrations()
  } catch {}
}

async function handleDelete(id: string) {
  try {
    await apiDeleteAlertChannel(id)
    loadIntegrations()
  } catch {}
}

async function handleTest(item: AlertChannel) {
  if (!item.id) return
  testingId.value = item.id
  try {
    const res = await apiTestAlertChannel(item.id)
    if (res.success) {
      alert(t('testNotificationSuccess', { name: item.name }))
    } else {
      alert(t('testNotificationFailed', { name: item.name }))
    }
  } catch {
    alert(t('testNotificationError'))
  } finally {
    testingId.value = null
  }
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    loadIntegrations()
    loadLogs()
  }
})

watch(activeTab, (tab) => {
  if (tab === 'logs') {
    loadLogs()
  }
})
</script>
