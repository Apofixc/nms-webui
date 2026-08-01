# Разрешения и RBAC в модулях

Система управления доступом на основе ролей и разрешений (Role-Based Access Control) в NMS WebUI.

## Обзор

Каждый модуль может объявлять собственную сетку разрешений в файле `manifest.yaml` модуля. Разрешения используются для защиты эндпоинтов REST API и элементов интерфейса.

## Объявление разрешений в manifest.yaml

```yaml
permissions:
  - id: "tuya.read"
    name: "Просмотр устройств Tuya"
    description: "Позволяет просматривать список устройств и статус"
  - id: "tuya.control"
    name: "Управление устройствами Tuya"
    description: "Позволяет включать/выключать устройства"
```

## Проверка разрешений в Backend (FastAPI)

Используйте декоратор `Depends(require_permission(...))`:

```python
from fastapi import APIRouter, Depends
from backend.core.auth import CurrentUser, require_permission

router = APIRouter()

@router.get("/devices")
async def get_devices(user: CurrentUser = Depends(require_permission("tuya.read"))):
    return {"status": "ok"}
```

## Проверка разрешений в Frontend (Vue 3)

Используйте глобальное хранилище авторизации или директивы проверки прав:
```html
<button v-if="hasPermission('tuya.control')" @click="toggleDevice">
  Переключить
</button>
```
