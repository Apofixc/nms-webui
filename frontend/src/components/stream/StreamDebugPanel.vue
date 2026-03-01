<template>
  <div class="bg-surface-800/60 rounded-xl border border-surface-700 p-5 shadow-sm">
    <div class="flex items-center justify-between mb-4 border-b border-surface-700/80 pb-3">
      <div class="flex gap-4">
        <button 
          @click="activeTab = 'stream'" 
          :class="['text-base font-semibold pb-3 -mb-3', activeTab === 'stream' ? 'text-white border-b-2 border-accent' : 'text-slate-500 hover:text-slate-300']"
        >
          Тест Стриминга
        </button>
        <button 
          @click="activeTab = 'preview'" 
          :class="['text-base font-semibold pb-3 -mb-3', activeTab === 'preview' ? 'text-white border-b-2 border-accent' : 'text-slate-500 hover:text-slate-300']"
        >
          Тест Превью
        </button>
      </div>
      <div 
        v-if="loading" 
        class="w-4 h-4 border-2 border-accent/40 border-t-accent rounded-full animate-spin"
      ></div>
    </div>

    <!-- Область предпросмотра -->
    <div class="w-full aspect-video bg-black rounded-lg overflow-hidden mb-4 relative flex items-center justify-center">
      <template v-if="mode === 'stream' && streamResult">
        <VideoPlayer 
          :url="streamResult.output_url" 
          :type="streamResult.output_type" 
          :metadata="streamResult.metadata"
          :muted="true"
        />
      </template>
      <template v-else-if="mode === 'preview' && previewUrl">
        <img :src="previewUrl" alt="Preview" class="w-full h-full object-contain" />
      </template>
      <div v-else class="text-slate-500 text-sm">Нет медиа</div>
    </div>
    </div>

    <form v-if="activeTab === 'stream'" @submit.prevent="runStream" class="space-y-4">
      <div>
        <label class="block text-xs font-medium text-slate-400 mb-1">Source URL</label>
        <input 
          v-model="sourceUrl"
          type="text" 
          placeholder="http://.../varjag.ts"
          class="w-full px-3 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          required
        />
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Бэкенд</label>
          <select 
            v-model="backend"
            class="w-full px-2 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          >
            <option value="auto">auto</option>
            <option value="pure_proxy">pure_proxy</option>
            <option value="pure_webrtc">pure_webrtc</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Формат выхода</label>
          <select 
            v-model="outputType"
            class="w-full px-2 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          >
            <option value="auto">auto</option>
            <option value="hls">hls</option>
            <option value="http_ts">http_ts</option>
            <option value="webrtc">webrtc</option>
            <option value="http">http (raw)</option>
          </select>
        </div>
      </div>

      <div class="flex gap-2 pt-2">
        <button 
          type="submit"
          class="flex-1 bg-accent/20 hover:bg-accent/30 text-accent font-medium text-xs px-3 py-2 rounded transition-colors"
        >
          Запустить Stream
        </button>
      </div>
    </form>

    <form v-if="activeTab === 'preview'" @submit.prevent="runPreview" class="space-y-4">
      <div>
        <label class="block text-xs font-medium text-slate-400 mb-1">Source URL (Превью)</label>
        <input 
          v-model="previewSourceUrl"
          type="text" 
          placeholder="http://.../varjag.ts"
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
            <option value="auto">auto</option>
            <option value="pure_preview">pure_preview</option>
            <option value="ffmpeg">ffmpeg</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Формат картинки</label>
          <select 
            v-model="previewFormat"
            class="w-full px-2 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          >
            <option value="jpeg">jpeg</option>
            <option value="png">png</option>
            <option value="webp">webp</option>
          </select>
        </div>
      </div>

      <div class="flex gap-2 pt-2">
        <button 
          type="submit"
          class="flex-1 bg-surface-700 hover:bg-surface-600 text-white font-medium text-xs px-3 py-2 rounded transition-colors"
        >
          Сгенерировать Preview
        </button>
      </div>
    </form>

    <div v-if="error" class="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400 break-words">
      {{ error }}
    </div>

    <!-- Результирующий JSON -->
    <details v-if="streamResult" class="mt-4 text-xs">
      <summary class="text-slate-400 cursor-pointer hover:text-white">Показать Result JSON</summary>
      <pre class="mt-2 p-2 bg-surface-900 rounded overflow-x-auto text-slate-300">{{ JSON.stringify(streamResult, null, 2) }}</pre>
    </details>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import VideoPlayer from '@/components/ui/VideoPlayer.vue'
import api from '@/core/api'

const activeTab = ref<'stream' | 'preview'>('stream')

// Настройки стрима
const sourceUrl = ref('http://31.130.202.110/httpts/tv3by/avchigh.ts')
const backend = ref('auto')
const outputType = ref('auto')

// Настройки превью
const previewSourceUrl = ref('http://31.130.202.110/httpts/tv3by/avchigh.ts')
const previewBackend = ref('auto')
const previewFormat = ref('jpeg')

const mode = ref<'none' | 'stream' | 'preview'>('none')
const loading = ref(false)
const error = ref('')

const streamResult = ref<any>(null)
const previewUrl = ref('')

async function runStream() {
  if (!sourceUrl.value) return
  mode.value = 'none'
  streamResult.value = null
  error.value = ''
  loading.value = true
  
  try {
    const params = new URLSearchParams()
    params.set('url', sourceUrl.value)
    if (outputType.value !== 'auto') params.set('output_type', outputType.value)
    if (backend.value !== 'auto') params.set('backend', backend.value)

    const response = await api.post(`/api/modules/stream/v1/start?${params.toString()}`)
    
    // Формируем абсолютный URL если нужно
    let res = response.data
    if (res.output_url && res.output_url.startsWith('/')) {
        // Относительный путь
        const host = window.location.origin
        res.output_url = host + res.output_url
    }
    
    streamResult.value = res
    mode.value = 'stream'
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err.message || 'Сбой запуска стрима'
  } finally {
    loading.value = false
  }
}

async function runPreview() {
  if (!previewSourceUrl.value) return
  mode.value = 'none'
  previewUrl.value = ''
  error.value = ''
  loading.value = true
  
  try {
    const params = new URLSearchParams()
    params.set('name', 'debug_preview_' + Date.now())
    params.set('url', previewSourceUrl.value)
    params.set('format', previewFormat.value)
    params.set('timeout', '10') // 10s timeout

    if (previewBackend.value !== 'auto') {
      params.set('backend', previewBackend.value)
    }

    const host = window.location.origin
    const url = `${host}/api/modules/stream/v1/preview?${params.toString()}`
    
    // Сначала делаем HTTP вызов чтобы убедиться что нет 500/400
    await api.get(`/api/modules/stream/v1/preview?${params.toString()}`)
    
    previewUrl.value = url
    mode.value = 'preview'
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err.message || 'Сбой генерации превью'
  } finally {
    loading.value = false
  }
}

</script>
