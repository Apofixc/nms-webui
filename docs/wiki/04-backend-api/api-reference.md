# Справочник REST API

Основной эндпоинт Swagger документации доступен по адресу `http://localhost:8000/docs` при запущенном Backend.

## Системные разделы API

### 🔑 Авторизация и Сессии (`/api/auth`)
- `POST /api/auth/login` — Авторизация пользователя (получение JWT).
- `GET /api/auth/me` — Получение данных текущего пользователя и его прав.
- `POST /api/auth/logout` — Завершение сессии.

### ⚙️ Системное администрирование (`/api/system`)
- `GET /api/system/health` — Статус здоровья БД, диска и модулей.
- `GET /api/system/backup` — Скачивание дампа базы данных `nms.db`.
- `POST /api/system/restore` — Восстановление базы данных из бэкапа.
- `GET /api/system/logs` — Список провайдеров логов.
- `GET /api/system/logs/{log_name}` — Чтение записей лога.
- `GET /api/system/sessions` — Активные сессии пользователей.

### 🧩 Модули (`/api/modules`)
- `GET /api/modules` — Список загруженных модулей.
- `POST /api/modules/scan` — Пересканирование директории модулей.
- `POST /api/modules/install` — Загрузка модуля из zip-архива.
- `DELETE /api/modules/{module_id}` — Удаление модуля.
- `GET /api/modules/widgets` — Реестр доступных виджетов.
