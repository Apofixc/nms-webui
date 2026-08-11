# 🪵 8. Использование логгера и провайдеры логов (Logger API)

---

Система логирования NMS WebUI обеспечивает единый стандарт ведения логов, изоляцию вывода отдельных модулей, а также гибкий механизм провайдеров логов (`Log Providers`) для централизованного просмотра, фильтрации, скачивания и WebSocket-стриминга логов как локального сервера, так и распределенных узлов network management system.

---

## 🏗️ 1. Архитектура системы логирования NMS

Система логирования бэкенда построена поверх стандартного модуля Python `logging` и разделена на несколько уровней:

```mermaid
graph TD
    SubModule["Код модуля (BaseModule)"] -->|self.context.logger| LoggerInstance["logging.Logger ('nms.plugin.<module_id>')"]
    LoggerInstance -->|Вывод в консоль/файл| BackendLog["backend.log"]
    
    SubModule -->|get_log_provider()| CustomProvider["LocalFileLogProvider / RemoteHTTPLogProvider / Custom"]
    CustomProvider -->|register()| Registry["log_provider_registry"]
    
    SystemLogsAPI["System API (/api/system/logs)"] -->|get / stream / download| Registry
    FrontendUI["SystemAdmin.vue (Логи системы)"] -->|REST / WebSocket| SystemLogsAPI
```

### Ключевые компоненты архитектуры:
1. **Иерархия логгеров Python**: Все модули используют дочерние логгеры с пространством имен `nms.plugin.<module_id>`. Это позволяет настраивать уровни детализации (DEBUG/INFO/ERROR) индивидуально для каждого модуля.
2. **Формат записей по умолчанию**: Форматтер системных логов бэкенда использует стандартный паттерн вида `YYYY-MM-DD HH:MM:SS | LEVEL | logger_name | message`.
3. **Чистка ANSI-кодов и нормализация**: Функция `clean_ansi()` очищает терминальные escape-последовательности (цветовые коды), а `matches_log_level()` распознает как стандартные, так и альтернативные метки уровней (`DEBUG`, `INFO`, `WARN`/`WARNING`, `ERROR`, `CRITICAL`/`FATAL`).
4. **Провайдеры логов (`BaseLogProvider`)**: Абстракция источника логов, позволяющая модулям транслировать данные из собственного файла логов, БД или удаленных сервисов напрямую в веб-интерфейс NMS.
5. **Центральный реестр (`log_provider_registry`)**: Синглтон-менеджер (`LogProviderRegistry`), агрегирующий все активные источники логов системы.

---

## 📌 2. Изолированное логирование через `context.logger`

Каждому модулю при инициализации передается экземпляр `ModuleContext`, предоставляющий свойство `context.logger`.

### Базовое использование логгера

```python
from backend.modules.base import BaseModule

class DeviceMonitorModule(BaseModule):
    def init(self) -> None:
        # Логирование на этапе инициализации
        self.context.logger.info("Инициализация модуля мониторинга устройств %s...", self.context.module_id)

    def start(self) -> None:
        self.context.logger.info("Запуск процессов опроса оборудования")

    def poll_device(self, ip_address: str) -> None:
        self.context.logger.debug("Начало опроса устройства по IP: %s", ip_address)
        try:
            # Логика опроса...
            self.context.logger.info("Устройство %s успешно опрошено", ip_address)
        except TimeoutError:
            self.context.logger.warning("Таймаут соединения с устройством %s", ip_address)
        except Exception as exc:
            # exc_info=True автоматически прикрепляет стек-трейс ошибки к логу
            self.context.logger.error("Критическая ошибка при опросе устройства %s: %s", ip_address, exc, exc_info=True)
```

### Доступные уровни логирования

| Метод логгера | Уровень | Назначение |
| :--- | :--- | :--- |
| `self.context.logger.debug(msg, *args)` | `DEBUG` (10) | Детальная отладочная информация (дампы пакетов, промежуточные состояния). |
| `self.context.logger.info(msg, *args)` | `INFO` (20) | Информационные сообщения о нормальной работе модуля (запуск, остановка, создание сущностей). |
| `self.context.logger.warning(msg, *args)` | `WARNING` (30) | Предупреждения о потенциальных проблемах (таймауты, повторные попытки, некритичные сбои). |
| `self.context.logger.error(msg, *args)` | `ERROR` (40) | Ошибки выполнения операций, требующие внимания администратора. |
| `self.context.logger.critical(msg, *args)` | `CRITICAL` (50) | Фатальные сбои, приводящие к остановке модуля или повреждению данных. |

> [!TIP]
> **Рекомендация по производительности**: Исполняйте форматирование строк через аргументы `%s` (например, `logger.debug("IP: %s", ip)`), а не через f-строки (`f"IP: {ip}"`). В этом случае интерполяция строки происходит **только** если текущий уровень логгера включен, предотвращая лишние накладные расходы при выключенном `DEBUG`.

---

## 🔍 3. Алгоритмы очистки и фильтрации логов

Для обеспечения корректной работы веб-интерфейса просмотрщика логов платформой используются две служебные функции из `backend/core/log_providers.py`:

### 1. Очистка ANSI Escape-кодов (`clean_ansi`)

Многие консольные утилиты выгружают логи с терминальным форматированием (цветовые коды ANSI). Функция `clean_ansi()` подготавливает текст к безопасному выводу в UI:

```python
def clean_ansi(text: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
```

*Пример:* Строка `"\x1b[38;5;40;1m[INFO]\x1b[0m Server running"` преобразуется в `"[INFO] Server running"`.

### 2. Фильтрация по уровням (`matches_log_level`)

Функция `matches_log_level()` реализует умное сопоставление выбранного пользователем уровня логов с каждой строкой:

1. **Структурированный поиск**: Анализирует наличие меток в форматах `|INFO|`, `[ERROR]`, `WARN:`, `CRITICAL` с помощью регулярного выражения `r'(?:\||\[|\b)(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)(?:\s*\||\]|:|\b)'`.
2. **Нормализация алиасов**:
   - `WARN` и `WARNING` признаются эквивалентными.
   - `CRITICAL` и `FATAL` нормализуются к одному уровню.
3. **Резервный подстроковый поиск**: Если строка не имеет четких разделителей, проверяется вхождение слова уровня на границах слов (`\bINFO\b`).

---

## 📜 4. Система Провайдеров Логов (Log Provider System)

Если ваш модуль генерирует собственный лог-файл (например, в своей изолированной директории данных `self.context.get_data_dir()`), обращается к сторонней БД или удаленному узлу, его можно зарегистрировать в системном веб-интерфейсе логов NMS WebUI.

### Базовый абстрактный класс `BaseLogProvider`

Все провайдеры логов наследуют класс `BaseLogProvider` и реализуют 3 обязательных асинхронных метода:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

class BaseLogProvider(ABC):
    def __init__(self, provider_id: str, name: str, category: str = "system"):
        self.id = provider_id          # Уникальный ID (например, "module_topology_events")
        self.name = name              # Человекочитаемое имя для UI ("Логи событий топологии")
        self.category = category      # Категория: "system", "module", "remote"

    @abstractmethod
    async def get_logs(self, lines: int = 200, level: str = "ALL", search: str = "") -> Dict[str, Any]:
        """Возвращает словарь с массивом строк лога, с учетом параметров фильтрации."""
        pass

    @abstractmethod
    async def download_log(self) -> Tuple[bytes, str, str]:
        """Возвращает (content_bytes, filename, media_type) для скачивания файла лога."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Проверяет доступность источника логов (существование файла / доступность узла)."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация базовых метаданных провайдера для REST API."""
        return {"id": self.id, "name": self.name, "category": self.category}
```

### Встроенные классы провайдеров

Платформа NMS предоставляет готовые реализации провайдеров:

#### 1. `LocalFileLogProvider`
Предназначен для чтения локальных лог-файлов с диска сервера. 

* **Ограничение объема (Safety Limit)**: Метод `get_logs()` автоматически ограничивает количество возвращаемых за раз строк в пределах `max(1, min(lines, 2000))`, защищая сервер и клиент от OOM при чтении гигабайтных логов.
* **Безопасная кодировка**: Чтение происходит с флагом `errors="replace"`, что предотвращает сбои при декодировании поврежденных байтов или бинарных символов.

```python
from pathlib import Path
from backend.core.log_providers import LocalFileLogProvider

log_file_path = Path("/var/log/nms/my_custom.log")
provider = LocalFileLogProvider(
    provider_id="my_custom_log",
    name="Лог пользовательского процесса",
    file_path=log_file_path,
    category="module"
)
```

#### 2. `RemoteHTTPLogProvider`
Предназначен для проксирования логов с удаленного NMS-сервера или агента по HTTP API.

* **Политика таймаутов**:
  - `is_available()`: 3.0 секунды.
  - `get_logs()`: 5.0 секунд.
  - `download_log()`: 10.0 секунд.
* **Graceful Degradation (Безопасность сетевых вызовов)**: В случае нехватки связи или сетевой ошибки `RemoteHTTPLogProvider` не вызывает ошибку 500 сервера, а возвращает в поле `content` элемент `[ERROR] Failed to load remote log / Не удалось загрузить удаленный лог: <exc>`.
* **Авторизация**: Автоматически передает токен доступа в заголовке `Authorization: Bearer <api_token>`.

```python
from backend.core.log_providers import RemoteHTTPLogProvider

remote_provider = RemoteHTTPLogProvider(
    provider_id="remote_node_01",
    name="Лог узла Москва-1",
    url="http://192.168.10.50:9000/api/system/logs/backend.log",
    headers={"Authorization": "Bearer SECRET_API_TOKEN"},
    category="remote"
)
```

### Регистрация через SDK ModuleContext (`ctx.register_log_provider`)

Вместо прямого импорта `log_provider_registry` из ядра, модули могут динамически регистрировать свои провайдеры логов через SDK:

```python
# Регистрация провайдера через контекст модуля
self.context.register_log_provider(my_provider)
```

Также все провайдеры агрегируются в едином ядре `log_provider_registry`:

```python
from backend.core.log_providers import log_provider_registry

# Регистрация провайдера
log_provider_registry.register(my_provider)

# Удаление из реестра
log_provider_registry.unregister("my_custom_log")

# Получение провайдера по ID или имени
provider = log_provider_registry.get("my_custom_log")
```

При старте бэкенда NMS автоматически регистрирует системный провайдер `backend.log` для главного лог-файла приложения (`NMS_ROOT/backend.log`).

---

## 🛠️ 5. Интеграция провайдера логов в свой модуль

Каждый модуль верхнего уровня (унаследованный от `BaseModule`) может объявить собственный провайдер логов, переопределив метод `get_log_provider()`.

При загрузке модуля платформа (`loader.py`) автоматически вызывает данный метод и регистрирует возвращенный провайдер в реестре `log_provider_registry`.

### Пример 1: Отдача локального файла логов модуля

```python
from pathlib import Path
from typing import Any
from backend.modules.base import BaseModule
from backend.core.log_providers import LocalFileLogProvider

class AuditLoggerModule(BaseModule):
    def init(self) -> None:
        self.log_file = self.context.get_data_dir() / "audit_events.log"
        self._ensure_log_file()

    def _ensure_log_file(self) -> None:
        if not self.log_file.exists():
            self.log_file.write_text("2026-08-07 12:00:00 | INFO | Audit Log Created\n", encoding="utf-8")

    def get_log_provider(self) -> Any | None:
        """Определяем провайдер логов для отображения в /system/logs"""
        return LocalFileLogProvider(
            provider_id=f"module_{self.context.module_id}",
            name=f"Аудит модуля {self.context.manifest.get('name', self.context.module_id)}",
            file_path=self.log_file,
            category="module"
        )
```

### Пример 2: Создание кастомного провайдера логов (на базе БД SQLite)

Если модуль хранит логи в своей таблице базы данных (например, `mod_my_module_logs`), можно создать кастомный класс провайдера:

```python
import sqlite3
from typing import Any, Dict, Tuple
from backend.core.log_providers import BaseLogProvider

class DBTableLogProvider(BaseLogProvider):
    def __init__(self, provider_id: str, name: str, db_path: str, table_name: str):
        super().__init__(provider_id, name, category="module")
        self.db_path = db_path
        self.table_name = table_name

    async def is_available(self) -> bool:
        return True

    async def get_logs(self, lines: int = 200, level: str = "ALL", search: str = "") -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = f"SELECT created_at, level, message FROM {self.table_name} WHERE 1=1"
        params = []

        if level and level != "ALL":
            query += " AND level = ?"
            params.append(level)

        if search:
            query += " AND message LIKE ?"
            params.append(f"%{search}%")

        query += " ORDER BY id DESC LIMIT ?"
        params.append(lines)

        rows = cursor.fetchall()
        conn.close()

        formatted_lines = [f"{r[0]} | {r[1]} | {r[2]}" for r in reversed(rows)]
        return {
            "id": self.id,
            "name": self.name,
            "content": formatted_lines,
            "total_lines": len(formatted_lines),
            "matched_lines": len(formatted_lines),
        }

    async def download_log(self) -> Tuple[bytes, str, str]:
        res = await self.get_logs(lines=5000)
        content_text = "\n".join(res["content"])
        return content_text.encode("utf-8"), f"{self.id}.log", "text/plain; charset=utf-8"
```

---

## 🌐 6. REST API & WebSocket эндпоинты

Системный API логирования реализован в `backend/core/system_api.py` под префиксом `/api/system`. Все HTTP-методы требуют права администратора `system.admin`.

### Таблица эндпоинтов REST API

| Метод | URL | Описание |
| :--- | :--- | :--- |
| `GET` | `/api/system/logs` | Возвращает массив метаданных всех зарегистрированных провайдеров логов. |
| `GET` | `/api/system/logs/{log_name}` | Чтение содержимого лога. Query-параметры: `lines` (default: 200), `level` (`ALL`, `DEBUG`, `INFO`, `WARN`, `ERROR`), `search` (строка поиска). |
| `GET` | `/api/system/logs/{log_name}/download` | Скачивание файла лога целиком (возвращает `Content-Disposition: attachment`). |
| `GET` | `/api/system/logs/remote-sources/list` | Возвращает список сохраненных в БД удаленных серверов логов. |
| `POST` | `/api/system/logs/remote-sources` | Добавление нового удаленного сервера логов. Pydantic-схема `RemoteLogSourceCreate`: `{ "name": "...", "url": "...", "api_token": "..." }`. |
| `DELETE` | `/api/system/logs/remote-sources/{source_id}` | Удаление удаленного источника логов. |

### WebSocket стриминг логов в реальном времени

```http
WS /api/system/logs/{log_name}/stream?level=ALL&search=keyword
```

При подключении по WebSocket бэкенд каждые **1.0 секунду** проверяет обновленный срез лога через выбранный провайдер. 

* **Оптимизация трафика**: Сервер отправляет кадр пользователю **только** если количество или состав фильтрованных строк изменился (`len(content) != last_lines_count`).
* **Обработка несуществующих провайдеров**: Если запрошен неизвестный `log_name`, WebSocket сразу закрывается со спец-кодом `1008` (Reason: `Log provider not found`).

```json
{
  "id": "backend.log",
  "name": "backend.log",
  "content": [
    "2026-08-07 21:55:00 | INFO | System started successfully",
    "2026-08-07 21:55:05 | DEBUG | Polling background jobs..."
  ],
  "matched_lines": 2,
  "total_lines": 1500
}
```

---

## 🗄️ 7. Хранение удаленных источников логов в БД

Для сохранения настроек подключений к удаленным NMS-узлам между перезапусками сервера используется таблица `remote_log_sources` в SQLite (`nms.db`).

### DDL Таблицы `remote_log_sources`

```sql
CREATE TABLE IF NOT EXISTS remote_log_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    api_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

При старте бэкенда вызывается функция `load_remote_sources_from_db()`, которая зачитывает записи из БД и автоматически инициализирует объекты `RemoteHTTPLogProvider` в глобальном реестре `log_provider_registry`.

---

## 💻 8. Фронтенд-интеграция (Vue 3, TypeScript & UI)

### API Клиент `frontend/src/core/api.ts`

Для работы с логами во фронтенд-коде вызовите стандартизированные асинхронные методы:

```typescript
import {
  apiFetchLogList,
  apiFetchLogContent,
  apiAddRemoteLogSource,
  apiDeleteRemoteLogSource
} from '@/core/api'

// 1. Получить список доступных источников логов
const providers = await apiFetchLogList()

// 2. Загрузить содержимое выбранного лога
const logData = await apiFetchLogContent('backend.log', {
  lines: 500,
  level: 'ERROR',
  search: 'connection'
})

// 3. Добавить новый удаленный узел
await apiAddRemoteLogSource({
  name: 'Узел СПб-North',
  url: 'http://10.0.1.10:9000/api/system/logs/backend.log',
  api_token: 'my-secret-bearer-token'
})
```

### Интерфейс просмотра в `SystemAdmin.vue`

Вкладка **"Логи системы"** административной панели предоставляет:
- Выпадающий список всех зарегистрированных локальных, модульных и удаленных провайдеров логов.
- Селектор фильтрации по уровням (`ALL`, `DEBUG`, `INFO`, `WARN`, `ERROR`).
- Живое поле текстового поиска.
- Кнопку скачивания файла лога целиком.
- Автоматический WebSocket стриминг в режиме реального времени.
- Модальное окно управления удаленными серверами логов (добавление узла с URL и Bearer-токеном).

---

## 🧪 9. Автоматическое тестирование лог-провайдеров

Для проверки работы собственных провайдеров логов используйте `pytest` и асинхронные фикстуры `pytest-asyncio`.

Пример теста для `LocalFileLogProvider` и реестра `LogProviderRegistry` (на базе `tests/test_log_providers.py`):

```python
import pytest
from pathlib import Path
from backend.core.log_providers import LocalFileLogProvider, LogProviderRegistry

@pytest.mark.asyncio
async def test_custom_file_log_provider(tmp_path: Path):
    log_file = tmp_path / "module_test.log"
    log_file.write_text(
        "2026-08-07 10:00:00 | INFO | Task started\n"
        "2026-08-07 10:01:00 | ERROR | Connection failed\n",
        encoding="utf-8"
    )

    provider = LocalFileLogProvider("test_mod", "Test Log", log_file, category="module")
    assert await provider.is_available() is True

    # Фильтрация по ERROR
    res_err = await provider.get_logs(lines=10, level="ERROR")
    assert len(res_err["content"]) == 1
    assert "Connection failed" in res_err["content"][0]

    # Скачивание лог-файла
    content, filename, media_type = await provider.download_log()
    assert b"Task started" in content
    assert filename == "module_test.log"
```

Запуск юнит-тестов логирования из корня проекта:
```bash
.venv/bin/pytest tests/test_log_providers.py tests/test_remote_log_manager.py
```

---

## 💡 10. Лучшие практики (Best Practices) & Безопасность

1. **Ротация файлов логов**:
   Если ваш модуль пишет собственный лог-файл, всегда используйте `logging.handlers.RotatingFileHandler` или `TimedRotatingFileHandler`. Это предотвратит непрерывный рост файла на диске:
   ```python
   from logging.handlers import RotatingFileHandler

   handler = RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
   ```
2. **Конфиденциальность данных**:
   Никогда не выводите в лог пароли, токены авторизации (`api_token`), приватные SSH-ключи или персональные данные пользователей.
3. **Обработка ошибок сетевых провайдеров**:
   При разработке кастомных сетевых лог-провайдеров на базе `RemoteHTTPLogProvider` устанавливайте разумные таймауты HTTP-запросов (от 3.0 до 5.0 секунд), чтобы сбой удаленного узла не блокировал интерфейс администрирования.
4. **Регулярная очистка удаленных источников**:
   При удалении модуля или отключении узла всегда отзывайте его провайдер с помощью `log_provider_registry.unregister(provider_id)`.
