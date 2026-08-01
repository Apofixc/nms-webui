# Система виджетов дашборда

Виджеты позволяют модулям встраивать интерактивные карточки и сводки на главный дашборд NMS WebUI.

## Типы виджетов

1. **Summary Widget (Сводный виджет)**:
   - Эндпоинт: `GET /api/modules/summary_widget` или `/api/v1/m/{module_id}/widgets/summary`.
   - Назначение: Компактное отображение ключевых метрик (количество активных устройств, статус подключения, алармы).

2. **Custom Dashboard Widgets**:
   - Динамические компоненты, доступные через реестр виджетов `/api/modules/widgets`.

## Формат ответа Summary Widget

```json
{
  "module_id": "tuya",
  "title": "Устройства Tuya",
  "status": "ok",
  "metrics": [
    { "label": "Всего", "value": 12 },
    { "label": "Онлайн", "value": 10 }
  ]
}
```
