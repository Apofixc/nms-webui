<template>
  <Transition name="toast">
    <div
      v-if="toastState.message"
      class="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-glow flex items-center gap-3 border transition-all"
      :class="toastState.isError ? 'bg-error-container border-error text-on-error-container' : 'bg-tertiary-container border-tertiary text-on-tertiary-container'"
    >
      <span class="material-symbols-outlined text-[20px]" :class="toastState.isError ? 'text-error' : 'text-tertiary'">
        {{ toastState.isError ? 'error' : 'check_circle' }}
      </span>
      <span class="text-xs font-semibold font-mono">{{ toastState.message }}</span>
      <button @click="clearToast" class="ml-2 hover:opacity-75 cursor-pointer">
        <span class="material-symbols-outlined text-sm">close</span>
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast'

const { toastState, clearToast } = useToast()
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>
