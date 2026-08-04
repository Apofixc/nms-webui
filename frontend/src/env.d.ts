/// <reference types="vite/client" />

declare module '*.vue' {
    import type { DefineComponent } from 'vue'
    const component: DefineComponent<{}, {}, any>
    export default component
}

declare module 'vue3-sfc-loader' {
    import type { Options, ModuleExport } from 'vue3-sfc-loader/dist/types/vue3-esm/types'
    export function loadModule(path: string, options?: Options): Promise<ModuleExport>
    export type { Options, ModuleExport }
}


