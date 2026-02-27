/**
 * Auth stub — always authenticated.
 */
export interface User {
    username: string
    isAuthenticated: boolean
}

const anonymousUser: User = {
    username: 'anonymous',
    isAuthenticated: false,
}

export function getCurrentUser(): User {
    return anonymousUser
}

export function isAuthenticated(): boolean {
    return true // stub: always pass
}
