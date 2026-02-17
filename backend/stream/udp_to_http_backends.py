"""Бэкенды UDP → HTTP (сырой MPEG-TS / HLS) для воспроизведения. FFmpeg, VLC, Astra, GStreamer, TSDuck, udp_proxy."""
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

from backend.stream.udp_to_http import parse_udp_url, stream_udp_to_http

UDP_TO_HTTP_BACKEND_ORDER = ["ffmpeg", "vlc", "astra", "gstreamer", "tsduck", "udp_proxy"]
VALID_UDP_TO_HTTP_BACKENDS = ("auto",) + tuple(UDP_TO_HTTP_BACKEND_ORDER)


def _norm_buffer_kb(opts: dict, key: str = "buffer_kb", default: int = 1024) -> int:
    v = opts.get(key)
    if not isinstance(v, (int, float)) or v < 64:
        return default
    return min(65536, max(64, int(v)))


def _norm_hls_params(opts: dict) -> tuple[int, int]:
    hls_time = 2
    if isinstance(opts.get("hls_time"), (int, float)):
        hls_time = max(1, min(30, int(opts["hls_time"])))
    hls_list_size = 5
    if isinstance(opts.get("hls_list_size"), (int, float)):
        hls_list_size = max(2, min(30, int(opts["hls_list_size"])))
    return hls_time, hls_list_size


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


class UdpToHttpBackend(ABC):
    """Бэкенд стриминга UDP-потока как MPEG-TS по HTTP."""

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
    ) -> AsyncIterator[bytes]:
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
        ff = opts.get("ffmpeg") or {}
        ffmpeg_bin = find_executable(ff.get("bin") or "ffmpeg")
        if not ffmpeg_bin:
            return
        chunk_size = _norm_buffer_kb(ff) * 1024
        extra = (ff.get("extra_args") or "").strip().split() if isinstance(ff.get("extra_args"), str) else []
        analyzeduration_us = min(30_000_000, max(10000, int(ff.get("analyzeduration_us") or 500000)))
        probesize = min(50_000_000, max(10000, int(ff.get("probesize") or 500000)))
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []

        def read_stdout() -> None:
            try:
                cmd = [
                    ffmpeg_bin,
                    "-protocol_whitelist", "file,http,https,tcp,tls,udp",
                    "-analyzeduration", str(analyzeduration_us),
                    "-probesize", str(probesize),
                ] + extra + ["-i", udp_url, "-c", "copy", "-f", "mpegts", "-"]
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                proc_holder.append(p)
                while not stop.is_set() and p.poll() is None and p.stdout:
                    chunk = p.stdout.read(chunk_size)
                    if not chunk:
                        break
                    queue.put(chunk)
            except Exception:
                pass
            finally:
                queue.put(b"")

        threading.Thread(target=read_stdout, daemon=True).start()
        async for chunk in _stream_from_queue(queue, request, stop, proc_holder):
            yield chunk

    @classmethod
    def start_hls(
        cls,
        udp_url: str,
        session_dir: Path,
        options: Optional[dict[str, Any]] = None,
    ) -> subprocess.Popen:
        opts = options or {}
        ff = opts.get("ffmpeg") or {}
        ffmpeg_bin = find_executable(ff.get("bin") or "ffmpeg")
        if not ffmpeg_bin:
            raise RuntimeError("ffmpeg not found")
        analyzeduration_us = min(30_000_000, max(10000, int(ff.get("analyzeduration_us") or 500000)))
        probesize = min(50_000_000, max(10000, int(ff.get("probesize") or 500000)))
        extra = (ff.get("extra_args") or "").strip().split() if isinstance(ff.get("extra_args"), str) else []
        hls_time, hls_list_size = _norm_hls_params(ff)
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = session_dir / "playlist.m3u8"
        seg_pattern = str(session_dir / "seg_%03d.ts")
        cmd = [
            ffmpeg_bin, "-y",
            "-protocol_whitelist", "file,http,https,tcp,tls,udp",
            "-analyzeduration", str(analyzeduration_us),
            "-probesize", str(probesize),
        ] + extra + [
            "-i", udp_url, "-c", "copy", "-f", "hls",
            "-hls_time", str(hls_time), "-hls_list_size", str(hls_list_size),
            "-hls_flags", "delete_segments+append_list+temp_file",
            "-hls_segment_filename", seg_pattern,
            str(playlist_path),
        ]
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class VLCUdpToHttpBackend(UdpToHttpBackend):
    name = "vlc"
    input_types = {"udp_ts"}
    output_types = {"http_ts", "http_hls"}

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
        vlc_bin = find_executable((opts.get("vlc") or {}).get("bin") or "vlc")
        if not vlc_bin:
            return
        chunk_size = _norm_buffer_kb(opts.get("vlc") or {}) * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []

        def read_stdout() -> None:
            try:
                cmd = [
                    vlc_bin, "-I", "dummy", "--no-video-title-show", "--no-audio", "--no-loop", "--run-time=0",
                    udp_url, "--sout", "#standard{access=file,mux=ts,dst=-}",
                ]
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                proc_holder.append(p)
                while not stop.is_set() and p.poll() is None and p.stdout:
                    chunk = p.stdout.read(chunk_size)
                    if not chunk:
                        break
                    queue.put(chunk)
            except Exception:
                pass
            finally:
                queue.put(b"")

        threading.Thread(target=read_stdout, daemon=True).start()
        async for chunk in _stream_from_queue(queue, request, stop, proc_holder):
            yield chunk

    @classmethod
    def start_hls(
        cls,
        udp_url: str,
        session_dir: Path,
        options: Optional[dict[str, Any]] = None,
    ) -> subprocess.Popen:
        opts = options or {}
        vlc_bin = find_executable((opts.get("vlc") or {}).get("bin") or "vlc")
        if not vlc_bin:
            raise RuntimeError("vlc not found")
        vlc_opts = opts.get("vlc") or {}
        hls_time, hls_list_size = _norm_hls_params(vlc_opts)
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = session_dir / "playlist.m3u8"
        seg_pattern = str(session_dir / "seg_###.ts")
        sout = (
            "#std{access=livehttp{seglen=%d,delsegs=true,numsegs=%d,index=%s,index-url=seg_###.ts},mux=ts,dst=%s}"
            % (hls_time, hls_list_size, playlist_path, seg_pattern)
        )
        cmd = [vlc_bin, "-I", "dummy", "--no-video-title-show", "--no-interact", "--run-time=0", udp_url, "--sout", sout]
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class AstraUdpToHttpBackend(UdpToHttpBackend):
    name = "astra"
    input_types = {"udp_ts"}
    output_types = {"http_ts"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        opts = options or {}
        relay_url = (opts.get("astra") or {}).get("relay_url") or ""
        return bool(str(relay_url).strip())

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
        base = ((opts.get("astra") or {}).get("relay_url") or "http://localhost:8000").strip().rstrip("/")
        addr = f"{mcast or '0.0.0.0'}:{port}"
        url = f"{base}/udp/{addr}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                async with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        return
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        try:
                            if await request.is_disconnected():
                                return
                        except Exception:
                            pass
                        yield chunk
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError):
            return


class GStreamerUdpToHttpBackend(UdpToHttpBackend):
    name = "gstreamer"
    input_types = {"udp_ts"}
    output_types = {"http_ts", "http_hls"}

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
        gst_bin = find_executable((opts.get("gstreamer") or {}).get("bin") or "gst-launch-1.0")
        if not gst_bin:
            return
        chunk_size = _norm_buffer_kb(opts.get("gstreamer") or {}) * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []
        pipeline = f"udpsrc uri={udp_url!r} ! fdsink sync=false"

        def read_stdout() -> None:
            try:
                p = subprocess.Popen([gst_bin, "-e", pipeline], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                proc_holder.append(p)
                while not stop.is_set() and p.poll() is None and p.stdout:
                    chunk = p.stdout.read(chunk_size)
                    if not chunk:
                        break
                    queue.put(chunk)
            except Exception:
                pass
            finally:
                queue.put(b"")

        threading.Thread(target=read_stdout, daemon=True).start()
        async for chunk in _stream_from_queue(queue, request, stop, proc_holder):
            yield chunk

    @classmethod
    def start_hls(
        cls,
        udp_url: str,
        session_dir: Path,
        options: Optional[dict[str, Any]] = None,
    ) -> subprocess.Popen:
        opts = options or {}
        gst_bin = find_executable((opts.get("gstreamer") or {}).get("bin") or "gst-launch-1.0")
        if not gst_bin:
            raise RuntimeError("gst-launch-1.0 not found")
        gst_opts = opts.get("gstreamer") or {}
        hls_time, hls_list_size = _norm_hls_params(gst_opts)
        session_dir.mkdir(parents=True, exist_ok=True)
        seg_pattern = session_dir / "seg_%05d.ts"
        playlist_path = session_dir / "playlist.m3u8"
        pipeline = (
            f"udpsrc uri={udp_url!r} ! tsparse set-timestamps=true ! tsdemux name=d "
            f"hlssink2 name=h location={seg_pattern!s} playlist-location={playlist_path!s} "
            f"target-duration={hls_time} max-files={hls_list_size} "
            f"d.video_0 ! queue ! h264parse ! h.video "
            f"d.audio_0 ! queue ! aacparse ! h.audio"
        )
        return subprocess.Popen([gst_bin, "-e", pipeline], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class TSDuckUdpToHttpBackend(UdpToHttpBackend):
    name = "tsduck"
    input_types = {"udp_ts"}
    output_types = {"http_ts", "http_hls"}

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
        tsp_bin = find_executable((opts.get("tsduck") or {}).get("bin") or "tsp")
        if not tsp_bin:
            return
        chunk_size = _norm_buffer_kb(opts.get("tsduck") or {}) * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []

        def read_stdout() -> None:
            try:
                cmd = [tsp_bin, "-I", "udp", "--local-port", str(port), "-O", "file", "-"]
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                proc_holder.append(p)
                while not stop.is_set() and p.poll() is None and p.stdout:
                    chunk = p.stdout.read(chunk_size)
                    if not chunk:
                        break
                    queue.put(chunk)
            except Exception:
                pass
            finally:
                queue.put(b"")

        threading.Thread(target=read_stdout, daemon=True).start()
        async for chunk in _stream_from_queue(queue, request, stop, proc_holder):
            yield chunk

    @classmethod
    def start_hls(
        cls,
        udp_url: str,
        session_dir: Path,
        options: Optional[dict[str, Any]] = None,
    ) -> subprocess.Popen:
        try:
            _bind_addr, port, _mcast = parse_udp_url(udp_url)
        except ValueError:
            raise RuntimeError("Invalid UDP URL for TSDuck")
        opts = options or {}
        tsp_bin = find_executable((opts.get("tsduck") or {}).get("bin") or "tsp")
        if not tsp_bin:
            raise RuntimeError("tsp not found")
        ts_opts = opts.get("tsduck") or {}
        hls_time, hls_list_size = _norm_hls_params(ts_opts)
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = session_dir / "playlist.m3u8"
        seg_template = session_dir / "seg.ts"
        cmd = [
            tsp_bin, "-I", "udp", "--local-port", str(port),
            "-O", "hls", "-d", str(hls_time), "-l", str(hls_list_size),
            "-p", str(playlist_path), str(seg_template),
        ]
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class ProxyUdpToHttpBackend(UdpToHttpBackend):
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
        async for chunk in stream_udp_to_http(
            udp_url,
            request_disconnected=lambda req=request: req.is_disconnected(),
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
    """Список имён бэкендов UDP→HTTP, доступных в системе (по типу входа и выхода)."""
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
