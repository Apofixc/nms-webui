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
export async function apiFetchUsers() {
    const { data } = await http.get('/api/users')
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

// ── Audit Logs API ─────────────────────────────────────────────────
export async function apiFetchAuditLogs(limit = 100, offset = 0) {
    const { data } = await http.get('/api/audit-logs', { params: { limit, offset } })
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

export default http
