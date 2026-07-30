<template>
  <Transition name="fade">
    <div v-if="confirmState" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div
        class="bg-surface-container-low border border-outline-variant p-6 rounded-2xl max-w-md w-full shadow-2xl space-y-4 animate-scale-in"
      >
        <div class="flex items-center gap-3">
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
            :class="confirmState.isDanger ? 'bg-error/20 text-error' : 'bg-primary/20 text-primary'"
          >
            <span class="material-symbols-outlined text-xl">
              {{ confirmState.isDanger ? 'warning' : 'help_outline' }}
            </span>
          </div>
          <div>
            <h3 class="font-bold text-base text-on-surface">
              {{ confirmState.title || t('confirmAction') }}
            </h3>
          </div>
        </div>

        <p class="text-xs text-on-surface-variant leading-relaxed font-mono">
          {{ confirmState.message }}
        </p>

        <div class="flex items-center justify-end gap-3 pt-2 border-t border-outline-variant/60">
          <button
            @click="handleCancel"
            class="px-4 py-2 rounded-lg text-xs font-semibold bg-surface-variant hover:bg-surface-bright text-on-surface-variant transition-colors cursor-pointer"
          >
            {{ confirmState.cancelText || t('cancel') }}
          </button>
          <button
            @click="handleConfirm"
            class="px-4 py-2 rounded-lg text-xs font-semibold shadow-glow transition-colors cursor-pointer"
            :class="confirmState.isDanger ? 'bg-error text-on-error hover:bg-error/90' : 'bg-primary text-on-primary hover:bg-primary-container'"
          >
            {{ confirmState.confirmText || t('confirm') }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { useConfirm } from '@/composables/useConfirm'
import { useI18n } from '@/core/i18n'

const { confirmState, handleConfirm, handleCancel } = useConfirm()
const { t, lang } = useI18n()
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
