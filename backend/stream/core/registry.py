"""Реестр бэкендов стриминга: константы и выбор бэкенда по (input_format, output_format)."""
from __future__ import annotations

from typing import Any, Optional

from backend.stream.backends import (
    AstraStreamBackend,
    FFmpegStreamBackend,
    GStreamerStreamBackend,
    ProxyUdpStreamBackend,
    StreamBackend,
    TSDuckStreamBackend,
    VLCStreamBackend,
    WebRTCStreamBackend,
)

STREAM_BACKEND_ORDER = ["ffmpeg", "vlc", "astra", "gstreamer", "tsduck", "udp_proxy"]
VALID_STREAM_BACKENDS = ("auto",) + tuple(STREAM_BACKEND_ORDER)

INPUT_FORMAT_TO_BACKEND_TYPES: dict[str, set[str]] = {
    "udp": {"udp", "udp_ts"},
    "http": {"http"},
    "rtp": {"rtp"},
    "file": {"file"},
    "rtsp": {"rtsp"},
    "srt": {"srt"},
    "hls": {"hls"},
    "tcp": {"tcp"},
}

STREAM_INPUT_FORMATS = ("udp", "http", "rtp", "file", "rtsp", "srt", "hls", "tcp")
STREAM_OUTPUT_FORMATS = ("http_ts", "http_hls", "webrtc")

STREAM_BACKENDS_BY_NAME: dict[str, type[StreamBackend]] = {
    "ffmpeg": FFmpegStreamBackend,
    "vlc": VLCStreamBackend,
    "astra": AstraStreamBackend,
    "gstreamer": GStreamerStreamBackend,
    "tsduck": TSDuckStreamBackend,
    "udp_proxy": ProxyUdpStreamBackend,
    "webrtc": WebRTCStreamBackend,
}


def _backend_supports_link(
    backend_cls: type[StreamBackend],
    input_format: str,
    output_format: str,
) -> bool:
    """Check if backend supports (input_format, output_format). Uses aliases (udp <-> udp_ts)."""
    input_types = getattr(backend_cls, "input_types", set())
    output_types = getattr(backend_cls, "output_types", set())
    allowed_inputs = INPUT_FORMAT_TO_BACKEND_TYPES.get(input_format, {input_format})
    if not allowed_inputs.intersection(input_types):
        return False
    return output_format in output_types


def get_available_stream_backends(
    options: Optional[dict[str, Any]] = None,
    input_type: str = "udp_ts",
    output_type: str = "http_ts",
) -> list[str]:
    """List of stream backend names available on the system for the given input/output type."""
    result = []
    for name in STREAM_BACKEND_ORDER:
        cls = STREAM_BACKENDS_BY_NAME.get(name)
        if (
            cls
            and input_type in getattr(cls, "input_types", set())
            and output_type in getattr(cls, "output_types", set())
            and cls.available(options)
        ):
            result.append(name)
    return result


def get_available_backends_for_link(
    input_format: str,
    output_format: str,
    options: Optional[dict[str, Any]] = None,
) -> list[str]:
    """List backend names that support (input_format, output_format) and are available."""
    result = []
    for name in STREAM_BACKEND_ORDER:
        cls = STREAM_BACKENDS_BY_NAME.get(name)
        if cls and _backend_supports_link(cls, input_format, output_format) and cls.available(options):
            result.append(name)
    return result


def get_backend_for_link(
    preference: str,
    input_format: str,
    output_format: str,
    options: Optional[dict[str, Any]] = None,
) -> str:
    """
    Select backend for (input_format, output_format).
    preference: auto | backend name.
    Returns backend name. Raises ValueError on manual choice with unsupported link or auto with no backends.
    Priority order when preference is 'auto': STREAM_BACKEND_ORDER.
    """
    available = get_available_backends_for_link(input_format, output_format, options)
    if preference and preference != "auto":
        if preference not in STREAM_BACKENDS_BY_NAME:
            raise ValueError(f"Unknown backend: {preference}")
        cls = STREAM_BACKENDS_BY_NAME[preference]
        if not _backend_supports_link(cls, input_format, output_format):
            raise ValueError(
                f"Backend '{preference}' does not support input {input_format!r} -> output {output_format!r}"
            )
        if not cls.available(options):
            raise ValueError(f"Backend '{preference}' is not available (not installed or not configured)")
        return preference
    if not available:
        raise ValueError(
            f"No backend available for input {input_format!r} -> output {output_format!r}"
        )
    return available[0]


def get_best(
    preference: str,
    input_format: str,
    output_format: str,
    options: Optional[dict[str, Any]] = None,
) -> str:
    """
    Best backend for (input_format, output_format) by priority (STREAM_BACKEND_ORDER).
    preference: auto | backend name. Same semantics as get_backend_for_link.
    """
    return get_backend_for_link(preference, input_format, output_format, options)


def get_stream_links(backend_name: str | None = None) -> list[dict[str, str]]:
    """
    List supported (input_format x output_format) links for UI settings.
    backend_name: if set, only for this backend; else all.
    Returns list of {"backend": str, "input_format": str, "output_format": str}.
    """
    backends_to_consider = (
        [backend_name] if backend_name and backend_name in STREAM_BACKENDS_BY_NAME
        else STREAM_BACKEND_ORDER
    )
    result = []
    for name in backends_to_consider:
        cls = STREAM_BACKENDS_BY_NAME.get(name)
        if not cls:
            continue
        input_types = getattr(cls, "input_types", set())
        output_types = getattr(cls, "output_types", set())
        for in_fmt in STREAM_INPUT_FORMATS:
            allowed = INPUT_FORMAT_TO_BACKEND_TYPES.get(in_fmt, {in_fmt})
            if not allowed.intersection(input_types):
                continue
            for out_fmt in STREAM_OUTPUT_FORMATS:
                if out_fmt in output_types:
                    result.append({
                        "backend": name,
                        "input_format": in_fmt,
                        "output_format": out_fmt,
                    })
    return result


def get_stream_backend_chain(preference: str) -> list[str]:
    """Return list of backend names to try for the given preference (auto | ffmpeg | ...)."""
    if not preference or preference == "auto":
        return list(STREAM_BACKEND_ORDER)
    if preference in STREAM_BACKENDS_BY_NAME:
        return [preference]
    return list(STREAM_BACKEND_ORDER)


def get_playback_backends_by_output() -> dict[str, list[str]]:
    """
    Backends per output format for UI. Keys: "http_ts", "hls" (http_hls), "webrtc".
    Values: list of backend names that support that output.
    """
    links = get_stream_links()
    by_out: dict[str, set[str]] = {"http_ts": set(), "hls": set(), "webrtc": set()}
    for link in links:
        out = link["output_format"]
        if out == "http_hls":
            by_out["hls"].add(link["backend"])
        elif out in by_out:
            by_out[out].add(link["backend"])
    return {k: sorted(v) for k, v in by_out.items()}
