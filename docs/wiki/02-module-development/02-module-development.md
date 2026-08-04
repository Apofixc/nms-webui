# 🏗 Руководство по созданию модулей (Backend + Frontend)

---

## 📦 Спецификация Pydantic-манифеста `manifest.yaml`

Каждый динамический модуль NMS WebUI должен содержать файл `manifest.yaml` в своем корневом каталоге. Этот файл описывает метаданные плагина, зависимости, точки входа, права доступа, виджеты и схему настроек.

```yaml
id: sensor_monitor                      # Уникальный ID модуля (a-z, 0-9, _)
name: sensorTitle                        # Ключ i18n или название модуля
version: 1.0.0                           # Версия модуля (SemVer)
description: sensorDesc                 # Описание модуля
enabled_by_default: true                 # Включен ли по умолчанию
type: feature                            # Тип: "system" | "feature" | "driver"

# Совместимость с версиями ядра NMS
min_core_version: "1.0.0"
max_core_version: "2.0.0"

# Зависимости от других модулей
deps: []                                 # Обязательные модули
optional_deps: []                        # Опциональные модули

# Точки входа Python
entrypoints:
  factory: "backend.modules.sensor_monitor:create_module"
  router: "backend.modules.sensor_monitor.api:get_router"
  services: "backend.modules.sensor_monitor.services:init_service"

# Спецификация UI роутов
routes:
  - path: "/sensor-monitor"
    name: "sensor-monitor-index"
    meta:
      title: "Датчики и Телеметрия"
      icon: "sensors"
      group: "monitoringGroup"
      requires_auth: true

# Элементы меню
menu:
  location: sidebar                      # "sidebar" | "footer" | null
  group: "monitoringGroup"
  items:
    - path: "/sensor-monitor"
      label: "sensorTitle"
      icon: "sensors"

# Динамическая схема настроек (JSON Schema)
config_schema:
  type: object
  properties:
    poll_interval:
      type: integer
      default: 10
      minimum: 1
      maximum: 300
      title: "Интервал опроса (сек)"
    sensor_ip:
      type: string
      default: "192.168.1.50"
      title: "IP адрес контроллера"

# Разрешения RBAC
permissions:
  - id: "module.sensor_monitor.view"
    name: "Просмотр датчиков"
    category: "Sensors"
    description: "Право на просмотр телеметрии"
  - id: "module.sensor_monitor.control"
    name: "Управление датчиками"
    category: "Sensors"
    description: "Право на сброс и калибровку"

# Виджеты для Дашборда
widgets:
  - id: "sensor-summary"
    title: "sensorWidgetTitle"
    description: "Сводный статус сенсоров"
    endpoint: "/api/v1/m/sensor_monitor/widgets/summary"
    stream_endpoint: "/api/v1/m/sensor_monitor/widgets/summary/stream"
    component: "SensorWidget"
    size: "medium"
    refresh_interval: 5
    resizable: true

# Жизненные хуки и скрипты
hooks:
  install: "scripts/install.sh"
  uninstall: "scripts/uninstall.sh"
  on_enable: "backend.modules.sensor_monitor:on_enable_hook"
  on_disable: "backend.modules.sensor_monitor:on_disable_hook"
```

---

## 🛠 Пошаговое руководство по созданию модуля `sensor_monitor`

### Шаг 1: Создание структуры директорий

Выполните команду в терминале:

```bash
mkdir -p backend/modules/sensor_monitor/scripts
mkdir -p backend/modules/sensor_monitor/locales
mkdir -p frontend/src/modules/sensor_monitor/widgets
```

---

### Шаг 2: Создание Манифеста (`manifest.yaml`)

Создайте файл `backend/modules/sensor_monitor/manifest.yaml` с содержимым, приведенным в спецификации выше.

---

### Шаг 3: Написание класса Модуля (`module.py`)

Создайте файл `backend/modules/sensor_monitor/module.py`:

```python
import logging
from backend.core.plugin.context import ModuleContext
from backend.core.log_providers import LocalFileLogProvider

_log = logging.getLogger("nms.module.sensor_monitor")

class SensorMonitorModule:
    """Главный класс динамического модуля."""

    def __init__(self, ctx: ModuleContext):
        self.ctx = ctx
        self.is_running = False

    def init(self):
        """Вызывается единоразово при первичной загрузке модуля."""
        _log.info("SensorMonitorModule initialized for %s", self.ctx.module_id)

    def start(self):
        """Вызывается при запуске сервиса или включении модуля."""
        self.is_running = True
        _log.info("SensorMonitorModule background polling started")

    def stop(self):
        """Вызывается при остановке или выключении модуля."""
        self.is_running = False
        _log.info("SensorMonitorModule stopped")

    def get_log_provider(self):
        """Регистрация пользовательского провайдера логов модуля (опционально)."""
        log_file = self.ctx.get_data_dir() / "sensor_events.log"
        return LocalFileLogProvider(
            provider_id=f"module.{self.ctx.module_id}",
            name="Логи Модуля Датчиков",
            file_path=log_file,
            category="module"
        )


def create_module(ctx: ModuleContext) -> SensorMonitorModule:
    """Точка входа factory."""
    return SensorMonitorModule(ctx)
```

---

### Шаг 4: Написание REST API Роутера (`api.py`)

Создайте файл `backend/modules/sensor_monitor/api.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from backend.core.auth import require_module_permission, CurrentUser
from backend.core.plugin.context import ModuleContext

def get_router(ctx: ModuleContext) -> APIRouter:
    router = APIRouter(prefix="/api/v1/m/sensor_monitor", tags=["Sensor Monitor Module"])

    @router.get("/status")
    async def get_status(user: CurrentUser = Depends(require_module_permission("sensor_monitor", "view"))):
        return {
            "status": "ok",
            "temperature": 23.5,
            "humidity": 45,
            "module_id": ctx.module_id
        }

    @router.get("/widgets/summary")
    async def get_widget_summary(user: CurrentUser = Depends(require_module_permission("sensor_monitor", "view"))):
        return {
            "status": "ok",
            "type": "summary",
            "title": "Статус Сенсоров",
            "metrics": [
                {"id": "temp", "label": "Температура", "value": "23.5", "unit": "°C", "status": "ok", "icon": "thermostat"},
                {"id": "hum", "label": "Влажность", "value": "45", "unit": "%", "status": "ok", "icon": "water_drop"}
            ],
            "actions": [
                {"label": "Сброс", "endpoint": "/api/v1/m/sensor_monitor/reset", "method": "POST", "confirm": "Вы уверены?"}
            ]
        }

    @router.post("/reset")
    async def reset_sensors(user: CurrentUser = Depends(require_module_permission("sensor_monitor", "control"))):
        return {"status": "success", "message": "Датчики успешно перезапущены"}

    return router
```

---

### Шаг 5: Скрипты установки (`scripts/install.sh`)

Создайте файл `backend/modules/sensor_monitor/scripts/install.sh`:

```bash
#!/bin/bash
# Автоматический скрипт установки модуля
echo "[INFO] Установка модуля $MODULE_ID..."
mkdir -p "$MODULE_DATA_DIR"
echo "[INFO] Каталог данных $MODULE_DATA_DIR подготовлен."
exit 0
```

Сделайте его исполняемым: `chmod +x backend/modules/sensor_monitor/scripts/install.sh`.

---

### Шаг 6: Фронтенд-виджет (`SensorWidget.vue`)

Создайте файл `frontend/src/modules/sensor_monitor/widgets/SensorWidget.vue`:

```vue
<template>
  <div class="sensor-widget space-y-2 p-2">
    <div class="flex items-center justify-between text-xs">
      <span class="text-on-surface-variant font-medium">Статус подключения:</span>
      <span class="px-2 py-0.5 rounded bg-tertiary/15 text-tertiary font-bold text-[10px]">ОК</span>
    </div>
    <div v-if="data" class="grid grid-cols-2 gap-2">
      <div v-for="m in data.metrics" :key="m.id" class="p-2 rounded bg-surface-container-high border border-outline-variant/40">
        <div class="text-[10px] text-on-surface-variant">{{ m.label }}</div>
        <div class="text-sm font-bold text-on-surface font-mono">{{ m.value }} {{ m.unit }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { WidgetProps } from '@/modules/widgets'

defineProps<WidgetProps>()
</script>
```

Зарегистрируйте виджет в `frontend/src/modules/registry.ts`:

```typescript
import { registerWidgetComponent } from '@/modules/registry'

registerWidgetComponent('SensorWidget', () => import('@/modules/sensor_monitor/widgets/SensorWidget.vue'))
```

---

### Шаг 7: Файлы локализации (`locales/ru.json`)

Создайте `backend/modules/sensor_monitor/locales/ru.json`:

```json
{
  "sensorTitle": "Мониторинг Датчиков",
  "sensorDesc": "Модуль контроля климатических параметров серверной",
  "sensorWidgetTitle": "Климат Серверной"
}
```

Модуль готов! Перезапустите бэкенд или нажмите «Сканировать модули» в меню администрирования.
