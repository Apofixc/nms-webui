# 📜 1. Общая информация о манифестах (`manifest.yaml`)

---

## 📌 Назначение и концепция

В платформе **NMS WebUI** каждый модуль описывается стандартизированным Pydantic-манифестом **`manifest.yaml`**, который располагается в корневой директории модуля (`backend/modules/<module_id>/manifest.yaml`).

Манифест является **Single Source of Truth** (единым источником истины) для системы. При запуске приложения Загрузчик плагинов ([loader.py](file:///opt/nms-webui/backend/core/plugin/loader.py)) сканирует директорию плагинов, выполняет строгую валидацию по Pydantic-схеме `ModuleManifest` и выстраивает граф зависимостей.

---

## 🧱 Структура полей `manifest.yaml`

```yaml
# === Основные метаданные ===
id: sensor_monitor                      # Уникальный ID модуля (snake_case)
name: sensorTitle                        # Ключ i18n или текстовое название
version: 1.0.0                           # Версия по стандарту SemVer
description: sensorDesc                 # Описание плагина
enabled_by_default: true                 # Флаг автоматической активации
type: feature                            # Тип: "system" | "feature" | "driver"

# === Требования к версионности ===
min_core_version: "1.0.0"                # Минимальная версия ядра NMS
max_core_version: "2.5.0"                # Максимальная версия ядра NMS

# === Граф зависимостей ===
deps:                                    # Обязательные модули
  - core_network
optional_deps: []                        # Опциональные модули

# === Точки входа Python ===
entrypoints:
  factory: "backend.modules.sensor_monitor:create_module"      # Класс/фабрика BaseModule
  router: "backend.modules.sensor_monitor.api:get_router"       # Возвращает APIRouter
  services: "backend.modules.sensor_monitor.services:init"     # Сервисные службы

# === Интерфейс UI (Vue Router & Menu) ===
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
```
