import { ref } from 'vue'
import { apiGetMe } from '@/core/api'

export interface User {
    id: string
    username: string
    full_name: string
    email?: string
    avatar?: string
    uid: string
    role_id: string
    role_name: string
    permissions?: string[]
    must_change_password?: boolean
    auth_enabled?: boolean
}

export function getStoredToken(): string | null {
    if (typeof localStorage === 'undefined') return null
    return localStorage.getItem('nms_token') || sessionStorage.getItem('nms_token')
}

export function getStoredUser(): User | null {
    if (typeof localStorage === 'undefined') return null
    const raw = localStorage.getItem('nms_user') || sessionStorage.getItem('nms_user')
    if (!raw) return null
    try {
        return JSON.parse(raw)
    } catch {
        return null
    }
}

const currentAuthUser = ref<User | null>(getStoredUser())
const currentAuthToken = ref<string | null>(getStoredToken())

export function syncAuthRef() {
    currentAuthUser.value = getStoredUser()
    currentAuthToken.value = getStoredToken()
}

if (typeof window !== 'undefined') {
    window.addEventListener('nms-user-updated', syncAuthRef)
    window.addEventListener('storage', syncAuthRef)
}

export function isAuthenticated(): boolean {
    return !!currentAuthToken.value
}

export function isAuthEnabled(): boolean {
    return currentAuthToken.value !== 'system_disabled_auth' && currentAuthUser.value?.auth_enabled !== false
}

export function setAuthSession(token: string, user: User, rememberMe: boolean = true) {
    clearAuthSession()
    const storage = rememberMe ? localStorage : sessionStorage
    storage.setItem('nms_token', token)
    storage.setItem('nms_user', JSON.stringify(user))
    syncAuthRef()
    if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('nms-user-updated', { detail: user }))
    }
}

export function clearAuthSession() {
    localStorage.removeItem('nms_token')
    localStorage.removeItem('nms_user')
    sessionStorage.removeItem('nms_token')
    sessionStorage.removeItem('nms_user')
    syncAuthRef()
    if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('nms-user-updated', { detail: null }))
    }
}

export async function ensureAuthStatus(): Promise<boolean> {
    const token = getStoredToken()
    try {
        const me = await apiGetMe()
        if (me) {
            if (me.auth_enabled === false) {
                setAuthSession('system_disabled_auth', {
                    id: me.id || '1',
                    username: me.username || 'root',
                    full_name: me.full_name || 'System Superuser',
                    email: me.email || 'root@nms.local',
                    uid: me.uid || 'ROOT-001',
                    role_id: me.role_id || '1',
                    role_name: me.role_name || 'Superuser',
                    permissions: me.permissions || ['system.all'],
                    auth_enabled: false,
                })
                return true
            } else {
                updateStoredUser({ auth_enabled: true })
                if (token && token !== 'system_disabled_auth') {
                    return true
                }
            }
        }
    } catch {
        if (token === 'system_disabled_auth') {
            clearAuthSession()
        }
    }
    return !!token && token !== 'system_disabled_auth'
}

export function updateStoredUser(fields: Partial<User>) {
    const user = getStoredUser()
    if (user) {
        const updated = { ...user, ...fields }
        const storage = localStorage.getItem('nms_user') ? localStorage : sessionStorage
        storage.setItem('nms_user', JSON.stringify(updated))
        syncAuthRef()
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('nms-user-updated', { detail: updated }))
        }
    }
}

const impliedPermissionsMap: Record<string, string[]> = {
    'users.view': ['users.manage'],
    'roles.view': ['roles.manage'],
    'settings.view': ['settings.edit'],
    'modules.view': ['modules.manage'],
    'audit.view': ['audit.export'],
}

/**
 * Проверка наличия разрешения у авторизованного пользователя.
 */
export function hasPermission(permission: string): boolean {
    const user = getStoredUser()
    if (!user || !user.permissions) return false

    const perms = user.permissions
    if (perms.includes('system.all')) return true
    if (perms.includes(permission)) return true

    const implied = impliedPermissionsMap[permission] || []
    return implied.some((imp) => perms.includes(imp))
}

/**
 * Проверка наличия хотя бы одного из перечисленных разрешений.
 */
export function hasAnyPermission(permissions: string[]): boolean {
    if (!permissions || permissions.length === 0) return true
    return permissions.some((p) => hasPermission(p))
}

/**
 * Проверка наличия всех перечисленных разрешений.
 */
export function hasAllPermissions(permissions: string[]): boolean {
    if (!permissions || permissions.length === 0) return true
    return permissions.every((p) => hasPermission(p))
}
