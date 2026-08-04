# Документация NMS WebUI

Добро пожаловать в официальный справочный центр платформы **NMS WebUI**, структурированный в формате **Mastra Docs**.

---

## 🧭 Навигация по разделам

```
├── 🏁 GETTING STARTED
│   ├── Быстрый старт                → 01-overview/quick-start.md
│   ├── Общая архитектура            → 01-overview/architecture.md
│   └── Ключевые концепции           → 01-overview/README.md
│
├── 🧩 GUIDES: ДИНАМИЧЕСКИЕ МОДУЛИ
│   ├── Полное руководство           → ../module-guide.md
│   ├── Жизненный цикл & 0 Rebuilds  → 02-module-development/plugin-lifecycle-and-hooks.md
│   ├── Права доступа & RBAC         → 02-module-development/permissions.md
│   ├── Настройки и БД               → 02-module-development/settings-and-db.md
│   └── Мультиязычность (i18n)      → 02-module-development/i18n-localization.md
│
├── 🎨 GUIDES: ИНТЕРФЕЙС И ВИДЖЕТЫ
│   ├── Виджеты Дашборда            → 03-widgets-and-ui/widget-system.md
│   └── Дизайн-система M3           → 03-widgets-and-ui/design-system-and-composables.md
│
├── 🔌 API REFERENCE
│   ├── REST API Справочник          → 04-backend-api/api-reference.md
│   ├── WebSockets & SSE             → 04-backend-api/events-and-websockets.md
│   └── Безопасность и 2FA           → 04-backend-api/security-auth-mfa.md
│
├── 🛠️ DEPLOYMENT & PRODUCTION
│   ├── Конфигурация & systemd       → 05-ops-and-deployment/configuration.md
│   ├── Резервное копирование        → 05-ops-and-deployment/backups-and-maintenance.md
│   ├── Логирование и Аудит          → 05-ops-and-deployment/logging-and-audit-system.md
│   └── Медиа-стриминг (MediaMTX)    → 05-ops-and-deployment/mediamtx-video-streaming.md
│
├── 🧪 TESTING & QA
│   ├── Backend Pytest               → 07-testing-and-qa/backend-testing.md
│   └── Frontend E2E                 → 07-testing-and-qa/frontend-testing.md
│
└── ❓ TROUBLESHOOTING
    └── FAQ & Диагностика           → 06-troubleshooting/FAQ.md
```

---

## ⚡ Быстрый обзор возможностей

- **Zero-Boilerplate Modules:** Разработка модулей без ручного переписывания основного кода.
- **0 Rebuilds Frontend:** Подгрузка и компиляция сырых `.vue` файлов прямо в браузере клиента ([`vueSfcLoader.ts`](file:///opt/nms-webui/frontend/src/core/vueSfcLoader.ts)).
- **Dual Install/Uninstall:** Установка простым копированием папок или исполнением `install.sh`/`uninstall.sh` скриптов.
- **Strict Sandboxing:** Изолированные директории хранения данных модуля в `backend/data/modules/<id>/`.
- **Real-Time Integration:** Полная поддержка WebSocket и SSE рассылок через `EventBroadcaster`.

