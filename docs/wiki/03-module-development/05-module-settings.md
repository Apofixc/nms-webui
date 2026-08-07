# ⚙️ 5. Настройки модулей и работа с JSON Schema (Config & Settings API)

---

## 📌 Динамические формы настроек (`config_schema`)

Каждый модуль может объявлять схему пользовательских настроек в манифесте `manifest.yaml` с использованием спецификации **JSON Schema**.

На основе этой схемы интерфейс NMS WebUI (`/settings/modules/<module_id>`) автоматически генерирует графическую форму управления настройками.

### Пример декларации `config_schema`:

```yaml
config_schema:
  type: object
  properties:
    poll_interval:
      type: integer
      title: "Интервал опроса (сек)"
      default: 30
      minimum: 5
      maximum: 3600
    alert_email:
      type: string
      title: "Email для оповещений"
      default: "admin@example.com"
      format: "email"
    enable_debug:
      type: boolean
      title: "Режим отладки"
      default: false
  required:
    - poll_interval
```

---

## 🐍 Динамическое формирование настроек (`entrypoints.settings`)

Если настройки модуля зависят от рантайм-условий (например, списка сетевых интерфейсов сервера), модуль может объявить функцию точки входа `entrypoints.settings`:

```yaml
entrypoints:
  settings: "backend.modules.sensor_monitor.settings:get_dynamic_schema"
```

```python
# backend/modules/sensor_monitor/settings.py
from typing import Any
from backend.core.plugin.context import ModuleContext

def get_dynamic_schema(ctx: ModuleContext) -> dict[str, Any]:
    # Динамически вычисляем опции
    interfaces = ["eth0", "eth1", "wlan0"]
    
    return {
        "type": "object",
        "properties": {
            "interface": {
                "type": "string",
                "title": "Сетевой интерфейс",
                "enum": interfaces,
                "default": interfaces[0]
            }
        }
    }
```

---

## 🔄 Получение и реакция на изменение настроек

Для получения актуальных настроек модуля в коде используется системная функция `get_security_settings(module_id)` из `registry.py`:

```python
from backend.core.plugin.registry import get_security_settings

settings = get_security_settings(self.context.module_id)
poll_interval = settings.get("poll_interval", 30)
```

При сохранении новых настроек через UI ядро высылает событие по WebSockets через `notify_settings_changed(module_id)`.
