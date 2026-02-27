# Stream Module (new architecture)

## Структура
- `core/` — типы (StreamTask/StreamResult), контракт IStreamBackend, loader/router, pipeline, worker_pool.
- `submodules/` — бэкенды:
  - external: ffmpeg, vlc, astra, gstreamer, tsduck
  - pure: pure_proxy (http/hls/udp), pure_preview (http/udp mjpeg), pure_webrtc (signaling stub)
  - echo — dummy для тестов
- `adapters/` — legacy API (`capture_frame`, `dict↔task/result` конвертеры) с feature flag.
- `tests/` — unittest для loader/router, worker_pool, pure_*.
- `manifest_schema.json` — jsonschema для субмодульных manifest.yaml.

## Манифест субмодуля
Пример `submodules/ffmpeg/manifest.yaml`:
```yaml
meta:
  name: "ffmpeg"
  version: "1.0.0"
  entry_point: "backend:FFmpegBackend"
  enabled: true
capabilities:
  protocols: ["udp", "http", "rtsp"]
  outputs: ["http_ts", "jpg"]
  features: ["transcoding"]
  priority_matrix:
    udp: { http_ts: 80 }
resources:
  binaries: ["ffmpeg", "ffprobe"]
config_schema: {type: object}
```
Схема в `manifest_schema.json` используется loader'ом при наличии jsonschema.

## Тесты
- `python3 -m unittest backend.modules.stream.tests.test_loader_router_unittest`
- `python3 -m unittest backend.modules.stream.tests.test_worker_pool_unittest`
- `python3 -m unittest backend.modules.stream.tests.test_pure_backends_unittest`
- Покрытие: `python3 -m coverage run -m unittest discover backend/modules/stream/tests && python3 -m coverage report`

## Работа без внешних зависимостей
- pydantic/jsonschema/httpx — опциональны: есть fallback/stub импорты, loader пропускает неподходящие manifests.
- pure_* бэкенды не требуют ffmpeg/vlc/gstreamer.

## Известные ограничения
- pure_preview: rtsp/h264 пока возвращает dummy PNG, UDP MJPEG — best effort.
- pure_webrtc: signaling stub, без реальных медиа-треков.
- pure_proxy: udp→http простая реализация, без гарантий качества сервиса.
