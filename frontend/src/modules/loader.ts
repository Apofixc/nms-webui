/**
 * Module view loader — automatic dynamic component resolution.
 *
 * Automatically discovers all Vue view files in src/views and src/modules/
 * using Vite glob imports without needing hardcoded component registrations.
 */
import { registerViewComponent } from './registry'

const viewModules = import.meta.glob<any>([
  '../views/**/*.vue',
  '../modules/**/*.vue',
])

/**
 * Register all dynamically discovered module views.
 * Call this at app startup.
 */
export function registerAllModuleViews() {
  for (const path in viewModules) {
    const filename = path.split('/').pop()?.replace(/\.vue$/, '') || ''
    if (!filename) continue

    const loader = viewModules[path] as () => Promise<any>

    // 1. Exact filename (e.g. "TuyaView")
    registerViewComponent(filename, loader)

    // 2. Kebab-case filename (e.g. "tuya-view")
    const kebabName = filename.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()
    registerViewComponent(kebabName, loader)

    // 3. Module route conventions (e.g. "tuya-index", "tuya")
    const baseName = kebabName.replace(/-view$/, '')
    registerViewComponent(`${baseName}-index`, loader)
    registerViewComponent(baseName, loader)
  }
}
