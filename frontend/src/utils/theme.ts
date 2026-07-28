/**
 * App-wide appearance & regionality management (Theme, Density, Timezone).
 */

export function applyTheme(theme: string) {
  localStorage.setItem('nms_theme', theme)
  const root = document.documentElement
  root.classList.remove('theme-dark', 'theme-light')

  if (theme === 'light') {
    root.classList.add('theme-light')
  } else if (theme === 'dark') {
    root.classList.add('theme-dark')
  } else {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    if (isDark) {
      root.classList.add('theme-dark')
    } else {
      root.classList.add('theme-light')
    }
  }
}

export function applyDensity(density: string) {
  localStorage.setItem('nms_density', density)
  const root = document.documentElement
  root.classList.remove('density-compact', 'density-standard', 'density-relaxed')
  root.classList.add(`density-${density}`)
}

export function applyTimezone(tz: string) {
  localStorage.setItem('nms_timezone', tz)
}

export function formatTimeWithTimezone(date: Date, tz: string): string {
  let offsetHours = 0
  let label = 'UTC'

  if (tz === 'utc+3') {
    offsetHours = 3
    label = 'MSK'
  } else if (tz === 'est') {
    offsetHours = -5
    label = 'EST'
  } else {
    offsetHours = 0
    label = 'UTC'
  }

  const utcMs = date.getTime() + date.getTimezoneOffset() * 60000
  const targetDate = new Date(utcMs + offsetHours * 3600000)

  const hours = String(targetDate.getHours()).padStart(2, '0')
  const minutes = String(targetDate.getMinutes()).padStart(2, '0')
  const seconds = String(targetDate.getSeconds()).padStart(2, '0')

  return `${hours}:${minutes}:${seconds} ${label}`
}

export function initAppSettings() {
  const savedTheme = localStorage.getItem('nms_theme') || 'dark'
  const savedDensity = localStorage.getItem('nms_density') || 'standard'
  const savedTz = localStorage.getItem('nms_timezone') || 'utc+3'

  applyTheme(savedTheme)
  applyDensity(savedDensity)
  applyTimezone(savedTz)
}
