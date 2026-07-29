/**
 * Axios instance + типизированные API-функции для модуля NMS.
 */
import axios from 'axios'
import type { ModuleManifest, EnableSchemaResponse } from '@/modules/types'

const http = axios.create({
    baseURL: '/',
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000,
})

// ── Interceptors ───────────────────────────────────────────────────
http.interceptors.request.use((config) => {
    const token = localStorage.getItem('nms_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    const lang = localStorage.getItem('nms_lang') || 'ru'
    config.headers['Accept-Language'] = lang
    return config
})

http.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error?.response?.status === 401) {
            localStorage.removeItem('nms_token')
            localStorage.removeItem('nms_user')
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

export async function apiTerminateSessions() {
    const { data } = await http.post('/api/auth/terminate-sessions')
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

export async function apiUpdateMe(userData: { full_name?: string; email?: string; avatar?: string }) {
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

export async function apiExportAuditLogs() {
    const response = await http.get('/api/audit-logs/export', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'audit_logs.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
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
    const { data } = await http.get(`/api/modules/${moduleId}/settings-definition`)
    return data
}

export async function fetchModuleSettings(
    moduleId: string,
): Promise<Record<string, any>> {
    const { data } = await http.get(`/api/modules/${moduleId}/settings`)
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

export async function apiFetchActiveSessions() {
    const { data } = await http.get('/api/system/sessions')
    return data
}

export async function apiTerminateAllSessions() {
    const { data } = await http.post('/api/system/sessions/terminate-all')
    return data
}

export default http
