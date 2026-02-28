# Субмодуль FFmpeg — основной универсальный бэкенд (стриминг, конвертация, превью)
from typing import Optional, Set
from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)


class FFmpegBackend(IStreamBackend):
    """Бэкенд на основе FFmpeg.

    Поддерживает все типы протоколов и форматов вывода.
    Основной универсальный инструмент.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self._ffmpeg_path = ffmpeg_path

    @property
    def backend_id(self) -> str:
        return "ffmpeg"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {
            BackendCapability.STREAMING,
            BackendCapability.CONVERSION,
            BackendCapability.PREVIEW,
        }

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.HLS,
            StreamProtocol.UDP, StreamProtocol.RTP, StreamProtocol.RTSP,
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS, OutputType.HLS, OutputType.WEBRTC}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.WEBP}

    async def start_stream(self, task: StreamTask) -> StreamResult:
        # TODO: реализовать запуск ffmpeg процесса
        raise NotImplementedError

    async def stop_stream(self, task_id: str) -> bool:
        # TODO: остановка процесса
        raise NotImplementedError

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        # TODO: ffmpeg -i url -vframes 1 -f image2 ...
        raise NotImplementedError

    async def is_available(self) -> bool:
        # TODO: проверка наличия бинарника
        raise NotImplementedError

    async def health_check(self) -> dict:
        return {"backend": "ffmpeg", "path": self._ffmpeg_path}


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда FFmpeg."""
    path = settings.get("ffmpeg_path", "ffmpeg")
    return FFmpegBackend(ffmpeg_path=path)
