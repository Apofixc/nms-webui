# Субмодуль VLC — резервный бэкенд (стриминг, превью)
from typing import Optional, Set
from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)


class VLCBackend(IStreamBackend):
    """Бэкенд на основе VLC (cvlc). Резервный вариант."""

    def __init__(self, vlc_path: str = "cvlc") -> None:
        self._vlc_path = vlc_path

    @property
    def backend_id(self) -> str:
        return "vlc"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING, BackendCapability.PREVIEW}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.HLS,
            StreamProtocol.UDP, StreamProtocol.RTP, StreamProtocol.RTSP,
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS, OutputType.HLS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return {PreviewFormat.JPEG, PreviewFormat.PNG}

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
        return {"backend": "vlc", "path": self._vlc_path}


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда VLC."""
    path = settings.get("vlc_path", "cvlc")
    return VLCBackend(vlc_path=path)
