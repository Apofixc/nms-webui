<template>
  <div class="space-y-6">
    <div v-if="loading" class="text-center py-12">
      <div class="inline-flex items-center gap-2 text-slate-400">
        <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span>Загрузка схемы...</span>
      </div>
    </div>

    <div v-else-if="!schema" class="text-center py-12 text-slate-500">
      Нет доступной схемы настроек
    </div>

    <div v-else>
      <div
        v-for="(prop, key) in properties"
        :key="key"
        class="bg-surface-750/50 rounded-lg p-4 space-y-2"
      >
        <label class="block text-sm font-medium text-slate-300">
          {{ prop.title || key }}
        </label>

        <!-- Boolean -->
        <div v-if="prop.type === 'boolean'" class="flex items-center gap-3">
          <button
            type="button"
            :class="[
              'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none',
              modelValue[key] ? 'bg-accent' : 'bg-surface-700',
            ]"
            @click="toggle(key)"
          >
            <span
              :class="[
                'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200',
                modelValue[key] ? 'translate-x-5' : 'translate-x-0',
              ]"
            />
          </button>
          <span class="text-sm text-slate-400">{{ modelValue[key] ? 'Вкл' : 'Выкл' }}</span>
        </div>

        <!-- String enum (select) -->
        <select
          v-else-if="prop.type === 'string' && prop.enum"
          :value="modelValue[key] ?? prop.default"
          class="w-full rounded-lg px-3 py-2 text-sm"
          @change="update(key, ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="opt in prop.enum" :key="opt" :value="opt">{{ opt }}</option>
        </select>

        <!-- Number / Integer -->
        <input
          v-else-if="prop.type === 'number' || prop.type === 'integer'"
          type="number"
          :value="modelValue[key] ?? prop.default"
          :min="prop.minimum"
          :max="prop.maximum"
          class="w-full rounded-lg px-3 py-2 text-sm"
          @input="update(key, Number(($event.target as HTMLInputElement).value))"
        />

        <!-- String -->
        <input
          v-else
          type="text"
          :value="modelValue[key] ?? prop.default ?? ''"
          :placeholder="prop.title || key"
          class="w-full rounded-lg px-3 py-2 text-sm"
          @input="update(key, ($event.target as HTMLInputElement).value)"
        />

        <p v-if="prop.description" class="text-xs text-slate-500 mt-1">
          {{ prop.description }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  schema: Record<string, any> | null
  modelValue: Record<string, any>
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
}>()

const properties = computed(() => {
  if (!props.schema?.properties) return {}
  return props.schema.properties as Record<string, any>
})

function update(key: string, value: any) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

function toggle(key: string) {
  emit('update:modelValue', { ...props.modelValue, [key]: !props.modelValue[key] })
}
</script>
