# Полное руководство по системе виджетов NMS-WebUI

Виджеты NMS-WebUI позволяют модулям и встроенным сервисам транслировать оперативную информацию, сводки показателей и интерактивные элементы управления напрямую на главный холст (Canvas) рабочего стола.

---

## 📁 1. Структура и авто-обнаружение

Система построена по принципу **Zero-Configuration**. Все виджеты размещаются в строго выделенных папках `widgets`:

* **Базовые виджеты ядра**: `frontend/src/widgets/`
* **Виджеты динамических модулей**: `frontend/src/modules/<module_id>/widgets/`

Загрузчик `loader.ts` автоматически обнаруживает файлы виджетов через Vite `import.meta.glob(['../widgets/**/*.vue', '../modules/**/widgets/**/*.vue'])` и регистрирует их в реестре компонентов.

---

## 📜 2. Декларация виджета в манифесте (`manifest.yaml`)

Каждый динамический модуль описывает свои виджеты в секции `widgets:` файла `manifest.yaml`:

```yaml
widgets:
  - id: "tuya-summary"                          # Уникальный ID виджета
    title: "tuyaWidgetTitle"                    # Ключ локализации или название
    description: "tuyaWidgetDesc"              # Описание для каталога виджетов
    endpoint: "/api/v1/m/tuya/widgets/summary"  # REST API эндпоинт данных виджета
    component: "TuyaWidget"                    # (Опционально) Имя Vue-компонента в папке widgets/
    size: "medium"                             # Начальный размер (small | medium | large)
    refresh_interval: 15                       # Период авто-обновления в секундах
    view_permission: "module.tuya.view"        # Право на просмотр виджета
    control_permission: "module.tuya.control"  # Право на выполнение управляющих действий
    default_active: true                       # Отображать ли на дашборде по умолчанию
```

---

## 💻 3. Разработка кастомных Vue-виджетов

Все кастомные Vue-компоненты виджетов получают стандартные входные параметры и события через TypeScript контракты `@/modules/widgets`:

```html
<template>
  <div class="p-3 space-y-3">
    <!-- Индикация загрузки -->
    <div v-if="loading" class="animate-pulse text-xs text-on-surface-variant">
      Обновление данных...
    </div>

    <!-- Отображение ошибки -->
    <div v-else-if="error" class="text-xs text-error">
      {{ error }}
    </div>

    <!-- Верстка данных виджета -->
    <div v-else-if="data" class="space-y-2">
      <div class="text-sm font-bold text-on-surface">
        Устройств онлайн: {{ data.metrics?.[0]?.value }}
      </div>

      <!-- Управляющая кнопка с проверкой прав canControl -->
      <button
        @click="triggerAction"
        :disabled="!canControl"
        class="px-3 py-1 rounded bg-primary text-on-primary text-xs font-semibold disabled:opacity-40"
      >
        Перезапустить
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { type WidgetProps, type WidgetEmits, executeWidgetAction } from '@/modules/widgets'

// Строгая типизация Props и Emits
const props = defineProps<WidgetProps>()
const emit = defineEmits<WidgetEmits>()

async function triggerAction() {
  if (!props.canControl) return
  await executeWidgetAction({
    endpoint: '/api/v1/m/tuya/control/restart',
    method: 'POST',
    payload: { force: true }
  })
  emit('refresh') // Принудительно обновить данные виджета
}
</script>
```

---

## 🔐 4. Двухуровневая система прав доступа (RBAC)

Каждый виджет автоматически валидирует права авторизованного пользователя:

1. **Право на просмотр (`view_permission`)**:
   * Если у пользователя **нет права на просмотр**, виджет не запрашивает данные из API.
   * Вместо содержимого рендерится защищенная карточка с иконкой замка 🔒 и сообщением **«Доступ ограничен»**.
2. **Право на управление (`control_permission`)**:
   * Передается в параметр `canControl: boolean`.
   * При отсутствии прав на управление виджет доступен для просмотра, но все интерактивные кнопки становятся заблокированными (`disabled`) с подсказкой про недостаток прав.

---

## ⚡ 5. Интерактивные действия и WebSocket / SSE

Виджеты поддерживают 2 типа динамического взаимодействия:

### Интерактивные экшены (`actions`):
В ответе API бэкенда объект `WidgetData` может содержать массив `actions`:
```json
"actions": [
  {
    "label": "Сбросить аларм",
    "endpoint": "/api/v1/m/tuya/device/alarm/reset",
    "method": "POST",
    "payload": { "clear": true },
    "confirm": "Вы уверены, что хотите сбросить аларм?"
  }
]
```
При нажатии на кнопку контейнер [WidgetRenderer.vue](file:///opt/nms-webui/frontend/src/components/common/WidgetRenderer.vue) выводит окно подтверждения, отправляет HTTP-запрос со спиннером загрузки и при успехе обновляет данные.

---

## 🎨 6. Физика холста и Режимы коллизий

Управление расположением карточек на дашборде осуществляется в режиме **«Настроить рабочий стол»**:

1. **Сетка (Snap to Grid)**: Все координаты выравниваются с шагом в **15px**.
2. **Режимы предотвращения коллизий (`collisionMode`)**:
   * **Направленный сдвиг (`push`)**: При перетаскивании виджета справа налево пересекаемый виджет автоматически смещается влево (и аналогично по вектору движения вверх/вниз/вправо).
   * **Запрет с рамкой (`block`)**: При пересечении карточек на холсте подсвечивается **красная пунктирная зона коллизии**, а попытка сбросить виджет на чужую позицию блокируется.
   * **Свободно (`off`)**: Карточки свободно перекрывают друг друга.
3. **Скрытие и Показ**:
   * Скрытые виджеты не тратят сетевой трафик и память в обычном режиме.
   * В режиме настройки они отображаются полупрозрачной рамкой для быстрого восстановления.
4. **Сохранение макета**: Позиции, размеры, видимость и выбранный режим коллизий сохраняются в `localStorage` (`nms_widget_canvas_v3`).
