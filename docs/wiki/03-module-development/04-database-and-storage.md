# 💾 4. Использование базы данных и хранилища (Database & Storage API)

---

## 📌 Подключение к базе данных SQLite

В платформе используется единая база данных **SQLite 3 (WAL)** `nms.db`. 

Модуль получает доступ к БД через метод `context.get_db()`. Таблицы модуля обязаны иметь префикс **`mod_<module_id>_`** (`context.py`).

### 1. Выполнение запросов

```python
with self.context.get_db() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mod_sensor_monitor_devices WHERE status = ?", ("online",))
    rows = cursor.fetchall()
```

---

## 🛠 Автоматическое создание таблиц (`create_table()`)

В методе `init()` модуля используйте метод `context.create_table()` для генерации схемы:

```python
def init(self) -> None:
    # Автоматически создаст таблицу 'mod_sensor_monitor_sensors'
    self.context.create_table(
        "sensors",
        {
            "id": "TEXT PRIMARY KEY",
            "name": "TEXT NOT NULL",
            "val": "REAL DEFAULT 0.0"
        }
    )
```

---

## 📁 Файловая песочница (`ensure_safe_path()`)

Для хранения файлов используются изолированные директории:
- `self.context.get_data_dir()` (`backend/data/modules/<module_id>/`).
- `self.context.get_cache_dir()` (`backend/cache/modules/<module_id>/`).

Для защиты от уязвимостей типа Path Traversal вызывайте `self.context.ensure_safe_path(target_path)`.
