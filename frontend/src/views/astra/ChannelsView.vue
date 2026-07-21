<template>
  <div class="p-6 space-y-6 animate-fade-in">
    <!-- Заголовок -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Каналы Astra</h1>
        <p class="mt-1 text-sm text-slate-400">Мониторинг битрейта, ошибок декодирования и управление вещанием каналов</p>
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
        <Button variant="secondary" size="sm" class="h-9 w-9 p-0 flex items-center justify-center" @click="showColumnSettings = !showColumnSettings" title="Настройка колонок">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </Button>

        <!-- Выпадающий список настроек колонок -->
        <div v-if="showColumnSettings" class="absolute right-0 mt-2 w-56 p-4 rounded-xl border border-surface-700 bg-surface-800 shadow-xl z-20 space-y-2">
          <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Отображать колонки</h4>
          
          <div v-if="activeTab === 'monitor'" class="space-y-2">
            <label v-for="col in monitorColumns" :key="col.key" class="flex items-center gap-2.5 text-sm text-slate-350 hover:text-white cursor-pointer select-none">
              <input
                type="checkbox"
                v-model="col.visible"
                :disabled="col.required"
                class="rounded bg-surface-700 border-surface-650 text-accent focus:ring-accent/40"
              />
              {{ col.label }}
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

    <!-- Таблица каналов -->
    <Card padded class="overflow-hidden">
      <div v-if="loading" class="space-y-4 py-8">
        <div v-for="i in 5" :key="i" class="h-10 bg-surface-750/30 rounded-lg animate-pulse" />
      </div>

      <div v-else-if="filteredChannels.length === 0" class="text-center py-12 text-slate-500">
        <div class="w-12 h-12 rounded-full bg-surface-750/50 flex items-center justify-center mx-auto mb-3">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-slate-450" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4" />
          </svg>
        </div>
        <h3 class="text-base font-semibold text-white mb-1">Каналы не найдены</h3>
        <p class="text-xs text-slate-400">На выбранном экземпляре нет запущенных или настроенных каналов.</p>
      </div>

      <div v-else class="overflow-x-auto">
        <!-- Таблица для вкладки Монитор -->
        <table v-if="activeTab === 'monitor'" class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-surface-700 text-slate-450 text-xs uppercase font-semibold">
              <th class="py-3 px-4">Имя канала</th>
              <th v-if="isVisible('instance', 'monitor')" class="py-3 px-4">Экземпляр</th>
              <th v-if="isVisible('status', 'monitor')" class="py-3 px-4">Статус</th>
              <th v-if="isVisible('scrambled', 'monitor')" class="py-3 px-4">Шифрование</th>
              <th v-if="isVisible('bitrate', 'monitor')" class="py-3 px-4 text-right">Битрейт</th>
              <th v-if="isVisible('errors', 'monitor')" class="py-3 px-4 text-right">Ошибки CC/PES</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-750/50 text-slate-300 text-sm">
            <tr
              v-for="chan in filteredChannels"
              :key="`${chan.instance_index}-${chan.name}`"
              class="hover:bg-surface-750/20"
            >
              <td class="py-3.5 px-4 font-semibold text-white">
                <div>{{ chan.name }}</div>
              </td>
              <td v-if="isVisible('instance', 'monitor')" class="py-3.5 px-4 text-xs text-slate-400">
                {{ chan.instance_label }}
              </td>
              <td v-if="isVisible('status', 'monitor')" class="py-3.5 px-4">
                <span
                  :class="[
                    'px-2 py-0.5 rounded-full text-xs font-medium inline-flex items-center gap-1.5',
                    chan.ready ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'
                  ]"
                >
                  <span :class="['w-1.5 h-1.5 rounded-full', chan.ready ? 'bg-success animate-pulse-soft' : 'bg-danger']" />
                  {{ chan.ready ? 'Вещает' : 'Остановлен' }}
                </span>
              </td>
              <td v-if="isVisible('scrambled', 'monitor')" class="py-3.5 px-4 text-xs">
                <span
                  v-if="chan.scrambled"
                  class="bg-warning/20 text-warning px-1.5 py-0.5 rounded font-bold uppercase text-[10px]"
                >
                  BISS / CAS
                </span>
                <span v-else class="text-slate-500">Открытый</span>
              </td>
              <td v-if="isVisible('bitrate', 'monitor')" class="py-3.5 px-4 text-right font-mono font-medium text-white">
                {{ formatBitrate(chan.bitrate) }}
              </td>
              <td v-if="isVisible('errors', 'monitor')" class="py-3.5 px-4 text-right font-mono text-xs">
                <span :class="chan.cc_errors > 0 ? 'text-danger font-bold' : 'text-slate-500'">
                  CC: {{ chan.cc_errors }}
                </span>
                <span class="text-slate-600 mx-1">|</span>
                <span :class="chan.pes_errors > 0 ? 'text-danger font-bold' : 'text-slate-500'">
                  PES: {{ chan.pes_errors }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Таблица для вкладки Данные -->
        <table v-if="activeTab === 'data'" class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-surface-700 text-slate-450 text-xs uppercase font-semibold">
              <th class="py-3 px-4">Имя канала</th>
              <th v-if="isVisible('instance', 'data')" class="py-3 px-4">Экземпляр</th>
              <th v-if="isVisible('inputs', 'data')" class="py-3 px-4">Входы</th>
              <th v-if="isVisible('outputs', 'data')" class="py-3 px-4">Выходы</th>
              <th v-if="isVisible('psi', 'data')" class="py-3 px-4 text-center">PSI Анализ</th>
              <th v-if="isVisible('actions', 'data')" class="py-3 px-4 text-right">Действия</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-750/50 text-slate-300 text-sm">
            <tr
              v-for="chan in filteredChannels"
              :key="`${chan.instance_index}-${chan.name}`"
              class="hover:bg-surface-750/20"
            >
              <td class="py-3.5 px-4 font-semibold text-white">
                <div>{{ chan.name }}</div>
              </td>
              <td v-if="isVisible('instance', 'data')" class="py-3.5 px-4 text-xs text-slate-400">
                {{ chan.instance_label }}
              </td>
              <td v-if="isVisible('inputs', 'data')" class="py-3.5 px-4 text-xs text-slate-400 font-mono">
                <div class="truncate max-w-xs" :title="chan.inputs.join(', ')">
                  {{ chan.inputs[0] || 'нет входа' }}
                  <span v-if="chan.inputs.length > 1" class="text-accent font-semibold"> (+{{ chan.inputs.length - 1 }})</span>
                </div>
              </td>
              <td v-if="isVisible('outputs', 'data')" class="py-3.5 px-4 text-xs text-slate-400 font-mono">
                <div class="truncate max-w-xs" :title="chan.outputs.join(', ')">
                  {{ chan.outputs[0] || 'нет выхода' }}
                  <span v-if="chan.outputs.length > 1" class="text-accent font-semibold"> (+{{ chan.outputs.length - 1 }})</span>
                </div>
              </td>
              <td v-if="isVisible('psi', 'data')" class="py-3.5 px-4 text-center">
                <Button
                  variant="secondary"
                  size="sm"
                  class="h-7 px-2 text-xs"
                  @click="viewChannelInfo(chan.instance_index, chan.name)"
                >
                  PSI
                </Button>
              </td>
              <td v-if="isVisible('actions', 'data')" class="py-3.5 px-4 text-right">
                <div class="inline-flex gap-1">
                  <Button
                    v-if="chan.ready"
                    variant="danger"
                    size="sm"
                    class="h-7 px-2 text-xs"
                    :loading="loadingAction === `${chan.instance_index}-${chan.name}-stop`"
                    @click="controlChannel(chan.instance_index, chan.name, 'stop')"
                  >
                    Стоп
                  </Button>
                  <Button
                    v-else
                    variant="primary"
                    size="sm"
                    class="h-7 px-2 text-xs"
                    :loading="loadingAction === `${chan.instance_index}-${chan.name}-start`"
                    @click="controlChannel(chan.instance_index, chan.name, 'restart')"
                  >
                    Старт
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    class="h-7 px-2 text-xs"
                    :loading="loadingAction === `${chan.instance_index}-${chan.name}-restart`"
                    @click="controlChannel(chan.instance_index, chan.name, 'restart')"
                  >
                    Рестарт
                  </Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <!-- Модальное окно детальной информации о канале -->
    <div v-if="infoModalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in-fast">
      <div class="w-full max-w-2xl p-6 rounded-xl border border-surface-700 bg-surface-800 shadow-xl space-y-6 max-h-[85vh] overflow-y-auto">
        <div class="flex items-start justify-between">
          <div>
            <h3 class="text-lg font-semibold text-white">Детали канала: {{ infoData.name }}</h3>
            <p class="text-xs text-slate-400 mt-0.5">Информация получена от HTTP API astra-monitor</p>
          </div>
          <span
            :class="[
              'px-2 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1.5',
              infoData.monitored ? 'bg-success/20 text-success' : 'bg-slate-700 text-slate-400'
            ]"
          >
            {{ infoData.monitored ? 'Мониторинг активен' : 'Без мониторинга' }}
          </span>
        </div>

        <div class="space-y-4 text-sm">
          <!-- Конфигурация входов/выходов -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="p-3 rounded-lg bg-surface-750/30 border border-surface-750/50 space-y-2">
              <span class="text-xs font-bold text-slate-450 uppercase tracking-wider">Входы (Inputs)</span>
              <ul class="list-disc pl-4 space-y-1 font-mono text-xs text-white">
                <li v-for="(inp, idx) in infoData.config.input" :key="idx" class="break-all">{{ inp }}</li>
                <li v-if="!infoData.config.input || infoData.config.input.length === 0" class="text-slate-500">Нет входов</li>
              </ul>
            </div>
            <div class="p-3 rounded-lg bg-surface-750/30 border border-surface-750/50 space-y-2">
              <span class="text-xs font-bold text-slate-450 uppercase tracking-wider">Выходы (Outputs)</span>
              <ul class="list-disc pl-4 space-y-1 font-mono text-xs text-white">
                <li v-for="(out, idx) in infoData.config.output" :key="idx" class="break-all">{{ out }}</li>
                <li v-if="!infoData.config.output || infoData.config.output.length === 0" class="text-slate-500">Нет выходов</li>
              </ul>
            </div>
          </div>

          <!-- PSI Анализ -->
          <div v-if="infoData.psi" class="space-y-3">
            <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">PSI-таблицы (Анализ потока)</h4>
            
            <div class="space-y-2">
              <!-- PAT -->
              <div v-if="infoData.psi.pat" class="p-3 rounded-lg bg-surface-850 border border-surface-750/60 space-y-1.5">
                <div class="text-xs font-bold text-accent">PAT (Program Association Table)</div>
                <div class="text-xs text-slate-300 font-mono">
                  <div>Transport Stream ID: {{ infoData.psi.pat.tsid }}</div>
                  <div class="mt-1 font-semibold text-slate-400">Программы (PMT PIDs):</div>
                  <ul class="list-disc pl-4 mt-0.5 space-y-0.5">
                    <li v-for="(pmtPid, pnr) in infoData.psi.pat.programs" :key="pnr">
                      PNR {{ pnr }}: PID {{ pmtPid }}
                    </li>
                  </ul>
                </div>
              </div>

              <!-- SDT -->
              <div v-if="infoData.psi.sdt" class="p-3 rounded-lg bg-surface-850 border border-surface-750/60 space-y-1.5">
                <div class="text-xs font-bold text-accent">SDT (Service Description Table)</div>
                <div class="text-xs text-slate-300 font-mono">
                  <div class="font-semibold text-slate-400">Сервисы:</div>
                  <ul class="list-disc pl-4 mt-0.5 space-y-0.5">
                    <li v-for="(srv, pnr) in infoData.psi.sdt.services" :key="pnr">
                      PNR {{ pnr }}: <span class="text-white font-semibold">{{ srv.name }}</span> ({{ srv.provider }})
                    </li>
                  </ul>
                </div>
              </div>

              <!-- PMT -->
              <div v-if="infoData.psi.pmt" class="p-3 rounded-lg bg-surface-850 border border-surface-750/60 space-y-1.5">
                <div class="text-xs font-bold text-accent">PMT (Program Map Table)</div>
                <div class="text-xs text-slate-300 font-mono">
                  <div v-for="(pmtInfo, pnr) in infoData.psi.pmt" :key="pnr" class="border-t border-surface-700/40 pt-1.5 first:border-0 first:pt-0">
                    <div class="font-semibold text-slate-400">Программа (PNR) {{ pnr }} (PCR PID: {{ pmtInfo.pcr }}):</div>
                    <ul class="list-disc pl-4 mt-0.5 space-y-0.5">
                      <li v-for="(stream, idx) in pmtInfo.streams" :key="idx">
                        PID {{ stream.pid }}: тип {{ stream.type }}
                        <span v-if="stream.type_desc" class="text-slate-500">({{ stream.type_desc }})</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

            </div>
          </div>
          
          <div v-else class="p-4 rounded-lg bg-surface-750/10 border border-surface-750/30 text-center text-xs text-slate-450 font-mono">
            PSI-таблицы отсутствуют или поток еще не проанализирован.
          </div>
        </div>

        <div class="flex justify-end gap-3 pt-4 border-t border-surface-700/60">
          <Button variant="ghost" size="sm" @click="closeInfoModal">Закрыть</Button>
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

interface ChannelItem {
  instance_index: number
  instance_label: string
  name: string
  ready: boolean
  scrambled: boolean
  bitrate: number
  cc_errors: number
  pes_errors: number
  inputs: string[]
  outputs: string[]
}

const channels = ref<ChannelItem[]>([])
const instances = ref<any[]>([])
const loading = ref(true)
const loadingAction = ref<string | null>(null)
const selectedInstance = ref<number | string>('')

// Состояние вкладок и настройки колонок
const activeTab = ref<'monitor' | 'data'>('monitor')
const showColumnSettings = ref(false)

const monitorColumns = ref([
  { key: 'instance', label: 'Экземпляр', visible: true, required: false },
  { key: 'status', label: 'Статус', visible: true, required: false },
  { key: 'scrambled', label: 'Шифрование', visible: true, required: false },
  { key: 'bitrate', label: 'Битрейт', visible: true, required: false },
  { key: 'errors', label: 'Ошибки CC/PES', visible: true, required: false },
])

const dataColumns = ref([
  { key: 'instance', label: 'Экземпляр', visible: true, required: false },
  { key: 'inputs', label: 'Входы', visible: true, required: false },
  { key: 'outputs', label: 'Выходы', visible: true, required: false },
  { key: 'psi', label: 'Детальная PSI', visible: true, required: false },
  { key: 'actions', label: 'Действия', visible: true, required: false },
])

function isVisible(key: string, type: 'monitor' | 'data'): boolean {
  if (key === 'name') return true
  const list = type === 'monitor' ? monitorColumns.value : dataColumns.value
  const found = list.find(c => c.key === key)
  return found ? found.visible : true
}

function loadSettings() {
  const monitorSaved = localStorage.getItem('channels_monitor_cols')
  if (monitorSaved) {
    try {
      const parsed = JSON.parse(monitorSaved)
      monitorColumns.value.forEach(col => {
        if (col.key in parsed) col.visible = parsed[col.key]
      })
    } catch (e) {}
  }
  
  const dataSaved = localStorage.getItem('channels_data_cols')
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
  () => monitorColumns.value,
  () => {
    const obj = monitorColumns.value.reduce((acc, col) => {
      acc[col.key] = col.visible
      return acc
    }, {} as Record<string, boolean>)
    localStorage.setItem('channels_monitor_cols', JSON.stringify(obj))
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
    localStorage.setItem('channels_data_cols', JSON.stringify(obj))
  },
  { deep: true }
)

// Модалки
const infoModalOpen = ref(false)

const infoData = ref({
  name: '',
  monitored: false,
  config: {
    input: [] as string[],
    output: [] as string[]
  },
  status: {} as any,
  psi: null as any
})

let timer: any = null

async function loadData() {
  try {
    const [chanRes, instRes] = await Promise.all([
      http.get('/api/v1/m/astra/monitoring/channels'),
      http.get('/api/v1/m/astra/instances')
    ])
    channels.value = chanRes.data.items || []
    instances.value = (instRes.data.items || []).filter((i: any) => i.online)
  } catch (err) {
    console.error('Ошибка загрузки каналов', err)
  } finally {
    loading.value = false
  }
}

const filteredChannels = computed(() => {
  if (selectedInstance.value === '') return channels.value
  return channels.value.filter(c => c.instance_index === Number(selectedInstance.value))
})

async function controlChannel(instanceIndex: number, channelName: string, action: string) {
  const key = `${instanceIndex}-${channelName}-${action}`
  loadingAction.value = key
  try {
    await http.post(`/api/v1/m/astra/monitoring/channels/${instanceIndex}/${channelName}/${action}`)
    await loadData()
  } catch (err: any) {
    alert(`Ошибка управления каналом: ${err?.response?.data?.detail || err.message}`)
  } finally {
    loadingAction.value = null
  }
}



async function viewChannelInfo(instanceIndex: number, channelName: string) {
  try {
    const { data } = await http.get(`/api/v1/m/astra/monitoring/channels/${instanceIndex}/${channelName}/info`)
    infoData.value = data
    infoModalOpen.value = true
  } catch (err: any) {
    alert(`Ошибка получения информации о канале: ${err?.response?.data?.detail || err.message}`)
  }
}

function closeInfoModal() {
  infoModalOpen.value = false
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
})
</script>
