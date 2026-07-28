import { ref } from 'vue'

export type Language = 'ru' | 'en'

const savedLang = (localStorage.getItem('nms_lang') as Language) || 'ru'
export const currentLang = ref<Language>(savedLang)

export function setLanguage(lang: Language) {
  currentLang.value = lang
  localStorage.setItem('nms_lang', lang)
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lang
  }
}

if (typeof document !== 'undefined') {
  document.documentElement.lang = savedLang
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
    auditLogs: 'Журнал аудита',
    accessIdentity: 'Доступ и Идентификация',
    configGroups: 'Группы конфигурации',
    searchPlaceholder: 'Поиск ресурсов NMS...',
    healthOptimal: 'Состояние NMS: Оптимально',
    healthOffline: 'Состояние NMS: Офлайн',

    // New status & connection keys
    wsLiveConnection: 'WS В сети',
    wsOffline: 'WS Офлайн',
    logoutTitle: 'Выйти из системы',
    logout: 'Выйти',

    // Faults on Dashboard
    activeFault1: 'Потеря оптического канала на магистральном интерфейсе eth0.',
    activeFault2: 'BGP сессия отключена. Peer IP: 192.168.10.5',
    activeFault3: 'Высокая загрузка процессора коммутатора (89%).',
    activeFault4: 'Таблица сопоставления соединений заполнена на 85%.',
    noLoadedModulesIn: 'Нет загруженных модулей в',

    // Timezone & Profile
    autoDetectBrowser: 'Автоопределить из браузера',
    autoDetect: 'Автоопределение',
    selectTimezone: 'Выберите часовой пояс...',
    searchTimezonePlaceholder: 'Поиск (напр. Moscow, Tokyo, London, UTC)...',
    timezoneNotFound: 'Часовой пояс не найден',
    tzChangedTo: 'Часовой пояс изменен на',
    tzSetToBrowser: 'Установлен часовой пояс браузера',
    maxFileSize2MB: 'Размер файла не должен превышать 2 МБ',
    avatarUpdated: 'Аватар успешно обновлен',
    avatarUpdateError: 'Ошибка при сохранении аватара',
    avatarReset: 'Аватар сброшен к инициалам',
    avatarResetError: 'Ошибка при сбросе аватара',
    fullNameRequired: 'ФИО не может быть пустым',
    profileSaved: 'Данные профиля успешно сохранены',
    profileSaveError: 'Ошибка сохранения профиля',
    fillAllPasswordFields: 'Заполните все поля смены пароля',
    passwordsDoNotMatch: 'Новый пароль и подтверждение не совпадают',
    passwordMinLength: 'Пароль должен состоять минимум из 4 символов',
    passwordChangedSuccess: 'Пароль успешно изменен',
    passwordChangeError: 'Не удалось изменить пароль',
    terminatingSessions: 'Завершение сессий на всех устройствах...',

    // User & Role Management
    editTooltip: 'Редактировать',
    resetPasswordTooltip: 'Сбросить пароль',
    deleteTooltip: 'Удалить',
    noUsersFound: 'Пользователи не найдены по запросу',
    defaultOperatorTitle: 'Оператор',
    userLockedToast: 'заблокирован',
    userUnlockedToast: 'разблокирован',
    statusChangeError: 'Не удалось изменить статус',
    userUpdatedSuccess: 'успешно обновлен',
    userCreatedSuccess: 'успешно создан',
    userSaveError: 'Не удалось сохранить пользователя',
    passwordResetSuccess: 'Пароль успешно обновлен',
    passwordResetError: 'Не удалось сбросить пароль',
    userDeletedSuccess: 'удален',
    userDeleteError: 'Не удалось удалить пользователя',
    errorPrefix: 'Ошибка',
    secPoliciesUpdated: 'Политики безопасности успешно обновлены',
    roleUpdatedSuccess: 'успешно обновлена',
    roleCreatedSuccess: 'успешно создана',
    roleSaveError: 'Не удалось сохранить роль',
    permUpdatedSuccess: 'Права обновлены',

    // Modules & Forms
    moduleFallback: 'Модуль',
    moduleSettingsSub: 'Настройки модуля',
    noConfigurableParams: 'У этого модуля нет настраиваемых параметров',
    resetButton: 'Сбросить',
    saveButton: 'Сохранить',
    loadingAuditData: 'Загрузка данных аудита...',
    noEventsFound: 'События не найдены',
    loadingSchema: 'Загрузка схемы...',
    noSchemaAvailable: 'Нет доступной схемы настроек',
    onState: 'Вкл',
    offState: 'Выкл',

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
    terminateAllSessions: 'Завершить все сессии',
    terminateSessionsSub: 'Завершение сессий отзовет авторизацию на всех устройствах',
    deviceBrowser: 'Устройство / Браузер',
    loginTime: 'Время входа',
    currentSessionActive: 'Текущая сессия (Активна)',
    sessionTerminated: 'Сессия завершена',
    today: 'Сегодня',
    readonlyField: '(только чтение)',
    refresh: 'Обновить',
    edit: 'Редактировать',
    delete: 'Удалить',
    lock: 'Заблокировать',
    unlock: 'Разблокировать',
    cancel: 'Отмена',
    saveRole: 'Сохранить роль',
    editRoleTitle: 'Редактировать роль',
    addRoleTitle: 'Добавить роль',
    roleNameLabel: 'Название роли',
    descriptionLabel: 'Описание',
    roleDescPlaceholder: 'Описание полномочий этой роли в системе',

    // User Modals & Form Labels
    editUserTitle: 'Редактировать пользователя',
    addUserTitle: 'Добавить пользователя',
    fullNameLabel: 'ФИО / Полное имя',
    fullNamePlaceholder: 'Иван Иванов',
    titleDepartmentLabel: 'Должность / Отдел',
    titleDepartmentPlaceholder: 'Инженер NOC',
    usernameLabel: 'Логин / Username',
    usernamePlaceholder: 'i.ivanov',
    uidLabel: 'UID',
    roleLabel: 'Роль',
    lockAccessLabel: 'Заблокировать доступ',
    saveUser: 'Сохранить',
    passwordResetTitle: 'Сброс пароля',
    newPasswordPlaceholder: 'Новый сложный пароль',
    generate: 'Сгенерировать',
    updatePassword: 'Обновить пароль',
    deleteUserTitle: 'Удаление пользователя',
    confirmDelete: 'Подтвердить удаление',

    // Roles & Titles & Descriptions
    roleSuperuser: 'Суперадминистратор',
    roleAdmin: 'Администратор',
    roleOperator: 'Оператор',
    roleViewer: 'Наблюдатель',
    superuserDesc: 'Полный доступ к системе и ее конфигурации',
    adminDesc: 'Административный контроль, ограничение на удаление',
    operatorDesc: 'Управление конфигурациями и мониторингом',
    viewerDesc: 'Только чтение параметров и логов',

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
    details: 'Детали',
    resource: 'Ресурс',
    action: 'Действие',
    loginAttempt: 'Попытка входа',
    userCreated: 'Создан пользователь',
    roleModified: 'Роль изменена',

    rolesMgmtSub: 'Определение и управление пользовательскими ролями доступа.',
    roleName: 'Наименование роли',
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

    filterOperators: 'Поиск и фильтр пользователей...',
    showingOperators: 'Отображается пользователей',
    usernameId: 'Логин / ID',
    endOfUserList: 'Конец списка пользователей.',

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
    online: 'В сети',
    offline: 'Офлайн',
    locked: 'Заблокирован',
    success: 'Успешно',
    failure: 'Ошибка',

    // Audit Logs Page
    auditLogsTitle: 'Журнал системного аудита',
    auditLogsSub: 'Лог событий безопасности, входов в систему и действий администраторов',
    auditSearchPlaceholder: 'Поиск по событию, пользователю, IP...',
    totalRecords: 'Всего записей',

    // Login Screen
    loginSubTitle: 'Авторизация оператора системы',
    operatorIdLabel: 'Идентификатор оператора',
    accessCodeLabel: 'Код доступа',
    rememberMe: 'Запомнить меня',
    forgotCode: 'Забыли код?',
    establishConnection: 'Установить соединение',
    authenticating: 'Авторизация...',
    systemStatusLive: 'Статус системы: В сети | Уровень: Омега',
    invalidCredentials: 'Неверный логин или пароль (по умолчанию: root / admin)',
    forgotNotice: 'Для восстановления доступа обратитесь к системному администратору (Root / Superuser).',
    serverError: 'Ошибка ответа сервера'
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
    auditLogs: 'Audit Logs',
    accessIdentity: 'Access & Identity',
    configGroups: 'Configuration Groups',
    searchPlaceholder: 'Search NMS resources...',
    healthOptimal: 'NMS Health: Optimal',
    healthOffline: 'NMS Health: Offline',

    // New status & connection keys
    wsLiveConnection: 'WS Live Connection',
    wsOffline: 'WS Offline',
    logoutTitle: 'Log out of system',
    logout: 'Logout',

    // Faults on Dashboard
    activeFault1: 'Optical channel loss on backbone interface eth0.',
    activeFault2: 'BGP session disconnected. Peer IP: 192.168.10.5',
    activeFault3: 'High switch CPU utilization (89%).',
    activeFault4: 'Connection tracking table 85% full.',
    noLoadedModulesIn: 'No loaded modules in',

    // Timezone & Profile
    autoDetectBrowser: 'Auto-detect from browser',
    autoDetect: 'Auto-detect',
    selectTimezone: 'Select timezone...',
    searchTimezonePlaceholder: 'Search (e.g. Moscow, Tokyo, London, UTC)...',
    timezoneNotFound: 'Timezone not found',
    tzChangedTo: 'Timezone changed to',
    tzSetToBrowser: 'Browser timezone set to',
    maxFileSize2MB: 'File size must not exceed 2 MB',
    avatarUpdated: 'Avatar updated successfully',
    avatarUpdateError: 'Error saving avatar',
    avatarReset: 'Avatar reset to initials',
    avatarResetError: 'Error resetting avatar',
    fullNameRequired: 'Full name cannot be empty',
    profileSaved: 'Profile data saved successfully',
    profileSaveError: 'Error saving profile',
    fillAllPasswordFields: 'Fill in all password fields',
    passwordsDoNotMatch: 'New password and confirmation do not match',
    passwordMinLength: 'Password must be at least 4 characters long',
    passwordChangedSuccess: 'Password changed successfully',
    passwordChangeError: 'Failed to change password',
    terminatingSessions: 'Terminating sessions on all devices...',

    // User & Role Management
    editTooltip: 'Edit',
    resetPasswordTooltip: 'Reset Password',
    deleteTooltip: 'Delete',
    noUsersFound: 'No users found matching query',
    defaultOperatorTitle: 'Operator',
    userLockedToast: 'locked',
    userUnlockedToast: 'unlocked',
    statusChangeError: 'Failed to change status',
    userUpdatedSuccess: 'updated successfully',
    userCreatedSuccess: 'created successfully',
    userSaveError: 'Failed to save user',
    passwordResetSuccess: 'Password updated successfully',
    passwordResetError: 'Failed to reset password',
    userDeletedSuccess: 'deleted',
    userDeleteError: 'Failed to delete user',
    errorPrefix: 'Error',
    secPoliciesUpdated: 'Security policies updated successfully',
    roleUpdatedSuccess: 'updated successfully',
    roleCreatedSuccess: 'created successfully',
    roleSaveError: 'Failed to save role',
    permUpdatedSuccess: 'Permissions updated',

    // Modules & Forms
    moduleFallback: 'Module',
    moduleSettingsSub: 'Module settings',
    noConfigurableParams: 'This module has no configurable parameters',
    resetButton: 'Reset',
    saveButton: 'Save',
    loadingAuditData: 'Loading audit data...',
    noEventsFound: 'Events not found',
    loadingSchema: 'Loading schema...',
    noSchemaAvailable: 'No settings schema available',
    onState: 'On',
    offState: 'Off',

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
    terminateAllSessions: 'Terminate All Sessions',
    terminateSessionsSub: 'Terminating sessions revokes authorization across all devices',
    deviceBrowser: 'Device / Browser',
    loginTime: 'Login Time',
    currentSessionActive: 'Current Session (Active)',
    sessionTerminated: 'Terminated',
    today: 'Today',
    readonlyField: '(readonly)',
    refresh: 'Refresh',
    edit: 'Edit',
    delete: 'Delete',
    lock: 'Lock',
    unlock: 'Unlock',
    cancel: 'Cancel',
    saveRole: 'Save Role',
    editRoleTitle: 'Edit Role',
    addRoleTitle: 'Add Role',
    roleNameLabel: 'Role Name',
    descriptionLabel: 'Description',
    roleDescPlaceholder: 'Description of role permissions',

    // User Modals & Form Labels
    editUserTitle: 'Edit User',
    addUserTitle: 'Add User',
    fullNameLabel: 'Full Name',
    fullNamePlaceholder: 'John Doe',
    titleDepartmentLabel: 'Title / Department',
    titleDepartmentPlaceholder: 'NOC Engineer',
    usernameLabel: 'Username',
    usernamePlaceholder: 'j.doe',
    uidLabel: 'UID',
    roleLabel: 'Role',
    lockAccessLabel: 'Lock Account',
    saveUser: 'Save',
    passwordResetTitle: 'Password Reset',
    newPasswordPlaceholder: 'New strong password',
    generate: 'Generate',
    updatePassword: 'Update Password',
    deleteUserTitle: 'Delete User',
    confirmDelete: 'Confirm Delete',

    // Roles & Titles & Descriptions
    roleSuperuser: 'Superuser',
    roleAdmin: 'Administrator',
    roleOperator: 'Operator',
    roleViewer: 'Viewer',
    superuserDesc: 'Full system access and full configuration rights',
    adminDesc: 'Administrative control, limited destructive actions',
    operatorDesc: 'Manage network state and configurations',
    viewerDesc: 'Read-only access to dashboards and logs',

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
    details: 'Details',
    resource: 'Resource',
    action: 'Action',
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
    failure: 'Failure',

    // Audit Logs Page
    auditLogsTitle: 'System Audit Logs',
    auditLogsSub: 'Security logs, logins, and administrator actions',
    auditSearchPlaceholder: 'Search event, user, IP...',
    totalRecords: 'Total records',

    // Login Screen
    loginSubTitle: 'System Operator Authentication',
    operatorIdLabel: 'Operator ID',
    accessCodeLabel: 'Access Code',
    rememberMe: 'Remember Me',
    forgotCode: 'Forgot Code?',
    establishConnection: 'Establish Connection',
    authenticating: 'Authenticating...',
    systemStatusLive: 'System Status: Live | Sec-Level: Omega',
    invalidCredentials: 'Invalid username or password (default: root / admin)',
    forgotNotice: 'To restore access, please contact your System Administrator (Root / Superuser).',
    serverError: 'Server response error'
  }
} as const

export type TranslationKey = keyof typeof translations.ru

export function t(key: TranslationKey): string {
  return translations[currentLang.value][key] || translations.ru[key] || key
}

export function getRoleTitle(roleName: string): string {
  if (!roleName) return ''
  const name = roleName.toLowerCase()
  if (name.includes('superuser') || name.includes('суперадминистратор')) {
    return t('roleSuperuser')
  }
  if (name.includes('admin') || name.includes('администратор')) {
    return t('roleAdmin')
  }
  if (name.includes('operator') || name.includes('оператор')) {
    return t('roleOperator')
  }
  if (name.includes('viewer') || name.includes('наблюдатель')) {
    return t('roleViewer')
  }
  return roleName
}

export function getRoleDescription(roleName: string, defaultDesc: string): string {
  if (!roleName) return defaultDesc || ''
  const name = roleName.toLowerCase()
  if (name.includes('superuser') || name.includes('суперадминистратор')) {
    return t('superuserDesc')
  }
  if (name.includes('admin') || name.includes('администратор')) {
    return t('adminDesc')
  }
  if (name.includes('operator') || name.includes('оператор')) {
    return t('operatorDesc')
  }
  if (name.includes('viewer') || name.includes('наблюдатель')) {
    return t('viewerDesc')
  }
  return defaultDesc || ''
}

export function useI18n() {
  return {
    lang: currentLang,
    setLanguage,
    t: (key: TranslationKey) => t(key),
    getRoleTitle,
    getRoleDescription
  }
}
