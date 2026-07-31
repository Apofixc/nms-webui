import { describe, test, expect } from 'vitest'
import { translations, t, currentLang, setLanguage, getRoleTitle, translatePermissionCategory, translateModuleName, registerModuleTranslations, DEFAULT_LANG } from '../i18n'

describe('i18n subsystem', () => {
  test('default language is en', () => {
    expect(DEFAULT_LANG).toBe('en')
  })

  test('key symmetry between RU and EN', () => {
    const ruKeys = Object.keys(translations.ru) as Array<keyof typeof translations.ru>
    const enKeys = Object.keys(translations.en) as Array<keyof typeof translations.en>

    const missingInEn = ruKeys.filter((k) => !(k in translations.en))
    const missingInRu = enKeys.filter((k) => !(k in translations.ru))

    expect(missingInEn).toEqual([])
    expect(missingInRu).toEqual([])

    for (const key of ruKeys) {
      const ruVal = String(translations.ru[key] ?? '')
      const enVal = String(translations.en[key] ?? '')
      expect(ruVal.trim().length).toBeGreaterThan(0)
      expect(enVal.trim().length).toBeGreaterThan(0)
    }
  })

  test('switching language and basic translation', () => {
    setLanguage('ru')
    expect(currentLang.value).toBe('ru')
    expect(t('dashboard')).toBe('Дашборд')

    setLanguage('en')
    expect(currentLang.value).toBe('en')
    expect(t('dashboard')).toBe('Dashboard')
  })

  test('parameter substitution', () => {
    setLanguage('ru')
    expect(t('userSessionsTerminated', { name: 'Иван' })).toBe('Все сессии пользователя Иван завершены')

    setLanguage('en')
    expect(t('userSessionsTerminated', { name: 'John' })).toBe('Terminated all sessions for John')
  })

  test('pluralization', () => {
    setLanguage('ru')
    expect(t('bulkActionSuccess', { count: 1 })).toBe('Массовое действие выполнено (1 пользователь)')
    expect(t('bulkActionSuccess', { count: 2 })).toBe('Массовое действие выполнено (2 пользователя)')
    expect(t('bulkActionSuccess', { count: 5 })).toBe('Массовое действие выполнено (5 пользователей)')

    setLanguage('en')
    expect(t('bulkActionSuccess', { count: 1 })).toBe('Bulk action applied (1 user)')
    expect(t('bulkActionSuccess', { count: 5 })).toBe('Bulk action applied (5 users)')
  })

  test('role helpers', () => {
    setLanguage('ru')
    expect(getRoleTitle('Superuser')).toBe('Суперадминистратор')
    expect(getRoleTitle('admin')).toBe('Администратор')

    setLanguage('en')
    expect(getRoleTitle('Superuser')).toBe('Superuser')
    expect(getRoleTitle('admin')).toBe('Administrator')
  })

  test('module and category helpers', () => {
    setLanguage('ru')
    expect(translatePermissionCategory('system')).toBe('Система')
    expect(translateModuleName('Core Engine')).toBe('Ядро системы')

    setLanguage('en')
    expect(translatePermissionCategory('system')).toBe('System')
    expect(translateModuleName('Core Engine')).toBe('Core Engine')
  })

  test('dynamic module translations registration', () => {
    registerModuleTranslations({
      ru: { test_module_title: 'Тестовый Модуль' },
      en: { test_module_title: 'Test Module' },
    })
    setLanguage('ru')
    expect(t('test_module_title')).toBe('Тестовый Модуль')
    setLanguage('en')
    expect(t('test_module_title')).toBe('Test Module')
  })
})


