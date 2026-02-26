import api from './api'

const fallbackModulesRegistry = [
  {
    id: 'cesbo-astra',
    name: 'Cesbo Astra',
    version: '1.0.0',
    deps: [],
    permissions: [],
    settings: [],
    menu: {
      location: 'sidebar',
      group: 'Cesbo Astra',
      items: [
        { path: '/', label: 'Общая информация' },
        { path: '/instances', label: 'Управление экземплярами' },
        { path: '/channels', label: 'Каналы' },
        { path: '/monitors', label: 'Мониторы' },
        { path: '/subscribers', label: 'Подписка' },
        { path: '/dvb', label: 'DVB-адаптеры' },
        { path: '/system', label: 'Система' },
      ],
    },
    routes: [
      { path: '/', name: 'Overview', component: () => import('./views/Dashboard.vue'), meta: { title: 'Общая информация' } },
      { path: '/instances', name: 'Instances', component: () => import('./views/Instances.vue'), meta: { title: 'Управление экземплярами' } },
      { path: '/channels', name: 'Channels', component: () => import('./views/Channels.vue'), meta: { title: 'Каналы' } },
      { path: '/monitors', name: 'Monitors', component: () => import('./views/Monitors.vue'), meta: { title: 'Мониторы' } },
      { path: '/subscribers', name: 'Subscribers', component: () => import('./views/Subscribers.vue'), meta: { title: 'Подписка' } },
      { path: '/dvb', name: 'Dvb', component: () => import('./views/Dvb.vue'), meta: { title: 'DVB-адаптеры' } },
      { path: '/system', name: 'System', component: () => import('./views/System.vue'), meta: { title: 'Система' } },
    ],
  },
  {
    id: 'settings',
    name: 'Настройки',
    version: '1.0.0',
    deps: [],
    permissions: [],
    settings: [],
    menu: {
      location: 'footer',
      items: [{ path: '/settings', label: 'Настройки', icon: 'settings' }],
    },
    routes: [
      { path: '/settings', name: 'Settings', component: () => import('./views/Settings.vue'), meta: { title: 'Настройки' } },
    ],
  },
]

const routeComponentsByName = {
  Overview: () => import('./views/Dashboard.vue'),
  Instances: () => import('./views/Instances.vue'),
  Channels: () => import('./views/Channels.vue'),
  Monitors: () => import('./views/Monitors.vue'),
  Subscribers: () => import('./views/Subscribers.vue'),
  Dvb: () => import('./views/Dvb.vue'),
  System: () => import('./views/System.vue'),
  Settings: () => import('./views/Settings.vue'),
  ModuleSettings: () => import('./views/ModuleSettings.vue'),
}

let modulesRegistry = [...fallbackModulesRegistry]

const toRouteWithComponent = (route) => {
  if (!route || typeof route !== 'object') return null
  const name = route.name
  let component = route.component || routeComponentsByName[name]
  // Dynamic component for module settings routes
  if (!component && route.meta?.settings_view) {
    component = routeComponentsByName.ModuleSettings
  }
  if (!route.path || !name || typeof component !== 'function') return null
  const routeObj = {
    path: route.path,
    name,
    component,
    meta: route.meta || {},
  }
  // Add moduleId param for settings views
  if (route.meta?.settings_view && route.meta?.module_id) {
    routeObj.props = (route) => ({
      ...route.props,
      moduleId: route.meta.module_id
    })
  }
  return routeObj
}

const normalizeModule = (mod) => {
  if (!mod || typeof mod !== 'object') return null
  const routes = (mod.routes || []).map(toRouteWithComponent).filter(Boolean)
  return {
    id: mod.id,
    name: mod.name,
    menu: mod.menu || null,
    routes,
  }
}

export const initModulesRegistry = async () => {
  try {
    const [loadedPayload, modulesPayload] = await Promise.all([
      api.modulesLoaded(),
      api.modulesGet(false, true),
    ])
    const loadedIds = Array.isArray(loadedPayload?.items) ? loadedPayload.items : []
    const modulesById = new Map(
      (Array.isArray(modulesPayload?.items) ? modulesPayload.items : [])
        .filter((mod) => mod && mod.id)
        .map((mod) => [mod.id, mod])
    )

    // preload maps for parents
    const parents = new Map(
      [...modulesById.entries()].filter(([, mod]) => !mod.is_submodule)
    )
    const routesByParent = new Map()
    const menuByParent = new Map()

    for (const moduleId of loadedIds) {
      const base = modulesById.get(moduleId)
      if (!base) continue

      let views = []
      try {
        const viewsPayload = await api.moduleViews(moduleId)
        views = Array.isArray(viewsPayload?.items) ? viewsPayload.items : []
      } catch {
        views = base.routes || []
      }

      if (base.is_submodule && base.parent_id && parents.has(base.parent_id)) {
        const r = routesByParent.get(base.parent_id) || []
        routesByParent.set(base.parent_id, [...r, ...views])

        const items = menuByParent.get(base.parent_id) || []
        const subItems = (base.menu && base.menu.items) || []
        menuByParent.set(base.parent_id, [...items, ...subItems])
      } else if (!base.is_submodule) {
        routesByParent.set(base.id, views)
        const items = (base.menu && base.menu.items) || []
        menuByParent.set(base.id, items)
      }
    }

    const dedupeByPath = (arr = []) => {
      const seen = new Set()
      return arr.filter((it) => {
        const path = it?.path
        if (!path) return false
        if (seen.has(path)) return false
        seen.add(path)
        return true
      })
    }

    const normalized = [...parents.values()].map((mod) => {
      const routes = dedupeByPath(routesByParent.get(mod.id) || [])
      const items = dedupeByPath(menuByParent.get(mod.id) || [])
      const menu = mod.menu ? { ...mod.menu, items } : items.length ? { items } : null
      return normalizeModule({ ...mod, routes, menu })
    }).filter(Boolean)

    modulesRegistry = normalized
  } catch {
    // fallback to static registry below
  }
  if (!modulesRegistry.length) {
    modulesRegistry = [...fallbackModulesRegistry]
  }
}

export const getModuleRoutes = () => modulesRegistry.flatMap((mod) => mod.routes || [])

export const getSidebarGroups = () => {
  const groups = modulesRegistry
    .filter((mod) => mod.menu && mod.menu.location === 'sidebar' && !mod.is_submodule)
    .map((mod) => ({
      id: mod.id,
      label: mod.menu.group || mod.name,
      items: mod.menu.items || [],
    }))

  // Attach submodules as nested items and deduplicate by path
  for (const group of groups) {
    const allItems = [...group.items]
    for (const mod of modulesRegistry) {
      if (mod.id.startsWith(`${group.id}.`) && mod.menu && mod.menu.location === 'sidebar') {
        allItems.push(...(mod.menu.items || []))
      }
    }
    // Deduplicate by path
    const seen = new Set()
    group.items = allItems.filter((item) => {
      if (seen.has(item.path)) return false
      seen.add(item.path)
      return true
    })
  }
  return groups
}

export const getFooterItems = () =>
  modulesRegistry
    .filter((mod) => mod.menu && mod.menu.location === 'footer')
    .flatMap((mod) => mod.menu.items || [])

export const preloadModuleRoutes = () => {
  modulesRegistry.forEach((mod) => {
    ;(mod.routes || []).forEach((route) => {
      if (typeof route.component === 'function') {
        route.component()
      }
    })
  })
}
