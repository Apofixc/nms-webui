/**
 * Module view & widget loader — automatic dynamic component resolution.
 *
 * Automatically discovers all Vue view files in src/views and src/modules/
 * and all widget components in src/widgets/ and src/modules/
 * using Vite glob imports without needing hardcoded component registrations.
 */
import { registerViewComponent, registerWidgetComponent } from './registry'

// 1. Specific glob scanner for widget components
const widgetModules = import.meta.glob<any>([
  '../widgets/**/*.vue',
  '../modules/**/widgets/**/*.vue',
  '../modules/**/*Widget.vue',
])

// 2. Glob scanner for view/page components
const viewModules = import.meta.glob<any>([
  '../views/**/*.vue',
  '../modules/**/*.vue',
])

/**
 * Register all dynamically discovered module views and widget components.
 * Call this at app startup.
 */
export function registerAllModuleViews() {
  // Register Widgets strictly from widget scanner
  for (const path in widgetModules) {
    const filename = path.split('/').pop()?.replace(/\.vue$/, '') || ''
    if (!filename) continue

    const loader = widgetModules[path] as () => Promise<any>
    const kebabName = filename.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()

    registerWidgetComponent(filename, loader)
    registerWidgetComponent(kebabName, loader)
    const baseName = kebabName.replace(/-widget$/, '')
    registerWidgetComponent(baseName, loader)
  }

  // Register Views (skipping Widget components)
  for (const path in viewModules) {
    const filename = path.split('/').pop()?.replace(/\.vue$/, '') || ''
    if (!filename || /widget$/i.test(filename)) continue

    const loader = viewModules[path] as () => Promise<any>
    const kebabName = filename.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase()

    registerViewComponent(filename, loader)
    registerViewComponent(kebabName, loader)
    const baseName = kebabName.replace(/-view$/, '')
    registerViewComponent(`${baseName}-index`, loader)
    registerViewComponent(baseName, loader)
  }
}


