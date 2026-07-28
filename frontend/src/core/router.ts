/**
 * Dynamic router — строится из манифестов модулей.
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { initModulesRegistry, getModuleRoutes } from '@/modules/registry'
import { registerAllModuleViews } from '@/modules/loader'
import { isAuthenticated } from '@/core/auth'

// Fallback routes (always present)
const baseRoutes: RouteRecordRaw[] = [
    {
        path: '/',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: 'Дашборд', requiresAuth: true },
    },
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/Login.vue'),
        meta: { title: 'Вход в систему', requiresAuth: false },
    },
    {
        path: '/settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { title: 'Центр настроек', requiresAuth: true },
    },
    {
        path: '/settings/access-control',
        name: 'AccessControl',
        component: () => import('@/views/AccessControl.vue'),
        meta: { title: 'Управление доступом', requiresAuth: true },
    },
    {
        path: '/settings/users',
        name: 'UsersManagement',
        component: () => import('@/views/UsersManagement.vue'),
        meta: { title: 'Управление пользователями', requiresAuth: true },
    },
    {
        path: '/settings/profile',
        name: 'UserProfile',
        component: () => import('@/views/UserProfile.vue'),
        meta: { title: 'Профиль пользователя', requiresAuth: true },
    },
    {
        path: '/settings/modules',
        name: 'ModuleManagement',
        component: () => import('@/views/ModuleManagement.vue'),
        meta: { title: 'Управление модулями', requiresAuth: true },
    },
    {
        path: '/settings/audit-logs',
        name: 'AuditLogs',
        component: () => import('@/views/AuditLogs.vue'),
        meta: { title: 'Журнал аудита', requiresAuth: true },
    },
    {
        path: '/:pathMatch(.*)*',
        redirect: '/',
    },
]

export async function createAppRouter() {
    // Register module view components
    registerAllModuleViews()

    // Load module routes from API
    await initModulesRegistry()
    const moduleRoutes = getModuleRoutes() as RouteRecordRaw[]

    // Merge: module routes override base routes by path
    const seenPaths = new Set(moduleRoutes.map((r) => r.path))
    const finalRoutes = [
        ...moduleRoutes,
        ...baseRoutes.filter((r) => !seenPaths.has(r.path as string)),
    ]

    const router = createRouter({
        history: createWebHistory(),
        routes: finalRoutes,
    })

    router.beforeEach((to, _from, next) => {
        const requiresAuth = to.meta.requiresAuth !== false
        if (requiresAuth && !isAuthenticated()) {
            next('/login')
        } else if (to.path === '/login' && isAuthenticated()) {
            next('/')
        } else {
            next()
        }
    })

    router.afterEach((to) => {
        const title = (to.meta as any)?.title
        document.title = title ? `${title} — NMS` : 'NMS'
    })

    return router
}
