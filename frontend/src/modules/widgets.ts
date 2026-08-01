import { ref } from 'vue'
import { fetchModuleWidgets, http } from '@/core/api'

export type WidgetStatus = 'ok' | 'warning' | 'error' | 'info'
export type WidgetType = 'summary' | 'stat' | 'list' | 'custom'

export interface WidgetMetric {
  id: string
  label: string
  value: any
  unit?: string
  status?: WidgetStatus
  icon?: string
}

export interface WidgetAction {
  label: string
  path: string
  icon?: string
}

export interface WidgetData {
  status?: WidgetStatus
  type?: WidgetType
  title?: string
  metrics?: WidgetMetric[]
  items?: Array<Record<string, any>>
  actions?: WidgetAction[]
  updated_at?: string
  extra?: Record<string, any>
}

export interface ModuleWidget {
  id: string
  module_id: string
  title: string
  description: string
  component: string
  endpoint?: string
  size?: 'small' | 'medium' | 'large'
  refresh_interval?: number
  type?: WidgetType
  default_active?: boolean
}

export const activeWidgets = ref<ModuleWidget[]>([])

export async function loadModuleWidgets(): Promise<ModuleWidget[]> {
  try {
    const res = await fetchModuleWidgets()
    activeWidgets.value = res?.items || []
    return activeWidgets.value
  } catch (err) {
    console.error('Failed to load module widgets:', err)
    activeWidgets.value = []
    return []
  }
}

export async function fetchWidgetData(endpoint: string): Promise<WidgetData> {
  const { data } = await http.get<WidgetData>(endpoint)
  return data
}
