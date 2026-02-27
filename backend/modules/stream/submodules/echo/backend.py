from __future__ import annotations

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


class EchoBackend(IStreamBackend):
    """Dummy backend для тестов loader/router."""

    def get_capabilities(self) -> dict:
        return {
            "protocols": ["http", "udp", "rtsp"],
            "outputs": ["http_ts", "http_hls", "jpg"],
            "features": [],
            "priority_matrix": {
                "http": {"http_ts": 10, "http_hls": 10},
                "udp": {"http_ts": 10},
                "rtsp": {"jpg": 10},
            },
        }

    def match_score(self, input_proto: str, output_format: str) -> int:
        caps = self.get_capabilities()
        if input_proto in caps.get("protocols", []) and output_format in caps.get("outputs", []):
            return 10
        return 0

    async def initialize(self, config: dict) -> bool:  # pragma: no cover - dummy
        return True

    async def health_check(self) -> bool:  # pragma: no cover - dummy
        return True

    async def shutdown(self) -> None:  # pragma: no cover - dummy
        return None

    async def process(self, task: StreamTask) -> StreamResult:
        return StreamResult(
            success=True,
            output_path=f"/tmp/{task.id}.echo",
            metrics={"echo": True},
            backend_name="echo",
        )
