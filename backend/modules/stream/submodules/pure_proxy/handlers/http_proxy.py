from __future__ import annotations

from typing import AsyncIterator


async def proxy_http(stream_reader, chunk_size: int = 64 * 1024) -> AsyncIterator[bytes]:
    """Простой http->http прокси: читает из reader, отдаёт чанками.

    Ожидается, что stream_reader поддерживает .read(chunk_size).
    """

    while True:
        chunk = await stream_reader.read(chunk_size)
        if not chunk:
            break
        yield chunk
