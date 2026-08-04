# 🏗 Ядро и Архитектурный Каркас NMS WebUI

---

## 🏛 Структура каталогов и компонентное деление

Система NMS WebUI спроектирована по схеме с графически изолированным бэкендом и фронтендом. Динамические модули (плагины) располагаются в строго отведенных директориях и подключаются автоматически без модификации файлов ядра.

```
/opt/nms-webui/
├── backend/                           # Бэкенд на FastAPI (Python 3.10+)
│   ├── core/                          # Системное ядро платформы
│   │   ├── plugin/                    # Менеджер и реестр плагинов
│   │   │   ├── manifest.py            # Pydantic-схемы ModuleManifest
│   │   │   ├── loader.py              # Сканер, топологический сортировщик и загрузчик
│   │   │   ├── registry.py            # Потокобезопасный реестр инстансов и ошибок
│   │   │   ├── resolver.py            # Разрешение графа зависимостей (toposort)
│   │   │   ├── context.py             # Объект ModuleContext для передачи в модули
│   │   │   ├── widgets.py             # Схемы и реестр виджетов бэкенда
│   │   │   └── api.py                 # REST API управления модулями (/api/modules)
│   │   ├── app.py                     # Фабрика create_app() и lifespan (startup/shutdown)
│   │   ├── auth.py                    # HMAC-SHA256 JWT, сессии, IP-вайтлисты и RBAC
│   │   ├── users_api.py               # REST API пользователей, ролей, 2FA/MFA и настроек
│   │   ├── system_api.py              # REST API логов, бэкапов, healthcheck и вики
│   │   ├── database.py                # Инициализация SQLite WAL (nms.db) и миграции
│   │   ├── events.py                  # EventBroadcaster (SSE) и ConnectionManager (WS)
│   │   ├── mfa.py                     # Pure-Python RFC 6238 TOTP и SVG QR генератор
│   │   ├── i18n.py                    # Движок мультиязычности и форматирования ошибок
│   │   ├── log_providers.py           # Провайдеры чтения локальных и удаленных логов
│   │   └── audit.py                   # Подсистема журналирования событий безопасности
│   ├── modules/                       # Каталог динамических бэкенд-модулей
│   │   └── tuya/                      # Пример модуля драйвера Tuya IoT
│   │       ├── manifest.yaml          # Pydantic-манифест модуля
│   │       ├── module.py              # Фабрика класса модуля (init/start/stop)
│   │       ├── api.py                 # REST API роутеры модуля
│   │       └── storage.py             # Хранилище состояния устройства
│   ├── scripts/                       # Вспомогательные скрипты (reset_root.py)
│   └── main.py                        # Точка входа Uvicorn / FastAPI
├── frontend/                          # Фронтенд на Vue 3 + Vite 5 (TypeScript)
│   ├── src/
│   │   ├── core/                      # Ядро фронтенда
│   │   │   ├── api.ts                 # HTTP-клиент Axios с перехватчиками токенов
│   │   │   ├── auth.ts                # Хранилище сессии и проверка прав (hasPermission)
│   │   │   ├── store.ts               # Глобальное состояние Pinia
│   │   │   ├── vueSfcLoader.ts        # In-Browser SFC компилятор компонентов .vue
│   │   │   ├── i18n.ts                # Реактивный движок локализации
│   │   │   └── router.ts              # Vue Router с динамическими роутами плагинов
│   │   ├── modules/                   # Реестр фронтенд-модулей
│   │   │   ├── registry.ts            # Динамическая загрузка роутов и локализаций из API
│   │   │   ├── loader.ts              # Менеджер динамических импортов
│   │   │   ├── widgets.ts             # Интерфейсы виджетов и выполнение действий
│   │   │   └── tuya/                  # Фронтенд компоненты модуля Tuya
│   │   ├── components/                # Базовые UI компоненты
│   │   │   ├── common/
│   │   │   │   └── WidgetRenderer.vue # Интерактивный рендерер дашбордов
│   │   │   └── layout/                # Шапка, боковая панель (Sidebar), футтер
│   │   └── views/                     # Представления (Dashboard, Settings, ModuleView)
├── data/                              # Хранилище SQLite базы данных (nms.db)
├── docs/                              # Документация и статьи Вики
└── run_webui.sh                       # Единый исполняемый скрипт управления
```

---

## 🔄 Жизненный цикл Бэкенда (Backend Lifecycle)

Инициализация бэкенда выполняется в двух ключевых этапах:

```svg
<svg viewBox="0 0 760 300" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g-step" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
  </defs>

  <!-- Step 1 -->
  <rect x="20" y="20" width="220" height="110" rx="10" fill="url(#g-step)" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="130" y="45" fill="#60a5fa" font-size="12" font-weight="bold" text-anchor="middle" font-family="sans-serif">1. create_app()</text>
  <text x="30" y="70" fill="#94a3b8" font-size="10" font-family="sans-serif">• setup_logging()</text>
  <text x="30" y="88" fill="#94a3b8" font-size="10" font-family="sans-serif">• register_exception_handlers()</text>
  <text x="30" y="106" fill="#94a3b8" font-size="10" font-family="sans-serif">• include system routers</text>

  <line x1="240" y1="75" x2="270" y2="75" stroke="#3b82f6" stroke-width="2"/>

  <!-- Step 2 -->
  <rect x="270" y="20" width="220" height="110" rx="10" fill="url(#g-step)" stroke="#8b5cf6" stroke-width="1.5"/>
  <text x="380" y="45" fill="#c084fc" font-size="12" font-weight="bold" text-anchor="middle" font-family="sans-serif">2. load_all_modules()</text>
  <text x="280" y="70" fill="#94a3b8" font-size="10" font-family="sans-serif">• discover_manifests()</text>
  <text x="280" y="88" fill="#94a3b8" font-size="10" font-family="sans-serif">• toposort_modules()</text>
  <text x="280" y="106" fill="#94a3b8" font-size="10" font-family="sans-serif">• check min/max_core_version</text>

  <line x1="490" y1="75" x2="520" y2="75" stroke="#8b5cf6" stroke-width="2"/>

  <!-- Step 3 -->
  <rect x="520" y="20" width="220" height="110" rx="10" fill="url(#g-step)" stroke="#ec4899" stroke-width="1.5"/>
  <text x="630" y="45" fill="#f472b6" font-size="12" font-weight="bold" text-anchor="middle" font-family="sans-serif">3. Module Entrypoints</text>
  <text x="530" y="70" fill="#94a3b8" font-size="10" font-family="sans-serif">• run install.sh hook</text>
  <text x="530" y="88" fill="#94a3b8" font-size="10" font-family="sans-serif">• load factory &amp; router</text>
  <text x="530" y="106" fill="#94a3b8" font-size="10" font-family="sans-serif">• call instance.init()</text>

  <!-- Down Line -->
  <line x1="630" y1="130" x2="630" y2="170" stroke="#ec4899" stroke-width="2"/>

  <!-- Step 4 -->
  <rect x="270" y="170" width="470" height="100" rx="10" fill="url(#g-step)" stroke="#10b981" stroke-width="1.5"/>
  <text x="505" y="195" fill="#34d399" font-size="12" font-weight="bold" text-anchor="middle" font-family="sans-serif">4. Lifespan Startup Context (app.py)</text>
  <text x="285" y="220" fill="#94a3b8" font-size="10" font-family="sans-serif">• init_db() — Миграции SQLite WAL | load_instances() — Чтение instances.yaml</text>
  <text x="285" y="238" fill="#94a3b8" font-size="10" font-family="sans-serif">• load_remote_sources_from_db() — Регистрация удаленных серверов логов</text>
  <text x="285" y="256" fill="#94a3b8" font-size="10" font-family="sans-serif">• inst.start() — Запуск фоновых процессов активных модулей</text>
</svg>
```

### Последовательность выполнения `loader.py`:
1. **Обнаружение манифестов (`discover_manifests`)**:
   - Сканируется каталоги `backend/modules/*/manifest.yaml` и их вложенные субмодули `backend/modules/*/submodules/*/manifest.yaml`.
   - Манифесты парсятся и валидируются Pydantic-моделью `ModuleManifest`.
2. **Топологическая сортировка (`toposort_modules`)**:
   - Строится граф зависимостей модулей (`deps`). Модули сортируются так, чтобы зависимости загружались раньше зависимых модулей. При циклических зависимостях генерируется ошибка.
3. **Проверка версий ядра (`is_version_compatible`)**:
   - Сравнивается текущая версия ядра (`CORE_VERSION = "1.0.0"`) с требованиями манифеста `min_core_version` и `max_core_version`. При несовместимости модуль блокируется.
4. **Выполнение Bash-хука установки**:
   - Запускается скрипт `scripts/install.sh` с передачей переменных окружения (`MODULE_ID`, `MODULE_ROOT`, `MODULE_DATA_DIR`, `PROJECT_ROOT`).
5. **Загрузка точек входа (Entrypoints)**:
   - **`factory`**: Вызывается функция-фабрика, создающая экземпляр класса модуля. Вызывается его метод `init()`, регистрируется провайдер логов `get_log_provider()`.
   - **`router`**: Загружается APIRouter и монтируется в FastAPI приложение (`app.include_router`).
   - **`services`**: Вызываются сервисные регистраторы.
   - **`settings`**: Схема динамических настроек объединяется с `config_schema`.

---

## 🎨 Архитектура Фронтенда (Frontend Architecture)

Фронтенд NMS WebUI реализует двухуровневую загрузку модулей:

### 1. Инициализация реестра модулей (`initModulesRegistry()`):
- Запрашивается список доступных и активных модулей из эндпоинта `/api/modules`.
- Запрашиваются роуты и представления для каждого модуля через `/api/modules/{id}/views`.
- Автоматически загружаются файлы переходов и локализаций (`loadModuleLocales`) с бэкенда для языка интерфейса.
- Формируется динамическое меню для боковой панели (`sidebar`) и футтера (`footer`).

### 2. In-Browser Vue SFC Compilation (`loadRemoteVueSFC`):
- Если для роута не найден статический сборный бандл Vue, срабатывает перехватчик `getModuleRoutes()`.
- Браузер обращается к бэкенду и скачивает исходный файл `.vue` из бэкенд-модуля.
- Модуль `vueSfcLoader.ts` на лету компилирует шаблон `<template>`, скрипт `<script setup>` и стили `<style scoped>` прямо в браузере клиента.
- **Результат**: Новые UI-страницы подключаются без пересборки проекта через npm/vite!

### 3. Автоматические фолбэк-страницы (`ModuleView.vue`):
- Если модуль не предоставляет кастомный `.vue` файл, фронтенд монтирует универсальную страницу `ModuleView.vue`.
- Она автоматически генерирует форму настроек и элементы управления на основе JSON-схемы `config_schema` из `manifest.yaml`.
