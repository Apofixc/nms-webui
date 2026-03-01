<template>
  <div class="bg-surface-800/60 rounded-xl border border-surface-700 p-5 shadow-sm">
    <div class="flex items-center justify-between mb-4 border-b border-surface-700/80 pb-3">
      <h4 class="text-sm font-semibold text-white">Тест Стриминга</h4>
      <div 
        v-if="loading" 
        class="w-4 h-4 border-2 border-accent/40 border-t-accent rounded-full animate-spin"
      ></div>
    </div>

    <!-- Область предпросмотра -->
    <div class="w-full aspect-video bg-black rounded-lg overflow-hidden mb-4 relative flex items-center justify-center">
      <template v-if="streamResult">
        <VideoPlayer 
          :url="streamResult.output_url" 
          :type="streamResult.output_type" 
          :metadata="streamResult.metadata"
          :muted="true"
        />
      </template>
      <div v-else class="text-slate-500 text-sm">Нет медиа</div>
    </div>

    <form @submit.prevent="runStream" class="space-y-4">
      <div>
        <label class="block text-xs font-medium text-slate-400 mb-1">Source URL</label>
        <input 
          v-model="testSourceUrl"
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
            v-model="testBackend"
            class="w-full px-2 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          >
            <option v-for="opt in backendOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Формат выхода</label>
          <select 
            v-model="testFormat"
            class="w-full px-2 py-1.5 text-sm bg-surface-700 border border-surface-600 rounded text-white focus:ring-1 focus:ring-accent outline-none"
          >
            <option v-for="opt in formatOptions" :key="opt" :value="opt">{{ opt }}</option>
          </select>
        </div>
      </div>

      <div class="flex gap-2 pt-2">
        <button 
          v-if="!streamResult"
          type="submit"
          class="flex-1 bg-accent/20 hover:bg-accent/30 text-accent font-medium text-xs px-3 py-2 rounded transition-colors"
          :disabled="loading"
        >
          Запустить Тестовый Стрим
        </button>
        <button 
          v-else
          type="button"
          @click="stopCurrentStream"
          class="flex-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 font-medium text-xs px-3 py-2 rounded transition-colors"
          :disabled="loading"
        >
          Остановить Стрим
        </button>
      </div>
    </form>

    <div v-if="error" class="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400 break-words">
      {{ error }}
    </div>

    <details v-if="streamResult" class="mt-4 text-xs">
      <summary class="text-slate-400 cursor-pointer hover:text-white">Показать Result JSON</summary>
      <pre class="mt-2 p-2 bg-surface-900 rounded overflow-x-auto text-slate-300">{{ JSON.stringify(streamResult, null, 2) }}</pre>
    </details>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import VideoPlayer from '@/components/ui/VideoPlayer.vue'
import api from '@/core/api'

const props = defineProps<{
  schema: any
  backendField: any
  formatField: any
}>()

const testSourceUrl = ref('http://31.130.202.110/httpts/tv3by/avchigh.ts')
const testBackend = ref('auto')
const testFormat = ref('auto')

const loading = ref(false)
const error = ref('')
const streamResult = ref<any>(null)

// Опции для бэкенда (обычно не фильтруются)
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
      // Проверяем условие на ТЕСТОВЫЙ бэкенд
      const ifProps = rule.if.properties
      if (ifProps[props.backendField.name]) {
        const cond = ifProps[props.backendField.name]
        const val = testBackend.value
        if (cond.const !== undefined && val !== cond.const) match = false
        if (cond.enum !== undefined && !cond.enum.includes(val)) match = false
      } else {
        match = false // Если в условии нет нашего зависимого поля, пропускаем
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
  if (!newOpts.includes(testFormat.value)) {
    testFormat.value = newOpts.includes('auto') ? 'auto' : newOpts[0]
  }
})

async function stopCurrentStream() {
  if (!streamResult.value?.stream_id) {
    streamResult.value = null
    return
  }
  
  const sid = streamResult.value.stream_id
  streamResult.value = null // Сразу убираем плеер
  
  try {
    await api.post(`/api/modules/stream/v1/stop?stream_id=${encodeURIComponent(sid)}`)
  } catch (err) {
    console.warn('Failed to stop test stream:', err)
  }
}

async function runStream() {
  if (!testSourceUrl.value) return
  
  // Если уже что-то запущено - останавливаем
  if (streamResult.value) {
    await stopCurrentStream()
  }
  
  error.value = ''
  loading.value = true
  
  try {
    const params = new URLSearchParams()
    params.set('url', testSourceUrl.value)
    params.set('output_type', testFormat.value)
    if (testBackend.value !== 'auto') params.set('backend', testBackend.value)

    const response = await api.post(`/api/modules/stream/v1/start?${params.toString()}`)
    
    let res = response.data
    if (res.output_url && res.output_url.startsWith('/')) {
        res.output_url = window.location.origin + res.output_url
    }
    
    streamResult.value = res
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err.message || 'Сбой запуска стрима'
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (streamResult.value) {
    stopCurrentStream()
  }
})
</script>
