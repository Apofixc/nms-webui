from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


_NETWORK_PROTOCOLS = ["http", "https", "rtsp", "rtmp", "rtmps", "udp", "srt", "hls", "dash"]
_BROWSER_OUTPUTS = ["http_ts", "http_hls", "dash", "mp4", "webm", "jpg", "png", "webrtc"]


class FFmpegBackend(IStreamBackend):
    """FFmpeg backend с сетевыми входами и браузерными выводами."""

    def __init__(self):
        self._available = False

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "protocols": _NETWORK_PROTOCOLS,
            "outputs": _BROWSER_OUTPUTS,
            "features": ["transcoding", "browser_formats"],
            "priority_matrix": {
                "http": {"http_hls": 80, "dash": 80, "mp4": 70, "webm": 60, "jpg": 60, "png": 60},
                "https": {"http_hls": 80, "dash": 80, "mp4": 70, "webm": 60},
                "rtsp": {"http_hls": 90, "dash": 85, "mp4": 80, "jpg": 70, "png": 70},
                "udp": {"http_ts": 85, "http_hls": 80, "dash": 75},
                "srt": {"http_hls": 85, "dash": 80, "mp4": 70},
            },
        }

    def match_score(self, input_proto: str, output_format: str) -> int:
        caps = self.get_capabilities()
        if input_proto in caps.get("protocols", []) and output_format in caps.get("outputs", []):
            return int((caps.get("priority_matrix", {}).get(input_proto, {}) or {}).get(output_format, 50))
        return 0

    async def initialize(self, config: dict[str, Any]) -> bool:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        self._available = bool(ffmpeg and ffprobe)
        return self._available

    async def health_check(self) -> bool:
        return self._available

    async def shutdown(self) -> None:
        return None

    async def _run_ffmpeg(self, args: list[str], timeout: float = 60.0) -> tuple[bool, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return False, "ffmpeg timeout"
            if proc.returncode != 0:
                return False, stderr.decode(errors="ignore")
            return True, ""
        except FileNotFoundError:
            return False, "ffmpeg not installed"
        except Exception as exc:  # pragma: no cover
            return False, str(exc)

    async def process(self, task: StreamTask) -> StreamResult:
        if not self._available:
            return StreamResult(success=False, output_path=None, backend_name="ffmpeg", error="ffmpeg unavailable")

        output_format = task.output_format or "mp4"
        input_url = task.input_url
        if not input_url:
            return StreamResult(success=False, output_path=None, backend_name="ffmpeg", error="input_url required")

        # Разрешаем только сетевые протоколы
        if not any(input_url.startswith(proto) for proto in ("http://", "https://", "rtsp://", "rtmp://", "rtmps://", "udp://", "srt://")):
            return StreamResult(success=False, output_path=None, backend_name="ffmpeg", error="protocol not allowed")

        out_dir = Path("/tmp/stream_ffmpeg") / (task.id or uuid.uuid4().hex)
        out_dir.mkdir(parents=True, exist_ok=True)

        # WebRTC не поддерживается напрямую ffmpeg
        if output_format == "webrtc":
            return StreamResult(success=False, output_path=None, backend_name="ffmpeg", error="webrtc not supported by ffmpeg")

        # Настройка команд под разные выводы
        out_path: Path
        cmd: list[str]
        common_input = ["ffmpeg", "-y", "-i", input_url]

        if output_format == "jpg" or output_format == "png":
            ext = "jpg" if output_format == "jpg" else "png"
            out_path = out_dir / f"frame.{ext}"
            cmd = common_input + ["-frames:v", "1", "-q:v", "3", str(out_path)]
        elif output_format == "mp4":
            out_path = out_dir / "output.mp4"
            cmd = common_input + ["-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-c:a", "aac", "-movflags", "+faststart", str(out_path)]
        elif output_format == "webm":
            out_path = out_dir / "output.webm"
            cmd = common_input + ["-c:v", "libvpx", "-deadline", "realtime", "-c:a", "libopus", str(out_path)]
        elif output_format == "http_ts":
            out_path = out_dir / "stream.ts"
            cmd = common_input + ["-c", "copy", "-f", "mpegts", str(out_path)]
        elif output_format == "http_hls":
            out_path = out_dir / "index.m3u8"
            cmd = common_input + [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                "-f",
                "hls",
                "-hls_time",
                "4",
                "-hls_list_size",
                "5",
                "-hls_flags",
                "delete_segments",
                str(out_path),
            ]
        elif output_format == "dash":
            out_path = out_dir / "manifest.mpd"
            cmd = common_input + [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                "-f",
                "dash",
                "-seg_duration",
                "4",
                str(out_path),
            ]
        else:
            return StreamResult(success=False, output_path=None, backend_name="ffmpeg", error="unsupported output format")

        ok, err = await self._run_ffmpeg(cmd)
        if not ok:
            return StreamResult(success=False, output_path=None, backend_name="ffmpeg", error=err)

        return StreamResult(success=True, output_path=str(out_path), backend_name="ffmpeg")
