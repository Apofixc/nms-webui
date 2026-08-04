# ⚙️ Backend API и WebSockets

---

## 📡 REST API Спецификация

Бэкенд NMS WebUI предоставляет REST API на базе FastAPI.
- **Спецификация OpenAPI**: Генерируется автоматически на основе Pydantic-схем.
- **Интерактивная документация**: Доступна по адресу `/docs` (Swagger UI) и `/redoc` при запущенном бэкенде.

---

## 🔄 Событийная модель реального времени (WebSockets & SSE)

Для передачи оперативной информации (изменение статусов узлов, аварийные тревоги, новые логи) используются протоколы **WebSocket** и **Server-Sent Events (SSE)**.

### Формат сообщений WebSocket:
Все системные события транслируются в едином JSON-формате:

```json
{
  "event": "device_status_changed",
  "timestamp": "2026-08-04T22:50:00Z",
  "data": {
    "device_id": "node-102",
    "status": "online",
    "latency_ms": 14.2
  }
}
```
