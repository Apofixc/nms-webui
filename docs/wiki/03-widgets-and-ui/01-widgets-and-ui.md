# 🏗 Виджеты, Рендерер и Дизайн-система (Widget System & Design Tokens)

---

## 🖼 Система виджетов (Widget System)

Интерфейс главными дашбордов NMS WebUI строится на базе модульной сетки, в которую монтируются независимые UI-виджеты.

### Ключевые компоненты архитектуры:
1. **Реестр виджетов бэкенда**: Собирает схемы виджетов из всех `manifest.yaml` файлов через эндпоинт `/api/modules/widgets`.
2. **Фронтенд-реестр (`widgets.ts`)**: Хранилище `activeWidgets` и функция выполнения интерактивных действий `executeWidgetAction()`.
3. **Универсальный Рендерер (`WidgetRenderer.vue`)**: Автономный компонент, отвечающий за позиционирование, подписку на live-стримы, опрос API, Drag & Drop, ресайз и разграничение прав доступа.

```svg
<svg viewBox="0 0 740 280" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g-dash" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="g-w1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="100%" stop-color="#1d4ed8"/>
    </linearGradient>
    <linearGradient id="g-w2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6"/>
      <stop offset="100%" stop-color="#6d28d9"/>
    </linearGradient>
  </defs>

  <!-- Container -->
  <rect x="10" y="10" width="720" height="260" rx="16" fill="url(#g-dash)" stroke="#334155" stroke-width="2"/>
  <text x="370" y="38" fill="#94a3b8" font-size="14" font-weight="bold" text-anchor="middle" font-family="sans-serif">Dashboard Grid Page (Freeform / Responsive Grid)</text>

  <!-- Widget 1 Card -->
  <g transform="translate(30, 55)">
    <rect width="320" height="190" rx="12" fill="#0f172a" stroke="#3b82f6" stroke-width="1.5"/>
    <!-- Header -->
    <rect width="320" height="36" rx="12" fill="url(#g-w1)"/>
    <text x="15" y="23" fill="#ffffff" font-size="12" font-weight="bold" font-family="sans-serif">WidgetRenderer: Tuya Devices</text>
    <text x="290" y="23" fill="#93c5fd" font-size="10" font-weight="bold" font-family="sans-serif">LIVE</text>
    <!-- Content -->
    <text x="15" y="60" fill="#94a3b8" font-size="11" font-family="sans-serif">• Data Source: SSE / WebSocket Stream</text>
    <text x="15" y="80" fill="#94a3b8" font-size="11" font-family="sans-serif">• Component: TuyaWidget.vue (Custom SFC)</text>
    <text x="15" y="100" fill="#94a3b8" font-size="11" font-family="sans-serif">• RBAC Check: module.tuya.view</text>
    <rect x="15" y="125" width="290" height="45" rx="6" fill="#1e293b" stroke="#475569"/>
    <text x="25" y="152" fill="#34d399" font-size="12" font-weight="bold" font-family="sans-serif">Metrics: 4 Devices Online (0 Errors)</text>
  </g>

  <!-- Widget 2 Card -->
  <g transform="translate(390, 55)">
    <rect width="320" height="190" rx="12" fill="#0f172a" stroke="#8b5cf6" stroke-width="1.5"/>
    <!-- Header -->
    <rect width="320" height="36" rx="12" fill="url(#g-w2)"/>
    <text x="15" y="23" fill="#ffffff" font-size="12" font-weight="bold" font-family="sans-serif">WidgetRenderer: System Health</text>
    <!-- Content -->
    <text x="15" y="60" fill="#94a3b8" font-size="11" font-family="sans-serif">• Data Source: REST API Polling (15s)</text>
    <text x="15" y="80" fill="#94a3b8" font-size="11" font-family="sans-serif">• Component: Standard Metrics View</text>
    <text x="15" y="100" fill="#94a3b8" font-size="11" font-family="sans-serif">• Actions: Execute POST /api/system/clean</text>
    <rect x="15" y="125" width="290" height="45" rx="6" fill="#1e293b" stroke="#475569"/>
    <text x="25" y="152" fill="#60a5fa" font-size="12" font-weight="bold" font-family="sans-serif">CPU: 12% | RAM: 1.4GB / 8GB</text>
  </g>
</svg>
```

---

## 📋 Контракты данных и TypeScript Интерфейсы

Каждый виджет взаимодействует с бэкендом по строгому JSON-контракту:

### 1. Интерфейс определения виджета (`ModuleWidget`):
```typescript
export interface ModuleWidget {
  id: string                   // Уникальный ID виджета
  module_id: string            // ID родительского модуля
  title: string                // Название виджета или ключ i18n
  description: string          // Описание виджета
  component: string            // Имя Vue-компонента
  endpoint?: string            // REST API эндпоинт данных
  stream_endpoint?: string     // SSE / WebSocket эндпоинт live-потока
  size?: 'small' | 'medium' | 'large' // Дефолтный размер
  refresh_interval?: number    // Интервал опроса в секундах
  type?: 'summary' | 'stat' | 'list' | 'custom'
  default_active?: boolean     // Отображать ли по умолчанию
  resizable?: boolean          // Разрешено ли изменять размеры
  view_permission?: string     // Право на просмотр
  control_permission?: string  // Право на управление
}
```

### 2. Структура ответа данных эндпоинта (`WidgetData`):
```typescript
export interface WidgetMetric {
  id: string
  label: string
  value: any
  unit?: string
  status?: 'ok' | 'warning' | 'error' | 'info'
  icon?: string
}

export interface WidgetAction {
  label: string                // Текст кнопки или ключ i18n
  path?: string                // Vue Router путь для перехода
  icon?: string                // Иконка Material Symbols
  endpoint?: string            // REST API эндпоинт для вызова
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' // HTTP метод
  payload?: Record<string, any>// Передаваемое тело запроса
  confirm?: string             // Текст подтверждения (modal)
}

export interface WidgetData {
  status?: 'ok' | 'warning' | 'error' | 'info'
  type?: 'summary' | 'stat' | 'list' | 'custom'
  title?: string
  metrics?: WidgetMetric[]     // Набор показателей для типа summary/stat
  items?: Array<Record<string, any>> // Список объектов для типа list
  actions?: WidgetAction[]     // Доступные интерактивные кнопки
  updated_at?: string          // Метка времени обновления
}
```

### 3. Контракт Props пользовательских виджетов (`WidgetProps<T>`):
Все пользовательские Vue-компоненты виджетов получают стандартные `props` и `emits`:

```typescript
export interface WidgetProps<T = WidgetData> {
  data: T | null               // Загруженные данные
  loading: boolean             // Статус загрузки
  error: string | null         // Текст ошибки при загрузке
  canControl?: boolean         // Наличие прав на управление
  isCustomizing?: boolean      // Включен ли режим настройки сетки
  widget?: ModuleWidget        // Конфигурация виджета
}
```

---

## ⚡️ Внутреннее устройство `WidgetRenderer.vue`

Компонент `WidgetRenderer.vue` выполняет следующие критические задачи:

1. **Адаптивное позиционирование (`cardStyle`)**:
   - **Десктоп**: Абсолютное позиционирование (`position: absolute`, `left`, `top`, `width`, `height`, `zIndex`).
   - **Мобильные устройства**: Относительный стек карт (`position: relative`, `width: 100%`).
2. **Механика Drag & Drop и Resize**:
   - Отслеживание событий указателя `onMovePointerDown` и `onResizePointerDown` для свободного перемещения и изменения размеров виджетов в режиме кастомизации.
3. **Оптимизация сетевой нагрузки (Visibility Change)**:
   - Слушает событие `visibilitychange` браузера: при свертывании окна или переключении вкладки стрим WebSockets/SSE автоматически разрывается, а опрос по `refresh_interval` приостанавливается. При возврате вкладки соединение мгновенно восстанавливается.
4. **Контроль прав доступа (RBAC)**:
   - Автоматически проверяет права `canView` и `canControl` через функцию `hasPermission()`. Если прав не достаточно, отображается заглушка блокировки доступа без запросов к бэкенду.
5. **Предотвращение падений UI (Error Boundary)**:
   - Если пользовательский компонент содержит синтаксическую ошибку, `defineAsyncComponent` перехватывает её через `onError`, отображая изолированную плашку ошибки в рамке виджета вместо краша всей страницы.

---

## 🎨 Дизайн-система и Токены (Theme Tokens)

Стилизация NMS WebUI построена на базе единой темы CSS-переменных:

### Переменные цветов и поверхностей:

```css
:root {
  --bg-surface: #0f172a;                /* Основной фон страниц */
  --surface-container-low: #1e293b;     /* Фон карточек виджетов */
  --surface-container-high: #334155;    /* Фон внутренних блоков */
  --text-primary: #f8fafc;              /* Основной цвет текста */
  --text-on-surface-variant: #94a3b8;   /* Вторичный цвет текста */
  --border-color: rgba(148, 163, 184, 0.2); /* Границы элементов */
  
  /* Акцентные цвета */
  --primary: #3b82f6;                   /* Синий акцент */
  --secondary: #8b5cf6;                 /* Фиолетовый акцент */
  --tertiary: #10b981;                  /* Изумрудный (Успех / ОК) */
  --error: #ef4444;                     /* Красный (Ошибки / Тревоги) */
  --warning: #f59e0b;                   /* Янтарь (Предупреждения) */
}
```

### Использование токенов в компонентах:

```vue
<template>
  <div class="custom-card">
    <h4 class="card-title">Заголовок</h4>
  </div>
</template>

<style scoped>
.custom-card {
  background-color: var(--surface-container-low);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
}
.card-title {
  color: var(--text-primary);
}
</style>
```
