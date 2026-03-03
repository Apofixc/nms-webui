# Субмодуль Builtin Engine — универсальный встроенный движок
import asyncio
import logging
from typing import Any, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import BuiltinEngineStreamer

logger = logging.getLogger(__name__)


class BuiltinEngineBackend(IStreamBackend):
    """Встроенный (Builtin) универсальный движок на базе PyAV и aiortc.

    Работает внутри процесса Python, не требует внешних бинарных файлов.
    Поддерживает широкий спектр входных протоколов и WebRTC на выходе.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._streamer = BuiltinEngineStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "builtin_engine"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        """Расширенный список протоколов благодаря поддержке PyAV/FFmpeg."""
        return {
            StreamProtocol.HTTP, 
            StreamProtocol.UDP, 
            StreamProtocol.RTP, 
            StreamProtocol.RTSP, 
            StreamProtocol.RTMP,
            StreamProtocol.RTMPS,
            StreamProtocol.HLS,
            StreamProtocol.SRT
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.WEBRTC}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        return await self._streamer.stop(task_id)

    def get_session(self, task_id: str) -> Optional[Any]:
        """Возвращает активную сессию движка по ID."""
        return self._streamer.get_session(task_id)

    async def get_signaling_offer(self, task_id: str) -> Optional[dict]:
        """Получение SDP Offer для WebRTC сессии (с ожиданием готовности)."""
        session = self._streamer.get_session(task_id)
        if not session:
            return None
            
        try:
            # Ждем готовности Offer (Long Polling на стороне бэкенда)
            offer = await session.wait_for_offer(timeout=20.0)
            return offer
        except Exception as e:
            logger.error(f"BuiltinEngine: ошибка получения Offer для {task_id}: {e}")
            return None

    async def set_signaling_answer(self, task_id: str, sdp: str, sdp_type: str) -> bool:
        """Установка SDP Answer для WebRTC сессии."""
        session = self._streamer.get_session(task_id)
        if not session:
            return False
        try:
            await session.set_remote_description(sdp, sdp_type)
            return True
        except Exception as e:
            logger.error(f"BuiltinEngine: ошибка установки remote description для {task_id}: {e}")
            raise

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return None

    async def is_available(self) -> bool:
        try:
            import aiortc  # noqa: F401
            import av      # noqa: F401
            return True
        except ImportError:
            return False

    async def health_check(self) -> dict:
        available = await self.is_available()
        return {
            "backend": "builtin_engine",
            "available": available,
            "active_sessions": self._streamer.get_active_count()
        }

    async def get_dynamic_cost(self, protocol: StreamProtocol) -> float:
        """Встроенный движок (PyAV) средней тяжести."""
        count = self._streamer.get_active_count()
        # Базовая стоимость 2.0 + 3.0 за каждую WebRTC сессию (кодирование дорого)
        return 2.0 + (count * 3.0)


def create_backend(settings: Any) -> IStreamBackend:
    """Фабрика создания бэкенда Builtin Engine.
    
    Поддерживает как прямой словарь настроек, так и ModuleContext.
    """
    if hasattr(settings, "manifest"):
        # Если передан ModuleContext
        actual_settings = settings.manifest.get("config", {})
    elif isinstance(settings, dict):
        actual_settings = settings
    else:
        actual_settings = {}
        
    return BuiltinEngineBackend(settings=actual_settings)
