<template>
  <div class="p-6 space-y-6 animate-fade-in">
    <!-- Заголовок -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Каналы Astra</h1>
        <p class="mt-1 text-sm text-slate-400">Мониторинг битрейта, ошибок декодирования и управление вещанием каналов</p>
      </div>
      <!-- Фильтр по инстансу -->
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
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-surface-700 text-slate-450 text-xs uppercase font-semibold">
              <th class="py-3 px-4">Имя канала</th>
              <th class="py-3 px-4">Экземпляр</th>
              <th class="py-3 px-4">Статус</th>
              <th class="py-3 px-4">Шифрование</th>
              <th class="py-3 px-4 text-right">Битрейт</th>
              <th class="py-3 px-4 text-right">Ошибки CC/PES</th>
              <th class="py-3 px-4 text-right">Действия</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-750/50 text-slate-300 text-sm">
            <tr
              v-for="chan in filteredChannels"
              :key="`${chan.instance_index}-${chan.name}`"
              class="hover:bg-surface-750/20"
            >
              <!-- Имя и URL -->
              <td class="py-3.5 px-4 font-semibold text-white">
                <div>{{ chan.name }}</div>
                <div class="text-[10px] text-slate-500 font-mono mt-0.5 truncate max-w-xs" :title="chan.inputs[0]">
                  {{ chan.inputs[0] || 'нет входа' }}
                </div>
              </td>
              <!-- Экземпляр -->
              <td class="py-3.5 px-4 text-xs text-slate-400">
                {{ chan.instance_label }}
              </td>
              <!-- Статус -->
              <td class="py-3.5 px-4">
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
              <!-- Скремблирование -->
              <td class="py-3.5 px-4 text-xs">
                <span
                  v-if="chan.scrambled"
                  class="bg-warning/20 text-warning px-1.5 py-0.5 rounded font-bold uppercase text-[10px]"
                >
                  BISS / CAS
                </span>
                <span v-else class="text-slate-500">Открытый</span>
              </td>
              <!-- Битрейт -->
              <td class="py-3.5 px-4 text-right font-mono font-medium text-white">
                {{ formatBitrate(chan.bitrate) }}
              </td>
              <!-- Ошибки -->
              <td class="py-3.5 px-4 text-right font-mono text-xs">
                <span :class="chan.cc_errors > 0 ? 'text-danger font-bold' : 'text-slate-500'">
                  CC: {{ chan.cc_errors }}
                </span>
                <span class="text-slate-600 mx-1">|</span>
                <span :class="chan.pes_errors > 0 ? 'text-danger font-bold' : 'text-slate-500'">
                  PES: {{ chan.pes_errors }}
                </span>
              </td>
              <!-- Действия -->
              <td class="py-3.5 px-4 text-right">
                <div class="inline-flex gap-2">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
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

function formatBitrate(kbps: number): string {
  if (!kbps) return '0.00 Mbps'
  const mbps = kbps / 1024
  return `${mbps.toFixed(2)} Mbps`
}

onMounted(() => {
  loadData()
  timer = setInterval(loadData, 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
