# NMS — API к lib-monitor (Astra)

Минимальный слой: агрегация нескольких инстансов Astra (lib-monitor) и современный Web-интерфейс.

## Backend (только lib-monitor API)

- Конфиг инстансов в **YAML**: `instances.yaml` в корне (см. `instances.sample.yaml`).
- Эндпоинты:
  - `GET /api/instances` — список инстансов
  - `GET /api/instances/{id}/health` — health одного инстанса
  - `GET /api/aggregate/health` — health всех
  - `GET /api/aggregate/channels` — каналы со всех инстансов (с полем `instance_id`, `instance_port`)
  - `GET /api/aggregate/channels/stats` — сводная статистика
  - Прокси: `DELETE .../channels/kill`, `POST .../channels`, `GET .../channels/inputs`, `DELETE .../streams/kill`, `POST .../streams`

## Запуск

```bash
# Backend (создаёт .venv при первом запуске)
./run_backend.sh

# В другом терминале — frontend
cd frontend && npm install && npm run dev
```

Откройте http://localhost:5173. API: http://127.0.0.1:9000/docs

## Интерфейс

- Тёмная тема, шрифт Outfit, акцент cyan.
- Боковое меню: Дашборд (инстансы с индикатором Online/Offline), Каналы (сетка с бейджем порта, Restart / Switch Input).
