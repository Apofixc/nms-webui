import { ref, type Ref } from 'vue'
import type { ModuleWidget } from '@/modules/widgets'

const STORAGE_KEY = 'nms_widget_canvas_v2'
const GRID_SNAP_SIZE = 15

export interface WidgetRect {
  x: number
  y: number
  width: number
  height: number
  zIndex?: number
}

interface SavedLayout {
  rects: Record<string, WidgetRect>
  hidden: string[]
}

export function useWidgetLayout() {
  const hiddenWidgetIds: Ref<Set<string>> = ref(new Set<string>())
  const widgetRects: Ref<Record<string, WidgetRect>> = ref<Record<string, WidgetRect>>({})
  const isCustomizing = ref(false)
  const snapToGrid = ref(true)
  const maxZIndex = ref(10)

  function snap(val: number): number {
    if (!snapToGrid.value) return Math.max(0, val)
    return Math.max(0, Math.round(val / GRID_SNAP_SIZE) * GRID_SNAP_SIZE)
  }

  function loadLayout() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed: SavedLayout = JSON.parse(raw)
        if (Array.isArray(parsed.hidden)) {
          hiddenWidgetIds.value = new Set(parsed.hidden)
        }
        if (parsed.rects && typeof parsed.rects === 'object') {
          widgetRects.value = parsed.rects
        }
      }
    } catch (err) {
      console.error('Failed to load widget layout from localStorage:', err)
    }
  }

  function saveLayout() {
    try {
      const payload: SavedLayout = {
        rects: widgetRects.value,
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

  function bringToFront(id: string) {
    maxZIndex.value += 1
    const current = getWidgetRect(id, 0)
    widgetRects.value = {
      ...widgetRects.value,
      [id]: {
        ...current,
        zIndex: maxZIndex.value,
      },
    }
    saveLayout()
  }

  function getWidgetRect(id: string, index: number = 0): WidgetRect {
    if (widgetRects.value[id]) {
      return widgetRects.value[id]
    }

    // Calculate default grid position (3 columns desktop layout)
    const colWidth = 360
    const rowHeight = 240
    const gap = 20
    const cols = 3

    const col = index % cols
    const row = Math.floor(index / cols)

    const defaultRect: WidgetRect = {
      x: col * (colWidth + gap) + 10,
      y: row * (rowHeight + gap) + 10,
      width: colWidth,
      height: rowHeight,
      zIndex: 1,
    }

    return defaultRect
  }

  function updateWidgetRect(id: string, rectDelta: Partial<WidgetRect>, index: number = 0) {
    const current = getWidgetRect(id, index)
    const newRect: WidgetRect = {
      x: rectDelta.x !== undefined ? snap(rectDelta.x) : current.x,
      y: rectDelta.y !== undefined ? snap(rectDelta.y) : current.y,
      width: rectDelta.width !== undefined ? Math.max(260, snap(rectDelta.width)) : current.width,
      height: rectDelta.height !== undefined ? Math.max(160, snap(rectDelta.height)) : current.height,
      zIndex: current.zIndex || 1,
    }

    widgetRects.value = {
      ...widgetRects.value,
      [id]: newRect,
    }
    saveLayout()
  }

  function resetLayout(allWidgets: ModuleWidget[]) {
    hiddenWidgetIds.value = new Set<string>()
    const newRects: Record<string, WidgetRect> = {}

    allWidgets.forEach((w, index) => {
      const colWidth = 360
      const rowHeight = 240
      const gap = 20
      const cols = 3
      const col = index % cols
      const row = Math.floor(index / cols)

      newRects[w.id] = {
        x: col * (colWidth + gap) + 10,
        y: row * (rowHeight + gap) + 10,
        width: colWidth,
        height: rowHeight,
        zIndex: 1,
      }
    })

    widgetRects.value = newRects
    saveLayout()
  }

  loadLayout()

  return {
    hiddenWidgetIds,
    widgetRects,
    isCustomizing,
    snapToGrid,
    loadLayout,
    saveLayout,
    toggleVisibility,
    isWidgetHidden,
    bringToFront,
    getWidgetRect,
    updateWidgetRect,
    resetLayout,
  }
}
