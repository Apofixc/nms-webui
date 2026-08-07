# 🌐 11. Использование локализации (i18n API)

---

## 📌 Движок мультиязычности (i18n)

Словари переводов задаются в `manifest.yaml` под секцией `i18n` или выносятся в отдельную директорию `locales/` (`locales/ru.json`, `locales/en.json`) (`i18n.py`):

```yaml
i18n:
  ru:
    sensorTitle: "Мониторинг Датчиков"
    sensorErrOverheat: "Внимание: Сенсор '{name}' перегрет ({val}°C)"
  en:
    sensorTitle: "Sensor Monitoring"
    sensorErrOverheat: "Warning: Sensor '{name}' overheated ({val}°C)"
```

---

## 🐍 Использование на бэкенде (`tr()`)

```python
from backend.core.i18n import tr

msg = tr(
    lang="ru",
    key="sensorErrOverheat",
    name="Датчик-101",
    val=89.5
)
# Выведет: "Внимание: Сенсор 'Датчик-101' перегрет (89.5°C)"
```

---

## 🎨 Использование во Vue фронтенде

Во Vue-компонентах переводы доступны через функцию `$t()`:

```html
<template>
  <h3>{{ $t('sensorTitle') }}</h3>
</template>
```
