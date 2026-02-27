from __future__ import annotations

import json
import uuid
from typing import Any

from backend.modules.stream.core.contract import IStreamBackend
from backend.modules.stream.core.types import StreamResult, StreamTask


class PureWebRTCBackend(IStreamBackend):
    """Минимальный WebRTC stub без внешних зависимостей: генерирует offer/answer JSON."""

    def __init__(self):
        self._available = True

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "protocols": ["http", "webrtc", "rtsp"],
            "outputs": ["webrtc"],
            "features": ["python_only", "webrtc"],
            "priority_matrix": {
                "http": {"webrtc": 60},
                "rtsp": {"webrtc": 60},
            },
        }

    def match_score(self, input_proto: str, output_format: str) -> int:
        caps = self.get_capabilities()
        if input_proto in caps.get("protocols", []) and output_format in caps.get("outputs", []):
            return int((caps.get("priority_matrix", {}).get(input_proto, {}) or {}).get(output_format, 20))
        return 0

    async def initialize(self, config: dict[str, Any]) -> bool:
        self._available = True
        return True

    async def health_check(self) -> bool:
        return self._available

    async def shutdown(self) -> None:
        return None

    async def process(self, task: StreamTask) -> StreamResult:
        # Минимальный signaling stub: возвращаем “offer/answer” JSON blob.
        session_id = task.id or str(uuid.uuid4())
        payload = {
            "session_id": session_id,
            "offer": {
                "type": "offer",
                "sdp": f"v=0\no=- {session_id} 1 IN IP4 127.0.0.1\ns=PureWebRTCStub\n",
            },
            "answer": {
                "type": "answer",
                "sdp": f"v=0\no=- {session_id} 1 IN IP4 127.0.0.1\ns=PureWebRTCStubAnswer\n",
            },
        }
        return StreamResult(success=True, output_path=json.dumps(payload), backend_name="pure_webrtc")
