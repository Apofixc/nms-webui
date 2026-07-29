import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { clearAuthSession, getStoredUser, getStoredToken } from '@/core/auth'
import { apiFetchSecuritySettings, apiLogout } from '@/core/api'

export function useIdleTimeout() {
  const router = useRouter()
  const isIdleWarningOpen = ref(false)
  const countdownSeconds = ref(30)
  
  let inactivityLimitMs = 30 * 60 * 1000 // 30 mins default
  let lastActivityTime = Date.now()
  let checkIntervalTimer: any = null
  let countdownTimer: any = null

  async function fetchTimeoutConfig() {
    try {
      const settings = await apiFetchSecuritySettings()
      if (settings?.inactivity_timeout_mins) {
        const mins = Number(settings.inactivity_timeout_mins)
        if (mins > 0) {
          inactivityLimitMs = mins * 60 * 1000
        }
      }
    } catch {
      // use default
    }
  }

  function resetActivity() {
    if (isIdleWarningOpen.value) return // If warning modal is open, require clicking "Extend"
    lastActivityTime = Date.now()
  }

  function extendSession() {
    isIdleWarningOpen.value = false
    lastActivityTime = Date.now()
    if (countdownTimer) clearInterval(countdownTimer)
  }

  async function forceLogout() {
    isIdleWarningOpen.value = false
    if (countdownTimer) clearInterval(countdownTimer)
    if (checkIntervalTimer) clearInterval(checkIntervalTimer)

    try {
      await apiLogout()
    } catch {
      // ignore
    } finally {
      clearAuthSession()
      router.push('/login')
    }
  }

  function checkIdle() {
    const user = getStoredUser()
    const token = getStoredToken()
    if (token === 'system_disabled_auth' || user?.auth_enabled === false) {
      return
    }

    const elapsed = Date.now() - lastActivityTime
    const remainingMs = inactivityLimitMs - elapsed

    if (remainingMs <= 30000 && !isIdleWarningOpen.value && window.location.pathname !== '/login') {
      isIdleWarningOpen.value = true
      countdownSeconds.value = Math.max(0, Math.floor(remainingMs / 1000))
      
      countdownTimer = setInterval(() => {
        countdownSeconds.value--
        if (countdownSeconds.value <= 0) {
          forceLogout()
        }
      }, 1000)
    }
  }

  const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart']

  onMounted(() => {
    fetchTimeoutConfig()
    events.forEach(evt => window.addEventListener(evt, resetActivity, { passive: true }))
    checkIntervalTimer = setInterval(checkIdle, 5000)
  })

  onUnmounted(() => {
    events.forEach(evt => window.removeEventListener(evt, resetActivity))
    if (checkIntervalTimer) clearInterval(checkIntervalTimer)
    if (countdownTimer) clearInterval(countdownTimer)
  })

  return {
    isIdleWarningOpen,
    countdownSeconds,
    extendSession,
    forceLogout
  }
}
