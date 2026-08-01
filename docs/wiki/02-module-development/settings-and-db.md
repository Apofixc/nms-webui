# Настройки модулей и работа с БД

Руководство по хранению конфигураций, созданию пользовательских таблиц и управлению транзакциями в базе данных NMS WebUI.

---

## ⚙️ Хранение настроек модуля (Module Settings)

Каждый модуль может иметь динамические настройки, изменяемые администратором через веб-интерфейс. Настройки автоматически сохраняются в системную базу данных SQLite `nms.db` в виде JSON-документа.

### 1. Описание схемы настроек в manifest.yaml

Схема описания настроек задаётся в `manifest.yaml` в поле `settings_schema`:

```yaml
settings_schema:
  client_id:
    type: "string"
    default: ""
    label: "Tuya Access ID"
    required: true
  secret_key:
    type: "string"
    default: ""
    label: "Tuya Access Secret"
    secret: true
  poll_interval:
    type: "integer"
    default: 30
    label: "Интервал опроса устройств (сек)"
    min: 5
    max: 300
```

### 2. Чтение и запись настроек из Backend кода

Для работы с настройками модуля используются системные хелперы `backend.core.plugin.registry`:

```python
from backend.core.plugin.registry import get_module_settings, save_module_settings

# Получить текущие настройки модуля "tuya"
settings = get_module_settings("tuya")
client_id = settings.get("client_id", "")
poll_interval = settings.get("poll_interval", 30)

# Сохранить новые настройки
save_module_settings("tuya", {
    "client_id": "new_id_value",
    "secret_key": "new_secret_value",
    "poll_interval": 60
})
```

---

## 🗄️ Создание собственных таблиц в SQLite

Если вашему модулю требуется хранить собственные реляционные данные (историю событий, состояния датчиков, пользовательские привязки), создавайте таблицы при инициализации модуля.

### Пример инициализации таблицы модуля:

```python
# modules/tuya/backend/main.py
from backend.core.database import get_db_connection

def init_tuya_db():
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS module_tuya_devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    online_status INTEGER DEFAULT 0,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tuya_devices_status 
                ON module_tuya_devices(online_status);
            """)
    finally:
        conn.close()

# Функция инициализации модуля, вызываемая движком NMS при старте
def init_module(app):
    init_tuya_db()
```

---

## 🔒 Безопасность и транзакции

1. **Использование сопоставления параметров (Parameterized Queries)**: Никогда не подставляйте переменные в SQL строки напрямую, во избежание SQL-инъекций.
   ```python
   # ПРАВИЛЬНО:
   conn.execute("SELECT * FROM module_tuya_devices WHERE id = ?", (device_id,))
   ```
2. **Контекстный менеджер `with conn`**: Автоматически выполняет `COMMIT` при успешном завершении блока и `ROLLBACK` в случае ошибки.
