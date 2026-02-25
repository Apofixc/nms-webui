<template>
  <div class="flex flex-col items-center justify-center min-h-[400px] text-center p-8">
    <div class="rounded-full bg-warning/10 p-4 mb-4">
      <svg class="w-8 h-8 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    </div>
    <h2 class="text-xl font-semibold text-white mb-2">Модуль недоступен</h2>
    <p class="text-slate-400 mb-4 max-w-md">
      {{ message }}
    </p>
    <div class="bg-slate-800/50 rounded-lg p-4 border border-slate-700 max-w-md">
      <p class="text-sm text-slate-400 mb-2">Возможные решения:</p>
      <ul class="text-sm text-slate-300 space-y-1 text-left">
        <li>• Проверьте, что модуль включен в настройках</li>
        <li>• Убедитесь, что все зависимости установлены</li>
        <li>• Перезапустите WebUI, если модуль был включен</li>
      </ul>
    </div>
    <button
      v-if="showSettingsButton"
      @click="$router.push('/settings')"
      class="mt-4 rounded-lg bg-accent/20 text-accent border border-accent/50 px-4 py-2 font-medium hover:bg-accent/30 transition-colors"
    >
      Перейти к настройкам модулей
    </button>
  </div>
</template>

<script>
export default {
  name: 'ModuleUnavailable',
  props: {
    message: {
      type: String,
      default: 'Запрошенный модуль не найден или отключен в текущей конфигурации.'
    },
    showSettingsButton: {
      type: Boolean,
      default: true
    }
  }
}
</script>
