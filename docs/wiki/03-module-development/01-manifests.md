# 📜 1. Общая информация о манифестах (`manifest.yaml`)

---

## 📌 Назначение, Архитектура и Жизненный цикл

В платформе **NMS WebUI** каждый модуль и субмодуль описываются стандартизированным YAML-файлом **`manifest.yaml`**. 

Манифест является **Single Source of Truth** (единым источником истины) для системы: он определяет идентификатор модуля, точки входа Python-кода, UI-маршруты, навигационное меню, зависимости, права доступа, виджеты дашборда и схему пользовательских настроек.

### Местоположение в проекте
- **Основной модуль**: `backend/modules/<module_id>/manifest.yaml`
- **Субмодуль (дочерний модуль)**: `backend/modules/<parent_id>/submodules/<sub_id>/manifest.yaml`

### Жизненный цикл загрузки манифеста
При старте сервера Загрузчик плагинов (`loader.py`) выполняет следующий цикл обработки:
1. **Discovery (Сканирование)**: Рекурсивно находит все файлы `manifest.yaml` в директории `backend/modules/` (функция `discover_manifests`).
2. **YAML Parsing & Pydantic Validation**: Парсит YAML и валидирует данные строго по Pydantic-модели `ModuleManifest` в функции `_parse_manifest`.
3. **Нормализация**: 
   - Для субмодулей автоматически формирует префикс `id` (`parent_id.sub_id`) и добавляет родителя в списки зависимостей `deps`.
   - Приводит одиночные строки в `entrypoints.router` и `entrypoints.services` к списку строк `list[str]`.
4. **Topological Sorting (Топологическая сортировка)**: Строит граф зависимостей через `toposort_modules` с учетом обязательных (`deps`) и опциональных (`optional_deps`) зависимостей.
5. **Registration & Permissions Sync**: Регистрирует модуль в реестре `registry.py` и автоматически синхронизирует объявленные права доступа с базой данных SQLite (`sync_module_permissions`).

---

## 🧱 Исчерпывающий шаблон `manifest.yaml`

Ниже представлен полный эталонный пример `manifest.yaml`, содержащий все возможные секции и поля платформы:

```yaml
# === Основные метаданные ===
id: sensor_monitor                      # Уникальный ID модуля (snake_case)
name: sensorTitle                        # Название или ключ i18n
version: 1.2.0                           # Версия модуля по SemVer
description: sensorDesc                 # Описание возможностей модуля
enabled_by_default: true                 # Флаг автоматической активации
type: feature                            # Тип: "system" | "feature" | "driver"

# === Версионность ядра ===
min_core_version: "1.0.0"                # Минимально требуемая версия ядра NMS
max_core_version: "2.5.0"                # Максимально поддерживаемая версия ядра NMS

# === Зависимости и субмодули ===
deps:                                    # Обязательные модули-предшественники
  - core_network
optional_deps:                           # Опциональные модули
  - notifications
parent: null                             # ID родительского модуля (если это субмодуль)

# === Точки входа Python ===
entrypoints:
  factory: "backend.modules.sensor_monitor:create_module"      # Класс/фабрика модуля (BaseModule)
  router:                                                       # Роутер FastAPI (строка или список строк)
    - "backend.modules.sensor_monitor.api:router"
    - "backend.modules.sensor_monitor.api_v2:router"
  services:                                                     # Фоновые службы
    - "backend.modules.sensor_monitor.services:init_collector"
  settings: "backend.modules.sensor_monitor.settings:register"  # Управление настройками

# === UI Маршруты (Vue Router) ===
routes:
  - path: "/sensor-monitor"
    name: "sensor-monitor-index"
    meta:
      title: "Мониторинг датчиков"
      icon: "sensors"
      group: "monitoringGroup"
      requires_auth: true
      permissions:
        - "module.sensor_monitor.view"
      settings_view: false
      module_id: "sensor_monitor"

# === Навигационное меню (Sidebar & Footer) ===
menu:
  location: sidebar                      # "sidebar" | "footer" | null
  group: "monitoringGroup"
  items:
    - path: "/sensor-monitor"
      label: "sensorTitle"
      icon: "sensors"

# === Права доступа (RBAC Permissions) ===
permissions:
  - id: "module.sensor_monitor.view"
    name: "Просмотр показаний датчиков"
    category: "Мониторинг"
    description: "Разрешает доступ к просмотру графиков и метрик датчиков"
  - id: "module.sensor_monitor.control"
    name: "Управление датчиками"
    category: "Мониторинг"
    description: "Разрешает перезапуск и калибровку датчиков"

# === Виджеты Главного Экрана (Dashboard) ===
widgets:
  - id: "sensor-summary-widget"
    title: "Статус датчиков"
    description: "Сводный виджет количества активных и авариных датчиков"
    component: "SensorSummaryWidget"     # Имя Vue-компонента
    endpoint: "/api/sensor-monitor/widget/summary"
    size: "medium"                        # "small" | "medium" | "large" | "full"
    refresh_interval: 10                  # Интервал автообновления в секундах
    type: "summary"                       # "summary" | "chart" | "table" | "status"
    default_active: true
    resizable: true

# === Схема настроек (JSON Schema) ===
config_schema:
  type: object
  properties:
    poll_interval:
      type: integer
      title: "Интервал опроса (сек)"
      default: 30
      minimum: 5
      maximum: 3600
    alert_email:
      type: string
      title: "Email для оповещений"
      default: "admin@example.com"
      format: "email"
  required:
    - poll_interval

# === Ресурсы и Системные директории ===
assets:
  cache_dirs:
    - "cache/sensors"
  data_dirs:
    - "data/rrd"

# === Локализация (i18n) ===
# Примечание: рекомендуется выносить основные словари в файлы `locales/ru.json`, `locales/en.json`,
# а в манифесте задавать только базовые inline-переводы.
i18n:
  ru:
    sensorTitle: "Мониторинг датчиков"
    sensorDesc: "Модуль сбора и визуализации телеметрии с датчиков"
  en:
    sensorTitle: "Sensor Monitor"
    sensorDesc: "Telemetry collection and visualization module"

# === Жизненный цикл (Hooks) ===
hooks:
  on_startup: "backend.modules.sensor_monitor.lifecycle:on_startup"
  on_shutdown: "backend.modules.sensor_monitor.lifecycle:on_shutdown"
```
