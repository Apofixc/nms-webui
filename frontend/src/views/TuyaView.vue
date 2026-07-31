<template>
  <div class="min-h-full p-6 flex flex-col gap-6 w-full animate-fade-in text-on-surface">
    <!-- Заголовок страницы и действия -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="font-bold text-2xl text-on-surface flex items-center gap-3">
          <span class="material-symbols-outlined text-primary text-2xl">cpu</span>
          Устройства Tuya
        </h1>
        <p class="text-xs text-on-surface-variant mt-1">
          Управление умными устройствами Tuya в локальном (LAN) и облачном (Cloud OpenAPI) режимах
        </p>
      </div>

      <div class="flex items-center gap-3">
        <button
          @click="loadData"
          :disabled="loading"
          class="bg-surface-container-high hover:bg-surface-variant text-on-surface border border-outline-variant px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition-colors"
        >
          <span class="material-symbols-outlined text-sm" :class="{ 'animate-spin': loading }">refresh</span>
          Обновить
        </button>

        <button
          @click="syncCloud"
          :disabled="syncing"
          class="bg-surface-container-high hover:bg-surface-variant text-on-surface border border-outline-variant px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition-colors"
        >
          <span class="material-symbols-outlined text-sm text-tertiary" :class="{ 'animate-spin': syncing }">cloud_sync</span>
          Синхронизация
        </button>

        <router-link
          to="/settings/modules"
          class="bg-surface-container-high hover:bg-surface-variant text-on-surface border border-outline-variant px-3 py-1.5 rounded text-xs font-semibold flex items-center gap-1.5 transition-colors"
          title="Настройка Client ID, Client Secret и региона"
        >
          <span class="material-symbols-outlined text-sm text-primary">settings</span>
          Настройки Cloud
        </router-link>

        <button
          @click="openAddModal"
          class="bg-primary hover:bg-primary/90 text-on-primary-container font-semibold px-4 py-1.5 rounded text-xs flex items-center gap-1.5 transition-colors shadow-glow"
        >
          <span class="material-symbols-outlined text-sm">add</span>
          Добавить устройство
        </button>
      </div>
    </div>

    <!-- Панель метрик -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
        <p class="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest">Всего устройств</p>
        <p class="text-2xl font-bold text-on-surface mt-1 font-mono">{{ status.total_devices || devices.length }}</p>
      </div>

      <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
        <p class="text-[10px] text-tertiary uppercase font-bold tracking-widest">Онлайн</p>
        <p class="text-2xl font-bold text-tertiary mt-1 font-mono">{{ status.online_devices || onlineCount }}</p>
      </div>

      <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
        <p class="text-[10px] text-primary uppercase font-bold tracking-widest">Локальное управление (LAN)</p>
        <p class="text-2xl font-bold text-primary mt-1 font-mono">{{ status.local_ready_devices || localReadyCount }}</p>
      </div>

      <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
        <p class="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest">Статус Tuya Cloud</p>
        <p class="text-xs font-bold mt-2.5 flex items-center gap-2" :class="status.cloud_configured ? 'text-tertiary' : 'text-on-surface-variant'">
          <span class="w-2 h-2 rounded-full" :class="status.cloud_configured ? 'bg-tertiary' : 'bg-outline'"></span>
          {{ status.cloud_configured ? 'Подключено' : 'Не настроено' }}
        </p>
      </div>
    </div>

    <!-- Таблица / список устройств -->
    <div class="bg-surface-container-low border border-outline-variant rounded-xl overflow-hidden shadow-glow">
      <div class="p-4 border-b border-outline-variant bg-surface-container-high flex items-center justify-between">
        <h3 class="font-bold text-sm text-on-surface">Реестр устройств Tuya</h3>
        <span class="text-xs text-on-surface-variant font-mono">{{ devices.length }} объектов</span>
      </div>

      <div v-if="loading && devices.length === 0" class="p-8 text-center text-sm text-on-surface-variant">
        Загрузка устройств Tuya...
      </div>

      <div v-else-if="devices.length === 0" class="p-12 text-center">
        <span class="material-symbols-outlined text-4xl text-on-surface-variant opacity-50 mb-2">devices_off</span>
        <p class="text-sm font-semibold text-on-surface">Устройства Tuya не добавлены</p>
        <p class="text-xs text-on-surface-variant mt-1">Добавьте устройство вручную или выполните синхронизацию с Tuya Cloud</p>
        <button
          @click="openAddModal"
          class="mt-4 bg-primary text-on-primary-container px-4 py-2 rounded text-xs font-semibold transition-colors"
        >
          Добавить устройство
        </button>
      </div>

      <table v-else class="w-full text-left border-collapse">
        <thead class="bg-surface-container-highest border-b border-outline-variant/30">
          <tr class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest">
            <th class="px-4 py-3">Устройство</th>
            <th class="px-4 py-3">IP / Сеть</th>
            <th class="px-4 py-3">Режим</th>
            <th class="px-4 py-3">Статус</th>
            <th class="px-4 py-3">DPS Состояние</th>
            <th class="px-4 py-3 text-right">Действия</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant/10 text-xs">
          <tr v-for="dev in devices" :key="dev.device_id" class="hover:bg-surface-container-high/50 transition-colors">
            <!-- Устройство -->
            <td class="px-4 py-4">
              <div class="font-bold text-on-surface">{{ dev.name }}</div>
              <div class="text-[11px] text-on-surface-variant font-mono opacity-80">{{ dev.device_id }}</div>
            </td>

            <!-- IP / Сеть -->
            <td class="px-4 py-4 font-mono text-on-surface-variant">
              <div v-if="dev.ip" class="flex items-center gap-1.5 text-on-surface">
                <span class="material-symbols-outlined text-sm text-primary">lan</span>
                {{ dev.ip }}
              </div>
              <div v-else class="text-[11px] opacity-60">Cloud Only</div>
            </td>

            <!-- Режим -->
            <td class="px-4 py-4">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                :class="{
                  'bg-primary/10 text-primary border border-primary/20': dev.mode === 'auto',
                  'bg-tertiary/10 text-tertiary border border-tertiary/20': dev.mode === 'local',
                  'bg-surface-variant text-on-surface-variant': dev.mode === 'cloud'
                }">
                {{ dev.mode }}
              </span>
            </td>

            <!-- Онлайн статус -->
            <td class="px-4 py-4">
              <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium"
                :class="dev.online ? 'bg-tertiary/10 text-tertiary' : 'bg-surface-variant text-on-surface-variant'">
                <span class="w-1.5 h-1.5 rounded-full" :class="dev.online ? 'bg-tertiary' : 'bg-outline'"></span>
                {{ dev.online ? 'Онлайн' : 'Офлайн' }}
              </span>
            </td>

            <!-- DPS Состояние -->
            <td class="px-4 py-4 font-mono text-[11px]">
              <div v-if="dev.dps && Object.keys(dev.dps).length" class="flex flex-wrap gap-1 max-w-xs">
                <span v-for="(val, key) in dev.dps" :key="key" class="px-1.5 py-0.5 bg-surface-container-high rounded border border-outline-variant/30 text-on-surface-variant">
                  {{ key }}: <strong class="text-on-surface">{{ val }}</strong>
                </span>
              </div>
              <span v-else class="text-on-surface-variant opacity-50">—</span>
            </td>

            <!-- Действия -->
            <td class="px-4 py-4 text-right">
              <div class="flex items-center justify-end gap-2">
                <button
                  @click="togglePower(dev)"
                  class="px-2.5 py-1 rounded text-xs font-semibold flex items-center gap-1 transition-colors"
                  :class="isPoweredOn(dev) ? 'bg-tertiary text-on-tertiary-container hover:bg-tertiary/90' : 'bg-surface-container-high text-on-surface hover:bg-surface-variant'"
                >
                  <span class="material-symbols-outlined text-sm">power_settings_new</span>
                  {{ isPoweredOn(dev) ? 'ВКЛ' : 'ВЫКЛ' }}
                </button>

                <button
                  @click="openEditModal(dev)"
                  class="p-1 rounded text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 transition-colors"
                  title="Редактировать"
                >
                  <span class="material-symbols-outlined text-sm">edit</span>
                </button>

                <button
                  @click="deleteDevice(dev.device_id)"
                  class="p-1 rounded text-error hover:bg-error/10 transition-colors"
                  title="Удалить"
                >
                  <span class="material-symbols-outlined text-sm">delete</span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Модальное окно Добавления / Редактирования устройства -->
    <div v-if="showModal" class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-surface-container-low border border-outline-variant rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-outline-variant/40 pb-3">
          <h3 class="font-bold text-lg text-on-surface">
            {{ isEditing ? 'Редактировать устройство' : 'Добавить устройство Tuya' }}
          </h3>
          <button @click="showModal = false" class="text-on-surface-variant hover:text-on-surface">
            <span class="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        <form @submit.prevent="saveDevice" class="space-y-3">
          <div>
            <label class="block text-xs font-semibold text-on-surface-variant mb-1">Device ID (Идентификатор) *</label>
            <input
              v-model="form.device_id"
              :disabled="isEditing"
              required
              type="text"
              placeholder="eb1234567890abcdef"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs font-mono text-on-surface focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-on-surface-variant mb-1">Название устройства</label>
            <input
              v-model="form.name"
              type="text"
              placeholder="Розетка в гостиной"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:outline-none focus:border-primary"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant mb-1">IP адрес (локальный)</label>
              <input
                v-model="form.ip"
                type="text"
                placeholder="192.168.1.100"
                class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs font-mono text-on-surface focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label class="block text-xs font-semibold text-on-surface-variant mb-1">Версия протокола</label>
              <select
                v-model="form.protocol_version"
                class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:outline-none focus:border-primary"
              >
                <option value="3.1">3.1</option>
                <option value="3.3">3.3 (Стандарт)</option>
                <option value="3.4">3.4</option>
                <option value="3.5">3.5</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-on-surface-variant mb-1">Local Key (Ключ шифрования LAN)</label>
            <input
              v-model="form.local_key"
              type="password"
              placeholder="16-символьный ключ"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs font-mono text-on-surface focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-on-surface-variant mb-1">Режим управления</label>
            <select
              v-model="form.mode"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-xs text-on-surface focus:outline-none focus:border-primary"
            >
              <option value="auto">Auto (Гибридный: LAN с фолбэком на Cloud)</option>
              <option value="local">Local (Только локальная сеть LAN)</option>
              <option value="cloud">Cloud (Только Tuya Cloud API)</option>
            </select>
          </div>

          <div class="flex justify-end gap-3 pt-3 border-t border-outline-variant/40">
            <button
              type="button"
              @click="showModal = false"
              class="px-4 py-2 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface"
            >
              Отмена
            </button>
            <button
              type="submit"
              :disabled="saving"
              class="bg-primary text-on-primary-container px-4 py-2 rounded text-xs font-semibold hover:bg-primary/90 transition-colors shadow-glow"
            >
              {{ saving ? 'Сохранение...' : 'Сохранить' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

interface TuyaDevice {
  device_id: string
  name: string
  ip: string | null
  local_key: string | null
  protocol_version: string
  category: string
  online: boolean
  mode: string
  dps: Record<string, any>
}


const loading = ref(false)
const syncing = ref(false)
const saving = ref(false)
const showModal = ref(false)
const isEditing = ref(false)

const status = ref<Record<string, any>>({})
const devices = ref<TuyaDevice[]>([])

const form = ref({
  device_id: '',
  name: '',
  ip: '',
  local_key: '',
  protocol_version: '3.3',
  category: 'general',
  mode: 'auto',
})

const onlineCount = computed(() => devices.value.filter((d) => d.online).length)
const localReadyCount = computed(() => devices.value.filter((d) => d.ip && d.local_key).length)

async function loadData() {
  loading.value = true
  try {
    const [resStatus, resDevs] = await Promise.all([
      fetch('/api/v1/m/tuya/status').then((r) => r.ok ? r.json() : {}),
      fetch('/api/v1/m/tuya/devices').then((r) => r.ok ? r.json() : []),
    ])
    status.value = resStatus
    devices.value = resDevs
  } catch (e) {
    console.error('Ошибка загрузки данных Tuya:', e)
  } finally {
    loading.value = false
  }
}

async function syncCloud() {
  syncing.value = true
  try {
    await fetch('/api/v1/m/tuya/sync', { method: 'POST' })
    await loadData()
  } catch (e) {
    console.error('Ошибка синхронизации Tuya:', e)
  } finally {
    syncing.value = false
  }
}

function openAddModal() {
  isEditing.value = false
  form.value = {
    device_id: '',
    name: '',
    ip: '',
    local_key: '',
    protocol_version: '3.3',
    category: 'general',
    mode: 'auto',
  }
  showModal.value = true
}

function openEditModal(dev: TuyaDevice) {
  isEditing.value = true
  form.value = {
    device_id: dev.device_id,
    name: dev.name || '',
    ip: dev.ip || '',
    local_key: dev.local_key || '',
    protocol_version: dev.protocol_version || '3.3',
    category: dev.category || 'general',
    mode: dev.mode || 'auto',
  }
  showModal.value = true
}

async function saveDevice() {
  if (!form.value.device_id) return
  saving.value = true
  try {
    const method = isEditing.value ? 'PUT' : 'POST'
    const url = isEditing.value
      ? `/api/v1/m/tuya/devices/${form.value.device_id}`
      : '/api/v1/m/tuya/devices'

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value),
    })

    if (res.ok) {
      showModal.value = false
      await loadData()
    }
  } catch (e) {
    console.error('Ошибка сохранения устройства Tuya:', e)
  } finally {
    saving.value = false
  }
}

async function deleteDevice(deviceId: string) {
  if (!confirm(`Удалить устройство ${deviceId}?`)) return
  try {
    const res = await fetch(`/api/v1/m/tuya/devices/${deviceId}`, { method: 'DELETE' })
    if (res.ok) {
      await loadData()
    }
  } catch (e) {
    console.error('Ошибка удаления устройства:', e)
  }
}

function isPoweredOn(dev: TuyaDevice): boolean {
  if (!dev.dps) return false
  return Boolean(dev.dps['1'] || dev.dps['switch_1'] || dev.dps['switch'])
}

async function togglePower(dev: TuyaDevice) {
  const currentState = isPoweredOn(dev)
  const newState = !currentState
  const commands = { '1': newState, switch_1: newState }

  try {
    const res = await fetch(`/api/v1/m/tuya/devices/${dev.device_id}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ commands }),
    })
    if (res.ok) {
      dev.dps['1'] = newState
      dev.dps['switch_1'] = newState
    }
  } catch (e) {
    console.error('Ошибка отправки команды:', e)
  }
}

onMounted(loadData)
</script>
