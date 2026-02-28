# Субмодуль Pure Preview — нативная генерация превью без внешних бинарников
from typing import Optional, Set
from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)


class PurePreviewBackend(IStreamBackend):
    """Нативный Python-бэкенд для генерации превью.

    Легковесная альтернатива FFmpeg/GStreamer для получения
    скриншотов из потоков. Использует I-frame (IDR) извлечение.
    """

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
        return {PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.WEBP}

    async def start_stream(self, task: StreamTask) -> StreamResult:
        # Не поддерживает стриминг
        return StreamResult(
            task_id=task.task_id or "",
            success=False,
            backend_used="pure_preview",
            error="pure_preview не поддерживает стриминг",
        )

    async def stop_stream(self, task_id: str) -> bool:
        return False

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        # TODO: реализовать парсинг MPEG-TS и декодирование I-frame
        raise NotImplementedError

    async def is_available(self) -> bool:
        # Нативный Python — всегда доступен
        return True

    async def health_check(self) -> dict:
        return {"backend": "pure_preview", "native": True}


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure Preview."""
    return PurePreviewBackend()
