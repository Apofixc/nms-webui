# 🛡 14. Журнал аудита безопасности и системные события (Audit & Events)

---

## 🛡 Журнал аудита безопасности (`log_audit_event`)

Все критические и административные действия модуля (изменение параметров оборудования, сброс настроек, деактивация датчиков, удаление логов) **обязаны** регистрироваться в немодифицируемом Журнале Аудита (`backend/core/audit.py`).

### Запись события безопасности:

```python
from fastapi import Request, Depends
from backend.core.audit import log_audit_event
from backend.core.auth import CurrentUser

@router.post("/sensors/{sensor_id}/reset")
async def reset_sensor(
    sensor_id: str,
    request: Request,
    user: dict = Depends(CurrentUser)
):
    # Выполнение сброса...
    
    # Регистрация события аудита
    log_audit_event(
        user_id=user["username"],
        action="SENSOR_HARD_RESET",
        target=f"sensor:{sensor_id}",
        details={"sensor_id": sensor_id, "timestamp": time.time()},
        ip_address=request.client.host
    )
    return {"status": "success"}
```

---

## 📐 Параметры функции `log_audit_event`

| Параметр | Тип | Описание |
| :--- | :--- | :--- |
| `user_id` | `str` | Имя пользователя или системный ID инициатора действия. |
| `action` | `str` | Системный код действия в UPPER_SNAKE_CASE (например: `MODULE_CONFIG_UPDATE`). |
| `target` | `str` | Идентификатор объекта (например: `device:192.168.1.10`). |
| `details` | `dict` | Произвольный JSON-словарь подробностей изменения. |
| `ip_address` | `str \| None` | IP-адрес клиента, вызвавшего действие. |
