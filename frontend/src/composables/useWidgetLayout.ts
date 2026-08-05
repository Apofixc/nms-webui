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

export interface DesktopWorkspace {
  id: string
  name: string
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
  const collisionHighlightRects = ref<WidgetRect[]>([])
  const dragGhostRect = ref<WidgetRect | null>(null)
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

  function getIntersectionRect(r1: WidgetRect, r2: WidgetRect): WidgetRect | null {
    const ix1 = Math.max(r1.x, r2.x)
    const iy1 = Math.max(r1.y, r2.y)
    const ix2 = Math.min(r1.x + r1.width, r2.x + r2.width)
    const iy2 = Math.min(r1.y + r1.height, r2.y + r2.height)

    if (ix2 > ix1 && iy2 > iy1) {
      return {
        x: ix1,
        y: iy1,
        width: ix2 - ix1,
        height: iy2 - iy1,
      }
    }
    return null
  }

  function clearCollisionHighlight() {
    collisionHighlightRect.value = null
    collisionHighlightRects.value = []
    dragGhostRect.value = null
  }

  const DESKTOPS_STORAGE_KEY = 'nms_widget_desktops_v1'
  const ACTIVE_DESKTOP_STORAGE_KEY = 'nms_active_desktop_id_v1'

  const desktops = ref<DesktopWorkspace[]>([])
  const activeDesktopId = ref<string>('')

  function syncCurrentDesktopToState() {
    if (!activeDesktopId.value) return
    const idx = desktops.value.findIndex(d => d.id === activeDesktopId.value)
    if (idx !== -1) {
      desktops.value[idx] = {
        ...desktops.value[idx],
        rects: { ...widgetRects.value },
        active: Array.from(activeWidgetIds.value),
        hidden: Array.from(hiddenWidgetIds.value),
        collisionMode: collisionMode.value,
      }
    }
  }

  function saveDesktops() {
    try {
      syncCurrentDesktopToState()
      localStorage.setItem(DESKTOPS_STORAGE_KEY, JSON.stringify(desktops.value))
      if (activeDesktopId.value) {
        localStorage.setItem(ACTIVE_DESKTOP_STORAGE_KEY, activeDesktopId.value)
      }
    } catch (err) {
      console.error('Failed to save desktops to localStorage:', err)
    }
  }

  function applyDesktop(id: string) {
    const target = desktops.value.find(d => d.id === id)
    if (!target) return
    activeDesktopId.value = id
    activeWidgetIds.value = new Set(target.active || [])
    hiddenWidgetIds.value = new Set(target.hidden || [])
    widgetRects.value = { ...(target.rects || {}) }
    if (target.collisionMode) {
      collisionMode.value = target.collisionMode
      preventCollision.value = target.collisionMode !== 'off'
    }
  }

  function loadDesktops(): boolean {
    try {
      const raw = localStorage.getItem(DESKTOPS_STORAGE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed) && parsed.length > 0) {
          desktops.value = parsed
          const savedActiveId = localStorage.getItem(ACTIVE_DESKTOP_STORAGE_KEY)
          const targetId = savedActiveId && desktops.value.some(d => d.id === savedActiveId)
            ? savedActiveId
            : desktops.value[0].id
          applyDesktop(targetId)
          isInitialized.value = true
          return true
        }
      }
    } catch (err) {
      console.error('Failed to load desktops from localStorage:', err)
    }
    return false
  }

  function switchDesktop(id: string) {
    if (id === activeDesktopId.value) return
    syncCurrentDesktopToState()
    applyDesktop(id)
    localStorage.setItem(ACTIVE_DESKTOP_STORAGE_KEY, id)
    saveDesktops()
  }

  function createDesktop(name?: string, copyCurrent: boolean = false, allWidgets: ModuleWidget[] = []) {
    syncCurrentDesktopToState()
    const newId = `desktop_${Date.now()}`
    const defaultName = name && name.trim() ? name.trim() : `Рабочий стол ${desktops.value.length + 1}`

    let newRects: Record<string, WidgetRect> = {}
    let newActive: string[] = []
    let newHidden: string[] = []

    if (copyCurrent) {
      newRects = JSON.parse(JSON.stringify(widgetRects.value))
      newActive = Array.from(activeWidgetIds.value)
      newHidden = Array.from(hiddenWidgetIds.value)
    } else {
      const defaultActive = allWidgets
        .filter((w) => w.default_active || w.id === 'system-modules')
        .map((w) => w.id)

      if (defaultActive.length === 0 && allWidgets[0]) {
        defaultActive.push(allWidgets[0].id)
      }
      newActive = defaultActive
      defaultActive.forEach((wId, index) => {
        newRects[wId] = calculateDefaultRect(index)
      })
    }

    const newDesktop: DesktopWorkspace = {
      id: newId,
      name: defaultName,
      rects: newRects,
      active: newActive,
      hidden: newHidden,
      collisionMode: collisionMode.value,
    }

    desktops.value.push(newDesktop)
    switchDesktop(newId)
  }

  function renameDesktop(id: string, newName: string) {
    const target = desktops.value.find(d => d.id === id)
    if (target && newName.trim()) {
      target.name = newName.trim()
      saveDesktops()
    }
  }

  function deleteDesktop(id: string) {
    if (desktops.value.length <= 1) return
    const index = desktops.value.findIndex(d => d.id === id)
    if (index === -1) return

    desktops.value.splice(index, 1)
    if (activeDesktopId.value === id) {
      const nextId = desktops.value[Math.max(0, index - 1)].id
      applyDesktop(nextId)
      localStorage.setItem(ACTIVE_DESKTOP_STORAGE_KEY, nextId)
    }
    saveDesktops()
  }

  function duplicateDesktop(id: string) {
    syncCurrentDesktopToState()
    const target = desktops.value.find(d => d.id === id)
    if (!target) return

    const newId = `desktop_${Date.now()}`
    const newDesktop: DesktopWorkspace = {
      ...JSON.parse(JSON.stringify(target)),
      id: newId,
      name: `${target.name} (копия)`,
    }

    desktops.value.push(newDesktop)
    switchDesktop(newId)
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
      saveDesktops()
    } catch (err) {
      console.error('Failed to save widget layout to localStorage:', err)
    }
  }

  function initLayout(allWidgets: ModuleWidget[]) {
    const hasDesktops = loadDesktops()
    if (!hasDesktops) {
      const hasSaved = loadLayout()
      const defaultActive = hasSaved && activeWidgetIds.value.size > 0
        ? Array.from(activeWidgetIds.value)
        : allWidgets.filter((w) => w.default_active || w.id === 'system-modules').map((w) => w.id)

      if (defaultActive.length === 0 && allWidgets[0]) {
        defaultActive.push(allWidgets[0].id)
      }

      const defaultRects: Record<string, WidgetRect> = hasSaved && Object.keys(widgetRects.value).length > 0
        ? { ...widgetRects.value }
        : {}

      if (!hasSaved) {
        defaultActive.forEach((id, index) => {
          defaultRects[id] = calculateDefaultRect(index)
        })
      }

      const defaultDesktop: DesktopWorkspace = {
        id: 'desktop_main',
        name: 'Основной',
        rects: defaultRects,
        active: defaultActive,
        hidden: Array.from(hiddenWidgetIds.value),
        collisionMode: collisionMode.value,
      }

      desktops.value = [defaultDesktop]
      activeDesktopId.value = 'desktop_main'
      applyDesktop('desktop_main')
      saveDesktops()
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
    clearCollisionHighlight()
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
      clearCollisionHighlight()
      widgetRects.value = {
        ...widgetRects.value,
        [id]: newRect,
      }
      saveLayout()
      return
    }

    // Check collision with other active, non-hidden widgets
    const collidingRects: WidgetRect[] = []
    for (const otherId of activeWidgetIds.value) {
      if (otherId === id || hiddenWidgetIds.value.has(otherId)) continue
      const otherRect = widgetRects.value[otherId] || calculateDefaultRect()
      const intersect = getIntersectionRect(newRect, otherRect)
      if (intersect) {
        collidingRects.push(intersect)
      }
    }

    if (mode === 'block') {
      if (collidingRects.length > 0) {
        // Highlight intersection area(s) in red hatch pattern and show drag ghost box
        collisionHighlightRects.value = collidingRects
        collisionHighlightRect.value = collidingRects[0]
        dragGhostRect.value = newRect
        return
      } else {
        clearCollisionHighlight()
        widgetRects.value = {
          ...widgetRects.value,
          [id]: newRect,
        }
        saveLayout()
        return
      }
    }

    if (mode === 'push') {
      clearCollisionHighlight()
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
    clearCollisionHighlight()
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
    collisionHighlightRects,
    dragGhostRect,
    clearCollisionHighlight,
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
    desktops,
    activeDesktopId,
    switchDesktop,
    createDesktop,
    renameDesktop,
    deleteDesktop,
    duplicateDesktop,
  }
}




