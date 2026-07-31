<template>
  <div class="min-h-full p-6 flex gap-6 w-full animate-fade-in text-on-surface">
    <!-- Reusable Secondary Settings Rail -->
    <SettingsRail />

    <!-- Configuration Content Area (Full Width) -->
    <div class="flex-1 flex flex-col gap-6 w-full pb-12 min-w-0">
      <div class="flex items-center justify-between mb-2">
        <div>
          <h1 class="font-bold text-2xl text-on-surface">{{ t('moduleManagement') }}</h1>
          <p class="text-xs text-on-surface-variant mt-1">{{ t('moduleMgmtSub') }}</p>
        </div>
        <div class="flex items-center gap-3">
          <button
            @click="handleScan"
            :disabled="loading"
            class="bg-surface-container-high hover:bg-surface-variant text-on-surface px-4 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 border border-outline-variant"
          >
            <span class="material-symbols-outlined text-sm" :class="{ 'animate-spin': loading }">refresh</span>
            {{ t('scanModules') }}
          </button>
          <button
            @click="showInstallModal = true"
            class="bg-primary hover:bg-primary-fixed text-on-primary px-4 py-2 rounded-lg text-xs font-bold transition-colors shadow-glow flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-sm">add</span>
            {{ t('installModule') }}
          </button>
        </div>
      </div>

      <!-- Top Metrics Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
          <p class="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest">{{ t('totalModules') }}</p>
          <p class="text-2xl font-bold text-on-surface mt-1 font-mono">{{ modules.length }}</p>
        </div>

        <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
          <p class="text-[10px] text-tertiary uppercase font-bold tracking-widest">{{ t('active') }}</p>
          <p class="text-2xl font-bold text-tertiary mt-1 font-mono">{{ activeCount }}</p>
        </div>

        <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
          <p class="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest">{{ t('disabled') }}</p>
          <p class="text-2xl font-bold text-on-surface-variant mt-1 font-mono">{{ disabledCount }}</p>
        </div>

        <div class="bg-surface-container-low border border-outline-variant p-4 rounded-xl shadow-glow">
          <p class="text-[10px] text-primary uppercase font-bold tracking-widest">{{ t('moduleType') }}</p>
          <p class="text-2xl font-bold text-primary mt-1 font-mono">{{ typeSummary }}</p>
        </div>

      </div>

      <!-- Main Layout Grid -->
      <div class="grid grid-cols-12 gap-6">
        <!-- Table Column (Left 8) -->
        <div class="col-span-12 lg:col-span-8 bg-surface-container-low border border-outline-variant rounded-xl overflow-hidden shadow-glow">
          <div class="p-4 border-b border-outline-variant bg-surface-container-high flex items-center justify-between">
            <h3 class="font-bold text-sm text-on-surface">{{ t('moduleRegistry') }}</h3>
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-bold text-on-surface-variant uppercase mr-2">{{ t('filter') }}</span>
              <button
                @click="filterState = 'all'"
                :class="filterState === 'all' ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'"
                class="px-2.5 py-1 rounded text-[10px] font-bold transition-colors"
              >
                {{ t('all') }}
              </button>
              <button
                @click="filterState = 'active'"
                :class="filterState === 'active' ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'"
                class="px-2.5 py-1 rounded text-[10px] font-bold transition-colors"
              >
                {{ t('active').toUpperCase() }}
              </button>
              <button
                @click="filterState = 'disabled'"
                :class="filterState === 'disabled' ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'"
                class="px-2.5 py-1 rounded text-[10px] font-bold transition-colors"
              >
                {{ t('disabled').toUpperCase() }}
              </button>
            </div>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead class="bg-surface-container-highest border-b border-outline-variant/30">
                <tr class="text-[11px] font-bold text-on-surface-variant uppercase tracking-widest">
                  <th class="px-4 py-3">{{ t('moduleName') }}</th>
                  <th class="px-4 py-3">{{ t('moduleType') }}</th>
                  <th class="px-4 py-3">{{ t('version') }}</th>
                  <th class="px-4 py-3">{{ t('status') }}</th>
                  <th class="px-4 py-3 text-right">{{ t('actions') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-variant/10 font-mono text-xs">
                <tr
                  v-for="mod in filteredModules"
                  :key="mod.id"
                  @click="selectedModule = mod"
                  :class="{ 'bg-primary/10': selectedModule?.id === mod.id, 'hover:bg-surface-container-high': selectedModule?.id !== mod.id }"
                  class="cursor-pointer transition-colors"
                >
                  <td class="px-4 py-4">
                    <div class="flex items-center gap-2">
                      <span class="font-bold text-on-surface">{{ t(mod.name || mod.id) }}</span>
                      <span class="text-[10px] text-on-surface-variant">({{ mod.id }})</span>
                    </div>
                  </td>
                  <td class="px-4 py-4">
                    <span class="px-2 py-0.5 rounded text-[10px] bg-surface-variant text-on-surface-variant font-sans">
                      {{ formatModuleType(mod.type) }}
                    </span>

                  </td>
                  <td class="px-4 py-4 text-on-surface-variant">{{ mod.version || '1.0.0' }}</td>
                  <td class="px-4 py-4">
                    <button
                      @click.stop="toggleModuleStatus(mod)"
                      class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none"
                      :class="mod.enabled ? 'bg-tertiary' : 'bg-surface-variant'"
                    >
                      <span
                        class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform"
                        :class="mod.enabled ? 'translate-x-4.5' : 'translate-x-1'"
                      />
                    </button>
                    <span class="ml-2 font-bold font-sans" :class="mod.enabled ? 'text-tertiary' : 'text-on-surface-variant'">
                      {{ mod.enabled ? t('active') : t('disabled') }}
                    </span>
                  </td>
                  <td class="px-4 py-4 text-right">
                    <div class="flex items-center justify-end gap-2" @click.stop>
                      <button
                        @click="handleExport(mod)"
                        class="p-1 rounded text-primary hover:bg-primary/10 transition-colors"
                        :title="t('exportModule')"
                      >
                        <span class="material-symbols-outlined text-base">download</span>
                      </button>
                      <button
                        v-if="mod.type !== 'system'"
                        @click="confirmDelete(mod)"
                        class="p-1 rounded text-error hover:bg-error/10 transition-colors"
                        :title="t('deleteModule')"
                      >
                        <span class="material-symbols-outlined text-base">delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="filteredModules.length === 0">
                  <td colspan="5" class="px-4 py-8 text-center text-on-surface-variant font-sans">
                    Модулей не найдено
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Details Column (Right 4) -->
        <div class="col-span-12 lg:col-span-4 space-y-4">
          <div v-if="selectedModule" class="bg-surface-container-low border border-primary/30 p-5 rounded-xl shadow-glow">
            <h3 class="font-bold text-sm text-primary mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined">extension</span> {{ t(selectedModule.name || selectedModule.id) }}
            </h3>

            <div class="space-y-4 text-xs font-sans">
              <div>
                <p class="text-[10px] uppercase font-bold text-on-surface-variant">ID модуля</p>
                <p class="font-mono text-on-surface text-sm mt-0.5">{{ selectedModule.id }}</p>
              </div>

              <div v-if="selectedModule.description">
                <p class="text-[10px] uppercase font-bold text-on-surface-variant">Описание</p>
                <p class="text-on-surface mt-0.5">{{ t(selectedModule.description) }}</p>
              </div>

              <div>
                <p class="text-[10px] uppercase font-bold text-on-surface-variant mb-1">{{ t('moduleDeps') }}</p>
                <div class="flex flex-wrap gap-1 font-mono">
                  <span v-for="dep in selectedModule.deps" :key="dep" class="px-2 py-0.5 bg-surface-variant rounded text-[10px] text-on-surface-variant">
                    {{ dep }}
                  </span>
                  <span v-if="!selectedModule.deps || selectedModule.deps.length === 0" class="text-on-surface-variant text-[11px] italic">
                    Нет зависимостей
                  </span>
                </div>
              </div>

              <div v-if="selectedModule.widgets && selectedModule.widgets.length > 0">
                <p class="text-[10px] uppercase font-bold text-on-surface-variant mb-1">{{ t('widgetsTitle') }}</p>
                <div class="space-y-1">
                  <div v-for="w in selectedModule.widgets" :key="w.id" class="p-2 rounded bg-surface-container-high border border-outline-variant/30 text-[11px]">
                    <p class="font-bold text-primary">{{ t(w.title || w.id) }}</p>
                    <p class="text-[10px] text-on-surface-variant">{{ t(w.description || '') }}</p>
                  </div>
                </div>
              </div>

              <div v-if="selectedModule.permissions && selectedModule.permissions.length > 0">
                <p class="text-[10px] uppercase font-bold text-on-surface-variant mb-1">{{ t('modulePermissions') }}</p>
                <div class="space-y-1 font-mono text-[10px]">
                  <div v-for="p in selectedModule.permissions" :key="p.id" class="px-2 py-1 rounded bg-surface-container-high text-on-surface-variant">
                    {{ p.id }}
                  </div>
                </div>
              </div>

              <!-- Ссылка на отдельную страницу настроек модуля -->
              <div v-if="selectedModule.config_schema && Object.keys(selectedModule.config_schema.properties || {}).length > 0" class="pt-3 border-t border-outline-variant/30">
                <router-link
                  :to="`/settings/modules/${selectedModule.id}`"
                  class="w-full py-2 rounded bg-surface-container-high hover:bg-surface-variant text-on-surface border border-outline-variant text-xs font-bold transition-colors flex items-center justify-center gap-2"
                >
                  <span class="material-symbols-outlined text-sm text-primary">settings</span>
                  Перейти к настройкам модуля
                </router-link>
              </div>


              <div class="pt-3 border-t border-outline-variant/30">

                <button
                  @click="handleExport(selectedModule)"
                  class="w-full py-2 rounded bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 text-xs font-bold transition-colors flex items-center justify-center gap-2"
                >
                  <span class="material-symbols-outlined text-sm">download</span>
                  {{ t('exportModule') }}
                </button>
              </div>
            </div>
          </div>
          <div v-else class="bg-surface-container-low border border-outline-variant p-6 rounded-xl text-center text-on-surface-variant text-xs">
            Выберите модуль из списка для просмотра сведений
          </div>
        </div>
      </div>
    </div>

    <!-- Install Modal -->
    <div v-if="showInstallModal" class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-surface-container-high border border-outline-variant rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="font-bold text-lg text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">upload_file</span> {{ t('installModule') }}
          </h3>
          <button @click="showInstallModal = false" class="text-on-surface-variant hover:text-on-surface">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <p class="text-xs text-on-surface-variant">{{ t('uploadZipDesc') }}</p>

        <div class="border-2 border-dashed border-outline-variant hover:border-primary rounded-xl p-6 text-center cursor-pointer transition-colors" @click="fileInput?.click()">
          <input type="file" ref="fileInput" accept=".zip" class="hidden" @change="onFileSelected" />
          <span class="material-symbols-outlined text-3xl text-primary mb-2">folder_zip</span>
          <p class="text-xs font-bold text-on-surface" v-if="!selectedFile">{{ t('selectZipFile') }}</p>
          <p class="text-xs font-bold text-primary" v-else>{{ selectedFile.name }}</p>
        </div>

        <div class="flex justify-end gap-3 pt-2">
          <button @click="showInstallModal = false" class="px-4 py-2 rounded-lg text-xs font-bold text-on-surface-variant hover:bg-surface-variant transition-colors">
            Отмена
          </button>
          <button
            @click="handleInstall"
            :disabled="!selectedFile || installing"
            class="px-4 py-2 rounded-lg text-xs font-bold bg-primary text-on-primary disabled:opacity-50 hover:bg-primary-fixed transition-colors flex items-center gap-2"
          >
            <span v-if="installing" class="material-symbols-outlined text-sm animate-spin">refresh</span>
            {{ installing ? t('installing') : t('installModule') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="moduleToDelete" class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-surface-container-high border border-outline-variant rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <h3 class="font-bold text-lg text-error flex items-center gap-2">
          <span class="material-symbols-outlined">warning</span> {{ t('deleteModule') }}
        </h3>
        <p class="text-xs text-on-surface">
          {{ t('confirmDeleteModule', { name: t(moduleToDelete.name || moduleToDelete.id) }) }}
        </p>

        <div class="flex justify-end gap-3 pt-2">
          <button @click="moduleToDelete = null" class="px-4 py-2 rounded-lg text-xs font-bold text-on-surface-variant hover:bg-surface-variant transition-colors">
            Отмена
          </button>
          <button @click="handleDelete" class="px-4 py-2 rounded-lg text-xs font-bold bg-error text-on-error hover:opacity-90 transition-colors">
            {{ t('deleteModule') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import SettingsRail from '@/components/layout/SettingsRail.vue'
import { useI18n } from '@/core/i18n'
import { fetchModules, scanModules, setModuleEnabled, installModule, deleteModule, exportModule } from '@/core/api'
import { initModulesRegistry } from '@/modules/registry'

const { t } = useI18n()
const route = useRoute()

const loading = ref(false)
const installing = ref(false)
const modules = ref<any[]>([])
const selectedModule = ref<any | null>(null)
const filterState = ref<'all' | 'active' | 'disabled'>('all')

const showInstallModal = ref(false)
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const moduleToDelete = ref<any | null>(null)



function formatModuleType(type?: string): string {
  if (!type) return t('moduleTypeFeature')
  if (type === 'system') return t('moduleTypeSystem')
  if (type === 'driver') return t('moduleTypeDriver')
  if (type === 'feature') return t('moduleTypeFeature')
  return type
}

const activeCount = computed(() => modules.value.filter((m) => m.enabled).length)
const disabledCount = computed(() => modules.value.filter((m) => !m.enabled).length)

const typeSummary = computed(() => {
  if (modules.value.length === 0) return '0'
  const counts: Record<string, number> = {}
  modules.value.forEach((m) => {
    const tName = m.type || 'feature'
    counts[tName] = (counts[tName] || 0) + 1
  })
  return Object.entries(counts)
    .map(([typeKey, count]) => `${count} ${formatModuleType(typeKey).toLowerCase()}`)
    .join(', ')
})


const filteredModules = computed(() => {
  if (filterState.value === 'active') return modules.value.filter((m) => m.enabled)
  if (filterState.value === 'disabled') return modules.value.filter((m) => !m.enabled)
  return modules.value
})

async function loadModulesList() {
  loading.value = true
  try {
    const res = await fetchModules(true, false)
    modules.value = res.items || []
    const selId = route.query.selected as string
    if (selId) {
      const target = modules.value.find((m) => m.id === selId)
      if (target) {
        selectedModule.value = target
      } else if (modules.value.length > 0) {
        selectedModule.value = modules.value[0]
      }
    } else if (modules.value.length > 0 && !selectedModule.value) {
      selectedModule.value = modules.value[0]
    }
  } catch (err) {
    console.error('Failed to load modules:', err)
  } finally {
    loading.value = false
  }
}

watch(() => route.query.selected, (newSelId) => {
  if (newSelId && modules.value.length > 0) {
    const target = modules.value.find((m) => m.id === newSelId)
    if (target) {
      selectedModule.value = target
    }
  }
})


async function handleScan() {
  loading.value = true
  try {
    await scanModules()
    await loadModulesList()
    await initModulesRegistry()
  } catch (err) {
    console.error('Failed to scan modules:', err)
  } finally {
    loading.value = false
  }
}

async function toggleModuleStatus(mod: any) {
  const newStatus = !mod.enabled
  try {
    await setModuleEnabled(mod.id, newStatus)
    mod.enabled = newStatus
    await initModulesRegistry()
  } catch (err) {
    console.error('Failed to toggle module status:', err)
  }
}

function onFileSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
  }
}

async function handleInstall() {
  if (!selectedFile.value) return
  installing.value = true
  try {
    await installModule(selectedFile.value)
    showInstallModal.value = false
    selectedFile.value = null
    await loadModulesList()
    await initModulesRegistry()
  } catch (err: any) {
    alert(err?.response?.data?.detail || 'Failed to install module')
  } finally {
    installing.value = false
  }
}

async function handleExport(mod: any) {
  if (!mod?.id) return
  try {
    await exportModule(mod.id)
  } catch (err: any) {
    alert(err?.response?.data?.detail || 'Failed to export module')
  }
}

function confirmDelete(mod: any) {
  moduleToDelete.value = mod
}

async function handleDelete() {
  if (!moduleToDelete.value) return
  try {
    await deleteModule(moduleToDelete.value.id)
    moduleToDelete.value = null
    selectedModule.value = null
    await loadModulesList()
    await initModulesRegistry()
  } catch (err: any) {
    alert(err?.response?.data?.detail || 'Failed to delete module')
  }
}

onMounted(() => {
  loadModulesList()
})
</script>
