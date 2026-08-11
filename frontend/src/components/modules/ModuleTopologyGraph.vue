<template>
  <div class="relative w-full h-[520px] bg-surface-container-lowest border border-outline-variant/50 rounded-xl overflow-hidden shadow-inner flex flex-col select-none">
    <!-- Graph Top Toolbar -->
    <div class="p-3 bg-surface-container-high/80 backdrop-blur border-b border-outline-variant/30 flex items-center justify-between z-10 text-xs">
      <div class="flex items-center gap-3">
        <span class="font-bold text-on-surface flex items-center gap-1.5">
          <span class="material-symbols-outlined text-primary text-base">hub</span>
          Топология связей модулей
        </span>
        <span class="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-mono border border-primary/20">
          {{ modules.length }} модулей
        </span>
      </div>

      <!-- Filters & Legend -->
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-3 text-[11px] text-on-surface-variant font-mono">
          <label class="flex items-center gap-1 cursor-pointer hover:text-on-surface">
            <input type="checkbox" v-model="showEvents" class="accent-primary rounded" />
            <span class="inline-block w-2.5 h-0.5 bg-emerald-400"></span>
            Pub/Sub события ({{ eventEdges.length }})
          </label>
          <label class="flex items-center gap-1 cursor-pointer hover:text-on-surface">
            <input type="checkbox" v-model="showDeps" class="accent-primary rounded" />
            <span class="inline-block w-2.5 h-0.5 bg-purple-400 stroke-dash"></span>
            Зависимости deps ({{ depEdges.length }})
          </label>
        </div>

        <div class="flex items-center gap-1 border-l border-outline-variant/30 pl-3">
          <button
            @click="zoomIn"
            class="p-1 rounded bg-surface-variant/50 hover:bg-surface-variant text-on-surface transition-colors"
            title="Приблизить"
          >
            <span class="material-symbols-outlined text-sm">add</span>
          </button>
          <button
            @click="zoomOut"
            class="p-1 rounded bg-surface-variant/50 hover:bg-surface-variant text-on-surface transition-colors"
            title="Отдалить"
          >
            <span class="material-symbols-outlined text-sm">remove</span>
          </button>
          <button
            @click="resetView"
            class="p-1 rounded bg-surface-variant/50 hover:bg-surface-variant text-on-surface transition-colors"
            title="Сбросить масштаб"
          >
            <span class="material-symbols-outlined text-sm">center_focus_strong</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Canvas Area -->
    <div
      class="flex-1 relative cursor-grab active:cursor-grabbing overflow-hidden"
      @mousedown="startPan"
      @mousemove="pan"
      @mouseup="stopPan"
      @mouseleave="stopPan"
      @wheel.prevent="onWheel"
    >
      <svg class="w-full h-full" :viewBox="viewBox">
        <defs>
          <!-- Arrow Markers -->
          <marker
            id="arrow-event"
            viewBox="0 0 10 10"
            refX="22"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#34d399" />
          </marker>

          <marker
            id="arrow-dep"
            viewBox="0 0 10 10"
            refX="22"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#c084fc" />
          </marker>

          <!-- Node Glow Filter -->
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        <!-- Edges Layer: Dependencies -->
        <g v-if="showDeps">
          <g v-for="edge in depEdges" :key="'dep-' + edge.id">
            <path
              :d="edge.pathD"
              fill="none"
              stroke="#c084fc"
              stroke-width="1.5"
              stroke-dasharray="4 3"
              stroke-opacity="0.6"
              marker-end="url(#arrow-dep)"
              :class="{ 'stroke-opacity-100 !stroke-width-2': isEdgeHighlighted(edge) }"
            />
          </g>
        </g>

        <!-- Edges Layer: Pub/Sub Events -->
        <g v-if="showEvents">
          <g v-for="edge in eventEdges" :key="'evt-' + edge.id">
            <path
              :d="edge.pathD"
              fill="none"
              stroke="#34d399"
              stroke-width="2"
              stroke-opacity="0.7"
              marker-end="url(#arrow-event)"
              :class="{ 'stroke-opacity-100 !stroke-width-3': isEdgeHighlighted(edge) }"
              @mouseenter="hoveredEdge = edge"
              @mouseleave="hoveredEdge = null"
            />
            <!-- Label on Edge Hover -->
            <text
              v-if="hoveredEdge?.id === edge.id"
              :x="edge.midX"
              :y="edge.midY - 8"
              fill="#34d399"
              font-size="10"
              font-family="monospace"
              font-weight="bold"
              text-anchor="middle"
              class="pointer-events-none drop-shadow-md"
            >
              {{ edge.label }}
            </text>
          </g>
        </g>

        <!-- Nodes Layer -->
        <g v-for="node in graphNodes" :key="node.id">
          <!-- Node Group -->
          <g
            :transform="`translate(${node.x}, ${node.y})`"
            class="cursor-pointer transition-transform duration-150 hover:scale-105"
            @click.stop="$emit('select', node.raw)"
            @mouseenter="hoveredNodeId = node.id"
            @mouseleave="hoveredNodeId = null"
          >
            <!-- Outer Ring when Selected or Hovered -->
            <circle
              r="28"
              fill="none"
              :stroke="selectedModuleId === node.id ? '#38bdf8' : (node.enabled ? '#34d399' : '#94a3b8')"
              :stroke-width="selectedModuleId === node.id ? '3' : '1.5'"
              :stroke-dasharray="selectedModuleId === node.id ? 'none' : '3 2'"
              class="transition-all"
            />

            <!-- Main Circle -->
            <circle
              r="22"
              :fill="node.enabled ? '#1e293b' : '#0f172a'"
              :stroke="node.enabled ? '#34d399' : '#64748b'"
              stroke-width="2"
              filter="url(#glow)"
            />

            <!-- Center Icon / Abbreviation -->
            <text
              y="4"
              fill="#f8fafc"
              font-size="11"
              font-weight="bold"
              font-family="sans-serif"
              text-anchor="middle"
              class="pointer-events-none"
            >
              {{ node.label.substring(0, 2).toUpperCase() }}
            </text>

            <!-- Node Label below circle -->
            <text
              y="40"
              fill="#e2e8f0"
              font-size="11"
              font-weight="600"
              font-family="sans-serif"
              text-anchor="middle"
              class="pointer-events-none"
            >
              {{ node.label }}
            </text>

            <!-- Type badge -->
            <text
              y="52"
              fill="#94a3b8"
              font-size="9"
              font-family="monospace"
              text-anchor="middle"
              class="pointer-events-none"
            >
              {{ node.type }}
            </text>
          </g>
        </g>
      </svg>

      <!-- Empty State -->
      <div v-if="modules.length === 0" class="absolute inset-0 flex items-center justify-center text-on-surface-variant text-xs font-sans">
        Нет доступных модулей для отображения топологии
      </div>

      <!-- Edge Hover Toast Indicator -->
      <div
        v-if="hoveredEdge"
        class="absolute bottom-3 left-3 bg-surface-container-high/90 backdrop-blur border border-emerald-500/40 text-emerald-300 px-3 py-1.5 rounded-lg text-xs font-mono shadow-lg flex items-center gap-2 pointer-events-none"
      >
        <span class="material-symbols-outlined text-sm">swap_horiz</span>
        <span>{{ hoveredEdge.source }} $\rightarrow$ {{ hoveredEdge.target }}: <strong>{{ hoveredEdge.label }}</strong></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ModuleManifest } from '@/modules/types'

const props = defineProps<{
  modules: ModuleManifest[]
  selectedModuleId?: string
}>()

defineEmits<{
  (e: 'select', module: ModuleManifest): void
}>()

const showEvents = ref(true)
const showDeps = ref(true)
const hoveredNodeId = ref<string | null>(null)
const hoveredEdge = ref<any | null>(null)

// Pan & Zoom state
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)
const isPanning = ref(false)
const startX = ref(0)
const startY = ref(0)

const viewBox = computed(() => {
  const width = 800 * scale.value
  const height = 500 * scale.value
  const x = panX.value - width / 2
  const y = panY.value - height / 2
  return `${x} ${y} ${width} ${height}`
})

function zoomIn() {
  scale.value = Math.max(0.4, scale.value - 0.15)
}

function zoomOut() {
  scale.value = Math.min(2.5, scale.value + 0.15)
}

function resetView() {
  scale.value = 1
  panX.value = 0
  panY.value = 0
}

function onWheel(e: WheelEvent) {
  if (e.deltaY < 0) zoomIn()
  else zoomOut()
}

function startPan(e: MouseEvent) {
  isPanning.value = true
  startX.value = e.clientX - panX.value
  startY.value = e.clientY - panY.value
}

function pan(e: MouseEvent) {
  if (!isPanning.value) return
  panX.value = e.clientX - startX.value
  panY.value = e.clientY - startY.value
}

function stopPan() {
  isPanning.value = false
}

// Compute Graph Nodes in circular arrangement
const graphNodes = computed(() => {
  const list = props.modules || []
  const count = list.length
  if (count === 0) return []

  const radius = Math.min(240, 60 + count * 25)
  return list.map((mod, index) => {
    const angle = (index / count) * 2 * Math.PI - Math.PI / 2
    return {
      id: mod.id,
      label: mod.name || mod.id,
      type: mod.type || 'feature',
      enabled: mod.enabled !== false,
      x: radius * Math.cos(angle),
      y: radius * Math.sin(angle),
      raw: mod,
    }
  })
})

const nodeMap = computed(() => {
  const map = new Map<string, any>()
  graphNodes.value.forEach((n) => map.set(n.id, n))
  return map
})

// Compute Event Pub/Sub Edges
const eventEdges = computed(() => {
  const edges: any[] = []
  props.modules.forEach((sourceMod) => {
    const sourceNode = nodeMap.value.get(sourceMod.id)
    if (!sourceNode) return

    const subscribes = sourceMod.events?.subscribes || []
    subscribes.forEach((topic) => {
      if (topic.startsWith('core.')) return
      const publisherId = topic.split('.')[0]
      const targetNode = nodeMap.value.get(publisherId)
      if (targetNode && targetNode.id !== sourceNode.id) {
        edges.push(buildCurveEdge(targetNode, sourceNode, topic, `${targetNode.id}->${sourceNode.id}:${topic}`))
      }
    })
  })
  return edges
})

// Compute Dependency Edges
const depEdges = computed(() => {
  const edges: any[] = []
  props.modules.forEach((sourceMod) => {
    const sourceNode = nodeMap.value.get(sourceMod.id)
    if (!sourceNode) return

    const deps = sourceMod.deps || []
    deps.forEach((depId) => {
      const targetNode = nodeMap.value.get(depId)
      if (targetNode && targetNode.id !== sourceNode.id) {
        edges.push(buildCurveEdge(sourceNode, targetNode, 'requires', `${sourceNode.id}->${targetNode.id}:dep`))
      }
    })
  })
  return edges
})

function buildCurveEdge(source: any, target: any, label: string, id: string) {
  const dx = target.x - source.x
  const dy = target.y - source.y
  const cx = (source.x + target.x) / 2 - dy * 0.2
  const cy = (source.y + target.y) / 2 + dx * 0.2
  return {
    id,
    source: source.id,
    target: target.id,
    label,
    pathD: `M ${source.x} ${source.y} Q ${cx} ${cy} ${target.x} ${target.y}`,
    midX: cx,
    midY: cy,
  }
}

function isEdgeHighlighted(edge: any) {
  const sel = props.selectedModuleId || hoveredNodeId.value
  return sel ? edge.source === sel || edge.target === sel : false
}
</script>
