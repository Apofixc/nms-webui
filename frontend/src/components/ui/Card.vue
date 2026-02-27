<template>
  <div
    :class="[
      'rounded-xl border border-surface-700 bg-surface-800/80 backdrop-blur-sm shadow-card',
      'transition-all duration-200',
      hoverable && 'hover:border-surface-600 hover:shadow-lg',
      padded && 'p-6',
    ]"
  >
    <div v-if="title || $slots.header" class="mb-4">
      <slot name="header">
        <h3 class="text-base font-semibold text-white">{{ title }}</h3>
        <p v-if="subtitle" class="mt-1 text-sm text-slate-400">{{ subtitle }}</p>
      </slot>
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    subtitle?: string
    hoverable?: boolean
    padded?: boolean
  }>(),
  {
    title: '',
    subtitle: '',
    hoverable: false,
    padded: true,
  },
)
</script>
