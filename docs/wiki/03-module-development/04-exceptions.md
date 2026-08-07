# 🚨 4. Использование исключений (Exceptions API)

---

## 📌 Базовое исключение `NMSError`

Система исключений ([backend/core/exceptions.py](file:///opt/nms-webui/backend/core/exceptions.py)) обеспечивает единый стандартизированный формат JSON-ответов для всех ошибок в системе.

Все исключения должны наследоваться от `NMSError`:

```python
class NMSError(Exception):
    def __init__(
        self,
        message: str = "Internal error",
        status_code: int = 400,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ): ...
```

---

## 📦 Встроенные типы исключений

| Исключение | HTTP Статус | Описание |
| :--- | :--- | :--- |
| `ValidationError` | `400 Bad Request` | Ошибка валидации входящих параметров |
| `AuthenticationError` | `401 Unauthorized` | Ошибка авторизации или истёк токен |
| `PermissionDeniedError` | `403 Forbidden` | Недостаточно прав для действия |
| `NotFoundError` | `404 Not Found` | Запрошенный ресурс не найден |
| `ModuleDisabledError` | `403 Forbidden` | Модуль отключен в системе |

### Пример в роуте API:

```python
from backend.core.exceptions import NotFoundError, ValidationError

@router.get("/sensors/{sensor_id}")
async def get_sensor(sensor_id: str):
    if not sensor_id.startswith("sns_"):
        raise ValidationError("Invalid ID format", code="INVALID_ID")
        
    sensor = db_find(sensor_id)
    if not sensor:
        raise NotFoundError(f"Sensor '{sensor_id}' not found", code="SENSOR_NOT_FOUND")
    return sensor
```
