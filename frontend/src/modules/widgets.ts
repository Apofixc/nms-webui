import { ref } from 'vue'
import { fetchModuleWidgets } from '@/core/api'

export interface ModuleWidget {
  id: string
  module_id: string
  title: string
  description: string
  component: string
  endpoint?: string
  size?: 'small' | 'medium' | 'large'
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
