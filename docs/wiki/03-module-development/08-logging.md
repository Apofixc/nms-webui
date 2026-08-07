# 🪵 8. Использование логгера и провайдеры логов (Logger API)

---

Система логирования NMS WebUI обеспечивает единый стандарт ведения логов, изоляцию вывода отдельных модулей, а также гибкий механизм провайдеров логов (`Log Providers`) для централизованного просмотра, фильтрации, скачивания и WebSocket-стриминга логов как локального сервера, так и распределенных узлов network management system.

---

## 🏗️ 1. Архитектура системы логирования NMS

Система логирования бэкенда построена поверх стандартного модуля Python [`logging`](https://docs.python.org/3/library/logging.html) и разделена на несколько уровней:

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
2. **Чистка ANSI-кодов и нормализация**: Функция [`clean_ansi()`](file:///opt/nms-webui/backend/core/log_providers.py#L36-L39) очищает терминальные escape-последовательности (цветовые коды), а [`matches_log_level()`](file:///opt/nms-webui/backend/core/log_providers.py#L14-L34) распознает стандартные метки уровней (`DEBUG`, `INFO`, `WARN`/`WARNING`, `ERROR`, `CRITICAL`/`FATAL`).
3. **Провайдеры логов (`BaseLogProvider`)**: Абстракция источника логов, позволяющая модулям транслировать свои собственного файла логов или удаленных сервисов напрямую в веб-интерфейс NMS.
4. **Центральный реестр (`log_provider_registry`)**: Синглтон-менеджер, агрегирующий все активные источники логов системы.

---

## 📌 2. Изолированное логирование через `context.logger`

Каждому модулю при инициализации передается экземпляр [`ModuleContext`](file:///opt/nms-webui/backend/core/plugin/context.py#L12), предоставляющий свойство [`context.logger`](file:///opt/nms-webui/backend/core/plugin/context.py#L25-L27).

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

## 📜 3. Система Провайдеров Логов (Log Provider System)

Если ваш модуль генерирует собственный лог-файл (например, в своей изолированной директории данных `self.context.get_data_dir()`) или обращается к внешнему сервису/оборудованию, его можно зарегистрировать в системном веб-интерфейсе логов NMS WebUI.

### Базовый абстрактный класс [`BaseLogProvider`](file:///opt/nms-webui/backend/core/log_providers.py#L41)

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

#### 1. [`LocalFileLogProvider`](file:///opt/nms-webui/backend/core/log_providers.py#L73)
Предназначен для чтения локальных лог-файлов с диска сервера. Поддерживает безопасное чтение последних $N$ строк (до 2000), очистку ANSI-кодов, текстовый поиск и фильтрацию по уровню логов.

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

#### 2. [`RemoteHTTPLogProvider`](file:///opt/nms-webui/backend/core/log_providers.py#L129)
Предназначен для проксирования логов с удаленного NMS-сервера или агента по HTTP API.

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

### Глобальный реестр [`LogProviderRegistry`](file:///opt/nms-webui/backend/core/log_providers.py#L190)

Все провайдеры регистрируются в синглтоне `log_provider_registry`:

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

## 🛠️ 4. Интеграция провайдера логов в свой модуль

Каждый модуль верхнего уровня (унаследованный от [`BaseModule`](file:///opt/nms-webui/backend/modules/base.py#L10)) может объявить собственный провайдер логов, переопределив метод [`get_log_provider()`](file:///opt/nms-webui/backend/modules/base.py#L32).

При загрузке модуля платформа ([`loader.py`](file:///opt/nms-webui/backend/core/plugin/loader.py#L295-L303)) автоматически вызывает данный метод и регистрирует возвращенный провайдер в реестре `log_provider_registry`.

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

## 🌐 5. REST API & WebSocket эндпоинты

Системный API логирования реализован в [`backend/core/system_api.py`](file:///opt/nms-webui/backend/core/system_api.py#L174) под префиксом `/api/system`. Все HTTP-методы требуют права администратора `system.admin`.

### Таблица эндпоинтов REST API

| Метод | URL | Описание |
| :--- | :--- | :--- |
| `GET` | `/api/system/logs` | Возвращает массив метаданных всех зарегистрированных провайдеров логов. |
| `GET` | `/api/system/logs/{log_name}` | Чтение содержимого лога. Query-параметры: `lines` (default: 200), `level` (`ALL`, `DEBUG`, `INFO`, `WARN`, `ERROR`), `search` (строка поиска). |
| `GET` | `/api/system/logs/{log_name}/download` | Скачивание файла лога целиком (возвращает `Content-Disposition: attachment`). |
| `GET` | `/api/system/logs/remote-sources/list` | Возвращает список сохраненных в БД удаленных серверов логов. |
| `POST` | `/api/system/logs/remote-sources` | Добавление нового удаленного сервера логов. Тело запроса: `{ "name": "...", "url": "...", "api_token": "..." }`. |
| `DELETE` | `/api/system/logs/remote-sources/{source_id}` | Удаление удаленного источника логов. |

### WebSocket стриминг логов в реальном времени

```http
WS /api/system/logs/{log_name}/stream?level=ALL&search=keyword
```

При подключении по WebSocket бэкенд каждые **1.0 секунду** проверяет обновленный срез лога через выбранный провайдер. Если количество или состав строк изменились, клиент получает обновленный JSON-пакет:

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

## 🗄️ 6. Хранение удаленных источников логов в БД

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

При старте бэкенда вызывается функция [`load_remote_sources_from_db()`](file:///opt/nms-webui/backend/core/log_providers.py#L231), которая зачитывает записи из БД и автоматически инициализирует объекты `RemoteHTTPLogProvider` в глобальном реестре `log_provider_registry`.

---

## 💻 7. Фронтенд-интеграция (Vue 3, TypeScript & UI)

### API Клиент [`frontend/src/core/api.ts`](file:///opt/nms-webui/frontend/src/core/api.ts#L376)

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

### Интерфейс просмотра в [`SystemAdmin.vue`](file:///opt/nms-webui/frontend/src/views/SystemAdmin.vue)

Вкладка **"Логи системы"** административной панели предоставляет:
- Выпадающий список всех зарегистрированных локальных, модульных и удаленных провайдеров логов.
- Селектор фильтрации по уровням (`ALL`, `DEBUG`, `INFO`, `WARN`, `ERROR`).
- Живое поле текстового поиска.
- Кнопку скачивания файла лога.
- Автоматический WebSocket стриминг в режиме реального времени.

---

## 💡 8. Лучшие практики (Best Practices) & Безопасность

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
