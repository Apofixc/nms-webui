# Субмодуль TSDuck — реализация контракта IStreamBackend
import asyncio
import logging
import shutil
from typing import Any, Optional, Set

from backend.modules.stream.core.interfaces import (
    IStreamBackend,
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import TSDuckStreamer

logger = logging.getLogger(__name__)


class TSDuckBackend(IStreamBackend):
    """Бэкенд на базе TSDuck (tsp).

    Специализированный процессор MPEG Transport Streams.
    Поддерживает стриминг через UDP, RTP, RIST, SRT, HTTP, HLS.
    Не поддерживает транскодинг и генерацию превью.
    """

    def __init__(self, settings: dict, manifest: dict):
        self._settings = settings
        self._manifest = manifest
        self._streamer = TSDuckStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "tsduck"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        """Динамическое определение поддерживаемых протоколов из манифеста."""
        formats = self._manifest.get("formats", {})
        protos = formats.get("input_protocols", [])
        result = set()
        for p in protos:
            try:
                result.add(StreamProtocol(p.lower()))
            except ValueError:
                logger.warning(f"TSDuck: Неизвестный протокол в манифесте: {p}")

        if not result:
            return {
                StreamProtocol.UDP, StreamProtocol.RTP,
                StreamProtocol.RIST, StreamProtocol.SRT,
                StreamProtocol.HTTP, StreamProtocol.HLS,
            }
        return result

    def supported_output_types(self) -> Set[OutputType]:
        """Динамическое определение типов выхода из манифеста."""
        formats = self._manifest.get("formats", {})
        types = formats.get("output_types", [])
        result = set()
        for t in types:
            try:
                result.add(OutputType(t.lower()))
            except ValueError:
                logger.warning(f"TSDuck: Неизвестный тип выхода в манифесте: {t}")

        if not result:
            return {OutputType.HTTP, OutputType.HTTP_TS}
        return result

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        """TSDuck не поддерживает генерацию превью."""
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск трансляции."""
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка трансляции."""
        return await self._streamer.stop(task_id)

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        """Возвращает процесс tsp для мониторинга."""
        return self._streamer.get_process(task_id)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Возвращает информацию для proxy_queue."""
        return self._streamer.get_playback_info(task_id)

    def get_temp_dirs(self, task_id: str) -> list[str]:
        """Возвращает временные директории сессии."""
        session = self._streamer.get_session(task_id)
        if session:
            return session.get_temp_dirs()
        return []

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        """TSDuck не поддерживает генерацию превью."""
        return None

    async def is_available(self) -> bool:
        """Проверка наличия бинарного файла tsp."""
        tsp_path = self._settings.get("binary_path", "tsp")
        return shutil.which(tsp_path) is not None

    async def health_check(self) -> dict:
        """Статус бэкенда для системы мониторинга."""
        return {
            "backend": "tsduck",
            "available": await self.is_available(),
            "active_processes": self._streamer.get_active_count(),
            "binary": self._settings.get("binary_path", "tsp"),
        }

    async def set_signaling_answer(
        self, task_id: str, sdp: str, sdp_type: str
    ) -> bool:
        """TSDuck не поддерживает WebRTC."""
        return False

    async def get_dynamic_cost(self, protocol: StreamProtocol) -> float:
        """TSDuck оптимален для TS-протоколов, стоимость ниже FFmpeg."""
        count = self._streamer.get_active_count()
        # Базовая стоимость 2.0 (ниже FFmpeg=4.0) + 1.5 за процесс
        return 2.0 + (count * 1.5)


def create_backend(
    settings: Any, manifest: Optional[dict] = None
) -> IStreamBackend:
    """Фабрика создания бэкенда TSDuck.

    Принимает манифест от загрузчика для динамической конфигурации.
    """
    if hasattr(settings, "manifest") and manifest is None:
        # Если передан ModuleContext
        actual_manifest = settings.manifest
        actual_settings = settings.manifest.get("config", {})
    else:
        actual_manifest = manifest or {}
        actual_settings = settings if isinstance(settings, dict) else {}

    return TSDuckBackend(settings=actual_settings, manifest=actual_manifest)
