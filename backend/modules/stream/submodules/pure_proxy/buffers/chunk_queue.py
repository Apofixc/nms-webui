from __future__ import annotations

import asyncio
from typing import Optional


class ChunkQueue:
    """Асинхронная очередь чанков для проксирования."""

    def __init__(self, max_chunks: int = 256):
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(max_chunks)

    async def push(self, chunk: bytes) -> None:
        await self._queue.put(chunk)

    async def read(self, timeout: Optional[float] = None) -> Optional[bytes]:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
