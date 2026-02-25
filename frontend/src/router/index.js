import { createRouter, createWebHistory } from 'vue-router'
import { getModuleRoutes, initModulesRegistry } from '../modules'

export const createAppRouter = async () => {
  await initModulesRegistry()
  const routes = getModuleRoutes()
  const router = createRouter({ history: createWebHistory(), routes })
  router.afterEach((to) => {
    document.title = to.meta.title ? `${to.meta.title} — NMS` : 'NMS'
  })
  return router
}
