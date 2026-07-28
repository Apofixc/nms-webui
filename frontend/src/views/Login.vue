<template>
  <div class="min-h-screen w-full flex items-center justify-center overflow-hidden bg-background relative font-sans text-on-surface p-4">
    <!-- Background Image Overlay -->
    <div class="absolute inset-0 z-0 opacity-20 pointer-events-none bg-gradient-to-br from-surface-dim via-background to-surface-container-lowest">
      <div class="w-full h-full bg-[radial-gradient(#22d3ee_1px,transparent_1px)] [background-size:24px_24px] opacity-20" />
    </div>

    <!-- Login Card -->
    <div class="relative z-10 w-full max-w-md p-6 bg-surface-container-high rounded-xl border border-outline-variant shadow-glow backdrop-blur-md">
      <!-- Logo Header -->
      <div class="flex flex-col items-center mb-6 text-center">
        <div class="w-16 h-16 rounded-xl bg-accent/10 flex items-center justify-center mb-3 border border-accent/20 text-accent font-mono text-xl font-bold shadow-glow">
          NMS
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white">NMS Command Center</h1>
        <p class="font-mono text-xs text-on-surface-variant mt-1">Требуется авторизация оператора</p>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block font-mono text-xs uppercase tracking-wider text-on-surface-variant mb-1">ID оператора</label>
          <div class="relative">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <input
              v-model="username"
              type="text"
              class="w-full bg-surface-container-lowest text-white border border-outline-variant focus:border-accent focus:ring-1 focus:ring-accent rounded-lg pl-10 pr-3 py-2.5 font-mono text-sm placeholder:text-slate-600 transition-colors"
              placeholder="operator@nms.net"
              required
            />
          </div>
        </div>

        <div>
          <label class="block font-mono text-xs uppercase tracking-wider text-on-surface-variant mb-1">Код доступа</label>
          <div class="relative">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <input
              v-model="password"
              type="password"
              class="w-full bg-surface-container-lowest text-white border border-outline-variant focus:border-accent focus:ring-1 focus:ring-accent rounded-lg pl-10 pr-3 py-2.5 font-mono text-sm placeholder:text-slate-600 transition-colors"
              placeholder="••••••••"
              required
            />
          </div>
        </div>

        <div class="flex items-center justify-between pt-1">
          <label class="flex items-center cursor-pointer gap-2">
            <input v-model="rememberMe" type="checkbox" class="w-4 h-4 rounded bg-surface-container-lowest border-outline-variant text-accent focus:ring-accent" />
            <span class="text-xs text-on-surface-variant">Запомнить терминал</span>
          </label>
          <a href="#" class="font-mono text-xs text-accent hover:underline transition-colors">Забыли код?</a>
        </div>

        <button
          type="submit"
          class="w-full mt-4 bg-accent text-slate-950 font-semibold text-sm py-3 rounded-lg hover:bg-accent-muted hover:text-white transition-all duration-150 flex items-center justify-center gap-2 shadow-glow"
        >
          <span>Установить соединение</span>
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
          </svg>
        </button>
      </form>

      <div class="mt-6 pt-4 border-t border-outline-variant text-center">
        <p class="font-mono text-[11px] text-on-surface-variant">
          Системный статус: <span class="text-tertiary font-semibold">Live</span> | Уровень: Omega-9
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref('')
const password = ref('')
const rememberMe = ref(true)

function handleLogin() {
  router.push('/')
}
</script>
