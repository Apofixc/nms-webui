# ⚙️ 5. Настройки модулей и работа с JSON Schema (Config & Settings API)

Настоящее руководство подробно описывает подсистему управления настройками модулей в NMS WebUI. Подсистема позволяет модулям декларативно описывать свои параметры через **JSON Schema**, автоматизировать генерацию пользовательского интерфейса (UI), поддерживать динамические настройки в зависимости от состояния окружения, а также обеспечивать горячее обновление параметров без перезапуска сервисов (Hot Reload).

---

## 🏗️ 1. Архитектура подсистемы настроек

Подсистема Config & Settings API состоит из трех ключевых слоев: декларации/вычисления схемы, изолированного SQLite-хранилища и графического интерфейса с подсиskew подписок на события.

```mermaid
sequenceDiagram
    autonumber
    participant UI as Vue Frontend (ModuleView)
    participant REST as REST API (/api/modules/{id}/settings)
    participant Reg as Core Plugin Registry
    participant Mod as Python Module (Instance)
    participant DB as SQLite (system_settings)

    UI->>REST: GET /api/modules/{id}/settings-definition
    REST->>Reg: get_module_settings_definition(module_id)
    alt Схема статическая (manifest.yaml)
        Reg->>Reg: get_module_settings_schema()
    else Схема динамическая (entrypoints.settings)
        Reg->>Mod: get_dynamic_schema(context)
        Mod-->>Reg: Вычисленная JSON Schema
    end
    Reg->>DB: _load_raw_settings()
    DB-->>Reg: Настройки из modules_settings
    Reg-->>REST: { schema, defaults, current }
    REST-->>UI: Отрендеренная схема и значения

    UI->>REST: PUT /api/modules/{id}/settings (Новые значения)
    REST->>Reg: save_module_settings(module_id, body)
    Reg->>DB: _save_raw_settings() (Обновление SQLite)
    Reg->>Reg: notify_settings_changed(module_id)
    Reg-->>UI: WebSocket событие "module_settings_changed"
    Reg-->>Mod: Вызов обработчика hot-reload в модуле
```

### Хранение настроек в БД
Настройки всех модулей централизованно хранятся в единой базе данных SQLite (`nms.db`) в системной таблице `system_settings` под ключом `modules_settings`.

Структура записи в БД:
```json
{
  "modules": {
    "sensor_monitor": {
      "enabled": true,
      "settings": {
        "poll_interval": 60,
        "interface": "eth0",
        "alert_email": "admin@example.com"
      }
    }
  }
}
```

Все операции чтения и записи производятся через функции служебного модуля `backend/core/plugin/registry.py`:
- `_load_raw_settings()` — считывает JSON-словарь из `system_settings`.
- `_save_raw_settings(data)` — атомарно обновляет настройки в `system_settings`.

---

## 📝 2. Декларативные схемы настроек (`config_schema`)

Каждый модуль может объявить статическую схему пользовательских настроек в своем манифесте `manifest.yaml` в блоке `config_schema`. Схема должна соответствовать спецификации **JSON Schema (Draft 7)**.

### Поддерживаемые типы данных и атрибуты

| Тип в JSON Schema | Элемент интерфейса (UI) | Поддерживаемые атрибуты валидации и UI |
| :--- | :--- | :--- |
| `boolean` | Кастомный переключатель (Toggle Switch) | `title`, `description`, `default` |
| `string` (с `enum`) | Выпадающий список (`<select>`) | `title`, `description`, `enum`, `default` |
| `string` | Текстовое поле ввода (`<input type="text">`) | `title`, `description`, `placeholder`, `default`, `pattern` |
| `string` (`format: password` или имя `secret`/`password`) | Маскированное поле ввода (`<input type="password">`) | `title`, `description`, `placeholder`, `default` |
| `integer` / `number` | Числовое поле ввода (`<input type="number">`) | `title`, `description`, `default`, `minimum`, `maximum` |

> [!NOTE]
> Заголовки (`title`), описания (`description`) и подсказки (`placeholder`) автоматически пропускаются через системную функцию локализации `t(key)`. Если ключа нет в словаре i18n модуля, отображается оригинальный текст.

### Пример декларации `config_schema` в `manifest.yaml`

```yaml
id: "sensor_monitor"
name: "Мониторинг сенсоров"
version: "1.2.0"

config_schema:
  type: "object"
  required:
    - "poll_interval"
    - "api_token"
  properties:
    poll_interval:
      type: "integer"
      title: "sensor_monitor.settings.poll_interval_title"
      description: "sensor_monitor.settings.poll_interval_desc"
      default: 30
      minimum: 5
      maximum: 3600

    alert_email:
      type: "string"
      title: "Email для алармов"
      placeholder: "admin@domain.com"
      default: "admin@example.com"

    api_token:
      type: "string"
      format: "password"
      title: "API Токен доступа"
      description: "Секретный токен для подключения к внешнему агенту"

    enable_notifications:
      type: "boolean"
      title: "Включить отправку уведомлений"
      default: true

    log_level:
      type: "string"
      title: "Уровень логирования"
      default: "INFO"
      enum:
        - "DEBUG"
        - "INFO"
        - "WARNING"
        - "ERROR"
```

---

## 🐍 3. Динамические схемы настроек (`entrypoints.settings`)

Если опции выпадающих списков или граничные значения параметров зависят от рантайм-условий (например, список физических сетевых интерфейсов, доступные COM-порты или текущий список пользователей системного окружения), модуль использует **динамическую схему**.

### Объявление точки входа в `manifest.yaml`
```yaml
entrypoints:
  settings: "backend.modules.sensor_monitor.settings:get_dynamic_schema"
```

### Реализация функции формирования схемы
Функция точки входа принимает единственный аргумент — `ctx: ModuleContext` — и возвращает полный словарь JSON Schema:

```python
# backend/modules/sensor_monitor/settings.py
from typing import Any
import psutil
from backend.core.plugin.context import ModuleContext

def get_dynamic_schema(ctx: ModuleContext) -> dict[str, Any]:
    """Динамически формирует JSON Schema настроек на основе реальных сетевых интерфейсов сервера."""
    # Получаем список физических и виртуальных сетевых интерфейсов сервера
    available_interfaces = list(psutil.net_if_addrs().keys())
    if not available_interfaces:
        available_interfaces = ["eth0", "lo"]

    ctx.logger.debug("Сформирован динамический список интерфейсов: %s", available_interfaces)

    return {
      "type": "object",
      "required": ["interface", "poll_interval"],
      "properties": {
        "interface": {
          "type": "string",
          "title": "Сетевой интерфейс опроса",
          "description": "Выберите сетевой интерфейс для отправки RAW-пакетов",
          "enum": available_interfaces,
          "default": available_interfaces[0]
        },
        "poll_interval": {
          "type": "integer",
          "title": "Интервал опроса (сек)",
          "default": 15,
          "minimum": 1,
          "maximum": 300
        },
        "enable_promiscuous": {
          "type": "boolean",
          "title": "Promiscuous Mode",
          "description": "Переводить ли адаптер в режим перехвата всех пакетов",
          "default": False
        }
      }
    }
```

---

## 🛠️ 4. Backend Python API: Работа с настройками

Ядро NMS WebUI предоставляет несколько служебных функций для работы с настройками в коде бекенда (`backend/core/plugin/registry.py`).

### Основные функции Registry

#### 1. Получение текущих настроек модуля
```python
from backend.core.plugin.registry import get_module_settings

settings: dict[str, Any] = get_module_settings("sensor_monitor")
poll_interval = settings.get("poll_interval", 30)
```

#### 2. Сохранение настроек модуля
```python
from backend.core.plugin.registry import save_module_settings

save_module_settings("sensor_monitor", {
    "poll_interval": 60,
    "interface": "eth1"
})
```

#### 3. Получение схемы и полных определений настроек
```python
from backend.core.plugin.registry import (
    get_module_settings_schema,
    get_module_settings_definition
)

# Возвращает чистую JSON Schema (статическую или динамическую)
schema = get_module_settings_schema("sensor_monitor")

# Возвращает полную структуру с дефолтами и текущими значениями
definition = get_module_settings_definition("sensor_monitor")
# Структура ответа definition:
# {
#    "module_id": "sensor_monitor",
#    "schema": { ... },
#    "defaults": { "poll_interval": 30, "interface": "eth0" },
#    "current": { "poll_interval": 60, "interface": "eth1" }
# }
```

### Автоматическое вычисление значений по умолчанию
Функция `_defaults_from_schema(schema)` в `registry.py` рекурсивно обходит JSON Schema и извлекает значения из полей `default`:

```python
def _defaults_from_schema(schema: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    props = schema.get("properties") or {}
    for key, prop in props.items():
        if isinstance(prop, dict) and "default" in prop:
            defaults[str(key)] = prop["default"]
        elif prop.get("type") == "object":
            nested = _defaults_from_schema(prop)
            if nested:
                defaults[str(key)] = nested
    return defaults
```

---

## 🌐 5. Спецификация REST API настроек

Управление настройками модулей осуществляется через HTTP API ядра (`backend/core/plugin/api.py`).

### Таблица эндпоинтов REST API

| Метод | URL-маршрут | Права RBAC | Описание |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/modules/{module_id}/settings-definition` | `settings.view` | Возвращает JSON Schema, значения по умолчанию и текущие сохраненные настройки |
| `GET` | `/api/modules/{module_id}/settings` | `settings.view` | Возвращает словарь текущих настроек модуля из SQLite |
| `PUT` | `/api/modules/{module_id}/settings` | `settings.edit` | Сохраняет новый словарь настроек модуля и инициирует событие обновления |

### Пример ответа `GET /api/modules/sensor_monitor/settings-definition`
```json
{
  "module_id": "sensor_monitor",
  "schema": {
    "type": "object",
    "required": ["poll_interval"],
    "properties": {
      "poll_interval": {
        "type": "integer",
        "title": "Интервал опроса",
        "default": 30,
        "minimum": 5
      }
    }
  },
  "defaults": {
    "poll_interval": 30
  },
  "current": {
    "poll_interval": 60
  }
}
```

### Ошибки и статусы ответов
- **`404 Not Found`** (`MODULE_NO_SETTINGS_SCHEMA`): у указанного модуля отсутствует декларация `config_schema` или точка входа `entrypoints.settings`.
- **`403 Forbidden`**: у текущего пользователя недостаточно прав (`settings.view` или `settings.edit`).

---

## 💻 6. Frontend: Автоматическая генерация UI форм настроек

Интерфейс настроек модулей расположен по маршруту `/settings/modules/:moduleId` в Vue 3 приложении.

```
frontend/src/
├── views/
│   ├── ModuleManagement.vue    # Общий список модулей и управление активностью
│   └── ModuleView.vue          # Страница настроек конкретного модуля
└── components/
    ├── layout/
    │   └── SettingsRail.vue    # Боковое меню быстрых настроек модулей
    └── settings/
        └── SettingsForm.vue    # Реактивный генератор полей формы по JSON Schema
```

### Логика генерации полей в `SettingsForm.vue`

Фронтенд динамически анализирует свойства схемы (`properties`) и рендерит соответствующие Vue-компоненты:

```vue
<!-- Выдержка из frontend/src/components/settings/SettingsForm.vue -->
<template>
  <div class="space-y-6">
    <div v-for="(prop, key) in properties" :key="key" class="bg-surface-750/50 rounded-lg p-4 space-y-2">
      <label class="block text-sm font-medium text-slate-300">
        {{ t(prop.title || key) }}
      </label>

      <!-- 1. Булево значение (Переключатель) -->
      <div v-if="prop.type === 'boolean'" class="flex items-center gap-3">
        <button type="button" :class="[modelValue[key] ? 'bg-accent' : 'bg-surface-700']" @click="toggle(key)">
          <span :class="[modelValue[key] ? 'translate-x-5' : 'translate-x-0']" />
        </button>
        <span class="text-sm text-slate-400">{{ modelValue[key] ? t('onState') : t('offState') }}</span>
      </div>

      <!-- 2. Выпадающий список (Enum) -->
      <select
        v-else-if="prop.type === 'string' && prop.enum"
        :value="modelValue[key] ?? prop.default"
        @change="update(key, ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="opt in prop.enum" :key="opt" :value="opt">{{ opt }}</option>
      </select>

      <!-- 3. Числовое поле (Number/Integer) -->
      <input
        v-else-if="prop.type === 'number' || prop.type === 'integer'"
        type="number"
        :value="modelValue[key] ?? prop.default"
        :min="prop.minimum"
        :max="prop.maximum"
        @input="update(key, Number(($event.target as HTMLInputElement).value))"
      />

      <!-- 4. Строковое/Секретное поле -->
      <input
        v-else
        :type="String(key).includes('secret') || String(key).includes('password') || prop.format === 'password' ? 'password' : 'text'"
        :value="modelValue[key] ?? prop.default ?? ''"
        :placeholder="t(prop.placeholder || prop.title || key)"
        @input="update(key, ($event.target as HTMLInputElement).value)"
      />

      <p v-if="prop.description" class="text-xs text-slate-500 mt-1">
        {{ t(prop.description) }}
      </p>
    </div>
  </div>
</template>
```

### Сброс и сохранение в `ModuleView.vue`
Страница `ModuleView.vue` объединяет текущие сохраненные значения и дефолты при загрузке:

```typescript
// Слияние сохраненных настроек со значениями по умолчанию
settingsValues.value = { ...(def?.defaults || {}), ...(current || {}) }

// Сброс к дефолтам
function resetToDefaults() {
  if (settingsDefinition.value) {
    settingsValues.value = { ...(settingsDefinition.value.defaults || {}) }
  }
}

// Отправка на бекенд
async function save() {
  await saveModuleSettings(moduleId.value, settingsValues.value)
}
```

---

## 🔄 7. Горячее обновление настроек (Hot Reload & WebSockets)

При сохранении настроек через REST API (`save_module_settings`) ядро NMS WebUI автоматически вызывает функцию утилиты `notify_settings_changed(module_id)`.

```python
# backend/core/plugin/registry.py
def save_webui_settings(update: dict[str, Any]) -> None:
    data = _load_raw_settings()
    # ... обновление словаря ...
    _save_raw_settings(data)

    for mid in update_mods:
        notify_settings_changed(mid) # Рассылка системных уведомлений
```

### 1. Подписка на фронтенде (WebSocket)
Компоненты веб-интерфейса подписываются на событие `module_settings_changed` для моментального перерисовывания статусов:

```typescript
import { onEvent } from '@/core/events'

onEvent('module_settings_changed', (payload) => {
  console.log(`Настройки модуля ${payload.module_id} были изменены`)
  // Повторная загрузка актуальных данных
  loadSettings()
})
```

### 2. Подписка и Hot Reload на Python бекенде
Для того чтобы модуль реагировал на изменение настроек без перезапуска веб-сервера, создается реактивный слушатель или сервис с фоновым циклом:

```python
# backend/modules/sensor_monitor/service.py
import asyncio
import logging
from backend.core.plugin.registry import get_module_settings
from backend.core.events import register_event_listener

logger = logging.getLogger("nms.plugin.sensor_monitor")

class SensorMonitorService:
    def __init__(self, module_id: str):
        self.module_id = module_id
        self.running = False
        self.load_config()

    def load_config(self):
        """Считывает свежие настройки из базы данных."""
        cfg = get_module_settings(self.module_id)
        self.poll_interval = cfg.get("poll_interval", 30)
        self.interface = cfg.get("interface", "eth0")
        logger.info(f"Обновлена конфигурация сервиса: interval={self.poll_interval}, iface={self.interface}")

    async def start(self):
        self.running = True
        # Регистрируем подписчик на изменение настроек
        register_event_listener("module_settings_changed", self._on_settings_changed)

        while self.running:
            logger.debug(f"Опрос интерфейса {self.interface} с интервалом {self.poll_interval}s...")
            await asyncio.sleep(self.poll_interval)

    def _on_settings_changed(self, event_data: dict):
        if event_data.get("module_id") == self.module_id:
            logger.info("Получен сигнал об изменении настроек. Перезагрузка конфигурации...")
            self.load_config()
```

---

## 🔒 8. Безопасность и обработка секретных данных

При работе с чувствительными данными (пароли к БД, API-ключи, токены доступа) необходимо придерживаться следующих правил безопасности:

1. **Маскирование в UI**: поля с `format: "password"` или содержащие ключевые слова `password`, `secret`, `api_key` автоматически рендерятся фронтендом с `type="password"`.
2. **Изоляция в логах**: никогда не выводите весь словарь `get_module_settings()` в логи формата `logger.info(settings)`. Логируйте только неконфиденциальные параметры (например, `poll_interval`).
3. **Разграничение прав RBAC**:
   - `settings.view` — право только на чтение схемы и текущих значений.
   - `settings.edit` — право на сохранение новых настроек.

---

## 🚀 9. Полный практический пример модуля `sensor_monitor`

Ниже приведен готовый комплект файлов для создания модуля с динамическими настройками и hot-reload.

### `manifest.yaml`
```yaml
id: "sensor_monitor"
name: "Сенсорный монитор"
version: "1.0.0"
description: "Модуль опроса аппаратных датчиков с динамическими настройками"
author: "NMS Developer Team"

entrypoints:
  main: "backend.modules.sensor_monitor.main:SensorModule"
  settings: "backend.modules.sensor_monitor.settings:get_dynamic_schema"
```

### `settings.py` (Динамическая схема)
```python
from typing import Any
import psutil
from backend.core.plugin.context import ModuleContext

def get_dynamic_schema(ctx: ModuleContext) -> dict[str, Any]:
    ifaces = list(psutil.net_if_addrs().keys()) or ["eth0"]

    return {
        "type": "object",
        "required": ["poll_interval", "interface"],
        "properties": {
            "interface": {
                "type": "string",
                "title": "Сетевой адаптер",
                "enum": ifaces,
                "default": ifaces[0]
            },
            "poll_interval": {
                "type": "integer",
                "title": "Частота опроса (сек)",
                "default": 30,
                "minimum": 5,
                "maximum": 600
            },
            "api_key": {
                "type": "string",
                "format": "password",
                "title": "Ключ доступа API"
            }
        }
    }
```

### `main.py` (Основной класс модуля)
```python
import asyncio
from backend.core.plugin.context import ModuleContext
from backend.core.plugin.registry import get_module_settings
from backend.core.events import register_event_listener

class SensorModule:
    def __init__(self, context: ModuleContext):
        self.ctx = context
        self.logger = context.logger
        self.task: asyncio.Task | None = None
        self.poll_interval = 30
        self.interface = "eth0"

    def apply_settings(self):
        settings = get_module_settings(self.ctx.module_id)
        self.poll_interval = settings.get("poll_interval", 30)
        self.interface = settings.get("interface", "eth0")
        self.logger.info("Применены настройки: interface=%s, interval=%d", self.interface, self.poll_interval)

    async def on_enable(self):
        self.apply_settings()
        register_event_listener("module_settings_changed", self._on_settings_changed)
        self.task = asyncio.create_task(self._worker_loop())
        self.logger.info("Модуль SensorModule успешно запущен.")

    async def _worker_loop(self):
        try:
            while True:
                self.logger.debug("Опрос датчиков через %s...", self.interface)
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            pass

    def _on_settings_changed(self, data: dict):
        if data.get("module_id") == self.ctx.module_id:
            self.logger.info("Обнаружено изменение настроек модуля в реальном времени.")
            self.apply_settings()

    async def on_disable(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        self.logger.info("Модуль SensorModule остановлен.")
```
