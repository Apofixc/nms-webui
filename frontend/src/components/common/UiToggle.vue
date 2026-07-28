<template>
  <label class="relative inline-flex items-center cursor-pointer select-none">
    <input
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
      class="sr-only peer"
    />
    <div
      class="w-11 h-6 bg-surface-variant rounded-full transition-all border border-outline-variant/60 peer-checked:bg-primary/20 peer-checked:border-primary/50 after:content-[''] after:absolute after:top-[3px] after:left-[3px] after:bg-on-surface-variant after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-5 peer-checked:after:bg-primary peer-disabled:opacity-40 peer-disabled:cursor-not-allowed shadow-inner"
    />
  </label>
</template>

<script setup lang="ts">
defineProps<{
  modelValue?: boolean
  disabled?: boolean
}>()

defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()
</script>
