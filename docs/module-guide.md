# Руководство по созданию пользовательских модулей NMS-WebUI

Данное руководство описывает архитектуру и процесс разработки пользовательских функциональных модулей (плагинов) для системы NMS-WebUI, включая серверную логику, клиентские Vue-компоненты, управление разрешениями, гибкие настройки, локализацию и виджеты дашборда.

---

## 📁 Общая структура модуля

Модуль NMS-WebUI состоит из бэкенд-части и фронтенд-части:

- **Бэкенд**: `backend/modules/<module_id>/`
- **Фронтенд**: `frontend/src/modules/<module_id>/`

### Полное дерево файлов модуля:
```text
backend/modules/<module_id>/
├── manifest.yaml      # ⚠️ Главный манифест (метаданные, роуты, настройки, пермишены, виджеты)
├── __init__.py        # Точка входа для загрузчика (функция create_module)
├── module.py          # Основной класс модуля (наследует BaseModule)
├── api.py             # FastAPI роутер (/api/v1/m/<module_id>)
├── services.py        # Бизнес-логика и сервисы
├── models.py          # Модели Pydantic / SQLAlchemy
├── locales/           # 🌍 Локализации модуля
│   ├── ru.json
│   └── en.json
└── widgets/           # Логика и обработчики виджетов
    └── __init__.py

frontend/src/modules/<module_id>/
├── <Module>View.vue   # Главная страница модуля (например, TuyaView.vue)
├── <Module>Widget.vue # (Опционально) Кастомный Vue-виджет дашборда (например, TuyaWidget.vue)
└── components/        # Внутренние Vue-компоненты модуля
```

---

## 📜 1. Создание модулей

### 1.1. Единый манифест (`manifest.yaml`)

`manifest.yaml` — это единый источник истины для системы. Бэкенд считывает его при старте для регистрации API и настроек, а фронтенд — для автоматического формирования роутов и меню.

#### Пример полновесного манифеста (`manifest.yaml`):

```yaml
id: tuya                        # kebab-case, уникальный идентификатор модуля
name: tuyaTitle                 # Ключ локализации или читаемое название
version: 1.0.0                  # Семантическое версионирование
description: tuyaSub            # Ключ локализации или краткое описание
enabled_by_default: true        # Авто-активация при первичной установке
type: driver                    # Тип: system | feature | driver

deps: []                        # Зависимости от других модулей (например: [database])

entrypoints:                    # Точки интеграции с бэкенд-ядром
  factory: "backend.modules.tuya:create_module"
  router: "backend.modules.tuya.api:get_router"

routes:                         # Регистрация UI-страниц во фронтенде
  - path: "/tuya"
    name: "tuya-index"
    meta:
      title: "Tuya Devices"
      titleKey: "tuyaTitle"
      icon: "cpu"              # Иконка Material Symbols
      group: "devicesGroup"    # Группа меню
      requires_auth: true
      permissions:
        - "module.tuya.view"

menu:                           # Отображение в навигации
  location: sidebar             # Место: sidebar или footer
  group: "devicesGroup"
  items:
    - path: "/tuya"
      label: "tuyaTitle"
      icon: "cpu"

config_schema:                  # JSON Schema для настроек
  type: object
  properties:
    client_id:
      type: string
      default: ""
      title: "tuyaClientId"
      group: "tuyaGroupCloud"
    poll_interval_sec:
      type: integer
      minimum: 5
      maximum: 300
      default: 15
      title: "tuyaPollInterval"
      group: "tuyaGroupControl"

permissions:                    # Разрешения модуля
  - id: "module.tuya.view"
    name: "permName_module.tuya.view"
    category: "Tuya"
    description: "permDesc_module.tuya.view"

widgets:                        # Виджеты дашборда
  - id: "tuya-summary"
    title: "tuyaWidgetTitle"
    description: "tuyaWidgetDesc"
    endpoint: "/api/v1/m/tuya/widgets/summary"
    component: "TuyaWidget"
    size: "medium"
    refresh_interval: 15
```

---

### 1.2. Бэкенд-реализация

#### Точка входа (`__init__.py`)
Содержит функцию-фабрику, указанную в `entrypoints.factory`:
```python
from backend.core.plugin.context import ModuleContext
from .module import TuyaModule

def create_module(ctx: ModuleContext) -> TuyaModule:
    return TuyaModule(ctx)
```

#### Класс модуля (`module.py`)
Наследует `BaseModule` и управляет жизненным циклом:
```python
from backend.modules.base import BaseModule
from typing import Any

class TuyaModule(BaseModule):
    def init(self) -> None:
        """Инициализация ресурсов при старте системы."""
        print(f"Модуль {self.context.id} инициализирован")

    def start(self) -> None:
        """Запуск фоновых задач или подписок."""
        pass

    def stop(self) -> None:
        """Корректное завершение работы."""
        pass

    def get_status(self) -> dict[str, Any]:
        """Возвращает текущий статус модуля."""
        return {"status": "online", "active_devices": 12}
```

#### Эндпоинты API (`api.py`)
Возвращает FastAPI `APIRouter`. Все эндпоинты модуля автоматически монтируются по префиксу `/api/v1/m/<module_id>`:
```python
from fastapi import APIRouter, Depends
from backend.core.auth import require_permission

router = APIRouter()

@router.get("/devices")
async def get_devices(user=Depends(require_permission("module.tuya.view"))):
    return [{"id": "dev-01", "name": "Smart Plug", "status": "on"}]

def get_router() -> APIRouter:
    return router
```

---

### 1.3. Фронтенд-реализация

Фронтенд NMS-WebUI автоматизирован через Vite `import.meta.glob`. Вам **не нужно** вручную править глобальный `router.ts` или добавлять импорты в ядре приложения.

1. Создайте файл страницы в `frontend/src/modules/<module_id>/<Module>View.vue` (например, `TuyaView.vue`).
2. Фронтенд-загрузчик `loader.ts` сканирует папку `src/modules/**/*.vue` и автоматически привязывает Vue-компонент к роутам из `manifest.yaml` по соглашению имен (`tuya-index`, `TuyaView`, `tuya`).

---

## 🔐 2. Разрешения (Permissions)

NMS-WebUI использует Role-Based Access Control (RBAC) с детализацией до конкретных прав.

### 2.1. Объявление разрешений в манифесте
Разрешения описываются в блоке `permissions:` файла `manifest.yaml`:
```yaml
permissions:
  - id: "module.tuya.view"
    name: "permName_module.tuya.view"
    category: "Tuya"
    description: "permDesc_module.tuya.view"
  - id: "module.tuya.edit"
    name: "permName_module.tuya.edit"
    category: "Tuya"
    description: "permDesc_module.tuya.edit"
  - id: "module.tuya.control"
    name: "permName_module.tuya.control"
    category: "Tuya"
    description: "permDesc_module.tuya.control"
```

### 2.2. Автоматическая синхронизация с БД
При регистрации модуля система исполняет функцию `sync_module_permissions(manifest)`:
1. Записывает разрешения в таблицу `permissions` в SQLite базе данных `nms.db`.
2. Автоматически привязывает новые разрешения к ролям **Суперпользователь** (role_id=1) и **Администратор** (role_id=2).
3. **Автодефолт**: Если блок `permissions:` в `manifest.yaml` опущен, система автоматически создаст 3 базовых разрешения:
   - `module.<module_id>.view` — Просмотр
   - `module.<module_id>.edit` — Настройка
   - `module.<module_id>.control` — Управление

### 2.3. Защита бэкенд API
Используйте FastAPI dependency `require_permission`:
```python
from fastapi import APIRouter, Depends
from backend.core.auth import require_permission, CurrentUser

router = APIRouter()

@router.post("/device/toggle")
async def toggle_device(
    device_id: str,
    user: CurrentUser = Depends(require_permission("module.tuya.control"))
):
    return {"success": True, "executed_by": user.username}
```

### 2.4. Защита UI-маршрутов на фронтенде
В манифесте в `routes[].meta.permissions` указаны права, необходимые для перехода на страницу:
```yaml
routes:
  - path: "/tuya"
    name: "tuya-index"
    meta:
      permissions:
        - "module.tuya.view"
```

---

## ⚙️ 3. Настройки (Settings)

Настройки модулей хранятся в единой таблице `system_settings` в SQLite базе данных и синхронизируются в реальном времени.

### 3.1. Схема настроек `config_schema`
Используется формат JSON Schema для автоматической генерации UI-форм:

```yaml
config_schema:
  type: object
  properties:
    client_id:
      type: string
      default: ""
      title: "tuyaClientId"       # Ключ локализации
      group: "tuyaGroupCloud"    # Группа полей на форме
    region:
      type: string
      default: "eu"
      title: "tuyaRegion"
      enum: ["eu", "us", "cn", "in"]
      group: "tuyaGroupCloud"
    poll_interval_sec:
      type: integer
      minimum: 5
      maximum: 300
      default: 15
      title: "tuyaPollInterval"
      group: "tuyaGroupControl"
    auto_discovery:
      type: boolean
      default: true
      title: "tuyaAutoDiscovery"
      group: "tuyaGroupControl"
```

#### Особенности генератора UI-форм:
- **Группировка**: Свойство `group` объединяет поля в логические секции/вкладки.
- **Валидация IP**: Поля с `format: "ipv4"` или содержащие `host`/`ip` в названии автоматически проверяются на валидность IP-адреса.
- **Диапазоны**: `minimum` и `maximum` ограничивают ввод чисел.

### 3.2. Чтение и запись настроек на бэкенде
Для доступа к настройкам используйте методы из `backend.core.plugin.registry`:

```python
from backend.core.plugin.registry import get_module_settings, save_module_settings

# Чтение настроек модуля
settings = get_module_settings("tuya")
region = settings.get("region", "eu")
poll_interval = settings.get("poll_interval_sec", 15)

# Сохранение настроек (сохраняются в nms.db и рассылают событие обновления)
save_module_settings("tuya", {
    "region": "us",
    "poll_interval_sec": 30
})
```

### 3.3. Автосохранение на фронтенде
Компоненты `ModuleView.vue` и `Settings.vue` автоматически генерируют форму на основе `config_schema`. При изменении пользователем любого поля происходит автосохранение с задержкой (debounce 750 мс).

---

## 🌍 4. Локализация (Localization / i18n)

В NMS-WebUI используется стандартизированная локализация через файлы JSON.

> [!IMPORTANT]
> **Единственный стандарт локализации модулей**: Переводы размещаются **исключительно** в файлах `locales/ru.json`, `locales/en.json` внутри папки модуля. В манифесте указываются ключи локализации.

### 4.1. Структура файлов локализации
Пример `backend/modules/tuya/locales/ru.json`:
```json
{
  "messages": {
    "tuyaTitle": "Устройства Tuya",
    "tuyaSub": "Интеграция со смарт-устройствами экосистемы Tuya",
    "devicesGroup": "Умный дом",
    "tuyaGroupCloud": "Облачное подключение",
    "tuyaGroupControl": "Параметры опроса",
    "tuyaClientId": "Client ID (Access Key)",
    "tuyaClientSecret": "Client Secret",
    "tuyaRegion": "Регион сервера",
    "tuyaPollInterval": "Интервал опроса (сек)",
    "tuyaWidgetTitle": "Статус Tuya",
    "tuyaWidgetDesc": "Сводка состояния устройств Tuya",
    "permName_module.tuya.view": "Просмотр устройств Tuya",
    "permDesc_module.tuya.view": "Доступ к просмотру состояния устройств Tuya"
  }
}
```

Пример `backend/modules/tuya/locales/en.json`:
```json
{
  "messages": {
    "tuyaTitle": "Tuya Devices",
    "tuyaSub": "Tuya Smart Home ecosystem integration",
    "devicesGroup": "Smart Home",
    "tuyaGroupCloud": "Cloud API Credentials",
    "tuyaGroupControl": "Polling Settings",
    "tuyaClientId": "Client ID (Access Key)",
    "tuyaClientSecret": "Client Secret",
    "tuyaRegion": "Server Region",
    "tuyaPollInterval": "Poll Interval (sec)",
    "tuyaWidgetTitle": "Tuya Status",
    "tuyaWidgetDesc": "Summary of Tuya devices status",
    "permName_module.tuya.view": "View Tuya Devices",
    "permDesc_module.tuya.view": "Permission to view Tuya device status"
  }
}
```

### 4.2. Автозагрузка локализаций
Бэкенд предоставляет эндпоинт `/api/modules/<module_id>/locales/<lang>`.При инициализации приложения фронтенд (`initModulesRegistry` в `registry.ts`) автоматически запрашивает и регистрирует локализации для всех поддерживаемых языков системы.

### 4.3. Использование во Vue-компонентах
```html
<template>
  <div>
    <h1>{{ t('tuyaTitle') }}</h1>
    <p>{{ t('tuyaSub') }}</p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '@/core/i18n'
const { t } = useI18n()
</script>
```

---

## 🧩 5. Виджеты (Widgets)

Виджеты позволяют выводить оперативные сводки модуля на главный дашборд приложения.

### 5.1. Объявление виджета в `manifest.yaml`
```yaml
widgets:
  - id: "tuya-summary"
    title: "tuyaWidgetTitle"
    description: "tuyaWidgetDesc"
    endpoint: "/api/v1/m/tuya/widgets/summary"  # API-эндпоинт данных виджета
    component: "TuyaWidget"                    # Имя Vue-компонента
    size: "medium"                             # Размер: small | medium | large
    refresh_interval: 15                       # Период автообновления в секундах
    type: "summary"                            # Тип: summary | stat | list | custom
```

### 5.2. Бэкенд-эндпоинт данных виджета (`api.py`)
Эндпоинт должен возвращать объект `WidgetData`:
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/widgets/summary")
async def get_tuya_widget_summary():
    return {
        "status": "ok",          # ok | warning | error | info
        "title": "tuyaWidgetTitle",
        "metrics": [
            {
                "id": "online_devs",
                "label": "Онлайн",
                "value": 8,
                "unit": "шт",
                "status": "ok",
                "icon": "power"
            },
            {
                "id": "offline_devs",
                "label": "Офлайн",
                "value": 1,
                "unit": "шт",
                "status": "warning",
                "icon": "power_off"
            }
        ],
        "actions": [
            {
                "label": "Перейти к устройствам",
                "path": "/tuya",
                "icon": "arrow_forward"
            }
        ]
    }
```

### 5.3. Фронтенд-виджеты

Существует 2 способа отображения виджетов:

#### Способ А: Стандартный рендеринг (Без написания Vue-кода)
Если `component` в манифесте опущен или указывает на базовый тип, `WidgetRenderer.vue` автоматически отрисует сетку метрик (`metrics`) или список элементов (`items`).

#### Способ Б: Кастомный Vue-виджет модуля (`TuyaWidget.vue`)
Создайте файл `frontend/src/modules/<module_id>/<WidgetName>.vue` (например, `TuyaWidget.vue`). Он будет автоматически обнаружен и зарегистрирован в `loader.ts`.

Пример `frontend/src/modules/tuya/TuyaWidget.vue`:
```html
<template>
  <div class="p-3 space-y-3">
    <!-- Загрузка -->
    <div v-if="loading" class="text-xs text-on-surface-variant animate-pulse">
      Обновление данных...
    </div>

    <!-- Ошибка -->
    <div v-else-if="error" class="text-xs text-error">
      {{ error }}
    </div>

    <!-- Кастомное содержимое виджета -->
    <div v-else-if="data" class="space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold">Всего устройств</span>
        <span class="font-mono text-sm font-bold text-primary">
          {{ totalDevices }}
        </span>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div v-for="m in data.metrics" :key="m.id" class="p-2 rounded bg-surface-container-high">
          <div class="text-[10px] text-on-surface-variant">{{ m.label }}</div>
          <div class="text-sm font-bold font-mono">{{ m.value }} {{ m.unit || '' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WidgetData } from '@/modules/widgets'

const props = defineProps<{
  data: WidgetData | null
  loading: boolean
  error: string | null
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
}>()

const totalDevices = computed(() => {
  if (!props.data?.metrics) return 0
  return props.data.metrics.reduce((acc, m) => acc + (Number(m.value) || 0), 0)
})
</script>
```

`WidgetRenderer.vue` автоматически передает пропсы `:data`, `:loading`, `:error` и слушает событие `@refresh` для ручного обновления.

---

## 🔁 6. Чеклист для проверки нового модуля

Before запуск модуля проверьте:
1. [ ] Файл `manifest.yaml` валиден и содержит все нужные эндпоинты и пути.
2. [ ] В `__init__.py` реализована функция `create_module(ctx)`.
3. [ ] В `api.py` функция `get_router()` возвращает FastAPI `APIRouter`.
4. [ ] Все эндпоинты защищены через `Depends(require_permission(...))`.
5. [ ] В `locales/ru.json` и `locales/en.json` присутствуют все ключи локализации.
6. [ ] Для фронтенд-страниц созданы соответствующие `.vue` файлы в `frontend/src/modules/<module_id>/`.