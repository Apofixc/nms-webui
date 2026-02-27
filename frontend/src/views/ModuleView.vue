<template>
  <div class="p-6 animate-fade-in">
    <div class="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight">
          {{ moduleTitle || 'Модуль' }}
        </h1>
        <p class="mt-1 text-sm text-slate-400">Настройки модуля</p>
      </div>

      <Card>
        <SettingsForm
          v-if="settingsDefinition"
          :schema="settingsDefinition.schema"
          v-model="settingsValues"
          :loading="loading"
        />

        <div v-else-if="!loading" class="text-center py-8 text-sm text-slate-500">
          У этого модуля нет настраиваемых параметров
        </div>
      </Card>

      <div v-if="settingsDefinition" class="flex justify-end gap-3">
        <Button variant="ghost" @click="resetToDefaults">Сбросить</Button>
        <Button variant="primary" :loading="saving" @click="save">Сохранить</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import SettingsForm from '@/components/settings/SettingsForm.vue'
import { fetchModuleSettingsDefinition, fetchModuleSettings, saveModuleSettings } from '@/core/api'

const route = useRoute()
const moduleId = computed(() => (route.params as any).moduleId || (route.meta as any).module_id || '')
const moduleTitle = computed(() => (route.meta as any).title || moduleId.value)

const loading = ref(true)
const saving = ref(false)
const settingsDefinition = ref<{ schema: Record<string, any>; defaults: Record<string, any> } | null>(null)
const settingsValues = ref<Record<string, any>>({})

async function loadSettings() {
  if (!moduleId.value) return
  loading.value = true
  try {
    const [def, current] = await Promise.all([
      fetchModuleSettingsDefinition(moduleId.value),
      fetchModuleSettings(moduleId.value),
    ])
    settingsDefinition.value = def
    settingsValues.value = { ...def.defaults, ...current }
  } catch {
    settingsDefinition.value = null
  } finally {
    loading.value = false
  }
}

function resetToDefaults() {
  if (settingsDefinition.value) {
    settingsValues.value = { ...settingsDefinition.value.defaults }
  }
}

async function save() {
  if (!moduleId.value) return
  saving.value = true
  try {
    await saveModuleSettings(moduleId.value, settingsValues.value)
  } catch (e) {
    console.error('Failed to save settings', e)
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>
