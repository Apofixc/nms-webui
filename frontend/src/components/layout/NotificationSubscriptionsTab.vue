<template>
  <div class="space-y-4">
    <!-- Header & Action Bar -->
    <div class="flex items-center justify-between">
      <div>
        <h4 class="text-xs font-bold text-on-surface">{{ t('subscriptionsTitle') }}</h4>
        <p class="text-[11px] text-on-surface-variant/70">
          {{ t('subscriptionsSubtitle') }}
        </p>
      </div>
      <button
        @click="openAddModal"
        class="px-3 py-1.5 rounded-xl bg-primary text-on-primary font-medium text-xs flex items-center gap-1 hover:bg-primary/90 transition-colors shadow-sm"
      >
        <span class="material-symbols-outlined text-sm">add</span>
        {{ t('addSubscription') }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="py-8 text-center text-xs text-on-surface-variant">
      {{ t('loadingSubscriptions') }}
    </div>

    <!-- Empty State -->
    <div
      v-else-if="subscriptions.length === 0"
      class="py-8 text-center border border-dashed border-outline-variant/60 rounded-xl p-6 text-on-surface-variant/70 space-y-2 bg-surface-variant/10"
    >
      <span class="material-symbols-outlined text-3xl opacity-40">notifications_active</span>
      <p class="text-xs font-medium">{{ t('noSubscriptions') }}</p>
      <p class="text-[11px] text-on-surface-variant/50">
        {{ t('noSubscriptionsDesc') }}
      </p>
    </div>

    <!-- Subscriptions List -->
    <div v-else class="space-y-3">
      <div
        v-for="sub in subscriptions"
        :key="sub.id"
        class="p-3.5 rounded-xl bg-surface-container-low border border-outline-variant/40 flex items-center justify-between gap-3 hover:border-outline-variant/80 transition-all"
      >
        <div class="flex items-center gap-3 min-w-0 flex-1">
          <!-- Icon depending on source type -->
          <div
            :class="[
              'w-9 h-9 rounded-xl flex items-center justify-center font-bold flex-shrink-0',
              sub.source_type === 'system'
                ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                : 'bg-primary/10 text-primary border border-primary/20'
            ]"
          >
            <span class="material-symbols-outlined text-xl">
              {{ sub.source_type === 'system' ? 'shield' : 'extension' }}
            </span>
          </div>

          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <h5 class="text-xs font-bold text-on-surface truncate">{{ sub.name }}</h5>

              <!-- Source Type Badge -->
              <span
                :class="[
                  'px-2 py-0.5 text-[10px] font-semibold rounded uppercase tracking-wider',
                  sub.source_type === 'system'
                    ? 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
                    : 'bg-primary/15 text-primary border border-primary/30'
                ]"
              >
                {{ sub.source_type === 'system' ? t('systemCore') : t('subModulePrefix', { id: sub.module_id }) }}
              </span>

              <!-- Severity Badge -->
              <span
                :class="[
                  'px-1.5 py-0.2 text-[10px] font-mono rounded uppercase',
                  getSeverityBadgeClass(sub.min_severity)
                ]"
              >
                ≥ {{ sub.min_severity }}
              </span>
            </div>

            <!-- Channels -->
            <div class="flex items-center gap-1.5 mt-1.5 flex-wrap">
              <span class="text-[11px] text-on-surface-variant/60">{{ t('targetChannels') }}:</span>
              <span
                v-for="ch in sub.channels"
                :key="ch"
                class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-surface-variant/40 text-on-surface border border-outline-variant/30 flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-[12px] opacity-70">{{ getChannelIcon(ch) }}</span>
                {{ getChannelLabel(ch) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Controls -->
        <div class="flex items-center gap-2 flex-shrink-0">
          <button
            @click="handleToggle(sub.id)"
            :title="sub.enabled ? t('deactivateSubscription') : t('activateSubscription')"
            :class="[
              'px-2.5 py-1 text-[11px] font-medium rounded-lg transition-colors flex items-center gap-1',
              sub.enabled
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25'
                : 'bg-surface-variant/40 text-on-surface-variant border border-outline-variant/30 hover:bg-surface-variant/60'
            ]"
          >
            <span class="material-symbols-outlined text-sm">{{ sub.enabled ? 'check_circle' : 'pause_circle' }}</span>
            {{ sub.enabled ? t('subActive') : t('subPause') }}
          </button>

          <button
            @click="openEditModal(sub)"
            class="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 transition-colors"
            :title="t('edit')"
          >
            <span class="material-symbols-outlined text-base">edit</span>
          </button>

          <button
            @click="handleDelete(sub.id)"
            class="p-1.5 rounded-lg text-error/80 hover:text-error hover:bg-error/10 transition-colors"
            :title="t('delete')"
          >
            <span class="material-symbols-outlined text-base">delete</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Create / Edit Modal -->
    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
        <div class="w-full max-w-lg bg-surface-container-high border border-outline-variant rounded-2xl shadow-2xl overflow-hidden flex flex-col text-on-surface">
          <!-- Modal Header -->
          <div class="p-4 border-b border-outline-variant flex items-center justify-between bg-surface-container-highest/60">
            <h4 class="font-bold text-sm text-on-surface">
              {{ isEditing ? t('editSubscription') : t('newSubscription') }}
            </h4>
            <button @click="showModal = false" class="p-1 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40">
              <span class="material-symbols-outlined text-lg">close</span>
            </button>
          </div>

          <!-- Modal Body -->
          <div class="p-4 space-y-4 max-h-[85vh] overflow-y-auto">
            <!-- Name -->
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant mb-1">{{ t('subscriptionName') }}</label>
              <input
                v-model="form.name"
                type="text"
                :placeholder="t('subscriptionNamePlaceholder')"
                class="w-full px-3 py-1.5 text-xs bg-surface-container-lowest border border-outline-variant rounded-xl focus:border-primary focus:outline-none text-on-surface"
              />
            </div>

            <!-- Source Type -->
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant mb-1">{{ t('eventSource') }}</label>
              <div class="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  @click="form.source_type = 'system'; form.module_id = 'system'"
                  :class="[
                    'p-2.5 rounded-xl border text-left flex items-center gap-2.5 transition-all text-xs',
                    form.source_type === 'system'
                      ? 'border-purple-500 bg-purple-500/10 text-purple-300 font-bold'
                      : 'border-outline-variant/40 bg-surface-container-lowest text-on-surface-variant hover:border-outline-variant'
                  ]"
                >
                  <span class="material-symbols-outlined text-lg text-purple-400">shield</span>
                  <div>
                    <div>{{ t('systemCore') }}</div>
                    <div class="text-[10px] font-normal text-on-surface-variant/60">{{ t('systemCoreDesc') }}</div>
                  </div>
                </button>

                <button
                  type="button"
                  @click="form.source_type = 'module'; form.module_id = '*'"
                  :class="[
                    'p-2.5 rounded-xl border text-left flex items-center gap-2.5 transition-all text-xs',
                    form.source_type === 'module'
                      ? 'border-primary bg-primary/10 text-primary font-bold'
                      : 'border-outline-variant/40 bg-surface-container-lowest text-on-surface-variant hover:border-outline-variant'
                  ]"
                >
                  <span class="material-symbols-outlined text-lg text-primary">extension</span>
                  <div>
                    <div>{{ t('modulePlugin') }}</div>
                    <div class="text-[10px] font-normal text-on-surface-variant/60">{{ t('modulePluginDesc') }}</div>
                  </div>
                </button>
              </div>
            </div>

            <!-- Module selection if source_type == 'module' -->
            <div v-if="form.source_type === 'module'">
              <label class="block text-xs font-semibold text-on-surface-variant mb-1">{{ t('selectModule') }}</label>
              <select
                v-model="form.module_id"
                class="w-full px-3 py-1.5 text-xs bg-surface-container-lowest border border-outline-variant rounded-xl focus:border-primary focus:outline-none text-on-surface"
              >
                <option value="*">{{ t('allModules') }}</option>
                <option
                  v-for="mod in sources.modules"
                  :key="mod.id"
                  :value="mod.id"
                >
                  {{ mod.name }} ({{ mod.id }})
                </option>
              </select>
            </div>

            <!-- Min Severity -->
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant mb-1">{{ t('minSeverity') }}</label>
              <select
                v-model="form.min_severity"
                class="w-full px-3 py-1.5 text-xs bg-surface-container-lowest border border-outline-variant rounded-xl focus:border-primary focus:outline-none text-on-surface uppercase"
              >
                <option value="info">{{ t('sevInfoAbove') }}</option>
                <option value="success">{{ t('sevSuccessAbove') }}</option>
                <option value="warning">{{ t('sevWarningAbove') }}</option>
                <option value="error">{{ t('sevErrorAbove') }}</option>
              </select>
            </div>

            <!-- Target Channels -->
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant mb-1.5">{{ t('targetChannels') }}</label>
              <div class="space-y-2">
                <label
                  v-for="ch in availableChannelsList"
                  :key="ch.id"
                  class="flex items-center gap-2.5 p-2 rounded-xl bg-surface-container-lowest border border-outline-variant/30 cursor-pointer hover:bg-surface-variant/20 transition-colors"
                >
                  <input
                    type="checkbox"
                    :value="ch.id"
                    v-model="form.channels"
                    class="rounded text-primary focus:ring-0 focus:outline-none"
                  />
                  <span class="material-symbols-outlined text-base text-on-surface-variant">{{ getChannelIcon(ch.id) }}</span>
                  <span class="text-xs text-on-surface font-medium">{{ getChannelName(ch.id) }}</span>
                </label>
              </div>
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="p-3 border-t border-outline-variant flex items-center justify-end gap-2 bg-surface-container-lowest">
            <button
              @click="showModal = false"
              class="px-3 py-1.5 rounded-xl border border-outline-variant text-xs text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40"
            >
              {{ t('cancel') }}
            </button>
            <button
              @click="handleSave"
              class="px-4 py-1.5 rounded-xl bg-primary text-on-primary text-xs font-bold hover:bg-primary/90 shadow-sm"
            >
              {{ t('save') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from '@/core/i18n'
import {
  apiFetchSubscriptionSources,
  apiFetchUserSubscriptions,
  apiCreateSubscription,
  apiUpdateSubscription,
  apiDeleteSubscription,
  apiToggleSubscription,
  type UserSubscription,
  type SubscribableSources
} from '@/core/subscriptions-api'

const { t } = useI18n()
const loading = ref(false)
const subscriptions = ref<UserSubscription[]>([])
const sources = ref<SubscribableSources>({
  system: { id: 'system', name: 'Ядро NMS', type: 'system' },
  modules: [],
  severities: [],
  available_channels: []
})

const availableChannelsList = computed(() => [
  { id: 'in_app', name: t('channelUi') },
  { id: 'telegram', name: t('channelTelegram') },
  { id: 'email', name: t('channelEmail') },
  { id: 'webhook', name: t('channelWebhook') },
  { id: 'syslog', name: t('channelSyslog') }
])

const showModal = ref(false)
const isEditing = ref(false)
const editingSubId = ref<string | null>(null)

const form = ref<Partial<UserSubscription>>({
  name: '',
  source_type: 'module',
  module_id: '*',
  min_severity: 'info',
  channels: ['in_app'],
  enabled: true
})

async function loadData() {
  loading.value = true
  try {
    const [subsRes, sourcesRes] = await Promise.all([
      apiFetchUserSubscriptions(),
      apiFetchSubscriptionSources()
    ])
    subscriptions.value = subsRes
    sources.value = sourcesRes
  } catch (err) {
    console.error('Failed to load subscriptions data:', err)
  } finally {
    loading.value = false
  }
}

function openAddModal() {
  isEditing.value = false
  editingSubId.value = null
  form.value = {
    name: '',
    source_type: 'module',
    module_id: '*',
    min_severity: 'info',
    channels: ['in_app'],
    enabled: true
  }
  showModal.value = true
}

function openEditModal(sub: UserSubscription) {
  isEditing.value = true
  editingSubId.value = sub.id
  form.value = {
    name: sub.name,
    source_type: sub.source_type,
    module_id: sub.module_id,
    min_severity: sub.min_severity,
    channels: [...sub.channels],
    enabled: sub.enabled
  }
  showModal.value = true
}

async function handleSave() {
  if (form.value.channels?.length === 0) {
    form.value.channels = ['in_app']
  }
  try {
    if (isEditing.value && editingSubId.value) {
      await apiUpdateSubscription(editingSubId.value, form.value)
    } else {
      await apiCreateSubscription(form.value)
    }
    showModal.value = false
    await loadData()
  } catch (err) {
    console.error('Failed to save subscription:', err)
  }
}

async function handleToggle(id: string) {
  try {
    await apiToggleSubscription(id)
    await loadData()
  } catch (err) {
    console.error('Failed to toggle subscription:', err)
  }
}

async function handleDelete(id: string) {
  try {
    await apiDeleteSubscription(id)
    await loadData()
  } catch (err) {
    console.error('Failed to delete subscription:', err)
  }
}

function getChannelIcon(ch: string) {
  switch (ch) {
    case 'in_app': return 'notifications'
    case 'telegram': return 'send'
    case 'email': return 'mail'
    case 'webhook': return 'webhook'
    case 'syslog': return 'terminal'
    default: return 'hub'
  }
}

function getChannelName(ch: string) {
  switch (ch) {
    case 'in_app': return t('channelUi')
    case 'telegram': return t('channelTelegram')
    case 'email': return t('channelEmail')
    case 'webhook': return t('channelWebhook')
    case 'syslog': return t('channelSyslog')
    default: return ch
  }
}

function getChannelLabel(ch: string) {
  switch (ch) {
    case 'in_app': return 'UI'
    case 'telegram': return 'Telegram'
    case 'email': return 'Email'
    case 'webhook': return 'Webhook'
    case 'syslog': return 'Syslog'
    default: return ch
  }
}

function getSeverityBadgeClass(sev: string) {
  switch (sev) {
    case 'error': return 'bg-error/20 text-error border border-error/30'
    case 'warning': return 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
    case 'success': return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
    default: return 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
  }
}

onMounted(() => {
  loadData()
})
</script>
