"""Бэкенд стриминга через TSDuck."""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from queue import Queue
from typing import Any, AsyncIterator, Optional

from backend.utils import find_executable

from backend.stream.backends.base import (
    PIPE_READ_KB,
    StreamBackend,
    _stream_from_queue,
)
from backend.stream.backends.udp_to_http import parse_udp_url
from backend.stream.outputs.hls import (
    default_playlist_path,
    norm_hls_params,
    tsduck_segment_path,
)


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
        hls_time, hls_list_size = norm_hls_params(ts_opts)
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = default_playlist_path(session_dir)
        seg_template = tsduck_segment_path(session_dir)
        cmd = [
            tsp_bin, "-I", "udp", "--local-port", str(port),
            "-O", "hls", "-d", str(hls_time), "-l", str(hls_list_size),
            "-p", str(playlist_path), str(seg_template),
        ]
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
