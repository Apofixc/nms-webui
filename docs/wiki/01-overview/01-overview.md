# 🚀 Обзор системы и архитектурный каркас NMS WebUI

---

## 📌 Назначение платформы

**NMS WebUI** (Network Management System Web Interface) — это модульная высокопроизводительная платформа для мониторинга, управления и визуализации распределенной сетевой инфраструктуры и IoT устройств.

Платформа спроектирована по принципу **Plug-and-Play**: функциональные модули (драйверы устройств, подсистемы мониторинга, аналитические виджеты) подключаются динамически во время выполнения без пересборки ядра или остановки сервиса.

---

## 🏗 Архитектурные принципы

1. **Zero External DB & Worker Dependencies**:
   - Работа от встроенного **SQLite 3** в режиме **WAL (Write-Ahead Logging)** со встроенной системой файловых миграций (`backend/core/migrations/`).
   - Нулевые сторонние БД-демоны и брокеры очередей (без PostgreSQL, Redis, MySQL или Celery).
2. **Динамический загрузчик модулей**:
   - Сканирование манифестов `manifest.yaml`, Pydantic-валидация и построение графа зависимостей с топологической сортировкой.
3. **In-Browser SFC Compilation**:
   - Пользовательские Vue 3 SFC (`.vue`) компоненты виджетов и представлений компилируются прямо в браузере клиента с помощью `vue3-sfc-loader`.
4. **Строгая безопасность, RBAC и MFA**:
   - Ролевая модель доступа, дихотомия Access (30m) & Refresh (`httpOnly` cookie) токенов с одноразовой ротацией, защита от подбора паролей (Sliding Window Rate Limiting), двухфакторная аутентификация TOTP (RFC 6238) с 8 одноразовыми Recovery-кодами и Журнал аудита.
5. **Наблюдаемость и Контейнеризация**:
   - Prometheus-метрики на `/metrics`, пробы здоровья `/health/live` и `/health/ready`, сквозной `X-Request-ID` заголовок, готовые `Dockerfile` и `docker-compose.yml`.
6. **Подсистема событий реального времени**:
   - Транспорт на базе **WebSockets** (`/api/v1/events/ws`) для мгновенного обновления виджетов и доставки системных уведомлений.

---

## 📂 Дерево каталогов проекта

```
/opt/nms-webui/
├── backend/                           # Бэкенд на FastAPI (Python 3.11+)
│   ├── core/                          # Системное ядро платформы
│   │   ├── migrations/                # Движок миграций схемы SQLite (0001_initial, 0002_...)
│   │   ├── plugin/                    # Загрузчик, реестр и контекст модулей
│   │   ├── app.py                     # Фабрика create_app() с мидлварями и /api/v1
│   │   ├── auth.py                    # Access/Refresh токены, RBAC, Recovery-коды
│   │   ├── crypto.py                  # At-Rest шифрование AES-256-GCM
│   │   ├── database.py                # Инициализация SQLite WAL (nms.db)
│   │   ├── rate_limiter.py            # In-Memory Sliding Window Rate Limiter
│   │   ├── metrics.py                 # Prometheus метрики (http_requests, active_sessions)
│   │   ├── backup.py                  # Атомарные бэкапы SQLite с ротацией
│   │   ├── pagination.py              # Единая модель пагинации PaginatedResponse[T]
│   │   ├── events.py                  # WebSockets менеджер и рассыльщик событий
│   │   ├── notifications_api.py       # Подсистема уведомлений
│   │   └── system_api.py              # Системный REST API и движок Вики
│   ├── modules/                       # Подключаемые динамические модули
│   └── main.py                        # Точка входа Uvicorn
├── frontend/                          # Фронтенд на Vue 3 + Vite 5
│   └── src/
│       ├── core/                      # Ядро (Pinia, Axios, Vue Router, i18n)
│       └── views/                     # Представления (Dashboard, Wiki, Settings)
├── data/                              # База данных SQLite (nms.db) и резервные копии (backups/)
├── docs/                              # Файлы документации и статей Вики
├── Dockerfile                         # Multi-stage Docker сборка
├── docker-compose.yml                 # Контейнеризированный запуск NMS WebUI
└── run_webui.sh                       # Единый скрипт управления платформой
```
