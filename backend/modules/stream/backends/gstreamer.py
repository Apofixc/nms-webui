"""GStreamer stream backend."""
from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path
from queue import Queue
from typing import Any, AsyncGenerator, Optional

from backend.core.utils import find_executable

from backend.modules.stream.backends.base import (
    PIPE_READ_KB,
    StreamBackend,
    _stream_from_queue,
)
from backend.modules.stream.backends.udp_to_http import parse_udp_url
from backend.modules.stream.outputs.hls import (
    default_playlist_path,
    gstreamer_segment_path,
    norm_hls_params,
)

logger = logging.getLogger(__name__)


def _read_and_log_stderr(proc: subprocess.Popen, prefix: str) -> None:
    try:
        if not proc.stderr:
            return
        err = proc.stderr.read()
        if not err:
            return
        msg = err.decode("utf-8", errors="replace").strip()
        if msg:
            logger.warning("%s stderr: %s", prefix, msg[:1200])
    except Exception:
        pass


def _source_elements(source_url: str) -> list[str]:
    url = (source_url or "").strip()
    lower = url.lower()
    if lower.startswith("udp://") or lower.startswith("udp@"):
        _bind_addr, port, mcast = parse_udp_url(url)
        elems = ["udpsrc", f"port={port}", "auto-multicast=true"]
        if mcast:
            elems.append(f"multicast-group={mcast}")
        return elems
    if lower.startswith("http://") or lower.startswith("https://"):
        return ["souphttpsrc", f"location={url}"]
    if lower.startswith("file://"):
        return ["filesrc", f"location={url[7:]}"]
    # Local path fallback
    return ["filesrc", f"location={url}"]


def _build_http_ts_cmd(gst_bin: str, source_url: str) -> list[str]:
    return [
        gst_bin,
        "-e",
        *_source_elements(source_url),
        "!",
        "queue",
        "!",
        "fdsink",
        "fd=1",
        "sync=false",
    ]


def _build_hls_cmd(gst_bin: str, source_url: str, seg_pattern: Path, playlist_path: Path, hls_time: int, hls_list_size: int) -> list[str]:
    return [
        gst_bin,
        "-e",
        *_source_elements(source_url),
        "!",
        "queue",
        "!",
        "hlssink2",
        f"location={seg_pattern}",
        f"playlist-location={playlist_path}",
        f"target-duration={hls_time}",
        f"max-files={hls_list_size}",
    ]


class GStreamerStreamBackend(StreamBackend):
    name = "gstreamer"
    input_types = {"udp_ts", "http", "file"}
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
    ) -> AsyncGenerator[bytes, None]:
        opts = options or {}
        gst_bin = find_executable((opts.get("gstreamer") or {}).get("bin") or "gst-launch-1.0")
        if not gst_bin:
            return
        read_size = PIPE_READ_KB * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []
        cmd = _build_http_ts_cmd(gst_bin, udp_url)

        def read_stdout() -> None:
            proc = None
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                proc_holder.append(proc)
                while not stop.is_set() and proc.poll() is None and proc.stdout:
                    chunk = proc.stdout.read(read_size)
                    if not chunk:
                        break
                    queue.put(chunk)
            except Exception as e:
                logger.warning("GStreamer stream read error: %s", e)
            finally:
                if proc is not None:
                    _read_and_log_stderr(proc, "GStreamer stream")
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
        hls_time, hls_list_size = norm_hls_params(gst_opts)
        session_dir.mkdir(parents=True, exist_ok=True)
        seg_pattern = gstreamer_segment_path(session_dir)
        playlist_path = default_playlist_path(session_dir)
        cmd = _build_hls_cmd(gst_bin, udp_url, seg_pattern, playlist_path, hls_time, hls_list_size)
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
