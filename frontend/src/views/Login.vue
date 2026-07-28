<template>
  <div class="h-screen w-full flex items-center justify-center overflow-hidden bg-background relative font-sans text-on-surface p-4">
    <!-- Server Room Background Overlay -->
    <div class="absolute inset-0 z-0">
      <div
        class="bg-cover bg-center w-full h-full opacity-35 pointer-events-none transition-opacity"
        :style="{ backgroundImage: `url(${bgImage})` }"
      />
      <div class="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent pointer-events-none" />
    </div>

    <!-- Login Card -->
    <div class="relative z-10 w-full max-w-md p-6 bg-surface-container-high/90 rounded-xl border border-outline-variant shadow-glow backdrop-blur-md">
      <!-- Logo Header -->
      <div class="flex flex-col items-center mb-6 text-center">
        <div class="w-16 h-16 rounded-xl bg-surface-variant flex items-center justify-center mb-3 border border-outline-variant font-mono font-bold text-2xl text-primary shadow-glow">
          NMS
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-on-surface">NMS</h1>
        <p class="font-mono text-xs text-on-surface-variant mt-1">Authentication Required / Авторизация</p>
      </div>

      <!-- Error Alert -->
      <div v-if="errorMessage" class="mb-4 p-3 rounded-lg bg-error/10 border border-error/30 text-error text-xs font-mono flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">warning</span>
        <span>{{ errorMessage }}</span>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block font-mono text-xs uppercase tracking-wider text-on-surface-variant mb-1.5">Operator ID / Идентификатор</label>
          <div class="relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">person</span>
            <input
              v-model="username"
              type="text"
              class="w-full bg-white text-surface-container-lowest border border-outline focus:border-primary focus:ring-1 focus:ring-primary rounded pl-10 pr-3 py-2 font-mono text-xs placeholder:text-outline-variant transition-colors outline-none font-medium"
              placeholder="e.g. admin"
              required
            />
          </div>
        </div>

        <div>
          <label class="block font-mono text-xs uppercase tracking-wider text-on-surface-variant mb-1.5">Access Code / Пароль</label>
          <div class="relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">lock</span>
            <input
              v-model="password"
              type="password"
              class="w-full bg-white text-surface-container-lowest border border-outline focus:border-primary focus:ring-1 focus:ring-primary rounded pl-10 pr-3 py-2 font-mono text-xs placeholder:text-outline-variant transition-colors outline-none font-medium"
              placeholder="••••••••"
              required
            />
          </div>
        </div>

        <!-- Options: Remember Me & Forgot Password -->
        <div class="flex items-center justify-between pt-1">
          <label class="flex items-center cursor-pointer gap-2">
            <input v-model="rememberMe" type="checkbox" class="rounded border-outline-variant bg-surface-container-high text-primary focus:ring-primary" />
            <span class="text-xs text-on-surface-variant">Запомнить меня</span>
          </label>
          <a href="#" @click.prevent="showForgotNotice" class="font-mono text-xs text-primary hover:text-primary-fixed transition-colors">Забыли код?</a>
        </div>

        <button
          type="submit"
          :disabled="isLoading"
          class="w-full mt-4 bg-primary text-on-primary font-bold text-xs py-3 rounded-lg hover:bg-primary-container transition-colors flex items-center justify-center gap-2 shadow-glow disabled:opacity-50 cursor-pointer"
        >
          <span v-if="!isLoading">Establish Connection / Войти</span>
          <span v-else>Авторизация...</span>
          <span v-if="!isLoading" class="material-symbols-outlined text-[18px]">login</span>
        </button>
      </form>

      <!-- System Status Footer -->
      <div class="mt-6 pt-4 border-t border-outline-variant/60 text-center">
        <p class="font-mono text-[11px] text-on-surface-variant">
          System Status: <span class="text-tertiary font-bold">Live</span> | Sec-Level: <span class="text-primary font-bold">Omega</span>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import bgImage from '@/assets/server_room.jpg'
import { apiLogin } from '@/core/api'
import { setAuthSession } from '@/core/auth'

const router = useRouter()
const username = ref('admin')
const password = ref('')
const rememberMe = ref(true)
const isLoading = ref(false)
const errorMessage = ref('')

function showForgotNotice() {
  alert('Для восстановления доступа обратитесь к системному администратору (Superuser).')
}

async function handleLogin() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const res = await apiLogin(username.value, password.value)
    if (res?.token && res?.user) {
      setAuthSession(res.token, res.user)
      router.push('/')
    } else {
      errorMessage.value = 'Ошибка ответа сервера'
    }
  } catch (err: any) {
    errorMessage.value = err?.response?.data?.detail || 'Неверный логин или пароль (default: admin / admin)'
  } finally {
    isLoading.value = false
  }
}
</script>

