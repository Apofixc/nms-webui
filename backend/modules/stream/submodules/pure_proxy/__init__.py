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

    Прокси-бэкенд пробрасывает входной поток (HTTP/HLS/UDP)
    через внутренний API-эндпоинт без транскодирования.
    Фактическая перекачка данных происходит при HTTP-запросе клиента.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._streamer = PureProxyStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "pure_proxy"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        # STREAMING — чтобы роутер мог выбрать для стриминга
        # PROXY — маркер нативного проксирования
        return {BackendCapability.STREAMING, BackendCapability.PROXY}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.HLS, StreamProtocol.UDP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    def get_output_priorities(self, protocol: StreamProtocol) -> list[OutputType]:
        """Приоритеты вывода зависят от протокола источника."""
        if protocol == StreamProtocol.UDP:
            # UDP лучше отдавать как HTTP_TS (MPEG-TS по HTTP)
            return [OutputType.HTTP_TS, OutputType.HTTP]
        # HTTP/HLS — прямой проброс предпочтительнее
        return [OutputType.HTTP, OutputType.HTTP_TS]

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        return await self._streamer.stop(task_id)

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        # Прокси-бэкенд не умеет делать превью
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
            "active_sessions": self._streamer.get_active_count() if available else 0,
        }


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure Proxy."""
    return PureProxyBackend(settings=settings)
