"""Типы данных модуля stream (Pydantic)."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# Строгая типизация для реестра и настроек WebUI
InputFormat = Literal["udp", "http", "rtp", "file", "rtsp", "srt", "hls", "tcp"]
OutputFormat = Literal["http_ts", "http_hls", "webrtc"]
BackendName = Literal[
    "ffmpeg", "vlc", "astra", "gstreamer", "tsduck", "udp_proxy", "webrtc"
]


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
