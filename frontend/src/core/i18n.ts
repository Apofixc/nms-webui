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

    // Subtitles & Descriptions
    accessIdentitySub: 'Управление глобальными политиками аутентификации и мониторинг событий безопасности.',
    globalAuthDesc: 'Главный переключатель авторизационной подсистемы. Отключение переводит доступ в локальный режим.',
    systemAuth: 'СИСТЕМНАЯ АВТОРИЗАЦИЯ',
    mandatoryPassword: 'Принудительная смена пароля',
    mandatoryPasswordDesc: 'Требует от новых пользователей обновить учётные данные при первом входе.',
    rateLimitingLockout: 'Ограничение частоты и блокировка',
    maxLoginAttempts: 'Макс. попыток входа',
    lockoutDuration: 'Длительность блокировки (мин)',
    liveMonitor: 'Живой мониторинг',
    timestamp: 'Время',
    eventType: 'Тип события',
    user: 'Пользователь',
    ipAddress: 'IP Адрес',
    status: 'Статус',
    loginAttempt: 'Попытка входа',
    userCreated: 'Создан пользователь',
    roleModified: 'Роль изменена',

    rolesMgmtSub: 'Определение и управление пользовательскими ролями доступа.',
    roleName: 'Имя роли',
    description: 'Описание',
    usersCount: 'Пользователи',
    actions: 'Действия',
    permMatrixSub: 'Детализированный контроль доступа по ролям для ресурсов системы.',
    permission: 'Разрешение',
    secPoliciesSub: 'Управление глобальными настройками безопасности и сессий.',
    loginRateLimiting: 'Ограничение частоты входа',
    maxAttemptsLabel: 'Макс. попыток',
    failedLogins: 'неудачных входов',
    lockoutDurationLabel: 'Длительность блокировки',
    minutes: 'минут',
    sessionLifecycle: 'Жизненный цикл сессии',
    sessionTtl: 'TTL сессии (время жизни)',
    hours: 'часов',
    inactivityTimeout: 'Тайм-аут бездействия',
    forceMfa: 'Принудительная 2FA (MFA)',
    mfaSub: 'Обязательная двухфакторная аутентификация для всех ролей.',

    filterOperators: 'Фильтр операторов...',
    showingOperators: 'Отображается операторов',
    usernameId: 'Логин / ID',
    endOfUserList: 'Конец списка активных операторов.',

    moduleMgmtSub: 'Мониторинг и управление сервисными модулями системы.',
    totalModules: 'Всего модулей',
    standby: 'В ожидании',
    warning: 'Предупреждение',
    filter: 'Фильтр:',
    all: 'ВСЕ',
    selected: 'Модулей выбрано',
    restartSelected: 'Перезапустить выбранные',
    stopSelected: 'Остановить выбранные',
    moduleName: 'Имя модуля',
    uptime: 'Время работы',
    version: 'Версия',
    cpuUsage: 'Загрузка ЦП',
    memory: 'Память',
    logLevel: 'Уровень логов',
    dependencies: 'Зависимости',
    restartModule: 'ПЕРЕЗАПУСТИТЬ МОДУЛЬ',
    viewLogs: 'ПРОСМОТРЕТЬ ЛОГИ',
    stopService: 'ОСТАНОВИТЬ СЕРВИС',

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

    // Subtitles & Descriptions
    accessIdentitySub: 'Manage global authentication policies and monitor security events.',
    globalAuthDesc: 'Master switch for the system-wide authorization module. Disabling this defaults all access to local bypass mode.',
    systemAuth: 'SYSTEM AUTHORIZATION',
    mandatoryPassword: 'Mandatory Password Change',
    mandatoryPasswordDesc: 'Forces all new users to update credentials upon initial entry.',
    rateLimitingLockout: 'Rate Limiting & Lockout',
    maxLoginAttempts: 'Max Login Attempts',
    lockoutDuration: 'Lockout Duration (min)',
    liveMonitor: 'Live Monitor',
    timestamp: 'Timestamp',
    eventType: 'Event Type',
    user: 'User',
    ipAddress: 'IP Address',
    status: 'Status',
    loginAttempt: 'Login Attempt',
    userCreated: 'User Created',
    roleModified: 'Role Modified',

    rolesMgmtSub: 'Define and manage custom access roles.',
    roleName: 'Role Name',
    description: 'Description',
    usersCount: 'Users',
    actions: 'Actions',
    permMatrixSub: 'Granular role-based access control for system resources.',
    permission: 'Permission',
    secPoliciesSub: 'Manage global security settings for authentication and sessions.',
    loginRateLimiting: 'Login Rate Limiting',
    maxAttemptsLabel: 'Max Attempts',
    failedLogins: 'failed logins',
    lockoutDurationLabel: 'Lockout Duration',
    minutes: 'minutes',
    sessionLifecycle: 'Session Lifecycle',
    sessionTtl: 'Session TTL (Time-to-Live)',
    hours: 'hours',
    inactivityTimeout: 'Inactivity Timeout',
    forceMfa: 'Force Multi-Factor Authentication (MFA)',
    mfaSub: 'Mandatory 2FA for all user roles.',

    filterOperators: 'Filter operators...',
    showingOperators: 'Showing Active Operators',
    usernameId: 'Username / ID',
    endOfUserList: 'End of active operator list.',

    moduleMgmtSub: 'Monitor and control system-level service modules.',
    totalModules: 'Total Modules',
    standby: 'Standby',
    warning: 'Warning',
    filter: 'Filter:',
    all: 'ALL',
    selected: 'Modules Selected',
    restartSelected: 'Restart Selected',
    stopSelected: 'Stop Selected',
    moduleName: 'Module Name',
    uptime: 'Uptime',
    version: 'Version',
    cpuUsage: 'CPU Usage',
    memory: 'Memory',
    logLevel: 'Log Level',
    dependencies: 'Dependencies',
    restartModule: 'RESTART MODULE',
    viewLogs: 'VIEW LOGS',
    stopService: 'STOP SERVICE',

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
