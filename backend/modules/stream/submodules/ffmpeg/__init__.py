# Субмодуль FFmpeg — точка входа (Фабрика)
import asyncio
import logging
import os
import shutil
from typing import Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import FFmpegStreamer
from .preview import FFmpegPreviewer

logger = logging.getLogger(__name__)


class FFmpegBackend(IStreamBackend):
    """Комбинированный бэкенд FFmpeg.

    Все настройки (базовые параметры, override-шаблоны) передаются
    из манифеста через словарь settings.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._binary_path = settings.get("binary_path", "ffmpeg")

        # Стример и превьюер получают единый словарь настроек
        self._streamer = FFmpegStreamer(settings)
        self._previewer = FFmpegPreviewer(settings)

    @property
    def backend_id(self) -> str:
        return "ffmpeg"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {
            BackendCapability.STREAMING,
            BackendCapability.CONVERSION,
            BackendCapability.PREVIEW
        }

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.HLS, StreamProtocol.UDP,
            StreamProtocol.RTP, StreamProtocol.RTSP, StreamProtocol.RTMP,
            StreamProtocol.RTMPS, StreamProtocol.SRT
        }

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {
            PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.WEBP,
            PreviewFormat.AVIF, PreviewFormat.TIFF, PreviewFormat.GIF
        }

    def get_output_priorities(self, protocol: StreamProtocol) -> list[OutputType]:
        if protocol == StreamProtocol.HLS:
            return [OutputType.HLS, OutputType.HTTP_TS]
        return [OutputType.HTTP_TS, OutputType.HLS, OutputType.WEBRTC]

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        return await self._streamer.stop(task_id)

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return await self._previewer.generate(url, protocol, fmt, width, quality)

    async def is_available(self) -> bool:
        if shutil.which(self._binary_path):
            return True
        return os.path.isfile(self._binary_path) and os.access(self._binary_path, os.X_OK)

    async def health_check(self) -> dict:
        available = await self.is_available()
        hc = {
            "backend": "ffmpeg",
            "path": self._binary_path,
            "available": available,
            "active_streams": self._streamer.get_active_count()
        }

        if available:
            try:
                proc = await asyncio.create_subprocess_exec(
                    self._binary_path, "-version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
                hc["version"] = stdout.decode(errors="replace").split("\n")[0].strip()
            except Exception:
                pass
        return hc


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда FFmpeg."""
    return FFmpegBackend(settings=settings)
