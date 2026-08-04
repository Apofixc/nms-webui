# 🏗 Ядро и Архитектурный Каркас

---

## 🏛 Архитектурный каркас NMS WebUI

Система спроектирована по схеме с динамически расширяемым бэкендом и фронтендом.

```svg
<svg viewBox="0 0 760 310" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad-frontend" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="100%" stop-color="#1d4ed8"/>
    </linearGradient>
    <linearGradient id="grad-backend" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6"/>
      <stop offset="100%" stop-color="#6d28d9"/>
    </linearGradient>
    <linearGradient id="grad-db" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#047857"/>
    </linearGradient>
    <linearGradient id="grad-driver" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ec4899"/>
      <stop offset="100%" stop-color="#be185d"/>
    </linearGradient>
    
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#94a3b8"/>
    </marker>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#60a5fa"/>
    </marker>
  </defs>

  <g transform="translate(230, 15)">
    <rect width="300" height="64" rx="14" fill="url(#grad-frontend)" filter="drop-shadow(0 4px 12px rgba(59, 130, 246, 0.35))"/>
    <text x="150" y="28" fill="#ffffff" font-size="15" font-weight="bold" text-anchor="middle" font-family="sans-serif">Vue 3 Frontend</text>
    <text x="150" y="48" fill="#dbeafe" font-size="11" text-anchor="middle" font-family="sans-serif">(Pinia, TypeScript, WidgetRenderer)</text>
  </g>

  <line x1="380" y1="79" x2="380" y2="128" stroke="#60a5fa" stroke-width="2.5" stroke-dasharray="6,4" marker-end="url(#arrow-blue)"/>
  
  <rect x="290" y="91" width="180" height="24" rx="12" fill="#1e293b" stroke="#3b82f6" stroke-width="1.5"/>
  <text x="380" y="107" fill="#93c5fd" font-size="10" font-weight="600" text-anchor="middle" font-family="sans-serif">HTTP / WebSockets / SSE</text>

  <g transform="translate(210, 130)">
    <rect width="340" height="66" rx="14" fill="url(#grad-backend)" filter="drop-shadow(0 4px 12px rgba(139, 92, 246, 0.35))"/>
    <text x="170" y="29" fill="#ffffff" font-size="15" font-weight="bold" text-anchor="middle" font-family="sans-serif">FastAPI Backend</text>
    <text x="170" y="49" fill="#ede9fe" font-size="11" text-anchor="middle" font-family="sans-serif">(Core Engine, Plugin Dynamic Loader)</text>
  </g>

  <line x1="290" y1="196" x2="210" y2="240" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="470" y1="196" x2="550" y2="240" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>

  <g transform="translate(100, 242)">
    <rect width="220" height="54" rx="12" fill="url(#grad-db)" filter="drop-shadow(0 4px 10px rgba(16, 185, 129, 0.25))"/>
    <text x="110" y="24" fill="#ffffff" font-size="13" font-weight="bold" text-anchor="middle" font-family="sans-serif">SQLite WAL</text>
    <text x="110" y="41" fill="#d1fae5" font-size="11" text-anchor="middle" font-family="sans-serif">(nms.db)</text>
  </g>

  <g transform="translate(440, 242)">
    <rect width="220" height="54" rx="12" fill="url(#grad-driver)" filter="drop-shadow(0 4px 10px rgba(236, 72, 153, 0.25))"/>
    <text x="110" y="24" fill="#ffffff" font-size="13" font-weight="bold" text-anchor="middle" font-family="sans-serif">External Drivers</text>
    <text x="110" y="41" fill="#fce7f3" font-size="11" text-anchor="middle" font-family="sans-serif">(Devices &amp; Hardware)</text>
  </g>
</svg>
```

```
/opt/nms-webui/
├── backend/
│   ├── core/                  # Системные ядра (БД, Auth, Plugin Loader)
│   │   ├── plugin/            # Манифесты и менеджер плагинов
│   │   │   └── manifest.py    # Базовые классы и валидация манифестов
│   │   ├── auth/              # Авторизация и RBAC
│   │   └── database.py        # Сессия и подключения SQLite WAL
│   ├── modules/               # Динамические бэкенд-модули
│   └── main.py                # Точка входа FastAPI
├── frontend/
│   ├── src/
│   │   ├── components/        # Базовые компоненты UI и WidgetRenderer.vue
│   │   ├── modules/           # Динамические модули фронтенда и widgets.ts
│   │   ├── stores/            # Хранилища состояния (Pinia)
│   │   └── App.vue            # Главный компонент Vue
└── docs/                      # Документация и Вики
```

---

## 🔄 Жизненный цикл приложения

### 1. Старт Backend (FastAPI):
1. **Инициализация ядра**: Загружаются конфигурации `.env` и подготавливается подключение к `nms.db`.
2. **Сканирование модулей**: Менеджер плагинов просматривает каталог `backend/modules/` и читает метаданные каждого `manifest.py`.
3. **Регистрация роутов**: Маршруты API, описанные в активных модулях, динамически монтируются в главный FastAPI роутер.
4. **Запуск фона**: Запускаются фоновые задачи (Event Bus, подписки на события и мониторинг логов).

### 2. Старт Frontend (Vue 3):
1. **Загрузка приложения**: Монтируется `App.vue`, инициализируются стили и темы.
2. **Получение структуры виджетов**: Приложение обращается к реестру виджетов (`widgets.ts`) и запрашивает доступные компоненты.
3. **Рендеринг дашборда**: Компонент `WidgetRenderer.vue` монтирует виджеты в определенные слоты.
