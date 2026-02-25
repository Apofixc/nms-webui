"""Общая логика отдачи MPEG-TS по HTTP: константы и заголовки."""
from __future__ import annotations

# Размер чтения из pipe процесса (KB): маленький = быстрый первый чанк для клиента
PIPE_READ_KB = 64

# Рекомендуемые заголовки для HTTP-TS streaming response
HTTP_TS_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}

MEDIA_TYPE_MPEGTS = "video/mp2t"
