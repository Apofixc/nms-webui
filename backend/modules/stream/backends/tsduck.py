"""Бэкенд стриминга через TSDuck."""
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
    norm_hls_params,
    tsduck_segment_path,
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


def _build_http_ts_cmd(tsp_bin: str, port: int) -> list[str]:
    return [tsp_bin, "-I", "udp", "--local-port", str(port), "-O", "file", "-"]


def _build_hls_cmd(
    tsp_bin: str,
    port: int,
    hls_time: int,
    hls_list_size: int,
    playlist_path: Path,
    seg_template: Path,
) -> list[str]:
    return [
        tsp_bin,
        "-I",
        "udp",
        "--local-port",
        str(port),
        "-O",
        "hls",
        "-d",
        str(hls_time),
        "-l",
        str(hls_list_size),
        "-p",
        str(playlist_path),
        str(seg_template),
    ]


class TSDuckStreamBackend(StreamBackend):
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
    ) -> AsyncGenerator[bytes, None]:
        try:
            _bind_addr, port, _mcast = parse_udp_url(udp_url)
        except ValueError as e:
            logger.warning("TSDuck: invalid UDP URL: %s", udp_url[:80])
            raise ValueError(f"Invalid UDP URL for TSDuck: {e}") from e
        opts = options or {}
        tsp_bin = find_executable((opts.get("tsduck") or {}).get("bin") or "tsp")
        if not tsp_bin:
            logger.warning("TSDuck: tsp not found")
            raise RuntimeError("tsp not found")
        read_size = PIPE_READ_KB * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []
        cmd = _build_http_ts_cmd(tsp_bin, port)

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
                logger.warning("TSDuck stream read error: %s", e)
            finally:
                if proc is not None:
                    _read_and_log_stderr(proc, "TSDuck stream")
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
        hls_time, hls_list_size = norm_hls_params(ts_opts)
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = default_playlist_path(session_dir)
        seg_template = tsduck_segment_path(session_dir)
        cmd = _build_hls_cmd(tsp_bin, port, hls_time, hls_list_size, playlist_path, seg_template)
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
