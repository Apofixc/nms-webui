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
    // Core views are pre-registered in registry.ts
    // Module-specific views will be registered here when modules are added.
    // Example:
    // registerViewComponent('Channels', () => import('@/views/Channels.vue'))
}
