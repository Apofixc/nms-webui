# Субмодуль Pure Proxy — точка входа
import asyncio
import logging
from typing import Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import PureProxyStreamer

logger = logging.getLogger(__name__)


class PureProxyBackend(IStreamBackend):
    """Нативный бэкенд проксирования.

    Все настройки передаются через словарь settings.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._streamer = PureProxyStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "pure_proxy"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.PROXY}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.HLS, StreamProtocol.UDP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HLS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        return await self._streamer.stop(task_id)

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return None

    async def is_available(self) -> bool:
        try:
            import aiohttp  # noqa: F401
            return True
        except ImportError:
            return False

    async def health_check(self) -> dict:
        available = await self.is_available()
        return {
            "backend": "pure_proxy",
            "available": available,
            "active_proxies": self._streamer.get_active_count() if available else 0
        }


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure Proxy."""
    return PureProxyBackend(settings=settings)
