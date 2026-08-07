# 🧩 12. Виджеты, их устройство и API (Widgets API)

---

## 📌 Назначение и концепция виджетов

Виджеты — это интерактивные карточки для Дашборда (`/dashboard`), визуализирующие графики, списки или кнопки управления.

Виджет объявляется в массиве `widgets` файла манифеста `manifest.yaml`:

```yaml
widgets:
  - id: "sensor-summary"
    title: "sensorWidgetTitle"
    endpoint: "/api/v1/m/sensor_monitor/widgets/summary"
    component: "SensorWidget"
    size: "medium"                        # "small" (1x1) | "medium" (2x2) | "large" (4x2)
    refresh_interval: 5                   # Автообновление в секундах
    resizable: true
```

---

## 🐍 Backend API данных виджета

Бэкенд должен предоставить HTTP GET эндпоинт, указанный в `endpoint`:

```python
@router.get("/widgets/summary")
async def get_widget_summary():
    return {
        "status": "ok",
        "data": {
            "total": 42,
            "online": 40,
            "offline": 2
        }
    }
```

---

## 🎨 Vue-компонент виджета

Компонент получает входные данные через `props`:

```vue
<template>
  <div class="p-4 bg-slate-800 text-white rounded">
    <h4>{{ widget.title }}</h4>
    <div>В сети: {{ data.online }} / {{ data.total }}</div>
  </div>
</template>

<script setup>
defineProps({ widget: Object, data: Object })
</script>
```
