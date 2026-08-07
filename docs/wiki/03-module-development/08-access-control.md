# 🔐 8. Уровни доступа и RBAC (Permissions API)

---

## 📌 Ролевое разграничение прав доступа (RBAC)

Модули объявляют свои атомарные разрешения в файле манифеста `manifest.yaml` ([auth.py](file:///opt/nms-webui/backend/core/auth.py)):

```yaml
permissions:
  - id: "module.sensor_monitor.view"
    name: "Просмотр датчиков"
    category: "Sensors"
  - id: "module.sensor_monitor.control"
    name: "Управление датчиками"
    category: "Sensors"
```

При загрузке плагина права автоматически регистрируются в системе и становятся доступны для назначения ролям пользователей.

---

## 🛡 Защита REST API эндпоинтов

Для защиты роутов бэкенда используйте функции `Depends(require_permission(...))` и `Depends(CurrentUser)`:

```python
from fastapi import APIRouter, Depends
from backend.core.auth import CurrentUser, require_permission

router = APIRouter(prefix="/api/v1/m/sensor_monitor", tags=["sensor_monitor"])

@router.post("/reboot")
async def reboot_sensor(
    sensor_id: str,
    user: dict = Depends(CurrentUser),
    _: None = Depends(require_permission("module.sensor_monitor.control"))
):
    return {"status": "rebooting", "by_user": user["username"]}
```
