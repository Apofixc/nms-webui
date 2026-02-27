"""Типы данных модуля stream (Pydantic)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any, Literal, Optional

try:
    from pydantic import BaseModel, Field  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal test env
    class _DummyField:
        def __call__(self, default=None, **kwargs):
            return default

    class BaseModel:  # type: ignore
        model_config: dict[str, Any] = {}

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def Field(default=None, **kwargs):  # type: ignore
        return default

# Строгая типизация для реестра и настроек WebUI (Literal для обратной совместимости)
InputFormat = Literal["udp", "http", "rtp", "file", "rtsp", "srt", "hls", "tcp"]
OutputFormat = Literal["http_ts", "http_hls", "webrtc"]
BackendName = Literal[
    "ffmpeg", "vlc", "astra", "gstreamer", "tsduck", "udp_proxy", "webrtc"
]


class InputFormatEnum(StrEnum):
    """Входные форматы (значения как строки для совместимости)."""
    UDP = "udp"
    HTTP = "http"
    RTP = "rtp"
    FILE = "file"
    RTSP = "rtsp"
    SRT = "srt"
    HLS = "hls"
    TCP = "tcp"


class OutputFormatEnum(StrEnum):
    """Выходные форматы."""
    HTTP_TS = "http_ts"
    HTTP_HLS = "http_hls"
    WEBRTC = "webrtc"


class PriorityEnum(IntEnum):
    """Приоритет выбора бэкенда (0-100)."""

    DISABLED = 0
    LOW = 25
    MEDIUM = 50
    HIGH = 75
    CRITICAL = 100


class TranscodeProfile(BaseModel):
    """Профиль транскодирования (опционально для конвертера)."""
    model_config = {"extra": "allow"}
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    bitrate: Optional[str] = None
    resolution: Optional[str] = None


class StreamConfig(BaseModel):
    """Единая конфигурация стрима для UniversalStreamConverter."""
    model_config = {"extra": "allow"}

    source_url: str = Field(..., description="URL источника (udp/http/rtsp/...)")
    input_format: str = Field(..., description="udp, http, rtp, file, rtsp, srt, hls, tcp")
    output_format: str = Field(..., description="http_ts, http_hls, webrtc")
    backend: Optional[str] = Field(default=None, description="Имя бэкенда или auto")
    buffer_size_kb: Optional[int] = Field(default=None, ge=64, le=65536)
    timeout: Optional[float] = Field(default=None, gt=0)
    hls_time: Optional[int] = Field(default=None, ge=1, le=30)
    hls_list_size: Optional[int] = Field(default=None, ge=2, le=30)
    backend_options: Optional[dict[str, Any]] = Field(default_factory=dict)

    def get_hls_time(self) -> int:
        """hls_time с дефолтом 2."""
        if self.hls_time is not None:
            return max(1, min(30, self.hls_time))
        opts = self.backend_options or {}
        if isinstance(opts.get("hls_time"), (int, float)):
            return max(1, min(30, int(opts["hls_time"])))
        return 2

    def get_hls_list_size(self) -> int:
        """hls_list_size с дефолтом 5."""
        if self.hls_list_size is not None:
            return max(2, min(30, self.hls_list_size))
        opts = self.backend_options or {}
        if isinstance(opts.get("hls_list_size"), (int, float)):
            return max(2, min(30, int(opts["hls_list_size"])))
        return 5


class StreamLink(BaseModel):
    """Связка входного и выходного формата для выбора бэкенда."""

    input_format: str = Field(..., description="udp, http, rtp, file, rtsp, srt, hls, tcp")
    output_format: str = Field(..., description="http_ts, http_hls, webrtc")


class HLSParams(BaseModel):
    """Параметры HLS-сегментации."""

    hls_time: int = Field(default=2, ge=1, le=30, description="Длительность сегмента в секундах")
    hls_list_size: int = Field(default=5, ge=2, le=30, description="Количество сегментов в плейлисте")


def norm_hls_params_from_dict(opts: dict[str, Any]) -> tuple[int, int]:
    """Нормализовать hls_time и hls_list_size из словаря опций. Возвращает (hls_time, hls_list_size)."""
    hls_time = 2
    if isinstance(opts.get("hls_time"), (int, float)):
        hls_time = max(1, min(30, int(opts["hls_time"])))
    hls_list_size = 5
    if isinstance(opts.get("hls_list_size"), (int, float)):
        hls_list_size = max(2, min(30, int(opts["hls_list_size"])))
    return hls_time, hls_list_size


class StreamOptions(BaseModel):
    """Общие опции стриминга (для валидации; в коде по-прежнему передаётся dict)."""

    model_config = {"extra": "allow"}

    buffer_kb: Optional[int] = Field(default=None, ge=64, le=65536)


# === Новые dataclasses ядра (для pipeline/router/worker_pool) ===


@dataclass(slots=True)
class StreamTask:
    """Единый объект задачи стриминга/превью."""

    id: str
    type: str  # preview | stream | record
    source_url: str
    input_protocol: str
    output_format: str
    config: dict[str, Any] = field(default_factory=dict)
    timeout_sec: int = 30
    created_at: float = 0.0


@dataclass(slots=True)
class StreamResult:
    """Результат выполнения задачи."""

    success: bool
    output_path: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)
    backend_name: Optional[str] = None
