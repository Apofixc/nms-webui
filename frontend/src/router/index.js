import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Overview', component: () => import('../views/Dashboard.vue'), meta: { title: 'Общая информация' } },
  { path: '/instances', name: 'Instances', component: () => import('../views/Instances.vue'), meta: { title: 'Управление экземплярами' } },
  { path: '/channels', name: 'Channels', component: () => import('../views/Channels.vue'), meta: { title: 'Каналы' } },
  { path: '/monitors', name: 'Monitors', component: () => import('../views/Monitors.vue'), meta: { title: 'Мониторы' } },
  { path: '/subscribers', name: 'Subscribers', component: () => import('../views/Subscribers.vue'), meta: { title: 'Подписка' } },
  { path: '/dvb', name: 'Dvb', component: () => import('../views/Dvb.vue'), meta: { title: 'DVB-адаптеры' } },
  { path: '/system', name: 'System', component: () => import('../views/System.vue'), meta: { title: 'Система' } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} — NMS` : 'NMS'
})

export default router
