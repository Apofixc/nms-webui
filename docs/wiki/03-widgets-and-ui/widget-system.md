# Система виджетов дашборда

Виджеты позволяют модулям NMS WebUI транслировать ключевую оперативную информацию и элементы управления напрямую на главный экран системы.

---

## 📊 Типы виджетов

1. **Summary Widget (Сводка на главном дашборде)**:
   - Легковесный виджет, отображающий общие метрики модуля (онлайн-устройства, алармы, статус соединения).
   - Запрашивается фронтендом через `/api/modules/summary_widget` или эндпоинт модуля `/api/v1/m/{module_id}/widgets/summary`.

2. **Custom Dashboard Component (Интерактивные карточки)**:
   - Полноценные Vue 3 компоненты, предоставляемые модулем для отображения графиков, видеопотоков или элементов управления.

---

## 📄 Спецификация ответа Summary Widget

Ответ REST API для сводного виджета должен иметь следующую структуру JSON:

```json
{
  "module_id": "tuya",
  "title": "Устройства Tuya",
  "status": "ok",
  "icon": "home_iot",
  "updated_at": "2026-08-01T18:00:00Z",
  "metrics": [
    {
      "label": "Всего устройств",
      "value": 15,
      "unit": "шт"
    },
    {
      "label": "В сети",
      "value": 13,
      "badge_type": "success"
    },
    {
      "label": "Не в сети",
      "value": 2,
      "badge_type": "warning"
    }
  ],
  "actions": [
    {
      "label": "Обновить статус",
      "action_id": "refresh_status",
      "icon": "sync"
    }
  ]
}
```

---

## 🛠️ Пример реализация виджета в Backend модуля

```python
from fastapi import APIRouter, Depends
from backend.core.auth import CurrentUser, require_permission

router = APIRouter(prefix="/api/v1/m/tuya/widgets", tags=["tuya-widgets"])

@router.get("/summary")
async def get_tuya_summary_widget(
    user: CurrentUser = Depends(require_permission("tuya.read"))
):
    total = 15
    online = 13
    
    return {
        "module_id": "tuya",
        "title": "Tuya IoT Hub",
        "status": "ok" if online > 0 else "error",
        "icon": "devices",
        "metrics": [
          {"label": "Всего", "value": total},
          {"label": "Онлайн", "value": online}
        ]
    }
```

---

## 🎨 Оформление и стилевые рекомендации

Для виджетов рекомендуются следующие правила внешнего вида:
- Использовать единые переменные цветов (`var(--color-primary)`, `var(--color-surface)`).
- Скруглять углы контейнеров классными карточками `rounded-xl border border-outline-variant/60`.
- Применять эффект свечения `shadow-glow` для подчеркивания активных элементов.
