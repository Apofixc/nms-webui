from __future__ import annotations

from typing import AsyncIterator


async def proxy_hls(stream_reader, chunk_size: int = 64 * 1024) -> AsyncIterator[bytes]:
    """HLS->HLS прокси: читает TS-чанки и отдаёт как есть."""
    while True:
        chunk = await stream_reader.read(chunk_size)
        if not chunk:
            break
        yield chunk
