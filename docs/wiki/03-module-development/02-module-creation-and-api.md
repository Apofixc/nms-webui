# 🛠 2. Создание модулей и базовое API (`BaseModule` & `ModuleContext`)

---

## 📌 Класс `BaseModule` и жизненный цикл

Все модули бэкенда наследуются от абстрактного класса `BaseModule` (`backend/modules/base.py`).

Каждому модулю при инициализации передается зафиксированный объект `ModuleContext` (`backend/core/plugin/context.py`).

### Полный пример класса модуля:

```python
from typing import Any
from backend.modules.base import BaseModule
from backend.core.plugin.context import ModuleContext

class SensorMonitorModule(BaseModule):
    def __init__(self, context: ModuleContext):
        super().__init__(context)
        self._running = False

    def init(self) -> None:
        """Этап 1: Подготовка модуля (DDL таблиц, валидация конфигурации)."""
        self.context.logger.info("Initializing SensorMonitor module...")
        self.context.create_table(
            "devices",
            {
                "id": "TEXT PRIMARY KEY",
                "name": "TEXT NOT NULL",
                "ip": "TEXT NOT NULL"
            }
        )

    def start(self) -> None:
        """Этап 2: Запуск сервисов и фоновых задач."""
        self.context.logger.info("Starting background services...")
        self._running = True

    async def stop(self) -> None:
        """Этап 3: Остановка модуля и высвобождение ресурсов."""
        self.context.logger.info("Stopping module...")
        self._running = False

    def get_status(self) -> dict[str, Any]:
        """Возврат текущего состояния здоровья модуля."""
        return {"status": "running" if self._running else "stopped"}

def create_module(context: ModuleContext) -> BaseModule:
    """Фабричная функция модуля."""
    return SensorMonitorModule(context)
```

---

## 🔗 Регистрация FastAPI роутера (`api.py`)

Модуль объявляет свой REST API через файл `api.py`:

```python
from fastapi import APIRouter, Depends
from backend.core.auth import CurrentUser, require_permission

router = APIRouter(prefix="/api/v1/m/sensor_monitor", tags=["sensor_monitor"])

@router.get("/devices")
async def get_devices(
    user: dict = Depends(CurrentUser),
    _: None = Depends(require_permission("module.sensor_monitor.view"))
):
    return {"status": "ok", "devices": []}

def get_router() -> APIRouter:
    return router
```
