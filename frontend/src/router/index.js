import { createRouter, createWebHistory } from 'vue-router'
import { getModuleRoutes } from '../modules'

const routes = getModuleRoutes()

const router = createRouter({ history: createWebHistory(), routes })

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} — NMS` : 'NMS'
})

export default router
