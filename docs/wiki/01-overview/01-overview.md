# 🚀 Обзор системы и ключевые концепции

---

## 📌 Назначение NMS WebUI

**NMS WebUI** (Network Management System Web Interface) — это современная модульная платформа для мониторинга, визуализации и централизованного управления сетевой инфраструктурой, узлами оборудования и связанными медиапотоками.

Платформа предназначена для:
- Сбора телеметрии и метрик с сетевых устройств в режиме реального времени.
- Отображения интерактивных дашбордов с кастомизируемой сеткой виджетов.
- Бесшовного подключения динамических плагинов и модулей расширения без изменения ядра.
- Просмотра и трансляции оперативных видеопотоков (RTSP/WebRTC/HLS) через встроенный медиасервер.
- Обеспечения строгой авторизации (RBAC) и ведения непрерывного журнала аудита.

---

## 🏗 Архитектурный стек

NMS WebUI построена по микросервисной/модульной веб-архитектуре:

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
    <linearGradient id="grad-media" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#d97706"/>
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

  <line x1="280" y1="196" x2="130" y2="240" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="380" y1="196" x2="380" y2="240" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="480" y1="196" x2="630" y2="240" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>

  <g transform="translate(40, 242)">
    <rect width="180" height="54" rx="12" fill="url(#grad-db)" filter="drop-shadow(0 4px 10px rgba(16, 185, 129, 0.25))"/>
    <text x="90" y="24" fill="#ffffff" font-size="13" font-weight="bold" text-anchor="middle" font-family="sans-serif">SQLite WAL</text>
    <text x="90" y="41" fill="#d1fae5" font-size="11" text-anchor="middle" font-family="sans-serif">(nms.db)</text>
  </g>

  <g transform="translate(290, 242)">
    <rect width="180" height="54" rx="12" fill="url(#grad-media)" filter="drop-shadow(0 4px 10px rgba(245, 158, 11, 0.25))"/>
    <text x="90" y="24" fill="#ffffff" font-size="13" font-weight="bold" text-anchor="middle" font-family="sans-serif">MediaMTX</text>
    <text x="90" y="41" fill="#fef3c7" font-size="11" text-anchor="middle" font-family="sans-serif">(RTSP / WebRTC / HLS)</text>
  </g>

  <g transform="translate(540, 242)">
    <rect width="180" height="54" rx="12" fill="url(#grad-driver)" filter="drop-shadow(0 4px 10px rgba(236, 72, 153, 0.25))"/>
    <text x="90" y="24" fill="#ffffff" font-size="13" font-weight="bold" text-anchor="middle" font-family="sans-serif">External Drivers</text>
    <text x="90" y="41" fill="#fce7f3" font-size="11" text-anchor="middle" font-family="sans-serif">(Devices &amp; Hardware)</text>
  </g>
</svg>
```

### Ключевые компоненты:
1. **Frontend**: Приложение на **Vue 3** + **TypeScript**, использующее компонентный подход, реактивную систему состояния (Pinia) и динамические слоты виджетов (`WidgetRenderer.vue`).
2. **Backend**: Высокопроизводительный сервер на **FastAPI** (Python 3.10+), поддерживающий динамическое сканирование и загрузку плагинов через манифесты (`manifest.py`).
3. **Хранилище данных**: **SQLite3** с включенным режимом **WAL (Write-Ahead Logging)**, обеспечивающим высокую параллельность чтения и надежность транзакций.
4. **Медиасервер**: Встроенный **MediaMTX** (`mediamtx.yml`) для маршрутизации и трансляции видеопотоков с IP-камер и устройств.

---

## 📖 Глоссарий терминов

| Термин | Описание |
| :--- | :--- |
| **NMS** | Network Management System — система управления сетевыми ресурсами. |
| **Plugin / Dynamic Module** | Независимый изолированный модуль, содержащий собственный манифест, роуты, модели БД и компоненты интерфейса. |
| **Plugin Manifest** | Файл `manifest.py`, описывающий метаданные плагина, зависимости, права и точки расширения. |
| **Slot (Слот)** | Заранее определенная область в UI, в которую модули могут встраивать свои виджеты и кнопки. |
| **Widget (Виджет)** | Интерактивный компонент интерфейса, монтируемый в дашборд. |
| **RBAC** | Role-Based Access Control — система разграничения прав пользователей на основе назначенных ролей. |
| **SQLite WAL** | Write-Ahead Logging — режим работы базы данных SQLite, при котором записи сначала фиксируются в отдельных лог-файлах. |
| **MediaMTX** | Легковесный медиасервер для трансляции потоков по протоколам RTSP, RTMP, WebRTC и HLS. |
