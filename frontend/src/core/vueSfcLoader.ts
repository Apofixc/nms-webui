/**
 * In-Browser Vue SFC Loader — динамическая подгрузка и компиляция сырых .vue файлов
 * прямо в браузере клиента без необходимости выполнения npm run build.
 */
import * as Vue from 'vue'
import { http } from '@/core/api'

const loadedSfcCache = new Map<string, any>()

/**
 * Загрузить и скомпилировать .vue файл с бэкенда по относительной ссылке.
 * Пример: loadRemoteVueSFC('tuya', 'views/TuyaDeviceView.vue')
 */
export async function loadRemoteVueSFC(moduleId: string, relativePath: string): Promise<any> {
    const cacheKey = `${moduleId}:${relativePath}`
    if (loadedSfcCache.has(cacheKey)) {
        return loadedSfcCache.get(cacheKey)
    }

    const cleanPath = relativePath.replace(/^\//, '')
    const url = `/api/modules/${moduleId}/files/${cleanPath}`

    try {
        const { data: sfcText } = await http.get(url, { responseType: 'text' })
        const component = parseAndCompileSfc(sfcText, cacheKey)
        loadedSfcCache.set(cacheKey, component)
        return component
    } catch (err) {
        console.error(`[vueSfcLoader] Failed to load remote Vue SFC ${url}:`, err)
        return null
    }
}

/**
 * Парсер и компилятор сырого текста .vue файла в инстанс Vue 3 компонента.
 */
export function parseAndCompileSfc(sfcText: string, fileKey: string = 'DynamicComponent'): any {
    if (!sfcText || typeof sfcText !== 'string') {
        return null
    }

    // 1. Извлечение <template>
    const templateMatch = sfcText.match(/<template>([\s\S]*)<\/template>/i)
    const templateContent = templateMatch ? templateMatch[1].trim() : ''

    // 2. Извлечение <script setup> или <script>
    const scriptMatch = sfcText.match(/<script(?:\s+setup)?.*?>([\s\S]*)<\/script>/i)
    const scriptContent = scriptMatch ? scriptMatch[1].trim() : ''

    // 3. Извлечение и внедрение <style>
    const styleMatch = sfcText.match(/<style.*?>([\s\S]*)<\/style>/i)
    if (styleMatch && styleMatch[1].trim()) {
        const styleId = `sfc-style-${fileKey.replace(/[^a-zA-Z0-9_-]/g, '_')}`
        if (!document.getElementById(styleId)) {
            const styleEl = document.createElement('style')
            styleEl.id = styleId
            styleEl.textContent = styleMatch[1].trim()
            document.head.appendChild(styleEl)
        }
    }

    // 4. Запуск скрипта в изоляции с предоставлением Vue API (ref, reactive, computed, onMounted и т.д.)
    let scriptExport: any = {}
    if (scriptContent) {
        try {
            const vueKeys = Object.keys(Vue)
            const vueValues = Object.values(Vue)

            // Нормализация экспорта
            let cleanScript = scriptContent
                .replace(/import\s+.*?\s+from\s+['"].*?['"];?/g, '')
                .replace(/export\s+default\s+/g, 'return ')

            if (!cleanScript.includes('return ')) {
                cleanScript += '\nreturn {};'
            }

            const factory = new Function(...vueKeys, cleanScript)
            scriptExport = factory(...vueValues) || {}
        } catch (e) {
            console.warn(`[vueSfcLoader] Error executing script block in ${fileKey}:`, e)
            scriptExport = {}
        }
    }

    // 5. Компиляция шаблона в render-функцию
    if (templateContent) {
        try {
            const renderFn = (Vue as any).compile ? (Vue as any).compile(templateContent) : null
            if (renderFn) {
                if (typeof scriptExport === 'function') {
                    const setupFn = scriptExport
                    scriptExport = Vue.defineComponent({
                        setup: setupFn,
                        render: renderFn,
                    })
                } else {
                    scriptExport.render = renderFn
                    scriptExport = Vue.defineComponent(scriptExport)
                }
            } else {
                scriptExport = Vue.defineComponent(scriptExport)
            }
        } catch (e) {
            console.error(`[vueSfcLoader] Template compilation error in ${fileKey}:`, e)
            scriptExport = Vue.defineComponent(scriptExport)
        }
    } else {
        scriptExport = Vue.defineComponent(scriptExport)
    }

    return scriptExport
}
