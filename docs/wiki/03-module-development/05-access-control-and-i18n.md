# 🧩 05. Разграничение доступа RBAC и локализация i18n

---

## 🔐 Разграничение прав доступа (RBAC)

Права декларируются в манифесте модуля и проверяются на бэкенде через `require_permission`:

```yaml
permissions:
  - id: "module.sensor_monitor.view"
    name: "Просмотр датчиков"
  - id: "module.sensor_monitor.control"
    name: "Управление датчиками"
```

```python
from fastapi import Depends
from backend.core.auth import CurrentUser, require_permission

@router.post("/reboot")
async def reboot_device(
    user: dict = Depends(CurrentUser),
    _: None = Depends(require_permission("module.sensor_monitor.control"))
):
    return {"status": "rebooting"}
```

---

## 🌐 Мультиязычность (i18n)

Словари переводов задаются в `manifest.yaml`:

```yaml
i18n:
  ru:
    sensorTitle: "Мониторинг Датчиков"
  en:
    sensorTitle: "Sensor Monitoring"
```

- На бэкенде: `from backend.core.i18n import tr`; `title = tr("ru", "sensorTitle")`.
- Во Vue-компонентах: `{{ $t('sensorTitle') }}`.
