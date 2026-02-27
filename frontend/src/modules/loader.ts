/**
 * Module view loader — dynamic component resolution.
 *
 * When a new module is added, register its view components here.
 */
import { registerViewComponent } from './registry'

/**
 * Register all known module views.
 * Call this at app startup.
 */
export function registerAllModuleViews() {
    // === Astra module views ===
    registerViewComponent('astra-instances', () => import('@/views/astra/InstancesView.vue'))
    registerViewComponent('astra-monitoring', () => import('@/views/astra/MonitoringView.vue'))
    registerViewComponent('astra-channels', () => import('@/views/astra/ChannelsView.vue'))
}
