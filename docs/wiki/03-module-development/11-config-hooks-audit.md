# ⚙️ 11. Динамические настройки, хуки и аудит (Config, Hooks & Audit)

---

## ⚙️ Динамическая схема настроек (`config_schema`)

Модуль декларирует параметры конфигурации по спецификации **JSON Schema**:

```yaml
config_schema:
  type: object
  properties:
    poll_interval:
      type: integer
      default: 10
      title: "Интервал опроса (сек)"
    sensor_ip:
      type: string
      default: "192.168.1.1"
      title: "IP адрес"
```

В интерфейсе настроек система автоматически отрендерит графическую форму для изменения этих полей.

---

## ⚓ Хуки жизненного цикла (`hooks`)

Секция `hooks` позволяет выполнять пользовательские скрипты или функции:

```yaml
hooks:
  install: "scripts/install.sh"
  on_enable: "backend.modules.sensor_monitor:on_enable_hook"
```

---

## 🛡 Журналирование безопасности (`log_audit_event`)

Критичные операции обязаны регистрироваться в журнале аудита ([audit.py](file:///opt/nms-webui/backend/core/audit.py)):

```python
from backend.core.audit import log_audit_event

log_audit_event(
    user_id=user["username"],
    action="DEVICE_RESET",
    target=f"device:{dev_id}",
    details={"ip": request.client.host}
)
```
