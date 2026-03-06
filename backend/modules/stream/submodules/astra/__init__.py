# Субмодуль Astra — точка входа
import asyncio
import logging
import os
import shutil
from typing import Any, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import AstraStreamer

logger = logging.getLogger(__name__)


class AstraBackend(IStreamBackend):
    """Бэкенд на базе Cesbo Astra 4.4.
    
    Реализует контракт IStreamBackend.
    Конфигурация берется из манифеста.
    """

    def __init__(self, settings: dict, manifest: dict):
        self._settings = settings
        self._manifest = manifest
        self._streamer = AstraStreamer(settings)

    @property
    def backend_id(self) -> str:
        return "astra"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING, BackendCapability.CONVERSION}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        """Определение поддерживаемых протоколов из манифеста."""
        formats = self._manifest.get("formats", {})
        protos = formats.get("input_protocols", [])
        result = set()
        for p in protos:
            try:
                result.add(StreamProtocol(p.lower()))
            except ValueError:
                logger.warning(f"Astra: Неизвестный протокол в манифесте: {p}")
        
        if not result:
            return {StreamProtocol.UDP, StreamProtocol.RTP}
        return result

    def supported_output_types(self) -> Set[OutputType]:
        """Определение типов выхода из манифеста."""
        formats = self._manifest.get("formats", {})
        types = formats.get("output_types", [])
        result = set()
        for t in types:
            try:
                result.add(OutputType(t.lower()))
            except ValueError:
                logger.warning(f"Astra: Неизвестный тип выхода в манифесте: {t}")
        
        if not result:
            return {OutputType.HTTP, OutputType.HTTP_TS}
        return result

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        """Astra 4.4 не поддерживает генерацию превью напрямую."""
        return set()

    def get_output_priorities(self, protocol: StreamProtocol) -> list[OutputType]:
        """Приоритеты для Astra: теперь HTTP_TS первый, так как он стабильнее в браузере."""
        return [OutputType.HTTP_TS, OutputType.HTTP]

    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск трансляции."""
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        """Остановка трансляции."""
        return await self._streamer.stop(task_id)

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        """Возвращает процесс для внешнего мониторинга."""
        return self._streamer.get_process(task_id)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Astra работает как внешний HTTP-сервер, поэтому playback_info не нужен (api.py использует output_url)."""
        return None

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        """Astra не генерирует превью."""
        return None

    async def is_available(self) -> bool:
        """Проверка наличия бинарного файла Astra."""
        binary = self._settings.get("binary_path", "/opt/astra/astra4.4.182")
        return os.path.exists(binary)

    async def health_check(self) -> dict:
        """Статус бэкенда для системы мониторинга."""
        return {
            "backend": "astra",
            "available": await self.is_available(),
            "active_processes": self._streamer.get_active_count(),
            "binary": self._settings.get("binary_path", "/opt/astra/astra4.4.182")
        }

    async def set_signaling_answer(self, task_id: str, sdp: str, sdp_type: str) -> bool:
        """WebRTC не поддерживается."""
        return False

    async def get_dynamic_cost(self, protocol: StreamProtocol) -> float:
        """Astra 'дороже' прокси, но 'дешевле' VLC, так как оптимизирована под это."""
        count = self._streamer.get_active_count()
        return 3.0 + (count * 1.5)


def create_backend(settings: Any, manifest: Optional[dict] = None) -> IStreamBackend:
    """Фабрика создания бэкенда Astra."""
    if hasattr(settings, "manifest") and manifest is None:
        actual_manifest = settings.manifest
        actual_settings = settings.manifest.get("config", {})
    else:
        actual_manifest = manifest or {}
        actual_settings = settings if isinstance(settings, dict) else {}
        
    return AstraBackend(settings=actual_settings, manifest=actual_manifest)
