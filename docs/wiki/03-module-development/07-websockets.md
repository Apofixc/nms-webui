# ⚡ 7. Использование WebSockets (WS API)

---

## 📌 Архитектура событий реального времени

Подсистема реального времени ([events.py](file:///opt/nms-webui/backend/core/events.py)) работает через протокол WebSockets (`ws://<host>:<port>/api/events/ws?token=<JWT>`).

---

## 📢 Трансляция событий через `broadcaster`

Для вещания событий в браузеры пользователей используйте глобальный синглтон `broadcaster`:

```python
from backend.core.events import broadcaster

# Рассылка данных живой телеметрии
broadcaster.broadcast(
    data_dict={
        "type": "telemetry_update",
        "sensor_id": "sns_01",
        "temperature": 24.5,
        "humidity": 60
    },
    target_user_id=None # None = всем подключенным клиентам
)
```

---

## 🎯 Прямой WebSocket эндпоинт модуля

Модуль может объявить собственный кастомный WS-эндпоинт в `api.py`:

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api/v1/m/sensor_monitor", tags=["sensor_monitor"])

@router.websocket("/ws/stream")
async def stream_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"val": 42.0})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
```
