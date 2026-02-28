# Субмодуль Pure Proxy — нативное проксирование HTTP/HLS и конвертация UDP-to-HTTP
from typing import Optional, Set
from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)


class PureProxyBackend(IStreamBackend):
    """Нативный Python-бэкенд для проксирования потоков.

    Возможности:
    - HTTP Bypass: прямая передача HTTP потока в mpegts.js
    - HLS Bypass: прямая передача HLS потока в hls.js
    - UDP-to-HTTP: конвертация мультикаст/юникаст в HTTP
    """

    @property
    def backend_id(self) -> str:
        return "pure_proxy"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.PROXY, BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.HTTP, StreamProtocol.HLS, StreamProtocol.UDP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HLS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        # TODO: запуск прокси-сервера (aiohttp или raw asyncio)
        raise NotImplementedError

    async def stop_stream(self, task_id: str) -> bool:
        raise NotImplementedError

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return None

    async def is_available(self) -> bool:
        # Нативный Python — всегда доступен
        return True

    async def health_check(self) -> dict:
        return {"backend": "pure_proxy", "native": True}


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Pure Proxy."""
    return PureProxyBackend()
