# Субмодуль Pure WebRTC — нативная реализация низкозадержкового стриминга
from typing import Optional, Set
from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)


class PureWebRTCBackend(IStreamBackend):
    """Нативный Python-бэкенд для WebRTC стриминга.

    Использует aiortc для организации peer connection,
    SDP обмена и передачи медиа-треков.
    """

    @property
    def backend_id(self) -> str:
        return "pure_webrtc"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.UDP, StreamProtocol.RTP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.WEBRTC}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        # TODO: создание RTCPeerConnection, SDP offer/answer
        raise NotImplementedError

    async def stop_stream(self, task_id: str) -> bool:
        raise NotImplementedError

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return None

    async def is_available(self) -> bool:
        # TODO: проверить наличие aiortc
        raise NotImplementedError

    async def health_check(self) -> dict:
        return {"backend": "pure_webrtc", "native": True}


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure WebRTC."""
    return PureWebRTCBackend()
