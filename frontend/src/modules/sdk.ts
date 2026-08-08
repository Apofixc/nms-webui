/**
 * Module SDK — единая точка входа для разработки фронтенд-модулей и виджетов.
 *
 * Собирает в одном месте всё публичное API, которое нужно разработчику
 * модуля: типы манифестов и маршрутов, контракты виджетов, регистрацию
 * компонентов, HTTP-клиент и локализацию.
 *
 * Использование в модуле:
 *
 *   import type { WidgetProps, WidgetData, ModuleWidget } from '@/modules/sdk'
 *   import { http, t, registerWidgetComponent, executeWidgetAction } from '@/modules/sdk'
 */

// --- Типы модульной системы (манифесты, маршруты, меню) ---
export type {
    RouteMeta,
    RouteDefinition,
    MenuItem,
    MenuConfig,
    ModuleManifest,
    ModuleRegistry,
    SidebarGroup,
    EnableSchemaNode,
    EnableSchemaResponse,
} from './types'

// --- Контракты и хелперы виджетов ---
export type {
    WidgetStatus,
    WidgetType,
    WidgetMetric,
    WidgetAction,
    WidgetData,
    WidgetPermissions,
    ModuleWidget,
    WidgetProps,
    WidgetEmits,
} from './widgets'
export {
    activeWidgets,
    loadModuleWidgets,
    fetchWidgetData,
    executeWidgetAction,
} from './widgets'

// --- Регистрация компонентов (views и widgets) ---
export {
    registerViewComponent,
    getViewComponent,
    registerWidgetComponent,
    getWidgetComponentLoader,
    loadModuleLocales,
    getModuleRoutes,
    getSidebarGroups,
    getFooterItems,
} from './registry'

// --- HTTP-клиент и API ядра ---
export { http, fetchModules, fetchLoadedModules, fetchModuleViews, fetchModuleWidgets } from '@/core/api'

// --- Локализация ---
export { t, registerModuleTranslations } from '@/core/i18n'
