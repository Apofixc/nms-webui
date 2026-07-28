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
