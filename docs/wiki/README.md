# База Знаний (Вики) NMS WebUI

Добро пожаловать в Базу Знаний и справочный центр разработчика платформы **NMS WebUI**. 

Здесь собраны подробные архитектурные руководства, инструкции по разработке модулей, справочники REST API, руководства по безопасности и деплою.

---

## 📚 Структура и Карта Базы Знаний

### 🚀 01. Обзор и Запуск (`01-overview`)
- 🏗️ [Архитектура NMS WebUI](file:///opt/nms-webui/docs/wiki/01-overview/architecture.md) — Схема взаимодействия Frontend, Backend, SQLite и MediaMTX.
- 📋 [Быстрый старт](file:///opt/nms-webui/docs/wiki/01-overview/quick-start.md) — Установка зависимостей, запуски в Dev Mode и конфигурация `.env`.

### 🧩 02. Разработка модулей (`02-module-development`)
- 📜 [Полное руководство по модулям](file:///opt/nms-webui/docs/module-guide.md) — Манифест `manifest.yaml`, точка входа и структура.
- 🔒 [Разрешения и RBAC](file:///opt/nms-webui/docs/wiki/02-module-development/permissions.md) — Объявление пермишенов, зависимости `require_permission` и аудит.
- ⚙️ [Настройки и Работа с БД](file:///opt/nms-webui/docs/wiki/02-module-development/settings-and-db.md) — Хранение настроек в JSON, собственные таблицы в SQLite.
- 🌐 [Локализация и i18n](file:///opt/nms-webui/docs/wiki/02-module-development/i18n-localization.md) — Мультиязычность модулей (`ru.json`, `en.json`), утилиты `tr()` и `useI18n()`.

### 🎨 03. Виджеты и UI (`03-widgets-and-ui`)
- 📊 [Система виджетов дашборда](file:///opt/nms-webui/docs/wiki/03-widgets-and-ui/widget-system.md) — Сводные карточки (Summary Widgets) и спецификации.
- 🎨 [Дизайн-система и Composables](file:///opt/nms-webui/docs/wiki/03-widgets-and-ui/design-system-and-composables.md) — Material 3 Expressive Tokens, эффект `shadow-glow`, Tailwind и Vue composables.

### 🔌 04. Backend & REST API (`04-backend-api`)
- 🔑 [Справочник REST API](file:///opt/nms-webui/docs/wiki/04-backend-api/api-reference.md) — Основные системные эндпоинты авторизации, бэкапов и модулей.
- ⚡ [События, WebSockets и SSE](file:///opt/nms-webui/docs/wiki/04-backend-api/events-and-websockets.md) — Броадкастинг событий через `EventBroadcaster`, WebSocket сокеты и SSE подписки.
- 🛡️ [Безопасность, 2FA и Сессии](file:///opt/nms-webui/docs/wiki/04-backend-api/security-auth-mfa.md) — TOTP / MFA (RFC 6238), QR SVG генератор, отзыв сессий и аудит.

### 🛠️ 05. Деплой и Интеграции (`05-ops-and-deployment`)
- 🐧 [Конфигурация и Обслуживание](file:///opt/nms-webui/docs/wiki/05-ops-and-deployment/configuration.md) — Настройка systemd сервисов, Nginx Reverse Proxy и `.env`.
- 📹 [Интеграция Видео (MediaMTX)](file:///opt/nms-webui/docs/wiki/05-ops-and-deployment/mediamtx-video-streaming.md) — *[Roadmap]* Проект архитектуры трансляции RTSP/HLS/WebRTC видеопотоков.

### ❓ 06. Поиск решений (`06-troubleshooting`)
- 💡 [Частые вопросы (FAQ)](file:///opt/nms-webui/docs/wiki/06-troubleshooting/FAQ.md) — Ответы на популярные вопросы, блокировки SQLite и сброс паролей.
