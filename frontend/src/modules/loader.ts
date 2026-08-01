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
    const kebabName = filename.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()

    if (/widget$/i.test(filename)) {
      // Module widget component (e.g. TuyaWidget.vue)
      registerWidgetComponent(filename, loader)
      registerWidgetComponent(kebabName, loader)
      const baseName = kebabName.replace(/-widget$/, '')
      registerWidgetComponent(baseName, loader)
    } else {
      // Module view/page component (e.g. TuyaView.vue)
      registerViewComponent(filename, loader)
      registerViewComponent(kebabName, loader)
      const baseName = kebabName.replace(/-view$/, '')
      registerViewComponent(`${baseName}-index`, loader)
      registerViewComponent(baseName, loader)
    }
  }
}

