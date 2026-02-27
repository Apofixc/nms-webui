<template>
  <div class="p-6 animate-fade-in">
    <div class="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">Настройки</h1>
        <p class="mt-1 text-sm text-slate-400">Управление модулями и конфигурацией</p>
      </div>

      <!-- Module enable/disable -->
      <Card title="Модули">
        <div v-if="loading" class="text-center py-8">
          <div class="inline-flex items-center gap-2 text-slate-400">
            <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span>Загрузка...</span>
          </div>
        </div>

        <div v-else-if="configSchema && configSchema.items.length > 0" class="space-y-3">
          <div
            v-for="item in configSchema.items"
            :key="item.id"
            class="rounded-lg bg-surface-750/50 p-4"
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

            <!-- Submodules -->
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

        <div v-else class="text-center py-8 text-sm text-slate-500">
          Нет доступных модулей для настройки
        </div>
      </Card>

      <!-- Info -->
      <Card>
        <div class="text-xs text-slate-500 space-y-1">
          <p>Изменения вступят в силу после перезапуска backend.</p>
          <p>Настройки хранятся в <code class="text-accent/60">modules_state.json</code></p>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Card from '@/components/ui/Card.vue'
import { fetchModuleConfigSchema, setModuleEnabled } from '@/core/api'
import type { EnableSchemaResponse, EnableSchemaNode } from '@/modules/types'

const loading = ref(true)
const configSchema = ref<EnableSchemaResponse | null>(null)

async function loadSchema() {
  loading.value = true
  try {
    configSchema.value = await fetchModuleConfigSchema()
  } catch {
    configSchema.value = null
  } finally {
    loading.value = false
  }
}

async function toggleModule(moduleId: string, enabled: boolean) {
  try {
    await setModuleEnabled(moduleId, enabled)
    // Update local state
    if (configSchema.value) {
      const updateNode = (nodes: EnableSchemaNode[]) => {
        for (const node of nodes) {
          if (node.id === moduleId) {
            node.enabled = enabled
          }
          if (node.children) updateNode(node.children)
        }
      }
      updateNode(configSchema.value.items)
    }
  } catch (e) {
    console.error('Failed to toggle module', e)
  }
}

onMounted(loadSchema)
</script>
