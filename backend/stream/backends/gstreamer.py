"""GStreamer stream backend."""
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
    gstreamer_segment_path,
    norm_hls_params,
)


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
        hls_time, hls_list_size = norm_hls_params(gst_opts)
        session_dir.mkdir(parents=True, exist_ok=True)
        seg_pattern = gstreamer_segment_path(session_dir)
        playlist_path = default_playlist_path(session_dir)
        pipeline = (
            f"udpsrc uri={udp_url!r} ! tsparse set-timestamps=true ! tsdemux name=d "
            f"hlssink2 name=h location={seg_pattern!s} playlist-location={playlist_path!s} "
            f"target-duration={hls_time} max-files={hls_list_size} "
            f"d.video_0 ! queue ! h264parse ! h.video "
            f"d.audio_0 ! queue ! aacparse ! h.audio"
        )
        return subprocess.Popen([gst_bin, "-e", pipeline], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
