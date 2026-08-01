# Разрешения и RBAC в модулях NMS WebUI

Подробное руководство по проектированию, объявлению и проверке прав доступа (Role-Based Access Control) в модулях.

---

## 🔒 Принципы безопасности в NMS WebUI

1. **Принцип наименьших привилегий (Principle of Least Privilege)**: По умолчанию у обычных пользователей нет доступа к потенциально опасным действиям модуля.
2. **Изоляция пространств имен**: Разрешения модуля должны начинаться с идентификатора самого модуля (например, `tuya.read`, `tuya.control`, `tuya.admin`).

---

## 📄 Объявление разрешений в manifest.yaml

Разрешения описываются в манифесте модуля `manifest.yaml` в блоке `permissions`:

```yaml
id: "tuya"
name: "Модуль Tuya IoT"
version: "1.0.0"

permissions:
  - id: "tuya.read"
    name: "Просмотр устройств Tuya"
    description: "Разрешает просмотр списка устройств, их статусов и виджетов"
  - id: "tuya.control"
    name: "Управление устройствами Tuya"
    description: "Разрешает включение, выключение и изменение параметров устройств"
  - id: "tuya.admin"
    name: "Администрирование ключей Tuya"
    description: "Разрешает изменение API ключей и настроек провайдера"
```

---

## 🛡️ Проверка разрешений на Backend (Python / FastAPI)

В эндпоинтах FastAPI используйте зависимость `require_permission`:

```python
from fastapi import APIRouter, Depends, HTTPException
from backend.core.auth import CurrentUser, require_permission

router = APIRouter(prefix="/api/v1/m/tuya", tags=["tuya"])

# Просмотр устройств (требует tuya.read)
@router.get("/devices")
async def list_devices(
    user: CurrentUser = Depends(require_permission("tuya.read"))
):
    return {"devices": [...]}

# Переключение состояния (требует tuya.control)
@router.post("/devices/{device_id}/toggle")
async def toggle_device(
    device_id: str,
    user: CurrentUser = Depends(require_permission("tuya.control"))
):
    # Логика управления устройством
    return {"status": "success", "device_id": device_id}
```

---

## 🖥️ Проверка разрешений на Frontend (Vue 3)

На фронтенде для скрытия или отключения элементов UI используется хранилище авторизации `useAuthStore`:

```vue
<template>
  <div class="device-card">
    <h3>{{ device.name }}</h3>

    <!-- Отображение кнопки только если у пользователя есть право tuya.control -->
    <button 
      v-if="authStore.hasPermission('tuya.control')" 
      @click="toggleDevice(device.id)"
      class="btn-primary"
    >
      Переключить
    </button>

    <span v-else class="text-xs text-neutral-400">
      Нет прав на управление
    </span>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/core/stores/auth'

const authStore = useAuthStore()
</script>
```

---

## 📝 Аудит действий

При выполнении операций, меняющих состояние (POST/PUT/DELETE), рекомендуется записывать событие в журнал аудита:

```python
from backend.core.audit import log_audit_event

log_audit_event(
    user_id=user.id,
    username=user.username,
    action="TUYA_DEVICE_TOGGLE",
    resource=f"device:{device_id}",
    details=f"Пользователь {user.username} переключил статус устройства {device_id}",
    ip_address=request.client.host if request.client else None,
)
```
