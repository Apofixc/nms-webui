/**
 * TypeScript интерфейсы для модульной системы.
 */

export interface RouteMeta {
    title?: string
    icon?: string
    group?: string
    requires_auth?: boolean
    permissions?: string[]
    settings_view?: boolean
    module_id?: string
    submodule?: string
}

export interface RouteDefinition {
    path: string
    name: string
    meta: RouteMeta
}

export interface MenuItem {
    path: string
    label: string
    icon?: string | null
}

export interface MenuConfig {
    location: 'sidebar' | 'footer' | null
    group?: string | null
    items: MenuItem[]
}

export interface ModuleManifest {
    id: string
    name: string
    version: string
    description?: string
    enabled_by_default: boolean
    type: string
    deps: string[]
    parent?: string | null
    parent_id?: string | null
    is_submodule: boolean
    routes: RouteDefinition[]
    menu: MenuConfig | null
    config_schema?: Record<string, any> | null
    enabled?: boolean
    settings_current?: Record<string, any> | null
}

export interface ModuleRegistry {
    id: string
    name: string
    menu: MenuConfig | null
    routes: RouteDefinition[]
}

export interface SidebarGroup {
    id: string
    label: string
    items: MenuItem[]
}

export interface EnableSchemaNode {
    id: string
    title: string
    enabled: boolean
    type: string
    is_submodule: boolean
    deps: string[]
    children: EnableSchemaNode[]
}

export interface EnableSchemaResponse {
    version: string
    type: string
    items: EnableSchemaNode[]
}
