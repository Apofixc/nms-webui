# Субмодуль Builtin Proxy — точка входа
import asyncio
import logging
import os
from typing import Any, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import BuiltinProxyStreamer

logger = logging.getLogger(__name__)


class BuiltinProxyBackend(IStreamBackend):
    """Встроенный бэкенд проксирования.

    Прокси-бэкенд пробрасывает входной поток (HTTP/HLS/UDP)
    через внутренний API-эндпоинт без транскодирования.
    Фактическая перекачка данных происходит при HTTP-запросе клиента.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._streamer = BuiltinProxyStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "builtin_proxy"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        # STREAMING — чтобы роутер мог выбрать для стриминга
        # PROXY — маркер нативного проксирования
        return {BackendCapability.STREAMING, BackendCapability.PROXY}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.HLS, StreamProtocol.UDP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS, OutputType.HLS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    def get_output_priorities(self, protocol: StreamProtocol) -> list[OutputType]:
        """Приоритеты вывода зависят от протокола источника."""
        if protocol == StreamProtocol.UDP:
            # UDP лучше отдавать как HTTP_TS или HLS
            return [OutputType.HTTP_TS, OutputType.HLS, OutputType.HTTP]
        # HTTP/HLS — прямой проброс (HTTP) или HLS предпочтительнее
        return [OutputType.HTTP, OutputType.HLS, OutputType.HTTP_TS]

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        return await self._streamer.stop(task_id)

    def get_session(self, task_id: str) -> Optional[Any]:
        """Возвращает активную ProxySession по ID."""
        return self._streamer.get_session(task_id)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Информация о воспроизведении для клиента.

        Бэкенд сам определяет формат ответа на основе типа вывода сессии.
        """
        session = self._streamer.get_session(task_id)
        if not session:
            return None

        output_type = session.task.output_type

        # HLS — отдаём как плейлист с сегментами
        if output_type == OutputType.HLS:
            return {
                "type": "hls_playlist",
                "content_type": "application/vnd.apple.mpegurl",
                "segments": list(session.segments),
                "segment_duration": session.segment_duration,
                "buffer_dir": session.buffer_dir,
                "playlist_url": f"/api/modules/stream/v1/proxy/{task_id}/index.m3u8",
            }

        # HTTP_TS — буферизированное чтение с диска
        if output_type == OutputType.HTTP_TS:
            session.enable_buffering()
            return {
                "type": "proxy_buffer",
                "content_type": "video/mp2t",
                "buffer_dir": session.buffer_dir,
                "segments": list(session.segments),
                "segment_duration": session.segment_duration,
                "get_session": lambda: self._streamer.get_session(task_id),
            }

        # HTTP — прямая передача через очередь
        q = session.subscribe()
        return {
            "type": "proxy_queue",
            "content_type": "video/mp2t",
            "queue": q,
            "unsubscribe": lambda: session.unsubscribe(q),
        }

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
            "backend": "builtin_proxy",
            "available": available,
            "active_sessions": self._streamer.get_active_count() if available else 0,
        }


def create_backend(settings: Any) -> IStreamBackend:
    """Фабрика создания бэкенда Builtin Proxy.
    
    Поддерживает как прямой словарь настроек, так и ModuleContext.
    """
    if hasattr(settings, "manifest"):
        # Если передан ModuleContext
        actual_settings = settings.manifest.get("config", {})
    elif isinstance(settings, dict):
        actual_settings = settings
    else:
        actual_settings = {}
        
    return BuiltinProxyBackend(settings=actual_settings)
