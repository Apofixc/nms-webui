"""Абстрактный StreamBackend и общие хелперы для бэкендов стриминга."""
from __future__ import annotations

import asyncio
import subprocess
import threading
from abc import ABC, abstractmethod
from queue import Empty, Queue
from typing import Any, AsyncGenerator, AsyncIterator, Optional

from backend.core.utils import find_executable

from backend.modules.stream.outputs.http_ts import PIPE_READ_KB
from backend.modules.stream.outputs.hls import norm_hls_params as _norm_hls_params

__all__ = [
    "StreamBackend",
    "PIPE_READ_KB",
    "_stream_from_queue",
    "_norm_buffer_kb",
    "_norm_hls_params",
    "_get_vlc_bin",
]


def _norm_buffer_kb(opts: dict, key: str = "buffer_kb", default: int = 1024) -> int:
    v = opts.get(key)
    if not isinstance(v, (int, float)) or v < 64:
        return default
    return min(65536, max(64, int(v)))


def _get_vlc_bin(opts: Optional[dict] = None) -> Optional[str]:
    """Предпочитаем cvlc (без интерфейса); иначе vlc. Учитываем opts['vlc']['bin']."""
    vlc_opts = (opts or {}).get("vlc") or {}
    explicit = vlc_opts.get("bin")
    if explicit:
        return find_executable(str(explicit).strip())
    return find_executable("cvlc") or find_executable("vlc")


async def _stream_from_queue(
    queue: Queue[bytes],
    request: Any,
    stop_event: threading.Event,
    proc_holder: list,
) -> AsyncIterator[bytes]:
    """Общий цикл: читаем из queue через executor, проверяем request.is_disconnected(); в finally останавливаем процесс."""
    loop = asyncio.get_running_loop()
    try:
        while True:
            try:
                chunk = await loop.run_in_executor(None, lambda q=queue: q.get(timeout=0.5))
            except Empty:
                try:
                    if await request.is_disconnected():
                        break
                except Exception:
                    pass
                continue
            if not chunk:
                break
            yield chunk
    finally:
        stop_event.set()
        proc = proc_holder[0] if proc_holder else None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


class StreamBackend(ABC):
    """Бэкенд стриминга (вход: UDP/HTTP/RTP/файл/RTSP и др. → выход: HTTP-TS, HLS, WebRTC)."""

    name: str = ""
    input_types: set[str] = set()
    output_types: set[str] = set()

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        raise NotImplementedError

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError
        yield  # unreachable; makes this an async generator to match overrides
