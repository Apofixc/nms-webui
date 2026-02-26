<template>
  <div class="p-6">
    <header class="mb-6">
      <h1 class="text-2xl font-semibold text-white mb-2">{{ moduleTitle }} — Настройки</h1>
      <p class="text-slate-400">Настройки модуля из manifest.yaml</p>
    </header>

    <div v-if="loading" class="flex justify-center py-20">
      <div class="w-10 h-10 border-2 border-accent/40 border-t-accent rounded-full animate-spin" />
    </div>

    <div v-else-if="error" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
      <p class="mb-2">{{ error }}</p>
      <button @click="loadSettings" class="text-accent hover:underline">Попробовать снова</button>
    </div>

    <div v-else-if="!definition" class="rounded-2xl bg-surface-800/60 border border-surface-700 p-12 text-center text-slate-400">
      <p>У этого модуля нет настроек в manifest.yaml</p>
    </div>

    <div v-else class="bg-surface-800/50 rounded-lg p-6 border border-surface-700">
      <form @submit.prevent="saveSettings" class="space-y-6">
        <div v-for="field in formFields" :key="field.name" class="space-y-2">
          <label :for="field.name" class="block text-sm font-medium text-slate-300">
            {{ field.label }}
            <span v-if="field.required" class="text-red-400">*</span>
            <span v-if="field.description" class="text-xs text-slate-500 ml-2">{{ field.description }}</span>
          </label>

          <input
            v-if="field.type === 'text' || field.type === 'url'"
            :id="field.name"
            v-model="settings[field.name]"
            :type="field.type === 'url' ? 'url' : 'text'"
            :placeholder="field.default"
            :required="field.required"
            class="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-md text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
          />

          <input
            v-else-if="field.type === 'number' || field.type === 'integer'"
            :id="field.name"
            v-model.number="settings[field.name]"
            type="number"
            :min="field.minimum"
            :max="field.maximum"
            :placeholder="field.default"
            :required="field.required"
            class="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-md text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
          />

          <label v-else-if="field.type === 'boolean'" class="flex items-center">
            <input
              :id="field.name"
              v-model="settings[field.name]"
              type="checkbox"
              :required="field.required"
              class="h-4 w-4 rounded bg-surface-700 border border-surface-600 text-accent focus:ring-accent"
            />
            <span class="ml-2 text-sm text-slate-300">{{ field.label }}</span>
          </label>

          <select
            v-else-if="field.type === 'enum'"
            :id="field.name"
            v-model="settings[field.name]"
            :required="field.required"
            class="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
          >
            <option v-for="opt in field.enum" :key="opt" :value="opt">{{ opt }}</option>
          </select>

          <div v-else-if="field.type === 'object'" class="ml-4 pl-4 border-l border-surface-600">
            <p class="text-xs text-slate-500 mb-2">{{ field.label }} (объект)</p>
            <div v-for="subField in field.properties" :key="subField.name" class="space-y-2">
              <label :for="subField.name" class="block text-xs font-medium text-slate-400">
                {{ subField.label }}
                <span v-if="subField.required" class="text-red-400">*</span>
              </label>
              <input
                v-if="subField.type === 'text' || subField.type === 'url'"
                :id="subField.name"
                v-model="settings[field.name][subField.name]"
                :type="subField.type === 'url' ? 'url' : 'text'"
                :placeholder="subField.default"
                :required="subField.required"
                class="w-full px-2 py-1 bg-surface-600 border border-surface-500 rounded text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-1 focus:ring-accent focus:border-transparent"
              />
              <input
                v-else-if="subField.type === 'number' || subField.type === 'integer'"
                :id="subField.name"
                v-model.number="settings[field.name][subField.name]"
                type="number"
                :min="subField.minimum"
                :max="subField.maximum"
                :placeholder="subField.default"
                :required="subField.required"
                class="w-full px-2 py-1 bg-surface-600 border border-surface-500 rounded text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-1 focus:ring-accent focus:border-transparent"
              />
              <label v-else-if="subField.type === 'boolean'" class="flex items-center">
                <input
                  :id="subField.name"
                  v-model="settings[field.name][subField.name]"
                  type="checkbox"
                  :required="subField.required"
                  class="h-3 w-3 rounded bg-surface-600 border border-surface-500 text-accent focus:ring-accent"
                />
                <span class="ml-2 text-xs text-slate-300">{{ subField.label }}</span>
              </label>
            </div>
          </div>
        </div>

        <div class="flex justify-end space-x-3 pt-4 border-t border-surface-600">
          <button
            type="button"
            @click="resetToDefaults"
            class="px-4 py-2 bg-surface-700 text-slate-300 font-medium rounded-md hover:bg-surface-600 focus:outline-none focus:ring-2 focus:ring-surface-500 focus:ring-offset-2 focus:ring-offset-surface-800"
          >
            Сбросить
          </button>
          <button
            type="submit"
            :disabled="saving"
            class="px-6 py-2 bg-accent hover:bg-accent/90 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-surface-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="saving">Сохранение...</span>
            <span v-else>Сохранить</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'

export default {
  name: 'ModuleSettings',
  props: {
    moduleId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const route = useRoute()
    const moduleId = computed(() => props.moduleId || route.params.moduleId || route.meta?.module_id)
    const loading = ref(true)
    const saving = ref(false)
    const error = ref('')
    const definition = ref(null)
    const settings = ref({})
    const formFields = ref([])

    const moduleTitle = computed(() => definition.value?.module_id || moduleId.value)

    const flattenSchema = (schema, prefix = '') => {
      const fields = []
      const properties = schema?.properties || {}
      for (const [key, prop] of Object.entries(properties)) {
        if (prop.type === 'object') {
          const nested = flattenSchema(prop, prefix ? `${prefix}.${key}` : key)
          fields.push({
            name: prefix ? `${prefix}.${key}` : key,
            label: prop.title || key,
            type: 'object',
            properties: nested,
            required: schema?.required?.includes(key) || false
          })
        } else {
          fields.push({
            name: prefix ? `${prefix}.${key}` : key,
            label: prop.title || key,
            type: prop.type || 'text',
            required: schema?.required?.includes(key) || false,
            default: prop.default,
            minimum: prop.minimum,
            maximum: prop.maximum,
            enum: prop.enum,
            description: prop.description
          })
        }
      }
      return fields
    }

    const loadSettings = async () => {
      loading.value = true
      error.value = ''
      try {
        const def = await api.moduleSettingsDefinition(moduleId.value)
        definition.value = def
        formFields.value = flattenSchema(def.schema)
        settings.value = def.current || def.defaults || {}
      } catch (e) {
        error.value = e.message || 'Не удалось загрузить настройки модуля'
      } finally {
        loading.value = false
      }
    }

    const saveSettings = async () => {
      saving.value = true
      try {
        await api.moduleSettingsPut(moduleId.value, settings.value)
      } catch (e) {
        error.value = e.message || 'Ошибка сохранения'
      } finally {
        saving.value = false
      }
    }

    const resetToDefaults = () => {
      if (definition.value?.defaults) {
        settings.value = JSON.parse(JSON.stringify(definition.value.defaults))
      }
    }

    onMounted(() => {
      loadSettings()
    })

    return {
      moduleId,
      loading,
      saving,
      error,
      definition,
      settings,
      formFields,
      moduleTitle,
      saveSettings,
      resetToDefaults
    }
  }
}
</script>
