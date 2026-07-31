import { translations, t, currentLang, setLanguage, getRoleTitle, translatePermissionCategory, translateModuleName, DEFAULT_LANG } from '../i18n'

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`)
  }
}

console.log('Testing i18n subsystem...')

assert(DEFAULT_LANG === 'en', 'DEFAULT_LANG should be en')

// 1. Verify key symmetry between RU and EN
const ruKeys = Object.keys(translations.ru) as Array<keyof typeof translations.ru>
const enKeys = Object.keys(translations.en) as Array<keyof typeof translations.en>

const missingInEn = ruKeys.filter((k) => !(k in translations.en))
const missingInRu = enKeys.filter((k) => !(k in translations.ru))

assert(missingInEn.length === 0, `Keys in RU missing in EN: ${missingInEn.join(', ')}`)
assert(missingInRu.length === 0, `Keys in EN missing in RU: ${missingInRu.join(', ')}`)

for (const key of ruKeys) {
  const ruVal = String(translations.ru[key] ?? '')
  const enVal = String(translations.en[key] ?? '')
  assert(ruVal.trim().length > 0, `RU translation for "${key}" is empty`)
  assert(enVal.trim().length > 0, `EN translation for "${key}" is empty`)
}

// 2. Test switching language & basic translation
setLanguage('ru')
assert(currentLang.value === 'ru', 'Language should be set to ru')
assert(t('dashboard') === 'Дашборд', 'RU translation for dashboard should be Дашборд')

setLanguage('en')
assert(currentLang.value === 'en', 'Language should be set to en')
assert(t('dashboard') === 'Dashboard', 'EN translation for dashboard should be Dashboard')

// 3. Test parameter substitution
setLanguage('ru')
assert(t('userSessionsTerminated', { name: 'Иван' }) === 'Все сессии пользователя Иван завершены', 'RU parameter interpolation failed')

setLanguage('en')
assert(t('userSessionsTerminated', { name: 'John' }) === 'Terminated all sessions for John', 'EN parameter interpolation failed')

// 4. Test pluralization
setLanguage('ru')
assert(t('bulkActionSuccess', { count: 1 }) === 'Массовое действие выполнено (1 пользователь)', 'RU plural 1 failed')
assert(t('bulkActionSuccess', { count: 2 }) === 'Массовое действие выполнено (2 пользователя)', 'RU plural 2 failed')
assert(t('bulkActionSuccess', { count: 5 }) === 'Массовое действие выполнено (5 пользователей)', 'RU plural 5 failed')

setLanguage('en')
assert(t('bulkActionSuccess', { count: 1 }) === 'Bulk action applied (1 user)', 'EN plural 1 failed')
assert(t('bulkActionSuccess', { count: 5 }) === 'Bulk action applied (5 users)', 'EN plural 5 failed')

// 5. Test role helpers
setLanguage('ru')
assert(getRoleTitle('Superuser') === 'Суперадминистратор', 'getRoleTitle superuser in RU')
assert(getRoleTitle('admin') === 'Администратор', 'getRoleTitle admin in RU')

setLanguage('en')
assert(getRoleTitle('Superuser') === 'Superuser', 'getRoleTitle superuser in EN')
assert(getRoleTitle('admin') === 'Administrator', 'getRoleTitle admin in EN')

// 6. Test module & category helpers
setLanguage('ru')
assert(translatePermissionCategory('system') === 'Система', 'Permission category system in RU')
assert(translateModuleName('Core Engine') === 'Ядро системы', 'Module name Core Engine in RU')

setLanguage('en')
assert(translatePermissionCategory('system') === 'System', 'Permission category system in EN')
assert(translateModuleName('Core Engine') === 'Core Engine', 'Module name Core Engine in EN')

console.log('All i18n tests passed successfully!')
