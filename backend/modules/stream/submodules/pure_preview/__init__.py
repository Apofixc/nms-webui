# Субмодуль Pure Preview — точка входа
import asyncio
import logging
from typing import Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .preview import PurePreviewer

logger = logging.getLogger(__name__)


class PurePreviewBackend(IStreamBackend):
    """Нативный бэкенд превью.

    Все настройки передаются через словарь settings.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._previewer = PurePreviewer(settings)

    @property
    def backend_id(self) -> str:
        return "pure_preview"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.PREVIEW}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.HLS, StreamProtocol.UDP}

    def supported_output_types(self) -> Set[OutputType]:
        return set()

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {
            PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.WEBP
        }

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return StreamResult(
            task_id=task.task_id or "", success=False,
            backend_used="pure_preview", error="Streaming not supported"
        )

    async def stop_stream(self, task_id: str) -> bool:
        return False

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return await self._previewer.generate(url, protocol, fmt, width, quality)

    async def is_available(self) -> bool:
        try:
            from PIL import Image  # noqa: F401
            import aiohttp  # noqa: F401
            return True
        except ImportError:
            return False

    async def health_check(self) -> dict:
        available = await self.is_available()
        return {
            "backend": "pure_preview",
            "available": available,
            "dependencies_installed": available
        }


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure Preview."""
    return PurePreviewBackend(settings=settings)
