# 📦 Module SDK — единая точка входа для разработки модулей

Раньше публичное API платформы было разбросано по разным местам:
`backend.core.plugin.context`, `backend.modules.base`, `backend.core.plugin.widgets`,
`backend.core.plugin.registry`, `backend.core.auth`, `backend.core.exceptions` и т.д.
Теперь всё, что нужно разработчику модуля, доступно из двух фасадов:

- **Backend**: `backend.core.sdk`
- **Frontend**: `@/modules/sdk`

Старые пути импорта продолжают работать (обратная совместимость), но для нового
кода рекомендуется использовать SDK.

---

## 🐍 Backend: `backend.core.sdk`

```python
from backend.core.sdk import (
    # Жизненный цикл модуля
    BaseModule, BaseSubmodule, ModuleContext, ModuleStatusResponse,
    # Виджеты
    WidgetDataResponse, WidgetMetric, WidgetAction, WidgetStatus, WidgetType,
    # RBAC
    CurrentUser, require_permission,
    # DI-хелперы
    get_module_instance, get_module_context,
    # Исключения
    NMSError, NotFoundError, ValidationError, PermissionDeniedError,
    # Локализация, события, уведомления
    tr, register_module_messages, broadcaster, create_notification,
)
```

### Состав SDK

| Группа | Экспорты |
|---|---|
| Контекст и базовые классы | `ModuleContext`, `BaseModule`, `BaseSubmodule`, `ModuleStatusResponse` |
| Виджеты | `WidgetStatus`, `WidgetType`, `WidgetMetric`, `WidgetAction`, `WidgetDataResponse` |
| FastAPI DI | `get_module_instance`, `get_module_context` |
| Реестр модулей | `get_instance`, `get_manifest`, `is_module_active`, `is_module_enabled`, `get_module_settings`, `save_module_settings` |
| RBAC | `CurrentUser`, `require_permission` |
| Исключения | `NMSError`, `NMSModuleNotFoundError`, `ModuleDisabledError`, `AuthenticationError`, `PermissionDeniedError`, `NotFoundError`, `ValidationError`, `RateLimitExceededError`, `register_exception` |
| Локализация | `tr`, `register_module_messages` |
| События и уведомления | `broadcaster`, `notify_settings_changed`, `create_notification` |
| Логи | `BaseLogProvider`, `LocalFileLogProvider`, `RemoteHTTPLogProvider`, `log_provider_registry` |
| Системные настройки | `get_system_setting`, `set_system_setting` |

### Новые удобные методы `ModuleContext`

`ModuleContext` теперь покрывает типовые задачи модуля без дополнительных импортов:

```python
class MyModule(BaseModule):
    def init(self) -> None:
        # Настройки модуля (defaults + сохраненные значения)
        settings = self.context.get_settings()
        self.context.save_settings({"poll_interval": 30})

        # WebSocket-событие всем клиентам (или адресно по user_id)
        self.context.broadcast("device_state_changed", {"device_id": "d1", "online": True})

        # Локализация по ключу
        title = self.context.tr("myModuleTitle")

        # Уже существовавшие возможности:
        self.context.logger.info("init")            # изолированный логгер
        self.context.create_table("devices", {...})  # таблица mod_<id>_devices
        self.context.notify("Title", "Message")      # системное уведомление
        self.context.get_data_dir()                  # песочница файлов
```

---

## 🌐 Frontend: `@/modules/sdk`

```typescript
// Типы
import type {
    ModuleManifest, RouteDefinition, MenuConfig,
    WidgetProps, WidgetEmits, WidgetData, WidgetAction, ModuleWidget,
} from '@/modules/sdk'

// Runtime-хелперы
import {
    http, t,
    registerWidgetComponent, registerViewComponent,
    fetchWidgetData, executeWidgetAction, loadModuleLocales,
} from '@/modules/sdk'
```

### Состав SDK

| Группа | Экспорты |
|---|---|
| Типы модульной системы | `ModuleManifest`, `RouteDefinition`, `RouteMeta`, `MenuItem`, `MenuConfig`, `ModuleRegistry`, `SidebarGroup`, `EnableSchemaNode`, `EnableSchemaResponse` |
| Контракты виджетов | `WidgetStatus`, `WidgetType`, `WidgetMetric`, `WidgetAction`, `WidgetData`, `WidgetPermissions`, `ModuleWidget`, `WidgetProps`, `WidgetEmits` |
| Хелперы виджетов | `activeWidgets`, `loadModuleWidgets`, `fetchWidgetData`, `executeWidgetAction` |
| Регистрация компонентов | `registerViewComponent`, `getViewComponent`, `registerWidgetComponent`, `getWidgetComponentLoader` |
| Маршруты и меню | `getModuleRoutes`, `getSidebarGroups`, `getFooterItems` |
| HTTP-клиент и API ядра | `http`, `fetchModules`, `fetchLoadedModules`, `fetchModuleViews`, `fetchModuleWidgets` |
| Локализация | `t`, `registerModuleTranslations`, `loadModuleLocales` |

### Пример Vue-виджета через SDK

```vue
<script setup lang="ts">
import type { WidgetProps, WidgetEmits } from '@/modules/sdk'

defineProps<WidgetProps>()
defineEmits<WidgetEmits>()
</script>
```

---

## Миграция существующих модулей

Замены эквивалентны один-в-один, ничего кроме пути импорта менять не нужно:

| Было | Стало |
|---|---|
| `from backend.core.plugin.context import ModuleContext` | `from backend.core.sdk import ModuleContext` |
| `from backend.modules.base import BaseModule` | `from backend.core.sdk import BaseModule` |
| `from backend.core.plugin.widgets import WidgetDataResponse` | `from backend.core.sdk import WidgetDataResponse` |
| `from backend.core.auth import require_permission` | `from backend.core.sdk import require_permission` |
| `import type { WidgetProps } from '@/modules/widgets'` | `import type { WidgetProps } from '@/modules/sdk'` |
| `import { http } from '@/core/api'` | `import { http } from '@/modules/sdk'` |
