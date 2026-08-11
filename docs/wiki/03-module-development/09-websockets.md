# ⚡ 9. Использование WebSockets (WS API)

---

## 📌 1. Архитектура событий реального времени

Подсистема событий реального времени NMS WebUI обеспечивает высоконадежный двухсторонний обмен сообщениями с низкими задержками между бэкендом (FastAPI) и фронтендом (Vue 3 / dynamic runtime components). В качестве основного транспорта используется протокол **WebSockets** (`ws://` / `wss://`).

```
                               ┌──────────────────────────────────────────────┐
                               │            Браузер пользователя              │
                               │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
                               │  │ Вкладка 1 │  │ Вкладка 2 │  │ Вкладка 3 │   │
                               │  │ (LEADER) │  │ (Follower)│  │ (Follower)│   │
                               │  └────┬─────┴──┴────▲─────┴──┴────▲─────┘   │
                               │       │ BroadcastChannel("nms_events")    │
                               └───────┼──────────────────────────────────────┘
                                       │ 1 WS-соединение (Sec-WebSocket-Protocol)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Окружение Бэкенда                               │
│                                                                             │
│ ┌───────────────────────┐   ┌───────────────────────┐                       │
│ │  Модуль / BaseModule  │   │   Фоновый воркер /    │                       │
│ │  (Telemetry, Actions) │   │  System Event / Task  │                       │
│ └───────────┬───────────┘   └───────────┬───────────┘                       │
│             │                           │                                   │
│             └─────────────┬─────────────┘                                   │
│                           ▼                                                 │
│             ┌───────────────────────────┐                                   │
│             │     broadcaster (Sync)    │                                   │
│             │  .broadcast(immediate=...)│                                   │
│             └─────────────┬─────────────┘                                   │
│                           │                                                 │
│                           ▼                                                 │
│             ┌───────────────────────────┐                                   │
│             │   ConnectionManager       │                                   │
│             │   - broadcast_immediate() │                                   │
│             │   - broadcast_batched()   │                                   │
│             └───────┬───────────────┬───┘                                   │
│                     │               │                                       │
│  ┌──────────────────▼──────┐  ┌─────▼────────────────────────────────────┐  │
│  │ SQLite Journal (Disk)   │  │ SharedLogStreamManager (O(1) Disk Read)  │  │
│  │ system_events_journal   │  │ /api/system/logs/{log_name}/stream       │  │
│  └─────────────────────────┘  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Ключевые компоненты подсистемы:

1. **`backend/core/events.py`**:
   - `ConnectionManager` (`ws_manager`): Асинхронный менеджер подключений. Отвечает за отслеживание активных сокетов, лимиты подключений (`MAX_CONNECTIONS_PER_USER = 10`), двухсторонний Heartbeat (ping 30s / timeout 60s) и параллельную отправку через `asyncio.gather` с таймаутом 2.0s.
   - `EventBroadcaster` (`broadcaster`): Потокобезопасный броадкастер с поддержкой **мгновенного** (`broadcast_immediate`) и **пакетного** (`broadcast_batched`) режимов рассылки.
   - `record_event_in_db` & `get_missed_events_from_db`: Сохранение событий в SQLite-таблицу `system_events_journal` для гарантированного восстановления данных при реконнекте или падении бэкенда.
   - `@router.websocket("/ws")`: Главный WebSocket-эндпоинт системы (доступен по URL `/api/events/ws`).
   - `@router.get("")`: Информационный REST-эндпоинт (возвращает статус транспорта `status: "online"`).
2. **`backend/core/log_providers.py`**:
   - `SharedLogStreamManager` (`shared_log_stream_manager`): Централизованный Pub/Sub менеджер стриминга логов. Обеспечивает $O(1)$ чтений с диска независимо от количества клиентов.
3. **`frontend/src/composables/useWebSocket.ts`**:
   - **Multi-Tab Leader Election**: Избрание вкладки-лидера через `BroadcastChannel` (открывает ровно **1 сокет** на весь браузер и транслирует ведомым вкладкам).
   - Автоматическая обработка единичных мгновенных событий и батчей (`batch`).
   - Рукопожатие `resume` по `lastSeenSeqId` для получения пропущенных сообщений при реконнекте.
   - Реактивные состояния `isConnected`, `lastEvent` и авто-отписка listener'ов (`onUnmounted`).
   - Глобальный интерфейс `window.NMS.events` для микрофронтенд-виджетов.

---

## 🔐 2. Аутентификация, безопасность и гарантии доставки

### Аутентификация по JWT Токену
П## 🔐 2. Аутентификация, безопасность и жизненный цикл подключения

### Ticket-Based Auth (Одноразовые билеты) и RFC 6455 Subprotocol
Для исключения утечки длительных JWT access-токенов в URL/Query-строках в NMS WebUI реализована аутентификация по одноразовым билетам:
1. Клиент выполняет REST-запрос `POST /api/auth/ws-ticket` и получает короткоживущий билет (`wst_...`, время жизни 30 сек).
2. При установлении WebSocket-соединения билет передается через стандартный RFC 6455 заголовок подпротокола:
   ```
   Sec-WebSocket-Protocol: bearer, wst_abc123...
   ```
   (Fallback: при невозможности задать заголовки допускается query-параметр `?token=wst_...`).
3. Бэкенд гасит билет в `consume_ws_ticket(ticket)` и связывает сессию с идентификатором пользователя `user_id`.

### Динамический RBAC для подписок на топики
При отправке клиентских команд подписки (`subscribe`) бэкенд выполняет функцию `can_subscribe_to_topic(user_id, topic)`:
- Суперадминистраторы (`system.admin` / `system.all`) обладают полным доступом ко всем топикам.
- Доступ пользователей проверяется по разрешениям `<topic_name>` или `<resource>.view`.
- Доступ к защищенным ресурсам (`audit`, `logs`, `users`, `system`, `security`) без наличия соответствующих прав блокируется с возвратом ошибки `403 Permission Denied`.

### Лимиты ресурсов и защита от атак (DOS/OOM)
| Лимит | Значение | Код закрытия | Поведение |
| :--- | :--- | :--- | :--- |
| **Max Frame Size** | `64 KB` (65536B) | `1009` | Закрытие при превышении размера кадра |
| **Rate Limit** | `50 msg/sec` | `4029` | Закрытие при превышении лимита сообщений в секунду |
| **Max Connections** | `10 conn/user` | `4008` | Закрытие при превышении лимита сессий пользователя |
| **JSON Error Limit** | `5 errors` | `4000` | Закрытие при передаче битых JSON кадров |

### Гарантия доставки и Восстановление Истории (Event Journal & Replay)
1. Все события журналируются асинхронной очередью `EventJournalQueue` в таблицу SQLite `system_events_journal`.
2. При переподключении клиент передает сообщение `{"type": "resume", "last_event_id": 1420}`.
3. Бэкенд с помощью `check_replay_status_from_db` досылает пропущенные события с учетом прав доступа и подписок.
4. Функция `prune_system_events_journal()` сбрасывает устаревшие логи старше 7 дней или при превышении 50 000 строк.

### Протокол кодирования MsgPack
Для снижения трафика поддерживается бинарный протокол MsgPack (`?protocol=msgpack`). На фронтенде кодирование/декодирование выполняется прозрачно библиотекой `@msgpack/msgpack`.

### Аутентификация по JWT Токену
Все WebSocket-эндпоинты (`/api/events/ws` и `/api/system/logs/{log_name}/stream`) требуют обязательной аутентификации. Передача JWT-токена поддерживается двумя способами:
1. **Заголовок субпротокола (`Sec-WebSocket-Protocol`)** *(Основой и рекомендуемый способ)*:
   ```typescript
   new WebSocket(wsUrl, ['bearer', token])
   ```
2. **Query-параметр `token`** *(Fallback для обратной совместимости)*:
   ```
   wss://<host>:<port>/api/events/ws?token=<JWT_ACCESS_TOKEN>
   ```

> [!IMPORTANT]
> Подключения без валидного токена или с истёкшим токеном автоматически отклоняются сервером с кодом `1008 (Unauthorized)`.

### Защита от CSWSH (Cross-Site WebSocket Hijacking) и Origin Check
При каждом подключении WebSocket бэкенд извлекает заголовок `Origin` и проверяет его через утилиту `is_origin_allowed(origin)` со списком разрешенных доменов (`get_allowed_cors_origins()`, задаваемым в `NMS_CORS_ORIGINS`). 
Запросы с недовластных или сторонних сайтов отклоняются с кодом `1008 (Forbidden Origin)`.

### Динамический SECRET_KEY и Проверка Отзыва Сессий (`is_session_revoked`)
1. **Динамический ключ подписи**: Секрет JWT-токенов загружается из переменной `NMS_SECRET_KEY` или персистентного файла `data/secret.key` (права `0600`), автоматически создаваемого при первом старте.
2. **Проверка при Handshake**: При подключении к сокету извлекается `jti` токена и проверяется статус отзыва сессии в БД (`active_sessions.is_revoked`).
3. **Фоновый мониторинг сессий**: В фоновом 30-секундном цикле `_heartbeat_loop` происходит постоянная перепроверка `is_session_revoked(jti)`. При аннулировании сессии администратором сокет немедленно закрывается с кодом `1008`.

### Graceful Shutdown (Корректная остановка WS)
При остановке бэкенда (`lifespan` в `core/app.py`) методы `ws_manager.close_all()` и `shared_log_stream_manager.close_all()` автоматически рассылают всем активным клиентам код закрытия `1001 (Going Away)`, избавляя клиенты от ожидания таймаутов.

### Единый клиентский слой на фронтенде (`createWsClient`)
Все WebSocket-подключения на фронтенде производятся исключительно через единую утилиту `createWsClient()` в `frontend/src/core/websocket.ts`:
* **Same-Origin Restriction (`sanitizeWsUrl`)**: Гарантирует, что подсоединения происходят строго к текущему хосту приложения (`window.location.host`).
* **Exponential Backoff**: Автоматический реконнект при обрыве связи с экспоненциальной задержкой и джиттером.
* **Heartbeat**: Автоматическая отправка `ping` каждые 30 секунд.
�ухрежимная рассылка событий (Immediate vs Batched)
1. **Мгновенная рассылка (`broadcast_immediate`)**: Для алармов и критических статусов (0 мс задержки, без ожидания батч-таймера).
2. **Пакетная рассылка (`broadcast_batched`)**: Для телеметрии и логов. Сообщения накапливаются во временной очереди и отправляются пачками каждые 100 мс (`{"type": "batch", "events": [...]}`).

### Двухсторонний Сердечный ритм (Ping-Pong Heartbeat)
- Бэкенд и клиент поддерживают двухсторонний Heartbeat: отправка `ping` каждые 30 секунд и авточистка неактивных сокетов при отсутствии ответа > 60 секунд.

### Фронтенд: Мульти-вкладки (Multi-Tab Leader Election)
- При открытии нескольких вкладок NMS WebUI выбирается **Leader Tab**, которая открывает единственный реальный WebSocket к бэкенду. Ведомые вкладки получают события от Лидера через `BroadcastChannel`. При закрытии Лидера оставшиеся вкладки за 300 мс выбирают нового лидера.
авто-подключением при появлении подписчиков (`subscriberCount`).
   - Поддержка реактивных состояний `isConnected`, `lastEvent`.
   - Автоматическая отписка listener'ов при размонтировании Vue-компонентов (`onUnmounted`).
   - Глобальный интерфейс `window.NMS.events` для обеспечения работы микрофронтенд-виджетов, загружаемых на лету без содействия сборщика Vite.

---

## 🔐 2. Аутентификация, безопасность и жизненный цикл подключения

### Ticket-Based Auth (Одноразовые билеты) и RFC 6455 Subprotocol
Для исключения утечки длительных JWT access-токенов в URL/Query-строках в NMS WebUI реализована аутентификация по одноразовым билетам:
1. Клиент выполняет REST-запрос `POST /api/auth/ws-ticket` и получает короткоживущий билет (`wst_...`, время жизни 30 сек).
2. При установлении WebSocket-соединения билет передается через стандартный RFC 6455 заголовок подпротокола:
   ```
   Sec-WebSocket-Protocol: bearer, wst_abc123...
   ```
   (Fallback: при невозможности задать заголовки допускается query-параметр `?token=wst_...`).
3. Бэкенд гасит билет в `consume_ws_ticket(ticket)` и связывает сессию с идентификатором пользователя `user_id`.

### Динамический RBAC для подписок на топики
При отправке клиентских команд подписки (`subscribe`) бэкенд выполняет функцию `can_subscribe_to_topic(user_id, topic)`:
- Суперадминистраторы (`system.admin` / `system.all`) обладают полным доступом ко всем топикам.
- Доступ пользователей проверяется по разрешениям `<topic_name>` или `<resource>.view`.
- Доступ к защищенным ресурсам (`audit`, `logs`, `users`, `system`, `security`) без наличия соответствующих прав блокируется с возвратом ошибки `403 Permission Denied`.

### Лимиты ресурсов и защита от атак (DOS/OOM)
| Лимит | Значение | Код закрытия | Поведение |
| :--- | :--- | :--- | :--- |
| **Max Frame Size** | `64 KB` (65536B) | `1009` | Закрытие при превышении размера кадра |
| **Rate Limit** | `50 msg/sec` | `4029` | Закрытие при превышении лимита сообщений в секунду |
| **Max Connections** | `10 conn/user` | `4008` | Закрытие при превышении лимита сессий пользователя |
| **JSON Error Limit** | `5 errors` | `4000` | Закрытие при передаче битых JSON кадров |

### Гарантия доставки и Восстановление Истории (Event Journal & Replay)
1. Все события журналируются асинхронной очередью `EventJournalQueue` в таблицу SQLite `system_events_journal`.
2. При переподключении клиент передает сообщение `{"type": "resume", "last_event_id": 1420}`.
3. Бэкенд с помощью `check_replay_status_from_db` досылает пропущенные события с учетом прав доступа и подписок.
4. Функция `prune_system_events_journal()` сбрасывает устаревшие логи старше 7 дней или при превышении 50 000 строк.

### Протокол кодирования MsgPack
Для снижения трафика поддерживается бинарный протокол MsgPack (`?protocol=msgpack`). На фронтенде кодирование/декодирование выполняется прозрачно библиотекой `@msgpack/msgpack`.

### Аутентификация по JWT Токену
Так как стандартный браузерный API `new WebSocket(url)` не позволяет передавать пользовательские HTTP-заголовки (Headers) при рукопожатии (Handshake), авторизация осуществляется через Query-параметр `token`:

```
ws://<host>:<port>/api/events/ws?token=<JWT_ACCESS_TOKEN>
```

При подключении бэкенд извлекает токен и выполняет его декодирование:
- Если токен валиден, из поля `sub` извлекается идентификатор пользователя `user_id`. Соединение регистрируется как персональное (`active_connections[websocket] = user_id`).
- Если токен отсутствует или невалиден, соединение сохраняется как анонимное/публичное (`user_id = None`).

### Актуализация JWT-токенов при переподключении (Re-authentication)
- Клиентская подсистема `useWebSocket` при открытии каждого нового соединения обращается к актуальному токену через функцию `getStoredToken()`.
- При повторном входе пользователя в систему или смене авторизации существующее соединение принудительно перезапускается, что гарантирует мгновенную актуализацию `user_id` на стороне бэкенда.

### Сердечный ритм (Ping-Pong Heartbeat)
Для предотвращения разрыва соединения прокси-серверами (Nginx, Traefik) по таймауту и обнаружения "зависших" клиентов используется механизм Heartbeat:
1. Фронтенд (`useWebSocket.ts`) каждые **25 секунд** отправляет строковое сообщение `"ping"`.
2. Бэкенд (`events.py`) принимает сообщение, идентифицирует `"ping"` и незамедлительно возвращает JSON-ответ `{"type": "pong"}`.
3. Если сокет закрывается или выбрасывает исключение, бэкенд автоматически вычищает его из реестра `ConnectionManager`.

### Автоматическое переподключение (Reconnection Strategy)
Клиентская часть ведет учет активных подписчиков (`subscriberCount`):
- Когда первый компонент запрашивает подписку, открывается WebSocket-соединение.
- В случае разрыва связи (`onclose`), если `subscriberCount > 0`, каждые **5 секунд** предпринимается попытка повторного подключения.
- Когда последний подписчик отписывается (например, пользователь перешел на страницу без real-time элементов), соединение корректно закрывается (`ws.close()`), а таймеры очищаются для экономии ресурсов клиентского браузера.

---

## 📢 3. Бэкенд API: Рассылка событий через SDK (`ctx.broadcast`) и `broadcaster`

Согласно правилам интеграции модулей («всё, что требует `module_id` или вещания событий из модуля — через `ctx`»), модули осуществляют отправку WebSocket событий напрямую через методы `context.broadcast()` или `context.events.publish()`.

### Сигнатура метода `context.broadcast()`

```python
self.context.broadcast(
    payload: dict[str, Any] | str,
    target_user_id: str | None = None
)
```

| Параметр | Тип | Описание |
| :--- | :--- | :--- |
| `payload` | `dict \| str` | Словарь с данными или JSON-строка события для отправки клиентам. |
| `target_user_id` | `Optional[str]` | ID целевого пользователя. Если `None` — рассылка всем клиентам. Если `str` — адресная доставка. |

---

### Примеры использования бэкенд API модулями

#### 1. Рассылка телеметрииВсем клиентам из модуля
```python
# Публикация обновления датчика от имени модуля
self.context.broadcast({
    "type": "telemetry_update",
    "module_id": self.context.module_id,
    "sensor_id": "sns-01",
    "values": {"temperature": 24.5, "humidity": 58.2},
    "timestamp": "2026-08-07T22:00:00Z"
})
```

#### 2. Адресная отправка персонального уведомления пользователю
```python
# Событие будет доставлено только сессиям пользователя с target_user_id
self.context.broadcast(
    payload={
        "type": "personal_alert",
        "title": "Задача завершена",
        "message": "Экспорт отчета готов к скачиванию"
    },
    target_user_id="usr_admin"
)
```

#### 3. Трансляция прогресса выполнения фоновой задачи модуля
```python
def execute_long_backup_task(ctx: ModuleContext, task_id: str, target_user: str):
    total_steps = 10
    for step in range(1, total_steps + 1):
        ctx.broadcast(
            payload={
                "type": "backup_progress",
                "task_id": task_id,
                "progress": step * 10
            },
            target_user_id=target_user
        )
        # Выполняем шаг длительной задачи...
        progress_pct = int((step / total_steps) * 100)
        
        # Отправляем обновленный прогресс по WebSocket
        broadcaster.broadcast(
            data_dict={
                "type": "task_progress",
                "task_id": task_id,
                "progress": progress_pct,
                "status": "processing" if step < total_steps else "completed"
            },
            target_user_id=target_user
        )
```

#### 4. Системное уведомление об изменении настроек модуля
В бэкенде предусмотрена вспомогательная функция `notify_settings_changed`:

```python
from backend.core.events import notify_settings_changed

# Уведомляет все клиенты об изменении конфигурации модуля и создает запись в ленте уведомлений
notify_settings_changed(module_id="device_manager")
```

---

## 🎯 4. Создание кастомных WebSocket эндпоинтов модуля

Если модулю недостаточно общего вещания Pub/Sub и требуется двухсторонний интерактивный канал (например, эмулятор CLI-терминала, потоковый логгер устройства или высокочастотный интерфейс), модуль может объявить собственный WebSocket эндпоинт в своем `api.py`.

### Пример кастомного WS-эндпоинта модуля

```python
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from backend.core.auth import decode_access_token

router = APIRouter(prefix="/api/v1/m/sensor_monitor", tags=["sensor_monitor"])

@router.websocket("/ws/stream")
async def sensor_stream_endpoint(
    websocket: WebSocket,
    token: str = Query(None)
):
    # 1. Аутентификация при необходимости
    user_id = None
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")

    # 2. Принятие соединения
    await websocket.accept()
    
    try:
        while True:
            # Двухсторонний обмен: ожидаем команду от клиента
            client_data = await websocket.receive_json()
            command = client_data.get("command")
            
            if command == "get_instant_readings":
                # Отправляем ответ клиенту
                await websocket.send_json({
                    "status": "ok",
                    "voltage": 220.4,
                    "current": 1.5
                })
            elif command == "ping":
                await websocket.send_json({"type": "pong"})
                
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        # Клиент отключился - освобождаем ресурсы
        pass
    except Exception as err:
        await websocket.close(code=1011, reason=str(err))
```

---

## ⚡ 5. Фронтенд API: Composable `useWebSocket` (Vue 3)

На фронтенде работу с событиями реального времени обеспечивает Composable `useWebSocket`. Он предоставляет реактивные переменные и хелперы подписки с поддержкой автоматического очищения ресурсов.

```typescript
import { useWebSocket } from '@/composables/useWebSocket'
```

### Справочник методов и переменных `useWebSocket()`

| Метод / Переменная | Тип | Описание |
| :--- | :--- | :--- |
| `isConnected` | `Ref<boolean>` | Реактивный флаг: `true` — сокет подключен и готов к работе. |
| `lastEvent` | `Ref<any>` | Реактивная ссылка на последнее полученное по WS событие (десериализованный JSON). |
| `onEvent(type, callback)` | `<T>(type: string \| null, cb: (data: T) => void) => () => void` | Регистрирует обработчик событий. Если передан `type`, фильтрует по `data.type`. **Автоматически отписывается** при размонтировании компонента. Возвращает функцию ручной отписки. |
| `subscribe(type, callback)`| `<T>(type: string \| null, cb: (data: T) => void) => () => void` | Низкоуровневая подписка вне setup-контекста Vue. Увеличивает счетчик `subscriberCount`. |
| `send(data)` | `(data: string \| object) => boolean` | Отправляет текстовую строку или JSON-объект на бэкенд. Возвращает `true` при успешной отправке. |

### Примеры использования во Vue 3 компонентах

#### Пример 1: Строго типизированная подписка на обновления телеметрии в `<script setup>`

```vue
<template>
  <div class="telemetry-card">
    <div class="status-header">
      <span>Статус соединения:</span>
      <span :class="['badge', isConnected ? 'online' : 'offline']">
        {{ isConnected ? 'Подключено' : 'Переподключение...' }}
      </span>
    </div>

    <div v-if="telemetryData" class="readings">
      <p>Датчик: {{ telemetryData.sensor_id }}</p>
      <p>Температура: {{ telemetryData.values?.temperature }} °C</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

// Определяем интерфейс события
interface TelemetryPayload {
  type: 'telemetry_update'
  module_id: string
  sensor_id: string
  values: { temperature: number; humidity: number }
}

const { isConnected, onEvent } = useWebSocket()
const telemetryData = ref<TelemetryPayload | null>(null)

// Подписываемся с авто-отпиской при unmount компонента
onEvent<TelemetryPayload>('telemetry_update', (data) => {
  telemetryData.value = data
})
</script>

<style scoped>
.badge.online { color: #4caf50; }
.badge.offline { color: #f44336; }
</style>
```

#### Пример 2: Синхронизация состояния с Pinia Store

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { subscribe } from '@/composables/useWebSocket'

export const useNotificationStore = defineStore('notifications', () => {
  const unreadCount = ref(0)

  // Глобальная подписка на системный поток notifications
  subscribe('notification', (data) => {
    if (data.notification) {
      unreadCount.value++
    }
  })

  return { unreadCount }
})
```

---

## 🌐 6. Глобальный клиентский API (`window.NMS.events`)

Для динамических модулей, микрофронтенд-виджетов и кастомных скриптов, загружаемых в рантайме браузера без возможности использования ES-импортов Vite (`import { useWebSocket } ...`), платформа экспортирует объекты в глобальную область видимости `window.NMS.events`.

```javascript
// Глобальная точка доступа в браузере
window.NMS.events = {
  subscribe,   // (eventType, callback) => unsubscribeFn
  send,        // (data) => boolean
  useWebSocket,// Composable функция
  isConnected, // Ref<boolean>
  lastEvent    // Ref<any>
}
```

### Пример использования в стороннем/динамическом виджете (Plain JS / HTML5 Widget)

```javascript
// Код динамического виджета, загруженного через <script> или eval
(function() {
  if (!window.NMS || !window.NMS.events) return;

  // Подписываемся на события изменения настроек модулей
  const unsubscribe = window.NMS.events.subscribe('module_settings_changed', function(data) {
    console.log('[Dynamic Widget] Настройки модуля изменены:', data.module_id);
    // Обновляем UI виджета...
  });

  // Если виджет удаляется со страницы:
  // unsubscribe();
})();
```

---

## 📋 7. Реестр системных типов событий, именование и схемы

### Соглашение по именованию событий (Event Namespacing)
Для исключения коллизий между модулями рекомендуется следовать иерархическому стандарту именования:

- **Системные события ядра:** `<action_or_type>` (например, `notification`, `ping`, `pong`).
- **События кастомных модулей:** `<module_id>:<entity>:<action>` (например, `sensor_monitor:device:online`, `backup_manager:task:progress`).

### Стандартные типы событий ядра NMS WebUI

| Тип события (`type`) | Направление | Описание |
| :--- | :--- | :--- |
| `notification` | Server → Client | Новое системное или персональное уведомление. |
| `module_settings_changed` | Server → Client | Изменены настройки модуля `module_id`. |
| `telemetry_update` | Server → Client | Данные живой телеметрии с датчиков/устройств. |
| `task_progress` | Server → Client | Статус выполнения фоновой задачи. |
| `ping` | Client → Server | Heartbeat запрос от клиента. |
| `pong` | Server → Client | Heartbeat ответ от сервера. |

### JSON-схемы полезной нагрузки (Payload Examples)

#### 1. Событие `notification`
```json
{
  "type": "notification",
  "notification": {
    "id": 42,
    "title": "Перегрузка CPU",
    "message": "Загрузка процессора узла core-router-01 превысила 90%",
    "notification_type": "warning",
    "category": "telemetry",
    "user_id": null,
    "read": false,
    "created_at": "2026-08-07T22:01:00Z"
  }
}
```

#### 2. Событие `task_progress`
```json
{
  "type": "task_progress",
  "task_id": "task-bk-902",
  "progress": 65,
  "status": "processing"
}
```

---

## 🧪 8. Тестирование, отладка и деплоймент WebSockets

### Автоматическое тестирование (Backend Pytest & Frontend Vitest)

В проекте реализованы модульные и интеграционные тесты WebSocket-подсистемы:

#### 1. Бэкенд тесты (`tests/test_websocket_enhancements.py`)
Запуск: `pytest tests/test_websocket_enhancements.py -v`
Покрывают:
- Ticket-auth и генерацию билетов.
- Защиту CSWSH (проверка Origin).
- RBAC-проверку прав подписки на топики (`can_subscribe_to_topic`).
- Лимиты размера кадра (64KB) и Rate Limiting (50 msg/s).
- MsgPack кодирование и восстановление истории Replay из `system_events_journal`.

#### 2. Фронтенд тесты (`frontend/src/core/__tests__/websocket.test.ts`)
Запуск: `npm --prefix frontend run test -- src/core/__tests__/websocket.test.ts`
Покрывают:
- Валидацию и очистку URL (`sanitizeWsUrl`).
- Очередь отправки FIFO при отсоединенном сокете (`maxQueueSize = 100`).
- Измерение сетевой задержки RTT при обмене Ping/Pong.
- Увеличенный Exponential Backoff при кодах `4008` / `4029`.

### Automated Testing (Pytest + FastAPI TestClient)

Для интеграционного тестирования WebSocket-эндпоинтов в `pytest` используется встроенный метод `websocket_connect` объекта `TestClient`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.events import broadcaster, ws_manager

client = TestClient(app)

def test_websocket_ping_pong():
    with client.websocket_connect("/api/events/ws") as websocket:
        # Отправляем ping
        websocket.send_text("ping")
        # Получаем pong
        data = websocket.receive_json()
        assert data["type"] == "pong"

def test_broadcaster_event_reception():
    with client.websocket_connect("/api/events/ws") as websocket:
        # Генерируем событие через broadcaster
        broadcaster.broadcast(data_dict={"type": "test_event", "payload": "hello"})
        
        # Проверяем получение клиентом
        data = websocket.receive_json()
        assert data["type"] == "test_event"
        assert data["payload"] == "hello"
```

### Конфигурация Reverse Proxy (Nginx Config)

При развертывании NMS WebUI за Nginx убедитесь, что включены HTTP/1.1 Upgrade заголовки и увеличен `proxy_read_timeout`:

```nginx
location /api/events/ws {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    
    # Отключаем обрыв длительных сокет-сессий по простою
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}
```

### Отладка в Chrome DevTools

1. Откройте панель разработчика Chrome (F12) -> вкладка **Network** (Сеть).
2. Установите фильтр **WS** (WebSockets).
3. Выберите соединение `ws` (или `/api/events/ws`).
4. Перейдите на вкладку **Messages** (Сообщения):
   - Зеленые стрелки вверх (`^`) — данные, отправленные клиентом (`ping` каждые 25с).
   - Красные/красно-белые стрелки вниз (`v`) — входящие события бэкенда (`{"type":"pong"}`, `{"type":"notification"}`, etc.).

---

## 🛡 9. Лучшие практики и предупреждения

> [!CAUTION]
> **Утечки памяти на фронтенде**: Всегда используйте `onEvent` внутри `setup()` / `<script setup>`, либо сохраняйте возвращаемую функцию `unsubscribe` при использовании `subscribe` и вызывайте ее в хуках уничтожения компонентов (`onUnmounted`, `beforeUnmount`). Забытые подписки приводят к накоплению дублирующихся callback-обработчиков.

> [!TIP]
> **Принцип минимального трафика**: Избегайте передачи избыточных гигабайтных структур данных каждые несколько миллисекунд по общему каналу events. Для тяжелых потоков данных (например, видеостриминг или мегабайтные логи) создавайте отдельные модульные WS-эндпоинты.

> `ponytail:` *Процессный лимит масштабирования*: Текущая реализация `ConnectionManager` хранит активные WebSocket соединения в оперативной памяти текущего процесса Python/Uvicorn. При будущем горизонтальном масштабировании на несколько процессов/воркеров (`gunicorn -w 4 -k uvicorn.workers.UvicornWorker`) требуется подключение брокера сообщений **Redis Pub/Sub** (или `aioredis`) для трансляции сообщений между процессами.
