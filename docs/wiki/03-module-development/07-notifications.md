# 🔔 7. Использование уведомлений (Notifications API)

---

## 📌 1. Архитектура подсистемы уведомлений

Подсистема уведомлений NMS WebUI обеспечивает надежную доставку событий операторам системы в реальном времени через веб-интерфейс, а также асинхронную трансляцию во внешние мессенджеры и SIEM-системы.

```
┌─────────────────────────┐       ┌────────────────────────┐
│  Модуль / BaseModule    │       │ Celery / Внешний скрипт │
│  self.context.notify()  │       │  create_notification() │
└────────────┬────────────┘       └───────────┬────────────┘
             │                                │
             └────────────────┬───────────────┘
                              ▼
                ┌──────────────────────────┐
                │  create_notification()   │
                │  (Дедупликация 60 сек)   │
                └─────────────┬────────────┘
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
   ┌───────────────────┐             ┌────────────────────┐
   │ БД SQLite (nms.db)│             │ Broadcaster        │
   │ notifications     │             │ (WebSockets / WS)  │
   └───────────────────┘             └─────────┬──────────┘
             │                                 │
             ▼                                 ▼
┌──────────────────────────┐         ┌────────────────────┐
│ Notification Dispatcher  │         │ Vue 3 Frontend     │
│ (Telegram, Discord,      │         │ NotificationCenter │
│  Email, Webhook, Syslog) │         │ (Toast, Sound, Push│
└──────────────────────────┘         └────────────────────┘
```

### Ключевые возможности подсистемы:
1. **Дедупликация событий**: Защита от флуда. Повторные идентичные уведомления (`title`, `message`, `category`, `user_id`), отправленные в течение 60 секунд, не создают дубликаты, а лишь обновляют штамп времени `created_at`.
2. **Адресация**: Уведомления могут быть общими/системными (`user_id=None`, видны всем операторам) или персональными (`user_id="user_123"`).
3. **Квитирование аварий (Acknowledge / Ack)**: Операторы могут подтверждать получение тревог с фиксацией времени и имени оператора.
4. **WebSocket Real-Time**: Мгновенная доставка на клиентские браузеры со звуковым сопровождением и поддержкой браузерных Web Push.
5. **Многоканальный Диспетчер (Notification Dispatcher)**: Рассылка в Telegram, Discord, Viber, Email (SMTP), Webhooks и Syslog (RFC 5424).

### 🗄 Схема таблиц базы данных (SQLite DDL):

```sql
-- Таблица хранения уведомлений
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',             -- info, success, warning, error
    category TEXT DEFAULT 'system',         -- system, telemetry, auth, etc.
    read BOOLEAN DEFAULT 0,                 -- 0 = unread, 1 = read
    link TEXT,                              -- Relative UI URL
    user_id TEXT,                           -- NULL = public, str = user ID
    acknowledged BOOLEAN DEFAULT 0,         -- 0 = unack, 1 = acked
    acknowledged_by TEXT,                   -- Username / Operator ID
    acknowledged_at DATETIME,               -- Timestamp of ACK
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимальной фильтрации и пагинации
CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, read);
CREATE INDEX IF NOT EXISTS idx_notifications_category ON notifications(category);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at);

-- Таблица конфигурации внешних каналов интеграции
CREATE TABLE IF NOT EXISTS notification_integrations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,                     -- telegram, discord, viber, email, webhook, syslog
    enabled BOOLEAN DEFAULT 1,              -- 0 = disabled, 1 = enabled
    min_type TEXT DEFAULT 'warning',        -- Min severity filter
    categories TEXT DEFAULT '*',           -- Comma-separated list or '*'
    config TEXT NOT NULL,                   -- JSON object with provider params
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📩 2. Отправка уведомления из модуля (`ModuleContext.notify`)

Внутри модуля (унаследованного от `BaseModule` или `BaseSubmodule`) отправка уведомлений выполняется через контекст `self.context.notify()`.

### Сигнатура метода:
```python
def notify(
    self,
    title: str,
    message: str,
    notification_type: str = "info",
    category: str | None = None,
    link: str | None = None,
    user_id: str | None = None,
) -> dict:
```

### Параметры:
| Параметр | Тип | По умолчанию | Описание |
| :--- | :--- | :--- | :--- |
| `title` | `str` | *обязательный* | Заголовок уведомления. |
| `message` | `str` | *обязательный* | Текст сообщения с подробной информацией. |
| `notification_type` | `str` | `"info"` | Критичность: `"info"`, `"success"`, `"warning"`, `"error"`. |
| `category` | `str \| None` | `None` | Категория события. **Если равен `None`, автоматически подставляется `self.module_id`**. |
| `link` | `str \| None` | `None` | Относительный URL для быстрого перехода в UI (например, `/devices/sns_01`). |
| `user_id` | `str \| None` | `None` | Идентификатор пользователя. `None` = доступно всем. |

---

### Примеры использования из модуля:

#### 1. Информационное событие (Успешное действие)
```python
self.context.notify(
    title="Конфигурация обновлена",
    message="Параметры опроса устройства 'Коммутатор-Core' успешно сохранены.",
    notification_type="success",
    link="/network/devices/sw_core"
)
# category автоматически станет равным module_id (например, "network_monitor")
```

#### 2. Предупреждение о пороговом значении (Warning)
```python
self.context.notify(
    title="Высокая загрузка CPU",
    message="Загрузка процессора на сервере 'App-Server-01' превысила 85%.",
    notification_type="warning",
    category="telemetry",
    link="/telemetry/servers/app_01"
)
```

#### 3. Критическая авария оборудования (Error)
```python
self.context.notify(
    title="Отказ питания",
    message="Основной ввод питания ИБП-02 обесточен! Переход на аккумуляторные батареи.",
    notification_type="error",
    category="power",
    link="/power/ups/ups_02"
)
```

#### 4. Персональное уведомление конкретному пользователю
```python
self.context.notify(
    title="Отчет сформирован",
    message="Ваш персональный отчет по аудиту за июль готов к скачиванию.",
    notification_type="info",
    category="reports",
    link="/reports/download/rep_789",
    user_id="user_admin"
)
```

---

## 🛠 3. Вызов вне контекста модуля (`create_notification`)

Если уведомление генерируется в фоновой Celery-задаче, отдельном воркере или независимом скрипте бэкенда, где объект `ModuleContext` недоступен, следует использовать глобальную функцию `create_notification`:

```python
from backend.core.notifications_api import create_notification

create_notification(
    title="Резервное копирование завершено",
    message="Автоматический бэкап системы выполнен успешно. Размер файла: 450 МБ.",
    notification_type="success",
    category="system",
    link="/system/backups"
)
```

> [!NOTE]
> Функция `create_notification()` возвращает словарь `dict` со всеми полями созданного (или обновленного при дедупликации) уведомления. В случае сбоя возвращает `{}`.

---

## 📑 4. Жизненный цикл и Квитирование аварий (Acknowledge)

Каждое уведомление имеет жизненный цикл и статус обработки оператором:

```
[Создано] ──► [WebSocket вещание / Push] ──► [Прочитано (Read)]
    │                                             │
    └──────────────────► [Квитировано (Ack)] ──────┘
```

### Поля объекта уведомления в БД:
```json
{
  "id": 142,
  "title": "Отказ оборудования",
  "message": "Датчик 'Сенсор-01' не отвечает по SNMP",
  "type": "error",
  "category": "telemetry",
  "read": false,
  "link": "/sensor-monitor/device/sns_01",
  "user_id": null,
  "acknowledged": true,
  "acknowledged_by": "operator_ivan",
  "acknowledged_at": "2026-08-07 21:45:00",
  "created_at": "2026-08-07 21:40:12"
}
```

* **`read`** (`bool`): Флаг прочтения оператором в интерфейсе.
* **`acknowledged`** (`bool`): Флаг квитирования (принятия тревоги в работу).
* **`acknowledged_by`** (`str`): Имя оператора или учетной записи, принявшей решение.
* **`acknowledged_at`** (`str`): Дата и время квитирования.

---

## 📡 5. WebSocket Real-Time события и контракты

При создании или обновлении уведомления система транслирует WebSocket-сообщения через шину `broadcaster` всем подключенным веб-клиентам.

### 1. Событие `notification_created`
Отправляется при создании нового уведомления (или при повторном дедуплицированном срабатывании):
```json
{
  "type": "notification_created",
  "notification": {
    "id": 142,
    "title": "Высокая загрузка CPU",
    "message": "Загрузка процессора превысила 90%",
    "type": "warning",
    "category": "telemetry",
    "read": false,
    "link": "/telemetry/cpu",
    "user_id": null,
    "acknowledged": false,
    "acknowledged_by": null,
    "acknowledged_at": null,
    "created_at": "2026-08-07 21:47:00"
  }
}
```

### 2. Событие `notification_updated`
Отправляется при изменении статуса квитирования (`ack`):
```json
{
  "type": "notification_updated",
  "notification": {
    "id": 142,
    "title": "Высокая загрузка CPU",
    "message": "Загрузка процессора превысила 90%",
    "type": "warning",
    "category": "telemetry",
    "read": false,
    "link": "/telemetry/cpu",
    "user_id": null,
    "acknowledged": true,
    "acknowledged_by": "operator_admin",
    "acknowledged_at": "2026-08-07 21:48:10",
    "created_at": "2026-08-07 21:47:00"
  }
}
```

---

## 🌐 6. Справочник REST API (`/api/notifications`)

Все эндпоинты зарегистрированы с префиксом `/api/notifications`.

### 1. Получение списка уведомлений
```http
GET /api/notifications?unread_only=false&category=telemetry&type=error&search=Сенсор&limit=50&offset=0
```
* **Параметры**:
  * `unread_only` (`bool`): Фильтр только непрочитанных.
  * `category` (`str`, опционально): Фильтр по категории (`system`, `telemetry`, `auth` и др.).
  * `type` (`str`, опционально): Фильтр по критичности (`info`, `success`, `warning`, `error`).
  * `search` (`str`, опционально): Полнотекстовый поиск по заголовку и сообщению (`title LIKE %...% OR message LIKE %...%`).
  * `limit` (`int`, default 50), `offset` (`int`, default 0): Пагинация.

### 2. Счетчик непрочитанных
```http
GET /api/notifications/unread-count
```
**Ответ**:
```json
{
  "count": 5
}
```

### 3. Ручное создание уведомления через HTTP
```http
POST /api/notifications
Content-Type: application/json

{
  "title": "Тестовое оповещение",
  "message": "Проверка связи через REST API",
  "type": "info",
  "category": "testing",
  "link": "/system/test"
}
```

### 4. Отметка прочтения
* **Одно уведомление**: `POST /api/notifications/{id}/read`
* **Все уведомления**: `POST /api/notifications/read-all`
* **Пакетная отметка (Batch)**:
  ```http
  POST /api/notifications/read-batch
  Content-Type: application/json

  {
    "ids": [101, 102, 105]
  }
  ```

### 5. Квитирование тревоги (Acknowledge)
```http
POST /api/notifications/{id}/ack
```
* Автоматически проставляет `acknowledged = 1`, текущего пользователя в `acknowledged_by` и штамп времени в `acknowledged_at`.
* Генерирует WebSocket-событие `notification_updated` для обновления интерфейса у всех подключенных операторов.

### 6. Удаление и очистка
* **Удалить одно**: `DELETE /api/notifications/{id}`
* **Очистить группу**: `DELETE /api/notifications/clear?unread_only=true&days_old=7`

---

## 📢 7. Многоканальная внешняя рассылка (Notification Dispatcher)

Подсистема рассылки (`backend/core/notification_dispatcher.py`) автоматически отправляет создаваемые уведомления во внешние каналы связи.

### Поддерживаемые провайдеры:

```
┌──────────────────────────────────────────────────────────┐
│               Notification Dispatcher                    │
├──────────────┬─────────────┬────────────┬────────────────┤
│ Telegram Bot │ Discord Web │ Viber Bot  │ Email (SMTP)   │
│ HTML Format  │ Rich Embeds │ REST API   │ HTML Template  │
├──────────────┴─────────────┴────────────┴────────────────┤
│ Webhooks (JSON POST + HMAC/Secret)                      │
│ Syslog (RFC 5424 UDP/TCP SIEM Integrations)             │
└──────────────────────────────────────────────────────────┘
```

#### 1. Telegram Bot API (`telegram`)
* **Параметры**: `bot_token`, `chat_id`.
* Сообщения форматируются в HTML с цветовыми иконками статусов (`🔴`, `🟡`, `ℹ️`).

#### 2. Discord Webhooks (`discord`)
* **Параметры**: `webhook_url`.
* Отправляются стилизованные Rich Embeds с цветом рамки в зависимости от `type`.

#### 3. Viber Bot REST API (`viber`)
* **Параметры**: `auth_token`, `receiver_id`.

#### 4. Email / SMTP (`email`)
* **Параметры**: `smtp_host`, `smtp_port`, `username`, `password`, `from_email`, `to_emails`, `use_tls`.
* Формирует HTML-письмо с цветовым выделением уровня критичности.

#### 5. Webhooks (`webhook`)
* **Параметры**: `webhook_url`, `secret_token` (опционально).
* Отправляет HTTP POST запрос с JSON полезной нагрузкой.
* При наличии `secret_token` передает значение в HTTP-заголовке `X-NMS-Secret`.
* **Формат Webhook Payload**:
  ```json
  {
    "event": "notification.created",
    "notification": {
      "id": 142,
      "title": "Отказ питания",
      "message": "Основной ввод питания обесточен!",
      "type": "error",
      "category": "power",
      "link": "/power/ups/ups_02",
      "created_at": "2026-08-07 21:40:12"
    }
  }
  ```

#### 6. Syslog / SIEM (`syslog`)
* **Параметры**: `syslog_host`, `syslog_port`, `protocol` (`udp` / `tcp`).
* Формат сообщений RFC 5424 (`<134>1 NMSWebUI ...`).
* Карта уровней Syslog (Severity Level):
  * `error` $\rightarrow$ Severity 3 (Error)
  * `warning` $\rightarrow$ Severity 4 (Warning)
  * `info` / `success` $\rightarrow$ Severity 6 (Informational)

---

### Фильтрация и шкала критичности каналов:
Каждая интеграция настраивается с двумя фильтрами:
* **`min_type`**: Минимальный порог критичности. Порядок уровней:
  $$\text{info (1)} \le \text{success (2)} \le \text{warning (3)} \le \text{error (4)}$$
  *Пример*: если в настройках интеграции указано `min_type = "warning"`, то сообщения `info` и `success` в этот канал не отправляются.
* **`categories`**: Перечень разрешенных категорий через запятую (например, `"system,telemetry"`) или `"*"` для всех категорий.

### REST API управления интеграциями:
* `GET /api/notifications/integrations` — Список интеграций.
* `POST /api/notifications/integrations` — Создать канал.
* `PUT /api/notifications/integrations/{id}` — Обновить параметры.
* `DELETE /api/notifications/integrations/{id}` — Удалить канал.
* `POST /api/notifications/integrations/{id}/test` — Отправить тестовое уведомление для проверки настроек.

---

## 💻 8. Использование на фронтенде (Vue 3 / TypeScript)

На фронтенде для работы с уведомлениями доступен Composable `useNotifications`:

```typescript
import { useNotifications } from '@/composables/useNotifications'

const { notify, fetchUnreadCount, markAsRead } = useNotifications()

// Создать уведомление с вызовом REST API и отображением локального тоста:
await notify({
  title: 'Устройство добавлено',
  message: 'Маршрутизатор R-01 успешно зарегистрирован',
  type: 'success',
  category: 'inventory',
  link: '/inventory/devices/r01'
}, true) // true = показать мгновенный Toast на экране
```

### Компонент `NotificationCenter.vue`:
Располагается в шапке (Header) NMS WebUI:
* Отображает иконку колокольчика с пульсирующим бедж-счетчиком непрочитанных.
* Воспроизводит звуковое оповещение при получении уведомлений типа `warning` и `error`.
* Поддерживает системные браузерные Web Push оповещения.
* Предоставляет поиск по истории, квитирование тревог и вызов модального окна настройки внешних каналов (`NotificationIntegrationsModal.vue`).

---

## 💡 9. Рекомендации и Практические Рецепты (Best Practices & Recipes)

### Рецепт 1. Защита от флуда при циклических опросах (State Change Pattern)
Хотя подсистема автоматически сглаживает повторы в течение 60 секунд, в циклах фонового мониторинга рекомендуется отправлять уведомления только при изменении состояния (*State Transition*):

```python
class SensorMonitorModule(BaseModule):
    def __init__(self, context):
        super().__init__(context)
        self._last_state = "OK"

    def check_sensor(self, current_temp: float):
        new_state = "CRITICAL" if current_temp > 80.0 else "OK"

        # Уведомляем только при СМЕНЕ СОСТОЯНИЯ
        if new_state != self._last_state:
            if new_state == "CRITICAL":
                self.context.notify(
                    title="Перегрев датчика",
                    message=f"Температура достигла {current_temp}°C!",
                    notification_type="error",
                    link="/sensors/temp"
                )
            elif new_state == "OK":
                self.context.notify(
                    title="Нормализация температуры",
                    message=f"Температура вернулась к норме: {current_temp}°C",
                    notification_type="success",
                    link="/sensors/temp"
                )
            self._last_state = new_state
```

### Рецепт 2. Использование уведомлений из субмодулей (`BaseSubmodule`)
Субмодули унаследуют доступ к контексту родительского модуля, поэтому метод `self.context.notify()` работает аналогично:

```python
from backend.core.base_submodule import BaseSubmodule

class StorageSettingsSubmodule(BaseSubmodule):
    def save_settings(self, data: dict):
        # Бизнес-логика сохранения...
        self.context.notify(
            title="Настройки хранилища сохранены",
            message="Квота дискового пространства обновлена.",
            notification_type="info"
        )
```

### Рецепт 3. Подписка на real-time события в пользовательском Vue-компоненте
Для обработки событий уведомлений в реальном времени внутри любого Vue-компонента можно использовать глобальный WebSocket клиент:

```vue
<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { wsClient } from '@/services/websocket'

function handleWsMessage(event: MessageEvent) {
  try {
    const data = JSON.parse(event.data)
    if (data.type === 'notification_created') {
      console.log('Новое уведомление получено:', data.notification)
    }
  } catch (err) {
    console.error('Ошибка обработки WS:', err)
  }
}

onMounted(() => {
  wsClient.addEventListener('message', handleWsMessage)
})

onUnmounted(() => {
  wsClient.removeEventListener('message', handleWsMessage)
})
</script>
```

---

### Резюме лучших практик:
1. **Используйте правильные категории**: Передавайте понятное имя категории или полагайтесь на автоподстановку `self.module_id`. Это позволит администраторам гибко фильтровать отправку в Telegram или Email.
2. **Не спамьте в циклических опросах**: Применяйте паттерн смены состояний (State Change).
3. **Задавайте информативные ссылки (`link`)**: Указывайте путь к конкретной странице устройства или ресурса (например, `/devices/mod-tuya-01`), чтобы оператор мог в один клик перейти к источнику проблемы из колокольчика уведомлений.
