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
    Конфигурация (протоколы, типы выхода) берется динамически из манифеста.
    """

    def __init__(self, settings: dict, manifest: dict):
        self._settings = settings
        self._manifest = manifest
        self._streamer = VLCStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "vlc"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING, BackendCapability.PREVIEW}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        """Динамическое определение поддерживаемых протоколов из манифеста."""
        formats = self._manifest.get("formats", {})
        protos = formats.get("input_protocols", [])
        result = set()
        for p in protos:
            try:
                result.add(StreamProtocol(p.lower()))
            except ValueError:
                logger.warning(f"VLC: Неизвестный протокол в манифесте: {p}")
        
        # Если в манифесте пусто, возвращаем базовый набор (fallback)
        if not result:
            return {
                StreamProtocol.HTTP, StreamProtocol.UDP, StreamProtocol.RTP,
                StreamProtocol.RTSP, StreamProtocol.RTMP, StreamProtocol.HLS
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
                logger.warning(f"VLC: Неизвестный тип выхода в манифесте: {t}")
        
        if not result:
            return {OutputType.HTTP, OutputType.HTTP_TS, OutputType.HLS}
        return result

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        """Динамическое определение форматов превью из манифеста."""
        formats = self._manifest.get("formats", {})
        fmts = formats.get("preview_formats", [])
        result = set()
        for f in fmts:
            try:
                result.add(PreviewFormat(f.lower()))
            except ValueError:
                logger.warning(f"VLC: Неизвестный формат превью в манифесте: {f}")
        
        if not result:
            return {PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.TIFF}
        return result

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

    async def get_dynamic_cost(self, protocol: StreamProtocol) -> float:
        """VLC 'дороже' прокси, так как запускает отдельный процесс cvlc."""
        count = self._streamer.get_active_count()
        # Базовая стоимость 5.0 + 2.0 за каждый активный процесс
        return 5.0 + (count * 2.0)


def create_backend(settings: Any, manifest: Optional[dict] = None) -> IStreamBackend:
    """Фабрика создания бэкенда VLC.
    
    Принимает манифест от загрузчика для динамической конфигурации.
    """
    if hasattr(settings, "manifest") and manifest is None:
        # Если передан ModuleContext
        actual_manifest = settings.manifest
        actual_settings = settings.manifest.get("config", {})
    else:
        actual_manifest = manifest or {}
        actual_settings = settings if isinstance(settings, dict) else {}
        
    return VLCBackend(settings=actual_settings, manifest=actual_manifest)
