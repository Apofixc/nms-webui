import { ref, computed } from 'vue'

export type Language = 'ru' | 'en'

const savedLang = (localStorage.getItem('nms_lang') as Language) || 'ru'
export const currentLang = ref<Language>(savedLang)

export function setLanguage(lang: Language) {
  currentLang.value = lang
  localStorage.setItem('nms_lang', lang)
}

export const translations = {
  ru: {
    // Navigation & Shell
    dashboard: 'Дашборд',
    topology: 'Топология сети',
    faults: 'Сбои & Алармы',
    performance: 'Производительность',
    documentation: 'Документация',
    settings: 'Настройки',
    configuration: 'Конфигурация',
    userProfile: 'Профиль пользователя',
    usersManagement: 'Управление пользователями',
    accessControl: 'Управление доступом',
    moduleManagement: 'Управление модулями',
    accessIdentity: 'Доступ и Идентификация',
    configGroups: 'Группы конфигурации',
    searchPlaceholder: 'Поиск ресурсов NMS...',
    healthOptimal: 'Состояние NMS: Оптимально',
    healthOffline: 'Состояние NMS: Офлайн',
    superuser: 'СУПЕРПОЛЬЗОВАТЕЛЬ',

    // Dashboard
    activeFaults: 'Активные сбои',
    topologyMap: 'Топология сети NMS',
    throughput: 'Пропускная способность (Gbps)',
    deviceStatus: 'Состояние устройств сети',
    modulesCount: 'Модули NMS',
    manage: 'Управление',
    zoomIn: 'ПРИБЛИЗИТЬ',
    zoomOut: 'ОТДАЛИТЬ',

    // Actions & Buttons
    exportLogs: 'Экспорт логов',
    applyChanges: 'Применить изменения',
    scanModules: 'Сканировать новые модули',
    addNewRole: 'Добавить роль',
    addNewUser: 'Добавить пользователя',
    saveChanges: 'Сохранить изменения',
    saveProfile: 'Сохранить профиль',
    changePassword: 'Сменить пароль',
    upload: 'Загрузить',
    reset: 'Сбросить',
    terminateSessions: 'Завершить остальные сессии',

    // Headers & Titles
    globalAuth: 'Глобальная аутентификация',
    securityPolicies: 'Политики безопасности',
    securityAuditLog: 'Журнал аудита безопасности',
    rolesManagement: 'Управление ролями',
    permissionsMatrix: 'Матрица разрешений',
    moduleRegistry: 'Реестр модулей',
    coreEngineDetails: 'Сведения о ядре',
    personalInfo: 'Персональная информация',
    appearanceRegionality: 'Внешний вид и региональность',
    activeSessions: 'Активные сессии',

    // Form Labels & Texts
    fullName: 'Полное имя',
    department: 'Отдел',
    role: 'Роль',
    emailAddress: 'Email адрес',
    theme: 'Тема',
    language: 'Язык',
    timezone: 'Часовой пояс',
    tableDensity: 'Плотность таблиц',
    currentPassword: 'Текущий пароль',
    newPassword: 'Новый пароль',
    confirmPassword: 'Подтвердите новый пароль',

    // Statuses
    active: 'Активен',
    disabled: 'Отключен',
    online: 'Онлайн',
    offline: 'Офлайн',
    locked: 'Заблокирован',
    success: 'Успешно',
    failure: 'Ошибка'
  },
  en: {
    // Navigation & Shell
    dashboard: 'Dashboard',
    topology: 'Network Topology',
    faults: 'Fault Management',
    performance: 'Performance',
    documentation: 'Documentation',
    settings: 'Settings',
    configuration: 'Configuration',
    userProfile: 'User Profile',
    usersManagement: 'Users Management',
    accessControl: 'Access Control',
    moduleManagement: 'Module Management',
    accessIdentity: 'Access & Identity',
    configGroups: 'Configuration Groups',
    searchPlaceholder: 'Search NMS resources...',
    healthOptimal: 'NMS Health: Optimal',
    healthOffline: 'NMS Health: Offline',
    superuser: 'SUPERUSER',

    // Dashboard
    activeFaults: 'Active Faults',
    topologyMap: 'NMS Network Topology',
    throughput: 'Network Throughput (Gbps)',
    deviceStatus: 'Network Devices Status',
    modulesCount: 'NMS Modules',
    manage: 'Manage',
    zoomIn: 'ZOOM IN',
    zoomOut: 'ZOOM OUT',

    // Actions & Buttons
    exportLogs: 'Export Logs',
    applyChanges: 'Apply Changes',
    scanModules: 'Scan for New Modules',
    addNewRole: 'Add New Role',
    addNewUser: 'Add New User',
    saveChanges: 'Save Changes',
    saveProfile: 'Save Profile',
    changePassword: 'Change Password',
    upload: 'Upload',
    reset: 'Reset',
    terminateSessions: 'Terminate All Other Sessions',

    // Headers & Titles
    globalAuth: 'Global Authentication',
    securityPolicies: 'Security Policies',
    securityAuditLog: 'Security Audit Log',
    rolesManagement: 'Roles Management',
    permissionsMatrix: 'Permissions Matrix',
    moduleRegistry: 'Module Registry',
    coreEngineDetails: 'Core Engine Details',
    personalInfo: 'Personal Information',
    appearanceRegionality: 'Appearance & Regionality',
    activeSessions: 'Active Sessions',

    // Form Labels & Texts
    fullName: 'Full Name',
    department: 'Department',
    role: 'Role',
    emailAddress: 'Email Address',
    theme: 'Theme',
    language: 'Language',
    timezone: 'Timezone',
    tableDensity: 'Table Density',
    currentPassword: 'Current Password',
    newPassword: 'New Password',
    confirmPassword: 'Confirm New Password',

    // Statuses
    active: 'Active',
    disabled: 'Disabled',
    online: 'Online',
    offline: 'Offline',
    locked: 'Locked',
    success: 'Success',
    failure: 'Failure'
  }
} as const

export type TranslationKey = keyof typeof translations.ru

export function t(key: TranslationKey): string {
  return translations[currentLang.value][key] || translations.ru[key] || key
}

export function useI18n() {
  const tComputed = computed(() => (key: TranslationKey) => t(key))
  return {
    lang: currentLang,
    setLanguage,
    t: tComputed
  }
}
