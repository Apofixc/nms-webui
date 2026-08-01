import { ref, watch, type Ref } from 'vue'
import type { ModuleWidget } from '@/modules/widgets'

const STORAGE_KEY = 'nms_widget_layout_v1'

interface SavedLayout {
  order: string[]
  hidden: string[]
}

export function useWidgetLayout() {
  const hiddenWidgetIds: Ref<Set<string>> = ref(new Set<string>())
  const widgetOrder: Ref<string[]> = ref<string[]>([])
  const isCustomizing = ref(false)

  function loadLayout() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed: SavedLayout = JSON.parse(raw)
        if (Array.isArray(parsed.hidden)) {
          hiddenWidgetIds.value = new Set(parsed.hidden)
        }
        if (Array.isArray(parsed.order)) {
          widgetOrder.value = parsed.order
        }
      }
    } catch (err) {
      console.error('Failed to load widget layout from localStorage:', err)
    }
  }

  function saveLayout() {
    try {
      const payload: SavedLayout = {
        order: widgetOrder.value,
        hidden: Array.from(hiddenWidgetIds.value),
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    } catch (err) {
      console.error('Failed to save widget layout to localStorage:', err)
    }
  }

  function toggleVisibility(id: string) {
    const next = new Set(hiddenWidgetIds.value)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    hiddenWidgetIds.value = next
    saveLayout()
  }

  function isWidgetHidden(id: string): boolean {
    return hiddenWidgetIds.value.has(id)
  }

  function setWidgetOrder(newOrder: string[]) {
    widgetOrder.value = newOrder
    saveLayout()
  }

  function moveWidget(fromIndex: number, toIndex: number) {
    if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) return
    const order = [...widgetOrder.value]
    const [moved] = order.splice(fromIndex, 1)
    order.splice(toIndex, 0, moved)
    widgetOrder.value = order
    saveLayout()
  }

  function resetLayout(allWidgets: ModuleWidget[]) {
    hiddenWidgetIds.value = new Set<string>()
    widgetOrder.value = allWidgets.map((w) => w.id)
    saveLayout()
  }

  function syncAvailableWidgets(allWidgets: ModuleWidget[]) {
    const allIds = allWidgets.map((w) => w.id)
    // Add missing new widgets to the end of order list
    const currentOrder = [...widgetOrder.value]
    allIds.forEach((id) => {
      if (!currentOrder.includes(id)) {
        currentOrder.push(id)
      }
    })
    // Remove deleted widgets from order
    widgetOrder.value = currentOrder.filter((id) => allIds.includes(id))
  }

  loadLayout()

  return {
    hiddenWidgetIds,
    widgetOrder,
    isCustomizing,
    loadLayout,
    saveLayout,
    toggleVisibility,
    isWidgetHidden,
    setWidgetOrder,
    moveWidget,
    resetLayout,
    syncAvailableWidgets,
  }
}
