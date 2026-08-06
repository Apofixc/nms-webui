# ⚙️ Эксплуатация, БД SQLite WAL, Логи и Продакшн-Деплой

---

## 💾 База данных SQLite в режиме WAL

Основным хранилищем данных NMS WebUI является файл базы данных **`data/nms.db`**, работающий под управлением встроенного движка SQLite 3.

### Преимущества режима Write-Ahead Logging (WAL):
- **Параллелизм чтения и записи**: Операции чтения выполняются параллельно с записью из лога WAL и не блокируют друг друга.
- **Высокая скорость отклика**: Критично при высокой частоте сбора телеметрии и активной записи журнала аудита.

Включение режима WAL (выполняется автоматически функцией `get_db_connection()`):
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
```

---

## 📊 Таблицы Базы Данных (Database Schema)

| Таблица | Назначение и ключевые поля |
| :--- | :--- |
| **`users`** | Пользователи системы (`id`, `username`, `full_name`, `email`, `hashed_password`, `role_id`, `is_active`, `token_valid_after`, `must_change_password`, `failed_login_attempts`, `locked_until`, `mfa_enabled`, `mfa_secret`). |
| **`roles`** | Системные и пользовательские роли (`id`, `name`, `description`, `is_system`). |
| **`permissions`** | Реестр доступных прав доступа (`id`, `category`, `name`, `description`, `module_id`). |
| **`role_permissions`** | Таблица связи ролей и прав (`role_id`, `permission_id`). |
| **`audit_logs`** | Журнал фиксации событий безопасности (`id`, `timestamp`, `user_id`, `username`, `action`, `resource`, `details`, `ip_address`). |
| **`system_settings`** | Системные настройки в формате Key-Value (`key`, `value`). |
| **`active_sessions`** | Учет сессий пользователей (`id`, `user_id`, `token_jti`, `ip_address`, `user_agent`, `last_seen`, `is_revoked`). |
| **`remote_log_sources`** | Зарегистрированные удаленные сервера логов (`id`, `name`, `url`, `api_token`). |

---

## 📦 Резервное копирование и Восстановление БД

### 1. Горячий бэкап и восстановление через API:
- **Скачивание бэкапа**: GET-запрос к `/api/system/backup` генерирует моментальный снимок базы с именем `nms-backup-YYYYMMDD-HHMMSS.db`.
- **Восстановление из файла**: POST-запрос к `/api/system/restore` принимает файл `.db`, производит проверку целостности таблицы `users`, сохраняет текущую базу в `nms.db.bak_<timestamp>` и выполняет горячую замену БД без остановки веб-сервера.

### 2. Резервное копирование через CLI (`sqlite3`):
```bash
# Создание горячей резервной копии
sqlite3 data/nms.db ".backup 'data/nms_backup_$(date +%Y%m%d_%H%M%S).db'"

# Проверка целостности файла бэкапа
sqlite3 data/nms_backup.db "PRAGMA integrity_check;"
```

---

## 📝 Инфраструктура Логов (Log Providers)

Подсистема логов построена на базе гибкого реестра `log_provider_registry` и единого абстрактного класса `LogProvider`:

### Типы провайдеров логов:
1. **Локальные файлы логов**:
   - `backend.log`: Основной журнал системных событий FastAPI бэкенда.
   - `mcp-server.log`: Лог MCP-сервисов управления.
2. **Провайдеры логов модулей**:
   - Плагины регистрируют собственные провайдеры через метод `get_log_provider()` (например, логи драйвера Tuya).
3. **Удаленные HTTP-источники логов (`RemoteHTTPLogProvider`)**:
   - Позволяют подключать внешние сервера NMS WebUI по API и централизованно просматривать их логи из единой консоли администратора.

### Стриминг логов в реальном времени:
Для просмотра живых логов консоль фронтенда подключается к WebSocket `/api/system/logs/{log_name}/stream` с поддержкой фильтрации по уровням (`ALL`, `ERROR`, `WARN`, `INFO`) и подстроке поиска.

---

## 🌐 Продакшн-развертывание (Production Deployment)

### 1. Настройка Nginx в качестве Reverse Proxy

Создайте конфигурационный файл `/etc/nginx/sites-available/nms-webui`:

```nginx
server {
    listen 80;
    server_name nms.your-domain.com;

    # Фронтенд (Статика или Vite Dev)
    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Бэкенд REST API
    location /api/ {
        proxy_pass http://127.0.0.1:9000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSockets стриминг
    location /api/events/ws {
        proxy_pass http://127.0.0.1:9000/api/events/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }

    # Информационный эндпоинт событий
    location /api/events {
        proxy_pass http://127.0.0.1:9000/api/events;
        proxy_set_header Host $host;
    }
}
```

### 2. Настройка Systemd сервиса бэкенда

Создайте файл `/etc/systemd/system/nms-backend.service`:

```ini
[Unit]
Description=NMS WebUI Backend FastAPI Service
After=network.target

[Service]
Type=simple
User=ttc
WorkingDirectory=/opt/nms-webui
ExecStart=/opt/nms-webui/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 9000 --workers 4
Restart=always
RestartSec=5
Environment=LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target
```

Активация сервиса:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nms-backend
```
