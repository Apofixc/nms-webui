/**
 * Auth state management helpers.
 */
export interface User {
    id: string
    username: string
    full_name: string
    email?: string
    uid: string
    role_id: string
    role_name: string
    permissions?: string[]
    must_change_password?: boolean
}

export function getStoredToken(): string | null {
    return localStorage.getItem('nms_token')
}

export function getStoredUser(): User | null {
    const raw = localStorage.getItem('nms_user')
    if (!raw) return null
    try {
        return JSON.parse(raw)
    } catch {
        return null
    }
}

export function isAuthenticated(): boolean {
    return !!getStoredToken()
}

export function setAuthSession(token: string, user: User) {
    localStorage.setItem('nms_token', token)
    localStorage.setItem('nms_user', JSON.stringify(user))
}

export function clearAuthSession() {
    localStorage.removeItem('nms_token')
    localStorage.removeItem('nms_user')
}

export function updateStoredUser(fields: Partial<User>) {
    const user = getStoredUser()
    if (user) {
        const updated = { ...user, ...fields }
        localStorage.setItem('nms_user', JSON.stringify(updated))
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
