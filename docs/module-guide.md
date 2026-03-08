# Руководство по созданию модулей NMS-WebUI

Это руководство описывает процесс создания новых функциональных модулей (плагинов) для системы NMS-WebUI. Каждый модуль является "плагином", который может содержать бэкенд-логику, API-эндпоинты и описание интерфейса для фронтенда.

---

## 🏗 Структура модуля

Все новые модули должны располагаться в директории `backend/modules/<module_id>/`.

Типовая структура:
```text
backend/modules/<module_id>/
├── manifest.yaml      # ⚠️ Основной файл: описание модуля, путей и UI
├── __init__.py        # Точка входа для инициализации
├── module.py          # Основной класс модуля (наследует BaseModule)
├── api.py             # Определение роутов FastAPI
├── services.py        # Бизнес-логика модуля
└── models.py          # Pydantic и DB модели
```

---

## 📜 1. Создание manifest.yaml

`manifest.yaml` — это "единый источник истины" для системы. Он используется бэкендом для загрузки логики и фронтендом для построения меню и роутов.

Пример манифеста (`backend/modules/notifications/manifest.yaml`):

```yaml
id: notifications              # kebab-case, уникальный ID проекта
name: Уведомления              # Читаемое имя для интерфейса
version: 1.0.0                 # Семантическое версионирование
description: Система алертов   # Краткое описание функционала
enabled_by_default: true       # Активация при первой установке
type: feature                  # Тип: system | feature | driver

deps:                          # Список ID модулей, необходимых для работы
  - database

entrypoints:                   # Точки интеграции с ядром системы
  factory: "backend.modules.notifications:create_module" # Python-путь к инициализации
  router: "backend.modules.notifications.api:router"     # Подключение API роутера
  settings: "backend.modules.notifications.config:schema" # Функция схемы настроек

routes:                        # Регистрация страниц в навигации фронтенда
  - path: "/notifications"
    name: "notifications-index"
    meta:
      title: "Журнал уведомлений"
      icon: "bell"             # Имя иконки из библиотеки
      group: "Система"         # Группа для хлебных крошек/заголовков
      requires_auth: true      # Проверка авторизации

config_schema:                 # JSON Schema для автоматической генерации форм
  type: object
  properties:
    host:                     # Если в имени есть "host" или "ip", будет авто-валидация IP
      type: string
      default: "127.0.0.1"
      group: "Сеть"           # Группировка полей в UI (опционально)
    scan_port:
      type: integer
      minimum: 1
      maximum: 65535
      default: 8000
      group: "Сканирование"
    email_enabled:
      type: boolean
      default: true
      group: "Уведомления"

menu:                          # Отображение в глобальной навигации
  location: sidebar            # Место: sidebar или footer
  group: "Мониторинг"          # Группировка в меню
  items:
    - path: "/notifications"
      label: "События"
      icon: "bell"

hooks: {}                      # Жизненный цикл (on_enable, on_disable)
assets:                        # Резервация системных путей
  cache_dirs: ["cache"]
  data_dirs: ["data"]
```

---

## 🐍 2. Реализация логики (Бэкенд)

### Класс модуля (`module.py`)

Модуль должен наследоваться от `BaseModule` и реализовывать жизненный цикл.

```python
from backend.modules.base import BaseModule
from typing import Any

class NotificationsModule(BaseModule):
    def init(self) -> None:
        # Регистрация ресурсов, проверка коннектов
        print(f"Инициализация {self.context.id}")

    def start(self) -> None:
        # Запуск фоновых задач, подписки
        pass

    def stop(self) -> None:
        # Корректное завершение работы
        pass

    def get_status(self) -> dict[str, Any]:
        return {"active": True, "processed_count": 42}
```

### Точка входа (`__init__.py`)

Функция `create_module` используется системным загрузчиком:

```python
from backend.core.plugin.context import ModuleContext
from .module import NotificationsModule

def create_module(ctx: ModuleContext) -> NotificationsModule:
    return NotificationsModule(ctx)
```

### API (`api.py`)

Используйте обычные роутеры FastAPI. Они будут автоматически подключены (mounted) с префиксом `/api/v1/m/<module_id>`.

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_notifications():
    return [{"id": 1, "text": "Система запущена"}]
```

### Работа с настройками (Settings)

Настройки модулей хранятся в едином файле `webui_settings.json`. Для доступа к ним используйте методы реестра:

```python
from backend.core.plugin.registry import get_module_settings, save_module_settings

# Чтение настроек
settings = get_module_settings("notifications")
is_enabled = settings.get("email_enabled", True)

# Сохранение (автоматически обновляет webui_settings.json)
save_module_settings("notifications", {"email_enabled": False})
```

> [!NOTE]
> Все изменения настроек через реестр мгновенно сохраняются на диск. Фронтенд автоматически получает эти обновления.

## 🌿 3. Субмодули (Submodules)

Субмодули предназначены для добавления **независимого** функционала, который расширяет возможности базового модуля, но не реализует его основные функции напрямую.

- **Расположение**: `backend/modules/<parent_id>/submodules/<sub_id>/`
- **Назначение**: Безопасное расширение системы функциями, которые можно отключить в любой момент без вреда для стабильности ядра.

### 📜 Манифест субмодуля (`manifest.yaml`)
Структура идентична основному модулю, но включает обязательное поле `parent`.

```yaml
id: playlist                   # ID субмодуля (уникально внутри родителя)
parent: astra                  # ID родителя (например, astra)
name: Плейлисты                # Имя субмодуля
version: 1.0.0
description: Управление очередью вещания

deps: [astra, database]        # Может зависеть от родителя и других модулей

entrypoints: 
  factory: "backend.modules.astra.submodules.playlist:init"
  router: "backend.modules.astra.submodules.playlist.api:router"

# Субмодуль может определять свои уникальные страницы и пункты меню
routes:
  - path: "/astra/playlists"
    name: "astra-playlists"
    meta:
      title: "Плейлисты Astra"
      icon: "list-video"

menu:
  location: sidebar
  group: "Управление Astra"
  items:
    - path: "/astra/playlists"
      label: "Плейлисты"
```

### ✨ Контроль и изоляция:
1. **Безопасность**: Добавление функционала субмодулем не требует изменения кода родителя.
2. **Каскад**: Если базовый модуль (например, `astra`) отключен, все его субмодули деактивируются автоматически.
3. **Изоляция**: Субмодуль имеет собственный API префикс и конфигурацию, что исключает конфликты.
4. **Принцип "Interfaces Only"**: Субмодули не должны импортировать внутренние компоненты ядра модуля напрямую. Все взаимодействия должны идти через публичные контракты и базовые классы (например, пакет `core.interfaces`).
5. **Централизованная очистка**: Субмодули не должны самостоятельно удалять временные файлы. Бэкенд должен реализовывать метод `get_temp_dirs()`, чтобы основной модуль мог корректно очистить ресурсы после завершения задачи.

---

## 🏗 Рекомендации для модуля Stream (Пример архитектуры)

При разработке бэкендов стриминга следуйте паттерну:
1. **Наследование**: Используйте `BaseStreamSession` (для простого проксирования) или `BufferedSession` (для HLS/HTTP_TS с дисковым буфером).
2. **Импорты**: 
   ```python
   from backend.modules.stream.core.interfaces import (
       IStreamBackend, StreamTask, BufferedSession, ...
   )
   ```
3. **Очистка**: Передавайте пути к временным папкам через `get_temp_dirs(task_id)`.

---

---

## 🎨 4. Фронтенд

Фронтенд в NMS-WebUI работает динамически. Вам **не нужно** вручную править `router.ts` в ядре фронтенда.

Система автоматически:
1. Запрашивает манифест через `/api/modules`.
2. Регистрирует пути, указанные в блоке `routes:`.
3. Отрисовывает элементы меню в сайдбаре из блока `menu:`.

Для отрисовки конкретной страницы модуля используется универсальный компонент `ModuleView.vue`. 

### Авто-генерация настроек
Если для модуля определена `config_schema`, страница настроек будет сгенерирована автоматически:
- **Группировка**: Используйте атрибут `group` в манифесте, чтобы разделить длинные формы на логические блоки.
- **Валидация**: 
    - Поля с `format: "ipv4"` или содержащие в названии `host`/`ip` автоматически проверяются на корректность IP-адреса.
    - Целые числа проверяются по `minimum`/`maximum`.
- **Автосохранение**: Любое изменение в форме настроек (через компонент `Settings.vue`) сохраняется автоматически (debounce 750ms).

---

## 🔗 5. Общие правила взаимодействия

Для того чтобы модули могли эффективно работать вместе, соблюдаются следующие правила:

1. **Строгий контроль зависимостей (Fail-fast)**: 
   - Модуль **не будет загружен**, если хотя бы одна зависимость из списка `deps` (в `manifest.yaml`) отсутствует в системе или отключена в настройках `webui_settings.json`.
   - В случае нехватки зависимости в системный лог выводится предупреждение (`WARNING`).
   - Для субмодулей отключение родителя (`parent`) является нормой, поэтому субмодули просто тихо игнорируются (`INFO`).
2. **Взаймодествия между элементами прилодения**:  
   - Приложение → Модуль → Субмодуль: не знают друг о друге до момента регистрации.
   - Обратно: субмодуль знает о контракте модуля и базового приложения, модуль знает о базовом приложении
3. **Shared Service Registry**: Модули регистрируют свои публичные сервисы в ядре. Другие модули могут получать доступ к этим сервисам, не импортируя код модуля напрямую (Loose Coupling).
4. **Celery Bus**: Все тяжелые или межмодульные задания передаются через очередь задач Celery.
5. **Frontend Dynamic Load**: Фронтенд ничего не знает о модулях до момента загрузки. Все меню и роуты строятся динамически на основе манифестов.

---

##  Дорожная карта (Roadmap)
1. **CLI Scaffold**: Команда `./run_webui.sh make-module` для мгновенного создания структуры по шаблону.
2. **Shared UI Kit**: Пакет визуальных компонентов для единообразия всех модулей.
3. **Module Migrations**: Автоматическое применение миграций БД для каждого модуля при его активации.
4. **Scaffold Script**: Используйте `/scripts/scaffold.py notifications` для быстрой генерации шаблона модуля (будет реализовано).
5. **Валидация**: Запустите `/scripts/validate.py`, чтобы проверить `manifest.yaml` на ошибки перед запуском.