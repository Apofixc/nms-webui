/**
 * Frontend Module & Dynamic Navigation Registry for NMS-WebUI v2.
 */
import type { ModuleManifest, ModuleRegistryItem, SidebarGroup, MenuItem } from './types'

let modulesRegistry: ModuleRegistryItem[] = []

// Standard views available in core
const viewComponentsByName: Record<string, () => Promise<any>> = {
  Dashboard: () => import('@/views/DashboardView.vue'),
  ModuleManager: () => import('@/views/ModuleManagerView.vue'),
  DynamicSettings: () => import('@/views/DynamicSettingsView.vue'),
  ModuleContainer: () => import('@/views/ModuleContainerView.vue'),
}

export function registerViewComponent(name: string, loader: () => Promise<any>) {
  viewComponentsByName[name] = loader
}

export function getViewComponent(name: string): (() => Promise<any>) | undefined {
  return viewComponentsByName[name] || viewComponentsByName['ModuleContainer']
}

/**
 * Инициализирует локальный реестр модулей демо/API данными.
 */
export async function initModulesRegistry(): Promise<ModuleRegistryItem[]> {
  try {
    const res = await fetch('/api/v1/modules')
    if (res.ok) {
      const data = await res.json()
      const items: ModuleManifest[] = data.items || []
      modulesRegistry = items.map(mod => ({
        id: mod.id,
        name: mod.name,
        version: mod.version || '1.0.0',
        is_submodule: !!mod.is_submodule,
        parent_id: mod.parent_id || mod.parent || null,
        menu: mod.menu || null,
        routes: mod.routes || [],
        manifest: mod,
      }))
      return modulesRegistry
    }
  } catch (e) {
    // Fallback to built-in system modules manifest
  }

  // Fallback default manifests representing NMS System & Astra module + submodules
  const defaultManifests: ModuleManifest[] = [
    {
      id: 'system',
      name: 'Система NMS',
      version: '2.0.0',
      description: 'Ядро управления и мониторинга',
      enabled_by_default: true,
      type: 'system',
      deps: [],
      is_submodule: false,
      enabled: true,
      health_status: 'healthy',
      routes: [
        { path: '/dashboard', name: 'Dashboard', meta: { title: 'Дашборд', icon: 'layout-dashboard', group: 'Система' } },
        { path: '/modules', name: 'ModuleManager', meta: { title: 'Менеджер модулей', icon: 'blocks', group: 'Система' } },
      ],
      menu: {
        location: 'sidebar',
        group: 'Система',
        items: [
          { path: '/dashboard', label: 'Дашборд', icon: 'layout-dashboard' },
          { path: '/modules', label: 'Модули системы', icon: 'blocks' },
        ],
      },
    },
    {
      id: 'astra',
      name: 'Astra Broadcast',
      version: '1.5.0',
      description: 'Управление вещанием и DVB адаптерами Cesbo Astra',
      enabled_by_default: true,
      type: 'feature',
      deps: ['system'],
      is_submodule: false,
      enabled: true,
      health_status: 'healthy',
      routes: [
        { path: '/astra/channels', name: 'AstraChannels', meta: { title: 'Каналы', icon: 'tv', group: 'Astra' } },
        { path: '/astra/adapters', name: 'AstraAdapters', meta: { title: 'DVB Адаптеры', icon: 'cpu', group: 'Astra' } },
        { path: '/astra/monitoring', name: 'AstraMonitoring', meta: { title: 'Мониторинг сигналов', icon: 'activity', group: 'Astra' } },
      ],
      menu: {
        location: 'sidebar',
        group: 'Вещание Astra',
        items: [
          { path: '/astra/channels', label: 'Каналы', icon: 'tv' },
          { path: '/astra/adapters', label: 'DVB Адаптеры', icon: 'cpu' },
          { path: '/astra/monitoring', label: 'Мониторинг SNR/BER', icon: 'activity' },
        ],
      },
    },
    {
      id: 'playlist',
      name: 'Плейлисты',
      version: '1.0.0',
      description: 'Управление плейлистами вещания',
      enabled_by_default: true,
      type: 'feature',
      deps: ['astra'],
      parent_id: 'astra',
      is_submodule: true,
      enabled: true,
      health_status: 'healthy',
      routes: [
        { path: '/astra/playlists', name: 'AstraPlaylists', meta: { title: 'Плейлисты', icon: 'list-video', group: 'Astra' } },
      ],
      menu: {
        location: 'sidebar',
        group: 'Вещание Astra',
        items: [
          { path: '/astra/playlists', label: 'Плейлисты', icon: 'list-video', submodule_id: 'playlist' },
        ],
      },
    },
    {
      id: 'snmp',
      name: 'Network & SNMP',
      version: '1.2.0',
      description: 'Мониторинг сетевого оборудования и коммутаторов',
      enabled_by_default: true,
      type: 'feature',
      deps: ['system'],
      is_submodule: false,
      enabled: true,
      health_status: 'healthy',
      routes: [
        { path: '/snmp/devices', name: 'SNMPDevices', meta: { title: 'Сетевые устройства', icon: 'network', group: 'Сеть & SNMP' } },
      ],
      menu: {
        location: 'sidebar',
        group: 'Сеть & SNMP',
        items: [
          { path: '/snmp/devices', label: 'Устройства SNMP', icon: 'network' },
        ],
      },
    },
  ]

  modulesRegistry = defaultManifests.map(mod => ({
    id: mod.id,
    name: mod.name,
    version: mod.version,
    is_submodule: mod.is_submodule,
    parent_id: mod.parent_id || null,
    menu: mod.menu,
    routes: mod.routes,
    manifest: mod,
  }))

  return modulesRegistry
}

export function getModulesRegistry(): ModuleRegistryItem[] {
  return modulesRegistry
}

/**
 * Генерирует динамическое дерево меню для сайдбара с учетом субмодулей и групп.
 */
export function getSidebarGroups(): SidebarGroup[] {
  const groupMap = new Map<string, SidebarGroup>()

  for (const mod of modulesRegistry) {
    if (!mod.menu || mod.menu.location !== 'sidebar') continue

    const groupName = mod.menu.group || mod.name
    if (!groupMap.has(groupName)) {
      groupMap.set(groupName, {
        id: `group-${groupName}`,
        label: groupName,
        items: [],
        submodules: [],
      })
    }

    const grp = groupMap.get(groupName)!
    if (mod.menu.items) {
      for (const item of mod.menu.items) {
        if (!grp.items.some(i => i.path === item.path)) {
          grp.items.push(item)
        }
      }
    }
  }

  return Array.from(groupMap.values())
}

export function getFooterItems(): MenuItem[] {
  return modulesRegistry
    .filter(mod => mod.menu?.location === 'footer')
    .flatMap(mod => mod.menu!.items || [])
}
