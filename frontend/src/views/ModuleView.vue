<template>
  <div class="p-6 animate-fade-in flex gap-6">
    <SettingsRail />

    <div class="flex-1 min-w-0 space-y-6">
      <div>
        <h1 class="text-2xl font-bold text-on-surface tracking-tight">
          {{ t(moduleTitle) || moduleTitle || t('moduleFallback') }}
        </h1>
        <p class="mt-1 text-sm text-on-surface-variant">{{ t('moduleSettingsSub') }}</p>
      </div>

      <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 shadow-glow">
        <SettingsForm
          v-if="settingsDefinition"
          :schema="settingsDefinition.schema"
          v-model="settingsValues"
          :loading="loading"
        />

        <div v-else-if="!loading" class="text-center py-8 text-sm text-on-surface-variant">
          {{ t('noConfigurableParams') }}
        </div>
      </div>

      <div v-if="settingsDefinition" class="flex justify-end gap-3">
        <Button variant="ghost" @click="resetToDefaults">{{ t('resetButton') }}</Button>
        <Button variant="primary" :loading="saving" @click="save">{{ t('saveButton') }}</Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import SettingsRail from '@/components/layout/SettingsRail.vue'
import SettingsForm from '@/components/settings/SettingsForm.vue'
import Button from '@/components/ui/Button.vue'
import { fetchModuleSettingsDefinition, fetchModuleSettings, saveModuleSettings } from '@/core/api'
import { useI18n } from '@/core/i18n'

const { t } = useI18n()

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
    settingsValues.value = { ...(def?.defaults || {}), ...(current || {}) }
  } catch {
    settingsDefinition.value = null
  } finally {
    loading.value = false
  }
}

function resetToDefaults() {
  if (settingsDefinition.value) {
    settingsValues.value = { ...(settingsDefinition.value.defaults || {}) }
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

watch(moduleId, loadSettings)
onMounted(loadSettings)
</script>
