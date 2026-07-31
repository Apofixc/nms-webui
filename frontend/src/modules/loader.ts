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
    registerViewComponent('tuya-index', () => import('@/views/TuyaView.vue'))
}

