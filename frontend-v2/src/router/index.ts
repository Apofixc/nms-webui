import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import DashboardView from '@/views/DashboardView.vue'
import ModuleManagerView from '@/views/ModuleManagerView.vue'
import DynamicSettingsView from '@/views/DynamicSettingsView.vue'
import ModuleContainerView from '@/views/ModuleContainerView.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    component: AppShell,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: DashboardView,
        meta: { title: 'Дашборд' },
      },
      {
        path: 'modules',
        name: 'ModuleManager',
        component: ModuleManagerView,
        meta: { title: 'Менеджер модулей' },
      },
      {
        path: 'settings',
        name: 'DynamicSettings',
        component: DynamicSettingsView,
        meta: { title: 'Настройки' },
      },
      // Dynamic module routes
      {
        path: 'astra/channels',
        name: 'AstraChannels',
        component: ModuleContainerView,
        meta: { title: 'Каналы Astra', module_id: 'astra' },
      },
      {
        path: 'astra/adapters',
        name: 'AstraAdapters',
        component: ModuleContainerView,
        meta: { title: 'DVB Адаптеры', module_id: 'astra' },
      },
      {
        path: 'astra/monitoring',
        name: 'AstraMonitoring',
        component: ModuleContainerView,
        meta: { title: 'Мониторинг сигналов', module_id: 'astra' },
      },
      {
        path: 'astra/playlists',
        name: 'AstraPlaylists',
        component: ModuleContainerView,
        meta: { title: 'Плейлисты', module_id: 'playlist', submodule: 'astra' },
      },
      {
        path: 'snmp/devices',
        name: 'SNMPDevices',
        component: ModuleContainerView,
        meta: { title: 'Сетевые устройства SNMP', module_id: 'snmp' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
