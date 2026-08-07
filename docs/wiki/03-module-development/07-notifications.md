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

## 🌐 5. Справочник REST API (`/api/notifications`)

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

## 📡 6. Многоканальная внешняя рассылка (Notification Dispatcher)

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
* **Параметры**: `webhook_url`, `secret_token`.
* Отправляет HTTP POST запрос с JSON payload. Если указан `secret_token`, передает его в заголовке `X-NMS-Secret`.

#### 6. Syslog / SIEM (`syslog`)
* **Параметры**: `syslog_host`, `syslog_port`, `protocol` (`udp` / `tcp`).
* Передает логи в формате RFC 5424 (`<134>1 NMSWebUI ...`).

---

### Фильтрация каналов:
Каждая интеграция настраивается с двумя фильтрами:
* **`min_type`**: Минимальный порог критичности (`info` $\le$ `success` $\le$ `warning` $\le$ `error`). Например, если указано `warning`, сообщения `info` и `success` в этот канал не пойдут.
* **`categories`**: Строка категорий через запятую (например, `"system,telemetry"`) или `"*"` для всех категорий.

### REST API управления интеграциями:
* `GET /api/notifications/integrations` — Список интеграций.
* `POST /api/notifications/integrations` — Создать канал.
* `PUT /api/notifications/integrations/{id}` — Обновить параметры.
* `DELETE /api/notifications/integrations/{id}` — Удалить канал.
* `POST /api/notifications/integrations/{id}/test` — Отправить тестовое уведомление для проверки настроек.

---

## 💻 7. Использование на фронтенде (Vue 3 / TypeScript)

На фронтенде работы с уведомлениями доступен Composable `useNotifications`:

```typescript
import { useNotifications } from '@/composables/useNotifications'

const { notify } = useNotifications()

// Создать уведомление с вызовом REST API и локальным тостом:
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

## 💡 8. Рекомендации и Best Practices

1. **Используйте правильные категории**: Передавайте понятное имя категории или полагайтесь на автоподстановку `self.module_id`. Это позволит администраторам гибко фильтровать отправку в Telegram или Email.
2. **Не спамьте в циклических опросах**: Подсистема сглаживает дубликаты за последние 60 секунд, однако для повторяющихся ошибок лучше обновлять локальное состояние устройства и отправлять уведомление только при изменении статуса (*State Changed*).
3. **Задавайте информативные ссылки (`link`)**: Указывайте путь к конкретной странице устройства или ресурса (например, `/devices/mod-tuya-01`), чтобы оператор мог в один клик перейти к источнику проблему из колокольчика уведомлений.

