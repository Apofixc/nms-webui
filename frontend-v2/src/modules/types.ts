/**
 * TypeScript интерфейсы для модульной системы NMS-WebUI v2.
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
  submodule_id?: string
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
  type: 'system' | 'feature' | 'driver' | string
  deps: string[]
  parent?: string | null
  parent_id?: string | null
  is_submodule: boolean
  routes: RouteDefinition[]
  menu: MenuConfig | null
  config_schema?: Record<string, any> | null
  enabled?: boolean
  settings_current?: Record<string, any> | null
  health_status?: 'healthy' | 'warning' | 'error' | 'disabled'
}

export interface ModuleRegistryItem {
  id: string
  name: string
  version: string
  is_submodule: boolean
  parent_id?: string | null
  menu: MenuConfig | null
  routes: RouteDefinition[]
  manifest: ModuleManifest
}

export interface SidebarGroup {
  id: string
  label: string
  items: MenuItem[]
  submodules?: SidebarGroup[]
}

export interface WidgetDefinition {
  id: string
  module_id: string
  module_name: string
  title: string
  description?: string
  default_size: 'sm' | 'md' | 'lg' | 'xl' // sm: 1x1, md: 2x1, lg: 2x2, xl: 4x2
  component: string
  category: 'system' | 'astra' | 'network' | 'telemetry' | 'alerts'
}

export interface PlacedWidget {
  instance_id: string
  widget_id: string
  size: 'sm' | 'md' | 'lg' | 'xl'
  x: number
  y: number
}
