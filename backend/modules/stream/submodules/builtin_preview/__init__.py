# Субмодуль Builtin Preview — точка входа
import asyncio
import logging
from typing import Any, Optional, Set

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)

from .preview import BuiltinPreviewer

logger = logging.getLogger(__name__)


class BuiltinPreviewBackend(IStreamBackend):
    """Встроенный бэкенд превью на базе PyAV и Pillow.

    Все настройки передаются через словарь settings.
    """

    def __init__(self, settings: dict):
        self._settings = settings
        self._previewer = BuiltinPreviewer(settings)
        self._active_tasks = 0

    @property
    def backend_id(self) -> str:
        return "builtin_preview"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.PREVIEW}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.HLS, 
            StreamProtocol.UDP, StreamProtocol.RTSP, StreamProtocol.RTP
        }

    def supported_output_types(self) -> Set[OutputType]:
        return set()

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {
            PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.WEBP,
            PreviewFormat.AVIF, PreviewFormat.TIFF, PreviewFormat.GIF
        }

    async def start_stream(self, task: StreamTask) -> StreamResult:
        return StreamResult(
            task_id=task.task_id or "", success=False,
            backend_used="builtin_preview", error="Streaming not supported"
        )

    async def stop_stream(self, task_id: str) -> bool:
        return False

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        self._active_tasks += 1
        try:
            return await self._previewer.generate(url, protocol, fmt, width, quality)
        finally:
            self._active_tasks -= 1

    async def is_available(self) -> bool:
        try:
            from PIL import Image  # noqa: F401
            import av  # noqa: F401
            return True
        except ImportError as e:
            logger.error(f"Бэкенд builtin_preview недоступен: отсутствует библиотека ({e})")
            return False
        except Exception as e:
            logger.error(f"Бэкенд builtin_preview недоступен: ошибка инициализации ({e})")
            return False

    async def health_check(self) -> dict:
        available = await self.is_available()
        return {
            "backend": "builtin_preview",
            "available": available,
            "dependencies_installed": available
        }

    async def get_dynamic_cost(self, protocol: StreamProtocol) -> float:
        # Базовая цена 1.0 + 0.5 за каждую активную генерацию
        return 1.0 + (self._active_tasks * 0.5)


def create_backend(settings: Any) -> IStreamBackend:
    """Фабрика создания бэкенда Builtin Preview.
    
    Поддерживает как прямой словарь настроек, так и ModuleContext.
    """
    if hasattr(settings, "manifest"):
        # Если передан ModuleContext
        actual_settings = settings.manifest.get("config", {})
    elif isinstance(settings, dict):
        actual_settings = settings
    else:
        actual_settings = {}
        
    return BuiltinPreviewBackend(settings=actual_settings)
