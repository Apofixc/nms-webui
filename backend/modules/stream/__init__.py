"""Модуль скриншотов и просмотра потоков (UDP/HTTP). Публичный API."""
from backend.modules.stream.capture import StreamFrameCapture
from backend.modules.stream.playback import StreamPlaybackSession, get_input_format
from backend.modules.stream.backends.udp_to_http import is_udp_url, stream_udp_to_http
from backend.modules.stream.core.registry import (
    STREAM_BACKENDS_BY_NAME,
    get_available_stream_backends,
    get_backend_for_link,
    get_stream_links,
    get_stream_backend_chain,
)

__all__ = [
    "StreamFrameCapture",
    "StreamPlaybackSession",
    "get_input_format",
    "is_udp_url",
    "stream_udp_to_http",
    "STREAM_BACKENDS_BY_NAME",
    "get_available_stream_backends",
    "get_backend_for_link",
    "get_stream_links",
    "get_stream_backend_chain",
]
