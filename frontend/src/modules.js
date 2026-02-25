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
}

let modulesRegistry = [...fallbackModulesRegistry]

const toRouteWithComponent = (route) => {
  if (!route || typeof route !== 'object') return null
  const name = route.name
  const component = route.component || routeComponentsByName[name]
  if (!route.path || !name || typeof component !== 'function') return null
  return {
    path: route.path,
    name,
    component,
    meta: route.meta || {},
  }
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
    const assembled = []
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
      assembled.push(normalizeModule({ ...base, routes: views }))
    }
    const normalized = assembled.filter(Boolean)
    if (normalized.length && normalized.some((mod) => (mod.routes || []).length > 0)) {
      modulesRegistry = normalized
      return
    }
  } catch {
    // fallback to static registry below
  }
  modulesRegistry = [...fallbackModulesRegistry]
}

export const getModuleRoutes = () => modulesRegistry.flatMap((mod) => mod.routes || [])

export const getSidebarGroups = () =>
  modulesRegistry
    .filter((mod) => mod.menu && mod.menu.location === 'sidebar')
    .map((mod) => ({
      id: mod.id,
      label: mod.menu.group || mod.name,
      items: mod.menu.items || [],
    }))

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
