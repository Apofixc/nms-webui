# ⚓ 13. Хуки жизненного цикла и фоновые задачи (Lifecycle & Async Services)

---

## ⚓ Хуки жизненного цикла (`hooks`)

В файле манифеста `manifest.yaml` модуль может задавать Python-пути к обработчикам событий жизненного цикла:

```yaml
hooks:
  on_startup: "backend.modules.sensor_monitor.lifecycle:on_startup"
  on_shutdown: "backend.modules.sensor_monitor.lifecycle:on_shutdown"
```

При старте сервера FastAPI Загрузчик опрашивает все включенные модули и в порядке их топологической сортировки исполняет `on_startup`, а при остановке приложения — `on_shutdown`.

---

## 🔄 Фоновые асинхронные задачи (Async Tasks)

Модули могут запускать длительные фоновые процессы (например, регулярный опрос датчиков или очистку устаревшего кэша) в методе `start()` класса модуля:

```python
import asyncio

class SensorMonitorModule(BaseModule):
    def start(self) -> None:
        self.context.logger.info("Launching background polling task...")
        self._task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self):
        while True:
            try:
                await self._poll_all_sensors()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.context.logger.error("Error in poll loop: %s", exc)

    async def stop(self) -> None:
        if hasattr(self, "_task") and self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
```

---

## 🧹 Деструкция ресурсов (`uninstall()`)

Если пользователь полностью удаляет модуль через UI, ядро очищает таблицы БД `mod_<module_id>_*` и директории данных, после чего вызывает деструктор модуля `instance.uninstall()` для доочистки любых внешних ресурсов.
