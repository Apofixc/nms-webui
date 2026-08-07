# 🧩 12. Виджеты, их устройство и API (Widgets API)

---

## 📌 1. Концепция и архитектура виджетов

Виджеты в платформе **nms-webui** — это динамические интерактивные карточки для Дашборда (`/dashboard`), визуализирующие сводные показатели, графики, списки элементов или элементы быстрого управления модулями.

Архитектура виджетов построена на **двухуровневой модели**:

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                     1. Уровень Декларации (Manifest)                        │
 │  Файл: manifest.yaml (секция widgets:)                                       │
 │  Описывает метаданные виджета: ID, компонент, размер, эндпоинт, тайм-аут   │
 └──────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                     2. Уровень Данных (Runtime Data API)                    │
 │  Бэкенд: GET /api/v1/m/<module>/widgets/<name>                              │
 │  Возвращает динамическое состояние в формате WidgetDataResponse (Pydantic)  │
 └─────────────────────────────────────────────────────────────────────────────┘
```

1. **Декларация (Метаданные)**: Описывается в файле `manifest.yaml` модуля в секции `widgets:`. Содержит конфигурацию карточки, системное имя Vue-компонента, габариты и URL эндпоинта данных.
2. **Данные и состояние (Runtime API)**: Предоставляется REST API эндпоинтом бэкенда модуля. Данные возвращаются в стандартизированном формате `WidgetDataResponse`, включающем статусы, метрики, списки и интерактивные действия.

---

## 📋 2. Декларация виджета в манифесте (`WidgetSchema`)

В манифесте модуля `manifest.yaml` виджеты объявляются в виде списка объектов в секции `widgets`. Каждая запись валидируется Pydantic-моделью WidgetSchema.

### Пример объявления виджета в манифесте:

```yaml
widgets:
  - id: "sensor-summary"
    title: "sensorWidgetTitle"
    description: "sensorWidgetDesc"
    component: "SensorWidget"
    endpoint: "/api/v1/m/sensor_monitor/widgets/summary"
    stream_endpoint: "/api/v1/m/sensor_monitor/ws/stream" # Live-поток обновлений (опционально)
    size: "medium"                        # "small" (1x1) | "medium" (2x2) | "large" (4x2)
    refresh_interval: 10                  # Автообновление в секундах (null — без обновления)
    type: "summary"                       # "summary" | "stat" | "list" | "custom"
    default_active: true                  # Добавлять на дашборд по умолчанию
    resizable: true                       # Разрешить пользовательский ресайз
    view_permission: "sensor.view"        # Право на просмотр виджета
    control_permission: "sensor.control"   # Право на управление действиями виджета
```

### Спецификация атрибутов `WidgetSchema`:

| Поле | Тип | Дефолт | Описание |
| :--- | :--- | :--- | :--- |
| `id` | `str` | *обязательно* | Уникальный идентификатор виджета в системе. |
| `title` | `str` | `""` | Ключ локализации `i18n` или отображаемый заголовок. |
| `description` | `str` | `""` | Ключ локализации или краткое описание назначения виджета. |
| `component` | `str` | `""` | Имя Vue-компонента фронтенда (например `SensorWidget` или `TuyaWidget`). |
| `endpoint` | `str \| null` | `None` | HTTP GET URL на бэкенде для получения динамических данных. |
| `stream_endpoint` | `str \| null` | `None` | WebSocket URL для моментального потока обмена данными в реальном времени. |
| `size` | `str` | `"medium"` | Начальный размер виджета в сетке: `"small"` (1x1), `"medium"` (2x2), `"large"` (4x2). |
| `refresh_interval`| `int \| null` | `None` | Интервал автоматического HTTP-поллинга данных (в секундах). |
| `type` | `str` | `"summary"` | Тип визуализации: `"summary"`, `"stat"`, `"list"`, `"custom"`. |
| `default_active` | `bool` | `False` | Если `true`, виджет автоматически помещается на Canvas при первой загрузке. |
| `resizable` | `bool` | `True` | Разрешено ли пользователю изменять размеры карточки виджета на Дашборде. |
| `view_permission` | `str \| null` | `None` | Скоуп прав RBAC, необходимый пользователю для отображения виджета. |
| `control_permission` | `str \| null` | `None` | Скоуп прав RBAC для активации элементов управления в виджете (`canControl`). |

---

## 🐍 3. Backend Widgets API и Pydantic-схемы

Для унификации ответа бэкенд использует стандартизированные Pydantic-модели из модуля backend/core/plugin/widgets.py.

### Перечисления (Enums)

- **`WidgetStatus`**: Семантический статус компонента или метрики.
  - `OK` (`"ok"`) — успешное состояние (зеленый индикатор).
  - `WARNING` (`"warning"`) — предупреждение (оранжевый индикатор).
  - `ERROR` (`"error"`) — ошибка / сбой (красный индикатор).
  - `INFO` (`"info"`) — информационный статус (синий/нейтральный индикатор).
- **`WidgetType`**: Базовый шаблон отображения виджета.
  - `SUMMARY` (`"summary"`) — сводка из нескольких счетчиков/метрик.
  - `STAT` (`"stat"`) — ключевой крупный показатель (число + тренд/единица).
  - `LIST` (`"list"`) — список записей с текстовыми метками и статусами.
  - `CUSTOM` (`"custom"`) — полностью произвольный интерфейс Vue-компонента.

### Структуры данных (Models)

```python
from pydantic import BaseModel, Field
from backend.core.plugin.widgets import WidgetStatus, WidgetType

class WidgetMetric(BaseModel):
    """Отдельная метрика или счетчик виджета."""
    id: str
    label: str
    value: Any
    unit: str | None = None
    status: WidgetStatus = WidgetStatus.INFO
    icon: str | None = None

class WidgetAction(BaseModel):
    """Быстрое действие или ссылка на элемент интерфейса."""
    label: str
    path: str
    icon: str | None = None

class WidgetDataResponse(BaseModel):
    """Единый формат ответа для всех эндпоинтов виджетов."""
    status: WidgetStatus = WidgetStatus.OK
    type: WidgetType = WidgetType.SUMMARY
    title: str | None = None
    metrics: list[WidgetMetric] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[WidgetAction] = Field(default_factory=list)
    updated_at: str = Field(default_factory=...)
    extra: dict[str, Any] = Field(default_factory=dict)
```

### Центральный реестр виджетов ядра

Функция `get_all_widgets()` из backend/core/plugin/registry.py сканирует все включенные модули и формирует единую витрину виджетов, доступную по REST API `GET /api/modules/widgets` (backend/core/plugin/api.py):

```python
@router.get("/modules/widgets")
async def list_widgets(user: User = Depends(get_current_user)):
    """Возвращает список всех зарегистрированных виджетов системы."""
    return {"items": get_all_widgets()}
```

### Пример реализации Backend-обработчика (Модуль Tuya)

Из файла backend/modules/tuya/widgets/__init__.py:

```python
from fastapi import APIRouter
from backend.core.plugin.widgets import (
    WidgetDataResponse, WidgetMetric, WidgetStatus, WidgetType, WidgetAction
)

router = APIRouter()

@router.get("/widgets/summary", response_model=WidgetDataResponse)
async def get_tuya_summary_widget():
    total_devices = 42
    online_devices = 40
    offline_devices = 2

    return WidgetDataResponse(
        status=WidgetStatus.OK,
        type=WidgetType.SUMMARY,
        title="tuyaWidgetTitle",
        metrics=[
            WidgetMetric(id="total", label="Всего устройств", value=total_devices, icon="devices"),
            WidgetMetric(id="online", label="В сети", value=online_devices, status=WidgetStatus.OK, icon="check_circle"),
            WidgetMetric(id="offline", label="Офлайн", value=offline_devices, status=WidgetStatus.WARNING, icon="error"),
        ],
        actions=[
            WidgetAction(label="Перейти к устройствам", path="/tuya/devices", icon="arrow_forward")
        ]
    )
```

---

## 🎨 4. Frontend устройство виджетов и Vue-компоненты

На фронтенде обработка виджетов делится на динамическую авто-регистрацию компонентов, типовой контракт Props/Emits и универсальный рендерер.

### Авто-регистрация компонентов

Модуль frontend/src/modules/loader.ts автоматически находити и регистрирует все файлы виджетов вида `*Widget.vue` через механизм Vite `import.meta.glob`:

```typescript
// Сканирует встроенные виджеты и виджеты из модулей
const widgetModules = import.meta.glob([
  '../widgets/**/*.vue',
  '../modules/**/widgets/**/*.vue'
], { eager: true })
```

### TypeScript контракт (`WidgetProps` и `WidgetEmits`)

Интерфейсы описаны в frontend/src/modules/widgets.ts:

```typescript
import type { WidgetData, WidgetAction, ModuleWidget } from '@/modules/widgets'

// Стандартные Props кастомного Vue-виджета
export interface WidgetProps<T = WidgetData> {
  data: T | null
  loading: boolean
  error: string | null
  canControl?: boolean
  isCustomizing?: boolean
  widget?: ModuleWidget
}

// Стандартные Emits кастомного Vue-виджета
export type WidgetEmits = {
  (e: 'refresh'): void
  (e: 'action', action: WidgetAction): void
}
```

### Универсальный рендерер (`WidgetRenderer.vue`)

Компонент WidgetRenderer.vue выполняет роль контейнера:
1. Запрашивает данные с `widget.endpoint` с помощью `fetchWidgetData()`.
2. Поддерживает поллинг по интервалу `widget.refresh_interval`.
3. Отображает скелетон при `loading` или плашку ошибки при сбое сети/API.
4. Если указан кастомный Vue-компонент в `widget.component`, то инстанцирует его через `<component :is="...">`.
5. Если компонент не задан, отрисовывает дефолтный UI в зависимости от `widget.type` (`summary`, `stat`, `list`).

---

## 🛠 5. Пошаговое руководство по созданию нового виджета

Рассмотрим процесс добавления нового виджета для модуля `device_monitor`.

### Шаг 1: Объявление в `manifest.yaml`

Добавьте секцию `widgets` в `backend/modules/device_monitor/manifest.yaml`:

```yaml
widgets:
  - id: "device-status-widget"
    title: "deviceWidgetTitle"
    description: "deviceWidgetDesc"
    component: "DeviceStatusWidget"
    endpoint: "/api/v1/m/device_monitor/widgets/status"
    size: "medium"
    refresh_interval: 15
    type: "summary"
    default_active: true
```

### Шаг 2: Создание Backend API эндпоинта

В файле `backend/modules/device_monitor/router.py`:

```python
from fastapi import APIRouter
from backend.core.plugin.widgets import WidgetDataResponse, WidgetMetric, WidgetStatus, WidgetType

router = APIRouter(prefix="/api/v1/m/device_monitor", tags=["device_monitor"])

@router.get("/widgets/status", response_model=WidgetDataResponse)
async def get_device_widget_status():
    return WidgetDataResponse(
        status=WidgetStatus.OK,
        type=WidgetType.SUMMARY,
        metrics=[
            WidgetMetric(id="active", label="Активные", value=128, status=WidgetStatus.OK, icon="router"),
            WidgetMetric(id="alerts", label="Тревоги", value=3, status=WidgetStatus.ERROR, icon="warning"),
        ]
    )
```

### Шаг 3: Разработка Vue-компонента виджета

Создайте файл `frontend/src/modules/device_monitor/widgets/DeviceStatusWidget.vue`:

```vue
<template>
  <div class="p-4 flex flex-col justify-between h-full bg-surface-container rounded-xl">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold text-on-surface">{{ widget?.title }}</h3>
      <button @click="$emit('refresh')" class="text-xs text-primary hover:underline">
        Обновить
      </button>
    </div>

    <div v-if="loading" class="text-xs text-outline animate-pulse">Загрузка...</div>

    <div v-else-if="error" class="text-xs text-error">
      {{ error }}
    </div>

    <div v-else-if="data" class="grid grid-cols-2 gap-2 my-2">
      <div 
        v-for="m in data.metrics" 
        :key="m.id"
        class="p-2 rounded bg-surface-container-high flex flex-col"
      >
        <span class="text-[10px] text-outline">{{ m.label }}</span>
        <span class="text-lg font-bold text-on-surface">{{ m.value }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { WidgetProps, WidgetEmits } from '@/modules/widgets'

defineProps<WidgetProps>()
defineEmits<WidgetEmits>()
</script>
```

### Шаг 4: Добавление i18n переводов

Добавьте ключи в файлы локализации модуля (`locales/ru.json` и `locales/en.json`):

```json
{
  "deviceWidgetTitle": "Мониторинг устройств",
  "deviceWidgetDesc": "Текущий статус и счетчики сетевых устройств"
}
```

---

## ⚡ 6. Интерактивные действия (`WidgetAction`) и Безопасность

Виджеты поддерживают выполнение действий с помощью структуры `WidgetAction`.

### Варианты действий:

1. **Навигация (Router path)**:
   При клике происходит переход на внутреннюю страницу фронтенда:
   ```json
   { "label": "Детализация", "path": "/devices/view/101", "icon": "visibility" }
   ```

2. **HTTP Запрос (Endpoint action)**:
   Отправка интерактивного вызова на бэкенд (выполняется через `executeWidgetAction(action)`):
   ```typescript
   export async function executeWidgetAction(action: WidgetAction): Promise<any> {
     const method = (action.method || 'POST').toLowerCase()
     const payload = action.payload || {}
     // Отправка http.get / http.post / http.put / http.delete
   }
   ```

### Ограничение прав доступа (RBAC)

В объявлении манифеста можно указывать скоупы разрешений для просмотра и управления виджетом:

```yaml
widgets:
  - id: "admin-system-control"
    component: "AdminControlWidget"
    view_permission: "system.view"
    control_permission: "system.admin"
```

На фронтенде с помощью флага `canControl` в `WidgetProps` компонент виджета блокирует элементы управления (кнопки, переключатели), если текущий пользователь не имеет прав уровня `control_permission`.

---

## 🧪 7. Тестирование и Best Practices

### Юнит-тестирование backend виджетов

Все виджеты и их эндпоинты покрываются юнит-тестами на pytest. Пример из tests/test_widgets.py:

```python
import pytest
from backend.core.plugin.registry import get_all_widgets
from backend.modules.tuya.widgets import get_tuya_summary_widget

def test_widget_manifest_registration():
    widgets = get_all_widgets()
    widget_ids = [w["id"] for w in widgets]
    assert "system-modules" in widget_ids

@pytest.mark.asyncio
async def test_tuya_summary_widget_structure():
    data = await get_tuya_summary_widget()
    assert data.status == "ok"
    assert len(data.metrics) > 0
```

### Рекомендации разработчикам (Best Practices)

1. **Оптимизация поллинга (`refresh_interval`)**: Не устанавливайте слишком частый интервал обновления (менее 5 секунд), чтобы не перегружать бэкенд и сети.
2. **Обработка отсутствия данных**: Компоненты виджетов всегда должны корректно обрабатывать состояние `data === null` и корректно показывать индикатор загрузки.
3. **Стандартизация ошибок**: Эндпоинты виджетов бэкенда должны возвращать `WidgetDataResponse(status=WidgetStatus.ERROR, extra={"error": "..."})` при внутренних ошибках вместо `500 Internal Server Error`, чтобы Дашборд оставался стабильным.
4. **Использование системных иконок**: Рекомендуется указывать стандартные имена иконок Material Symbols в свойстве `icon`.

---

## 📡 8. Live Streaming & WebSockets (`stream_endpoint`)

Для виджетов, требующих мгновенного обновления показателей в реальном времени (например, нагрузка на ЦП, входящий сетевой трафик, онлайн-тревоги), платформа поддерживает гибридный режим получения данных:

1. **Начальный запрос (Initial Fetch)**: Загружается по HTTP GET через `endpoint` при монтировании виджета.
2. **Потоковые обновления (Live Stream)**: Передаются через WebSocket, указанный в параметре `stream_endpoint`.

### Пример инициализации WebSocket в Vue-виджете:

```typescript
import { ref, onMounted, onUnmounted } from 'vue'
import type { WidgetProps, WidgetData } from '@/modules/widgets'

const props = defineProps<WidgetProps>()
const liveData = ref<WidgetData | null>(props.data)
let socket: WebSocket | null = null

onMounted(() => {
  if (props.widget?.stream_endpoint) {
    const wsUrl = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}${props.widget.stream_endpoint}`
    socket = new WebSocket(wsUrl)
    
    socket.onmessage = (event) => {
      try {
        const delta = JSON.parse(event.data)
        // Обновление локального состояния виджета дельтой данных
        if (liveData.value) {
          Object.assign(liveData.value, delta)
        }
      } catch (err) {
        console.error('Ошибка разбора WebSocket пакета виджета:', err)
      }
    }
  }
})

onUnmounted(() => {
  if (socket) {
    socket.close()
  }
})
```

---

## 📐 9. Позиционирование, размеры и сетка (Dashboard Layout)

Все виджеты размещаются в адаптивной сетке (Canvas Grid) страницы Дашборда. 

### Градация начальных размеров (`size`):

- **`small` (1x1)**: Компактный плашка-индикатор статуса или одиночный счетчик.
- **`medium` (2x2)**: Стандартный размер виджета со сводкой из 2–4 метрик или кратким списком.
- **`large` (4x2 или 4x3)**: Полноразмерный виджет с таблицей, журналом событий или динамическим графиком.

### Атрибуты управления поведением карточки:

- `default_active`: При значении `true` виджет появляется на холсте пользователя по умолчанию при первом входе.
- `resizable`: Флаг, разрешающий пользователю растягивать или сжимать карточку виджета с помощью интерактивных маркеров изменения размера.
- **Сохранение раскладки (Persistence)**: Позиция (x, y) и текущие габариты (w, h) каждого виджета автоматически сохраняются в пользовательском профиле дашборда на бэкенде.

---

## 📊 10. Визуализация графиков и временных рядов (`extra.chart`)

Для передачи временных рядов (time-series), мини-графиков (sparklines) или распределений используйте поле `extra` в объекте `WidgetDataResponse`.

### Пример формата ответа бэкенда с временным рядом:

```python
@router.get("/widgets/network_traffic", response_model=WidgetDataResponse)
async def get_network_traffic_widget():
    return WidgetDataResponse(
        status=WidgetStatus.OK,
        type=WidgetType.CUSTOM,
        title="Трафик интерфейсов",
        metrics=[
            WidgetMetric(id="rx", label="Входящий", value="1.2 Gbps", status=WidgetStatus.OK),
            WidgetMetric(id="tx", label="Исходящий", value="450 Mbps", status=WidgetStatus.OK)
        ],
        extra={
            "chart_type": "sparkline",
            "timestamps": ["10:00", "10:05", "10:10", "10:15", "10:20"],
            "series": [
                {"name": "RX", "data": [800, 950, 1100, 1050, 1200]},
                {"name": "TX", "data": [300, 400, 380, 420, 450]}
            ]
        }
    )
```

В Vue-компоненте `extra.series` можно легко визуализировать с помощью системных библиотек графиков или встроенных SVG sparkline-элементов.

---

## 🎨 11. Дизайн-система, токены и поддержка Dark/Light тем

Для того чтобы виджет гармонично вписывался в интерфейс **nms-webui** и корректно переключался между светлой и темной темами оформления, строго придерживайтесь правил дизайн-системы:

### Системные CSS-классы и токены:

| Семантический элемент | Рекомендуемые CSS-классы Tailwind / CSS Tokens |
| :--- | :--- |
| **Фон карточки виджета** | `bg-surface-container` или `bg-surface` |
| **Фон внутренних блоков** | `bg-surface-container-high` или `bg-surface-variant` |
| **Основной текст** | `text-on-surface` |
| **Второстепенный текст/метки** | `text-outline` или `text-on-surface-variant` |
| **Акцентные элементы/ссылки** | `text-primary` |
| **Статус Успех (`OK`)** | `text-success` / `bg-success-container` |
| **Статус Предупреждение (`WARNING`)** | `text-warning` / `bg-warning-container` |
| **Статус Ошибка (`ERROR`)** | `text-error` / `bg-error-container` |

> [!TIP]
> Избегайте использования жестко запрограммированных (hardcoded) HEX-цветов (например `#ffffff` или `#121212`). Всегда используйте переменные темы для полной совместимости с динамическим переключателем тем.

