/**
 * Axios instance + типизированные API-функции для модуля NMS.
 */
import axios from 'axios'
import type { ModuleManifest, EnableSchemaResponse } from '@/modules/types'
import { getStoredToken, clearAuthSession } from '@/core/auth'
import { t, DEFAULT_LANG, currentLang, translations } from '@/core/i18n'
import { loadModuleLocales } from '@/modules/registry'

export const http = axios.create({
    baseURL: '/',
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000,
})

// ── Interceptors ───────────────────────────────────────────────────
http.interceptors.request.use((config) => {
    const token = getStoredToken()
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    config.headers['Accept-Language'] = currentLang.value || DEFAULT_LANG
    return config
})

http.interceptors.response.use(
    (response) => response,
    async (error) => {
        const config = error?.config
        if (config && (error.code === 'ECONNABORTED' || !error.response || [502, 503, 504].includes(error.response.status))) {
            config._retryCount = (config._retryCount || 0) + 1
            if (config._retryCount <= 2 && (config.method?.toUpperCase() === 'GET')) {
                await new Promise((resolve) => setTimeout(resolve, 1000 * config._retryCount))
                return http(config)
            }
        }

        if (error?.response?.data?.error_code) {
            const code = error.response.data.error_code
            const translatedMsg = t(`errors.${code}`)
            if (translatedMsg && translatedMsg !== `errors.${code}`) {
                error.response.data.detail = translatedMsg
            }
        }
        if (error?.response?.status === 401) {
            clearAuthSession()
            if (window.location.pathname !== '/login') {
                window.location.href = '/login'
            }
        }
        console.error('[API]', error?.response?.status, error?.config?.url, error?.message)
        return Promise.reject(error)
    },
)

// ── Auth API ───────────────────────────────────────────────────────
export async function apiLogin(username: string, password: string) {
    const { data } = await http.post('/api/auth/login', { username, password })
    return data
}

export async function apiVerifyMfa(mfaTicket: string, code: string) {
    const { data } = await http.post('/api/auth/mfa/verify', { mfa_ticket: mfaTicket, code })
    return data
}

export async function apiSetupMfa() {
    const { data } = await http.post('/api/auth/mfa/setup')
    return data
}

export async function apiEnableMfa(secret: string, code: string) {
    const { data } = await http.post('/api/auth/mfa/enable', { secret, code })
    return data
}

export async function apiDisableMfa() {
    const { data } = await http.post('/api/auth/mfa/disable')
    return data
}

export async function apiLogout() {
    const { data } = await http.post('/api/auth/logout')
    return data
}

export async function apiTerminateSessions(otherOnly = false) {
    const { data } = await http.post(`/api/auth/terminate-sessions${otherOnly ? '?other_only=true' : ''}`)
    return data
}

export async function apiGetMe() {
    const { data } = await http.get('/api/auth/me')
    return data
}

export async function apiChangePassword(oldPassword: string, newPassword: string) {
    const { data } = await http.put('/api/users/me/password', {
        old_password: oldPassword,
        new_password: newPassword,
    })
    return data
}

export async function apiUpdateMe(userData: { full_name?: string; email?: string; avatar?: string; timezone?: string }) {
    const { data } = await http.put('/api/users/me', userData)
    return data
}

// ── Users Management API ───────────────────────────────────────────
export async function apiFetchUsers(params?: { page?: number; page_size?: number; search?: string; role_id?: string }) {
    const { data } = await http.get('/api/users', { params })
    return data
}

export async function apiCreateUser(userData: Record<string, any>) {
    const { data } = await http.post('/api/users', userData)
    return data
}

export async function apiUpdateUser(userId: string, userData: Record<string, any>) {
    const { data } = await http.put(`/api/users/${userId}`, userData)
    return data
}

export async function apiDeleteUser(userId: string) {
    const { data } = await http.delete(`/api/users/${userId}`)
    return data
}

export async function apiTerminateUserSessions(userId: string) {
    const { data } = await http.post(`/api/users/${userId}/terminate-sessions`)
    return data
}

export async function apiFetchUserSessions(userId: string) {
    const { data } = await http.get(`/api/users/${userId}/sessions`)
    return data
}

export async function apiRevokeSession(sessionId: string) {
    const { data } = await http.delete(`/api/users/sessions/${sessionId}`)
    return data
}

export async function apiFetchMySessions() {
    const { data } = await http.get('/api/users/me/sessions')
    return data
}

export async function apiRevokeMySession(sessionId: string) {
    const { data } = await http.delete(`/api/users/me/sessions/${sessionId}`)
    return data
}

export async function apiBulkUsersAction(userIds: string[], action: string, roleId?: string) {
    const { data } = await http.post('/api/users/bulk-action', { user_ids: userIds, action, role_id: roleId })
    return data
}

// ── Roles & Permissions API ─────────────────────────────────────────
export async function apiFetchRoles() {
    const { data } = await http.get('/api/roles')
    return data
}

export async function apiFetchPermissions() {
    const { data } = await http.get('/api/permissions')
    return data
}

export async function apiCreateRole(roleData: Record<string, any>) {
    const { data } = await http.post('/api/roles', roleData)
    return data
}

export async function apiUpdateRole(roleId: string, roleData: Record<string, any>) {
    const { data } = await http.put(`/api/roles/${roleId}`, roleData)
    return data
}

export async function apiDeleteRole(roleId: string) {
    const { data } = await http.delete(`/api/roles/${roleId}`)
    return data
}

// ── Audit Logs API ─────────────────────────────────────────────────
export async function apiFetchAuditLogs(limit = 100, offset = 0, category?: string, search?: string) {
    const { data } = await http.get('/api/audit-logs', { params: { limit, offset, category, search } })
    return data
}

export async function apiExportAuditLogs(format: string = 'xlsx') {
    const response = await http.get('/api/audit-logs/export', { params: { format }, responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url

    const contentDisposition = response.headers['content-disposition'] || response.headers['Content-Disposition']
    let filename = format === 'csv' ? 'audit_logs.csv' : 'audit_logs.xlsx'
    if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/)
        if (match && match[1]) filename = match[1]
    }

    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
}

export async function apiRotateAuditLogs(maxDays = 90, maxRecords = 100000) {
    const { data } = await http.post('/api/audit-logs/rotate', { max_days: maxDays, max_records: maxRecords })
    return data
}

export async function apiFetchSecuritySettings() {
    const { data } = await http.get('/api/settings/security')
    return data
}

export async function apiSaveSecuritySettings(settings: {
    auth_enabled: boolean
    mandatory_password_change: boolean
    max_login_attempts: number
    lockout_duration: number
    session_ttl_hours?: number
    inactivity_timeout_mins?: number
    force_mfa?: boolean
    min_password_length?: number
    require_uppercase?: boolean
    require_digits?: boolean
    require_special_chars?: boolean
    ip_whitelist?: string
}) {
    const { data } = await http.put('/api/settings/security', settings)
    return data
}


// ── Modules API ────────────────────────────────────────────────────
export async function fetchModules(
    withSettings = false,
    onlyEnabled = false,
): Promise<{ items: ModuleManifest[] }> {
    const { data } = await http.get('/api/modules', {
        params: { with_settings: withSettings, only_enabled: onlyEnabled },
    })
    if (data?.items && Array.isArray(data.items)) {
        const supportedLangs = Object.keys(translations)
        await Promise.all(
            data.items.map(async (mod: ModuleManifest) => {
                if (mod?.id) {
                    await Promise.all(
                        supportedLangs.map((lang) => loadModuleLocales(mod.id, lang))
                    )
                }
            })
        )
    }
    return data
}

export async function fetchLoadedModules(): Promise<{ items: string[] }> {
    const { data } = await http.get('/api/modules/loaded')
    return data
}

export async function fetchModuleViews(
    moduleId: string,
): Promise<{ items: Array<{ path: string; name: string; meta: Record<string, any> }> }> {
    const { data } = await http.get(`/api/modules/${moduleId}/views`)
    return data
}

export async function fetchModuleConfigSchema(): Promise<EnableSchemaResponse> {
    const { data } = await http.get('/api/modules/config-schema')
    return data
}

export async function setModuleEnabled(
    moduleId: string,
    enabled: boolean,
): Promise<any> {
    const { data } = await http.put(`/api/modules/${moduleId}/enabled`, { enabled })
    return data
}

export async function fetchModuleSettingsDefinition(
    moduleId: string,
): Promise<{ module_id: string; schema: Record<string, any>; defaults: Record<string, any>; current?: Record<string, any> }> {
    const supportedLangs = Object.keys(translations)
    await Promise.all(supportedLangs.map((lang) => loadModuleLocales(moduleId, lang)))
    const { data } = await http.get(`/api/modules/${moduleId}/settings-definition`)
    return data
}

export async function fetchModuleSettings(
    moduleId: string,
): Promise<Record<string, any>> {
    const { data } = await http.get(`/api/modules/${moduleId}/settings`)
    return data
}

export async function scanModules(): Promise<any> {
    const { data } = await http.post('/api/modules/scan')
    return data
}

export async function installModule(file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await http.post('/api/modules/install', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
}

export async function deleteModule(moduleId: string): Promise<any> {
    const { data } = await http.delete(`/api/modules/${moduleId}`)
    return data
}

export async function exportModule(moduleId: string): Promise<void> {
    const response = await http.get(`/api/modules/${moduleId}/export`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${moduleId}.zip`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
}

export async function fetchModuleWidgets(): Promise<{ items: any[] }> {
    const { data } = await http.get('/api/modules/widgets')
    return data
}

export async function saveModuleSettings(
    moduleId: string,
    body: Record<string, any>,
): Promise<any> {
    const { data } = await http.put(`/api/modules/${moduleId}/settings`, body)
    return data
}

export async function fetchRoot(): Promise<{ service: string; docs: string }> {
    const { data } = await http.get('/')
    return data
}

// ── System Administration API ──────────────────────────────────────
export async function apiDownloadBackup() {
    const response = await http.get('/api/system/backup', { responseType: 'blob' })
    return response.data
}

export async function apiRestoreBackup(file: File) {
    const { data } = await http.post('/api/system/restore', file, {
        headers: { 'Content-Type': 'application/x-sqlite3' },
    })
    return data
}

export async function apiFetchLogList() {
    const { data } = await http.get('/api/system/logs')
    return data
}

export async function apiFetchLogContent(logName: string, params: { lines?: number; level?: string; search?: string }) {
    const { data } = await http.get(`/api/system/logs/${logName}`, { params })
    return data
}

export async function apiAddRemoteLogSource(payload: { name: string; url: string; api_token?: string }) {
    const { data } = await http.post('/api/system/logs/remote-sources', payload)
    return data
}

export async function apiDeleteRemoteLogSource(sourceId: string) {
    const { data } = await http.delete(`/api/system/logs/remote-sources/${sourceId}`)
    return data
}

export async function apiFetchActiveSessions() {
    const { data } = await http.get('/api/system/sessions')
    return data
}

export async function apiTerminateAllSessions(keepCurrent = true) {
    const { data } = await http.post(`/api/system/sessions/terminate-all${!keepCurrent ? '?keep_current=false' : ''}`)
    return data
}

export async function apiFetchModuleGuideDoc() {
    const { data } = await http.get<{ content: string; filename: string }>('/api/system/docs/module-guide')
    return data
}

export interface WikiArticleItem {
    path: string
    title: string
    filename: string
}

export interface WikiCategoryItem {
    id: string
    title: string
    icon: string
    articles: WikiArticleItem[]
}

export async function apiFetchWikiTree(): Promise<{ categories: WikiCategoryItem[] }> {
    const { data } = await http.get<{ categories: WikiCategoryItem[] }>('/api/system/docs/wiki/tree')
    return data
}

export async function apiFetchWikiArticle(path: string): Promise<{ content: string; path: string; filename: string }> {
    const { data } = await http.get<{ content: string; path: string; filename: string }>('/api/system/docs/wiki/article', {
        params: { path },
    })
    return data
}

export interface NotificationItem {
    id: number
    title: string
    message: string
    type: 'info' | 'success' | 'warning' | 'error'
    category: string
    read: boolean
    link?: string | null
    user_id?: string | null
    created_at: string
}

export interface NotificationCreatePayload {
    title: string
    message: string
    type?: 'info' | 'success' | 'warning' | 'error'
    category?: string
    link?: string | null
    user_id?: string | null
}

export async function apiCreateNotification(payload: NotificationCreatePayload): Promise<NotificationItem> {
    const { data } = await http.post<NotificationItem>('/api/notifications', payload)
    return data
}

export async function apiFetchNotifications(
    unreadOnly = false,
    limit = 50,
    search?: string,
    category?: string,
    type?: string
): Promise<NotificationItem[]> {
    const { data } = await http.get<NotificationItem[]>('/api/notifications', {
        params: { unread_only: unreadOnly, limit, search, category, type }
    })
    return data
}

export async function apiFetchUnreadCount(): Promise<{ count: number }> {
    const { data } = await http.get<{ count: number }>('/api/notifications/unread-count')
    return data
}

export async function apiMarkNotificationRead(id: number) {
    const { data } = await http.post(`/api/notifications/${id}/read`)
    return data
}

export async function apiMarkAllNotificationsRead() {
    const { data } = await http.post('/api/notifications/read-all')
    return data
}

export async function apiDeleteNotification(id: number) {
    const { data } = await http.delete(`/api/notifications/${id}`)
    return data
}

export async function apiClearNotifications() {
    const { data } = await http.delete('/api/notifications/clear')
    return data
}

export default http


