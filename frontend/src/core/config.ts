/**
 * Application config — loads runtime configuration.
 */
export interface AppConfig {
    apiBaseUrl: string
}

let _config: AppConfig | null = null

export function getConfig(): AppConfig {
    if (!_config) {
        _config = {
            apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/',
        }
    }
    return _config
}
