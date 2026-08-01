# Настройки модулей и работа с БД

Руководство по хранению конфигурации и данных модулей в NMS WebUI.

## Хранение настроек модуля

Настройки модуля сохраняются в системной базе данных SQLite (`nms.db`) в таблице `module_settings` в формате JSON.

### Получение и сохранение через REST API

- `GET /api/modules/{module_id}/settings` — Получить текущие настройки модуля.
- `PUT /api/modules/{module_id}/settings` — Обновить настройки модуля.

### Инициализация дефолтных настроек

Дефолтные значение описываются в `manifest.yaml`:

```yaml
settings_schema:
  api_key:
    type: "string"
    default: ""
    label: "API Ключ"
  sync_interval:
    type: "integer"
    default: 60
    label: "Интервал синхронизации (сек)"
```

## Собственные таблицы в БД

Если модулю требуются собственные таблицы для хранения историй или состояний, инициализация таблиц производится при загрузке модуля в метод `init_module(app)`:

```python
from backend.core.database import get_db_connection

def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS module_tuya_devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT
            )
        """)
    conn.close()
```
