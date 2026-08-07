# 🧩 06. Разработка виджетов дашборда, динамические настройки и аудит

---

## 🧩 Разработка виджетов Дашборда

Виджеты регистрируются в манифесте модуля `manifest.yaml`:

```yaml
widgets:
  - id: "sensor-summary"
    title: "sensorWidgetTitle"
    endpoint: "/api/v1/m/sensor_monitor/widgets/summary"
    component: "SensorWidget"
    size: "medium"                        # "small" | "medium" | "large"
    refresh_interval: 5
```

REST-эндпоинт данных виджета отдает актуальный JSON-объект:

```python
@router.get("/widgets/summary")
async def get_widget_summary():
    return {"status": "ok", "data": {"online": 40, "offline": 2}}
```

---

## ⚙️ Динамическая схема настроек (`config_schema`)

Описывает параметры модуля в формате **JSON Schema**:

```yaml
config_schema:
  type: object
  properties:
    poll_interval:
      type: integer
      default: 10
      title: "Интервал опроса (сек)"
```

---

## 🛡 Журнал аудита безопасности (`log_audit_event`)

Критичные действия пользователей фиксируются в аудите:

```python
from backend.core.audit import log_audit_event

log_audit_event(
    user_id=user["username"],
    action="SENSOR_RESET",
    target=f"sensor:{sensor_id}",
    details={"ip": request.client.host}
)
```
