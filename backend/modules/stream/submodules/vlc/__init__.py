# Субмодуль VLC — полная реализация контракта IStreamBackend
import asyncio
import logging
import shutil
from typing import Any, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import VLCStreamer

logger = logging.getLogger(__name__)


class VLCBackend(IStreamBackend):
    """Бэкенд на базе VLC (cvlc).
    
    Полностью реализует контракт IStreamBackend для интеграции с ядром системы.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._streamer = VLCStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "vlc"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING, BackendCapability.PREVIEW}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP,
            StreamProtocol.UDP,
            StreamProtocol.RTP,
            StreamProtocol.RTSP,
            StreamProtocol.RTMP,
            StreamProtocol.RTMPS,
            StreamProtocol.SRT,
            StreamProtocol.HLS,
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS, OutputType.HLS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {PreviewFormat.JPEG, PreviewFormat.PNG}

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск трансляции."""
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка трансляции."""
        return await self._streamer.stop(task_id)

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        """Возвращает процесс для мониторинга."""
        return self._streamer.get_process(task_id)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """КРИТИЧНО: Возвращает сессию для механизма proxy_buffer в api.py."""
        return self._streamer.get_playback_info(task_id)

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        """Генерация скриншота."""
        return await self._streamer.generate_preview(url, protocol, fmt, width, quality)

    async def is_available(self) -> bool:
        """Проверка наличия бинарного файла VLC."""
        vlc_path = self._settings.get("binary_path", "cvlc")
        return shutil.which(vlc_path) is not None

    async def health_check(self) -> dict:
        """Статус бэкенда для системы мониторинга."""
        return {
            "backend": "vlc",
            "available": await self.is_available(),
            "active_processes": self._streamer.get_active_count(),
            "binary": self._settings.get("binary_path", "cvlc")
        }

    async def set_signaling_answer(self, task_id: str, sdp: str, sdp_type: str) -> bool:
        """VLC не поддерживает WebRTC, возвращаем False."""
        return False


def create_backend(settings: Any) -> IStreamBackend:
    """Фабрика создания бэкенда VLC.
    
    Поддерживает как прямой словарь настроек, так и ModuleContext.
    """
    if hasattr(settings, "manifest"):
        # Если передан ModuleContext
        actual_settings = settings.manifest.get("config", {})
    elif isinstance(settings, dict):
        actual_settings = settings
    else:
        actual_settings = {}
        
    return VLCBackend(settings=actual_settings)
