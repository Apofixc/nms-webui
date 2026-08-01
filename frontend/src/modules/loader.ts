/**
 * Module view loader — automatic dynamic component resolution.
 *
 * Automatically discovers all Vue view files in src/views and src/modules/
 * using Vite glob imports without needing hardcoded component registrations.
 */
import { registerViewComponent, registerWidgetComponent } from './registry'

const viewModules = import.meta.glob<any>([
  '../views/**/*.vue',
  '../modules/**/*.vue',
])

/**
 * Register all dynamically discovered module views and widget components.
 * Call this at app startup.
 */
export function registerAllModuleViews() {
  for (const path in viewModules) {
    const filename = path.split('/').pop()?.replace(/\.vue$/, '') || ''
    if (!filename) continue

    const loader = viewModules[path] as () => Promise<any>

    // 1. Exact filename (e.g. "TuyaView", "TuyaWidget")
    registerViewComponent(filename, loader)
    registerWidgetComponent(filename, loader)

    // 2. Kebab-case filename (e.g. "tuya-view", "tuya-widget")
    const kebabName = filename.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()
    registerViewComponent(kebabName, loader)
    registerWidgetComponent(kebabName, loader)

    // 3. Module route conventions (e.g. "tuya-index", "tuya")
    const baseName = kebabName.replace(/-(view|widget)$/, '')
    registerViewComponent(`${baseName}-index`, loader)
    registerViewComponent(baseName, loader)
    registerWidgetComponent(baseName, loader)
  }
}

