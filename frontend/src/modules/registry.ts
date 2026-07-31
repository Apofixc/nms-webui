/**
 * Frontend module registry — загрузка и нормализация модулей из API.
 */
import type { ModuleManifest, ModuleRegistry } from './types'
import { fetchModules, fetchLoadedModules, fetchModuleViews, http } from '@/core/api'
import { registerModuleTranslations, translations } from '@/core/i18n'

let modulesRegistry: ModuleRegistry[] = []

/**
 * Загрузить и зарегистрировать локализации для модуля динамически из API.
 */
export async function loadModuleLocales(moduleId: string, lang: string): Promise<void> {
    try {
        const { data } = await http.get(`/api/modules/${moduleId}/locales/${lang}`)
        if (data?.messages) {
            registerModuleTranslations({ [lang]: data.messages })
        }
    } catch {
        // ignore
    }
}


/**
 * View component map — route name → lazy import.
 * Module-specific views will be registered here when modules are added.
 */
const viewComponentsByName: Record<string, () => Promise<any>> = {
    Dashboard: () => import('@/views/Dashboard.vue'),
    Settings: () => import('@/views/Settings.vue'),
    ModuleView: () => import('@/views/ModuleView.vue'),
}

/**
 * Register a view component for a route name.
 */
export function registerViewComponent(name: string, loader: () => Promise<any>) {
    viewComponentsByName[name] = loader
}

/**
 * Get the component loader for a route name.
 */
export function getViewComponent(name: string): (() => Promise<any>) | undefined {
    return viewComponentsByName[name]
}

function normalizeModule(mod: ModuleManifest): ModuleRegistry | null {
    if (!mod?.id) return null
    return {
        id: mod.id,
        name: mod.name,
        menu: mod.menu || null,
        routes: mod.routes || [],
    }
}

/**
 * Инициализировать реестр модулей из API.
 */
export async function initModulesRegistry(): Promise<void> {
    try {
        const [loadedPayload, modulesPayload] = await Promise.all([
            fetchLoadedModules(),
            fetchModules(false, true),
        ])

        const loadedIds = loadedPayload?.items || []
        const rawModules = modulesPayload?.items || []
        
        // Автоматическая загрузка локализаций модулей из API для всех языков системы
        const supportedLangs = Object.keys(translations)
        await Promise.all(
            rawModules.map(async (mod: ModuleManifest) => {
                if (mod?.id) {
                    await Promise.all(
                        supportedLangs.map((lang) => loadModuleLocales(mod.id, lang))
                    )
                }
            })
        )

        const modulesById = new Map(
            rawModules
                .filter((mod: ModuleManifest) => mod?.id)
                .map((mod: ModuleManifest) => [mod.id, mod]),
        )

        // Only top-level modules
        const parents = new Map(
            [...modulesById.entries()].filter(([, mod]) => !mod.is_submodule),
        )

        const routesByParent = new Map<string, any[]>()
        const menuByParent = new Map<string, any[]>()

        for (const moduleId of loadedIds) {
            const base = modulesById.get(moduleId)
            if (!base) continue

            let views: any[] = []
            try {
                const viewsPayload = await fetchModuleViews(moduleId)
                views = viewsPayload?.items || []
            } catch {
                views = base.routes || []
            }

            if (base.is_submodule && base.parent_id && parents.has(base.parent_id)) {
                const r = routesByParent.get(base.parent_id) || []
                routesByParent.set(base.parent_id, [...r, ...views])
                const items = menuByParent.get(base.parent_id) || []
                const subItems = base.menu?.items || []
                menuByParent.set(base.parent_id, [...items, ...subItems])
            } else if (!base.is_submodule) {
                routesByParent.set(base.id, views)
                menuByParent.set(base.id, base.menu?.items || [])
            }
        }

        const dedupeByPath = <T extends { path?: string }>(arr: T[]): T[] => {
            const seen = new Set<string>()
            return arr.filter((it) => {
                const path = it?.path
                if (!path || seen.has(path)) return false
                seen.add(path)
                return true
            })
        }

        const normalized = [...parents.values()]
            .map((mod) => {
                const routes = dedupeByPath(routesByParent.get(mod.id) || [])
                const items = dedupeByPath(menuByParent.get(mod.id) || [])
                const menu = mod.menu
                    ? { ...mod.menu, items }
                    : items.length
                        ? { location: null, items }
                        : null
                return normalizeModule({ ...mod, routes, menu } as ModuleManifest)
            })
            .filter(Boolean) as ModuleRegistry[]

        modulesRegistry = normalized
    } catch {
        // keep empty
    }
}

/**
 * Get all module routes with component loaders attached.
 */
export function getModuleRoutes() {
    return modulesRegistry.flatMap((mod) =>
        (mod.routes || [])
            .map((route) => {
                const component = viewComponentsByName[route.name] || viewComponentsByName['ModuleView']
                if (!component) return null
                return {
                    path: route.path,
                    name: route.name,
                    component,
                    meta: { ...(route.meta || {}), module_id: mod.id },

                }
            })
            .filter(Boolean),
    )
}


export function getSidebarGroups() {
    return modulesRegistry
        .filter((mod) => mod.menu?.location === 'sidebar')
        .map((mod) => ({
            id: mod.id,
            label: mod.menu!.group || mod.name,
            items: mod.menu!.items || [],
        }))
}

export function getFooterItems() {
    return modulesRegistry
        .filter((mod) => mod.menu?.location === 'footer')
        .flatMap((mod) => mod.menu!.items || [])
}

export function preloadModuleRoutes() {
    modulesRegistry.forEach((mod) => {
        ; (mod.routes || []).forEach((route) => {
            const loader = viewComponentsByName[route.name]
            if (typeof loader === 'function') {
                loader()
            }
        })
    })
}
