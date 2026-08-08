# ⚡ 9. Использование WebSockets (WS API)

---

## 📌 1. Архитектура событий реального времени

Подсистема событий реального времени NMS WebUI обеспечивает двухсторонний обмен сообщениями с низкими задержками между бэкендом (FastAPI) и фронтендом (Vue 3 / dynamic runtime components). В качестве основного транспорта используется протокол **WebSockets** (`ws://` / `wss://`).

```
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
│             │  EventBroadcaster.broadcast│                                   │
│             └─────────────┬─────────────┘                                   │
│                           │ (loop.create_task / run_coroutine_threadsafe)   │
│                           ▼                                                 │
│             ┌───────────────────────────┐                                   │
│             │   ConnectionManager (Async)│                                   │
│             │   ws_manager.broadcast_json│                                   │
│             └─────────────┬─────────────┘                                   │
│                           │                                                 │
│                           ▼                                                 │
│             ┌───────────────────────────┐                                   │
│             │  FastAPI WebSocket Route  │                                   │
│             │  /api/events/ws?token=JWT │                                   │
│             └─────────────┬─────────────┘                                   │
└───────────────────────────┼─────────────────────────────────────────────────┘
                            │ WS Protocol (JSON / Ping-Pong)
                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Окружение Фронтенда                              │
│                                                                             │
│             ┌───────────────────────────┐                                   │
│             │   useWebSocket Composable │                                   │
│             │   (Singleton WS Instance) │                                   │
│             └─────────────┬─────────────┘                                   │
│                           │                                                 │
│             ┌─────────────┼─────────────────────────┐                       │
│             ▼             ▼                         ▼                       │
│ ┌──────────────────┐ ┌───────────────────────┐ ┌──────────────────────────┐ │
│ │ Vue 3 Components │ │ Pinia Store State     │ │ window.NMS.events        │ │
│ │ (Notification,   │ │ (Notifications,       │ │ (Dynamic Runtime         │ │
│ │  Telemetry Card) │ │  Live Topology)       │ │  Widgets & Plugins)      │ │
│ └──────────────────┘ └───────────────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Ключевые компоненты подсистемы:

1. **`backend/core/events.py`**:
   - `ConnectionManager` (`ws_manager`): Асинхронный менеджер подключений. Отвечает за хранение активных сокетов `active_connections: Dict[WebSocket, Optional[str]]`, фильтрацию по `user_id` и рассылку JSON.
   - `EventBroadcaster` (`broadcaster`): Потокобезопасный синглтон-броадкастер. Позволяет отправлять события из синхронного кода, методов модулей и фоновых задач без блокировки asyncio-петли.
   - `@router.websocket("/ws")`: Главный WebSocket-эндпоинт системы (доступен по URL `/api/events/ws`).
   - `@router.get("")`: Информационный REST-эндпоинт (возвращает статус транспорта `status: "online"`).
2. **`frontend/src/composables/useWebSocket.ts`**:
   - Единый клиентский синглтон-клиент с авто-подключением при появлении подписчиков (`subscriberCount`).
   - Поддержка реактивных состояний `isConnected`, `lastEvent`.
   - Автоматическая отписка listener'ов при размонтировании Vue-компонентов (`onUnmounted`).
   - Глобальный интерфейс `window.NMS.events` для обеспечения работы микрофронтенд-виджетов, загружаемых на лету без содействия сборщика Vite.

---

## 🔐 2. Аутентификация, безопасность и жизненный цикл подключения

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

## 📢 3. Бэкенд API: Рассылка событий через `broadcaster`

Для вещания событий из любых компонентов бэкенда (модулей, фоновых задач, REST-контроллеров) используется синглтон `broadcaster`.

```python
from backend.core.events import broadcaster
```

### Сигнатура метода `broadcast()`

```python
broadcaster.broadcast(
    message: str = "",
    data_dict: Optional[dict] = None,
    target_user_id: Optional[str] = None
)
```

| Параметр | Тип | Описание |
| :--- | :--- | :--- |
| `message` | `str` | Строка сообщения в формате JSON. Если `data_dict` не передан, пытаемся распарсить эту строку. |
| `data_dict` | `dict` | Словарь с данными события. Рекомендуемый формат для передачи structured payloads. |
| `target_user_id` | `Optional[str]` | ID целевого пользователя. Если `None` — рассылка выполнится **всем** подключенным клиентам. Если указан str — событие получит **только** указанный пользователь. |

> [!NOTE]
> Если `target_user_id` не передан явным образом, `broadcaster` автоматически проверяет наличие поля `data_dict["notification"]["user_id"]`. Если оно существует, вещание автоматически становится адресным.

### Примеры использования бэкенд API

#### 1. Рассылка телеметрии всем клиентам
```python
from backend.core.events import broadcaster

# Публикация обновления датчика
broadcaster.broadcast(
    data_dict={
        "type": "telemetry_update",
        "module_id": "sensor_monitor",
        "sensor_id": "sns-01",
        "values": {"temperature": 24.5, "humidity": 58.2},
        "timestamp": "2026-08-07T22:00:00Z"
    }
)
```

#### 2. Адресная отправка персонального уведомления
```python
from backend.core.events import broadcaster

# Событие будет доставлено только сессии пользователя с user_id="usr_admin"
broadcaster.broadcast(
    data_dict={
        "type": "personal_alert",
        "title": "Задача завершена",
        "message": "Экспорт отчета готов к скачиванию"
    },
    target_user_id="usr_admin"
)
```

#### 3. Трансляция прогресса выполнения фоновой задачи
В фоновых задачах `broadcaster.broadcast` позволяет отправлять статус выполнения без блокировки воркера:

```python
from backend.core.events import broadcaster

def execute_long_backup_task(task_id: str, target_user: str):
    total_steps = 10
    for step in range(1, total_steps + 1):
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
