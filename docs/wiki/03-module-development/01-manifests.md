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
2. **YAML Parsing & Pydantic Validation**: Парсит YAML и валидирует данные строго по Pydantic-модели `ModuleManifest` в функции `_parse_manifest` (`loader.py`).
3. **Нормализация**: 
   - Для субмодулей автоматически формирует префикс `id` (`parent_id.sub_id`) и добавляет родителя в списки зависимостей `deps`.
   - Приводит одиночные строки в `entrypoints.router` и `entrypoints.services` к списку строк `list[str]`.
4. **Topological Sorting (Топологическая сортировка)**: Строит граф зависимостей через `toposort_modules` (`resolver.py`) с учетом обязательных (`deps`) и опциональных (`optional_deps`) зависимостей.
5. **Registration & Permissions Sync**: Регистрирует модуль в `registry.py` и автоматически синхронизирует объявленные права доступа с базой данных SQLite (`sync_module_permissions`).

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

---

## 🔍 Полный справочник полей манифеста

Все поля валидируются Pydantic-классом `ModuleManifest` (`backend/core/plugin/manifest.py`).

### 1. Основные метаданные

| Поле | Тип | Default | Описание |
| :--- | :--- | :--- | :--- |
| `id` | `str` | *Обязательное* | Уникальный системный идентификатор модуля в формате `snake_case` (например: `sensor_monitor`). |
| `name` | `str` | `""` | Отображаемое имя модуля или ключ i18n (например: `sensorTitle`). |
| `version` | `str` | `"1.0.0"` | Версия модуля по стандарту SemVer (например: `1.2.0`). |
| `description` | `str` | `""` | Краткое описание функциональности модуля или ключ i18n. |
| `enabled_by_default` | `bool` | `true` | Флаг автоматической активации модуля при первом старте системы. |
| `type` | `str` | `"feature"` | Тип модуля: `"system"` (системное ядро), `"feature"` (прикладной модуль), `"driver"` (драйвер устройств). |

---

### 2. Совместимость с версией ядра

| Поле | Тип | Default | Описание |
| :--- | :--- | :--- | :--- |
| `min_core_version` | `str \| null` | `null` | Минимальная версия ядра NMS WebUI, необходимая для работы модуля. |
| `max_core_version` | `str \| null` | `null` | Максимальная версия ядра NMS WebUI, с которой протестирован модуль. |

---

### 3. Зависимости и Субмодули

| Поле | Тип | Default | Описание |
| :--- | :--- | :--- | :--- |
| `deps` | `list[str]` | `[]` | Список ID модулей, обязательных для загрузки текущего модуля. |
| `optional_deps` | `list[str]` | `[]` | Опциональные зависимости. Если эти модули присутствуют и включены, данный модуль будет загружен *после* них. |
| `parent` | `str \| null` | `null` | ID родительского модуля (заполняется только для дочерних субмодулей). |

---

### 4. Точки входа Python (`EntrypointsSchema`)

Точки входа определяют, какие Python-модули и функции вызываются ядром при загрузке. Все пути указываются в формате `path.to.module:attribute` и импортируются с помощью функции `_import_from_path` (`loader.py`).

> [!NOTE]
> **Передача контекста (`ModuleContext`)**: При вызове функций точек входа Загрузчик автоматически пытается передать объект `ctx: ModuleContext` (содержащий `module_id`, `root`, `manifest`). Благодаря механизму `_call_with_fallbacks` (`loader.py`), функция точки входа может принимать 2 аргумента `(app, ctx)`, 1 аргумент `(ctx)` или не принимать аргументов `()`.

#### Подробный разбор элементов `entrypoints`:

##### 1. `entrypoints.factory` — Фабрика инстанса модуля
- **Формат**: `"path.to.module:create_module"` или `"path.to.module:ModuleClass"`
- **Назначение**: Возвращает созданный экземпляр модуля (наследуемый от `BaseModule`).
- **Автоматический жизненный цикл инстанса**:
  1. Экземпляр сохраняется в реестре инстансов (`register_instance` в `registry.py`).
  2. Если у объекта есть метод `get_log_provider()`, зарегистрирует его лог-провайдер в `log_provider_registry`.
  3. Если у объекта есть метод `init()`, Загрузчик вызывает `instance.init()`.
  4. Если у объекта есть метод `start()` и активен asyncio loop, Загрузчик вызывает `instance.start()`.

*Пример кода (`backend/modules/sensor_monitor/__init__.py`)*:
```python
from backend.core.plugin.base import BaseModule
from backend.core.plugin.context import ModuleContext

class SensorMonitorModule(BaseModule):
    def init(self):
        # Первичная инициализация ресурсов
        pass

    def start(self):
        # Запуск фоновых задач
        pass

def create_module(ctx: ModuleContext) -> SensorMonitorModule:
    return SensorMonitorModule(ctx)
```

##### 2. `entrypoints.router` — API Роутеры FastAPI
- **Формат**: `str` или `list[str]` (например: `"backend.modules.sensor_monitor.api:get_router"`)
- **Назначение**: Функция или переменная, возвращающая экземпляр `fastapi.APIRouter`.
- **Механизм**: Загрузчик вызывает функцию (с передачей `ctx`), проверяет тип через `isinstance(router, APIRouter)` и автоматически выполняет `app.include_router(router)`, подключая эндпоинты модуля к главному API платформы NMS WebUI.

*Пример кода (`backend/modules/sensor_monitor/api.py`)*:
```python
from fastapi import APIRouter
from backend.core.plugin.context import ModuleContext

def get_router(ctx: ModuleContext) -> APIRouter:
    router = APIRouter(prefix="/api/sensor-monitor", tags=["Sensor Monitor"])

    @router.get("/metrics")
    async def get_metrics():
        return {"status": "ok", "module": ctx.module_id}

    return router
```

##### 3. `entrypoints.services` — Регистрация фоновых служб
- **Формат**: `str` или `list[str]` (например: `"backend.modules.sensor_monitor.services:init_services"`)
- **Назначение**: Функция регистрации независимых фоновых служб, подписчиков событий или периодических задач.
- **Сигнатура**: Принимает `(app: FastAPI, ctx: ModuleContext)`.

*Пример кода (`backend/modules/sensor_monitor/services.py`)*:
```python
from fastapi import FastAPI
from backend.core.plugin.context import ModuleContext

def init_services(app: FastAPI, ctx: ModuleContext) -> None:
    # Регистрация слушателей событий или фоновых задач
    print(f"Службы модуля {ctx.module_id} успешно зарегистрированы")
```

##### 4. `entrypoints.settings` — Динамическая схема настроек
- **Формат**: `str` (например: `"backend.modules.sensor_monitor.settings:get_schema"`)
- **Назначение**: Позволяет динамически вычислять и отдавать JSON Schema пользовательских настроек в рантайме.
- **Механизм**: Возвращенный словарь объединяется с существующим `manifest.config_schema`, обогащая форму настроек в UI.

*Пример кода (`backend/modules/sensor_monitor/settings.py`)*:
```python
from typing import Any
from backend.core.plugin.context import ModuleContext

def get_schema(ctx: ModuleContext) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "dynamic_option": {
                "type": "string",
                "title": "Динамический параметр",
                "default": "default_value"
            }
        }
    }
```

---

### 5. UI Маршруты (`RouteSchema` и `RouteMetaSchema`)

Секция `routes` содержит список UI-маршрутов Vue Router. Каждый элемент имеет структуру:

```yaml
routes:
  - path: "/sensor-monitor"              # URL путь в SPA
    name: "sensor-monitor-index"         # Уникальное имя маршрута
    meta:
      title: "Датчики"                   # Заголовок страницы
      icon: "sensors"                    # Иконка (Lucide / Material)
      group: "monitoringGroup"           # Группировка
      requires_auth: true                # Требуется ли авторизация
      permissions:                       # Необходимые права доступа
        - "module.sensor_monitor.view"
      settings_view: false               # Является ли страницей настроек
```

---

### 6. Элементы Меню Навигации (`MenuSchema`)

Секция `menu` конфигурирует отображение в левой панели (Sidebar) или подвале (Footer):

```yaml
menu:
  location: sidebar                      # "sidebar" | "footer" | null
  group: "monitoringGroup"               # Идентификатор группы в меню
  items:
    - path: "/sensor-monitor"            # Путь перехода
      label: "sensorTitle"               # Текст пункта или ключ i18n
      icon: "sensors"                    # Иконка
```

---

### 7. Права доступа RBAC (`PermissionSchema`)

Разрешения, регистрируемые модулем в общей системе ролей платформы:

```yaml
permissions:
  - id: "module.sensor_monitor.control"  # Уникальный ID разрешения
    name: "Управление датчиками"         # Понятное имя в UI
    category: "Мониторинг"               # Группа на странице назначения ролей
    description: "Описание действия"      # Подробная подсказка
```

---

### 8. Виджеты Дашборда (`WidgetSchema`)

Виджеты, добавляемые модулем на главную панель (Dashboard):

| Поле | Тип | Default | Описание |
| :--- | :--- | :--- | :--- |
| `id` | `str` | *Обязательное* | Уникальный ID виджета. |
| `title` | `str` | `""` | Заголовок карточки виджета. |
| `description` | `str` | `""` | Краткое описание функции виджета. |
| `component` | `str` | `""` | Имя Vue-компонента на фронтенде. |
| `endpoint` | `str \| null` | `null` | REST API URL для получения метрик виджета. |
| `size` | `str` | `"medium"` | Размер сетки: `"small"`, `"medium"`, `"large"`, `"full"`. |
| `refresh_interval` | `int \| null` | `null` | Периодичность обновления данных в секундах. |
| `type` | `str` | `"summary"` | Тип отображения: `"summary"`, `"chart"`, `"table"`, `"status"`. |
| `default_active` | `bool` | `false` | Отображать ли виджет по умолчанию при новом дашборде. |
| `resizable` | `bool` | `true` | Разрешено ли пользователю изменять размер виджета. |

---

### 9. Схема Конфигурации (`config_schema`)

Поле `config_schema` содержит описание пользовательских настроек в формате **JSON Schema**. Опираясь на эту схему, ядро NMS WebUI:
1. Валидирует сохраняемые настройки модуля в базе данных SQLite.
2. Динамически генерирует форму редактирования настроек в интерфейсе администрирования.
3. Автоматически подставляет значения по умолчанию (`default`).

---

### 10. Дополнительные секции (`assets`, `i18n`, `hooks`)

- **`assets`**: Объявляет директории хранения данных и кэшей (`AssetsSchema`):
  - `cache_dirs: list[str]` — временные директории.
  - `data_dirs: list[str]` — директории постоянных данных.
- **`i18n`**: Встроенный (inline) словарь переводов `dict[str, dict[str, str]]` для базовых названий и меню. 
  > [!TIP]
  > **Лучшая практика**: Чтобы не раздувать `manifest.yaml`, основные словари переводов интерфейса и сообщений рекомендуется хранить в отдельной директории модуля `locales/` (`locales/ru.json`, `locales/en.json`). Загрузчик `loader.py` автоматически сканирует директорию `locales/` и объединяет эти словари с inline-переводами из `manifest.i18n`.
- **`hooks`**: Словарь `dict[str, str]` Python-путей к обработчикам событий жизненного цикла модуля (`on_startup`, `on_shutdown`).

---

## ⚙️ Системные механизмы и поведение ядра

При загрузке и работе с манифестом ядро NMS WebUI выполняет ряд автоматических неявных действий:

### 1. Автоматическая генерация прав доступа по умолчанию
Если секция `permissions` в `manifest.yaml` **отсутствует или пуста**, функция `sync_module_permissions` в `registry.py` автоматически создаст в БД SQLite 3 дефолтных разрешения:
- `module.<id>.view` — Доступ к просмотру интерфейса модуля.
- `module.<id>.edit` — Редактирование параметров модуля.
- `module.<id>.control` — Выполнение команд и управление модулем.

Все указанные разрешения автоматизировано связываются с базовыми системными ролями: **Суперпользователь (роль '1')** и **Администратор (роль '2')**.

### 2. Извлечение дефолтных настроек
Функция `_defaults_from_schema` в `registry.py` рекурсивно обходит `config_schema` модуля и извлекает все указанные там поля `default`. Это позволяет модулю работать с корректной конфигурацией сразу после установки.

### 3. Авто-нормализация субмодулей
Когда `_parse_manifest` находит субмодуль (находящийся в папке `submodules/`):
- Если `id` субмодуля не содержит точки, ему присваивается составной ID: `<parent_id>.<submodule_id>`.
- Родительский модуль автоматически прописывается в поле `parent` и добавляется в массив `deps`.

### 4. Агрегация виджетов Дашборда
При вызове `get_all_widgets` в `registry.py` система опрашивает манифесты всех **включенных** модулей, собирает их виджеты и добавляет системный виджет управления модулями (`system-modules`), формируя единую витрину виджетов для фронтенда.

### 5. Топологическая сортировка и защита от циклов
Функция `toposort_modules` в `resolver.py` упорядочивает модули так, чтобы все зависимости инициализировались строго до зависимых модулей. Если в графе `deps` обнаружена **циклическая зависимость**:
- Выводится предупреждение в системный лог: `Module dependency cycle detected; loading in discovery order`.
- Загрузка продолжается в порядке сканирования файлов без остановки приложения.

---

## 🛠 Troubleshooting и типичные ошибки

### 1. Ошибка валидации Pydantic (`ValidationError`)
**Симптом**: В логе появляется сообщение `Failed to parse manifest <path>: <error>`.
**Причина**: В `manifest.yaml` указаны неверные типы данных (например, `refresh_interval: "пять"` вместо числа) или нарушена структра YAML.
**Решение**: Проверьте типы полей по разделу [Полный справочник полей манифеста](#-полный-справочник-полей-манифеста).

### 2. Ошибка импорта точечных входов (`ImportError` / `AttributeError`)
**Симптом**: Модуль не загружает свои API-маршруты или сервисы.
**Причина**: В секции `entrypoints` указан несуществующий модуль Python или опечатка в имени переменной `router`/`factory`.
**Решение**: Убедитесь, что Python-путь вида `"backend.modules.my_mod.api:router"` указывает на валидный объект в коде.

### 3. Отсутствие обязательной зависимости
**Симптом**: В логе появляется `Module <id> declares unknown dependency: <dep_id>`.
**Причина**: Модуль, указанный в `deps`, отсутствует в директории `backend/modules/` или не смог загрузиться из-за ошибки в собственном манифесте.
**Решение**: Проверьте наличие и корректность загрузки всех модулей из списка `deps`.
