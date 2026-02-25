"""Общее состояние и утилиты потокового модуля."""
from __future__ import annotations

import asyncio
import re
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Request

from backend.core.config import get_settings
from backend.core.utils import find_executable
from backend.core.webui_settings import (
    get_stream_capture_backend,
    get_stream_capture_backend_options,
    get_stream_capture_options,
    get_stream_playback_udp_backend,
    get_stream_playback_udp_backend_options,
    get_stream_playback_udp_output_format,
    get_webui_settings,
)

from backend.modules.stream import StreamFrameCapture, StreamPlaybackSession
from backend.modules.stream.capture import _backends_with_options, get_capture_backends_for_setting
from backend.modules.stream.utils.url import normalize_stream_url as _normalize_stream_url

_root = Path(__file__).resolve().parent.parent

_stream_capture: StreamFrameCapture | None = None
_playback_sessions: dict[str, StreamPlaybackSession] = {}
_whep_connections: dict[str, tuple] = {}
_queue = None
_preview_refresh_job_id: str | None = None
_preview_refresh_running = False
_preview_refresh_done_at: float | None = None

PREVIEW_CACHE_DIR = _root / "preview_cache"

_HEAVY_PREVIEW_SEMAPHORE = None
_HEAVY_PLAYBACK_SEMAPHORE = None

_per_ip_lock = asyncio.Lock()
_per_ip_semaphores: dict[tuple[str, str], asyncio.Semaphore] = {}


def init_heavy_semaphores() -> None:
    global _HEAVY_PREVIEW_SEMAPHORE, _HEAVY_PLAYBACK_SEMAPHORE
    s = get_settings()
    _HEAVY_PREVIEW_SEMAPHORE = asyncio.Semaphore(s.heavy_preview_global) if s.heavy_preview_global else None
    _HEAVY_PLAYBACK_SEMAPHORE = asyncio.Semaphore(s.heavy_playback_global) if s.heavy_playback_global else None


def get_heavy_semaphores():
    return _HEAVY_PREVIEW_SEMAPHORE, _HEAVY_PLAYBACK_SEMAPHORE


def set_stream_capture(capture: StreamFrameCapture | None) -> None:
    global _stream_capture
    _stream_capture = capture


def get_stream_capture() -> StreamFrameCapture | None:
    return _stream_capture


def set_queue(queue) -> None:
    global _queue
    _queue = queue


def get_queue():
    return _queue


def get_playback_sessions() -> dict[str, StreamPlaybackSession]:
    return _playback_sessions


def get_whep_connections() -> dict[str, tuple]:
    return _whep_connections


def set_preview_refresh_job_id(job_id: str | None) -> None:
    global _preview_refresh_job_id
    _preview_refresh_job_id = job_id


def get_preview_refresh_job_id() -> str | None:
    return _preview_refresh_job_id


def set_preview_refresh_state(running: bool, done_at: float | None = None) -> None:
    global _preview_refresh_running, _preview_refresh_done_at
    _preview_refresh_running = running
    if done_at is not None:
        _preview_refresh_done_at = done_at


def get_preview_refresh_state() -> tuple[bool, float | None]:
    return _preview_refresh_running, _preview_refresh_done_at


def get_preview_cache_dir() -> Path:
    return PREVIEW_CACHE_DIR


def get_stream_settings():
    return {
        "capture_opts": get_stream_capture_backend_options(),
        "playback_opts": get_stream_playback_udp_backend_options(),
        "playback_backend": get_stream_playback_udp_backend(),
        "playback_output": get_stream_playback_udp_output_format(),
        "capture_options": get_stream_capture_options(),
        "settings": get_webui_settings(),
    }


def create_stream_capture_from_settings() -> StreamFrameCapture:
    backend_classes = get_capture_backends_for_setting(get_stream_capture_backend())
    opts = get_stream_capture_backend_options()
    backends_with_opts = _backends_with_options(backend_classes, opts)
    return StreamFrameCapture(backends=backends_with_opts)


def client_ip(request: Request) -> str:
    return (request.client.host if request.client else "") or "unknown"


async def per_ip_semaphore(kind: str, ip: str, limit: int) -> asyncio.Semaphore:
    key = (kind, ip)
    async with _per_ip_lock:
        if key not in _per_ip_semaphores:
            _per_ip_semaphores[key] = asyncio.Semaphore(limit)
        return _per_ip_semaphores[key]


@asynccontextmanager
async def optional_sem(sem: asyncio.Semaphore | None):
    if sem is not None:
        async with sem:
            yield
    else:
        yield


def preview_cache_path(instance_id: int, name: str) -> Path:
    safe = re.sub(r"[^\w\-.]", "_", f"{instance_id}_{name}")[:200].strip("_") or "channel"
    return PREVIEW_CACHE_DIR / f"{safe}.jpg"


def normalize_stream_url(url: str, stream_host: str | None = None) -> str:
    return _normalize_stream_url(url, stream_host)
