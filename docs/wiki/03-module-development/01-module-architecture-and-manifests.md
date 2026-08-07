# 🧩 01. Архитектура модулей и манифесты (`manifest.yaml`)

---

## 📌 Архитектура динамических модулей

В платформе **NMS WebUI** каждый плагин размещается в отдельной папе директории `backend/modules/<module_id>/`.

Единым источником истины (Single Source of Truth) для каждого модуля служит файл **`manifest.yaml`**. Он описывает все метаданные плагина, зависимости, точки входа на Python, UI-маршруты, элементы меню, права доступа, виджеты и схему настроек.

---

## 🧱 Pydantic-схема манифеста (`ModuleManifest`)

Манифесты валидируются при старте приложения через класс `ModuleManifest` ([backend/core/plugin/manifest.py](file:///opt/nms-webui/backend/core/plugin/manifest.py)).

### Пример полного `manifest.yaml`:

```yaml
id: sensor_monitor                      # Уникальный ID модуля (snake_case)
name: sensorTitle                        # Ключ локализации i18n или название
version: 1.0.0                           # Версия по SemVer
description: sensorDesc                 # Описание назначения
enabled_by_default: true                 # Активировать ли по умолчанию
type: feature                            # Тип: "system" | "feature" | "driver"

min_core_version: "1.0.0"                # Совместимость с версиями ядра
max_core_version: "2.5.0"

deps: []                                 # Обязательные модули-зависимости
optional_deps: []                        # Опциональные модули

entrypoints:
  factory: "backend.modules.sensor_monitor:create_module" # Фабрика BaseModule
  router: "backend.modules.sensor_monitor.api:get_router"  # Роутер FastAPI

routes:
  - path: "/sensor-monitor"
    name: "sensor-monitor-index"
    meta:
      title: "Датчики"
      icon: "sensors"
      requires_auth: true
      permissions: ["module.sensor_monitor.view"]

menu:
  location: sidebar                      # "sidebar" | "footer" | null
  group: "monitoringGroup"
  items:
    - path: "/sensor-monitor"
      label: "sensorTitle"
      icon: "sensors"

permissions:
  - id: "module.sensor_monitor.view"
    name: "Просмотр датчиков"
    category: "Sensors"
  - id: "module.sensor_monitor.control"
    name: "Управление датчиками"
    category: "Sensors"

widgets:
  - id: "sensor-summary"
    title: "sensorWidgetTitle"
    endpoint: "/api/v1/m/sensor_monitor/widgets/summary"
    component: "SensorWidget"
    size: "medium"                        # "small" | "medium" | "large"
    refresh_interval: 5
```
