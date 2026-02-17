"""Бэкенды UDP → HTTP (сырой MPEG-TS) для воспроизведения. Цепочка: FFmpeg → VLC → Astra → GStreamer → TSDuck → proxy."""
from __future__ import annotations

import asyncio
import subprocess
import threading
from abc import ABC, abstractmethod
from queue import Empty, Queue
from typing import Any, AsyncIterator, Optional

from backend.utils import find_executable

# Порядок при auto
UDP_TO_HTTP_BACKEND_ORDER = ["ffmpeg", "vlc", "astra", "gstreamer", "tsduck", "udp_proxy"]

VALID_UDP_TO_HTTP_BACKENDS = ("auto",) + tuple(UDP_TO_HTTP_BACKEND_ORDER)


class UdpToHttpBackend(ABC):
    """Бэкенд стриминга UDP-потока как MPEG-TS по HTTP."""

    name: str = ""
    # Типы потоков (для матрицы возможностей).
    # Для UDP-воспроизведения вход всегда udp_ts; выход — http_ts или http_hls.
    input_types: set[str] = set()
    output_types: set[str] = set()

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        """Доступен ли бэкенд (с учётом опций из настроек)."""
        raise NotImplementedError

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        """Стримить байты MPEG-TS. request — FastAPI Request для проверки отключения клиента."""
        raise NotImplementedError


class FFmpegUdpToHttpBackend(UdpToHttpBackend):
    name = "ffmpeg"
    input_types = {"udp_ts"}
    # Сейчас реализуем только сырой MPEG-TS по HTTP; HLS можно добавить позже.
    output_types = {"http_ts"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        opts = options or {}
        bin_name = (opts.get("ffmpeg") or {}).get("bin") or "ffmpeg"
        return find_executable(bin_name) is not None

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        opts = options or {}
        ff_opts = opts.get("ffmpeg") or {}
        bin_name = ff_opts.get("bin") or "ffmpeg"
        ffmpeg_bin = find_executable(bin_name)
        if not ffmpeg_bin:
            return
        buffer_kb = ff_opts.get("buffer_kb")
        if not isinstance(buffer_kb, (int, float)) or buffer_kb < 64:
            buffer_kb = 1024
        buffer_kb = min(65536, max(64, int(buffer_kb)))
        chunk_size = buffer_kb * 1024
        extra_args_str = ff_opts.get("extra_args") or ""
        extra_args: list[str] = []
        if isinstance(extra_args_str, str) and extra_args_str.strip():
            extra_args = extra_args_str.strip().split()
        analyzeduration_us = ff_opts.get("analyzeduration_us")
        if not isinstance(analyzeduration_us, (int, float)) or analyzeduration_us < 10000:
            analyzeduration_us = 500000
        analyzeduration_us = min(30_000_000, max(10000, int(analyzeduration_us)))
        probesize = ff_opts.get("probesize")
        if not isinstance(probesize, (int, float)) or probesize < 10000:
            probesize = 500000
        probesize = min(50_000_000, max(10000, int(probesize)))
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc = None

        def read_stdout():
            nonlocal proc
            try:
                cmd = [
                    ffmpeg_bin,
                    "-protocol_whitelist", "file,http,https,tcp,tls,udp",
                    "-analyzeduration", str(analyzeduration_us),
                    "-probesize", str(probesize),
                ] + extra_args + [
                    "-i", udp_url,
                    "-c", "copy",
                    "-f", "mpegts",
                    "-",
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                while not stop.is_set() and proc.poll() is None and proc.stdout:
                    chunk = proc.stdout.read(chunk_size)
                    if not chunk:
                        break
                    queue.put(chunk)
            except Exception:
                pass
            finally:
                queue.put(b"")

        thread = threading.Thread(target=read_stdout, daemon=True)
        thread.start()
        try:
            while True:
                try:
                    chunk = await asyncio.get_running_loop().run_in_executor(
                        None, lambda: queue.get(timeout=0.5)
                    )
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
            stop.set()
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()


class VLCUdpToHttpBackend(UdpToHttpBackend):
    name = "vlc"
    input_types = {"udp_ts"}
    output_types = {"http_ts", "http_hls"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        return False

    @classmethod
    async def stream(cls, udp_url: str, request: Any, options: Optional[dict[str, Any]] = None) -> AsyncIterator[bytes]:
        raise NotImplementedError("VLC UDP→HTTP не реализован")


class AstraUdpToHttpBackend(UdpToHttpBackend):
    name = "astra"
    input_types = {"udp_ts"}
    output_types = {"http_ts", "http_hls"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        return False

    @classmethod
    async def stream(cls, udp_url: str, request: Any, options: Optional[dict[str, Any]] = None) -> AsyncIterator[bytes]:
        raise NotImplementedError("Astra UDP→HTTP не реализован")


class GStreamerUdpToHttpBackend(UdpToHttpBackend):
    name = "gstreamer"
    input_types = {"udp_ts"}
    output_types = {"http_ts", "http_hls"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        return False

    @classmethod
    async def stream(cls, udp_url: str, request: Any, options: Optional[dict[str, Any]] = None) -> AsyncIterator[bytes]:
        raise NotImplementedError("GStreamer UDP→HTTP не реализован")


class TSDuckUdpToHttpBackend(UdpToHttpBackend):
    name = "tsduck"
    input_types = {"udp_ts"}
    output_types = {"http_ts", "http_hls"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        return False

    @classmethod
    async def stream(cls, udp_url: str, request: Any, options: Optional[dict[str, Any]] = None) -> AsyncIterator[bytes]:
        raise NotImplementedError("TSDuck UDP→HTTP не реализован")


class ProxyUdpToHttpBackend(UdpToHttpBackend):
    """Встроенный прокси без внешних программ."""
    name = "udp_proxy"
    input_types = {"udp_ts"}
    output_types = {"http_ts"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        return True

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        from backend.stream.udp_to_http import stream_udp_to_http
        async for chunk in stream_udp_to_http(
            udp_url,
            request_disconnected=lambda: request.is_disconnected(),
        ):
            yield chunk


UDP_TO_HTTP_BACKENDS_BY_NAME: dict[str, type[UdpToHttpBackend]] = {
    "ffmpeg": FFmpegUdpToHttpBackend,
    "vlc": VLCUdpToHttpBackend,
    "astra": AstraUdpToHttpBackend,
    "gstreamer": GStreamerUdpToHttpBackend,
    "tsduck": TSDuckUdpToHttpBackend,
    "udp_proxy": ProxyUdpToHttpBackend,
}


def get_available_udp_to_http_backends(
    options: Optional[dict[str, Any]] = None,
    input_type: str = "udp_ts",
    output_type: str = "http_ts",
) -> list[str]:
    """
    Список имён бэкендов UDP→HTTP, доступных в системе,
    с учётом типа входа и желаемого формата выхода.
    """
    result = []
    for name in UDP_TO_HTTP_BACKEND_ORDER:
        cls = UDP_TO_HTTP_BACKENDS_BY_NAME.get(name)
        if (
            cls
            and input_type in getattr(cls, "input_types", set())
            and output_type in getattr(cls, "output_types", set())
            and cls.available(options)
        ):
            result.append(name)
    return result


def get_udp_to_http_backend_chain(preference: str) -> list[str]:
    """По настройке (auto | ffmpeg | ...) вернуть список имён бэкендов для перебора."""
    if not preference or preference == "auto":
        return list(UDP_TO_HTTP_BACKEND_ORDER)
    if preference in UDP_TO_HTTP_BACKENDS_BY_NAME:
        return [preference]
    return list(UDP_TO_HTTP_BACKEND_ORDER)
