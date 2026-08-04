# 🏗 Руководство по созданию модулей (Backend + Frontend)

---

## 📦 Пошаговое руководство по созданию модуля

Динамический модуль NMS WebUI состоит из backend-части (API, бизнес-логика, модели БД) и frontend-части (UI-компоненты, виджеты, локализация).

---

### Шаг 1: Создание структуры каталогов

Для нового модуля `example_module` создайте директории:

```bash
mkdir -p backend/modules/example_module
mkdir -p frontend/src/modules/example_module
```

---

### Шаг 2: Создание Манифеста Backend (`manifest.py`)

В директории `backend/modules/example_module/` создайте файл `manifest.py`:

```python
from backend.core.plugin.manifest import PluginManifest

class Manifest(PluginManifest):
    name = "example_module"
    version = "1.0.0"
    description = "Пример пользовательского модуля NMS"
    enabled = True
```

---

### Шаг 3: Добавление API Роутов

Создайте файл `router.py` в бэкенд-части модуля:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/example", tags=["Example Module"])

@router.get("/status")
async def get_example_status():
    return {"status": "ok", "message": "Модуль example_module успешно работает!"}
```

Подключите роутер в `manifest.py`:
```python
from .router import router

class Manifest(PluginManifest):
    routes = [router]
```

---

### Шаг 4: Создание Frontend-компонента

В каталоге `frontend/src/modules/example_module/` создайте файл `ExampleWidget.vue`:

```vue
<template>
  <div class="example-widget">
    <h3>Пример виджета</h3>
    <p>{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const message = ref('Загрузка...')

onMounted(async () => {
  const res = await fetch('/api/v1/example/status')
  const data = await res.json()
  message.value = data.message
})
</script>
</style>
```

---

### Шаг 5: Регистрация Виджета

Зарегистрируйте созданный виджет в реестре виджетов фронтенда (`widgets.ts`). Модуль будет автоматически подключен при перезапуске!
