# Типы данных ядра модуля stream
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Priority(Enum):
    """Приоритет задачи стриминга."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class StreamProtocol(Enum):
    """Поддерживаемые сетевые протоколы на входе."""
    HTTP = "http"
    HLS = "hls"
    UDP = "udp"
    RTP = "rtp"
    RTSP = "rtsp"
    SRT = "srt"
    RTMPS = "rtmps"
    RTMP = "rtmp"


class OutputType(Enum):
    """Типы выходных медиапотоков (поддерживаемые браузером)."""
    AUTO = "auto"
    HTTP = "http"
    HTTP_TS = "http_ts"
    HLS = "hls"
    WEBRTC = "webrtc"


class PreviewFormat(Enum):
    """Форматы генерации превью."""
    AUTO = "auto"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    AVIF = "avif"
    TIFF = "tiff"
    GIF = "gif"


class BackendCapability(Enum):
    """Возможности бэкенда."""
    STREAMING = "streaming"
    CONVERSION = "conversion"
    PREVIEW = "preview"
    PROXY = "proxy"


@dataclass
class StreamTask:
    """Задача на стриминг или генерацию превью.

    Содержит всю информацию, необходимую для маршрутизации
    и выполнения задачи конкретным бэкендом.
    """
    # Источник
    input_url: str
    input_protocol: StreamProtocol

    # Вывод
    output_type: OutputType

    # Конфигурация
    priority: Priority = Priority.NORMAL
    forced_backend: Optional[str] = None          # Принудительный выбор бэкенда
    forced_preview_backend: Optional[str] = None  # Принудительный выбор бэкенда превью
    preview_format: PreviewFormat = PreviewFormat.JPEG
    preview_width: int = 640
    preview_quality: int = 75

    # Метаданные
    task_id: Optional[str] = None
    extra: dict = field(default_factory=dict)


@dataclass
class StreamResult:
    """Результат выполнения задачи стриминга."""
    task_id: str
    success: bool
    backend_used: str
    output_url: Optional[str] = None
    process: Optional[any] = None
    preview_data: Optional[bytes] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
