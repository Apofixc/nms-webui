/**
 * In-Browser Vue SFC Loader — динамическая подгрузка и компиляция сырых .vue файлов
 * прямо в браузере клиента с использованием vue3-sfc-loader.
 */
import * as Vue from 'vue'
import * as Pinia from 'pinia'
import * as VueRouter from 'vue-router'
import { loadModule, type Options } from 'vue3-sfc-loader'
import { http } from '@/core/api'

const loadedSfcCache = new Map<string, any>()

const defaultOptions: Options = {
    moduleCache: {
        vue: Vue,
        pinia: Pinia,
        'vue-router': VueRouter,
    },
    async getFile(url: string) {
        const res = await http.get(url, { responseType: 'text' })
        return res.data
    },
    addStyle(textContent: string, scopeId?: string) {
        const styleId = scopeId ? `sfc-style-${scopeId}` : undefined
        if (styleId && document.getElementById(styleId)) {
            return
        }
        const styleEl = document.createElement('style')
        if (styleId) styleEl.id = styleId
        if (scopeId) styleEl.setAttribute('scoped', scopeId)
        styleEl.textContent = textContent
        document.head.appendChild(styleEl)
    },
    log(type: string, ...args: any[]) {
        if (type === 'error') {
            console.error('[vueSfcLoader]', ...args)
        } else if (type === 'warn') {
            console.warn('[vueSfcLoader]', ...args)
        }
    },
}

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
        const component = await loadModule(url, defaultOptions)
        if (component) {
            loadedSfcCache.set(cacheKey, component)
        }
        return component
    } catch (err) {
        console.error(`[vueSfcLoader] Failed to load remote Vue SFC ${url}:`, err)
        return null
    }
}

/**
 * Функция альтернативной компиляции сырого текста .vue файла в компонент Vue.
 */
export async function parseAndCompileSfc(sfcText: string, fileKey: string = 'DynamicComponent'): Promise<any> {
    if (!sfcText || typeof sfcText !== 'string') {
        return null
    }

    const options: Options = {
        ...defaultOptions,
        async getFile() {
            return sfcText
        },
    }

    try {
        return await loadModule(`${fileKey}.vue`, options)
    } catch (e) {
        console.error(`[vueSfcLoader] Error compiling SFC text for ${fileKey}:`, e)
        return null
    }
}

