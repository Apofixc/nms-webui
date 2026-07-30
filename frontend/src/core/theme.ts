export type ThemeMode = 'system' | 'dark' | 'light'

const THEME_KEY = 'nms_theme'

export function getStoredTheme(): ThemeMode {
  const theme = localStorage.getItem(THEME_KEY)
  if (theme === 'light' || theme === 'dark' || theme === 'system') {
    return theme
  }
  return 'dark'
}

export function applyTheme(theme: ThemeMode): void {
  const isDark =
    theme === 'dark' ||
    (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)

  if (isDark) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

export function setStoredTheme(theme: ThemeMode): void {
  localStorage.setItem(THEME_KEY, theme)
  applyTheme(theme)
}

export function initTheme(): void {
  const theme = getStoredTheme()
  applyTheme(theme)

  // Слушатель изменения системной темы
  if (typeof window !== 'undefined' && window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (getStoredTheme() === 'system') {
        applyTheme('system')
      }
    })
  }
}
