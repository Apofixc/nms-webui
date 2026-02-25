// New file
export const modulesRegistry = [
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
