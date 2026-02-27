# Структура проекта NMS WebUI

## Обзор

**NMS WebUI** — это система мониторинга и управления для Cesco Astra (lib-monitor) с современным веб-интерфейсом. Проект построен на модульной архитектуре с бэкендом на Python/FastAPI и фронтендом на Vue.js.

## Корневая структура

```
nms-webui/
├── backend/                    # Python бэкенд (FastAPI)
├── frontend/                   # Vue.js фронтенд
├── instances.yaml             # Конфигурация инстансов Astra
├── run_webui.sh              # Скрипт запуска (бэкенд + фронтенд)
├── telegraf.conf             # Конфигурация Telegraf
├── webui_settings.json       # Настройки веб-интерфейса
├── requirements.txt          # Python зависимости
└── README.md                 # Документация
```

## Backend (`/backend`)

### Основные компоненты
```
backend/
├── main.py                   # Точка входа FastAPI приложения
├── core/                     # Ядро системы
│   ├── config.py            # Конфигурация приложения
│   ├── module_registry.py   # Реестр модулей
│   ├── module_router.py     # Роутер модулей
│   ├── module_state.py      # Управление состоянием модулей
│   ├── ui_manifest.py       # Работа с UI манифестами
│   ├── utils.py             # Утилиты
│   └── webui_settings.py    # Управление настройками
└── modules/                 # Модульная система
```

### Модульная архитектура (`/backend/modules`)

```
modules/
├── base.py                   # Базовые классы модулей
├── astra/                    # Модуль Cesco Astra
│   ├── manifest.yaml        # Манифест модуля
│   ├── api/                 # API эндпоинты
│   └── ...
├── stream/                   # Модуль стриминга
└── __init__.py
```

#### Структура модуля
```
astra/
├── manifest.yaml            # Метаданные и конфигурация
├── api/                     # API роутеры
│   ├── instances.py        # Управление инстансами
│   ├── aggregates.py       # Агрегация данных
│   └── ...
├── submodules/              # Подмодули
│   ├── instances-api/
│   └── channels/
└── __init__.py
```

### Манифест модуля

Каждый модуль содержит `manifest.yaml` с метаданными:
- **id**: Уникальный идентификатор
- **name**: Отображаемое название
- **version**: Версия
- **description**: Описание модуля
- **enabled_by_default**: Включен по умолчанию
- **deps**: Зависимости
- **entrypoints**: Точки входа
- **ui**: Точки входа


- **config_schema**: Схема конфигурации
- **routes**: Маршруты UI
- **menu**: Пункты меню

- **hooks**: Хуки жизненного цикла
- **assets**: Ресурсы модуля

## Frontend (`/frontend`)

### Структура
```
frontend/
├── src/
│   ├── App.vue             # Корневой компонент
│   ├── main.js             # Точка входа
│   ├── api.js              # API клиент
│   ├── modules.js          # Управление модулями
│   ├── style.css           # Глобальные стили
│   ├── components/         # Компоненты
│   ├── router/             # Vue Router
│   └── views/              # Страницы
├── dist/                   # Сборка
├── package.json            # Зависимости
├── vite.config.js          # Конфигурация Vite
└── tailwind.config.js      # Конфигурация Tailwind
```

### Vue.js компоненты
- **App.vue**: Основное приложение с навигацией
- **views/**: Страницы для каждого модуля
- **components/**: Переиспользуемые компоненты
- **router/**: Динамическая маршрутизация на основе манифестов

## API Эндпоинты

### Основные эндпоинты
- `GET /api/modules` — Список модулей и состояние
- `GET /api/modules/config-schema` — Схема конфигурации
- `PUT /api/modules/{module_id}/enabled` — Включение/выключение модуля
- `GET /api/instances` — Инстансы Astra
- `GET /api/instances/{id}/health` — Health инстанса
- `GET /api/aggregate/health` — Общий health
- `GET /api/aggregate/channels` — Каналы всех инстансов
- `GET /api/aggregate/channels/stats` — Статистика

### Прокси эндпоинты (для Astra)
- `DELETE .../channels/kill` — Убить канал
- `POST .../channels` — Создать канал
- `GET .../channels/inputs` — Входы каналов
- `DELETE .../streams/kill` — Убить стрим
- `POST .../streams` — Создать стрим

## Текущие модули

### 1. Cesco Astra (`cesbo-astra`)
- **instances-api**: Управление инстансами
- **channels**: Управление каналами

### 2. Stream (`stream`)
- **playback**: Воспроизведение
- **preview**: Предпросмотр
- **backends**: Бэкенды стриминга/ превью

## Конфигурация

### Инстансы (`instances.yaml`)
```yaml
instances:
  - name: "Main Instance"
    host: "localhost"
    port: 8000
    auth:
      login: "admin"
      password: "password"
```

### Настройки (`webui_settings.json`)
- Тема интерфейса
- Настройки превью
- Конфигурация стриминга
- Параметры метрик

## Запуск

```bash
# Одна командой
./run_webui.sh
```

### Очередь задач
```bash
# Redis + RQ для тяжёлых задач
redis-server &
NMS_REDIS_URL=redis://localhost:6379/0 ./run_worker.sh
```

## Инструменты

Для превью и стриминга требуются:
- **FFmpeg**: Основной инструмент
- **VLC**: Резервный бэкенд
- **GStreamer**: Альтернативный бэкенд
- **TSDuck**: Альтернативный бэкенд
- **Astra4.4.182**: Альтернативный бэкенд
- **pure_preview**: Альтернативный бэкенд
- **pure_proxy**: Альтернативный бэкенд
- **pure_webrtc**: Альтернативный бэкенд

Установка:
```bash
sudo ./scripts/install-stream-tools.sh
```

## Архитектурные особенности

1. **Модульность**: Плагинная система с динамической загрузкой
2. **Манифесты**: Декларативная конфигурация модулей
3. **Изоляция**: Каждый модуль работает в своём контексте
4. **Динамическое UI**: Фронтенд строится на основе бэкенд манифестов
5. **Агрегация**: Объединение данных из нескольких инстансов
6. **Проксирование**: Прямой прокси к Astra API

## Технологический стек

### Backend
- **Python 3.8+**
- **FastAPI**: Веб-фреймворк
- **Pydantic**: Валидация данных
- **PyYAML**: Работа с YAML
- **Redis/RQ**: Очередь задач для работы тяжелых задач

### Frontend
- **Vue.js 3**: Фреймворк
- **Vite**: Сборщик
- **Tailwind CSS**: Стили
- **Vue Router**: Маршрутизация
- **Axios**: HTTP клиент

### Инфраструктура
- **Docker**: Контейнеризация (опционально)
- **Nginx**: Reverse proxy (опционально)
- **Telegraf**: Сбор метрик
- **Grafana**: Визуализация метрик (опционально)
