"""Бэкенды UDP → HTTP (сырой MPEG-TS) для воспроизведения. Цепочка: FFmpeg → VLC → Astra → GStreamer → TSDuck → proxy."""
from __future__ import annotations

import asyncio
import subprocess
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from queue import Empty, Queue
from typing import Any, AsyncIterator, Optional

import httpx
from backend.utils import find_executable

from backend.stream.udp_to_http import parse_udp_url

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
    output_types = {"http_ts", "http_hls"}

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

    @classmethod
    def start_hls(
        cls,
        udp_url: str,
        session_dir: Path,
        options: Optional[dict[str, Any]] = None,
    ) -> subprocess.Popen:
        """Запустить FFmpeg: UDP → HLS (playlist.m3u8 + сегменты в session_dir). Возвращает процесс."""
        opts = options or {}
        ff_opts = opts.get("ffmpeg") or {}
        bin_name = ff_opts.get("bin") or "ffmpeg"
        ffmpeg_bin = find_executable(bin_name)
        if not ffmpeg_bin:
            raise RuntimeError("ffmpeg not found")
        analyzeduration_us = 500000
        if isinstance(ff_opts.get("analyzeduration_us"), (int, float)):
            analyzeduration_us = min(30_000_000, max(10000, int(ff_opts["analyzeduration_us"])))
        probesize = 500000
        if isinstance(ff_opts.get("probesize"), (int, float)):
            probesize = min(50_000_000, max(10000, int(ff_opts["probesize"])))
        extra_args: list[str] = []
        if isinstance(ff_opts.get("extra_args"), str) and ff_opts["extra_args"].strip():
            extra_args = ff_opts["extra_args"].strip().split()
        hls_time = 2
        if isinstance(ff_opts.get("hls_time"), (int, float)):
            hls_time = max(1, min(30, int(ff_opts["hls_time"])))
        hls_list_size = 5
        if isinstance(ff_opts.get("hls_list_size"), (int, float)):
            hls_list_size = max(2, min(30, int(ff_opts["hls_list_size"])))
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = session_dir / "playlist.m3u8"
        seg_pattern = str(session_dir / "seg_%03d.ts")
        cmd = [
            ffmpeg_bin,
            "-y",
            "-protocol_whitelist", "file,http,https,tcp,tls,udp",
            "-analyzeduration", str(analyzeduration_us),
            "-probesize", str(probesize),
        ] + extra_args + [
            "-i", udp_url,
            "-c", "copy",
            "-f", "hls",
            "-hls_time", str(hls_time),
            "-hls_list_size", str(hls_list_size),
            "-hls_flags", "delete_segments+append_list",
            "-hls_segment_filename", seg_pattern,
            str(playlist_path),
        ]
        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class VLCUdpToHttpBackend(UdpToHttpBackend):
    name = "vlc"
    input_types = {"udp_ts"}
    output_types = {"http_ts"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        opts = options or {}
        bin_name = (opts.get("vlc") or {}).get("bin") or "vlc"
        return find_executable(bin_name) is not None

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        opts = options or {}
        vlc_opts = opts.get("vlc") or {}
        bin_name = vlc_opts.get("bin") or "vlc"
        vlc_bin = find_executable(bin_name)
        if not vlc_bin:
            return
        buffer_kb = 1024
        if isinstance(vlc_opts.get("buffer_kb"), (int, float)) and vlc_opts["buffer_kb"] >= 64:
            buffer_kb = min(65536, int(vlc_opts["buffer_kb"]))
        chunk_size = buffer_kb * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc = None

        def read_stdout():
            nonlocal proc
            try:
                # VLC: читаем UDP, отдаём TS в stdout. --run-time=0 = без лимита.
                cmd = [
                    vlc_bin,
                    "-I", "dummy",
                    "--no-video-title-show",
                    "--no-audio",
                    "--no-loop",
                    "--run-time=0",
                    udp_url,
                    "--sout", "#standard{access=file,mux=ts,dst=-}",
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


class AstraUdpToHttpBackend(UdpToHttpBackend):
    """
    Стриминг UDP→HTTP через Astra Relay (astra --relay -p PORT).
    Relay отдаёт поток по адресу http://relay_host:port/udp/<address>:<port>.
    """
    name = "astra"
    input_types = {"udp_ts"}
    output_types = {"http_ts"}  # Astra 4.x Relay только TS; HLS в Astra 5

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        opts = options or {}
        astra_opts = opts.get("astra") or {}
        relay_url = (astra_opts.get("relay_url") or "").strip()
        return bool(relay_url)

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        try:
            _bind_addr, port, mcast = parse_udp_url(udp_url)
        except ValueError:
            return
        opts = options or {}
        astra_opts = opts.get("astra") or {}
        base = (astra_opts.get("relay_url") or "http://localhost:8000").strip().rstrip("/")
        # Astra Relay: /udp/<address>:<port>, например /udp/239.255.1.1:1234
        addr = f"{mcast or '0.0.0.0'}:{port}"
        relay_path = f"/udp/{addr}"
        url = f"{base}{relay_path}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        return
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        try:
                            if await request.is_disconnected():
                                break
                        except Exception:
                            pass
                        yield chunk
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError):
            return


class GStreamerUdpToHttpBackend(UdpToHttpBackend):
    name = "gstreamer"
    input_types = {"udp_ts"}
    output_types = {"http_ts"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        opts = options or {}
        bin_name = (opts.get("gstreamer") or {}).get("bin") or "gst-launch-1.0"
        return find_executable(bin_name) is not None

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        opts = options or {}
        gst_opts = opts.get("gstreamer") or {}
        bin_name = gst_opts.get("bin") or "gst-launch-1.0"
        gst_bin = find_executable(bin_name)
        if not gst_bin:
            return
        buffer_kb = 1024
        if isinstance(gst_opts.get("buffer_kb"), (int, float)) and gst_opts["buffer_kb"] >= 64:
            buffer_kb = min(65536, int(gst_opts["buffer_kb"]))
        chunk_size = buffer_kb * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc = None
        pipeline = f"udpsrc uri={udp_url!r} ! fdsink sync=false"

        def read_stdout():
            nonlocal proc
            try:
                proc = subprocess.Popen(
                    [gst_bin, "-e", pipeline],
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


class TSDuckUdpToHttpBackend(UdpToHttpBackend):
    name = "tsduck"
    input_types = {"udp_ts"}
    output_types = {"http_ts"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        opts = options or {}
        bin_name = (opts.get("tsduck") or {}).get("bin") or "tsp"
        return find_executable(bin_name) is not None

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        try:
            _bind_addr, port, _mcast = parse_udp_url(udp_url)
        except ValueError:
            return
        opts = options or {}
        ts_opts = opts.get("tsduck") or {}
        bin_name = ts_opts.get("bin") or "tsp"
        tsp_bin = find_executable(bin_name)
        if not tsp_bin:
            return
        buffer_kb = 1024
        if isinstance(ts_opts.get("buffer_kb"), (int, float)) and ts_opts["buffer_kb"] >= 64:
            buffer_kb = min(65536, int(ts_opts["buffer_kb"]))
        chunk_size = buffer_kb * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc = None

        def read_stdout():
            nonlocal proc
            try:
                cmd = [
                    tsp_bin,
                    "-I", "udp", "--local-port", str(port),
                    "-O", "file", "-",
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
