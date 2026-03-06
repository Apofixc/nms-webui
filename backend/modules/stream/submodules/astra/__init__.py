# Субмодуль Astra — точка входа
import asyncio
import logging
import os
from typing import Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import AstraStreamer

logger = logging.getLogger(__name__)


class AstraBackend(IStreamBackend):
    """Бэкенд Cesbo Astra 4.4.182.

    Все настройки передаются из манифеста через словарь settings.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._binary_path = settings.get("binary_path", "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182")
        self._http_port = settings.get("http_port", 8100)

        # Стример получает единый словарь настроек
        self._streamer = AstraStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "astra"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING, BackendCapability.CONVERSION}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.UDP,
            StreamProtocol.RTP, StreamProtocol.SRT
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {
            OutputType.HTTP, OutputType.HTTP_TS
        }

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    def get_output_priorities(self, protocol: StreamProtocol) -> list[OutputType]:
        return [OutputType.HTTP_TS]

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
        return os.path.isfile(self._binary_path) and os.access(self._binary_path, os.X_OK)

    async def health_check(self) -> dict:
        available = await self.is_available()
        return {
            "backend": "astra",
            "path": self._binary_path,
            "available": available,
            "active_streams": self._streamer.get_active_count(),
            "http_port": self._http_port
        }


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Astra."""
    return AstraBackend(settings=settings)
