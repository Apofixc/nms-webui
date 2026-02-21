"""VLC stream backend."""
from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path
from queue import Queue
from typing import Any, AsyncIterator, Optional

from backend.utils import find_executable

from backend.stream.backends.base import (
    PIPE_READ_KB,
    StreamBackend,
    _get_vlc_bin,
    _stream_from_queue,
)
from backend.stream.outputs.hls import default_playlist_path, norm_hls_params

logger = logging.getLogger(__name__)


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
                        msg = b"".join(stderr_chunks).decode("utf-8", errors="replace").strip() or "(empty)"
                        logger.warning("VLC stderr: %s", msg)
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
        hls_time, hls_list_size = norm_hls_params(vlc_opts)
        session_dir = Path(session_dir).resolve()
        session_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = default_playlist_path(session_dir)
        seg_pattern = str(session_dir / "seg_###.ts")
        sout = "#std{access=livehttp{seglen=" + str(hls_time) + ",delsegs=true,numsegs=" + str(hls_list_size)
        sout += ",index=" + str(playlist_path) + ",index-url=seg_###.ts},mux=ts,dst=" + seg_pattern + "}"
        cmd = [vlc_bin, "-I", "dummy", "--no-video-title-show", "--no-interact", "--run-time=0", udp_url, "--sout", sout]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        def _log_vlc_stderr_on_exit():
            try:
                proc.wait()
                if proc.stderr:
                    err = proc.stderr.read().decode("utf-8", errors="replace").strip()
                    if err:
                        logger.warning("VLC HLS process exited (code=%s), stderr: %s", proc.returncode, err)
            except Exception as e:
                logger.debug("VLC HLS stderr reader: %s", e)

        threading.Thread(target=_log_vlc_stderr_on_exit, daemon=True).start()
        return proc
