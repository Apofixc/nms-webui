# 🔔 7. Использование уведомлений (Notifications API)

---

## 📌 Подсистема уведомлений

Уведомления (`notifications_api.py`) сохраняются в системной базе данных SQLite и мгновенно доставляются браузерным клиентам по WebSockets.

---

## 📩 Отправка уведомления из модуля

Используйте метод `context.notify()`:

```python
self.context.notify(
    title="Отказ оборудования",
    message="Датчик 'Сенсор-01' превысил порог температуры 85°C",
    notification_type="error",  # "info" | "success" | "warning" | "error"
    category="telemetry",        # Категория
    link="/sensor-monitor/device/sns_01", # Ссылка в UI
    user_id=None                 # None = для всех пользователей
)
```

---

## 🛠 Вызов вне контекста (`create_notification`)

Если контекст не доступен (например, из фонового Celery-таска), используйте глобальную функцию:

```python
from backend.core.notifications_api import create_notification

create_notification(
    title="Бэкап завершен",
    message="Резервная копия базы данных успешно создана",
    notification_type="success",
    category="system"
)
```
