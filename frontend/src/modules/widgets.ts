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
  path?: string
  icon?: string
  action_id?: string
  endpoint?: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  payload?: Record<string, any>
  confirm?: string
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

export interface WidgetPermissions {
  view?: string
  control?: string
}

export interface ModuleWidget {
  id: string
  module_id: string
  title: string
  description: string
  component: string
  endpoint?: string
  stream_endpoint?: string
  size?: 'small' | 'medium' | 'large'
  refresh_interval?: number
  type?: WidgetType
  default_active?: boolean
  resizable?: boolean
  view_permission?: string
  control_permission?: string
  permissions?: WidgetPermissions
}

/**
 * Standard typed props contract for custom Vue widget components
 */
export interface WidgetProps<T = WidgetData> {
  data: T | null
  loading: boolean
  error: string | null
  canControl?: boolean
  isCustomizing?: boolean
  widget?: ModuleWidget
}

/**
 * Standard typed emits contract for custom Vue widget components
 */
export type WidgetEmits = {
  (e: 'refresh'): void
  (e: 'action', action: WidgetAction): void
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

/**
 * Execute interactive action for a widget endpoint
 */
export async function executeWidgetAction(action: WidgetAction): Promise<any> {
  if (!action.endpoint) {
    throw new Error('Action endpoint is missing')
  }
  const method = (action.method || 'POST').toLowerCase()
  const payload = action.payload || {}

  if (method === 'get') {
    const { data } = await http.get(action.endpoint, { params: payload })
    return data
  } else if (method === 'put') {
    const { data } = await http.put(action.endpoint, payload)
    return data
  } else if (method === 'delete') {
    const { data } = await http.delete(action.endpoint, { data: payload })
    return data
  } else {
    const { data } = await http.post(action.endpoint, payload)
    return data
  }
}
