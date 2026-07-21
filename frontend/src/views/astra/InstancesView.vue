<template>
  <div class="p-6 space-y-6 animate-fade-in">
    <!-- Заголовок -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Экземпляры Astra</h1>
        <p class="mt-1 text-sm text-slate-400">Управление подключениями и состоянием экземпляров Cesbo Astra</p>
      </div>
      <div class="flex flex-wrap gap-2 self-start sm:self-auto">
        <Button variant="secondary" @click="openScanModal">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Слепое сканирование
        </Button>
        <Button variant="primary" @click="openAddModal">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Добавить экземпляр
        </Button>
      </div>
    </div>

    <!-- Список карточек инстансов -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 3" :key="i" class="h-44 rounded-xl border border-surface-700 bg-surface-800/40 animate-pulse" />
    </div>

    <div v-else-if="instances.length === 0" class="flex flex-col items-center justify-center p-12 rounded-xl border border-surface-700 bg-surface-800/20 text-center">
      <div class="w-16 h-16 rounded-2xl bg-surface-700/50 flex items-center justify-center mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-white mb-1">Экземпляры не настроены</h3>
      <p class="text-sm text-slate-400 max-w-sm mb-4">
        Подключите первый экземпляр Astra для мониторинга потоков и DVB-адаптеров.
      </p>
      <Button variant="secondary" size="sm" @click="openAddModal">Добавить подключение</Button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card
        v-for="inst in instances"
        :key="inst.index"
        :title="inst.label"
        class="relative overflow-hidden group hover:border-surface-600"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-white truncate max-w-[70%]">
              {{ inst.label }}
            </h3>
            <span
              :class="[
                'px-2 py-0.5 rounded-full text-xs font-semibold tracking-wide flex items-center gap-1.5',
                inst.online ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'
              ]"
            >
              <span :class="['w-1.5 h-1.5 rounded-full', inst.online ? 'bg-success animate-pulse-soft' : 'bg-danger']" />
              {{ inst.online ? 'Онлайн' : 'Офлайн' }}
            </span>
          </div>
        </template>

        <div class="mt-2 space-y-2 text-sm text-slate-350">
          <div class="flex justify-between">
            <span>Адрес:</span>
            <span class="font-mono text-white">{{ inst.host }}:{{ inst.port }}</span>
          </div>
          <div class="flex justify-between" v-if="inst.online">
            <span>Версия:</span>
            <span class="text-white">{{ inst.version }}</span>
          </div>
          <div class="flex justify-between" v-if="inst.last_seen > 0">
            <span>Опрос:</span>
            <span class="text-white">{{ formatTime(inst.last_seen) }}</span>
          </div>
          <div v-if="!inst.online && inst.error" class="mt-3 p-2 rounded bg-danger/10 border border-danger/20 text-xs text-danger break-words">
            {{ inst.error }}
          </div>
        </div>

        <div class="mt-6 pt-4 border-t border-surface-700/60 flex items-center justify-between gap-2">
          <div class="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              :disabled="!inst.online"
              :loading="reloadingIndex === inst.index"
              @click="reloadConfig(inst.index)"
              title="Перезагрузить конфигурацию"
            >
              Reload
            </Button>
            <Button
              variant="danger"
              size="sm"
              :disabled="!inst.online"
              :loading="exitingIndex === inst.index"
              @click="restartAstra(inst.index)"
              title="Перезапустить процесс Astra"
            >
              Restart
            </Button>
          </div>
          <div class="flex gap-1">
            <Button variant="ghost" size="sm" @click="openEditModal(inst)">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-slate-400 hover:text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </Button>
            <Button variant="ghost" size="sm" @click="deleteInstance(inst.index, inst.label)">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-danger/80 hover:text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </Button>
          </div>
        </div>
      </Card>
    </div>

    <!-- Модальное окно создания / редактирования -->
    <div v-if="modalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in-fast">
      <div class="w-full max-w-md p-6 rounded-xl border border-surface-700 bg-surface-800 shadow-xl space-y-6">
        <div>
          <h3 class="text-lg font-semibold text-white">
            {{ isEdit ? 'Редактировать экземпляр' : 'Добавить новый экземпляр' }}
          </h3>
          <p class="text-sm text-slate-400 mt-1">Параметры HTTP-соединения с astra-monitor</p>
        </div>

        <form @submit.prevent="submitForm" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Название (Label)</label>
            <input
              type="text"
              v-model="form.label"
              placeholder="Например, Astra Главный"
              class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-500 focus:outline-none focus:border-accent"
              required
            />
          </div>

          <div class="grid grid-cols-3 gap-4">
            <div class="col-span-2">
              <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">IP / Хост</label>
              <input
                type="text"
                v-model="form.host"
                placeholder="127.0.0.1"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-500 focus:outline-none focus:border-accent"
                required
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Порт API</label>
              <input
                type="number"
                v-model.number="form.port"
                placeholder="8000"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-500 focus:outline-none focus:border-accent"
                required
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Ключ API (ASTRA_API_KEY)</label>
            <input
              type="password"
              v-model="form.api_key"
              placeholder="Введите ключ доступа"
              class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-500 focus:outline-none focus:border-accent"
              required
            />
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-surface-700/60">
            <Button variant="ghost" size="sm" @click="closeModal">Отмена</Button>
            <Button variant="primary" size="sm" type="submit" :loading="submitting">
              {{ isEdit ? 'Сохранить' : 'Добавить' }}
            </Button>
          </div>
        </form>
      </div>
    </div>
    <!-- Модальное окно слепого сканирования -->
    <div v-if="scanModalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in-fast">
      <div class="w-full max-w-xl p-6 rounded-xl border border-surface-700 bg-surface-800 shadow-xl space-y-6 max-h-[90vh] overflow-y-auto">
        <div>
          <h3 class="text-lg font-semibold text-white">Слепое сканирование сети</h3>
          <p class="text-sm text-slate-400 mt-1">Автоматический поиск активных веб-интерфейсов Cesbo Astra</p>
        </div>

        <form @submit.prevent="startScanning" class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Подсеть (CIDR)</label>
              <input
                type="text"
                v-model="scanForm.subnet"
                placeholder="Например, 192.168.1.0/24"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-500 focus:outline-none focus:border-accent"
                required
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Порты API (через запятую)</label>
              <input
                type="text"
                v-model="scanForm.ports"
                placeholder="8000, 8001"
                class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-500 focus:outline-none focus:border-accent"
                required
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Ключ API для проверки (ASTRA_API_KEY)</label>
            <input
              type="text"
              v-model="scanForm.api_key"
              placeholder="test"
              class="w-full px-3 py-2 text-sm rounded-lg bg-surface-750 border border-surface-650 text-white placeholder-slate-500 focus:outline-none focus:border-accent"
              required
            />
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-surface-700/60">
            <Button variant="ghost" size="sm" @click="closeScanModal" :disabled="scanning">Закрыть</Button>
            <Button variant="primary" size="sm" type="submit" :loading="scanning">
              Начать сканирование
            </Button>
          </div>
        </form>

        <!-- Результаты сканирования -->
        <div v-if="scanning || scanResults.length > 0" class="space-y-3 pt-4 border-t border-surface-700/60">
          <h4 class="text-xs font-bold text-slate-450 uppercase tracking-wider">Результаты поиска</h4>
          
          <div v-if="scanning" class="flex flex-col items-center justify-center py-8 space-y-3 text-slate-400">
            <svg class="animate-spin h-8 w-8 text-accent" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span class="text-sm">Сканирование подсети... Это может занять несколько секунд</span>
          </div>

          <div v-else class="max-h-60 overflow-y-auto border border-surface-700 rounded-lg divide-y divide-surface-750/50">
            <div
              v-for="(item, idx) in scanResults"
              :key="idx"
              class="p-3 flex items-center justify-between hover:bg-surface-750/20 text-sm"
            >
              <div>
                <div class="font-semibold text-white font-mono">{{ item.host }}:{{ item.port }}</div>
                <div class="text-xs text-slate-400 mt-0.5">Версия Astra: {{ item.version }}</div>
              </div>
              <div>
                <span v-if="item.added" class="text-xs text-slate-500 font-medium">Добавлено</span>
                <Button
                  v-else
                  variant="primary"
                  size="sm"
                  class="h-7 px-2.5 text-xs"
                  :loading="addingScanIndex === idx"
                  @click="addScanResult(item, idx)"
                >
                  Добавить
                </Button>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="scanResults !== null && scanResults.length === 0 && !scanning" class="pt-4 border-t border-surface-700/60 text-center py-4 text-xs text-slate-500">
          Устройства Astra не найдены. Проверьте правильность подсети, портов и API ключа.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import http from '@/core/api'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'

interface InstanceItem {
  index: number
  host: string
  port: number
  api_key: string
  label: string
  online: boolean
  last_seen: number
  error: string | null
  version: string
}

const instances = ref<InstanceItem[]>([])
const loading = ref(true)
const reloadingIndex = ref<number | null>(null)
const exitingIndex = ref<number | null>(null)
const submitting = ref(false)

// Модальное окно
const modalOpen = ref(false)
const isEdit = ref(false)
const editIndex = ref<number | null>(null)
const form = ref({
  label: '',
  host: '',
  port: 8000,
  api_key: ''
})

// Состояние слепого сканирования
const scanModalOpen = ref(false)
const scanning = ref(false)
const scanForm = ref({
  subnet: '',
  ports: '8000',
  api_key: 'test'
})
const scanResults = ref<any[]>([])
const addingScanIndex = ref<number | null>(null)

let timer: any = null

async function loadData() {
  try {
    const { data } = await http.get('/api/v1/m/astra/instances')
    instances.value = data.items || []
  } catch (err) {
    console.error('Ошибка загрузки инстансов', err)
  } finally {
    loading.value = false
  }
}

async function reloadConfig(index: number) {
  reloadingIndex.value = index
  try {
    await http.post(`/api/v1/m/astra/instances/${index}/reload`)
    alert('Конфигурация успешно отправлена на перезапуск!')
  } catch (err: any) {
    alert(`Ошибка отправки reload: ${err?.response?.data?.detail || err.message}`)
  } finally {
    reloadingIndex.value = null
    loadData()
  }
}

async function restartAstra(index: number) {
  if (!confirm('Вы действительно хотите остановить (перезапустить) процесс Astra?')) return
  exitingIndex.value = index
  try {
    await http.post(`/api/v1/m/astra/instances/${index}/exit`)
    alert('Сигнал завершения процесса Astra успешно отправлен!')
  } catch (err: any) {
    alert(`Ошибка перезапуска: ${err?.response?.data?.detail || err.message}`)
  } finally {
    exitingIndex.value = null
    loadData()
  }
}

async function deleteInstance(index: number, label: string) {
  if (!confirm(`Вы действительно хотите удалить инстанс "${label}"?`)) return
  try {
    await http.delete(`/api/v1/m/astra/instances/${index}`)
    loadData()
  } catch (err: any) {
    alert(`Ошибка удаления инстанса: ${err?.response?.data?.detail || err.message}`)
  }
}

function openAddModal() {
  isEdit.value = false
  editIndex.value = null
  form.value = {
    label: '',
    host: '',
    port: 8000,
    api_key: 'test'
  }
  modalOpen.value = true
}

function openEditModal(inst: InstanceItem) {
  isEdit.value = true
  editIndex.value = inst.index
  form.value = {
    label: inst.label,
    host: inst.host,
    port: inst.port,
    api_key: inst.api_key
  }
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
}

async function submitForm() {
  submitting.value = true
  try {
    if (isEdit.value && editIndex.value !== null) {
      await http.put(`/api/v1/m/astra/instances/${editIndex.value}`, form.value)
    } else {
      await http.post('/api/v1/m/astra/instances', form.value)
    }
    closeModal()
    loadData()
  } catch (err: any) {
    alert(`Ошибка сохранения: ${err?.response?.data?.detail || err.message}`)
  } finally {
    submitting.value = false
  }
}

async function openScanModal() {
  scanModalOpen.value = true
  scanResults.value = []
  scanning.value = false
  try {
    const { data } = await http.get('/api/v1/m/astra/instances/local-subnet')
    scanForm.value.subnet = data.subnet || ''
  } catch (err) {
    console.error('Ошибка получения локальной подсети', err)
  }
}

function closeScanModal() {
  scanModalOpen.value = false
}

async function startScanning() {
  scanning.value = true
  scanResults.value = []
  try {
    const portsList = scanForm.value.ports
      .split(',')
      .map(p => parseInt(p.trim(), 10))
      .filter(p => !isNaN(p))
    
    const payload = {
      subnet: scanForm.value.subnet || null,
      ports: portsList.length > 0 ? portsList : [8000],
      api_key: scanForm.value.api_key || 'test',
      timeout: 1.0
    }
    const { data } = await http.post('/api/v1/m/astra/instances/scan', payload)
    
    const existing = new Set(instances.value.map(i => `${i.host}:${i.port}`))
    scanResults.value = (data.items || []).map((item: any) => ({
      ...item,
      added: existing.has(`${item.host}:${item.port}`)
    }))
  } catch (err: any) {
    alert(`Ошибка сканирования: ${err?.response?.data?.detail || err.message}`)
  } finally {
    scanning.value = false
  }
}

async function addScanResult(item: any, idx: number) {
  addingScanIndex.value = idx
  try {
    await http.post('/api/v1/m/astra/instances', {
      label: item.label,
      host: item.host,
      port: item.port,
      api_key: item.api_key
    })
    item.added = true
    loadData()
  } catch (err: any) {
    alert(`Ошибка добавления: ${err?.response?.data?.detail || err.message}`)
  } finally {
    addingScanIndex.value = null
  }
}

function formatTime(timestamp: number): string {
  if (!timestamp) return 'никогда'
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString()
}

onMounted(() => {
  loadData()
  timer = setInterval(loadData, 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
