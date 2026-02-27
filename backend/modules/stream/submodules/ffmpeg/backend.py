from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


class FFmpegBackend(IStreamBackend):
    """Заглушка ffmpeg backend (enable=False по умолчанию)."""

    def __init__(self):
        self._available = False

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "protocols": ["udp", "http", "rtsp", "srt", "hls", "file"],
            "outputs": ["http_ts", "http_hls", "webrtc", "jpg", "png", "mp4"],
            "features": ["transcoding"],
            "priority_matrix": {
                "udp": {"http_ts": 80, "http_hls": 85},
                "rtsp": {"http_hls": 90, "jpg": 90},
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

    async def process(self, task: StreamTask) -> StreamResult:
        # Пока stub: просто создаём пустой файл и возвращаем путь
        out_dir = Path("/tmp")
        out_path = out_dir / f"{task.id}.{task.output_format}"
        out_dir.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, out_path.write_bytes, b"")
        return StreamResult(success=True, output_path=str(out_path), backend_name="ffmpeg")
