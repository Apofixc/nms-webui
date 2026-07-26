import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import DashboardView from '@/views/DashboardView.vue'
import ModuleManagerView from '@/views/ModuleManagerView.vue'
import DynamicSettingsView from '@/views/DynamicSettingsView.vue'

import AstraChannelsView from '@/views/astra/AstraChannelsView.vue'
import AstraAdaptersView from '@/views/astra/AstraAdaptersView.vue'
import AstraMonitoringView from '@/views/astra/AstraMonitoringView.vue'
import AstraInstancesView from '@/views/astra/AstraInstancesView.vue'
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
        meta: { title: 'Дашборд NMS' },
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
        meta: { title: 'Глобальные настройки' },
      },
      // Real Astra views
      {
        path: 'astra/channels',
        name: 'AstraChannels',
        component: AstraChannelsView,
        meta: { title: 'ТВ-Каналы Astra', module_id: 'astra' },
      },
      {
        path: 'astra/adapters',
        name: 'AstraAdapters',
        component: AstraAdaptersView,
        meta: { title: 'DVB Адаптеры', module_id: 'astra' },
      },
      {
        path: 'astra/monitoring',
        name: 'AstraMonitoring',
        component: AstraMonitoringView,
        meta: { title: 'Мониторинг SNR/BER', module_id: 'astra' },
      },
      {
        path: 'astra/instances',
        name: 'AstraInstances',
        component: AstraInstancesView,
        meta: { title: 'Инстансы Astra', module_id: 'astra' },
      },
      {
        path: 'astra/playlists',
        name: 'AstraPlaylists',
        component: ModuleContainerView,
        meta: { title: 'Плейлисты Astra', module_id: 'playlist', submodule: 'astra' },
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
