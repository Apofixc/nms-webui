# Субмодуль Pure WebRTC — точка входа
import asyncio
import logging
from typing import Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import PureWebRTCStreamer

logger = logging.getLogger(__name__)


class PureWebRTCBackend(IStreamBackend):
    """Нативный бэкенд WebRTC."""

    def __init__(self, settings: dict):
        self._settings = settings
        self._streamer = PureWebRTCStreamer()

    @property
    def backend_id(self) -> str:
        return "pure_webrtc"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.UDP, StreamProtocol.RTP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.WEBRTC}

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
            import aiortc  # noqa: F401
            return True
        except ImportError:
            return False

    async def health_check(self) -> dict:
        available = await self.is_available()
        return {
            "backend": "pure_webrtc",
            "available": available,
            "active_sessions": self._streamer.get_active_count()
        }


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure WebRTC."""
    return PureWebRTCBackend(settings=settings)
