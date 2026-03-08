# Субмодуль Astra — точка входа
import asyncio
import logging
import os
from typing import Optional, Set, Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import AstraStreamer

logger = logging.getLogger(__name__)


class AstraBackend(IStreamBackend):
    """Бэкенд Cesbo Astra 4.4.182."""

    def __init__(self, settings: dict, manifest: Optional[dict] = None):
        self._settings = settings
        self._manifest = manifest or {}
        self._binary_path = settings.get("binary_path", "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182")
        self._http_port = settings.get("http_port", 8200)

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
            StreamProtocol.RTP
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {
            OutputType.HTTP
        }

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    def get_output_priorities(self, protocol: StreamProtocol) -> list[OutputType]:
        return [OutputType.HTTP]

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        return await self._streamer.stop(task_id)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Возвращает информацию для воспроизведения (Astra отдает HTTP)."""
        port = self._streamer.get_task_port(task_id) or self._http_port
        return {
            "type": "redirect",
            "url": f"http://127.0.0.1:{port}/{task_id}"
        }

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


def create_backend(settings: Any, manifest: Optional[dict] = None) -> IStreamBackend:
    """Фабрика создания бэкенда Astra.
    
    Поддерживает вызов как из SubmoduleLoader (dict), так и из nms.plugin.loader (ModuleContext).
    """
    if hasattr(settings, "manifest") and manifest is None:
        # Вызов из системного лоадера (context)
        actual_manifest = settings.manifest
        actual_settings = settings.manifest.get("config", {})
    else:
        # Вызов из SubmoduleLoader
        actual_manifest = manifest or {}
        actual_settings = settings if isinstance(settings, dict) else {}

    return AstraBackend(settings=actual_settings, manifest=actual_manifest)
