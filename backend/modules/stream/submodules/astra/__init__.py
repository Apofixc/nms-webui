# Субмодуль Cesbo Astra — точка входа
import asyncio
import logging
import os
from typing import Any, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .backend import AstraStreamer

logger = logging.getLogger(__name__)


class AstraBackend(IStreamBackend):
    """Реализация IStreamBackend для Cesbo Astra 4.4 (free).

    Принимает UDP/RTP/HTTP на входе,
    отдаёт HTTP (MPEG-TS) на выходе через проксирование.
    """

    def __init__(self, settings: dict, manifest: dict):
        self._settings = settings
        self._manifest = manifest
        self._streamer = AstraStreamer(settings)

    # ── Идентификация ───────────────────────────────────────────────────

    @property
    def backend_id(self) -> str:
        return "astra"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING, BackendCapability.CONVERSION}

    # ── Протоколы и форматы (берём из манифеста) ────────────────────────

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        """Из манифеста: http, udp, rtp."""
        formats = self._manifest.get("formats", {})
        protos = formats.get("input_protocols", [])
        result = set()
        for p in protos:
            try:
                result.add(StreamProtocol(p.lower()))
            except ValueError:
                logger.warning(f"Astra: неизвестный протокол «{p}»")
        return result or {StreamProtocol.UDP, StreamProtocol.RTP, StreamProtocol.HTTP}

    def supported_output_types(self) -> Set[OutputType]:
        """Из манифеста: http."""
        formats = self._manifest.get("formats", {})
        types = formats.get("output_types", [])
        result = set()
        for t in types:
            try:
                result.add(OutputType(t.lower()))
            except ValueError:
                logger.warning(f"Astra: неизвестный тип выхода «{t}»")
        return result or {OutputType.HTTP}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        """Astra free не умеет делать скриншоты."""
        return set()

    def get_output_priorities(self, protocol: StreamProtocol) -> list[OutputType]:
        """Для любого входа приоритет — HTTP."""
        return [OutputType.HTTP]

    # ── Стриминг ────────────────────────────────────────────────────────

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return await self._streamer.start(task)

    async def stop_stream(self, task_id: str) -> bool:
        return await self._streamer.stop(task_id)

    # ── Сессия и воспроизведение ────────────────────────────────────────

    def get_session(self, task_id: str) -> Optional[Any]:
        return self._streamer.get_session(task_id)

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        return self._streamer.get_process(task_id)

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Создаёт индивидуальную очередь для каждого клиента.

        API вызывает _serve_proxy_queue для раздачи чанков.
        """
        session = self._streamer.get_session(task_id)
        if not session:
            return None

        q = session.subscribe()
        return {
            "type": "proxy_queue",
            "content_type": "video/mp2t",
            "queue": q,
            "unsubscribe": lambda: session.unsubscribe(q),
        }

    # ── Превью (не поддерживается) ──────────────────────────────────────

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return None

    # ── Здоровье и доступность ──────────────────────────────────────────

    async def is_available(self) -> bool:
        """Проверяет наличие бинарника Astra на диске."""
        return os.path.isfile(self._streamer.binary_path)

    async def health_check(self) -> dict:
        available = await self.is_available()
        return {
            "backend": "astra",
            "available": available,
            "binary": self._streamer.binary_path,
            "active_streams": self._streamer.get_active_count(),
        }

    async def get_dynamic_cost(self, protocol: StreamProtocol) -> float:
        """Astra тяжелее чистого прокси, но легче VLC/FFmpeg."""
        count = self._streamer.get_active_count()
        return 1.0 + (count * 0.2)


# ── Фабрика (вызывается загрузчиком) ────────────────────────────────────

def create_backend(settings: Any, manifest: Optional[dict] = None) -> IStreamBackend:
    """Точка входа для системного загрузчика субмодулей."""
    if hasattr(settings, "manifest") and manifest is None:
        actual_manifest = settings.manifest
        actual_settings = settings.manifest.get("config", {})
    else:
        actual_manifest = manifest or {}
        actual_settings = settings if isinstance(settings, dict) else {}

    return AstraBackend(settings=actual_settings, manifest=actual_manifest)
