<template>
  <div class="bg-surface-800/60 rounded-xl border border-surface-700 p-5 shadow-sm">
    <div class="flex items-center justify-between mb-4 border-b border-surface-700/80 pb-3">
      <h4 class="text-sm font-semibold text-white">Тест Стриминга</h4>
      <div 
        v-if="loading" 
        class="w-4 h-4 border-2 border-accent/40 border-t-accent rounded-full animate-spin"
      ></div>
    </div>

    <!-- Область предпросмотра (Сетка плееров) -->
    <div 
      class="w-full bg-black rounded-lg overflow-hidden mb-4 relative min-h-[200px]"
      :class="[
        streamResults.length > 1 ? 'grid grid-cols-1 md:grid-cols-2 gap-2 p-2' : 'flex items-center justify-center aspect-video'
      ]"
    >
      <template v-if="streamResults.length > 0">
        <div 
          v-for="res in streamResults" 
          :key="res.stream_id" 
          class="relative bg-surface-900 rounded overflow-hidden aspect-video border border-surface-700 group"
        >
          <VideoPlayer 
            :url="res.output_url || ''" 
            :type="res.output_type || 'auto'" 
            :metadata="res.metadata"
            :muted="true"
            class="w-full h-full"
          />
          <div class="absolute top-1 left-1 bg-black/60 px-1.5 py-0.5 rounded text-[9px] text-white backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity">
            {{ res.output_type?.toUpperCase() || 'AUTO' }}
          </div>
          <button 
            @click="stopStreamById(res.stream_id)"
            class="absolute top-1 right-1 bg-red-500/80 hover:bg-red-500 text-white p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
            title="Остановить этот поток"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </template>
      <div v-else-if="error" class="p-4 text-red-400 text-xs text-center">{{ error }}</div>
      <div v-else class="text-slate-500 text-sm">Нет активных потоков</div>
    </div>

    <form @submit.prevent="runStream" class="space-y-4">
      <div>
        <div class="flex items-center justify-between mb-1">
          <label class="block text-xs font-medium text-slate-400">Source URL</label>
          <div class="relative group">
            <button 
              type="button"
              class="text-[10px] text-accent hover:text-accent/80 flex items-center gap-1 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
              Пресеты
            </button>
            <div class="absolute right-0 top-full pt-1 w-64 z-50 hidden group-hover:block blur-none">
              <div class="bg-surface-700 border border-surface-600 rounded-md shadow-xl py-1">
                <div v-for="group in presetGroups" :key="group.name">
                  <div class="px-3 py-1 text-[10px] uppercase tracking-wider text-slate-500 bg-surface-800/50">{{ group.name }}</div>
                  <button 
                    v-for="preset in group.items" 
                    :key="preset.url"
                    type="button"
                    @click="applyPreset(preset)"
                    class="w-full text-left px-3 py-1.5 text-xs text-slate-300 hover:bg-surface-600 hover:text-white transition-colors flex justify-between items-center"
                  >
                    <span>{{ preset.name }}</span>
                    <span class="text-[9px] px-1 bg-surface-800 rounded text-slate-500">{{ preset.proto }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <input 
          v-model="testSourceUrl"
          type="text" 
          placeholder="http://.../stream.ts"
          class="w-full px-3 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          required
        />
      </div>

      <div class="mb-3">
        <label class="block text-xs font-medium text-slate-400 mb-1">Бэкенд</label>
        <select 
          v-model="testBackend"
          class="w-full px-2 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
        >
          <option v-for="opt in backendOptions" :key="opt" :value="opt">{{ opt }}</option>
        </select>
        <div v-if="currentSupportedProtocols.length > 0" class="mt-1 text-[10px] text-slate-500 truncate" :title="currentSupportedProtocols.join(', ')">
          Протоколы: {{ currentSupportedProtocols.join(', ') }}
        </div>
      </div>

      <div class="flex flex-col gap-2 pt-2">
        <button 
          type="submit"
          class="w-full bg-accent/20 hover:bg-accent/30 text-accent font-medium text-xs px-3 py-2 rounded transition-colors"
          :disabled="loading || testBackend === 'auto'"
        >
          {{ testBackend === 'auto' ? 'Выберите бэкенд для тестирования' : 'Протестировать все выходные форматы' }}
        </button>

        <button 
          v-if="streamResults.length > 0"
          type="button"
          @click="stopAllStreams"
          class="w-full bg-red-500/20 hover:bg-red-500/30 text-red-400 font-medium text-xs px-3 py-2 rounded transition-colors"
          :disabled="loading"
        >
          Остановить Все ({{ streamResults.length }})
        </button>
      </div>
    </form>


    <details v-if="streamResults.length > 0" class="mt-4 text-xs">
      <summary class="text-slate-400 cursor-pointer hover:text-white">Показать Result JSON ({{ streamResults.length }})</summary>
      <div class="mt-2 space-y-2">
        <pre v-for="res in streamResults" :key="res.stream_id" class="p-2 bg-surface-900 rounded overflow-x-auto text-slate-300">{{ JSON.stringify(res, null, 2) }}</pre>
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import VideoPlayer from '@/components/ui/VideoPlayer.vue'
import api from '@/core/api'

const props = defineProps<{
  schema: any
  backendField: any
  formatField: any
}>()

const testSourceUrl = ref('http://31.130.202.110/httpts/tv3by/avchigh.ts')
const testBackend = ref('auto')

const loading = ref(false)
const error = ref('')
const streamResults = ref<any[]>([])
const backendInfo = ref<any[]>([])

async function loadBackendInfo() {
  try {
    const res = await api.get('/api/modules/stream/v1/backends')
    backendInfo.value = res.data.backends
  } catch (e) {
    console.warn('Failed to load backend info', e)
  }
}

const currentSupportedProtocols = computed(() => {
  if (testBackend.value === 'auto') {
    const all = new Set<string>()
    backendInfo.value.forEach(b => {
      if (b.supported_protocols) b.supported_protocols.forEach((p: string) => all.add(p))
    })
    return Array.from(all).sort()
  }
  const b = backendInfo.value.find(x => x.id === testBackend.value)
  return (b?.supported_protocols || []).slice().sort()
})

// Пресеты для быстрого тестирования
const presetGroups = [
  {
    name: 'Локальные (test_signal_generator.py)',
    items: [
      { name: 'UDP Multicast', url: 'udp://239.0.0.1:1234', proto: 'UDP' },
      { name: 'RTP', url: 'rtp://239.0.0.1:1235', proto: 'RTP' },
      { name: 'HTTP-TS', url: 'http://127.0.0.1:8081/test.ts', proto: 'HTTP' },
      { name: 'HTTP (No Ext)', url: 'http://127.0.0.1:8080/test', proto: 'HTTP' },
      { name: 'HLS Live', url: 'http://127.0.0.1:8888/test_hls/index.m3u8', proto: 'HLS' },

      { name: 'RTSP', url: 'rtsp://127.0.0.1:8554/test_rtsp', proto: 'RTSP' },
      { name: 'SRT (Read)', url: 'srt://127.0.0.1:8890?streamid=read:test_srt', proto: 'SRT' },
      { name: 'RTMP', url: 'rtmp://127.0.0.1:1935/test_rtmp', proto: 'RTMP' },
      { name: 'TCP (MPEG-TS)', url: 'tcp://127.0.0.1:1236', proto: 'TCP' },
      { name: 'RIST', url: 'rist://127.0.0.1:1238', proto: 'RIST' },
    ]
  },
  {
    name: 'Публичные / Тестовые',
    items: [
      { name: 'UDP Ростелеком', url: 'udp://224.100.100.19:1234', proto: 'UDP' },
      { name: 'Big Buck Bunny (HLS)', url: 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8', proto: 'HLS' },
      { name: 'Apple Test (HLS)', url: 'https://devimages.apple.com.edgekey.net/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8', proto: 'HLS' },
      { name: 'TV3 (HTTP-TS)', url: 'http://31.130.202.110/httpts/tv3by/avchigh.ts', proto: 'HTTP' },
      { name: 'RTSP Example', url: 'rtsp://rtspstream.com/pattern', proto: 'RTSP' },
      { name: 'RTMP Example', url: 'rtmp://127.0.0.1/live/test', proto: 'RTMP' },
    ]
  }
]

function applyPreset(preset: any) {
  testSourceUrl.value = preset.url
}

// Опции для бэкенда (обычно не фильтруются)
const backendOptions = computed(() => props.backendField?.enum || ['auto'])

// Форматы, доступные для тестирования (вычисляются на основе бэкенда)
const availableFormats = computed(() => {
  if (!props.formatField?.enum) return []
  
  let currentEnum = [...props.formatField.enum]
  const schema = props.schema

  if (schema?.allOf) {
    for (const rule of schema.allOf) {
      if (!rule.if?.properties || !rule.then?.properties) continue
      
      let match = true
      const ifProps = rule.if.properties
      if (ifProps[props.backendField.name]) {
        const cond = ifProps[props.backendField.name]
        const val = testBackend.value
        if (cond.const !== undefined && val !== cond.const) match = false
        if (cond.enum !== undefined && !cond.enum.includes(val)) match = false
      } else {
        match = false
      }
      
      if (match) {
        const thenProps = rule.then.properties
        if (thenProps[props.formatField.name]?.enum) {
          const allowed = thenProps[props.formatField.name].enum
          currentEnum = currentEnum.filter(v => allowed.includes(v))
        }
      }
    }
  }

  return currentEnum.filter(f => f !== 'auto')
})

async function stopStreamById(sid: string) {
  try {
    await api.post(`/api/modules/stream/v1/stop?stream_id=${encodeURIComponent(sid)}`)
    const index = streamResults.value.findIndex(r => r.stream_id === sid)
    if (index !== -1) {
      streamResults.value.splice(index, 1)
    }
  } catch (err) {
    console.warn(`Failed to stop stream ${sid}:`, err)
    // Все равно удаляем из UI, чтобы не "висело", если сервер не отвечает
    const index = streamResults.value.findIndex(r => r.stream_id === sid)
    if (index !== -1) {
      streamResults.value.splice(index, 1)
    }
  }
}

async function stopAllStreams() {
  const ids = streamResults.value.map(r => r.stream_id)
  loading.value = true
  error.value = ''
  
  try {
    // Останавливаем все параллельно и ждем завершения
    await Promise.all(ids.map(sid => 
      api.post(`/api/modules/stream/v1/stop?stream_id=${encodeURIComponent(sid)}`)
         .catch(err => console.warn(`Failed to stop stream ${sid}:`, err))
    ))
  } finally {
    streamResults.value = []
    loading.value = false
  }
}

async function startSingleStreamFormat(url: string, format: string) {
  try {
    const params = new URLSearchParams()
    params.set('url', url)
    params.set('output_type', format)
    if (testBackend.value !== 'auto') params.set('backend', testBackend.value)

    const response = await api.post(`/api/modules/stream/v1/start?${params.toString()}`)
    
    let res = response.data
    if (res.output_url && res.output_url.startsWith('/')) {
        res.output_url = window.location.origin + res.output_url
    }
    
    streamResults.value.push(res)
  } catch (err: any) {
    const errorMsg = err?.response?.data?.detail || err.message || 'Сбой запуска стрима'
    error.value = error.value ? `${error.value}\n${format}: ${errorMsg}` : `${format}: ${errorMsg}`
  }
}

async function runStream() {
  if (testBackend.value === 'auto' || !testSourceUrl.value) return
  
  const formats = availableFormats.value
  if (formats.length === 0) return

  // Останавливаем предыдущие перед запуском новых (если требуется обновлять список)
  if (streamResults.value.length > 0) {
    await stopAllStreams()
  }

  loading.value = true
  error.value = ''

  for (const format of formats) {
    await startSingleStreamFormat(testSourceUrl.value, format)
  }
  
  loading.value = false
}



onMounted(() => {
  loadBackendInfo()
})

onBeforeUnmount(() => {
  stopAllStreams()
})
</script>
