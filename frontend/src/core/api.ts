/**
 * Axios instance + типизированные API-функции.
 */
import axios from 'axios'
import type { ModuleManifest, EnableSchemaResponse } from '@/modules/types'

const http = axios.create({
    baseURL: '/',
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000,
})

// ── Interceptors ───────────────────────────────────────────────────
http.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('[API]', error?.response?.status, error?.config?.url, error?.message)
        return Promise.reject(error)
    },
)

// ── API functions ──────────────────────────────────────────────────

/** Modules */
export async function fetchModules(
    withSettings = false,
    onlyEnabled = false,
): Promise<{ items: ModuleManifest[] }> {
    const { data } = await http.get('/api/modules', {
        params: { with_settings: withSettings, only_enabled: onlyEnabled },
    })
    return data
}

export async function fetchLoadedModules(): Promise<{ items: string[] }> {
    const { data } = await http.get('/api/modules/loaded')
    return data
}

export async function fetchModuleViews(
    moduleId: string,
): Promise<{ items: Array<{ path: string; name: string; meta: Record<string, any> }> }> {
    const { data } = await http.get(`/api/modules/${moduleId}/views`)
    return data
}

export async function fetchModuleConfigSchema(): Promise<EnableSchemaResponse> {
    const { data } = await http.get('/api/modules/config-schema')
    return data
}

export async function setModuleEnabled(
    moduleId: string,
    enabled: boolean,
): Promise<any> {
    const { data } = await http.put(`/api/modules/${moduleId}/enabled`, { enabled })
    return data
}

export async function fetchModuleSettingsDefinition(
    moduleId: string,
): Promise<{ module_id: string; schema: Record<string, any>; defaults: Record<string, any>; current?: Record<string, any> }> {
    const { data } = await http.get(`/api/modules/${moduleId}/settings-definition`)
    return data
}

export async function fetchModuleSettings(
    moduleId: string,
): Promise<Record<string, any>> {
    const { data } = await http.get(`/api/modules/${moduleId}/settings`)
    return data
}

export async function saveModuleSettings(
    moduleId: string,
    body: Record<string, any>,
): Promise<any> {
    const { data } = await http.put(`/api/modules/${moduleId}/settings`, body)
    return data
}

/** Health check */
export async function fetchRoot(): Promise<{ service: string; docs: string }> {
    const { data } = await http.get('/')
    return data
}

export default http
