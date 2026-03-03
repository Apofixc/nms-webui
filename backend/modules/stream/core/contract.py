# Контракт (абстрактный интерфейс) для всех стрим-бэкендов
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional, Set

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
    builtin_proxy, builtin_engine, builtin_preview) обязан реализовать
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

    async def get_dynamic_cost(self, protocol: StreamProtocol) -> float:
        """Возвращает динамическую стоимость использования бэкенда для протокола.
        
        Чем ниже значение, тем предпочтительнее бэкенд.
        Дефолтная реализация возвращает 0 (нейтрально).
        """
        return 0.0

    # --- Расширенный контракт (опциональные методы с дефолтной реализацией) ---

    def get_session(self, task_id: str) -> Optional[Any]:
        """Получение активной сессии по ID (для бэкендов с сессиями).

        Бэкенды, управляющие сессиями (proxy, engine), переопределяют
        этот метод. Остальные возвращают None.
        """
        return None

    def get_process(self, task_id: str) -> Optional[asyncio.subprocess.Process]:
        """Получение процесса для потока (для внешних бэкендов).

        Бэкенды, запускающие внешние процессы (ffmpeg, vlc),
        переопределяют этот метод. Остальные возвращают None.
        """
        return None

    def get_playback_info(self, task_id: str) -> Optional[dict]:
        """Информация о воспроизведении для клиента.

        Бэкенд сам определяет, как отдавать поток, возвращая словарь:
        {
            "type": "redirect" | "proxy_queue" | "proxy_buffer" | "process_stdout" | "file_stream",
            "content_type": "video/mp2t" | "application/vnd.apple.mpegurl" | ...,
            "url": "...",           # для redirect
            "subscribe": callable,  # для proxy_queue
            "unsubscribe": callable,
            "buffer_dir": "...",    # для proxy_buffer
            "segments": [...],
            "segment_duration": int,
            ...
        }
        Возвращает None, если бэкенд не предоставляет воспроизведение.
        """
        return None

    async def get_signaling_offer(self, task_id: str) -> Optional[dict]:
        """Получение SDP Offer для WebRTC сессии.

        Возвращает {"sdp": "...", "type": "offer"} или None
        для бэкендов без поддержки WebRTC.
        """
        return None

    async def set_signaling_answer(self, task_id: str, sdp: str, sdp_type: str) -> bool:
        """Установка SDP Answer для WebRTC сессии.

        Возвращает True при успехе, False для бэкендов без WebRTC.
        """
        return False
