<template>
  <div class="bg-surface-800/60 rounded-xl border border-surface-700 p-5 shadow-sm">
    <div class="flex items-center justify-between mb-4 border-b border-surface-700/80 pb-3">
      <h4 class="text-sm font-semibold text-white">Тест Превью</h4>
      <div 
        v-if="loading" 
        class="w-4 h-4 border-2 border-accent/40 border-t-accent rounded-full animate-spin"
      ></div>
    </div>

    <!-- Область предпросмотра -->
    <div class="w-full aspect-video bg-black rounded-lg overflow-hidden mb-4 relative flex items-center justify-center border border-surface-700">
      <template v-if="previewUrl">
        <img :src="previewUrl" alt="Preview Result" class="w-full h-full object-contain" @error="handleImgError" />
        <div class="absolute bottom-2 right-2 bg-black/60 px-2 py-1 rounded text-[10px] text-white backdrop-blur-sm">
          {{ previewFormat.toUpperCase() }}
        </div>
      </template>
      <div v-else class="text-slate-500 text-sm flex flex-col items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span>Превью не сгенерировано</span>
      </div>
    </div>

    <form @submit.prevent="runPreview" class="space-y-4">
      <div>
        <div class="flex items-center justify-between mb-1">
          <label class="block text-xs font-medium text-slate-400">Source URL (Превью)</label>
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
          v-model="previewSourceUrl"
          type="text" 
          placeholder="http://.../stream.ts"
          class="w-full px-3 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          required
        />
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Бэкенд</label>
          <select 
            v-model="previewBackend"
            class="w-full px-2 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          >
            <option v-for="opt in backendOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Формат картинки</label>
          <select 
            v-model="previewFormat"
            class="w-full px-2 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          >
            <option v-for="opt in formatOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </div>
      </div>

      <div class="flex gap-2 pt-2">
        <button 
          type="submit"
          class="flex-1 bg-surface-700 hover:bg-surface-600 text-white font-medium text-xs px-3 py-2 rounded transition-colors"
          :disabled="loading"
        >
          Сгенерировать Preview
        </button>
      </div>
    </form>

    <div v-if="error" class="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400 break-words">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import api from '@/core/api'

const props = defineProps<{
  schema: any
  backendField: any
  formatField: any
}>()

const previewSourceUrl = ref('http://31.130.202.110/httpts/tv3by/avchigh.ts')
const previewBackend = ref('auto')
const previewFormat = ref('jpeg')

const loading = ref(false)
const error = ref('')
const previewUrl = ref('')

// Пресеты для быстрого тестирования превью
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
    ]
  },
  {
    name: 'Публичные / Тестовые',
    items: [
      { name: 'Big Buck Bunny (HLS)', url: 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8', proto: 'HLS' },
      { name: 'Apple Test (HLS)', url: 'https://devimages.apple.com.edgekey.net/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8', proto: 'HLS' },
      { name: 'TV3 (HTTP-TS)', url: 'http://31.130.202.110/httpts/tv3by/avchigh.ts', proto: 'HTTP' },
      { name: 'RTSP Example', url: 'rtsp://rtspstream.com/pattern', proto: 'RTSP' },
      { name: 'RTMP Example', url: 'rtmp://127.0.0.1/live/test', proto: 'RTMP' },
    ]
  }
]

function applyPreset(preset: any) {
  previewSourceUrl.value = preset.url
}

// Опции для бэкенда
const backendOptions = computed(() => props.backendField?.enum || ['auto'])

// Опции для формата (ФИЛЬТРУЮТСЯ ПО БЭКЕНДУ)
const formatOptions = computed(() => {
  if (!props.formatField?.enum) return ['auto']
  
  let currentEnum = [...props.formatField.enum]
  const schema = props.schema

  if (schema?.allOf) {
    for (const rule of schema.allOf) {
      if (!rule.if?.properties || !rule.then?.properties) continue
      
      let match = true
      const ifProps = rule.if.properties
      if (ifProps[props.backendField.name]) {
        const cond = ifProps[props.backendField.name]
        const val = previewBackend.value
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

  return currentEnum
})

// Сброс формата при несовместимости
watch(formatOptions, (newOpts) => {
  if (!newOpts.includes(previewFormat.value)) {
    previewFormat.value = newOpts.includes('auto') ? 'auto' : newOpts[0]
  }
})

function handleImgError() {
  error.value = 'Ошибка загрузки изображения. Возможно, формат не поддерживается браузером или бэкендом.'
  previewUrl.value = ''
}

async function runPreview() {
  if (!previewSourceUrl.value) return
  previewUrl.value = ''
  error.value = ''
  loading.value = true
  
  try {
    const params = new URLSearchParams()
    params.set('url', previewSourceUrl.value)
    params.set('format', previewFormat.value)
    params.set('width', '640')
    params.set('quality', '75')

    if (previewBackend.value !== 'auto') {
      params.set('backend', previewBackend.value)
    }

    // Используем выделенный эндпоинт для синхронной генерации (debug)
    // Сначала проверяем доступность через api (чтобы поймать ошибки JSON)
    await api.get(`/api/modules/stream/v1/preview/debug?${params.toString()}`)
    
    // Если успешно, формируем URL для <img> (добавляем t для обхода кэша)
    const host = window.location.origin
    previewUrl.value = `${host}/api/modules/stream/v1/preview/debug?${params.toString()}&t=${Date.now()}`
    
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err.message || 'Сбой генерации превью'
    previewUrl.value = ''
  } finally {
    loading.value = false
  }
}
</script>
