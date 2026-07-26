/**
 * Widget Registry Engine for NMS-WebUI v2.
 * Allows modules to contribute customizable dashboard widgets.
 */
import type { WidgetDefinition, PlacedWidget } from './types'
import { ref } from 'vue'

const availableWidgets = ref<WidgetDefinition[]>([
  {
    id: 'astra-bitrate-cc',
    module_id: 'astra',
    module_name: 'Astra Broadcast',
    title: 'График битрейта и ошибок CC',
    description: 'Отображение суммарного потока вещания и счетчик Continuity Counter ошибок',
    default_size: 'lg',
    component: 'BitrateWidget',
    category: 'astra',
  },
  {
    id: 'astra-snr-ber',
    module_id: 'astra',
    module_name: 'Astra Broadcast',
    title: 'Сигнал DVB (SNR / BER)',
    description: 'Круговые стрелочные индикаторы уровня сигнала и ошибок на тюнерах',
    default_size: 'md',
    component: 'SignalWidget',
    category: 'telemetry',
  },
  {
    id: 'astra-active-channels',
    module_id: 'astra',
    module_name: 'Astra Broadcast',
    title: 'Активные ТВ-каналы',
    description: 'Мини-таблица текущих потоков с битрейтом и статусами',
    default_size: 'md',
    component: 'ChannelTableWidget',
    category: 'astra',
  },
  {
    id: 'system-live-logs',
    module_id: 'system',
    module_name: 'Система NMS',
    title: 'Живая лента событий',
    description: 'Лог системных сообщений и алертов модулей в реальном времени',
    default_size: 'lg',
    component: 'LogWidget',
    category: 'alerts',
  },
])

// User's active placed widgets layout
const defaultPlacedWidgets: PlacedWidget[] = [
  { instance_id: 'w-1', widget_id: 'astra-bitrate-cc', size: 'lg', x: 0, y: 0 },
  { instance_id: 'w-2', widget_id: 'astra-snr-ber', size: 'md', x: 2, y: 0 },
  { instance_id: 'w-3', widget_id: 'astra-active-channels', size: 'md', x: 0, y: 1 },
  { instance_id: 'w-4', widget_id: 'system-live-logs', size: 'lg', x: 1, y: 1 },
]

const placedWidgets = ref<PlacedWidget[]>(loadSavedWidgets())

function loadSavedWidgets(): PlacedWidget[] {
  try {
    const saved = localStorage.getItem('nms_v2_dashboard_widgets')
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {}
  return [...defaultPlacedWidgets]
}

export function savePlacedWidgets(widgets: PlacedWidget[]) {
  placedWidgets.value = widgets
  try {
    localStorage.setItem('nms_v2_dashboard_widgets', JSON.stringify(widgets))
  } catch (e) {}
}

export function getAvailableWidgets(): WidgetDefinition[] {
  return availableWidgets.value
}

export function getPlacedWidgets() {
  return placedWidgets
}

export function addWidgetToDashboard(widgetId: string) {
  const def = availableWidgets.value.find(w => w.id === widgetId)
  if (!def) return
  const newInstance: PlacedWidget = {
    instance_id: `w-${Date.now()}`,
    widget_id: widgetId,
    size: def.default_size,
    x: 0,
    y: placedWidgets.value.length,
  }
  placedWidgets.value.push(newInstance)
  savePlacedWidgets(placedWidgets.value)
}

export function removeWidgetFromDashboard(instanceId: string) {
  placedWidgets.value = placedWidgets.value.filter(w => w.instance_id !== instanceId)
  savePlacedWidgets(placedWidgets.value)
}
