# 🧩 03. База данных SQLite и файловое хранилище

---

## 💾 Подключение к SQLite (`context.get_db()`)

Все модули платформы работают с единой базой данных **SQLite (WAL)** `nms.db`.

Изоляция таблиц достигается обязательным префиксом **`mod_<module_id>_`**.

### 1. Получение подключения и создание таблиц

```python
def init(self) -> None:
    # Безопасное создание таблицы mod_sensor_monitor_devices
    self.context.create_table(
        "devices",
        {
            "id": "TEXT PRIMARY KEY",
            "name": "TEXT NOT NULL",
            "ip": "TEXT NOT NULL",
            "status": "TEXT DEFAULT 'offline'"
        }
    )

def fetch_data(self):
    with self.context.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mod_sensor_monitor_devices")
        return cursor.fetchall()
```

---

## 📁 Файловая песочница (`ensure_safe_path()`)

Модули сохраняют локальные файлы только в отведенных директориях:
- **Данные**: `self.context.get_data_dir()` (`backend/data/modules/<module_id>/`).
- **Кэш**: `self.context.get_cache_dir()` (`backend/cache/modules/<module_id>/`).

Для защиты от Path Traversal используется проверка `self.context.ensure_safe_path(target_path)`.
