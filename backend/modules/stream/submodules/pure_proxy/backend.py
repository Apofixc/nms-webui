# Нативная логика проксирования (HTTP/HLS/UDP)
import asyncio
import logging
from typing import Optional, Dict

from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType
)

logger = logging.getLogger(__name__)


class PureProxyStreamer:
    """Нативный прокси на базе aiohttp и asyncio.

    Все параметры (буферы, таймауты) берутся из settings.
    """

    def __init__(self, settings: dict):
        self.buffer_size = settings.get("buffer_size", 65536)
        self.connect_timeout = settings.get("connect_timeout", 15)
        self.read_timeout = settings.get("read_timeout", 30)
        self.max_redirects = settings.get("max_redirects", 5)
        self.udp_recv_buffer = settings.get("udp_recv_buffer", 65536)
        self._active_proxies: Dict[str, asyncio.Task] = {}

    async def start(self, task: StreamTask) -> StreamResult:
        task_id = task.task_id or ""

        # Для проксирования: подтверждаем готовность, данные перекачиваются при HTTP-запросе
        return StreamResult(
            task_id=task_id,
            success=True,
            backend_used="pure_proxy",
            output_url=f"/api/modules/stream/v1/proxy/{task_id}",
            metadata={
                "type": "native_proxy",
                "buffer_size": self.buffer_size,
                "connect_timeout": self.connect_timeout,
            }
        )

    async def stop(self, task_id: str) -> bool:
        proxy_task = self._active_proxies.pop(task_id, None)
        if proxy_task:
            proxy_task.cancel()
            return True
        return False

    def get_active_count(self) -> int:
        return len(self._active_proxies)
