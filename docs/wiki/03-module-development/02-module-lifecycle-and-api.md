# 🧩 02. Создание модулей, жизненный цикл и FastAPI роутеры

---

## 📌 Класс `BaseModule` и жизненный цикл

Все модули бэкенда наследуются от абстрактного класса `BaseModule` ([backend/modules/base.py](file:///opt/nms-webui/backend/modules/base.py)).

### Методы жизненного цикла:

```python
from backend.modules.base import BaseModule
from backend.core.plugin.context import ModuleContext

class SensorMonitorModule(BaseModule):
    def __init__(self, context: ModuleContext):
        super().__init__(context)

    def init(self) -> None:
        """Этап 1: Инициализация таблиц и ресурсов."""
        self.context.logger.info("Initializing module...")

    def start(self) -> None:
        """Этап 2: Запуск фоновых сервисов и задач."""
        self.context.logger.info("Starting services...")

    async def stop(self) -> None:
        """Этап 3: Остановка модуля и высвобождение ресурсов."""
        self.context.logger.info("Stopping module...")

    def get_status(self) -> dict:
        """Состояние модуля для системных мониторов."""
        return {"status": "ok", "module_id": self.context.module_id}

def create_module(context: ModuleContext) -> BaseModule:
    """Фабричная функция для NMS Loader."""
    return SensorMonitorModule(context)
```

---

## 🔗 Регистрация FastAPI роутера (`api.py`)

Модуль объявляет свои API эндпоинты через объект `APIRouter`:

```python
from fastapi import APIRouter, Depends
from backend.core.auth import CurrentUser, require_permission

router = APIRouter(prefix="/api/v1/m/sensor_monitor", tags=["sensor_monitor"])

@router.get("/devices")
async def list_devices(
    user: dict = Depends(CurrentUser),
    _: None = Depends(require_permission("module.sensor_monitor.view"))
):
    return {"status": "ok", "devices": []}

def get_router() -> APIRouter:
    return router
```
