<template>
  <div class="min-h-screen flex">
    <aside class="w-60 flex-shrink-0 bg-surface-800/90 border-r border-surface-700 flex flex-col">
      <div class="p-5 border-b border-surface-700 bg-gradient-to-br from-surface-800 to-surface-850">
        <h1 class="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center text-accent font-mono text-sm shadow-glow">NMS</span>
          <span>Astra Monitor</span>
        </h1>
      </div>
      <nav class="p-3 flex-1 overflow-y-auto">
        <!-- Выпадающий раздел: Cesbo Astra -->
        <div class="mb-1">
          <button
            type="button"
            class="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg text-left font-medium text-white bg-surface-750 hover:bg-surface-700 transition-colors"
            @click="cesboOpen = !cesboOpen"
          >
            <span>Cesbo Astra</span>
            <span class="text-slate-400 text-sm transition-transform duration-200" :class="cesboOpen && 'rotate-180'">▾</span>
          </button>
          <transition
            enter-active-class="transition ease-out duration-200"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition ease-in duration-150"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-1"
          >
            <div v-show="cesboOpen" class="mt-1 ml-2 pl-4 border-l border-surface-700 space-y-0.5">
              <router-link
                v-for="item in cesboNav"
                :key="item.path"
                :to="item.path"
                class="flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-surface-750 transition-colors block"
                active-class="!text-accent !bg-accent/10"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-current opacity-60" />
                {{ item.label }}
              </router-link>
            </div>
          </transition>
        </div>
      </nav>
      <div class="p-3 border-t border-surface-700">
        <div v-if="!backendOk" class="text-xs text-danger bg-danger/10 rounded-lg p-2">
          Backend недоступен. Запустите: <code class="block mt-1 text-[10px] break-all">./run_backend.sh</code>
        </div>
        <div v-else class="text-xs text-success/80">API подключён</div>
      </div>
    </aside>
    <main class="flex-1 overflow-auto">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" v-if="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from './api'

const backendOk = ref(true)
const cesboOpen = ref(true)

const cesboNav = [
  { path: '/', label: 'Общая информация' },
  { path: '/instances', label: 'Управление экземплярами' },
  { path: '/channels', label: 'Каналы' },
  { path: '/monitors', label: 'Мониторы' },
  { path: '/subscribers', label: 'Подписка' },
  { path: '/dvb', label: 'DVB-адаптеры' },
  { path: '/system', label: 'Система' },
]

onMounted(async () => {
  try {
    await api.instances()
  } catch {
    backendOk.value = false
  }
  // Предзагрузка остальных вкладок — переключение без задержки
  setTimeout(() => {
    import('./views/Dashboard.vue')
    import('./views/Instances.vue')
    import('./views/Channels.vue')
    import('./views/Monitors.vue')
    import('./views/Subscribers.vue')
    import('./views/Dvb.vue')
    import('./views/System.vue')
  }, 300)
})
</script>

<style scoped>
.page-enter-active,
.page-leave-active { transition: opacity 0.12s ease, transform 0.12s ease; }
.page-enter-from { opacity: 0; transform: translateY(4px); }
.page-leave-to { opacity: 0; transform: translateY(-2px); }
</style>
