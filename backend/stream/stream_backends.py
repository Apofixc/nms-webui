"""Бэкенды стриминга (вход: UDP/HTTP/RTP/файл/RTSP/SRT/HLS и др. → выход: HTTP-TS, HLS, WebRTC).

FFmpeg, VLC, Astra, GStreamer, TSDuck, udp_proxy. Реестр связок: выбор бэкенда по паре (input_format, output_format).
У Astra выход np — push по HTTP; для браузера в NMS используется только выход http (pull).
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from queue import Empty, Queue
from typing import Any, AsyncIterator, Optional

import httpx
from backend.utils import find_executable

logger = logging.getLogger(__name__)

from backend.stream.udp_to_http import parse_udp_url, stream_udp_to_http

STREAM_BACKEND_ORDER = ["ffmpeg", "vlc", "astra", "gstreamer", "tsduck", "udp_proxy"]
VALID_STREAM_BACKENDS = ("auto",) + tuple(STREAM_BACKEND_ORDER)

# Алиасы входных форматов для сопоставления с input_types бэкендов (udp <-> udp_ts и др.)
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

# Входные и выходные форматы для реестра (браузер). Расширенный список по документации бэкендов.
STREAM_INPUT_FORMATS = ("udp", "http", "rtp", "file", "rtsp", "srt", "hls", "tcp")
STREAM_OUTPUT_FORMATS = ("http_ts", "http_hls", "webrtc")


# Размер чтения из pipe процесса (KB): маленький = быстрый первый чанк для клиента
PIPE_READ_KB = 64

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
    ) -> AsyncIterator[bytes]:
        raise NotImplementedError


class FFmpegStreamBackend(StreamBackend):
    name = "ffmpeg"
    input_types = {"udp_ts", "http", "file", "rtp", "tcp", "rtsp", "srt", "hls"}
    output_types = {"http_ts", "http_hls", "webrtc"}

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
        read_size = PIPE_READ_KB * 1024
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
                    chunk = p.stdout.read(read_size)
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


class VLCStreamBackend(StreamBackend):
    name = "vlc"
    input_types = {"udp_ts", "http", "file", "rtp", "rtsp"}
    output_types = {"http_ts", "http_hls"}

    @classmethod
    def available(cls, options: Optional[dict[str, Any]] = None) -> bool:
        return _get_vlc_bin(options) is not None

    @classmethod
    async def stream(
        cls,
        udp_url: str,
        request: Any,
        options: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        opts = options or {}
        vlc_bin = _get_vlc_bin(opts)
        if not vlc_bin:
            return
        read_size = PIPE_READ_KB * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []
        # Разбуферизация stdout (при pipe VLC может буферизовать до заполнения)
        stdbuf_bin = find_executable("stdbuf")
        vlc_cmd = [
            vlc_bin, "-I", "dummy", "--no-video-title-show", "--no-audio", "--no-loop", "--run-time=0",
            udp_url, "--sout", "#std{access=file,mux=ts,dst=-}",
        ]
        cmd = [stdbuf_bin, "-o0"] + vlc_cmd if stdbuf_bin else vlc_cmd

        def read_stderr(proc: subprocess.Popen, holder: list) -> None:
            if proc.stderr:
                try:
                    err = proc.stderr.read()
                    if err:
                        holder.append(err)
                except Exception:
                    pass

        def read_stdout() -> None:
            stderr_chunks: list = []
            stderr_reader: Optional[threading.Thread] = None
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                proc_holder.append(p)
                stderr_reader = threading.Thread(target=read_stderr, args=(p, stderr_chunks), daemon=True)
                stderr_reader.start()
                while not stop.is_set() and p.poll() is None and p.stdout:
                    chunk = p.stdout.read(read_size)
                    if not chunk:
                        break
                    queue.put(chunk)
            except Exception as e:
                logger.warning("VLC stream read_stdout: %s", e)
            finally:
                if proc_holder:
                    try:
                        proc_holder[0].stderr.close()
                    except Exception:
                        pass
                if stderr_reader is not None:
                    stderr_reader.join(timeout=1.0)
                if stderr_chunks:
                    try:
                        logger.warning(
                            "VLC stderr: %s",
                            b"".join(stderr_chunks).decode("utf-8", errors="replace").strip() or "(empty)",
                        )
                    except Exception:
                        pass
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
        vlc_bin = _get_vlc_bin(opts)
        if not vlc_bin:
            raise RuntimeError("cvlc/vlc not found")
        vlc_opts = opts.get("vlc") or {}
        hls_time, hls_list_size = _norm_hls_params(vlc_opts)
        session_dir = Path(session_dir).resolve()
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = session_dir / "playlist.m3u8"
        seg_pattern = str(session_dir / "seg_###.ts")
        sout = (
            "#std{access=livehttp{seglen=%d,delsegs=true,numsegs=%d,index=%s,index-url=seg_###.ts},mux=ts,dst=%s}"
            % (hls_time, hls_list_size, playlist_path, seg_pattern)
        )
        cmd = [vlc_bin, "-I", "dummy", "--no-video-title-show", "--no-interact", "--run-time=0", udp_url, "--sout", sout]
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class AstraStreamBackend(StreamBackend):
    name = "astra"
    input_types = {"udp_ts", "rtp", "file", "http"}
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


class GStreamerStreamBackend(StreamBackend):
    name = "gstreamer"
    input_types = {"udp_ts", "http", "file", "rtp", "rtsp"}
    output_types = {"http_ts", "http_hls", "webrtc"}

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
        read_size = PIPE_READ_KB * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []
        pipeline = f"udpsrc uri={udp_url!r} ! fdsink sync=false"

        def read_stdout() -> None:
            try:
                p = subprocess.Popen([gst_bin, "-e", pipeline], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                proc_holder.append(p)
                while not stop.is_set() and p.poll() is None and p.stdout:
                    chunk = p.stdout.read(read_size)
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


class TSDuckStreamBackend(StreamBackend):
    name = "tsduck"
    input_types = {"udp_ts", "file", "http", "hls", "srt"}
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
        read_size = PIPE_READ_KB * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []

        def read_stdout() -> None:
            try:
                cmd = [tsp_bin, "-I", "udp", "--local-port", str(port), "-O", "file", "-"]
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                proc_holder.append(p)
                while not stop.is_set() and p.poll() is None and p.stdout:
                    chunk = p.stdout.read(read_size)
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


class ProxyUdpStreamBackend(StreamBackend):
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


STREAM_BACKENDS_BY_NAME: dict[str, type[StreamBackend]] = {
    "ffmpeg": FFmpegStreamBackend,
    "vlc": VLCStreamBackend,
    "astra": AstraStreamBackend,
    "gstreamer": GStreamerStreamBackend,
    "tsduck": TSDuckStreamBackend,
    "udp_proxy": ProxyUdpStreamBackend,
}


def _backend_supports_link(
    backend_cls: type[StreamBackend],
    input_format: str,
    output_format: str,
) -> bool:
    """Проверить, что бэкенд поддерживает связку (input_format, output_format). Учитывает алиасы (udp <-> udp_ts)."""
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
    """Список имён бэкендов стриминга, доступных в системе (по типу входа и выхода)."""
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
    """
    Список имён бэкендов, поддерживающих связку (input_format, output_format) и доступных в системе.
    input_format: udp | http | rtp | file | rtsp | srt | hls | tcp, output_format: http_ts | http_hls | webrtc.
    """
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
    Выбрать бэкенд для связки (input_format, output_format).
    preference: auto | имя бэкенда.
    Возвращает имя бэкенда. При ручном выборе и неподдерживаемой связке — ValueError.
    При авто и отсутствии доступных бэкендов — ValueError.
    """
    available = get_available_backends_for_link(input_format, output_format, options)
    if preference and preference != "auto":
        if preference not in STREAM_BACKENDS_BY_NAME:
            raise ValueError(f"Unknown backend: {preference}")
        cls = STREAM_BACKENDS_BY_NAME[preference]
        if not _backend_supports_link(cls, input_format, output_format):
            raise ValueError(
                f"Backend '{preference}' does not support input {input_format!r} → output {output_format!r}"
            )
        if not cls.available(options):
            raise ValueError(f"Backend '{preference}' is not available (not installed or not configured)")
        return preference
    if not available:
        raise ValueError(
            f"No backend available for input {input_format!r} → output {output_format!r}"
        )
    return available[0]


def get_stream_links(backend_name: str | None = None) -> list[dict[str, str]]:
    """
    Список поддерживаемых связок (input_format × output_format) для UI настроек.
    backend_name: если задан, только для этого бэкенда; иначе для всех.
    Возвращает список {"backend": str, "input_format": str, "output_format": str}.
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
    """По настройке (auto | ffmpeg | ...) вернуть список имён бэкендов для перебора."""
    if not preference or preference == "auto":
        return list(STREAM_BACKEND_ORDER)
    if preference in STREAM_BACKENDS_BY_NAME:
        return [preference]
    return list(STREAM_BACKEND_ORDER)
