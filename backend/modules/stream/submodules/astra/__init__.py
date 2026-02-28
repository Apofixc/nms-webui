# Субмодуль Astra 4.4.182 — профессиональное вещание и конвертация (без превью)
from typing import Optional, Set
from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import (
    StreamTask, StreamResult, StreamProtocol, OutputType,
    PreviewFormat, BackendCapability,
)


class AstraBackend(IStreamBackend):
    """Бэкенд на основе Cesbo Astra 4.4.182.

    Управление через Lua-скрипты (make_channel).
    Бинарник: /opt/Cesbo-Astra-4.4.-monitor/astra4.4.182
    Не поддерживает генерацию превью.
    """

    def __init__(self, astra_path: str = "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182") -> None:
        self._astra_path = astra_path

    @property
    def backend_id(self) -> str:
        return "astra"

    @property
    def capabilities(self) -> Set[BackendCapability]:
        # Astra НЕ умеет делать превью
        return {BackendCapability.STREAMING, BackendCapability.CONVERSION}

    def supported_input_protocols(self) -> Set[StreamProtocol]:
        return {
            StreamProtocol.HTTP, StreamProtocol.UDP,
            StreamProtocol.RTP,
        }

    def supported_output_types(self) -> Set[OutputType]:
        return {OutputType.HTTP, OutputType.HTTP_TS}

    def supported_preview_formats(self) -> Set[PreviewFormat]:
        # Превью не поддерживается
        return set()

    async def start_stream(self, task: StreamTask) -> StreamResult:
        # TODO: генерация Lua-конфига и запуск astra --stream script.lua
        raise NotImplementedError

    async def stop_stream(self, task_id: str) -> bool:
        raise NotImplementedError

    async def generate_preview(
        self, url: str, protocol: StreamProtocol,
        fmt: PreviewFormat, width: int = 640, quality: int = 75,
    ) -> Optional[bytes]:
        # Astra не поддерживает превью
        return None

    async def is_available(self) -> bool:
        # TODO: проверка наличия бинарника по пути
        raise NotImplementedError

    async def health_check(self) -> dict:
        return {"backend": "astra", "path": self._astra_path}


def create_backend(settings: dict) -> IStreamBackend:
    """Фабрика создания бэкенда Astra."""
    path = settings.get("astra_path", "/opt/Cesbo-Astra-4.4.-monitor/astra4.4.182")
    return AstraBackend(astra_path=path)
