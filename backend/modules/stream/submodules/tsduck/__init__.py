# Субмодуль TSDuck — точка входа
import asyncio
import logging
import shutil
from typing import Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import TSDuckStreamer

logger = logging.getLogger(__name__)


class TSDuckBackend(IStreamBackend):
    """Бэкенд TSDuck.

    Все настройки передаются через словарь settings.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._binary_path = settings.get("binary_path", "tsp")
        self._streamer = TSDuckStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "tsduck"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.HLS, StreamProtocol.UDP,
            StreamProtocol.RTP, StreamProtocol.SRT
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {
            OutputType.HTTP, OutputType.HTTP_TS, OutputType.HLS
        }

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
        return bool(shutil.which(self._binary_path))

    async def health_check(self) -> dict:
        available = await self.is_available()
        hc = {
            "backend": "tsduck",
            "path": self._binary_path,
            "available": available,
            "active_streams": self._streamer.get_active_count()
        }

        if available:
            try:
                proc = await asyncio.create_subprocess_exec(
                    self._binary_path, "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
                hc["version"] = stdout.decode(errors="replace").split("\n")[0].strip()
            except Exception:
                pass
        return hc


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда TSDuck."""
    return TSDuckBackend(settings=settings)
