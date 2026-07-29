/**
 * Dynamic router — строится из манифестов модулей.
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { initModulesRegistry, getModuleRoutes } from '@/modules/registry'
import { registerAllModuleViews } from '@/modules/loader'
import { isAuthenticated, getStoredUser } from '@/core/auth'
import { t, type TranslationKey } from '@/core/i18n'

// Fallback routes (always present)
const baseRoutes: RouteRecordRaw[] = [
    {
        path: '/',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { titleKey: 'dashboard', requiresAuth: true },
    },
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/Login.vue'),
        meta: { titleKey: 'loginSubTitle', requiresAuth: false },
    },
    {
        path: '/settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { titleKey: 'settings', requiresAuth: true },
    },
    {
        path: '/settings/access-control',
        redirect: '/settings',
    },
    {
        path: '/settings/users',
        name: 'UsersManagement',
        component: () => import('@/views/UsersManagement.vue'),
        meta: { titleKey: 'usersManagement', requiresAuth: true },
    },
    {
        path: '/settings/profile',
        name: 'UserProfile',
        component: () => import('@/views/UserProfile.vue'),
        meta: { titleKey: 'userProfile', requiresAuth: true },
    },
    {
        path: '/settings/modules',
        name: 'ModuleManagement',
        component: () => import('@/views/ModuleManagement.vue'),
        meta: { titleKey: 'moduleManagement', requiresAuth: true },
    },
    {
        path: '/settings/system',
        name: 'SystemAdmin',
        component: () => import('@/views/SystemAdmin.vue'),
        meta: { titleKey: 'systemAdmin', requiresAuth: true },
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
        const user = getStoredUser()
        const requiresAuth = to.meta.requiresAuth !== false

        if (requiresAuth && !isAuthenticated()) {
            next('/login')
        } else if (to.path === '/login' && isAuthenticated()) {
            next('/')
        } else if (user?.must_change_password && to.path !== '/settings/profile' && to.path !== '/login') {
            next('/settings/profile?must_change=true')
        } else {
            next()
        }
    })

    router.afterEach((to) => {
        const key = (to.meta as any)?.titleKey as TranslationKey | undefined
        const rawTitle = (to.meta as any)?.title
        const title = key ? t(key) : (rawTitle || 'NMS')
        document.title = `${title} — NMS`
    })

    return router
}
