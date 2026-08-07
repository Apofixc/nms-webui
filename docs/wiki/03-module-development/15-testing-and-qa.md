# 🧪 15. Тестирование модулей и автотесты (Module QA)

---

## 📌 Подходы к тестированию модулей

Тестирование модулей в NMS WebUI осуществляется с помощью фреймворка `pytest`.

Все модульные автотесты располагаются либо в папке `tests/modules/` корневого проекта, либо в поддиректории `tests/` самого модуля (`backend/modules/<module_id>/tests/`).

---

## 🛠 Пример автотеста для модуля `sensor_monitor`

### 1. Тестирование манифеста и класса модуля (`tests/test_sensor_module.py`)

```python
import pytest
from pathlib import Path
from backend.core.plugin.context import ModuleContext
from backend.modules.sensor_monitor import SensorMonitorModule

@pytest.fixture
def mock_context(tmp_path):
    return ModuleContext(
        module_id="sensor_monitor",
        root=tmp_path,
        manifest={"version": "1.0.0"}
    )

def test_module_lifecycle(mock_context):
    module = SensorMonitorModule(mock_context)
    
    # Тест инициализации
    module.init()
    
    # Тест статуса
    status = module.get_status()
    assert status["module_id"] == "sensor_monitor"
```

---

## 🌐 Тестирование REST API эндпоинтов через FastAPI `TestClient`

```python
from fastapi.testclient import TestClient
from backend.core.app import create_app

def test_sensor_api_endpoints():
    app = create_app()
    client = TestClient(app)
    
    # Запрос к защищенному роуту
    response = client.get("/api/v1/m/sensor_monitor/devices")
    
    # Должен вернуть 401 Unauthorized без JWT токена
    assert response.status_code == 401
```
