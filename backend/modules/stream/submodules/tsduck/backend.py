from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


class TSDuckBackend(IStreamBackend):
    """Заглушка TSDuck backend (disabled by default)."""

    def __init__(self):
        self._available = False

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "protocols": ["udp", "srt"],
            "outputs": ["http_ts"],
            "features": ["playback"],
            "priority_matrix": {
                "udp": {"http_ts": 60},
                "srt": {"http_ts": 55},
            },
        }

    def match_score(self, input_proto: str, output_format: str) -> int:
        caps = self.get_capabilities()
        if input_proto in caps.get("protocols", []) and output_format in caps.get("outputs", []):
            return int((caps.get("priority_matrix", {}).get(input_proto, {}) or {}).get(output_format, 30))
        return 0

    async def initialize(self, config: dict[str, Any]) -> bool:
        self._available = bool(config.get("enabled", False))
        return self._available

    async def health_check(self) -> bool:
        return self._available

    async def shutdown(self) -> None:
        return None

    async def process(self, task: StreamTask) -> StreamResult:
        out_dir = Path("/tmp")
        out_path = out_dir / f"{task.id}.tsduck.{task.output_format}"
        out_dir.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, out_path.write_bytes, b"")
        return StreamResult(success=True, output_path=str(out_path), backend_name="tsduck")
