# Контракт (абстрактный интерфейс) для всех стрим-бэкендов
from abc import ABC, abstractmethod
from typing import Optional, Set

from .types import (
    StreamTask,
    StreamResult,
    StreamProtocol,
    OutputType,
    BackendCapability,
    PreviewFormat,
)


class IStreamBackend(ABC):
    """Единый интерфейс для всех субмодулей (бэкендов) стриминга.

    Каждый бэкенд (FFmpeg, VLC, GStreamer, Astra, TSDuck,
    pure_proxy, pure_webrtc, pure_preview) обязан реализовать
    этот контракт для интеграции с ядром модуля.
    """

    @property
    @abstractmethod
    def backend_id(self) -> str:
        """Уникальный идентификатор бэкенда (например, 'ffmpeg', 'vlc')."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> Set[BackendCapability]:
        """Набор возможностей бэкенда (streaming, conversion, preview, proxy)."""
        ...

    @abstractmethod
    def supported_input_protocols(self) -> Set[StreamProtocol]:
        """Список поддерживаемых входных протоколов."""
        ...

    @abstractmethod
    def supported_output_types(self) -> Set[OutputType]:
        """Список поддерживаемых типов вывода."""
        ...

    @abstractmethod
    def supported_preview_formats(self) -> Set[PreviewFormat]:
        """Список поддерживаемых форматов превью (пустой, если превью не поддерживается)."""
        ...

    def get_output_priorities(self, protocol: StreamProtocol) -> list[OutputType]:
        """Приоритеты типов вывода для режима 'auto'."""
        return [OutputType.HTTP_TS, OutputType.HLS]

    def get_preview_priorities(self) -> list[PreviewFormat]:
        """Приоритеты форматов превью для режима 'auto'."""
        return [PreviewFormat.JPEG, PreviewFormat.PNG]

    @abstractmethod
    async def start_stream(self, task: StreamTask) -> StreamResult:
        """Запуск стриминга по заданной задаче.

        Создает процесс/соединение для трансляции потока
        с входного URL на указанный тип вывода.
        """
        ...

    @abstractmethod
    async def stop_stream(self, task_id: str) -> bool:
        """Остановка активного потока по его идентификатору."""
        ...

    @abstractmethod
    async def generate_preview(
        self,
        url: str,
        protocol: StreamProtocol,
        fmt: PreviewFormat,
        width: int = 640,
        quality: int = 75,
    ) -> Optional[bytes]:
        """Генерация превью (скриншота) из потока.

        Возвращает байты изображения или None, если превью невозможно.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Проверка доступности бэкенда (бинарник существует, сервис запущен)."""
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """Расширенная проверка здоровья бэкенда."""
        ...
