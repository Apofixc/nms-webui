# Интернационализация (i18n) и локализация модулей

Руководство по добавлению мультиязычной поддержки (русский, английский) в бэкенд и фронтенд пользовательских модулей NMS WebUI.

---

## 🌐 Архитектурный подход к локализации

NMS WebUI поддерживает динамическое переключение языков интерфейса без перезагрузки страницы. Локализация строится на следующих принципах:

1. **Единые ключи локализации**: В `manifest.yaml` используются строковые ключи (например, `tuyaTitle`, `tuyaSub`), которые автоматически сопоставляются со словарями.
2. **Словари внутри модуля**: Модули хранят файлы переводов в папке `backend/modules/<module_id>/locales/` (`ru.json`, `en.json`).
3. **Автоматическая передача клиенту**: Бэкенд объединяет системные переводы с переводами активных модулей и отдаёт их фронтенду.

---

## 📁 Структура файлов локализации модуля

Файлы локализации размещаются в поддиректории `locales/` вашего модуля:

```text
backend/modules/tuya/
├── manifest.yaml
└── locales/
    ├── ru.json    # Русские переводы
    └── en.json    # Английские переводы
```

### Пример файла `locales/ru.json`:

```json
{
  "tuyaTitle": "Устройства Tuya IoT",
  "tuyaSub": "Интеграция и управление умными устройствами Tuya",
  "tuyaClientId": "Access ID (Client ID)",
  "tuyaGroupCloud": "Параметры подключения к Tuya Cloud",
  "tuyaGroupControl": "Параметры опроса устройств",
  "permName_module.tuya.view": "Просмотр Tuya устройств",
  "permDesc_module.tuya.view": "Разрешает доступ к просмотру списка устройств и виджетов Tuya"
}
```

### Пример файла `locales/en.json`:

```json
{
  "tuyaTitle": "Tuya IoT Devices",
  "tuyaSub": "Tuya Smart Devices integration and management",
  "tuyaClientId": "Access ID (Client ID)",
  "tuyaGroupCloud": "Tuya Cloud Connection Settings",
  "tuyaGroupControl": "Device Polling Settings",
  "permName_module.tuya.view": "View Tuya Devices",
  "permDesc_module.tuya.view": "Allows viewing Tuya device lists and dashboard widgets"
}
```

---

## 🐍 Локализация на Backend (Python)

Для локализации сообщений об ошибках, ответов API или сообщений аудита на стороне бэкенда используйте утилиту `tr` из `backend.core.i18n`:

```python
from fastapi import APIRouter, Request, Depends
from backend.core.i18n import tr
from backend.core.auth import CurrentUser, require_permission

router = APIRouter(prefix="/api/v1/m/tuya", tags=["tuya"])

@router.post("/sync")
async def sync_devices(
    request: Request,
    user: CurrentUser = Depends(require_permission("tuya.control"))
):
    # Извлечение локализованной строки по текущему языку пользователя (Accept-Language или куки)
    msg = tr(request, "tuyaSyncSuccess")
    
    return {
        "status": "success",
        "message": msg
    }
```

---

## 🖥️ Локализация на Frontend (Vue 3)

На фронтенде доступен композиция-хелпер `useI18n()` из `@/core/i18n`:

```vue
<template>
  <div class="p-4">
    <h1>{{ t('tuyaTitle') }}</h1>
    <p class="text-sm text-neutral-400">{{ t('tuyaSub') }}</p>

    <button class="btn-primary">
      {{ t('refresh') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '@/core/i18n'

const { t, locale } = useI18n()
</script>
```

> [!TIP]
> При объявлении элементов меню и роутов в `manifest.yaml` указывайте ключ локализации в поле `titleKey` или `label`. Фронтенд автоматически применит перевод при смене языка.
