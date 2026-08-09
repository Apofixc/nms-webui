import { http } from '@/core/api'

export interface SubscriptionSourceItem {
  id: string
  name: string
  description?: string
  type: 'system' | 'module'
  version?: string
}

export interface SubscribableSources {
  system: SubscriptionSourceItem
  modules: SubscriptionSourceItem[]
  severities: { id: string; name: string }[]
  available_channels: { id: string; name: string }[]
}

export interface UserSubscription {
  id: string
  user_id: string
  name: string
  source_type: 'system' | 'module'
  module_id: string
  min_severity: 'info' | 'success' | 'warning' | 'error'
  channels: string[]
  mute_until?: string | null
  enabled: boolean
  created_at?: string
  updated_at?: string
}

export async function apiFetchSubscriptionSources(): Promise<SubscribableSources> {
  const { data } = await http.get<SubscribableSources>('/api/subscriptions/sources')
  return data
}

export async function apiFetchUserSubscriptions(): Promise<UserSubscription[]> {
  const { data } = await http.get<UserSubscription[]>('/api/subscriptions')
  return data
}

export async function apiCreateSubscription(payload: Partial<UserSubscription>): Promise<UserSubscription> {
  const { data } = await http.post<UserSubscription>('/api/subscriptions', payload)
  return data
}

export async function apiUpdateSubscription(subId: string, payload: Partial<UserSubscription>): Promise<UserSubscription> {
  const { data } = await http.put<UserSubscription>(`/api/subscriptions/${subId}`, payload)
  return data
}

export async function apiDeleteSubscription(subId: string): Promise<{ status: string; deleted: boolean; id: string }> {
  const { data } = await http.delete<{ status: string; deleted: boolean; id: string }>(`/api/subscriptions/${subId}`)
  return data
}

export async function apiToggleSubscription(subId: string): Promise<UserSubscription> {
  const { data } = await http.post<UserSubscription>(`/api/subscriptions/${subId}/toggle`)
  return data
}
