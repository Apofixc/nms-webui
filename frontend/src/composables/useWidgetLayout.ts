import { ref, type Ref } from 'vue'
import type { ModuleWidget } from '@/modules/widgets'

const STORAGE_KEY = 'nms_widget_canvas_v3'
const GRID_SNAP_SIZE = 15

export type CollisionMode = 'push' | 'block' | 'off'

export interface WidgetRect {
  x: number
  y: number
  width: number
  height: number
  zIndex?: number
}

export interface LayoutPreset {
  id: string
  name: string
  isSystem?: boolean
  rects: Record<string, WidgetRect>
  active: string[]
  hidden?: string[]
  collisionMode?: CollisionMode
}

interface SavedLayout {
  rects: Record<string, WidgetRect>
  active: string[]
  hidden?: string[]
  preventCollision?: boolean
  collisionMode?: CollisionMode
}

export function useWidgetLayout() {
  const activeWidgetIds: Ref<Set<string>> = ref(new Set<string>())
  const hiddenWidgetIds: Ref<Set<string>> = ref(new Set<string>())
  const widgetRects: Ref<Record<string, WidgetRect>> = ref<Record<string, WidgetRect>>({})
  const isCustomizing = ref(false)
  const snapToGrid = ref(true)
  const preventCollision = ref(true)
  const collisionMode = ref<CollisionMode>('push')
  const collisionHighlightRect = ref<WidgetRect | null>(null)
  const maxZIndex = ref(10)
  const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)
  const isInitialized = ref(false)

  if (typeof window !== 'undefined') {
    const checkMobile = () => {
      isMobile.value = window.innerWidth < 768
    }
    window.addEventListener('resize', checkMobile)
  }

  function snap(val: number): number {
    if (!snapToGrid.value) return Math.max(0, val)
    return Math.max(0, Math.round(val / GRID_SNAP_SIZE) * GRID_SNAP_SIZE)
  }

  function isOverlapping(r1: WidgetRect, r2: WidgetRect): boolean {
    return !(
      r1.x + r1.width <= r2.x ||
      r1.x >= r2.x + r2.width ||
      r1.y + r1.height <= r2.y ||
      r1.y >= r2.y + r2.height
    )
  }

  function loadLayout(): boolean {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const parsed: SavedLayout = JSON.parse(raw)
        if (Array.isArray(parsed.active)) {
          activeWidgetIds.value = new Set(parsed.active)
        }
        if (Array.isArray(parsed.hidden)) {
          hiddenWidgetIds.value = new Set(parsed.hidden)
        }
        if (parsed.collisionMode) {
          collisionMode.value = parsed.collisionMode
          preventCollision.value = parsed.collisionMode !== 'off'
        } else if (typeof parsed.preventCollision === 'boolean') {
          preventCollision.value = parsed.preventCollision
          collisionMode.value = parsed.preventCollision ? 'push' : 'off'
        }
        if (parsed.rects && typeof parsed.rects === 'object') {
          widgetRects.value = parsed.rects
        }
        isInitialized.value = true
        return true
      }
    } catch (err) {
      console.error('Failed to load widget layout from localStorage:', err)
    }
    return false
  }

  function saveLayout() {
    try {
      const payload: SavedLayout = {
        rects: widgetRects.value,
        active: Array.from(activeWidgetIds.value),
        hidden: Array.from(hiddenWidgetIds.value),
        preventCollision: collisionMode.value !== 'off',
        collisionMode: collisionMode.value,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    } catch (err) {
      console.error('Failed to save widget layout to localStorage:', err)
    }
  }

  function initLayout(allWidgets: ModuleWidget[]) {
    const hasSaved = loadLayout()
    if (!hasSaved && allWidgets.length > 0) {
      // Авто-активация стартовых виджетов (default_active или system-modules)
      const defaultActive = allWidgets
        .filter((w) => w.default_active || w.id === 'system-modules')
        .map((w) => w.id)

      if (defaultActive.length === 0 && allWidgets[0]) {
        defaultActive.push(allWidgets[0].id)
      }

      activeWidgetIds.value = new Set(defaultActive)
      hiddenWidgetIds.value = new Set<string>()

      const defaultRects: Record<string, WidgetRect> = {}
      defaultActive.forEach((id, index) => {
        defaultRects[id] = calculateDefaultRect(index)
      })
      widgetRects.value = defaultRects
      saveLayout()
    }
    isInitialized.value = true
  }

  function isWidgetActive(id: string): boolean {
    return activeWidgetIds.value.has(id)
  }

  function isWidgetHidden(id: string): boolean {
    return hiddenWidgetIds.value.has(id)
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

  function addWidget(id: string) {
    const nextActive = new Set(activeWidgetIds.value)
    nextActive.add(id)
    activeWidgetIds.value = nextActive

    // При добавлении убираем из скрытых, если там был
    const nextHidden = new Set(hiddenWidgetIds.value)
    nextHidden.delete(id)
    hiddenWidgetIds.value = nextHidden

    if (!widgetRects.value[id]) {
      const newIndex = activeWidgetIds.value.size - 1
      widgetRects.value = {
        ...widgetRects.value,
        [id]: calculateDefaultRect(newIndex),
      }
    }
    bringToFront(id)
    saveLayout()
  }

  function removeWidget(id: string) {
    const nextActive = new Set(activeWidgetIds.value)
    nextActive.delete(id)
    activeWidgetIds.value = nextActive

    const nextHidden = new Set(hiddenWidgetIds.value)
    nextHidden.delete(id)
    hiddenWidgetIds.value = nextHidden

    saveLayout()
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

  function calculateDefaultRect(index: number = 0): WidgetRect {
    const colWidth = 360
    const rowHeight = 240
    const gap = 20
    const cols = 3

    const col = index % cols
    const row = Math.floor(index / cols)

    return {
      x: col * (colWidth + gap) + 10,
      y: row * (rowHeight + gap) + 10,
      width: colWidth,
      height: rowHeight,
      zIndex: 1,
    }
  }

  function getWidgetRect(id: string, index: number = 0): WidgetRect {
    if (widgetRects.value[id]) {
      return widgetRects.value[id]
    }
    return calculateDefaultRect(index)
  }

  function setCollisionMode(mode: CollisionMode) {
    collisionMode.value = mode
    preventCollision.value = mode !== 'off'
    collisionHighlightRect.value = null
    saveLayout()
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

    const dx = newRect.x - current.x
    const dy = newRect.y - current.y
    const mode = collisionMode.value

    if (mode === 'off') {
      collisionHighlightRect.value = null
      widgetRects.value = {
        ...widgetRects.value,
        [id]: newRect,
      }
      saveLayout()
      return
    }

    // Check collision with other active, non-hidden widgets
    let collidingWidgetId: string | null = null
    for (const otherId of activeWidgetIds.value) {
      if (otherId === id || hiddenWidgetIds.value.has(otherId)) continue
      const otherRect = widgetRects.value[otherId] || calculateDefaultRect()
      if (isOverlapping(newRect, otherRect)) {
        collidingWidgetId = otherId
        break
      }
    }

    if (mode === 'block') {
      if (collidingWidgetId) {
        // Highlight collision zone in red and prevent movement into it
        collisionHighlightRect.value = { ...newRect }
        // Keep current coordinates (block move)
        return
      } else {
        collisionHighlightRect.value = null
        widgetRects.value = {
          ...widgetRects.value,
          [id]: newRect,
        }
        saveLayout()
        return
      }
    }

    if (mode === 'push') {
      collisionHighlightRect.value = null
      const updatedRects: Record<string, WidgetRect> = {
        ...widgetRects.value,
        [id]: newRect,
      }

      const gap = 20
      let hasOverlap = true
      let passCounter = 0

      while (hasOverlap && passCounter < 10) {
        hasOverlap = false
        passCounter++

        for (const otherId of activeWidgetIds.value) {
          if (otherId === id || hiddenWidgetIds.value.has(otherId)) continue
          const otherRect = updatedRects[otherId] || calculateDefaultRect()

          if (isOverlapping(updatedRects[id], otherRect)) {
            let newX = otherRect.x
            let newY = otherRect.y

            // Directional pushing based on movement vector dx, dy
            if (Math.abs(dx) >= Math.abs(dy) && dx !== 0) {
              if (dx < 0) {
                // Moving Right to Left -> push other left
                newX = snap(updatedRects[id].x - otherRect.width - gap)
                if (newX < 0) {
                  // Fallback: push right or down
                  newX = snap(updatedRects[id].x + updatedRects[id].width + gap)
                }
              } else {
                // Moving Left to Right -> push other right
                newX = snap(updatedRects[id].x + updatedRects[id].width + gap)
              }
            } else if (Math.abs(dy) > Math.abs(dx) && dy !== 0) {
              if (dy < 0) {
                // Moving Bottom to Top -> push other up
                newY = snap(updatedRects[id].y - otherRect.height - gap)
                if (newY < 0) {
                  // Fallback: push down
                  newY = snap(updatedRects[id].y + updatedRects[id].height + gap)
                }
              } else {
                // Moving Top to Bottom -> push other down
                newY = snap(updatedRects[id].y + updatedRects[id].height + gap)
              }
            } else {
              // Default push down
              newY = snap(updatedRects[id].y + updatedRects[id].height + gap)
            }

            updatedRects[otherId] = {
              ...otherRect,
              x: Math.max(0, newX),
              y: Math.max(0, newY),
            }
            hasOverlap = true
          }
        }
      }

      widgetRects.value = updatedRects
      saveLayout()
    }
  }

  function resetLayout(allWidgets: ModuleWidget[]) {
    const defaultActive = allWidgets
      .filter((w) => w.default_active || w.id === 'system-modules')
      .map((w) => w.id)

    if (defaultActive.length === 0 && allWidgets[0]) {
      defaultActive.push(allWidgets[0].id)
    }

    activeWidgetIds.value = new Set(defaultActive)
    hiddenWidgetIds.value = new Set<string>()
    collisionHighlightRect.value = null
    const newRects: Record<string, WidgetRect> = {}

    defaultActive.forEach((id, index) => {
      newRects[id] = calculateDefaultRect(index)
    })

    widgetRects.value = newRects
    saveLayout()
  }

  // ── Layout Presets & Export/Import ────────────────────────────────────────────────
  const PRESETS_STORAGE_KEY = 'nms_widget_presets_v1'
  const userPresets = ref<LayoutPreset[]>([])
  const activePresetId = ref<string>('custom')

  function loadPresets() {
    try {
      const raw = localStorage.getItem(PRESETS_STORAGE_KEY)
      if (raw) {
        userPresets.value = JSON.parse(raw)
      }
    } catch (err) {
      console.error('Failed to load layout presets:', err)
    }
  }

  function savePresets() {
    try {
      localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(userPresets.value))
    } catch (err) {
      console.error('Failed to save layout presets:', err)
    }
  }

  function saveCurrentAsPreset(name: string): LayoutPreset {
    const newPreset: LayoutPreset = {
      id: `preset_${Date.now()}`,
      name,
      rects: { ...widgetRects.value },
      active: Array.from(activeWidgetIds.value),
      hidden: Array.from(hiddenWidgetIds.value),
      collisionMode: collisionMode.value,
    }
    userPresets.value = [...userPresets.value, newPreset]
    activePresetId.value = newPreset.id
    savePresets()
    return newPreset
  }

  function applyPreset(preset: LayoutPreset) {
    activeWidgetIds.value = new Set(preset.active || [])
    hiddenWidgetIds.value = new Set(preset.hidden || [])
    widgetRects.value = { ...(preset.rects || {}) }
    if (preset.collisionMode) {
      setCollisionMode(preset.collisionMode)
    }
    activePresetId.value = preset.id
    saveLayout()
  }

  function deletePreset(presetId: string) {
    userPresets.value = userPresets.value.filter((p) => p.id !== presetId)
    savePresets()
    if (activePresetId.value === presetId) {
      activePresetId.value = 'custom'
    }
  }

  function exportLayoutJson(): string {
    const payload = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      rects: widgetRects.value,
      active: Array.from(activeWidgetIds.value),
      hidden: Array.from(hiddenWidgetIds.value),
      collisionMode: collisionMode.value,
      preventCollision: collisionMode.value !== 'off',
    }
    return JSON.stringify(payload, null, 2)
  }

  function importLayoutJson(rawJson: string): boolean {
    try {
      const parsed = JSON.parse(rawJson)
      if (!parsed || typeof parsed !== 'object') return false
      if (Array.isArray(parsed.active)) {
        activeWidgetIds.value = new Set(parsed.active)
      }
      if (Array.isArray(parsed.hidden)) {
        hiddenWidgetIds.value = new Set(parsed.hidden)
      }
      if (parsed.collisionMode) {
        setCollisionMode(parsed.collisionMode)
      }
      if (parsed.rects && typeof parsed.rects === 'object') {
        widgetRects.value = parsed.rects
      }
      activePresetId.value = 'imported'
      saveLayout()
      return true
    } catch (err) {
      console.error('Failed to import layout JSON:', err)
      return false
    }
  }

  loadLayout()
  loadPresets()

  return {
    activeWidgetIds,
    hiddenWidgetIds,
    widgetRects,
    isCustomizing,
    snapToGrid,
    preventCollision,
    collisionMode,
    collisionHighlightRect,
    userPresets,
    activePresetId,
    isMobile,
    isInitialized,
    initLayout,
    loadLayout,
    saveLayout,
    isWidgetActive,
    isWidgetHidden,
    toggleVisibility,
    addWidget,
    removeWidget,
    bringToFront,
    getWidgetRect,
    setCollisionMode,
    updateWidgetRect,
    resetLayout,
    saveCurrentAsPreset,
    applyPreset,
    deletePreset,
    exportLayoutJson,
    importLayoutJson,
  }
}




