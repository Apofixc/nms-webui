# 🧩 04. Системные подсистемы: Исключения, Уведомления, Логирование и WebSockets

---

## 🚨 Обработка исключений (`NMSError`)

Все ошибки модуля должны наследоваться от `NMSError` ([backend/core/exceptions.py](file:///opt/nms-webui/backend/core/exceptions.py)):

```python
from backend.core.exceptions import NotFoundError, ValidationError

if not device:
    raise NotFoundError(message="Device not found", code="DEVICE_NOT_FOUND")
```

---

## 🔔 Отправка уведомлений (`context.notify()`)

Модуль создает системные и пользовательские уведомления:

```python
self.context.notify(
    title="Отказ питания",
    message="Превышен порог температуры сенсора 01",
    notification_type="error",  # "info" | "success" | "warning" | "error"
    category="telemetry"
)
```

---

## 🪵 Изолированное логирование (`context.logger`)

Каждый модуль имеет собственный изолированный логгер `nms.plugin.<module_id>`:

```python
self.context.logger.info("Service started successfully")
self.context.logger.error("Polling error", exc_info=True)
```

---

## ⚡ События в реальном времени (`EventBroadcaster`)

Для отправки сообщений по WebSockets клиентам используется `broadcaster`:

```python
from backend.core.events import broadcaster

broadcaster.broadcast(
    data_dict={"type": "telemetry_update", "temp": 24.5},
    target_user_id=None
)
```
