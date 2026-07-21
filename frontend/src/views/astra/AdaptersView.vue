<template>
  <div class="p-6 space-y-6 animate-fade-in">
    <!-- Заголовок -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">DVB Адаптеры</h1>
        <p class="mt-1 text-sm text-slate-400">Мониторинг сигнала тюнеров DVB-S/S2/T2/C и сканирование частот транспондеров</p>
      </div>
      <div class="flex items-center gap-2 self-start sm:self-auto">
        <span class="text-xs font-semibold text-slate-450 uppercase tracking-wider">Экземпляр:</span>
        <select
          v-model="selectedInstance"
          class="px-3 py-1.5 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white focus:outline-none focus:border-accent"
        >
          <option value="">Все экземпляры</option>
          <option
            v-for="inst in instances"
            :key="inst.index"
            :value="inst.index"
          >
            {{ inst.label }}
          </option>
        </select>
      </div>
    </div>

    <!-- Вкладки и кнопка настроек -->
    <div class="flex flex-row items-center justify-between gap-4 border-b border-surface-700/60 pb-3">
      <div class="flex gap-2">
        <Button
          :variant="activeTab === 'monitor' ? 'primary' : 'ghost'"
          size="sm"
          class="h-9"
          @click="activeTab = 'monitor'"
        >
          Монитор
        </Button>
        <Button
          :variant="activeTab === 'data' ? 'primary' : 'ghost'"
          size="sm"
          class="h-9"
          @click="activeTab = 'data'"
        >
          Данные
        </Button>
      </div>

      <div class="relative">
        <Button variant="secondary" size="sm" class="h-9 w-9 p-0 flex items-center justify-center" @click="showSettings = !showSettings" title="Настройка отображения">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </Button>

        <!-- Выпадающий список настроек отображения -->
        <div v-if="showSettings" class="absolute right-0 mt-2 w-56 p-4 rounded-xl border border-surface-700 bg-surface-800 shadow-xl z-20 space-y-2">
          <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Настройка вида</h4>
          
          <div v-if="activeTab === 'monitor'" class="space-y-2">
            <label v-for="item in monitorSettings" :key="item.key" class="flex items-center gap-2.5 text-sm text-slate-350 hover:text-white cursor-pointer select-none">
              <input
                type="checkbox"
                v-model="item.visible"
                class="rounded bg-surface-700 border-surface-650 text-accent focus:ring-accent/40"
              />
              {{ item.label }}
            </label>
          </div>

          <div v-if="activeTab === 'data'" class="space-y-2">
            <label v-for="col in dataColumns" :key="col.key" class="flex items-center gap-2.5 text-sm text-slate-350 hover:text-white cursor-pointer select-none">
              <input
                type="checkbox"
                v-model="col.visible"
                :disabled="col.required"
                class="rounded bg-surface-700 border-surface-650 text-accent focus:ring-accent/40"
              />
              {{ col.label }}
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Индикатор загрузки -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div v-for="i in 2" :key="i" class="h-64 rounded-xl border border-surface-700 bg-surface-800/40 animate-pulse" />
    </div>

    <!-- Пустое состояние -->
    <div v-else-if="filteredAdapters.length === 0" class="text-center py-12 text-slate-500 rounded-xl border border-surface-700 bg-surface-800/20">
      <div class="w-12 h-12 rounded-full bg-surface-750/50 flex items-center justify-center mx-auto mb-3">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-slate-450" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
        </svg>
      </div>
      <h3 class="text-base font-semibold text-white mb-1">DVB-адаптеры не найдены</h3>
      <p class="text-xs text-slate-400">На выбранном экземпляре Astra нет подключенных или настроенных DVB карт.</p>
    </div>

    <div v-else>
      <!-- Вкладка Монитор: сетка карточек с метриками сигнала -->
      <div v-if="activeTab === 'monitor'" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card
          v-for="adap in filteredAdapters"
          :key="`${adap.instance_index}-${adap.name}`"
          :title="adap.name"
          class="hover:border-surface-600"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-lg font-semibold text-white">{{ adap.name }}</h3>
                <p class="text-xs text-slate-450 font-mono mt-0.5">
                  {{ adap.instance_label }} • Адаптер #{{ adap.adapter_id }} (DVB-{{ adap.type }})
                </p>
              </div>
              <span
                v-if="isSettingVisible('lock')"
                :class="[
                  'px-2 py-0.5 rounded-full text-xs font-semibold tracking-wide flex items-center gap-1.5',
                  adap.lock ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'
                ]"
              >
                <span :class="['w-1.5 h-1.5 rounded-full', adap.lock ? 'bg-success animate-pulse-soft' : 'bg-danger']" />
                {{ adap.lock ? 'LOCK (Сигнал)' : 'NO LOCK' }}
              </span>
            </div>
          </template>

          <div class="mt-4 space-y-4">
            <!-- SNR -->
            <div v-if="isSettingVisible('snr')" class="space-y-1.5">
              <div class="flex justify-between text-xs">
                <span class="text-slate-400 font-semibold uppercase tracking-wider">Качество сигнала (SNR)</span>
                <span class="font-mono text-white font-semibold">{{ adap.snr.toFixed(1) }} dB</span>
              </div>
              <div class="h-2 w-full bg-surface-750 rounded-full overflow-hidden border border-surface-700">
                <div
                  :class="[
                    'h-full rounded-full transition-all duration-300',
                    adap.snr >= 10 ? 'bg-success' : adap.snr >= 5 ? 'bg-warning' : 'bg-danger'
                  ]"
                  :style="{ width: `${Math.min((adap.snr / 16) * 100, 100)}%` }"
                />
              </div>
            </div>

            <!-- Signal Strength -->
            <div v-if="isSettingVisible('signal')" class="space-y-1.5">
              <div class="flex justify-between text-xs">
                <span class="text-slate-400 font-semibold uppercase tracking-wider">Уровень сигнала (Strength)</span>
                <span class="font-mono text-white font-semibold">{{ adap.signal.toFixed(0) }}%</span>
              </div>
              <div class="h-2 w-full bg-surface-750 rounded-full overflow-hidden border border-surface-700">
                <div
                  :class="[
                    'h-full rounded-full transition-all duration-300',
                    adap.signal >= 70 ? 'bg-success' : adap.signal >= 40 ? 'bg-warning' : 'bg-danger'
                  ]"
                  :style="{ width: `${adap.signal}%` }"
                />
              </div>
            </div>

            <!-- Ошибки UNC / BER -->
            <div v-if="isSettingVisible('ber') || isSettingVisible('unc')" class="grid grid-cols-2 gap-4 mt-2 p-2 rounded bg-surface-750/30 border border-surface-750/50">
              <div v-if="isSettingVisible('ber')" class="text-center">
                <div class="text-[10px] text-slate-450 uppercase font-bold tracking-wider">Ошибки BER</div>
                <div :class="['text-sm font-mono mt-0.5', adap.ber > 0 ? 'text-danger font-bold' : 'text-slate-300']">
                  {{ formatBer(adap.ber) }}
                </div>
              </div>
              <div v-if="isSettingVisible('unc')" class="text-center" :class="isSettingVisible('ber') ? 'border-l border-surface-700/60' : ''">
                <div class="text-[10px] text-slate-450 uppercase font-bold tracking-wider">Пакеты UNC</div>
                <div :class="['text-sm font-mono mt-0.5', adap.unc > 0 ? 'text-danger font-bold' : 'text-slate-300']">
                  {{ adap.unc }}
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <!-- Вкладка Данные: плоская таблица адаптеров -->
      <div v-if="activeTab === 'data'" class="overflow-x-auto rounded-xl border border-surface-700 bg-surface-800/80 backdrop-blur-sm shadow-card p-6">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-surface-700 text-slate-450 text-xs uppercase font-semibold">
              <th class="py-3 px-4">Имя адаптера</th>
              <th v-if="isSettingVisible('instance', 'data')" class="py-3 px-4">Экземпляр</th>
              <th v-if="isSettingVisible('adapter_id', 'data')" class="py-3 px-4">ID адаптера</th>
              <th v-if="isSettingVisible('type', 'data')" class="py-3 px-4">Тип DVB</th>
              <th v-if="isSettingVisible('actions', 'data')" class="py-3 px-4 text-right">Действия</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-750/50 text-slate-300 text-sm">
            <tr
              v-for="adap in filteredAdapters"
              :key="`${adap.instance_index}-${adap.name}`"
              class="hover:bg-surface-750/20"
            >
              <td class="py-3.5 px-4 font-semibold text-white">
                {{ adap.name }}
              </td>
              <td v-if="isSettingVisible('instance', 'data')" class="py-3.5 px-4 text-xs text-slate-400">
                {{ adap.instance_label }}
              </td>
              <td v-if="isSettingVisible('adapter_id', 'data')" class="py-3.5 px-4 text-xs text-slate-300 font-mono">
                #{{ adap.adapter_id }}
              </td>
              <td v-if="isSettingVisible('type', 'data')" class="py-3.5 px-4 text-xs text-slate-300 font-mono">
                DVB-{{ adap.type }}
              </td>
              <td v-if="isSettingVisible('actions', 'data')" class="py-3.5 px-4 text-right">
                <Button
                  variant="secondary"
                  size="sm"
                  @click="startScanning(adap.instance_index, adap.name)"
                  :loading="scanningAdapter === `${adap.instance_index}-${adap.name}`"
                >
                  Сканировать частоту
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Модалка процесса сканирования DVB -->
    <div v-if="scanModalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in-fast">
      <div class="w-full max-w-lg p-6 rounded-xl border border-surface-700 bg-surface-800 shadow-xl space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-lg font-semibold text-white">Сканирование транспондера</h3>
            <p class="text-sm text-slate-400 mt-1">Адаптер: {{ activeScanName }}</p>
          </div>
          <span
            v-if="scanStatus === 'scanning'"
            class="px-2 py-0.5 rounded-full text-xs font-semibold bg-accent/20 text-accent animate-pulse-soft"
          >
            В процессе...
          </span>
          <span
            v-else
            class="px-2 py-0.5 rounded-full text-xs font-semibold bg-success/20 text-success"
          >
            Завершено
          </span>
        </div>

        <!-- Прогресс сканирования -->
        <div class="space-y-2">
          <div class="flex justify-between text-xs text-slate-400 font-mono">
            <span>Прогресс:</span>
            <span>{{ scanProgress }}%</span>
          </div>
          <div class="h-2 w-full bg-surface-750 rounded-full overflow-hidden border border-surface-700">
            <div
              class="h-full bg-accent rounded-full transition-all duration-300"
              :style="{ width: `${scanProgress}%` }"
            />
          </div>
        </div>

        <!-- Найденные ТВ/Радио каналы -->
        <div class="space-y-2">
          <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Найденные ТВ каналы ({{ foundChannels.length }})</div>
          <div class="bg-surface-850 rounded-lg border border-surface-750/70 max-h-48 overflow-y-auto divide-y divide-surface-750/40">
            <div v-if="foundChannels.length === 0" class="p-4 text-center text-xs text-slate-500">
              Пока ничего не найдено...
            </div>
            <div
              v-else
              v-for="(chan, idx) in foundChannels"
              :key="idx"
              class="p-2 px-3 text-xs flex justify-between items-center text-slate-350 hover:bg-surface-750/20"
            >
              <span class="font-medium text-white">{{ chan.name || 'Без имени' }}</span>
              <span class="font-mono text-slate-550">PNR: {{ chan.pnr }}</span>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3 pt-4 border-t border-surface-700/60">
          <Button variant="ghost" size="sm" :disabled="scanStatus === 'scanning'" @click="closeScanModal">Закрыть</Button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import http from '@/core/api'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'

interface AdapterItem {
  instance_index: number
  instance_label: string
  name: string
  adapter_id: number
  type: string
  lock: boolean
  signal: number
  snr: number
  ber: number
  unc: number
}

interface FoundChannel {
  name: string
  pnr: number
}

const adapters = ref<AdapterItem[]>([])
const instances = ref<any[]>([])
const loading = ref(true)
const selectedInstance = ref<number | string>('')

// Состояние вкладок и настройки отображения
const activeTab = ref<'monitor' | 'data'>('monitor')
const showSettings = ref(false)

const monitorSettings = ref([
  { key: 'lock', label: 'Статус LOCK', visible: true },
  { key: 'snr', label: 'Качество (SNR)', visible: true },
  { key: 'signal', label: 'Уровень (Strength)', visible: true },
  { key: 'ber', label: 'Ошибки BER', visible: true },
  { key: 'unc', label: 'Пакеты UNC', visible: true },
])

const dataColumns = ref([
  { key: 'instance', label: 'Экземпляр', visible: true, required: false },
  { key: 'adapter_id', label: 'ID адаптера', visible: true, required: false },
  { key: 'type', label: 'Тип DVB', visible: true, required: false },
  { key: 'actions', label: 'Действия', visible: true, required: false },
])

function isSettingVisible(key: string, type: 'monitor' | 'data' = 'monitor'): boolean {
  const list = type === 'monitor' ? monitorSettings.value : dataColumns.value
  const found = list.find(c => c.key === key)
  return found ? found.visible : true
}

function loadSettings() {
  const monitorSaved = localStorage.getItem('adapters_monitor_settings')
  if (monitorSaved) {
    try {
      const parsed = JSON.parse(monitorSaved)
      monitorSettings.value.forEach(item => {
        if (item.key in parsed) item.visible = parsed[item.key]
      })
    } catch (e) {}
  }
  
  const dataSaved = localStorage.getItem('adapters_data_cols')
  if (dataSaved) {
    try {
      const parsed = JSON.parse(dataSaved)
      dataColumns.value.forEach(col => {
        if (col.key in parsed) col.visible = parsed[col.key]
      })
    } catch (e) {}
  }
}

watch(
  () => monitorSettings.value,
  () => {
    const obj = monitorSettings.value.reduce((acc, item) => {
      acc[item.key] = item.visible
      return acc
    }, {} as Record<string, boolean>)
    localStorage.setItem('adapters_monitor_settings', JSON.stringify(obj))
  },
  { deep: true }
)

watch(
  () => dataColumns.value,
  () => {
    const obj = dataColumns.value.reduce((acc, col) => {
      acc[col.key] = col.visible
      return acc
    }, {} as Record<string, boolean>)
    localStorage.setItem('adapters_data_cols', JSON.stringify(obj))
  },
  { deep: true }
)

// Сканирование
const scanModalOpen = ref(false)
const scanningAdapter = ref<string | null>(null)
const activeScanName = ref('')
const scanStatus = ref('scanning')
const scanProgress = ref(0)
const foundChannels = ref<FoundChannel[]>([])



let timer: any = null
let scanTimer: any = null
let activeScanIndex = 0
let activeAdapterName = ''

async function loadData() {
  try {
    const [adapRes, instRes] = await Promise.all([
      http.get('/api/v1/m/astra/monitoring/adapters'),
      http.get('/api/v1/m/astra/instances')
    ])
    adapters.value = adapRes.data.items || []
    instances.value = (instRes.data.items || []).filter((i: any) => i.online)
  } catch (err) {
    console.error('Ошибка загрузки адаптеров', err)
  } finally {
    loading.value = false
  }
}

const filteredAdapters = computed(() => {
  if (selectedInstance.value === '') return adapters.value
  return adapters.value.filter(a => a.instance_index === Number(selectedInstance.value))
})

async function startScanning(instanceIndex: number, adapterName: string) {
  const key = `${instanceIndex}-${adapterName}`
  scanningAdapter.value = key
  activeScanName.value = adapterName
  activeScanIndex = instanceIndex
  activeAdapterName = adapterName
  foundChannels.value = []
  scanProgress.value = 0
  scanStatus.value = 'scanning'
  scanModalOpen.value = true

  try {
    await http.post(`/api/v1/m/astra/monitoring/adapters/${instanceIndex}/${adapterName}/scan`)
    // Запускаем периодический опрос результатов
    pollScanResult()
  } catch (err: any) {
    alert(`Ошибка запуска сканирования: ${err?.response?.data?.detail || err.message}`)
    scanModalOpen.value = false
    scanningAdapter.value = null
  }
}

async function pollScanResult() {
  if (scanTimer) clearTimeout(scanTimer)
  try {
    const { data } = await http.get(`/api/v1/m/astra/monitoring/adapters/${activeScanIndex}/${activeAdapterName}/scan-result`)
    scanProgress.value = data.progress || 0
    scanStatus.value = data.status || 'scanning'
    foundChannels.value = data.channels || []

    if (scanStatus.value === 'scanning') {
      scanTimer = setTimeout(pollScanResult, 2000)
    } else {
      scanningAdapter.value = null
    }
  } catch (err) {
    console.error('Ошибка опроса сканирования', err)
    scanStatus.value = 'error'
    scanningAdapter.value = null
  }
}

function closeScanModal() {
  scanModalOpen.value = false
  if (scanTimer) clearTimeout(scanTimer)
}

function formatBer(ber: number): string {
  if (ber === 0) return '0'
  return ber.toExponential(1)
}

function formatBitrate(kbps: number): string {
  if (!kbps) return '0.00 Mbps'
  const mbps = kbps / 1024
  return `${mbps.toFixed(2)} Mbps`
}

onMounted(() => {
  loadSettings()
  loadData()
  timer = setInterval(loadData, 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (scanTimer) clearTimeout(scanTimer)
})
</script>
