<template>
  <div class="h-screen w-full flex items-center justify-center overflow-hidden bg-background relative font-sans text-on-surface p-4">
    <!-- Server Room Background Overlay -->
    <div class="absolute inset-0 z-0 overflow-hidden">
      <div
        class="bg-cover bg-center w-full h-full opacity-55 pointer-events-none transition-all duration-500 scale-[1.02]"
        :style="{ backgroundImage: `url(${bgImage})` }"
      />
      <div class="absolute inset-0 bg-gradient-to-t from-background via-background/65 to-surface-dim/40 pointer-events-none" />
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,#10131a_100%)] pointer-events-none" />
    </div>

    <!-- Login Card -->
    <div class="relative z-10 w-full max-w-md p-6 bg-surface-container-high/90 rounded-xl border border-outline-variant shadow-glow backdrop-blur-md">
      <!-- Language Switcher Pill (Top Right) -->
      <div class="absolute top-4 right-4 flex items-center bg-surface-container border border-outline-variant/60 rounded-lg p-0.5 text-[11px] font-mono font-bold">
        <button
          @click="setLanguage('ru')"
          type="button"
          class="px-2 py-0.5 rounded transition-colors cursor-pointer"
          :class="lang === 'ru' ? 'bg-primary text-on-primary-container font-bold' : 'text-on-surface-variant hover:text-on-surface'"
        >
          RU
        </button>
        <button
          @click="setLanguage('en')"
          type="button"
          class="px-2 py-0.5 rounded transition-colors cursor-pointer"
          :class="lang === 'en' ? 'bg-primary text-on-primary-container font-bold' : 'text-on-surface-variant hover:text-on-surface'"
        >
          EN
        </button>
      </div>

      <!-- Logo Header -->
      <div class="flex flex-col items-center mb-6 text-center">
        <div class="w-16 h-16 rounded-xl bg-surface-variant flex items-center justify-center mb-3 border border-outline-variant font-mono font-bold text-2xl text-primary shadow-glow">
          NMS
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-on-surface">NMS</h1>
        <p class="font-mono text-xs text-on-surface-variant mt-1">{{ t('loginSubTitle') }}</p>
      </div>

      <!-- Error Alert -->
      <div v-if="errorKey" class="mb-4 p-3 rounded-lg bg-error/10 border border-error/30 text-error text-xs font-mono flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">warning</span>
        <span>{{ t(errorKey) }}</span>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block font-mono text-xs uppercase tracking-wider text-on-surface-variant mb-1.5">{{ t('operatorIdLabel') }}</label>
          <div class="relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">person</span>
            <input
              v-model="username"
              type="text"
              class="w-full bg-white text-surface-container-lowest border border-outline focus:border-primary focus:ring-1 focus:ring-primary rounded pl-10 pr-3 py-2 font-mono text-xs placeholder:text-outline-variant transition-colors outline-none font-medium"
              placeholder="root"
              required
            />
          </div>
        </div>

        <div>
          <label class="block font-mono text-xs uppercase tracking-wider text-on-surface-variant mb-1.5">{{ t('accessCodeLabel') }}</label>
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
            <span class="text-xs text-on-surface-variant">{{ t('rememberMe') }}</span>
          </label>
          <a href="#" @click.prevent="showForgotNotice" class="font-mono text-xs text-primary hover:text-primary-fixed transition-colors">{{ t('forgotCode') }}</a>
        </div>

        <button
          type="submit"
          :disabled="isLoading"
          class="w-full mt-4 bg-primary text-on-primary font-bold text-xs py-3 rounded-lg hover:bg-primary-container transition-colors flex items-center justify-center gap-2 shadow-glow disabled:opacity-50 cursor-pointer"
        >
          <span v-if="!isLoading">{{ t('establishConnection') }}</span>
          <span v-else>{{ t('authenticating') }}</span>
          <span v-if="!isLoading" class="material-symbols-outlined text-[18px]">login</span>
        </button>
      </form>

      <!-- System Status Footer -->
      <div class="mt-6 pt-4 border-t border-outline-variant/60 text-center">
        <p class="font-mono text-[11px] text-on-surface-variant">
          {{ t('systemStatusLive') }}
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
import { useI18n, type TranslationKey } from '@/core/i18n'

const router = useRouter()
const { t, lang, setLanguage } = useI18n()

const username = ref('root')
const password = ref('')
const rememberMe = ref(true)
const isLoading = ref(false)
const errorKey = ref<TranslationKey | null>(null)

function showForgotNotice() {
  alert(t('forgotNotice'))
}

async function handleLogin() {
  isLoading.value = true
  errorKey.value = null
  try {
    const res = await apiLogin(username.value, password.value)
    if (res?.token && res?.user) {
      setAuthSession(res.token, res.user)
      if (res.must_change_password || res.user.must_change_password) {
        router.push('/settings/profile?must_change=true')
      } else {
        router.push('/')
      }
    } else {
      errorKey.value = 'serverError'
    }
  } catch (err: any) {
    if (err?.response?.status === 401 || err?.response?.status === 400) {
      errorKey.value = 'invalidCredentials'
    } else {
      errorKey.value = 'serverError'
    }
  } finally {
    isLoading.value = false
  }
}
</script>

