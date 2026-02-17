# Тесты NMS WebUI

## Тесты бэкендов (захват кадра и воспроизведение)

Проверяются:
- порядок бэкендов превью (FFmpeg → VLC → GStreamer → builtin);
- доступность бэкендов захвата и воспроизведения (http_ts, http_hls);
- захват кадра по HTTP (тестовый JPEG);
- наличие HLS-параметров в настройках и метод `start_hls` у HLS-бэкендов;
- вызов FFmpeg `start_hls` (dry run).

**Запуск** (из корня проекта, с виртуальным окружением):

```bash
.venv/bin/python tests/test_stream_backends.py
```

Или с `PYTHONPATH`:

```bash
PYTHONPATH=. .venv/bin/python tests/test_stream_backends.py
```

Тест захвата по HTTP требует доступ в интернет (https://httpbin.org/image/jpeg).
