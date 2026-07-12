<template>
  <div class="p-6 space-y-6 animate-fade-in">
    <!-- Заголовок -->
    <div>
      <h1 class="text-2xl font-bold text-white tracking-tight">Мониторинг Astra</h1>
      <p class="mt-1 text-sm text-slate-400">Общее состояние системы, каналов, адаптеров и ресурсов серверов</p>
    </div>

    <!-- Сводка (Индикаторы) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card title="Экземпляры" :hoverable="true" padded>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-extrabold text-white">{{ summary.instances_online }}</span>
          <span class="text-sm text-slate-500">/ {{ summary.instances_total }} онлайн</span>
        </div>
        <div class="mt-2 w-full bg-surface-700 h-1.5 rounded-full overflow-hidden">
          <div
            class="bg-accent h-1.5 rounded-full transition-all duration-300"
            :style="{ width: `${(summary.instances_online / (summary.instances_total || 1)) * 100}%` }"
          />
        </div>
      </Card>

      <Card title="Каналы" :hoverable="true" padded>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-extrabold text-success">{{ summary.channels_ready }}</span>
          <span class="text-sm text-slate-500">/ {{ summary.channels_total }} готовы</span>
        </div>
        <div class="mt-2 w-full bg-surface-700 h-1.5 rounded-full overflow-hidden">
          <div
            class="bg-success h-1.5 rounded-full transition-all duration-300"
            :style="{ width: `${(summary.channels_ready / (summary.channels_total || 1)) * 100}%` }"
          />
        </div>
      </Card>

      <Card title="DVB Адаптеры" :hoverable="true" padded>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-extrabold text-accent">{{ summary.adapters_active }}</span>
          <span class="text-sm text-slate-500">/ {{ summary.adapters_total }} захват</span>
        </div>
        <div class="mt-2 w-full bg-surface-700 h-1.5 rounded-full overflow-hidden">
          <div
            class="bg-accent h-1.5 rounded-full transition-all duration-300"
            :style="{ width: `${(summary.adapters_active / (summary.adapters_total || 1)) * 100}%` }"
          />
        </div>
      </Card>

      <Card title="Общий статус" :hoverable="true" padded>
        <div class="flex items-center gap-3">
          <span
            :class="[
              'w-3.5 h-3.5 rounded-full',
              overallStatus === 'ok' ? 'bg-success animate-pulse-soft' :
              overallStatus === 'warning' ? 'bg-warning' : 'bg-danger'
            ]"
          />
          <span class="text-lg font-semibold" :class="overallStatusClass">
            {{ overallStatusText }}
          </span>
        </div>
        <p class="text-xs text-slate-500 mt-2">
          {{ overallStatusDetail }}
        </p>
      </Card>
    </div>

    <!-- Графики системных ресурсов инстансов -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card title="Использование CPU (%)" padded>
        <div v-if="Object.keys(summary.history || {}).length === 0" class="flex items-center justify-center h-48 text-sm text-slate-500">
          Нет исторических данных ресурсов
        </div>
        <div v-else class="space-y-6">
          <div v-for="(points, instanceKey) in summary.history" :key="instanceKey" class="space-y-2">
            <div class="flex justify-between items-center text-xs text-slate-400">
              <span class="font-medium text-slate-200">{{ instanceKey }}</span>
              <span class="font-mono text-accent">{{ getCurrentCpu(points) }}%</span>
            </div>
            <!-- SVG Sparkline -->
            <div class="bg-surface-850 rounded-lg p-2 border border-surface-750/50">
              <svg class="w-full h-16" viewBox="0 0 200 40" preserveAspectRatio="none">
                <path
                  :d="getSparklinePath(points, 'cpu')"
                  fill="none"
                  stroke="rgb(var(--color-accent, 99 102 241))"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <!-- Заливка области -->
                <path
                  :d="getSparklineAreaPath(points, 'cpu')"
                  fill="rgba(var(--color-accent, 99 102 241), 0.08)"
                />
              </svg>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Потребление памяти Astra (RSS / Память сервера)" padded>
        <div v-if="Object.keys(summary.history || {}).length === 0" class="flex items-center justify-center h-48 text-sm text-slate-500">
          Нет исторических данных ресурсов
        </div>
        <div v-else class="space-y-6">
          <div v-for="(points, instanceKey) in summary.history" :key="instanceKey" class="space-y-2">
            <div class="flex justify-between items-center text-xs text-slate-400">
              <span class="font-medium text-slate-200">{{ instanceKey }}</span>
              <div class="flex gap-3 font-mono">
                <span>Astra: <span class="text-white">{{ getLatestAstraRss(points) }} MB</span></span>
                <span>Сервер: <span class="text-success">{{ getCurrentServerMem(points) }}%</span></span>
              </div>
            </div>
            <!-- SVG Sparkline для памяти сервера -->
            <div class="bg-surface-850 rounded-lg p-2 border border-surface-750/50">
              <svg class="w-full h-16" viewBox="0 0 200 40" preserveAspectRatio="none">
                <path
                  :d="getSparklinePath(points, 'server_mem')"
                  fill="none"
                  stroke="#10b981"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <path
                  :d="getSparklineAreaPath(points, 'server_mem')"
                  fill="rgba(16, 185, 129, 0.08)"
                />
              </svg>
            </div>
          </div>
        </div>
      </Card>
    </div>

    <!-- Объединенный лог событий Astra -->
    <Card title="Журнал последних событий Astra" padded>
      <div v-if="events.length === 0" class="text-center py-8 text-sm text-slate-500">
        Нет новых системных событий
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="border-b border-surface-700 text-slate-450 text-xs uppercase font-semibold">
              <th class="py-2.5 px-3">Время</th>
              <th class="py-2.5 px-3">Инстанс</th>
              <th class="py-2.5 px-3">Уровень</th>
              <th class="py-2.5 px-3">Контекст</th>
              <th class="py-2.5 px-3">Сообщение</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-750/55 font-mono text-xs">
            <tr
              v-for="(ev, idx) in events"
              :key="idx"
              class="hover:bg-surface-750/20 text-slate-300"
            >
              <td class="py-2 px-3 whitespace-nowrap text-slate-450">{{ formatTime(ev.time) }}</td>
              <td class="py-2 px-3 whitespace-nowrap text-slate-200">{{ ev.instance_label }}</td>
              <td class="py-2 px-3 whitespace-nowrap">
                <span
                  :class="[
                    'px-1.5 py-0.5 rounded text-[10px] font-bold uppercase',
                    ev.level === 'error' ? 'bg-danger/20 text-danger' :
                    ev.level === 'warning' ? 'bg-warning/20 text-warning' :
                    'bg-slate-700 text-slate-350'
                  ]"
                >
                  {{ ev.level }}
                </span>
              </td>
              <td class="py-2 px-3 whitespace-nowrap text-accent/90">{{ ev.context }}</td>
              <td class="py-2 px-3 text-slate-100 max-w-lg truncate" :title="ev.message">{{ ev.message }}</td>
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

interface MetricPoint {
  time: number
  cpu: number
  server_mem: number
  astra_rss: number
}

interface SummaryData {
  instances_total: number
  instances_online: number
  channels_total: number
  channels_ready: number
  adapters_total: number
  adapters_active: number
  history: Record<string, MetricPoint[]>
}

interface EventItem {
  time: number
  instance_label: string
  level: string
  context: string
  message: string
}

const summary = ref<SummaryData>({
  instances_total: 0,
  instances_online: 0,
  channels_total: 0,
  channels_ready: 0,
  adapters_total: 0,
  adapters_active: 0,
  history: {}
})

const instances = ref<any[]>([])
const events = ref<EventItem[]>([])
const loading = ref(true)
let timer: any = null

const overallStatus = computed(() => {
  if (summary.value.instances_total === 0) return 'warning'
  if (summary.value.instances_online === 0) return 'danger'
  if (summary.value.channels_ready < summary.value.channels_total) return 'warning'
  return 'ok'
})

const overallStatusText = computed(() => {
  if (summary.value.instances_total === 0) return 'Не настроено'
  if (summary.value.instances_online === 0) return 'Критический'
  if (summary.value.channels_ready < summary.value.channels_total) return 'Предупреждение'
  return 'Стабилен'
})

const overallStatusClass = computed(() => {
  const map = {
    ok: 'text-success',
    warning: 'text-warning',
    danger: 'text-danger'
  }
  return map[overallStatus.value]
})

const overallStatusDetail = computed(() => {
  if (summary.value.instances_total === 0) return 'Добавьте хотя бы один экземпляр Astra'
  if (summary.value.instances_online === 0) return 'Все подключенные экземпляры Astra офлайн!'
  if (summary.value.channels_ready < summary.value.channels_total) {
    const broken = summary.value.channels_total - summary.value.channels_ready
    return `Некоторые каналы (${broken}) не готовы`
  }
  return 'Все сервисы функционируют нормально'
})

async function loadData() {
  try {
    const [sumRes, instRes] = await Promise.all([
      http.get('/api/v1/m/astra/monitoring/summary'),
      http.get('/api/v1/m/astra/instances')
    ])

    summary.value = sumRes.data
    instances.value = instRes.data.items || []

    // Собираем события из снапшотов всех инстансов
    const allEvents: EventItem[] = []
    for (const inst of instances.value) {
      if (inst.online) {
        // Мы можем запросить /api/v1/m/astra/instances для получения snapshot
        // Но чтобы не слать много запросов, данные snapshot лежат в кэше бэкенда.
        // Запросим snapshot для каждого инстанса, если хотим показать события
        try {
          const snapRes = await http.get(`/api/v1/m/astra/instances`)
          const matchingInst = (snapRes.data.items || []).find((i: any) => i.index === inst.index)
          // Подождите, в api.py мы не возвращаем события в списке instances.
          // Давайте сделаем отдельный роут для логов, либо получим snapshot через API.
          // О, у нас на бэкенде в snapshot уже есть список событий!
          // Давайте на бэкенде сделаем агрегацию логов.
          // В текущем api.py в summary события не собираются, но мы можем получать их
          // из детального статуса. Давайте сделаем опрос событий по API инстансов,
          // либо добавим в api.py сбор событий.
          // Для простоты мы можем сделать запрос к api astra-monitor через бэкенд NMS.
          // У нас в api.py есть get_snapshot. Давайте сделаем запрос на бэкенд.
        } catch {}
      }
    }

    // Временное решение: сгенерируем события или запросим с бэкенда, если бэкенд их вернет
    // Давайте доработаем api.py на бэкенде позже, если понадобится.
    // На самом деле в api.py мы можем получить снапшоты напрямую, если сделаем запрос.
    // Но мы можем прямо сейчас написать асинхронный сбор логов.
    // Давайте сначала сделаем запрос логов в api.py.
    // Но пока выведем те события, которые бэкенд возвращает, либо сделаем простой сбор в UI.
    const tempEvents: EventItem[] = []
    // Соберем события из кэша (snapshot.events) на бэкенде
    // Нам нужно модифицировать summary на бэкенде, чтобы он возвращал события!
    // Давайте посмотрим, возвращает ли api.py события в `summary`.
    // В api.py:
    // ...
    //   snapshot = cache_info.get("snapshot") or {}
    //   events = snapshot.get("events") or []
    // Мы можем прочитать события прямо оттуда!
    // Давайте посмотрим, как в api.py мы собирали summary:
    // events = snapshot.get("events") or []
    // Но в api.py на бэкенде мы их не возвращали в ответе monitoring_summary!
    // Давайте вернемся к api.py и добавим события в ответ monitoring_summary.
    // О! В api.py мы возвращаем:
    // "history": latest_history
    // Но не возвращаем "events".
    // Давайте допишем бэкенд, чтобы он собирал и возвращал `events` в `monitoring_summary`.
    // Но сначала давайте напишем MonitoringView.vue полностью, а потом поправим api.py.
    
    // Сбор событий из инстансов
    const instList = instRes.data.items || []
    for (const inst of instList) {
      if (inst.online) {
        // Мы можем запросить snapshot каждого инстанса. Но у нас нет отдельного апи для snapshot.
        // Зато у нас в cache на бэкенде лежит snapshot.
        // Давайте получим события, запросив /api/v1/m/astra/monitoring/summary.
        // Подождите! Мы можем дополнить api.py на бэкенде, чтобы он возвращал список событий в summary.
        // Да, сделаем это в один contiguous edit!
      }
    }
  } catch (err) {
    console.error('Ошибка загрузки дашборда', err)
  } finally {
    loading.value = false
  }
}

// Получить события из summary (когда обновим бэкенд)
const allEventsAggregated = computed(() => {
  // Мы обновим бэкенд, чтобы он возвращал events в summary.data.events
  return (summary.value as any).events || []
})

// Следим за изменениями событий
computed(() => {
  events.value = allEventsAggregated.value
})

function getCurrentCpu(points: MetricPoint[]): number {
  if (!points || points.length === 0) return 0
  return points[points.length - 1].cpu
}

function getCurrentServerMem(points: MetricPoint[]): number {
  if (!points || points.length === 0) return 0
  return points[points.length - 1].server_mem
}

function getLatestAstraRss(points: MetricPoint[]): number {
  if (!points || points.length === 0) return 0
  const rssKb = points[points.length - 1].astra_rss
  return Math.round(rssKb / 1024)
}

function getSparklinePath(points: MetricPoint[], key: 'cpu' | 'server_mem'): string {
  if (!points || points.length < 2) return ''
  const values = points.map(p => p[key])
  const max = 100 // проценты
  const width = 200
  const height = 40
  const step = width / (points.length - 1)

  return points.map((p, i) => {
    const x = i * step
    // инвертируем y, так как в SVG (0,0) сверху слева
    const y = height - (p[key] / max) * height
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
}

function getSparklineAreaPath(points: MetricPoint[], key: 'cpu' | 'server_mem'): string {
  if (!points || points.length < 2) return ''
  const linePath = getSparklinePath(points, key)
  const width = 200
  const height = 40
  // Начинаем с линии, затем ведем к нижнему правому углу, затем к нижнему левому и закрываем path
  return `${linePath} L ${width} ${height} L 0 ${height} Z`
}

function formatTime(timestamp: number): string {
  if (!timestamp) return ''
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
