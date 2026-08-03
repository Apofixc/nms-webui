import { ref } from 'vue'
import { translations } from './locales'

export type Language = 'ru' | 'en'

export const DEFAULT_LANG: Language = 'en'

function detectBrowserLanguage(): Language {
  if (typeof navigator !== 'undefined' && navigator.language) {
    if (navigator.language.toLowerCase().startsWith('ru')) {
      return 'ru'
    }
  }
  return DEFAULT_LANG
}

const defaultLang: Language = detectBrowserLanguage()
const savedLang = typeof localStorage !== 'undefined' ? (localStorage.getItem('nms_lang') as Language) : null
export const currentLang = ref<Language>(savedLang || defaultLang)

export function setLanguage(lang: Language) {
  currentLang.value = lang
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('nms_lang', lang)
  }
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lang
    window.dispatchEvent(new CustomEvent('nms-language-changed', { detail: { lang } }))
  }
}

if (typeof document !== 'undefined') {
  document.documentElement.lang = currentLang.value
}

export { translations }

export function registerModuleTranslations(moduleLocales: Record<string, Record<string, string>>) {
  if (!moduleLocales) return
  Object.entries(moduleLocales).forEach(([lang, dict]) => {
    if (!dict) return
    const targetDict = (translations as Record<string, any>)[lang]
    if (targetDict) {
      Object.assign(targetDict, dict)
    } else {
      (translations as Record<string, any>)[lang] = { ...dict }
    }
  })
}

export type TranslationKey = keyof typeof translations[typeof DEFAULT_LANG] | (string & {})

function getLanguageChain(lang: string): string[] {
  const chain = [lang]
  if (DEFAULT_LANG !== lang && DEFAULT_LANG in translations) {
    chain.push(DEFAULT_LANG)
  }
  for (const l of Object.keys(translations)) {
    if (!chain.includes(l)) {
      chain.push(l)
    }
  }
  return chain
}

export function t(key: string, params?: Record<string, string | number>): string {
  const langChain = getLanguageChain(currentLang.value)
  let targetKey = key

  if (params && typeof params.count === 'number') {
    try {
      const pr = new Intl.PluralRules(currentLang.value)
      const rule = pr.select(params.count)
      const pluralKey = `${key}_${rule}`
      for (const l of langChain) {
        const dict = (translations as Record<string, any>)[l]
        if (dict && dict[pluralKey] !== undefined) {
          targetKey = pluralKey
          break
        }
      }
    } catch {
      // fallback to original key
    }
  }

  let str = ''
  for (const l of langChain) {
    const dict = (translations as Record<string, any>)[l]
    if (dict && dict[targetKey] !== undefined) {
      str = dict[targetKey]
      break
    }
  }

  if (!str && targetKey.includes('.')) {
    const parts = targetKey.split('.')
    for (const l of langChain) {
      const dict = (translations as Record<string, any>)[l]
      if (!dict) continue
      const val = parts.reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : undefined), dict)
      if (val !== undefined) {
        str = String(val)
        break
      }
    }
  }

  if (!str) {
    str = targetKey
  }

  if (params && typeof str === 'string') {
    Object.entries(params).forEach(([k, v]) => {
      str = str.split(`{${k}}`).join(String(v))
    })
  }

  return str
}

const ROLE_KEYS: Array<{ id: string; titleKey: TranslationKey; descKey: TranslationKey }> = [
  { id: 'superuser', titleKey: 'roleSuperuser', descKey: 'superuserDesc' },
  { id: 'admin', titleKey: 'roleAdmin', descKey: 'adminDesc' },
  { id: 'operator', titleKey: 'roleOperator', descKey: 'operatorDesc' },
  { id: 'viewer', titleKey: 'roleViewer', descKey: 'viewerDesc' },
]

function findMatchingRole(roleName: string) {
  if (!roleName) return null
  const lower = roleName.toLowerCase().trim()
  for (const role of ROLE_KEYS) {
    if (lower.includes(role.id)) return role
    for (const langDict of Object.values(translations)) {
      const title = (langDict as any)[role.titleKey]
      if (title && lower.includes(title.toLowerCase())) {
        return role
      }
    }
  }
  return null
}

export function getRoleTitle(roleName: string): string {
  const match = findMatchingRole(roleName)
  return match ? t(match.titleKey) : roleName
}

export function getRoleDescription(roleName: string, defaultDesc?: string): string {
  const match = findMatchingRole(roleName)
  return match ? t(match.descKey) : (defaultDesc || '')
}

const CATEGORY_IDS = ['system', 'users', 'access', 'settings', 'modules', 'audit']

export function translatePermissionCategory(category: string): string {
  if (!category) return ''
  const catLower = category.toLowerCase().trim()

  for (const catId of CATEGORY_IDS) {
    const key = `permCategory_${catId}` as TranslationKey
    if (catLower === catId || catLower === key.toLowerCase()) {
      return t(key)
    }
    for (const langDict of Object.values(translations)) {
      const title = (langDict as any)[key]
      if (title && catLower === title.toLowerCase()) {
        return t(key)
      }
    }
  }

  for (const langDict of Object.values(translations)) {
    const moduleFallback = ((langDict as any).moduleFallback || '').toLowerCase()
    if (moduleFallback && catLower.startsWith(`${moduleFallback} `)) {
      const modName = category.slice(moduleFallback.length + 1).trim()
      return t('moduleCategoryFormat', { name: modName })
    }
  }

  return category
}

export function translatePermissionName(permId: string, fallbackName?: string): string {
  const key = `permName_${permId}`
  const val = t(key)
  return val !== key ? val : (fallbackName || permId)
}

export function translatePermissionDesc(permId: string, fallbackDesc?: string): string {
  const key = `permDesc_${permId}`
  const val = t(key)
  return val !== key ? val : (fallbackDesc || '')
}

export function translateModuleName(nameOrId: string): string {
  if (!nameOrId) return ''
  const val = t(nameOrId)
  if (val && val !== nameOrId) {
    return val
  }
  const lower = nameOrId.toLowerCase().trim()
  if (lower === 'core engine' || lower === 'coreenginename') {
    return t('coreEngineName')
  }
  for (const langDict of Object.values(translations)) {
    const coreName = (langDict as any).coreEngineName
    if (coreName && lower === coreName.toLowerCase()) {
      return t('coreEngineName')
    }
  }
  return nameOrId
}

const API_ERROR_KEYS: Array<{ key: TranslationKey; keywords: string[] }> = [
  { key: 'apiError_invalidCredentials', keywords: ['credentials'] },
  { key: 'apiError_userExists', keywords: ['exists'] },
  { key: 'apiError_permissionDenied', keywords: ['permission'] },
  { key: 'apiError_cannotDeleteSelf', keywords: ['own account'] },
  { key: 'apiError_cannotDeleteSuperuser', keywords: ['superuser'] },
  { key: 'apiError_roleInUse', keywords: ['assigned'] },
  { key: 'apiError_passwordTooWeak', keywords: ['weak'] },
]

export function translateApiError(err: any, fallbackKey?: string): string {
  const detail = err?.response?.data?.detail || err?.message || ''
  if (typeof detail === 'string' && detail.trim()) {
    const dLower = detail.toLowerCase()
    for (const item of API_ERROR_KEYS) {
      if (item.keywords.some((kw) => dLower.includes(kw))) {
        return t(item.key)
      }
      for (const langDict of Object.values(translations)) {
        const transText = (langDict as any)[item.key]
        if (transText && dLower.includes(transText.toLowerCase())) {
          return t(item.key)
        }
      }
    }
    return detail
  }
  return fallbackKey ? t(fallbackKey) : t('serverError')
}

export function useI18n() {
  return {
    lang: currentLang,
    setLanguage,
    t: (key: TranslationKey, params?: Record<string, string | number>) => t(key, params),
    getRoleTitle,
    getRoleDescription,
    translatePermissionCategory,
    translatePermissionName,
    translatePermissionDesc,
    translateModuleName,
    translateApiError,
    formatDateTime: (date: string | number | Date, options?: Intl.DateTimeFormatOptions) => {
      return new Date(date).toLocaleString(currentLang.value, options)
    },
    formatTime: (date: string | number | Date, options?: Intl.DateTimeFormatOptions) => {
      return new Date(date).toLocaleTimeString(currentLang.value, options)
    }
  }
}
