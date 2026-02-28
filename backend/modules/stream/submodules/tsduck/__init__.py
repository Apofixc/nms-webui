# Субмодуль TSDuck — стриминг по сетевым протоколам (IP/TS)
from typing import Optional, Set
from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)


class TSDuckBackend(IStreamBackend):
    """Бэкенд на основе TSDuck (tsp).

    Специализация: работа с Transport Stream по сетевым протоколам.
    """

    def __init__(self, tsp_path: str = "tsp") -> None:
        self._tsp_path = tsp_path

    @property
    def backend_id(self) -> str:
        return "tsduck"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        return {BackendCapability.STREAMING}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {StreamProtocol.UDP, StreamProtocol.RTP, StreamProtocol.HTTP}

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        # TODO: tsp -I ip ... -O ip ...
        raise NotImplementedError

    async def stop_stream(self, task_id: str) -> bool:
        raise NotImplementedError

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        return None

    async def is_available(self) -> bool:
        raise NotImplementedError

    async def health_check(self) -> dict:
        return {"backend": "tsduck", "path": self._tsp_path}


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда TSDuck."""
    path = settings.get("tsduck_path", "tsp")
    return TSDuckBackend(tsp_path=path)
