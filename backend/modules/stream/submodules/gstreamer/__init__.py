# Субмодуль GStreamer — высокопроизводительная конвертация и превью
from typing import Optional, Set
from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)


class GStreamerBackend(IStreamBackend):
    """Бэкенд на основе GStreamer (gst-launch-1.0)."""

    def __init__(self, gst_path: str = "gst-launch-1.0") -> None:
        self._gst_path = gst_path

    @property
    def backend_id(self) -> str:
        return "gstreamer"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.CONVERSION, BackendCapability.PREVIEW}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.UDP,
            StreamProtocol.RTP, StreamProtocol.RTSP,
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {PreviewFormat.JPEG, PreviewFormat.PNG, PreviewFormat.WEBP}

    async def start_stream(self, task: StreamTask) -> StreamResult:
        raise NotImplementedError

    async def stop_stream(self, task_id: str) -> bool:
        raise NotImplementedError

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        raise NotImplementedError

    async def is_available(self) -> bool:
        raise NotImplementedError

    async def health_check(self) -> dict:
        return {"backend": "gstreamer", "path": self._gst_path}


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда GStreamer."""
    path = settings.get("gstreamer_path", "gst-launch-1.0")
    return GStreamerBackend(gst_path=path)
