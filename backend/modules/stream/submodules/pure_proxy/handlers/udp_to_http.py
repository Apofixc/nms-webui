from __future__ import annotations

import asyncio
from typing import AsyncIterator


async def udp_to_http_stream(reader, chunk_size: int = 1316) -> AsyncIterator[bytes]:
    """UDP→HTTP: читает из reader (ожидается datagram-like интерфейс with .read), отдаёт TS чанки."""
    while True:
        try:
            chunk = await reader.read(chunk_size)
        except Exception:
            break
        if not chunk:
            break
        yield chunk
