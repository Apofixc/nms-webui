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
        <label class="block text-xs font-medium text-slate-400 mb-1">Source URL (Превью)</label>
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
    params.set('name', 'debug_preview_' + Date.now())
    params.set('url', previewSourceUrl.value)
    params.set('format', previewFormat.value)
    params.set('timeout', '15') 

    if (previewBackend.value !== 'auto') {
      params.set('backend', previewBackend.value)
    }

    // Сначала делаем контрольный запрос, чтобы получить ошибку в JSON если она есть
    await api.get(`/api/modules/stream/v1/preview?${params.toString()}`)
    
    // Если успешно, формируем URL для <img> (добавляем t для обхода кэша)
    const host = window.location.origin
    previewUrl.value = `${host}/api/modules/stream/v1/preview?${params.toString()}&t=${Date.now()}`
    
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err.message || 'Сбой генерации превью'
  } finally {
    loading.value = false
  }
}
</script>
