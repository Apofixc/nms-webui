# 🪵 6. Использование логгера и провайдеры логов (Logger API)

---

## 📌 Изолированное логирование через `context.logger`

Каждому модулю выделяется собственный изолированный логгер Python `logging.Logger` с пространством имен `nms.plugin.<module_id>`.

```python
# Использование внутри класса модуля
self.context.logger.info("Initializing module components...")
self.context.logger.debug("Polling device IP %s", ip_address)
self.context.logger.warning("Retry attempt %d for sensor", attempt)
self.context.logger.error("Connection failed", exc_info=True)
```

---

## 📜 Провайдеры логов (`get_log_provider()`)

Если модуль ведет свой отдельный логирующий файл или обращается к удаленному веб-серверу логов, он может отдать свой провайдер логов системному интерфейсу NMS (`/system/logs`), переопределив `get_log_provider()`:

```python
from backend.core.log_providers import RemoteHTTPLogProvider

class MyModule(BaseModule):
    def get_log_provider(self):
        log_file = self.context.get_data_dir() / "device_events.log"
        return RemoteHTTPLogProvider(
            provider_id=f"module_{self.context.module_id}",
            name=f"Логи модуля {self.context.module_id}",
            file_path=str(log_file)
        )
```
