"""FFmpeg stream backend."""
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
from backend.stream.outputs.hls import (
    default_playlist_path,
    ffmpeg_segment_pattern,
    norm_hls_params,
)


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
        hls_time, hls_list_size = norm_hls_params(ff)
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = default_playlist_path(session_dir)
        seg_pattern = ffmpeg_segment_pattern(session_dir)
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
