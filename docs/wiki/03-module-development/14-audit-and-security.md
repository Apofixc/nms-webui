# 🛡 14. Журнал аудита безопасности и системные события (Audit & Events)

Система **NMS WebUI** включает в себя встроенную подсистему аудита безопасности (Audit Log) и брокер системных событий реального времени (Event Bus & WebSockets). Каждое критическое административное действие, аутентификация пользователя или изменение конфигурации должно быть зафиксировано в журнале аудита, а важные изменения состояния — транслироваться клиентам через WebSocket.

---

## 🧭 0. Матрица разделения подсистем (Audit vs Logger vs Event Bus vs Notifications)

Разработчикам модулей доступно 4 подсистемы для протоколирования и коммуникации. Правильный выбор инструмента гарантирует производительность и целостность системы:

| Подсистема | Назначение | Целевая аудитория | Хранение / Срок жизни | Пример использования |
| :--- | :--- | :--- | :--- | :--- |
| **Logger API** (`_log.info`) | Техническая отладка, стектрейсы, внутреннее состояние | Разработчики, DevOps | Файлы логов (`nms.log`), ротация файлов | `_log.error("DB connection error: %s", exc)` |
| **Audit Log** (`log_audit_event`) | Юридически значимый аудит административных и security-событий | Аудиторы, Системные Администраторы | Таблица БД `audit_logs` (неизменяемая) | `log_audit_event(..., action="user.delete")` |
| **Event Bus** (`broadcaster`) | Мгновенная трансляция событий в UI реального времени | Фронтенд (Vue.js) | В памяти (In-Memory WebSocket Broadcast) | `broadcaster.broadcast({"type": "device_online"})` |
| **Notification API** (`create_notification`) | Системные и пользовательские алерты в иконку уведомлений | Конечные пользователи UI | Таблица БД `notifications` (до прочтения) | `create_notification(title="Alert", category="hardware")` |

---

## 📋 1. Подсистема аудита безопасности (`backend/core/audit.py`)

Функция `log_audit_event` предоставляет единый точечный механизм для записи событий аудита безопасности и административных операций в систему.

### 📐 Сигнатура функции `log_audit_event`

```python
def log_audit_event(
    user_id: Optional[str],
    username: str,
    action: str,
    resource: str,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
```

### 📝 Параметры вызова

| Параметр | Тип | Описание | Пример значения |
| :--- | :--- | :--- | :--- |
| `user_id` | `Optional[str]` | Уникальный системный или UUID идентификатор пользователя. | `"1"`, `"usr_99"` |
| `username` | `str` | Имя пользователя или системного процесса (обязательно). | `"admin"`, `"system"` |
| `action` | `str` | Код произошедшего действия (snake_case с префиксом категории). | `"auth.login_success"`, `"module.tuya.reset"` |
| `resource` | `str` | Целевой объект или сущность, над которой совершено действие. | `"user:admin"`, `"sensor:192.168.1.10"` |
| `details` | `Optional[str]` | Текстовая отладочная информация или сериализованный JSON с деталями. | `"{\"reason\": \"manual_trigger\"}"` |
| `ip_address` | `Optional[str]` | Сетевой IP-адрес инициатора (из `request.client.host`). | `"192.168.1.50"`, `"127.0.0.1"` |

### 🛡 Отказоустойчивость записи аудита

Функция `log_audit_event` работает по принципу **non-blocking error isolation**:
- Запись происходит в изолированном контекстном менеджере SQLite.
- Любое исключение при записи лога (например, кратковременная блокировка базы данных) перехватывается, логируется в системный логгер `nms.audit` уровня `ERROR` и **не приводит к сбою** основного бизнес-запроса пользователя.

### 🛡 1.1. Безопасность аудита, неизменяемость и Data Masking

1. **Запрет записи секретов**: Пароли, JWT-токены, API-ключи, PIN-коды и приватные ключи **категорически запрещено** передавать в `details` или `resource`.
2. **Защита целостности (Immutability)**: Записи в `audit_logs` создаются только на добавление (`INSERT`). Никакие REST-эндпоинты не позволяют редактировать или выборочно удалять логи (допускается только системная автоматическая ротация).
3. **Локализация контекста**: Поле `details` может содержать локализованную строку, созданную с помощью `tr(request, "audit_key", ...)` для удобства чтения администраторами разных языковых локалей.

```python
# Пример безопасной записи события изменения API-ключа внешнего сервиса
log_audit_event(
    user_id=str(user["id"]),
    username=user["username"],
    action="module.tuya.update_api_key",
    resource="config:tuya_cloud",
    details=tr(request, "audit_tuya_key_updated", masked_key=f"***{api_key[-4:]}"),
    ip_address=request.client.host if request.client else None
)
```

---

## 🗄 2. Схема базы данных (`audit_logs`)

Записи аудита сохраняются в таблицы базы данных SQLite, инициализируемой в `backend/core/database.py`:

```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    details TEXT,
    ip_address TEXT
);
```

### 🏷 Стандарты именования категорий действий (`action`)

Рекомендуется использовать стандартную префиксную схему `категория.действие` для упрощения последующей фильтрации и локализации:

- `auth.login_success` — Успешный вход в систему.
- `auth.login_failed` — Неудачная попытка входа.
- `auth.login_lockout` — Блокировка аккаунта из-за превышения попыток.
- `auth.logout` — Выход пользователя.
- `user.create` / `user.update` / `user.delete` — Управление пользователями.
- `role.create` / `role.update` — Изменение ролей и прав доступа.
- `system.audit_logs_rotated` — Ротация логов аудита.
- `module.<module_id>.<action>` — Пользовательские действия модулей (например, `module.tuya.device_reboot`).

---

## 📡 3. Брокер системных событий и WebSockets (`backend/core/events.py`)

NMS WebUI предоставляет шину событий реального времени на основе WebSocket (`/api/events/ws`).

### 🏗 Архитектура `ConnectionManager` и `EventBroadcaster`

- **`ConnectionManager`**: отслеживает все активные WebSocket-подключения, их статус и связанные `user_id`. Поддерживает как широковещательную рассылку всем подключенным веб-клиентам, так и адресную отправку конкретному пользователю.
- **`EventBroadcaster` (`broadcaster`)**: синглтон для безопасной отправки событий из синхронного и асинхронного Python-кода без блокировки основного Event Loop.

### 🔌 Использование `broadcaster` в модулях

Модули могут транслировать любые пользовательские события или уведомления веб-клиентам:

```python
from backend.core.events import broadcaster

# 1. Рассылка произвольного события всем подключенным веб-клиентам
broadcaster.broadcast(
    data_dict={
        "type": "device_status_changed",
        "device_id": "dev_102",
        "status": "online"
    }
)

# 2. Адресная отправка события конкретному пользователю
broadcaster.broadcast(
    data_dict={
        "type": "task_completed",
        "task_id": "job_55"
    },
    target_user_id="user_123"
)
```

### 🔔 Уведомление об изменении настроек модуля (`notify_settings_changed`)

Для автоматического оповещения клиентов об изменении настроек модуля используется встроенная функция:

```python
from backend.core.events import notify_settings_changed

# Рассылает WebSocket событие "module_settings_changed" и создает системное уведомление
notify_settings_changed("tuya")
```

### 🔑 3.1. Передача JWT-токена аутентификации

При подключении клиенты передают JWT-токен в URL Query-параметре:
`ws://<host>/api/events/ws?token=<access_token>`

На бэкенде `websocket_endpoint` автоматически декодирует токен с помощью `decode_access_token(token)` и привязывает WebSocket-соединение к конкретному `user_id`. Это позволяет отправлять как общесистемные события, так и персональные сообщения конкретному пользователю (`target_user_id`).

### 💓 3.2. Поддержание соединения (Ping-Pong Heartbeat)

Для предотвращения закрытия WebSocket-соединения прокси-серверами (Nginx, Traefik) по idle-таймауту поддерживается протокол пульсации (Heartbeat):
- Клиент отправляет строку `"ping"` каждые 30 секунд.
- Бэкенд отвечает JSON-объектом `{"type": "pong"}`.

### 📐 3.3. Стандартизация именования WebSocket событий

Для обеспечения предсказуемости обработки событий на фронтенде рекомендуется использовать следующую структуру payload:

```json
{
  "type": "module.<module_id>.<event_name>",
  "timestamp": "2026-08-07T22:21:00Z",
  "payload": {
    "device_id": "dev_101",
    "state": "online"
  }
}
```

---

## 🌐 4. REST API журнала аудита (`backend/core/users_api.py`)

Для работы с журналом аудита в backend реализованы 3 основных REST-эндпоинта.

### 🔍 4.1. Получение записей аудита (`GET /api/audit-logs`)

- **Право доступа (RBAC)**: `audit.view`
- **Параметры запроса**:
  - `limit` (int, по умолчанию `100`): количество записей на страницу.
  - `offset` (int, по умолчанию `0`): смещение для пагинации.
  - `category` (optional str): быстрая фильтрация категорий (`"auth"`, `"user"`, `"errors"`).
  - `search` (optional str): полнотекстовый поиск по полям `username`, `action`, `resource`, `details`, `ip_address`.

#### Пример ответа:
```json
{
  "total": 142,
  "items": [
    {
      "id": 142,
      "timestamp": "2026-08-07 22:15:30",
      "user_id": "1",
      "username": "admin",
      "action": "auth.login_success",
      "resource": "auth",
      "details": null,
      "ip_address": "127.0.0.1"
    }
  ]
}
```

### 📥 4.2. Экспорт журнала аудита (`GET /api/audit-logs/export`)

- **Право доступа (RBAC)**: `audit.export`
- **Параметры запроса**: `format` (`"xlsx"` или `"csv"`).
- **Особенности**:
  - `format=xlsx`: формирует стилизованный файл Excel с зафиксированной шапкой, автошириной колонок и чередующейся подсвечиваемой заливкой строк через библиотеку `openpyxl`. Заголовок `Content-Disposition: attachment; filename="audit_logs.xlsx"`.
  - `format=csv`: формирует файл CSV с кодировкой UTF-8 BOM (`utf-8-sig`) для корректного открытия в MS Excel без искажения символов Кириллицы. Заголовок `Content-Disposition: attachment; filename="audit_logs.csv"`.

### 🧹 4.3. Ротация и очистка журнала (`POST /api/audit-logs/rotate`)

- **Право доступа (RBAC)**: `system.admin`
- **Тело запроса (`AuditRotateRequest`)**:
  ```json
  {
    "max_days": 90,
    "max_records": 100000
  }
  ```
- **Результат**: вызывает ротацию и автоматически записывает событие `system.audit_logs_rotated` в базу аудита.

---

## 🔄 5. Ротация и автоматическое обслуживание (`backend/core/audit.py`)

Для предотвращения бесконечного роста базы данных предусмотрена функция `rotate_audit_logs`:

```python
def rotate_audit_logs(max_days: int = 90, max_records: int = 100000) -> int:
```

### ⚙️ Алгоритм ротации (2 этапа):

1. **Очистка по возрасту**:
   Удаление всех записей, датированных старше `max_days` дней с использованием вычисления SQLite `julianday`:
   ```sql
   DELETE FROM audit_logs
   WHERE (julianday('now') - julianday(replace(timestamp, 'T', ' '))) > ?
   ```
2. **Ограничение по максимальному количеству**:
   Удаление самых старых записей, если общее число записей превышает `max_records`:
   ```sql
   DELETE FROM audit_logs
   WHERE id NOT IN (
       SELECT id FROM audit_logs ORDER BY id DESC LIMIT ?
   )
   ```

Функция возвращает общее суммарное количество удаленных записей.

### ⏰ 5.1. Автоматическая ротация через фоновые задачи (Lifecycle Task)

Для вызова автоматической ротации раз в сутки в фоновых сервисах модуля или ядра (см. руководство по [Хукам и фоновым задачам](file:///opt/nms-webui/docs/wiki/03-module-development/13-hooks-and-background-tasks.md)) используйте следующий паттерн:

```python
import asyncio
import logging
from backend.core.audit import rotate_audit_logs

_log = logging.getLogger("nms.audit.task")

async def periodic_audit_rotation_task(interval_seconds: int = 86400):
    """Фоновый процесс регулярной очистки устаревших записей аудита."""
    while True:
        try:
            deleted_count = rotate_audit_logs(max_days=90, max_records=100000)
            if deleted_count > 0:
                _log.info("Scheduled audit log rotation cleaned %d old records", deleted_count)
        except Exception as exc:
            _log.error("Error during automated audit rotation: %s", exc)
            
        await asyncio.sleep(interval_seconds)
```

---

## 💻 6. Фронтенд-интеграция и локализация (`frontend/src/core/`)

В фронтенд-приложении взаимодействия с логами аудита вынесены в модуль API [`frontend/src/core/api.ts`](file:///opt/nms-webui/frontend/src/core/api.ts):

### 🛠 API Методы:

```typescript
// Получение логов с фильтрацией и пагинацией
export async function apiFetchAuditLogs(limit = 100, offset = 0, category?: string, search?: string)

// Экспорт отчета (.xlsx / .csv)
export async function apiExportAuditLogs(format: string = 'xlsx')

// Принудительный запуск ротации логов
export async function apiRotateAuditLogs(maxDays = 90, maxRecords = 100000)
```

### 🌐 Локализация действий аудита

Все коды действий (`action`) локализуются в файлах перевода (`en.ts`, `ru.ts`) с помощью префикса `auditAction_`:

```typescript
// frontend/src/core/locales/ru.ts
auditAction_auth_login_success: 'Успешный вход',
auditAction_auth_login_failed: 'Ошибка входа',
auditAction_auth_login_lockout: 'Блокировка аккаунта',
auditAction_auth_logout: 'Выход из системы',
auditAction_system_audit_logs_rotated: 'Ротация журнала аудита',
```

### 🔌 Vue 3 Composable для подписки на события WebSockets (`useSystemEvents`)

Для удобной подписки на события реального времени в компонентах Vue 3:

```typescript
import { onMounted, onUnmounted } from 'vue'

export function useSystemEvents(onEventCallback: (data: any) => void) {
  let socket: WebSocket | null = null
  let pingTimer: any = null

  onMounted(() => {
    const token = localStorage.getItem('access_token') || ''
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/events/ws?token=${encodeURIComponent(token)}`

    socket = new WebSocket(wsUrl)

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'pong') return
        onEventCallback(data)
      } catch (err) {
        console.error('Failed to parse WebSocket message', err)
      }
    }

    // Ping каждые 30 секунд для поддержания активности Nginx/прокси
    pingTimer = setInterval(() => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send('ping')
      }
    }, 30000)
  })

  onUnmounted(() => {
    if (pingTimer) clearInterval(pingTimer)
    if (socket) socket.close()
  })
}
```

---

## 💡 7. Практические примеры для разработчиков модулей

### 7.1. Регистрация события аудита из роутера модуля

При создании REST API методов в модуле следует логировать ключевые изменения:

```python
from fastapi import APIRouter, Depends, Request
from backend.core.audit import log_audit_event
from backend.core.auth import CurrentUser

router = APIRouter(prefix="/api/modules/my-module", tags=["my-module"])

@router.post("/devices/{device_id}/reboot")
async def reboot_device(
    device_id: str,
    request: Request,
    user: dict = Depends(CurrentUser)
):
    # Выполнение логики перезагрузки устройства...
    
    # Регистрация события безопасности
    log_audit_event(
        user_id=str(user.get("id", "")),
        username=user.get("username", "unknown"),
        action="module.my_module.device_reboot",
        resource=f"device:{device_id}",
        details=f"Manual reboot triggered for device {device_id}",
        ip_address=request.client.host if request.client else None
    )
    
    return {"status": "ok", "message": f"Device {device_id} reboot initiated"}
```

### 7.2. Отправка события в WebSocket из фоновой задачи модуля

```python
import asyncio
from backend.core.events import broadcaster

async def background_monitoring_task():
    while True:
        await asyncio.sleep(30)
        # При обнаружении критического события рассылаем всем клиентам
        broadcaster.broadcast(
            data_dict={
                "type": "my_module_alert",
                "severity": "warning",
                "message": "High CPU utilization detected on sensor #4"
            }
        )
```

---

## 🔗 Связанные руководства

- 🔑 [10. Система прав и контроля доступа (RBAC)](file:///opt/nms-webui/docs/wiki/03-module-development/10-access-control.md)
- 📡 [09. Использование WebSockets (WS API)](file:///opt/nms-webui/docs/wiki/03-module-development/09-websockets.md)
- 📝 [08. Система логирования (Logger API)](file:///opt/nms-webui/docs/wiki/03-module-development/08-logging.md)
- ⚙️ [13. Хуки жизненного цикла и фоновые задачи](file:///opt/nms-webui/docs/wiki/03-module-development/13-hooks-and-background-tasks.md)
