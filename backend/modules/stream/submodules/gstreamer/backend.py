from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path
from typing import Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


_NETWORK_PROTOCOLS = ["http", "https", "rtsp", "rtmp", "rtmps", "udp", "srt", "rtp"]
_BROWSER_OUTPUTS = ["http_ts", "http_hls", "webrtc"]


class GStreamerBackend(IStreamBackend):
    """GStreamer backend: сетевые входы, браузерные mp4/webm выходы."""

    def __init__(self):
        self._available = False

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "protocols": _NETWORK_PROTOCOLS,
            "outputs": _BROWSER_OUTPUTS,
            "features": ["transcoding", "browser_formats"],
            "priority_matrix": {
                "http": {"http_hls": 60, "http_ts": 55},
                "https": {"http_hls": 60, "http_ts": 55},
                "rtsp": {"http_hls": 65, "http_ts": 60},
                "udp": {"http_ts": 55},
                "srt": {"http_ts": 55},
            },
        }

    def match_score(self, input_proto: str, output_format: str) -> int:
        caps = self.get_capabilities()
        if input_proto in caps.get("protocols", []) and output_format in caps.get("outputs", []):
            return int((caps.get("priority_matrix", {}).get(input_proto, {}) or {}).get(output_format, 30))
        return 0

    async def initialize(self, config: dict[str, Any]) -> bool:
        gst = shutil.which("gst-launch-1.0")
        self._available = bool(gst)
        return self._available

    async def health_check(self) -> bool:
        return self._available

    async def shutdown(self) -> None:
        return None

    async def _run_gst(self, cmd: list[str], timeout: float = 60.0) -> tuple[bool, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return False, "gst timeout"
            if proc.returncode != 0:
                return False, stderr.decode(errors="ignore")
            return True, ""
        except FileNotFoundError:
            return False, "gst-launch-1.0 not installed"
        except Exception as exc:  # pragma: no cover
            return False, str(exc)

    async def process(self, task: StreamTask) -> StreamResult:
        if not self._available:
            return StreamResult(success=False, output_path=None, backend_name="gstreamer", error="gstreamer unavailable")

        output_format = task.output_format or "http_ts"
        input_url = task.input_url
        if not input_url:
            return StreamResult(success=False, output_path=None, backend_name="gstreamer", error="input_url required")

        if not any(input_url.startswith(proto) for proto in ("http://", "https://", "rtsp://", "rtmp://", "rtmps://", "udp://", "srt://", "rtp://")):
            return StreamResult(success=False, output_path=None, backend_name="gstreamer", error="protocol not allowed")

        out_dir = Path("/tmp/stream_gst") / (task.id or uuid.uuid4().hex)
        out_dir.mkdir(parents=True, exist_ok=True)

        if output_format not in _BROWSER_OUTPUTS:
            return StreamResult(success=False, output_path=None, backend_name="gstreamer", error="unsupported output format")

        if output_format == "webrtc":
            return StreamResult(success=False, output_path=None, backend_name="gstreamer", error="webrtc not supported by gstreamer stub")

        if output_format == "http_ts":
            out_path = out_dir / "stream.ts"
            cmd = [
                "gst-launch-1.0",
                "-e",
                "uridecodebin",
                f"uri={input_url}",
                "name=src",
                "src.",
                "!",
                "queue",
                "!",
                "tsmux",
                "!",
                "filesink",
                f"location={out_path}",
            ]
        else:  # http_hls
            out_path = out_dir / "index.m3u8"
            # hls sink via hlssink2 if available
            cmd = [
                "gst-launch-1.0",
                "-e",
                "uridecodebin",
                f"uri={input_url}",
                "name=src",
                "src.",
                "!",
                "queue",
                "!",
                "x264enc",
                "tune=zerolatency",
                "speed-preset=ultrafast",
                "!",
                "h264parse",
                "!",
                "mpegtsmux",
                "!",
                "hlssink2",
                f"playlist-location={out_path}",
                f"location={out_dir/'segment_%05d.ts'}",
                "target-duration=4",
                "max-files=5",
            ]

        ok, err = await self._run_gst(cmd)
        if not ok:
            return StreamResult(success=False, output_path=None, backend_name="gstreamer", error=err)

        return StreamResult(success=True, output_path=str(out_path), backend_name="gstreamer")
