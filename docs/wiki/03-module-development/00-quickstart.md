# 🚀 0. Быстрый старт: Создание собственного модуля

Добро пожаловать в руководство по разработке модулей для **NMS-WebUI**!

Платформа NMS-WebUI построена на принципах **модульности, изоляции и автообнаружения** (Zero Configuration). Каждый модуль — это независимый плагин со своей серверной логикой, API, фронтенд-компонентами, настройками и правами доступа.

Данная статья позволит вам создать первый рабочий модуль всего за **5 минут**, а также служит навигатором по всем глубоким техническим руководствам раздела.

---

## ⚡ Разработка модуля за 5 минут (Hello World)

Структура каждого модуля NMS-WebUI состоит из двух частей:
- **Бэкенд**: `backend/modules/<module_id>/`
- **Фронтенд**: `frontend/src/modules/<module_id>/`

### Шаг 1. Создание структуры папок

Создайте две директории для вашего модуля (замените `my_plugin` на уникальный идентификатор вашего модуля в `snake_case`):

```bash
mkdir -p backend/modules/my_plugin/locales
mkdir -p frontend/src/modules/my_plugin
```

---

### Шаг 2. Манифест модуля (`backend/modules/my_plugin/manifest.yaml`)

Манифест — это единственный источник истины (Single Source of Truth) для системы. Создайте файл `manifest.yaml`:

```yaml
id: my_plugin
name: myPluginTitle
version: 1.0.0
description: myPluginDesc
type: feature
enabled_by_default: true

entrypoints:
  factory: "backend.modules.my_plugin:create_module"
  router: "backend.modules.my_plugin.api:get_router"

routes:
  - path: "/my-plugin"
    name: "my-plugin-index"
    meta:
      title: "My Plugin"
      titleKey: "myPluginTitle"
      icon: "extension"
      requires_auth: true
      permissions:
        - "module.my_plugin.view"

menu:
  location: sidebar
  group: "main"
  items:
    - path: "/my-plugin"
      label: "myPluginTitle"
      icon: "extension"

permissions:
  - id: "module.my_plugin.view"
    name: "perm_my_plugin_view"
    category: "My Plugin"
    description: "Просмотр модуля My Plugin"
```

---

### Шаг 3. Точка входа бэкенда (`backend/modules/my_plugin/__init__.py`)

```python
from backend.core.plugin.context import ModuleContext
from .module import MyPluginModule

def create_module(ctx: ModuleContext) -> MyPluginModule:
    """Фабрика инициализации модуля."""
    return MyPluginModule(ctx)
```

---

### Шаг 4. Класс жизненного цикла модуля (`backend/modules/my_plugin/module.py`)

```python
from typing import Any
from backend.modules.base import BaseModule

class MyPluginModule(BaseModule):
    """Класс управления жизненным циклом модуля."""

    def init(self) -> None:
        """Инициализация ресурсов при старте системы."""
        self.context.logger.info(f"Модуль {self.manifest.id} инициализирован.")

    def start(self) -> None:
        """Запуск фоновых процессов при необходимости."""
        pass

    def stop(self) -> None:
        """Корректная остановка ресурсов."""
        pass
```

---

### Шаг 5. REST API эндпоинты (`backend/modules/my_plugin/api.py`)

Все эндпоинты модуля автоматически монтируются по префиксу `/api/v1/m/my_plugin`:

```python
from fastapi import APIRouter, Depends
from backend.core.auth import require_permission, CurrentUser

router = APIRouter()

@router.get("/hello")
async def say_hello(user: CurrentUser = Depends(require_permission("module.my_plugin.view"))):
    return {
        "status": "ok",
        "message": f"Привет, {user.username}! Модуль My Plugin успешно работает.",
    }

def get_router() -> APIRouter:
    return router
```

---

### Шаг 6. Файлы локализации (`locales/ru.json` и `locales/en.json`)

Создайте `backend/modules/my_plugin/locales/ru.json`:
```json
{
  "messages": {
    "myPluginTitle": "Мой Модуль",
    "myPluginDesc": "Персональный пользовательский модуль NMS-WebUI"
  }
}
```

Создайте `backend/modules/my_plugin/locales/en.json`:
```json
{
  "messages": {
    "myPluginTitle": "My Plugin",
    "myPluginDesc": "Custom NMS-WebUI module"
  }
}
```

---

### Шаг 7. Фронтенд-страница (`frontend/src/modules/my_plugin/MyPluginView.vue`)

Благодаря автосканированию Vite `import.meta.glob`, компонент автоматически связывается с роутом `my-plugin-index`:

```html
<template>
  <div class="p-6 space-y-4">
    <div class="flex items-center space-x-3">
      <span class="material-symbols-outlined text-primary text-3xl">extension</span>
      <div>
        <h1 class="text-2xl font-bold">{{ t('myPluginTitle') }}</h1>
        <p class="text-sm text-on-surface-variant">{{ t('myPluginDesc') }}</p>
      </div>
    </div>

    <div class="p-4 rounded-lg bg-surface-container border border-outline-variant">
      <p class="text-sm font-medium">Ответ от API модуля:</p>
      <pre class="mt-2 p-3 rounded bg-surface-container-high font-mono text-xs">{{ apiData }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from '@/core/i18n'

const { t } = useI18n()
const apiData = ref<any>('Загрузка...')

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/m/my_plugin/hello')
    apiData.value = await res.json()
  } catch (err) {
    apiData.value = { error: String(err) }
  }
})
</script>
```

---

### Шаг 8. Запуск и проверка!

Перезапустите приложение или запустите в dev-режиме:

```bash
./run_webui.sh dev
```

Система автоматически обнаружит манифест, зарегистрирует модуль, добавит пункт «Мой Модуль» в боковое меню и предоставит API!

---

## 🗺️ Карта руководств по разработке (Roadmap)

Когда ваш базовый модуль работает, используйте подробные статьи нашего раздела для реализации конкретных возможностей:

| Какая задача перед вами стоит? | Куда обратиться |
| :--- | :--- |
| **Структура манифеста и схемы полей** | 📖 [01. Общая информация о манифестах](01-manifests.md) |
| **Жизненный цикл модуля и FastAPI Роутер** | 📖 [02. Создание модулей и API](02-module-creation-and-api.md) |
| **Иерархия модулей и субмодули** | 📖 [03. Иерархия модулей и субмодули](03-submodules-hierarchy.md) |
| **Таблицы в SQLite / SQLAlchemy** | 📖 [04. База данных и хранилище](04-database-and-storage.md) |
| **Пользовательские настройки (JSON Schema)** | 📖 [05. Настройки модулей](05-module-settings.md) |
| **Обработка ошибок и кастомные исключения** | 📖 [06. Исключения и ошибки](06-exceptions.md) |
| **Отправка всплывающих уведомлений** | 📖 [07. Системные уведомления](07-notifications.md) |
| **Логирование и провайдеры логов** | 📖 [08. Логирование и система провайдеров](08-logging.md) |
| **WebSockets и Push-уведомления** | 📖 [09. Использование WebSockets](09-websockets.md) |
| **Разграничение прав доступа (RBAC)** | 📖 [10. Управление доступом и разрешения](10-access-control.md) |
| **Локализация (i18n)** | 📖 [11. Локализация модулей](11-localization.md) |
| **Виджеты на главном Дашборде** | 📖 [12. Разработка виджетов дашборда](12-widgets.md) |
| **Фоновые задачи и хуки запуска** | 📖 [13. Хуки жизненного цикла и фоновые задачи](13-hooks-and-background-tasks.md) |
| **Журнал аудита безопасности и события** | 📖 [14. Журнал аудита и системные события](14-audit-and-security.md) |
| **Автотесты (pytest) и QA** | 📖 [15. Тестирование модулей и автотесты](15-testing-and-qa.md) |
| **Распределенные воркеры Celery** | 📖 [16. Фоновые воркеры и очереди Celery](16-background-workers.md) |

---

## ✅ Чеклист проверки перед релизом модуля

Before передачей модуля в продакшн проверьте:
1. [ ] Файл `manifest.yaml` валиден по Pydantic-модели и содержит корректный `id`.
2. [ ] В `__init__.py` объявлена функция-фабрика `create_module(ctx)`.
3. [ ] В `api.py` функция `get_router()` возвращает роутер FastAPI.
4. [ ] Все эндпоинты защищены через `Depends(require_permission(...))`.
5. [ ] В `locales/ru.json` и `locales/en.json` переведены все строки и названия меню.
6. [ ] Для UI-маршрутов создан соответствующий `.vue` компонент во `frontend/src/modules/<module_id>/`.
7. [ ] Реализована очистка данных в методе `uninstall()` (если модуль создаёт свои таблицы/файлы).
