<template>
  <div class="flex min-h-full w-full">
    <!-- Боковая навигация: список модулей -->
    <nav class="w-52 flex-shrink-0 min-w-0 border-r border-surface-700 bg-surface-800/80 p-3 sticky top-0 h-screen overflow-y-auto">
      <h2 class="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Настройки</h2>
      <ul class="space-y-0.5">
        <!-- Общие настройки -->
        <li>
          <button
            type="button"
            :class="[
              'w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              activeNav === 'general'
                ? 'bg-accent/15 text-accent'
                : 'text-slate-400 hover:text-white hover:bg-surface-700/50'
            ]"
            @click="activeNav = 'general'"
          >
            Общие
          </button>
        </li>
        <!-- Модули -->
        <li v-for="mod in modules" :key="mod.id">
          <button
            type="button"
            :class="[
              'w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              activeNav === mod.id
                ? 'bg-accent/15 text-accent'
                : 'text-slate-400 hover:text-white hover:bg-surface-700/50'
            ]"
            @click="selectModule(mod.id)"
          >
            {{ mod.name }}
          </button>
          <!-- Субмодули -->
          <ul v-if="activeNav === mod.id && mod.children && mod.children.length" class="ml-3 mt-0.5 space-y-0.5">
            <li v-for="sub in mod.children" :key="sub.id">
              <button
                type="button"
                :class="[
                  'w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors',
                  activeSubNav === sub.id
                    ? 'bg-accent/10 text-accent'
                    : 'text-slate-500 hover:text-slate-300 hover:bg-surface-700/30'
                ]"
                @click="activeSubNav = sub.id; loadModuleSettings(sub.id)"
              >
                {{ sub.title }}
              </button>
            </li>
          </ul>
        </li>
      </ul>
    </nav>

    <!-- Основная панель -->
    <main class="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 overflow-auto">
      <div v-if="loading" class="flex justify-center py-20">
        <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
      </div>

      <template v-else>
        <!-- Общие настройки: enable/disable модулей -->
        <template v-if="activeNav === 'general'">
          <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
            <div>
              <h1 class="text-xl font-semibold text-white">Общие настройки</h1>
              <p class="text-sm text-slate-400 mt-0.5">Управление модулями и конфигурацией</p>
            </div>
          </div>

          <div v-if="configSchema && configSchema.items.length > 0" class="space-y-3">
            <div
              v-for="item in configSchema.items"
              :key="item.id"
              class="rounded-xl border border-surface-700 bg-surface-800/60 p-4"
            >
              <div class="flex items-center justify-between">
                <div>
                  <span class="text-sm font-medium text-white">{{ item.title }}</span>
                  <span
                    class="ml-2 text-xs px-1.5 py-0.5 rounded"
                    :class="item.type === 'core' ? 'bg-accent/20 text-accent' : 'bg-surface-700 text-slate-400'"
                  >
                    {{ item.type }}
                  </span>
                </div>
                <button
                  type="button"
                  :class="[
                    'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200',
                    item.enabled ? 'bg-accent' : 'bg-surface-700',
                  ]"
                  @click="toggleModule(item.id, !item.enabled)"
                >
                  <span
                    :class="[
                      'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200',
                      item.enabled ? 'translate-x-5' : 'translate-x-0',
                    ]"
                  />
                </button>
              </div>

              <!-- Субмодули -->
              <div v-if="item.children && item.children.length > 0" class="mt-3 ml-4 space-y-2 border-l border-surface-700 pl-4">
                <div
                  v-for="child in item.children"
                  :key="child.id"
                  class="flex items-center justify-between"
                >
                  <span class="text-sm text-slate-300">{{ child.title }}</span>
                  <button
                    type="button"
                    :class="[
                      'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200',
                      child.enabled ? 'bg-accent' : 'bg-surface-700',
                      !item.enabled && 'opacity-50 cursor-not-allowed',
                    ]"
                    :disabled="!item.enabled"
                    @click="toggleModule(child.id, !child.enabled)"
                  >
                    <span
                      :class="[
                        'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200',
                        child.enabled ? 'translate-x-4' : 'translate-x-0',
                      ]"
                    />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
            Нет доступных модулей для настройки
          </div>

          <div class="mt-6 text-xs text-slate-500 space-y-1">
            <p>Изменения вступят в силу после перезапуска backend.</p>
            <p>Настройки хранятся в <code class="text-accent/60">modules_state.json</code></p>
          </div>
        </template>

        <!-- Настройки модуля -->
        <template v-else>
          <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
              <div class="flex flex-col">
                <h1 class="text-xl font-semibold text-white">{{ activeModuleTitle }} — Настройки</h1>
                <p class="text-sm text-slate-400 mt-0.5">Настройки модуля из manifest.yaml</p>
                
                <div class="flex items-center gap-3 mt-3">
                  <span v-if="saving" class="text-sm text-slate-400">Сохранение…</span>
                  <span v-if="saveOk" class="text-sm text-green-400">Сохранено</span>
                  <span v-if="saveError2" class="text-sm text-danger">{{ saveError2 }}</span>
                </div>
              </div>
              
              <button
                type="button"
                @click="resetToDefaults"
                class="px-4 py-1.5 text-sm bg-surface-700 text-slate-300 font-medium rounded-md hover:bg-surface-600 border border-surface-600 transition-colors"
              >
                К значениям по умолчанию
              </button>
            </div>

          <div v-if="settingsLoading" class="flex justify-center py-20">
            <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
          </div>

          <div v-else-if="settingsError" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
            <p class="mb-2">{{ settingsError }}</p>
            <button @click="loadModuleSettings(settingsModuleId)" class="text-accent hover:underline">Попробовать снова</button>
          </div>

          <div v-else-if="!settingsDefinition" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
            <p>У этого модуля нет настроек в manifest.yaml</p>
          </div>

          <div v-else class="bg-surface-800/50 rounded-lg p-6 border border-surface-700 max-w-2xl">
            <form @submit.prevent="saveSettings" class="space-y-6">
              <div v-for="(group, gIdx) in groupedFormFields" :key="gIdx" class="mb-8 last:mb-0">
                <h3 v-if="group.title !== 'Общие'" class="text-base font-medium text-white mb-4 pb-2 border-b border-surface-700/50">{{ group.title }}</h3>
                <div class="space-y-6">
                  <div v-for="field in group.fields" :key="field.name" class="space-y-2">
                <label :for="field.name" class="block text-sm font-medium text-slate-300">
                  {{ field.label }}
                  <span v-if="field.required" class="text-red-400">*</span>
                </label>

                <p v-if="field.description && field.type !== 'boolean'" class="text-xs text-slate-400 mb-1.5">{{ field.description }}</p>

                <input
                  v-if="field.type === 'text' || field.type === 'url' || field.type === 'string'"
                  :id="field.name"
                  v-model="settingsForm[field.name]"
                  :type="field.type === 'url' ? 'url' : 'text'"
                  :placeholder="String(field.default ?? '')"
                  :required="field.required"
                  :pattern="field.pattern"
                  class="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-md text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent invalid:border-danger invalid:focus:ring-danger"
                />

                <input
                  v-else-if="field.type === 'number' || field.type === 'integer'"
                  :id="field.name"
                  v-model.number="settingsForm[field.name]"
                  type="number"
                  :min="field.minimum"
                  :max="field.maximum"
                  :placeholder="String(field.default ?? '')"
                  :required="field.required"
                  class="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-md text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent invalid:border-danger invalid:focus:ring-danger"
                />

                <label v-else-if="field.type === 'boolean'" class="flex items-center">
                  <input
                    :id="field.name"
                    v-model="settingsForm[field.name]"
                    type="checkbox"
                    class="h-4 w-4 rounded bg-surface-700 border border-surface-600 text-accent focus:ring-accent"
                  />
                  <span class="ml-2 text-sm text-slate-300">{{ field.label }}</span>
                </label>

                <select
                  v-else-if="field.type === 'enum'"
                  :id="field.name"
                  v-model="settingsForm[field.name]"
                  class="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                >
                  <option v-for="opt in field.enum" :key="opt" :value="opt">{{ opt }}</option>
                </select>
              </div>
            </div>
            </form>
          </div>
        </template>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import {
  fetchModules,
  fetchModuleConfigSchema,
  setModuleEnabled,
  fetchModuleSettingsDefinition,
  fetchModuleSettings,
  saveModuleSettings,
} from '@/core/api'
import type { EnableSchemaResponse, EnableSchemaNode } from '@/modules/types'
import { useAppStore } from '@/core/store'

const store = useAppStore()

// ── Навигация ──
const loading = ref(true)
const activeNav = ref('general')
const activeSubNav = ref('')
const modules = ref<any[]>([])
const configSchema = ref<EnableSchemaResponse | null>(null)

// ── Настройки модуля ──
const settingsLoading = ref(false)
const settingsError = ref('')
const settingsDefinition = ref<any>(null)
const settingsForm = ref<Record<string, any>>({})
const settingsModuleId = ref('')
const formFields = ref<any[]>([])
const saving = ref(false)
const saveOk = ref(false)
const saveError2 = ref('')

let isProgrammaticUpdate = false
let saveTimeout: ReturnType<typeof setTimeout> | null = null

watch(settingsForm, () => {
  if (isProgrammaticUpdate) return
  if (saveTimeout) clearTimeout(saveTimeout)
  saveTimeout = setTimeout(() => {
    saveSettings()
  }, 750)
}, { deep: true })

const groupedFormFields = computed(() => {
  const map = new Map<string, any[]>()
  for (const field of formFields.value) {
    if (!map.has(field.group)) map.set(field.group, [])
    map.get(field.group)!.push(field)
  }
  return [...map.entries()].map(([title, fields]) => ({ title, fields }))
})

const activeModuleTitle = computed(() => {
  const mod = modules.value.find((m) => m.id === activeNav.value)
  return mod?.name || activeNav.value
})

// ── Загрузка списка модулей ──
async function loadAll() {
  loading.value = true
  try {
    const [schemaRes, modulesRes] = await Promise.all([
      fetchModuleConfigSchema(),
      fetchModules(true, false),
    ])
    configSchema.value = schemaRes

    const allModules = modulesRes?.items || []
    modules.value = allModules
      .filter((m) => !m.is_submodule)
      .map((parent) => ({
        id: parent.id,
        name: parent.name,
        children: allModules
          .filter((m) => m.is_submodule && m.parent_id === parent.id)
          .map((sub) => ({
            id: sub.id,
            title: sub.name,
          })),
      }))
  } catch {
    configSchema.value = null
    modules.value = []
  } finally {
    loading.value = false
  }
}

// ── Enable/disable модуля ──
async function toggleModule(moduleId: string, enabled: boolean) {
  try {
    await setModuleEnabled(moduleId, enabled)
    
    // Реактивное обновление состояния стора без перезагрузки вкладки
    await store.loadModules()

    // Если нужна локальная актуализация переключателей в дереве (configSchema.items)
    if (configSchema.value) {
      const updateNode = (nodes: EnableSchemaNode[]) => {
        for (const node of nodes) {
          if (node.id === moduleId) node.enabled = enabled
          if (node.children) updateNode(node.children)
        }
      }
      updateNode(configSchema.value.items)
    }
  } catch (e) {
    console.error('Failed to toggle module', e)
  }
}

// ── Выбор модуля в навигации ──
function selectModule(moduleId: string) {
  activeNav.value = moduleId
  activeSubNav.value = ''
  loadModuleSettings(moduleId)
}

// ── Загрузка настроек модуля ──
function flattenSchema(schema: any): any[] {
  const fields: any[] = []
  const properties = schema?.properties || {}
  for (const [key, prop] of Object.entries<any>(properties)) {
    fields.push({
      name: key,
      label: prop.title || key,
      type: prop.type || 'text',
      required: schema?.required?.includes(key) || false,
      default: prop.default,
      minimum: prop.minimum,
      maximum: prop.maximum,
      enum: prop.enum,
      description: prop.description,
      group: prop.group || 'Общие',
      pattern: prop.format === 'ipv4' || key.includes('host') || key.includes('ip') 
        ? '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$' 
        : prop.pattern,
    })
  }
  return fields
}

async function loadModuleSettings(moduleId: string) {
  settingsLoading.value = true
  settingsError.value = ''
  settingsDefinition.value = null
  settingsModuleId.value = moduleId
  saveOk.value = false
  saveError2.value = ''
  try {
    const def = await fetchModuleSettingsDefinition(moduleId)
    settingsDefinition.value = def
    formFields.value = flattenSchema(def.schema)
    
    isProgrammaticUpdate = true
    settingsForm.value = { ...def.defaults, ...(def.current || {}) }
    nextTick(() => { isProgrammaticUpdate = false })
  } catch (e: any) {
    if (e?.response?.status === 404) {
      settingsDefinition.value = null
    } else {
      settingsError.value = e?.response?.data?.detail || e.message || 'Не удалось загрузить настройки модуля'
    }
  } finally {
    settingsLoading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveOk.value = false
  saveError2.value = ''
  try {
    await saveModuleSettings(settingsModuleId.value, settingsForm.value)
    saveOk.value = true
    setTimeout(() => { saveOk.value = false }, 3000)
  } catch (e: any) {
    saveError2.value = e?.response?.data?.detail || e.message || 'Ошибка сохранения'
  } finally {
    saving.value = false
  }
}

function resetToDefaults() {
  if (settingsDefinition.value?.defaults) {
    isProgrammaticUpdate = true
    settingsForm.value = JSON.parse(JSON.stringify(settingsDefinition.value.defaults))
    nextTick(() => {
      isProgrammaticUpdate = false
      saveSettings()
    })
  }
}

onMounted(loadAll)
</script>
