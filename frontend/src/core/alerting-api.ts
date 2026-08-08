import { http } from '@/core/api'

export interface AlertChannel {
    id?: string
    name: string
    type: 'telegram' | 'discord' | 'viber' | 'email' | 'webhook' | 'syslog'
    enabled: boolean
    min_type: 'info' | 'success' | 'warning' | 'error'
    categories: string
    config: Record<string, any>
    created_at?: string
}

export interface AlertLogEntry {
    id: number
    channel_id: string
    channel_type: string
    title: string
    message: string
    severity: 'info' | 'success' | 'warning' | 'error'
    category: string
    success: boolean
    error_message?: string | null
    created_at: string
}

export async function apiFetchAlertChannels(): Promise<AlertChannel[]> {
    const { data } = await http.get<AlertChannel[]>('/api/alerting/channels')
    return data
}

export async function apiCreateAlertChannel(payload: AlertChannel) {
    const { data } = await http.post<{ status: string; id: string }>('/api/alerting/channels', payload)
    return data
}

export async function apiUpdateAlertChannel(id: string, payload: AlertChannel) {
    const { data } = await http.put<{ status: string; id: string }>(`/api/alerting/channels/${id}`, payload)
    return data
}

export async function apiDeleteAlertChannel(id: string) {
    const { data } = await http.delete<{ status: string; id: string }>(`/api/alerting/channels/${id}`)
    return data
}

export async function apiTestAlertChannel(id: string): Promise<{ status: string; success: boolean }> {
    const { data } = await http.post<{ status: string; success: boolean }>(`/api/alerting/channels/${id}/test`)
    return data
}

export async function apiFetchAlertLog(limit = 50, offset = 0): Promise<AlertLogEntry[]> {
    const { data } = await http.get<AlertLogEntry[]>('/api/alerting/log', {
        params: { limit, offset }
    })
    return data
}
