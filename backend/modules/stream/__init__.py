"""Модуль скриншотов и просмотра потоков (UDP/HTTP). Публичный API."""

import logging

__all__ = []


def _safe_import(name: str, target: str):
    try:
        module = __import__(name, fromlist=[target])
        return getattr(module, target)
    except ModuleNotFoundError as exc:  # опциональные зависимости (httpx и т.п.)
        logging.getLogger(__name__).debug("stream optional import failed: %s", exc)
        return None


StreamFrameCapture = _safe_import("backend.modules.stream.capture", "StreamFrameCapture")
StreamPlaybackSession = _safe_import("backend.modules.stream.playback", "StreamPlaybackSession")
get_input_format = _safe_import("backend.modules.stream.playback", "get_input_format")
is_udp_url = _safe_import("backend.modules.stream.backends.udp_to_http", "is_udp_url")
stream_udp_to_http = _safe_import("backend.modules.stream.backends.udp_to_http", "stream_udp_to_http")
registry_module = _safe_import("backend.modules.stream.core.registry", "STREAM_BACKENDS_BY_NAME")

if StreamFrameCapture:
    __all__.append("StreamFrameCapture")
if StreamPlaybackSession:
    __all__.append("StreamPlaybackSession")
if get_input_format:
    __all__.append("get_input_format")
if is_udp_url:
    __all__.append("is_udp_url")
if stream_udp_to_http:
    __all__.append("stream_udp_to_http")
if registry_module:
    from backend.modules.stream.core.registry import (
        STREAM_BACKENDS_BY_NAME,
        get_available_stream_backends,
        get_backend_for_link,
        get_stream_links,
        get_stream_backend_chain,
    )

    __all__.extend(
        [
            "STREAM_BACKENDS_BY_NAME",
            "get_available_stream_backends",
            "get_backend_for_link",
            "get_stream_links",
            "get_stream_backend_chain",
        ]
    )
