/**
 * Парсинг манифестов для роутера и sidebar.
 */
import type { ModuleManifest, RouteDefinition, SidebarGroup, MenuItem } from '@/modules/types'

/**
 * Извлечь все routes из массива модулей.
 */
export function extractRoutes(modules: ModuleManifest[]): RouteDefinition[] {
    return modules.flatMap((mod) => mod.routes || [])
}

/**
 * Извлечь sidebar groups из массива модулей.
 */
export function extractSidebarGroups(modules: ModuleManifest[]): SidebarGroup[] {
    return modules
        .filter((mod) => mod.menu?.location === 'sidebar' && !mod.is_submodule)
        .map((mod) => ({
            id: mod.id,
            label: mod.menu!.group || mod.name,
            items: mod.menu!.items || [],
        }))
}

/**
 * Извлечь footer items из массива модулей.
 */
export function extractFooterItems(modules: ModuleManifest[]): MenuItem[] {
    return modules
        .filter((mod) => mod.menu?.location === 'footer')
        .flatMap((mod) => mod.menu!.items || [])
}
