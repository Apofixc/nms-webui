"""VLC stream backend."""
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
    _get_vlc_bin,
    _stream_from_queue,
)
from backend.modules.stream.outputs.hls import default_playlist_path, norm_hls_params

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


def _build_http_ts_cmd(vlc_bin: str, source_url: str) -> list[str]:
    return [
        vlc_bin,
        "-I",
        "dummy",
        "--no-video",
        "--no-audio",
        "--no-video-title-show",
        "--sout",
        "#std{access=file,mux=ts,dst=-}",
        source_url,
        "vlc://quit",
    ]


def _build_hls_cmd(vlc_bin: str, source_url: str, playlist_path: Path, seg_pattern: str, hls_time: int, hls_list_size: int) -> list[str]:
    sout = (
        "#std{access=livehttp{"
        f"seglen={hls_time},"
        f"delsegs=true,"
        f"numsegs={hls_list_size},"
        f"index={playlist_path},"
        "index-url=seg_###.ts"
        "},mux=ts,"
        f"dst={seg_pattern}"
        "}"
    )
    return [
        vlc_bin,
        "-I",
        "dummy",
        "--no-video",
        "--no-audio",
        "--no-video-title-show",
        "--sout",
        sout,
        source_url,
    ]


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
    ) -> AsyncGenerator[bytes, None]:
        opts = options or {}
        vlc_bin = _get_vlc_bin(opts)
        if not vlc_bin:
            return
        read_size = PIPE_READ_KB * 1024
        queue: Queue[bytes] = Queue()
        stop = threading.Event()
        proc_holder: list = []
        cmd = _build_http_ts_cmd(vlc_bin, udp_url)

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
                logger.warning("VLC stream read_stdout: %s", e)
            finally:
                if proc is not None:
                    _read_and_log_stderr(proc, "VLC stream")
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
        cmd = _build_hls_cmd(vlc_bin, udp_url, playlist_path, seg_pattern, hls_time, hls_list_size)
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
