# 🧩 Полное руководство по системе виджетов NMS-WebUI

Виджеты NMS-WebUI позволяют модулям и встроенным сервисам системы транслировать оперативную информацию, сводные метрики и интерактивные элементы управления напрямую на главный холст (Canvas) рабочего стола.

Архитектура виджетов построена по принципу **Zero-Configuration (нулевой ручной настройки)**: как только файл виджета создается в специализированной папке `widgets` и объявляется в манифесте, система автоматически подхватывает бэкенд API, монтирует Vue-компонент, подгружает локализации, проверяет права доступа и добавляет виджет в интерактивный каталог.

---

## 📁 1. Файловая структура и размещение

Все компоненты виджетов хранятся строго в специализированных папках `widgets`:

```text
/opt/nms-webui/
├── backend/
│   └── modules/
│       └── <module_id>/
│           ├── manifest.yaml          # ⚠️ Декларация виджета (widgets:)
│           ├── api.py                 # REST API эндпоинты виджета (/widgets/summary)
│           ├── locales/               # 🌍 Переводы заголовков и метрик виджета
│           │   ├── ru.json
│           │   └── en.json
│           └── widgets/               # (Опционально) Бэкенд-логика виджета
│
└── frontend/
    └── src/
        ├── widgets/                   # 🏠 Виджеты базового приложения (ядра)
        │   └── SystemStatusWidget.vue
        │
        └── modules/
            └── <module_id>/
                └── widgets/           # 📦 Виджеты динамических модулей
                    └── TuyaWidget.vue
```

Загрузчик [loader.ts](file:///opt/nms-webui/frontend/src/modules/loader.ts) сканирует виджеты с помощью точечных шаблонов Vite `import.meta.glob`:
- `'../widgets/**/*.vue'` — базовые виджеты приложения
- `'../modules/**/widgets/**/*.vue'` — виджеты динамических модулей

---

## 📜 2. Декларация виджета в манифесте (`manifest.yaml`)

Виджеты динамических модулей объявляются в секции `widgets:` файла `manifest.yaml`:

```yaml
widgets:
  - id: "tuya-summary"                          # Уникальный ID виджета (kebab-case)
    title: "tuyaWidgetTitle"                    # Ключ локализации или читаемое название
    description: "tuyaWidgetDesc"              # Ключ описания для каталога виджетов
    endpoint: "/api/v1/m/tuya/widgets/summary"  # REST API эндпоинт данных виджета
    stream_endpoint: ""                        # (Опционально) WebSocket / SSE эндпоинт
    component: "TuyaWidget"                    # (Опционально) Имя Vue-компонента в папке widgets/
    size: "medium"                             # Начальный размер: small | medium | large
    refresh_interval: 15                       # Период автообновления данных (в секундах)
    type: "summary"                            # Тип: summary | stat | list | custom
    view_permission: "module.tuya.view"        # Право на просмотр виджета
    control_permission: "module.tuya.control"  # Право на выполнение управляющих действий
    default_active: true                       # Отображать ли на дашборде по умолчанию
```

### Спецификация полей манифеста:

| Поле | Тип | Обязательное | Описание |
| :--- | :--- | :---: | :--- |
| `id` | `string` | **Да** | Уникальный идентификатор виджета в системе. |
| `title` | `string` | **Да** | Заголовок виджета или ключ локализации. |
| `description` | `string` | Нет | Краткое описание назначения виджета для каталога. |
| `endpoint` | `string` | **Да** | HTTP REST эндпоинт бэкенда, возвращающий `WidgetData`. |
| `stream_endpoint`| `string` | Нет | URL для живых подписок через WebSocket или SSE. |
| `component` | `string` | Нет | Имя Vue-файла из папки `widgets/`. Если не указано, используется **Zero-Code** шаблон. |
| `size` | `string` | Нет | Начальный размер карточки: `small` (260x160), `medium` (360x240), `large` (480x320). |
| `refresh_interval`| `number`| Нет | Интервал автообновления данных в секундах (по умолчанию `15`). |
| `view_permission` | `string`| Нет | Разрешение RBAC для просмотра (по умолчанию `module.<id>.view`). |
| `control_permission`| `string`| Нет | Разрешение RBAC для управления (по умолчанию `module.<id>.control`). |
| `default_active`| `boolean`| Нет | Авто-добавление на холст при первой установке (по умолчанию `false`). |

---

## 🐍 3. Бэкенд-реализация (Python & FastAPI)

Бэкенд должен предоставить HTTP GET эндпоинт, возвращающий данные в формате `WidgetData`.

### 3.1. Полная JSON-схема ответа `WidgetData`:
```json
{
  "status": "ok",
  "title": "tuyaWidgetTitle",
  "updated_at": "2026-08-03T18:00:00Z",
  "metrics": [
    {
      "id": "online_devices",
      "label": "tuyaOnline",
      "value": 12,
      "unit": "шт",
      "status": "ok",
      "icon": "power"
    },
    {
      "id": "offline_devices",
      "label": "tuyaOffline",
      "value": 2,
      "unit": "шт",
      "status": "warning",
      "icon": "power_off"
    }
  ],
  "items": [
    { "id": "dev-1", "name": "Умная розетка #1", "value": "220V" }
  ],
  "actions": [
    {
      "label": "tuyaRestartAction",
      "action_id": "restart_hub",
      "endpoint": "/api/v1/m/tuya/control/restart",
      "method": "POST",
      "payload": { "force": true },
      "confirm": "tuyaConfirmRestart",
      "icon": "restart_alt"
    },
    {
      "label": "tuyaOpenList",
      "path": "/tuya",
      "icon": "arrow_forward"
    }
  ],
  "extra": {
    "total": 14,
    "firmware": "v2.1.0"
  }
}
```

### 3.2. Пример кода FastAPI в `backend/modules/tuya/api.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from backend.core.auth import CurrentUser, require_permission

router = APIRouter(prefix="/api/v1/m/tuya", tags=["tuya-widgets"])

# 1. Эндпоинт чтения данных виджета (требуется право на просмотр)
@router.get("/widgets/summary")
async def get_tuya_widget_summary(
    user: CurrentUser = Depends(require_permission("module.tuya.view"))
):
    return {
        "status": "ok",
        "title": "tuyaWidgetTitle",
        "metrics": [
            {"id": "online", "label": "tuyaOnline", "value": 12, "unit": "шт", "status": "ok", "icon": "check_circle"},
            {"id": "offline", "label": "tuyaOffline", "value": 2, "unit": "шт", "status": "warning", "icon": "error"}
        ],
        "actions": [
            {
                "label": "tuyaRestartAction",
                "endpoint": "/api/v1/m/tuya/control/restart",
                "method": "POST",
                "confirm": "tuyaConfirmRestart"
            }
        ],
        "extra": {"total": 14, "online": 12, "offline": 2}
    }

# 2. Интерактивный эндпоинт управления (требуется право на управление)
@router.post("/control/restart")
async def restart_tuya_hub(
    user: CurrentUser = Depends(require_permission("module.tuya.control"))
):
    # Бизнес-логика перезапуска устройства / сервиса
    return {"success": True, "message": "IoT Hub restarted", "executed_by": user.username}
```

---

## 💻 4. Фронтенд-разработка виджетов

Фронтенд поддерживает два варианта отображения:

### Вариант А: Zero-Code (Стандартное отображение)
Если кастомный `.vue` файл не создаётся, контейнер [WidgetRenderer.vue](file:///opt/nms-webui/frontend/src/components/common/WidgetRenderer.vue) автоматически отрисует:
- Сетку метрик с цветовой индикацией статусов (`ok` — зеленый, `warning` — янтарный, `error` — красный).
- Список элементов `items`.
- Нижнюю панель действий с кнопками переходов или отправки POST/PUT команд.

---

### Вариант Б: Кастомный Vue 3 виджет

Кастомный виджет создается в файле `src/modules/<module_id>/widgets/<WidgetName>.vue` и использует стандартные контракты типизации из `@/modules/widgets`:

#### Использование `WidgetProps<T>` и `WidgetEmits`:

```html
<template>
  <div class="h-full flex flex-col justify-between space-y-2">
    <!-- Шапка виджета -->
    <div class="flex items-center justify-between p-2 rounded-lg bg-surface-container-high border border-outline-variant/40">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-primary text-sm">hub</span>
        <span class="text-xs font-semibold text-on-surface">{{ t('tuyaWidgetTitle') }}</span>
      </div>
      <span class="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-mono text-[10px] font-bold">
        Всего: {{ totalDevices }}
      </span>
    </div>

    <!-- Метрики -->
    <div class="grid grid-cols-2 gap-2 flex-1">
      <div class="p-2 rounded-lg bg-tertiary/10 border border-tertiary/30 flex flex-col justify-between">
        <span class="text-[10px] text-tertiary font-medium">{{ t('tuyaOnline') }}</span>
        <div class="font-bold text-lg text-tertiary font-mono">{{ onlineDevices }}</div>
      </div>
      <div class="p-2 rounded-lg bg-warning/10 border border-warning/30 flex flex-col justify-between">
        <span class="text-[10px] text-warning font-medium">{{ t('tuyaOffline') }}</span>
        <div class="font-bold text-lg text-warning font-mono">{{ offlineDevices }}</div>
      </div>
    </div>

    <!-- Интерактивное действие с проверкой прав canControl -->
    <div class="pt-1 flex items-center justify-between">
      <button
        @click="handleRestart"
        :disabled="!canControl || isExecuting"
        class="px-2.5 py-1 rounded text-xs font-semibold bg-primary text-on-primary hover:opacity-90 disabled:opacity-40 transition-opacity flex items-center gap-1 cursor-pointer"
        :title="!canControl ? t('widgetNoControlPermission') : ''"
      >
        <span v-if="isExecuting" class="material-symbols-outlined text-xs animate-spin">progress_activity</span>
        <span v-else class="material-symbols-outlined text-xs">restart_alt</span>
        <span>{{ t('tuyaRestartAction') }}</span>
      </button>

      <button
        @click="$emit('refresh')"
        :disabled="loading"
        class="p-1 rounded text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
      >
        <span class="material-symbols-outlined text-xs" :class="{ 'animate-spin': loading }">refresh</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from '@/core/i18n'
import { type WidgetProps, type WidgetEmits, executeWidgetAction } from '@/modules/widgets'

// 1. Принятие стандартных типов Props и Emits
const props = defineProps<WidgetProps>()
const emit = defineEmits<WidgetEmits>()

const { t } = useI18n()
const isExecuting = ref(false)

// 2. Извлечение данных из extra или metrics
const totalDevices = computed(() => props.data?.extra?.total ?? 0)
const onlineDevices = computed(() => props.data?.extra?.online ?? 0)
const offlineDevices = computed(() => props.data?.extra?.offline ?? 0)

// 3. Выполнение управляющего действия
async function handleRestart() {
  if (!props.canControl) return
  if (!confirm(t('tuyaConfirmRestart'))) return

  isExecuting.value = true
  try {
    await executeWidgetAction({
      endpoint: '/api/v1/m/tuya/control/restart',
      method: 'POST',
      payload: { force: true }
    })
    // Принудительно обновить данные виджета после выполнения действия
    emit('refresh')
  } catch (err) {
    console.error('Action failed:', err)
  } finally {
    isExecuting.value = false
  }
}
</script>
```

---

## 🌍 5. Локализация виджета (i18n)

Все тексты виджета (заголовки, названия метрик, кнопки действий и сообщения) автоматически переподключаются фронтендом.

Файлы локализаций помещаются в папку модуля:
- `backend/modules/<module_id>/locales/ru.json`
- `backend/modules/<module_id>/locales/en.json`

Пример `backend/modules/tuya/locales/ru.json`:
```json
{
  "messages": {
    "tuyaWidgetTitle": "Сводка устройств Tuya",
    "tuyaWidgetDesc": "Статистика подключенных устройств и управление IoT-хабом",
    "tuyaOnline": "В сети",
    "tuyaOffline": "Не в сети",
    "tuyaRestartAction": "Перезапустить хаб",
    "tuyaConfirmRestart": "Вы действительно хотите перезапустить IoT-хаб?"
  }
}
```

Фронтенд автоматический подгружает локализации при инициализации модуля, поэтому вызов `t('tuyaWidgetTitle')` вернет правильный переведенный текст.

---

## 🔐 6. Двухуровневая система прав доступа (RBAC)

Каждый виджет автоматически проверяет права текущего пользователя через модуль `@/core/auth`:

1. **Право на просмотр (`view_permission`)**:
   - Проверяется перед отправкой HTTP-запроса данных.
   - При отсутствии прав виджет **не совершает вызовы API**.
   - Вместо содержимого отрисовывается защищенная карточка с иконкой замка 🔒 и текстом **«Доступ ограничен: У вас недостаточно прав для просмотра этого виджета»**.

2. **Право на управление (`control_permission`)**:
   - Передается в кастомный виджет через `props.canControl` (`boolean`).
   - Если пользователь имеет право на просмотр, но не имеет права на управление, виджет отображает данные, но все кнопки действий переходят в состояние `disabled` с подсказкой **«Недостаточно прав для управления»**.

---

## ⚡ 7. Интерактивные действия и WebSocket / SSE

### 7.1. Управляющие экшены (`actions`)
Массив `actions` поддерживает выполнение гибких команд:
- `endpoint`: URL приема команды.
- `method`: HTTP метод (`POST`, `PUT`, `DELETE`, `GET`).
- `payload`: Объект передаваемых параметров.
- `confirm`: Ключ или текст окна подтверждения перед отправкой.

### 7.2. Живые обновления (WebSocket / SSE)
Если в манифесте или ответах бэкенда указан `stream_endpoint`, контейнер [WidgetRenderer.vue](file:///opt/nms-webui/frontend/src/components/common/WidgetRenderer.vue) подписывается на WebSocket/SSE поток. При получении новых данных `data.value` обновляется в реальном времени, а опрос по таймеру `refresh_interval` автоматически отключается.

---

## 🎨 8. Физика холста и Режимы коллизий (Canvas & Layout)

Пользователи могут свободно настраивать рабочий стол в режиме **«Настроить рабочий стол»**:

### 8.1. 3 Режима предотвращения коллизий (`collisionMode`)
1. **Направленный сдвиг (`push`)**:
   - При перемещении карточки справа налево пересекаемый виджет автоматически выталкивается влево (и аналогично по вектору движения вверх/вниз/вправо).
2. **Запрет с рамкой (`block`)**:
   - При наведении виджета на уже занятую позицию подсвечивается **красная пунктирная область коллизии** с надписью **«Занято»**, а сбрасывание блокируется.
3. **Свободно (`off`)**:
   - Отключение контроля перекрытий (свободное наложение).

### 8.2. Каталог, поиск и скрытие
- **Каталог виджетов**: Открывается по кнопке «+ Добавить виджет», содержит встроенную поисковую строку по названиям, описаниям и идентификаторам модулей.
- **Скрытие/Показ**: Скрытые виджеты не потребляют память и сетевые запросы в обычном режиме, но остаются доступными для восстановления на панели кастомизации.
- **Персистентность**: Все настройки дашборда сохраняются в `localStorage` по ключу `nms_widget_canvas_v3`.

---

## 🛡️ 9. Обработка ошибок (Error Boundary)

Контейнер [WidgetRenderer.vue](file:///opt/nms-webui/frontend/src/components/common/WidgetRenderer.vue) защищен от сбоев:
- **Ошибка сетевого API**: Отрисовывает блок с предупреждением и кнопкой повтора «Обновить».
- **Ошибка компонентов (Error Boundary)**: Если `.vue` файл виджета содержит ошибку сборки или отвалился при динамическом импорте, выводится аккуратный блок **«Ошибка загрузки интерфейса виджета»**, предотвращая падение всего приложения.

---

## 📋 10. Чек-лист создания виджета с нуля

1. [ ] **Манифест**: Добавить блок `widgets:` в `backend/modules/<module_id>/manifest.yaml`.
2. [ ] **Бэкенд API**: Создать эндпоинт `GET /api/v1/m/<module_id>/widgets/summary` в `api.py` с декоратором `@require_permission`.
3. [ ] **Локализации**: Добавить ключи заголовков и метрик в `locales/ru.json` и `locales/en.json`.
4. [ ] **Фронтенд Component**: Создать `frontend/src/modules/<module_id>/widgets/<WidgetName>.vue`.
5. [ ] **Типизация**: Подключить `defineProps<WidgetProps>()` и `defineEmits<WidgetEmits>()`.
6. [ ] **Проверка**: Выполнить `npx vue-tsc --noEmit` и открыть Главный Дашборд!
