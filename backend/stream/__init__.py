"""Модуль скриншотов, просмотра и анализа потоков (UDP/HTTP). Без зависимости от Astra."""
from backend.stream.capture import StreamFrameCapture
from backend.stream.playback import StreamPlaybackSession
from backend.stream.ts_analyzer import TsAnalyzer
from backend.stream.udp_to_http import is_udp_url, stream_udp_to_http

__all__ = [
    "StreamFrameCapture",
    "StreamPlaybackSession",
    "TsAnalyzer",
    "is_udp_url",
    "stream_udp_to_http",
]
