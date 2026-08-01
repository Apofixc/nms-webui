# Событийная модель, WebSockets и SSE

Руководство по архитектуре реального времени, броадкастингу событий и подпискам клиентов в NMS WebUI.

---

## ⚡ Обзор событийной архитектуры

NMS WebUI поддерживает передачу оперативных событий (изменение метрик, сработка тревог, обновление настроек модулей) в браузер в реальном времени через два протокола:

1. **Server-Sent Events (SSE)**: Однонаправленный стрим событий от сервера к клиенту (`GET /api/events`).
2. **WebSockets (WS)**: Двунаправленный канал связи (`WS /api/events/ws`).

Подсистема реализована в модуле `backend/core/events.py`.

---

## 🐍 Шина событий на Backend

Бэкенд предоставляет класс `EventBroadcaster` и синглтон `broadcaster` для рассылки событий всем подсоединенным клиентам.

### Отправка уведомлений из модуля:

```python
from backend.core.events import broadcaster

# Рассылка произвольного события
event_payload = {
    "type": "device_status_changed",
    "module_id": "tuya",
    "device_id": "dev-102",
    "status": "online"
}

# Отправляет событие как в SSE, так и в активные WebSocket-сессии
broadcaster.broadcast(
    message=json.dumps(event_payload),
    data_dict=event_payload
)
```

### Специализированный хелпер изменения настроек:

```python
from backend.core.events import notify_settings_changed

# Вызывается при успешном сохранении настроек модуля
notify_settings_changed("tuya")
```

---

## 🌐 Клиентские подписки (Frontend Vue 3)

### 1. Подключение по WebSocket (`/api/events/ws`)

```typescript
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const wsUrl = `${wsProtocol}//${window.location.host}/api/events/ws`

const socket = new WebSocket(wsUrl)

socket.onopen = () => {
  console.log('WebSocket connection established')
}

socket.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'module_settings_changed') {
    console.log('Settings changed for module:', data.module_id)
  }
}

// Отправка ping для поддержания соединения
setInterval(() => {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send('ping')
  }
}, 30000)
```

### 2. Подключение по SSE (`/api/events`)

```typescript
const eventSource = new EventSource('/api/events')

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data)
  console.log('Received SSE event:', data)
}

eventSource.onerror = (err) => {
  console.error('SSE Error:', err)
  eventSource.close()
}
```

---

## 🔒 Безопасность и оптимизация сетевых ресурсов

> [!IMPORTANT]
> 1. Все вещания происходят асинхронно без блокировки основного потока FastAPI (используется `asyncio.Queue` и `create_task`).
> 2. Отключенные клиенты автоматически удаляются из списков рассылок `ConnectionManager` при возникновении ошибок сокета.
